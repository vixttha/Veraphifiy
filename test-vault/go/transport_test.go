package graphify_test

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const citationReply = "Built at commit: " + source

type fixtureRequest struct {
	ID     json.RawMessage `json:"id"`
	Method string          `json:"method"`
	Params struct {
		Name   string `json:"name"`
		Cursor string `json:"cursor"`
	} `json:"params"`
}

// Controlled stdio server for the protocol branches that the frozen archive
// cannot produce on demand. The parent uses the normal SDK CommandTransport.
func TestMCPFixtureProcess(t *testing.T) {
	mode := os.Getenv("GHQ_MCP_FIXTURE")
	if mode == "" {
		return
	}
	writer := json.NewEncoder(os.Stdout)
	reader := bufio.NewScanner(os.Stdin)
	initialized := false
	for reader.Scan() {
		var req fixtureRequest
		if err := json.Unmarshal(reader.Bytes(), &req); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(2)
		}
		if len(req.ID) == 0 {
			if req.Method == "notifications/initialized" {
				initialized = true
			}
			continue
		}
		message := map[string]any{"jsonrpc": "2.0", "id": req.ID}
		switch req.Method {
		case "initialize":
			version := "2025-11-25"
			if mode == "bad-version" {
				version = "1900-01-01"
			}
			capabilities := map[string]any{"tools": map[string]any{}}
			if mode == "no-tools" {
				capabilities = map[string]any{}
			}
			if mode == "initialization-boundary" {
				time.Sleep(30 * time.Millisecond)
			}
			message["result"] = map[string]any{
				"protocolVersion": version, "capabilities": capabilities,
				"serverInfo": map[string]string{"name": "vault-fixture", "version": "1"},
			}
		case "tools/list":
			if !initialized || mode == "no-tools" {
				os.Exit(2)
			}
			if req.Params.Cursor == "" {
				message["result"] = map[string]any{"tools": []any{fixtureTool("graph_stats")}, "nextCursor": "page-two"}
			} else if req.Params.Cursor != "page-two" {
				os.Exit(2)
			} else if mode == "cursor-cycle" {
				message["result"] = map[string]any{"tools": []any{fixtureTool("get_node")}, "nextCursor": req.Params.Cursor}
			} else {
				message["result"] = map[string]any{"tools": []any{fixtureTool("get_node")}}
			}
		case "tools/call":
			if !initialized {
				os.Exit(2)
			}
			switch req.Params.Name {
			case "missing":
				message["error"] = map[string]any{"code": -32602, "message": "fixture tool not found"}
			case "error":
				message["result"] = fixtureContent("fixture tool failure", true)
			case "empty":
				message["result"] = map[string]any{"content": []any{}}
			case "blocked":
				continue
			case "multiline":
				message["result"] = fixtureContent("first line\nsecond line", false)
			case "fragmented":
				message["result"] = fixtureContent(strings.Repeat("x", 65536)+"é\nend", false)
				data, err := json.Marshal(message)
				if err != nil {
					os.Exit(2)
				}
				split := strings.Index(string(data), "é") + 1
				if split < 1 {
					os.Exit(2)
				}
				if _, err = os.Stdout.Write(data[:split]); err != nil {
					os.Exit(2)
				}
				if _, err = os.Stdout.Write(append(data[split:], '\n')); err != nil {
					os.Exit(2)
				}
				continue
			case "unmatched", "id-type":
				wrongID := any(8675309)
				if req.Params.Name == "id-type" {
					wrongID = string(req.ID)
				}
				if writer.Encode(map[string]any{"jsonrpc": "2.0", "id": wrongID, "result": fixtureContent("wrong request", false)}) != nil {
					os.Exit(2)
				}
				message["result"] = fixtureContent(citationReply, false)
			case "notification":
				if writer.Encode(map[string]any{"jsonrpc": "2.0", "method": "notifications/message",
					"params": map[string]any{"level": "info", "data": "independent message"}}) != nil {
					os.Exit(2)
				}
				message["result"] = fixtureContent(citationReply, false)
			case "get_node":
				message["result"] = fixtureContent(anchor, false)
			default:
				message["result"] = fixtureContent(citationReply, false)
			}
		default:
			message["result"] = map[string]any{}
		}
		if writer.Encode(message) != nil {
			os.Exit(2)
		}
	}
	if reader.Err() != nil {
		os.Exit(2)
	}
	os.Exit(0)
}

func fixtureTool(name string) map[string]any {
	return map[string]any{"name": name, "inputSchema": map[string]string{"type": "object"}}
}

func fixtureContent(value string, failed bool) map[string]any {
	return map[string]any{"isError": failed, "content": []any{map[string]string{"type": "text", "text": value}}}
}

func connectFixture(ctx context.Context, mode string) (*mcp.ClientSession, error) {
	command := exec.Command(os.Args[0], "-test.run=^TestMCPFixtureProcess$")
	command.Env = append(command.Environ(), "GHQ_MCP_FIXTURE="+mode)
	command.Stderr = os.Stderr
	client := mcp.NewClient(&mcp.Implementation{Name: "vault-protocol-test", Version: "1"}, nil)
	return client.Connect(ctx, &mcp.CommandTransport{Command: command}, nil)
}

func useFixture(t *testing.T, mode string) (context.Context, *mcp.ClientSession) {
	t.Helper()
	ctx, cancel := context.WithTimeout(t.Context(), 6*time.Second)
	t.Cleanup(cancel)
	session, err := connectFixture(ctx, mode)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = session.Close() })
	return ctx, session
}

func requireReply(t *testing.T, ctx context.Context, session *mcp.ClientSession, tool, want string) {
	t.Helper()
	reply, err := callText(ctx, session, tool, nil)
	if err != nil || reply != want {
		t.Fatalf("%s reply mismatch (length %d, want %d): %v", tool, len(reply), len(want), err)
	}
}

func listAllTools(ctx context.Context, session *mcp.ClientSession) ([]*mcp.Tool, error) {
	if session.InitializeResult().Capabilities.Tools == nil {
		return nil, fmt.Errorf("session did not negotiate tool discovery")
	}
	var tools []*mcp.Tool
	params := &mcp.ListToolsParams{}
	seen := map[string]bool{}
	for {
		page, err := session.ListTools(ctx, params)
		if err != nil {
			return nil, err
		}
		tools = append(tools, page.Tools...)
		if page.NextCursor == "" {
			return tools, nil
		}
		if seen[page.NextCursor] {
			return nil, fmt.Errorf("repeated tools cursor %q", page.NextCursor)
		}
		seen[page.NextCursor] = true
		params.Cursor = page.NextCursor
	}
}

func protocolCases(t *testing.T) {
	t.Run("GHQ-GO-015 surfaces a protocol error and keeps the session usable", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		result, err := session.CallTool(ctx, &mcp.CallToolParams{Name: "missing"})
		if err == nil || result != nil || !strings.Contains(err.Error(), "fixture tool not found") {
			t.Fatalf("expected JSON-RPC invocation error, got %v %v", result, err)
		}
		requireReply(t, ctx, session, "graph_stats", citationReply)
	})
	t.Run("GHQ-GO-016 bounds a blocked request without closing its sibling", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		limited, cancel := context.WithTimeout(ctx, 200*time.Millisecond)
		defer cancel()
		outcome := make(chan error, 1)
		go func() {
			_, err := callText(limited, session, "blocked", nil)
			outcome <- err
		}()
		requireReply(t, ctx, session, "graph_stats", citationReply)
		if err := <-outcome; err == nil || limited.Err() != context.DeadlineExceeded {
			t.Fatalf("blocked caller did not reach its own deadline: %v", err)
		}
		requireReply(t, ctx, session, "get_node", anchor)
	})
	t.Run("GHQ-GO-022 reconstructs fragmented UTF-8 on a real pipe", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		requireReply(t, ctx, session, "fragmented", strings.Repeat("x", 65536)+"é\nend")
		requireReply(t, ctx, session, "graph_stats", citationReply)
	})
	t.Run("GHQ-GO-024 decodes multiline content without splitting messages", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		requireReply(t, ctx, session, "multiline", "first line\nsecond line")
		requireReply(t, ctx, session, "get_node", anchor)
	})
	t.Run("GHQ-GO-025 requires negotiated tool discovery", func(t *testing.T) {
		ctx, session := useFixture(t, "no-tools")
		tools, err := listAllTools(ctx, session)
		if len(tools) != 0 || err == nil || !strings.Contains(err.Error(), "did not negotiate") {
			t.Fatalf("tool capability was not enforced: %v %v", tools, err)
		}
		if err := session.Ping(ctx, nil); err != nil {
			t.Fatalf("tool discovery was sent against an incompatible capability: %v", err)
		}
		readyCtx, ready := useFixture(t, "normal")
		if tools, err := listAllTools(readyCtx, ready); err != nil || len(tools) == 0 {
			t.Fatalf("negotiated control did not list tools: %v", err)
		}
	})

	t.Run("GHQ-GO-026 never assigns an unrelated response to the pending call", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		requireReply(t, ctx, session, "graph_stats", citationReply)
		got, err := callText(ctx, session, "unmatched", nil)
		if got == "wrong request" || (err == nil && got != citationReply) {
			t.Fatalf("unmatched reply escaped the SDK correlation checks: %q %v", got, err)
		}
	})
	t.Run("GHQ-GO-027 does not confuse tool-level failure with transport success", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		result, err := session.CallTool(ctx, &mcp.CallToolParams{Name: "error"})
		if err != nil || !result.IsError {
			t.Fatalf("expected a successful transport carrying an error reply: %v %v", result, err)
		}
		if _, err = callText(ctx, session, "error", nil); err == nil {
			t.Fatal("error text was accepted as evidence")
		}
		requireReply(t, ctx, session, "graph_stats", citationReply)
	})
	t.Run("GHQ-GO-028 does not confuse numeric and string request identities", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		requireReply(t, ctx, session, "graph_stats", citationReply)
		got, err := callText(ctx, session, "id-type", nil)
		if got == "wrong request" || (err == nil && got != citationReply) {
			t.Fatalf("type-mismatched reply escaped the SDK correlation checks: %q %v", got, err)
		}
	})
	t.Run("GHQ-GO-029 keeps a notification separate from evidence", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		requireReply(t, ctx, session, "notification", citationReply)
		requireReply(t, ctx, session, "get_node", anchor)
	})
	t.Run("GHQ-GO-031 rejects incompatible protocol versions", func(t *testing.T) {
		ctx, valid := useFixture(t, "normal")
		requireReply(t, ctx, valid, "graph_stats", citationReply)
		session, err := connectFixture(ctx, "bad-version")
		if err == nil {
			_ = session.Close()
			t.Fatal("client opened a session with an unsupported protocol version")
		}
		if !strings.Contains(strings.ToLower(err.Error()), "version") {
			t.Fatalf("unexpected rejection: %v", err)
		}
	})
	t.Run("GHQ-GO-032 discovers and invokes a tool from a later page", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		tools, err := listAllTools(ctx, session)
		if err != nil || len(tools) != 2 || tools[0].Name != "graph_stats" || tools[1].Name != "get_node" {
			t.Fatalf("unexpected discovery outcome: %v %v", tools, err)
		}
		requireReply(t, ctx, session, tools[1].Name, anchor)
	})
	t.Run("GHQ-GO-033 rejects a repeated pagination cursor without partial evidence", func(t *testing.T) {
		ctx, session := useFixture(t, "cursor-cycle")
		tools, err := listAllTools(ctx, session)
		if len(tools) != 0 || err == nil || !strings.Contains(err.Error(), "repeated tools cursor") {
			t.Fatalf("repeated cursor was not rejected with its specific diagnostic: %v %v", tools, err)
		}
	})
	t.Run("GHQ-GO-034 treats error-free empty tool content as missing evidence", func(t *testing.T) {
		ctx, session := useFixture(t, "normal")
		raw, err := session.CallTool(ctx, &mcp.CallToolParams{Name: "empty"})
		if err != nil || raw.IsError || len(raw.Content) != 0 {
			t.Fatalf("unexpected empty result: %v %v", raw, err)
		}
		got, err := callText(ctx, session, "empty", nil)
		if err == nil || got != "" {
			t.Fatalf("empty content yielded evidence: %q %v", got, err)
		}
		requireReply(t, ctx, session, "get_node", anchor)
	})
	t.Run("GHQ-GO-038 sends evidence requests only after the initialization exchange", func(t *testing.T) {
		ctx, session := useFixture(t, "initialization-boundary")
		requireReply(t, ctx, session, "graph_stats", citationReply)
	})

}
