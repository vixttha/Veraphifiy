package graphify_test

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func serverCases(t *testing.T, archive string) {
	t.Run("GHQ-GO-012 bounds a request after a real server exits", func(t *testing.T) {
		ctx, session, command := openGraph(t, archive)
		requireStats(t, ctx, session, source)
		if err := command.Process.Kill(); err != nil {
			t.Fatal(err)
		}
		closed := make(chan error, 1)
		go func() { closed <- session.Wait() }()
		select {
		case <-closed:
		case <-ctx.Done():
			t.Fatal("session did not observe the server exit")
		}
		bounded, cancel := context.WithTimeout(ctx, time.Second)
		defer cancel()
		got, err := callText(bounded, session, "graph_stats", nil)
		if err == nil || got != "" || bounded.Err() != nil {
			t.Fatalf("closed session did not return its own connection error: %q %v", got, err)
		}
		nextCtx, nextSession, _ := openGraph(t, archive)
		requireStats(t, nextCtx, nextSession, source)
	})

	t.Run("GHQ-GO-014 keeps simultaneously connected archive identities separate", func(t *testing.T) {
		raw, err := os.ReadFile(filepath.Join(archive, "graph.json"))
		if err != nil {
			t.Fatal(err)
		}
		variantDir := t.TempDir()
		variantCommit := strings.Repeat("a", 40)
		variantPath := "tools/independent_archive.py"
		variant := strings.ReplaceAll(string(raw), source, variantCommit)
		variant = strings.ReplaceAll(variant, "tools/verify_archive.py", variantPath)
		if err := os.WriteFile(filepath.Join(variantDir, "graph.json"), []byte(variant), 0600); err != nil {
			t.Fatal(err)
		}
		firstCtx, first, _ := openGraph(t, archive)
		secondCtx, second, _ := openGraph(t, variantDir)
		requireStats(t, firstCtx, first, source)
		requireStats(t, secondCtx, second, variantCommit)
		for _, variant := range []struct {
			ctx     context.Context
			session *mcp.ClientSession
			matches string
			foreign string
		}{
			{firstCtx, first, "tools/verify_archive.py", variantPath},
			{secondCtx, second, variantPath, "tools/verify_archive.py"},
		} {
			reply, err := callText(variant.ctx, variant.session, "get_neighbors",
				map[string]any{"node_id": feature, "relation_filter": "implemented_in"})
			if err != nil || !strings.Contains(reply, variant.matches+" L30") || strings.Contains(reply, variant.foreign) {
				t.Fatalf("graph responses were mixed: %q %v", reply, err)
			}
		}
	})

	t.Run("GHQ-GO-017 reaps Graphify subprocesses after session closure", func(t *testing.T) {
		for range 2 {
			ctx, session, command := openGraph(t, archive)
			requireStats(t, ctx, session, source)
			if err := session.Close(); err != nil {
				t.Fatal(err)
			}
			if command.ProcessState == nil || !command.ProcessState.Exited() {
				t.Fatal("session returned before the child was reaped")
			}
			bounded, cancel := context.WithTimeout(ctx, time.Second)
			reply, err := callText(bounded, session, "graph_stats", nil)
			cancel()
			if err == nil || reply != "" {
				t.Fatalf("closed pipes still returned tool output: %q %v", reply, err)
			}
		}
	})

	t.Run("GHQ-GO-019 reports source freshness for detached Git checkouts", func(t *testing.T) {
		root := t.TempDir()
		git := func(args ...string) string {
			t.Helper()
			cmd := exec.Command("git", args...)
			cmd.Dir = root
			output, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("git: %v %s", err, output)
			}
			return strings.TrimSpace(string(output))
		}
		commit := func(message string) string {
			git("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid",
				"-c", "commit.gpgsign=false", "commit", "-qm", message, "--allow-empty")
			return git("rev-parse", "HEAD")
		}
		git("init", "-q")
		pinned := commit("pinned archive")
		git("checkout", "-q", "--detach", pinned)
		raw, err := os.ReadFile(filepath.Join(archive, "graph.json"))
		if err != nil {
			t.Fatal(err)
		}
		graph := strings.ReplaceAll(string(raw), source, pinned)
		if err := os.WriteFile(filepath.Join(root, "graph.json"), []byte(graph), 0600); err != nil {
			t.Fatal(err)
		}
		for _, changed := range []bool{false, true} {
			head := pinned
			if changed {
				head = commit("different detached HEAD")
			}
			ctx, session, _ := openGraph(t, root)
			reply, err := callText(ctx, session, "graph_stats", nil)
			if err != nil {
				t.Fatal(err)
			}
			requireText(t, reply, "Built at commit: "+pinned)
			if strings.Contains(reply, "graph may be stale") != changed {
				t.Fatalf("incorrect staleness for HEAD %s: %q", head, reply)
			}
		}
	})

	t.Run("GHQ-GO-020 bounds the reported path across a directed cycle and alternate route", func(t *testing.T) {
		var graph struct {
			Nodes json.RawMessage  `json:"nodes"`
			Links []map[string]any `json:"links"`
		}
		raw, err := os.ReadFile(filepath.Join(archive, "graph.json"))
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(raw, &graph); err != nil {
			t.Fatal(err)
		}
		alternative := "implemented_in:versions/v0.0.8/evidence_map.py:L203"
		graph.Links = append(graph.Links,
			map[string]any{"source": anchor, "target": feature, "relation": "tested_by", "confidence": "EXTRACTED"},
			map[string]any{"source": alternative, "target": file, "relation": "located_in", "confidence": "EXTRACTED"},
		)
		variant := writeGraphFixture(t, map[string]any{
			"directed": true, "multigraph": false, "nodes": graph.Nodes, "links": graph.Links, "built_at_commit": source,
		})
		ctx, session, _ := openGraph(t, variant)
		for _, hop := range []struct{ from, to, relation string }{
			{anchor, feature, "tested_by"}, {alternative, file, "located_in"},
		} {
			got, err := callText(ctx, session, "shortest_path", map[string]any{"source": hop.from, "target": hop.to, "max_hops": 1})
			if err != nil {
				t.Fatal(err)
			}
			requireText(t, got, "Shortest path (1 hops):", "--"+hop.relation+" [EXTRACTED]-->")
		}
		bounded, err := callText(ctx, session, "shortest_path", map[string]any{"source": feature, "target": file, "max_hops": 1})
		if err != nil || bounded != "Path exceeds max_hops=1 (2 hops found)." {
			t.Fatalf("incorrect path limit response: %q %v", bounded, err)
		}
		got, err := callText(ctx, session, "shortest_path", map[string]any{"source": feature, "target": file, "max_hops": 2})
		if err != nil {
			t.Fatal(err)
		}
		requireText(t, got, "Shortest path (2 hops):", "--implemented_in [EXTRACTED]-->", "--located_in [EXTRACTED]--> tools/verify_archive.py", "weakest of 2 equal-length routes")
		if strings.Count(got, "Reproducible Graphify archive") != 1 || strings.Contains(got, "--tested_by") {
			t.Fatalf("reported path revisited the starting node: %q", got)
		}
	})

	t.Run("GHQ-GO-035 joins a released MCP path with an exact source citation", func(t *testing.T) {
		var graph map[string]json.RawMessage
		raw, err := os.ReadFile(filepath.Join(archive, "graph.json"))
		if err != nil {
			t.Fatal(err)
		}
		if err := json.Unmarshal(raw, &graph); err != nil {
			t.Fatal(err)
		}
		var nodes []map[string]any
		if err := json.Unmarshal(graph["nodes"], &nodes); err != nil {
			t.Fatal(err)
		}
		for _, node := range nodes {
			if node["id"] == anchor {
				node["source_location"] = "L31"
			}
		}
		graph["nodes"], err = json.Marshal(nodes)
		if err != nil {
			t.Fatal(err)
		}
		variant := writeGraphFixture(t, graph)
		for _, candidate := range []struct{ directory, line string }{{archive, "L30"}, {variant, "L31"}} {
			ctx, session, _ := openGraph(t, candidate.directory)
			requireStats(t, ctx, session, source)
			path, err := callText(ctx, session, "shortest_path", map[string]any{"source": feature, "target": file})
			if err != nil {
				t.Fatal(err)
			}
			requireText(t, path, "--implemented_in [EXTRACTED]--> tools/verify_archive.py L30 --located_in [EXTRACTED]--> tools/verify_archive.py\n")
			location, err := callText(ctx, session, "get_node", map[string]any{"node_id": anchor})
			if err != nil {
				t.Fatal(err)
			}
			requireText(t, location, "ID: "+anchor+"\n", "Source: tools/verify_archive.py "+candidate.line+"\n")
			agrees := strings.Contains(location, "Source: tools/verify_archive.py L30\n")
			if agrees != (candidate.directory == archive) {
				t.Fatalf("path and source reply were reconciled incorrectly: %q and %q", path, location)
			}
		}
	})
}

func writeGraphFixture(t *testing.T, value any) string {
	t.Helper()
	data, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	directory := t.TempDir()
	if err := os.WriteFile(filepath.Join(directory, "graph.json"), data, 0600); err != nil {
		t.Fatal(err)
	}
	return directory
}

func requireStats(t *testing.T, ctx context.Context, session *mcp.ClientSession, want string) {
	t.Helper()
	reply, err := callText(ctx, session, "graph_stats", nil)
	if err != nil {
		t.Fatal(err)
	}
	requireText(t, reply, "Built at commit: "+want)
}
