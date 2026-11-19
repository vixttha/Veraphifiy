# Graphify HQ language audit

The audited checkout is [3651503](https://github.com/vixttha/Graphify-HQ/commit/3651503ad22a9db480dc8eb31c17599803f35ae8). The [public workflow](https://github.com/vixttha/Graphify-HQ/actions/runs/44516091602) completed successfully. Its logs account for 66 named results on Ubuntu and 11 on Windows. The Ubuntu handoff recorded identical graph SHA-256 values from Python and Node and a passing Lydite v2 verdict for the exact audited checkout and run.

The audit compared the executable case catalog, test sources, runner reconciliation, producer and consumer behavior, and Lydite inventory. The local inventory reports one generic sample in each of 14 language folders. The installed catalog validator, receipt verifier, and Git source helper are byte-identical to the [pinned Lydite starter](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault). The [pinned Lydite run](https://github.com/vixttha/Lydite-Test-Vault-Template/actions/runs/44506598515) is evidence for the upstream tool revision.

## Reproduced gaps

Local probes used temporary copies of the known-good Python handoff and the pinned Node runtime. Mutated graph fixtures received matching graph digests and updated counts where relevant, so they exercised the targeted checks independently of the existing digest and count checks. The unchanged controls passed.

| Checkpoint | Observation on the audited code | Proposed coverage |
| --- | --- | --- |
| JavaScript decoding | A duplicate top-level source field passed when the last value matched. An invalid UTF-8 byte inside a label was decoded and also passed. | GHQ-JS-013, GHQ-JS-014 |
| JavaScript source identity | Changing the source-root node and its incident links passed while the top-level source SHA remained correct. Removing an inventory digest or replacing it with an invalid-length value also passed. | GHQ-JS-015, GHQ-JS-016, GHQ-JS-019 |
| JavaScript topology | A repeated contains_feature edge passed after counts and digests were refreshed. The same verifier accepted an undirected flag on the directed fixture. | GHQ-JS-017, GHQ-JS-018 |
| TypeScript navigation | A valid-looking edge location that disagreed with its target still yielded a citation. A runtime array containing L3 reached the numeric conversion and yielded line 0. | GHQ-TS-013, GHQ-TS-015 |
| TypeScript compiler evidence | In an isolated compiler fixture, tsc succeeded when the expected-error annotation suppressed a deliberately unrelated error. The run reconciler counted the original named case from the annotation and file listing. | GHQ-PY-033 |
| Lydite handoff scope | The recorder and Lydite v2 verifier returned PASS after the graph's companion receipt was replaced in a disposable copy. Both observers had recorded the original graph digest. The present contract therefore verifies the shared graph bytes. | GHQ-PY-032 proposes binding the complete observed bundle. |
| BART draft recovery | The exact pinned candidate removed both fixture evidence files when an empty pending journal directory was present. For the repeat probe, the pair's raw graph digest and independent source pin agreed before recovery, and the probe ran against temporary copies. The existing CI cases exercise interruptions with a healthy journal. | GHQ-PY-035 |
| JavaScript citation lookup | The normal path resolved to line 3. Giving the edge and its target the same noncanonical path also returned a citation. The current lookup checks agreement on both ends. | GHQ-JS-025 |
| JavaScript numeric evidence | A raw JSON exponent outside the finite range reached graph inspection as Infinity. The fixture's recomputed digest passed. RFC 8259 discusses interoperability limits for such inputs. The proposed finite-value rule applies to Graphify's graph contract. | GHQ-JS-028 |
| Standalone named result reconciliation | The reconciler accepted a named JavaScript TAP pass followed by a failure or skip for the same ID. It also accepted a Go JSON pass followed by a fail for the same test. The public workflow separately gates test command exit through Bash pipefail. This probe isolated the parser boundary. | GHQ-PY-040 |

The proposed cases describe the target behavior. The reproduced cases are queued for implementation and verification.

## Coverage by language

| Language | Executable cases | Baseline actually exercised | Proposed |
| --- | ---: | --- | ---: |
| Python | 27 | Real build and MCP handoff, reproducibility, Git blobs, released builder behavior, simulated provenance, pinned draft journaling and test-run gate. | 16 |
| Bash | 6 | Pinned workflow step bodies, staged Git fetch and extraction in fixtures, quoting, and simulated dependency failures. Live Graphify workflow routing remains open. | 16 |
| JavaScript | 12 | Fresh graph and companion receipt inspection, exact graph digest, identity, counts, endpoint integrity and source anchors. | 16 |
| TypeScript | 10 | Three compiler checks and seven runtime citation checks at the current reference adapter. The type gate accounts for included expect-error annotations. | 16 |
| Go | 11 | Real MCP stdio client against pinned Graphify with discovery, lookup, directed routes, concurrency and stale warnings. | 16 |
| PowerShell | 11 | Windows CLI subprocess results, environment handling, v1 and v2 Lydite receipts, exact graph bytes and Git checkout checks. | 16 |
| C++ | 0 | Pinned Lydite C++20 sample. Graphify work requires a compiler-backed adopter emitter. | 10 |
| C# | 0 | Pinned Lydite .NET sample. Graphify work requires an actual receipt or graph consumer. | 10 |
| F# | 0 | Pinned Lydite F# Interactive sample. Graphify work requires a cross-snapshot analyzer. | 10 |
| Haskell | 0 | Pinned Lydite runghc sample. Graphify work requires a release dependency analyzer. | 10 |
| Java | 0 | Pinned Lydite Java source launcher sample. Graphify work requires a JVM MCP client. | 10 |
| Lua | 0 | Pinned Lydite Lua sample. Graphify work requires an editor adapter. | 10 |
| Ruby | 0 | Pinned Lydite Ruby sample. Graphify work requires an adopter task with a machine-readable verdict. | 10 |
| Rust | 0 | Pinned Lydite rustc harness sample. Graphify work requires a streaming archive importer. | 10 |
| **Total** | **77** | **Six active Graphify tracks.** | **176** |

The pinned released builder, candidate code, and staged workflow are distinct audit targets. Fresh builds use the [BART v0.0.8 release fixture](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1). The evidence-loss probe concerns the [BART draft candidate](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/d227b202c7cce1b86a1ee06596d709f3dfee1039/candidate/evidence_map.py). Bash uses bodies from the [pinned OBJ/MTL workflow](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/2680e03a3d1a7216666554c5baca43b2ec93b944/.github/workflows/obj-mtl-evidence.yml). Live private dispatch and live GitHub PR provenance remain unverified. The eight adopter tracks remain conditional on a real entry point and native named outcome reconciliation.

See the [expanded language plan](LANGUAGE-PLAN.md) for fixtures and expected outcomes.

## Verified sources by language

The pinned inventory and public run establish enabled coverage. These primary references explain the mechanics used in the proposed acceptance conditions. The eight adopter tracks remain conditional on integrating their actual entry points.

| Language | Basis for the proposed tests | Primary sources |
| --- | --- | --- |
| Python | The pinned journal and receipt code establish publication and verification order. Python supplies a JSON hook that can inspect fields before collapsing repeated names. Named results still come from the actual runner logs. | [Candidate recovery](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/d227b202c7cce1b86a1ee06596d709f3dfee1039/candidate/evidence_map.py) · [Pinned receipt verifier](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/test-vault/verify_receipts.py) · [Python JSON decoder](https://docs.python.org/3.12/library/json.html) |
| Bash | Explicit Bash jobs run with pipefail. GitHub reruns preserve the original event SHA and some jobs can retain outputs from a previous attempt, which makes an attempt-aware handoff a separate test. | [Workflow shell](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) · [Rerun behavior](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs) · [Run and attempt variables](https://docs.github.com/en/actions/reference/workflows-and-actions/variables) |
| JavaScript | RFC 8259 describes UTF-8, interoperability limits for numbers, and recommends unique object names. The Graphify strict rejection rules are proposed application contracts. The pinned inspector establishes the existing behavior. | [JSON specification](https://www.rfc-editor.org/rfc/rfc8259.html) · [Pinned inspect-evidence](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/test-vault/javascript/inspect-evidence.mjs) |
| TypeScript | Discriminated narrowing and exhaustive handling can constrain consumers after runtime decoding. The pinned typed adapter and compiler gate establish the current entry points. | [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/2/narrowing.html) · [Typed citation adapter](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/test-vault/typescript/citations.ts) · [Result reconciler](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/test-vault/verify_case_run.py) |
| Go | The Go context package defines cancellation and deadlines. The stdio transport specifies line-delimited JSON-RPC and permits diagnostic output on stderr. Use the pinned session-init path as the version boundary. | [Go context](https://pkg.go.dev/context) · [MCP stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) · [Pinned Go suite](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/test-vault/go/mcp_test.go) |
| PowerShell | Native exit status and the Lydite receipt schema are independent checks. The Windows workflow reads the native result before reconciling the logs. | [PowerShell automatic variables](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_automatic_variables?view=powershell-7.6) · [Pinned Windows workflow](https://github.com/vixttha/Graphify-HQ/blob/3651503ad22a9db480dc8eb31c17599803f35ae8/.github/workflows/test-vault.yml) · [Lydite receipt verifier](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/verify_receipts.py) |
| C++ | The compilation database defines working directories, command forms, and multiple compile commands for one source file. CMake documents generator support and Unity-build limitations. | [Clang database specification](https://clang.llvm.org/docs/JSONCompilationDatabase.html) · [CMake compilation database](https://cmake.org/cmake/help/latest/variable/CMAKE_EXPORT_COMPILE_COMMANDS.html) |
| C# | System.Text.Json supports required-field enforcement and .NET 8 supports rejecting unmapped fields. The adopter still chooses and tests its own JSON profile. | [.NET required fields](https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/required-properties) · [.NET unmapped fields](https://learn.microsoft.com/en-us/dotnet/standard/serialization/system-text-json/missing-members) |
| F# | Discriminated unions give a typed representation for unavailable or ambiguous observations alongside known changes. Exhaustiveness and replay are acceptance conditions for the adopter. | [F# discriminated unions](https://learn.microsoft.com/en-us/dotnet/fsharp/language-reference/discriminated-unions) |
| Haskell | Data.Graph exposes keyed graph construction and strongly connected components. Stable tie ordering and duplicate-key rejection belong to the schedule adapter. | [Pinned containers 0.7 graph implementation](https://github.com/haskell/containers/blob/v0.7/containers/src/Data/Graph.hs) |
| Java | ProcessBuilder exposes per-child environment, working directory and stream redirection. The Process API documents limited native buffers. A JVM consumer must preserve MCP framing while draining them. | [Java 21 ProcessBuilder](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessBuilder.html) · [Java 21 Process](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/Process.html) · [MCP stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports) |
| Lua | Neovim's API provides buffer validity and window-specific cursor functions. Fixture expectations use that editor's indexing and the adopter's navigation policy. | [Neovim v0.11.5 API reference](https://github.com/neovim/neovim/blob/v0.11.5/runtime/doc/api.txt) |
| Ruby | Open3 exposes distinct output streams, binary output mode, and child process status. The adopter's task decides how to record and enforce those results. | [Ruby 3.4 Open3](https://docs.ruby-lang.org/en/3.4/Open3.html) |
| Rust | The standard I/O traits distinguish interrupted reads, short writes, and error results. A streaming importer must separately enforce its selected frame and publication contract. | [Rust Read](https://doc.rust-lang.org/std/io/trait.Read.html) · [Rust Write](https://doc.rust-lang.org/std/io/trait.Write.html) |

The first implementation tranche should cover the candidate journal and the reproduced verification gaps. Later cases include workflow observations and behaviors whose contract must be agreed in the adopter first.
