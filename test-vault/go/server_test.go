package graphify_test

import (
	"context"
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
}

func requireStats(t *testing.T, ctx context.Context, session *mcp.ClientSession, want string) {
	t.Helper()
	reply, err := callText(ctx, session, "graph_stats", nil)
	if err != nil {
		t.Fatal(err)
	}
	requireText(t, reply, "Built at commit: "+want)
}
