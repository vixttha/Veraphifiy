# Branchwell Graphify adoption

The default main branch holds a README. This branch builds on the active Graphify HQ vault at 87638fb, which has a case catalog, verification tooling, and archived source pins. The published 288-scenario expansion is a proposal set. It is distinct from the cases exercised by the vault workflow.

## Branchwell backend graph

Start with three tracked JavaScript modules under `server/`. Keep SQLite data, account activity, tokens and local machine paths out of the graph and its artifacts. Run the structural extraction from the Branchwell checkout. Graphify 0.9.91 measured 30 nodes, 44 edges, and four communities in the initial backend. The exported graph showed no dangling endpoints or collapsed pairs in the built graph.

```sh
graphify extract server --out .
graphify cluster-only . --no-label
graphify query "What calls syncGitHub and where is the repository snapshot saved?"
```

Inspect `graphify-out/GRAPH_REPORT.md`, `graph.html`, and `graph.json`. The server calls the GitHub sync and profile parser. The SQLite write is confirmed from the HTTP handler and store source. Record the source commit and graph version when sharing evidence.
