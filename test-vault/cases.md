# Graphify HQ case catalog

The entries below have executable checks. The [initial three-language plan](PLAN.md) holds the proposed Python, Bash, and JavaScript cases.

| Case | Area | Priority | Suggested implementation | Expected outcome |
|---|---|---|---|---|
| GHQ-TS-001 | TypeScript | P1 | Require a successful lookup before reading citations. `npm --prefix test-vault/typescript test` | A consumer cannot read citations from an unresolved result. |
| GHQ-TS-002 | TypeScript | P1 | Convert exported source locations to editor line numbers. `npm --prefix test-vault/typescript test` | The compiler rejects a raw location such as L30 as a numeric line. |
| GHQ-TS-003 | TypeScript | P1 | Require a nonempty citation list on success. `npm --prefix test-vault/typescript test` | The compiler rejects a found result with zero citations. |
| GHQ-TS-004 | TypeScript | P0 | Resolve implementation citations from the pinned graph. `npm --prefix test-vault/typescript test` | The export yields all three expected implementation paths and one-based lines at the archived source commit. |
| GHQ-TS-005 | TypeScript | P1 | Require a known feature ID. `npm --prefix test-vault/typescript test` | An unknown ID or an evidence node ID cannot stand in for a feature. |
| GHQ-TS-006 | TypeScript | P1 | Separate implementation, documentation, and test links. `npm --prefix test-vault/typescript test` | Documentation and test links alone yield no implementation. |
| GHQ-TS-007 | TypeScript | P1 | Reject invalid editor line values. `npm --prefix test-vault/typescript test` | Null, zero, missing L prefix, and unsafe integers cannot be opened as source lines. |
| GHQ-TS-008 | TypeScript | P1 | Reject a dangling implementation anchor. `npm --prefix test-vault/typescript test` | A missing implementation node withholds the result even when other citations are valid. |
| GHQ-TS-009 | TypeScript | P1 | Reject a blank implementation path. `npm --prefix test-vault/typescript test` | A line with no source path does not become a navigation target. |
| GHQ-GO-001 | Go MCP | P1 | Discover MCP tools and input schema. `go test` in `test-vault/go` | A Go client sees the discovery tools and expected neighbor argument types. |
| GHQ-GO-002 | Go MCP | P0 | Read pinned graph identity and counts over stdio. `go test` in `test-vault/go` | Graphify serves 33 nodes and 51 edges at the archived source SHA. |
| GHQ-GO-003 | Go MCP | P0 | Filter feature neighbors by implementation relation. `go test` in `test-vault/go` | The three implementation edges remain and unrelated evidence relations are excluded. |
| GHQ-GO-004 | Go MCP | P0 | Resolve a discovered source anchor. `go test` in `test-vault/go` | The exact MCP node ID resolves to tools/verify_archive.py at line 30. |
| GHQ-GO-005 | Go MCP | P1 | Recognize a feature that cannot be found. `go test` in `test-vault/go` | The server returns an explicit no-match result for the requested ID. |
| GHQ-GO-006 | Go MCP | P1 | Continue after a request with no node selector. `go test` in `test-vault/go` | The server gives input guidance and the same session answers a valid lookup. |
| GHQ-GO-007 | Go MCP | P1 | Keep concurrent MCP replies associated with their requests. `go test` in `test-vault/go` | An overlapping stats and node lookup return their own evidence. |
| GHQ-GO-008 | Go MCP | P0 | Follow a directed implementation path to its inventory file. `go test` in `test-vault/go` | The forward route includes implemented_in and located_in. The reverse route requires undirected search. |
| GHQ-GO-009 | Go MCP | P1 | Detect when the loaded graph describes an older Git commit. `go test` in `test-vault/go` | The server states the real source SHA and reports stale checkout evidence. |
| GHQ-GO-010 | Go MCP | P0 | Discover implementation from an ordinary feature name. `go test` in `test-vault/go` | A query for archive verification returns its Graphify implementation file without a supplied node ID. |
| GHQ-GO-011 | Go MCP | P1 | Warn when a token budget truncates graph evidence. `go test` in `test-vault/go` | The bounded response announces truncation. A larger budget returns the full set of relevant neighbors. |
| GHQ-PS-001 | PowerShell | P0 | Invoke the verifier with literal paths. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The CLI returns 0 for a valid bundle in paths with spaces and brackets. |
| GHQ-PS-002 | PowerShell | P0 | Handle a missing required receipt at the native boundary. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | PowerShell observes exit 1 and a named missing check. |
| GHQ-PS-003 | PowerShell | P1 | Append pass and fail verdicts to the Actions summary. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The verdicts arrive in order and the summary’s existing contents survive. |
| GHQ-PS-004 | PowerShell | P1 | Supply run identity through the process environment. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The child verifies the bundle using the inherited run ID and attempt. |
| GHQ-PS-005 | PowerShell | P1 | Preserve explicit run identity options. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | Explicit values take precedence over a different inherited run and attempt. |
| GHQ-PS-006 | PowerShell | P0 | Pass exact shared evidence bytes to the verifier. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The verifier accepts the PowerShell digest and rejects changed bytes of the same length. |
| GHQ-PS-007 | PowerShell | P1 | Report a missing run identity in local execution. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | Without flags or environment values the verifier exits 1 and creates no summary. |
| GHQ-PS-008 | PowerShell | P1 | Reject evidence from the previous Git checkout. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The verifier observes the child checkout HEAD and exits 1 for the stale bundle. |
| GHQ-PS-009 | PowerShell | P0 | Bind v2 receipts to the exact case plan. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | The original manifest passes and a whitespace change makes the old receipts fail verification. |
| GHQ-PS-010 | PowerShell | P1 | Verify legacy v1 receipts after the upgrade. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | Matching legacy receipts pass and the verdict identifies receipt version 1. |
| GHQ-PS-011 | PowerShell | P0 | Require a clean checkout for receipt verification. `pwsh -File test-vault/powershell/verify-receipts.tests.ps1` | A valid bundle passes in the clean fixture. A tracked catalog edit then causes verification to fail. |
