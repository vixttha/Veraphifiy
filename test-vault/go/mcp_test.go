package graphify_test

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	feature = "feature:archive-verification"
	anchor  = "implemented_in:tools/verify_archive.py:L30"
	file    = "file:tools/verify_archive.py"
	source  = "062fb633838daa42204289d889850c03e89d45eb"
)

func TestGraphifyMCP(t *testing.T) {
	archive := os.Getenv("GRAPHIFY_HQ_ARCHIVE")
	if archive == "" {
		t.Fatal("set GRAPHIFY_HQ_ARCHIVE to the pinned v0.0.8 graph directory")
	}
	archive, err := filepath.Abs(archive)
	if err != nil {
		t.Fatal(err)
	}
	python := os.Getenv("GRAPHIFY_HQ_PYTHON")
	if python == "" {
		python = "python"
	}
	command := exec.Command(python, "-m", "graphify.serve", filepath.Join(archive, "graph.json"))
	command.Dir = t.TempDir()
	command.Env = append(command.Environ(), "GRAPHIFY_QUERY_LOG_DISABLE=1")
	command.Stderr = os.Stderr
	ctx, cancel := context.WithTimeout(t.Context(), 30*time.Second)
	defer cancel()
	client := mcp.NewClient(&mcp.Implementation{Name: "graphify-hq-test-vault", Version: "1"}, nil)
	session, err := client.Connect(ctx, &mcp.CommandTransport{Command: command}, nil)
	if err != nil {
		t.Fatalf("connect to the pinned Graphify MCP server: %v", err)
	}
	defer func() {
		if err := session.Close(); err != nil {
			t.Errorf("close Graphify MCP session: %v", err)
		}
	}()

	call := func(t *testing.T, name string, args map[string]any) string {
		t.Helper()
		reply, err := callText(ctx, session, name, args)
		if err != nil {
			t.Fatal(err)
		}
		return reply
	}

	t.Run("GHQ-GO-001 discover tools and input schema", func(t *testing.T) {
		result, err := session.ListTools(ctx, nil)
		if err != nil {
			t.Fatal(err)
		}
		var neighbors *mcp.Tool
		names := make(map[string]bool)
		for _, tool := range result.Tools {
			names[tool.Name] = true
			if tool.Name == "get_neighbors" {
				neighbors = tool
			}
		}
		for _, name := range []string{"get_neighbors", "get_node", "graph_stats", "query_graph", "shortest_path"} {
			if !names[name] {
				t.Errorf("MCP did not advertise %q", name)
			}
		}
		if neighbors == nil {
			t.Fatal("no get_neighbors schema")
		}
		raw, err := json.Marshal(neighbors.InputSchema)
		if err != nil {
			t.Fatal(err)
		}
		var schema struct {
			Properties map[string]struct{ Type string } `json:"properties"`
		}
		if err := json.Unmarshal(raw, &schema); err != nil {
			t.Fatal(err)
		}
		for name, want := range map[string]string{"node_id": "string", "relation_filter": "string", "token_budget": "integer"} {
			if got := schema.Properties[name].Type; got != want {
				t.Errorf("get_neighbors property %s has type %q, want %q", name, got, want)
			}
		}
	})

	t.Run("GHQ-GO-002 inspect the pinned graph over stdio", func(t *testing.T) {
		got := call(t, "graph_stats", nil)
		requireText(t, got, "Nodes: 33\n", "Edges: 51\n", "Built at commit: "+source+"\n")
	})

	t.Run("GHQ-GO-003 recover implementation links via relation filtering", func(t *testing.T) {
		got := call(t, "get_neighbors", map[string]any{"node_id": feature, "relation_filter": "implemented_in"})
		requireText(t, got, "--> tools/verify_archive.py L30 [implemented_in]", "at=tools/verify_archive.py:L30")
		if count := strings.Count(got, "[implemented_in]"); count != 3 {
			t.Errorf("got %d implementation links, want 3:\n%s", count, got)
		}
		for _, other := range []string{"[documented_in]", "[changed_in]", "[tested_by]"} {
			if strings.Contains(got, other) {
				t.Errorf("unrequested relation %q leaked into %q", other, got)
			}
		}
	})

	t.Run("GHQ-GO-004 resolve a discovered anchor to its exact source location", func(t *testing.T) {
		got := call(t, "get_node", map[string]any{"node_id": anchor})
		requireText(t, got, "ID: "+anchor+"\n", "Source: tools/verify_archive.py L30\n")
	})

	t.Run("GHQ-GO-005 distinguish an unknown feature", func(t *testing.T) {
		unknown := "feature:ghq-vault-no-such-feature"
		got := call(t, "get_neighbors", map[string]any{"node_id": unknown})
		if got != "No node matching '"+unknown+"' found." {
			t.Errorf("expected a no-match result for %q, got %q", unknown, got)
		}
	})

	t.Run("GHQ-GO-006 receive input guidance and keep the session usable", func(t *testing.T) {
		got := call(t, "get_neighbors", map[string]any{})
		requireText(t, got, "Provide a node label or id")
		got = call(t, "get_node", map[string]any{"node_id": anchor})
		requireText(t, got, "ID: "+anchor)
	})

	t.Run("GHQ-GO-007 keep concurrent replies associated with their tool calls", func(t *testing.T) {
		type answer struct {
			name, text string
			err        error
		}
		answers := make(chan answer, 2)
		go func() {
			got, err := callText(ctx, session, "graph_stats", nil)
			answers <- answer{"graph_stats", got, err}
		}()
		go func() {
			got, err := callText(ctx, session, "get_node", map[string]any{"node_id": anchor})
			answers <- answer{"get_node", got, err}
		}()
		expected := map[string]string{"graph_stats": "Built at commit: " + source, "get_node": "ID: " + anchor}
		for range 2 {
			got := <-answers
			if got.err != nil {
				t.Errorf("%s: %v", got.name, got.err)
				continue
			}
			requireText(t, got.text, expected[got.name])
		}
	})

	t.Run("GHQ-GO-008 discover a directed path from the feature to the inventoried file", func(t *testing.T) {
		got := call(t, "shortest_path", map[string]any{"source": feature, "target": file})
		requireText(t, got, "--implemented_in", "--located_in", "tools/verify_archive.py")
		reverse := call(t, "shortest_path", map[string]any{"source": file, "target": feature})
		requireText(t, reverse, "No directed path found")
		reverse = call(t, "shortest_path", map[string]any{"source": file, "target": feature, "undirected": true})
		requireText(t, reverse, "<--located_in", "<--implemented_in")
	})

	t.Run("GHQ-GO-009 report the actual source and warn when checkout HEAD is different", func(t *testing.T) {
		head, err := exec.Command("git", "-C", archive, "rev-parse", "HEAD").Output()
		if err != nil {
			t.Fatalf("the pinned graph fixture must live in its Git checkout: %v", err)
		}
		checkout := strings.TrimSpace(string(head))
		if checkout == source || len(checkout) != 40 {
			t.Fatalf("fixture must distinguish archive source and checkout HEAD, got %q", checkout)
		}
		got := call(t, "graph_stats", nil)
		requireText(t, got, "Built at commit: "+source, "HEAD is "+checkout[:7]+", graph built at "+source[:7]+": graph may be stale")
	})

	t.Run("GHQ-GO-010 find the implementation from a feature name without a node ID", func(t *testing.T) {
		got := call(t, "query_graph", map[string]any{"question": "archive verification", "depth": 2, "token_budget": 8000})
		requireText(t, got, "EDGE Reproducible Graphify archive --implemented_in [EXTRACTED]--> tools/verify_archive.py L30")
	})

	t.Run("GHQ-GO-011 warn when a low token budget hides additional neighbors", func(t *testing.T) {
		got := call(t, "get_neighbors", map[string]any{"node_id": feature, "token_budget": 20})
		if !strings.HasPrefix(got, "[!] TRUNCATED:") {
			t.Errorf("a bounded reply must identify itself as incomplete before listing evidence: %q", got)
		}
		full := call(t, "get_neighbors", map[string]any{"node_id": feature, "token_budget": 8000})
		if strings.Contains(full, "[!] TRUNCATED:") {
			t.Errorf("the full reply should fit within the larger budget: %q", full)
		}
		requireText(t, full, "[implemented_in]", "[documented_in]", "[changed_in]", "[tested_by]")
	})
}

func callText(ctx context.Context, session *mcp.ClientSession, name string, args map[string]any) (string, error) {
	result, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		return "", fmt.Errorf("%s: %w", name, err)
	}
	var lines []string
	for _, item := range result.Content {
		if text, ok := item.(*mcp.TextContent); ok {
			lines = append(lines, text.Text)
		}
	}
	if result.IsError || len(lines) == 0 {
		return "", fmt.Errorf("%s did not return a successful text result: %v", name, lines)
	}
	return strings.Join(lines, "\n"), nil
}

func requireText(t *testing.T, got string, fragments ...string) {
	t.Helper()
	for _, want := range fragments {
		if !strings.Contains(got, want) {
			t.Errorf("response does not contain %q:\n%s", want, got)
		}
	}
}
