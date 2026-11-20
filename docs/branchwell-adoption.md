# Branchwell evidence adoption

The default main branch holds a README. This branch builds on the active Graphify HQ vault at 87638fb, which has a case catalog, verification tooling, and archived source pins. The published 288-scenario expansion is a proposal set. It is distinct from the cases exercised by the vault workflow.

## Branchwell backend graph

Start with three tracked JavaScript modules under `server/`. Keep SQLite data, account activity, tokens and local machine paths out of the graph and its artifacts. Run the structural extraction from the Branchwell checkout. Graphify 0.9.91 measured 30 nodes, 44 edges, and four communities in the initial backend. The exported graph showed no dangling endpoints or collapsed pairs in the built graph.

```sh
graphify extract server --out .
graphify cluster-only . --no-label
graphify query "What calls syncGitHub and where is the repository snapshot saved?"
```

Inspect `graphify-out/GRAPH_REPORT.md`, `graph.html`, and `graph.json`. The server calls the GitHub sync and profile parser. The SQLite write is confirmed from the HTTP handler and store source. Record the source commit and graph version when sharing evidence.

## Veraphify v0.0.9 adoption

Use [Veraphify v0.0.9 at `ed56500`](https://github.com/vixttha/Veraphify/commit/ed5650085e33cf142a37de695757a4df999a7cf3) to import, verify, and look up source-linked archives. This Git SHA is the merged mechanical revision. The [adopter walkthrough](https://github.com/vixttha/Veraphify/blob/ed5650085e33cf142a37de695757a4df999a7cf3/docs/adopter-walkthrough.md) documents the archive commands and limits. The Graphify producer and the Veraphify archive reader have separate version pins.

The public adoption check archives this guide's reviewed Graphify command and verifies its exact citation using the public checkout. Keep application code, repository profiles, tokens, SQLite and Supabase data in the owner-approved private workspace. Application verification needs an approved private execution path.

The [public workflow](../.github/workflows/veraphify-adoption.yml) checks the source pin, runs the Graphify MCP check, compares the archive SHA-256, and verifies the citation against the exact Git blob. The disposable archive version `v0.0.0.1` identifies the probe. Each public run retains a small receipt with the adopter SHA, Veraphify SHA, and citation.
