# Graphify HQ test language plan

This plan maps all 14 language tracks in the [pinned Lydite v0.0.4 inventory](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/87d25d80d3154d295052412b64b29a0f0f152c27/languages). The verified Graphify HQ baseline is [9dea866](https://github.com/vixttha/Graphify-HQ/commit/9dea866272f45717c4fbe01934eca21c3dcbeb8a). Its [case catalog](cases.md) has 77 checks across six languages, confirmed by the [public Ubuntu and Windows run](https://github.com/vixttha/Graphify-HQ/actions/runs/44512932507).

The 40 cases below are proposed. Register a proposed ID in the executable catalog once the named assertion runs through a real entry point and produces a verifiable result. The active runner reconciles named results with the catalog. An additional language needs a runner result the reconciler can recognize when that language is adopted.

## Active languages

### Python · 27 verified cases

Python owns graph production, Git-source identity, provenance, publication recovery, and verification of the test evidence itself. Run unit and integration cases through unittest.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-PY-028 · Live public PR provenance | Use a pinned, merged public PR with independently recorded base, head, and merge commit IDs. Exercise the real read-only GitHub verification path. | The report identifies the correct repository and PR, reports the source pin and merge commit separately, and recognizes their actual membership. Remote review totals are checked only for a fixture whose expected values are pinned. |
| GHQ-PY-029 · Rebuild in independent checkouts | Build the same source pin from two clean checkout paths with different absolute locations and locales. Pin dependencies and build settings. | Canonical graph and receipt bytes match across both contexts and neither contains a checkout-specific absolute path. |
| GHQ-PY-030 · Preserve source bytes and line identity | Commit UTF-8 source fixtures with LF and CRLF line endings. Reference known anchors in both. | The locations are the expected one-based lines. Each recorded source digest matches its own committed Git blob, including line endings and Unicode bytes. |
| GHQ-PY-031 · Interrupt before publication | Hold a fixture build at MCP verification and terminate the builder before publication starts. Invoke the ordinary build again after termination. | The previous verified pair remains byte-identical. The next successful build produces a valid pair from the requested source. |

### Bash · 6 verified cases

Bash owns exact pin checkout, dependency installation, and propagation of native failures through workflow steps.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-SH-007 · Verify a real public workflow dispatch | Run the pinned Graphify workflow in a public test fixture with a known event, source commit, and a newer branch tip. | The job lands on standard public hosted compute. The reported checkout, fixture source, and workflow pins match independently recorded values. |
| GHQ-SH-008 · Verify private dispatch with an existing runner | Exercise the private workflow in a dedicated fixture with its intended self-hosted runner. Compare a pull-request event with an opted-in push to the template branch. | The untrusted event never starts a job on the private runner. The trusted event uses the intended runner and produces the allowed receipt without placing private graph payloads in public logs. |
| GHQ-SH-009 · Refuse a changed locked wheel | Feed the real install step a local wheelhouse. Keep the lockfile and replace one wheel with a different byte sequence. | The trusted wheel installs. The changed wheel fails hash verification and the build step is never reached. |
| GHQ-SH-010 · Keep a failing test visible through a log pipeline | Run the actual Vault logging command with a named fixture test that exits nonzero while the log writer completes. | The log records the named error, the workflow step exits nonzero, and receipt publication never runs for that suite. |

### JavaScript · 12 verified cases

Node independently reads the fresh export and its receipt at the wire-format boundary. Use node:test and mutate copies of the Python-generated handoff.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-JS-013 · Reject ambiguous JSON fields | Give the verifier a raw receipt containing two source or digest fields with different values. Keep the graph bytes valid. | The receipt is rejected as ambiguous before any claim of verification is produced. |
| GHQ-JS-014 · Require valid UTF-8 evidence bytes | Write invalid UTF-8 inside a graph label, keep the surrounding JSON parseable after replacement decoding, and recompute the graph digest in the fixture receipt. | The raw encoding error fails verification even though the forged digest matches the bytes. A valid non-ASCII label survives unchanged. |
| GHQ-JS-015 · Bind evidence to its source root | Change only the source-root ID and its incident links, leaving the declared source pin, sizes, and recalculated digest otherwise consistent. | A source root for the wrong Git commit fails even when graph and receipt metadata still agree. |
| GHQ-JS-016 · Reconcile the source inventory | Remove a required source digest or change the source inventory independently of its file nodes. Keep edge counts and the graph digest valid. | The verifier identifies the missing digest or inconsistent inventory. Linked-only and inventoried source paths follow their documented rules. |

### TypeScript · 10 verified cases

TypeScript owns the typed consumer boundary and source-navigation results. Compile-time cases must be included by tsc. Use node:test for runtime lookup behavior.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-TS-011 · Parse external graph data at a typed boundary | Send an unknown payload and then a verified graph fixture through the consumer's graph decoder. Try compiling a call that reads the unknown payload directly. | The unverified payload cannot reach the typed lookup API. A verified fixture narrows to the lookup input type and produces a citation. |
| GHQ-TS-012 · Require exhaustive handling of citation states | Build a consumer switch that handles every lookup result. In the negative compile fixture omit one status from the switch. | tsc accepts the exhaustive handler and rejects the omitted state through a never assertion. |
| GHQ-TS-013 · Reject conflicting citation metadata | Provide an implementation edge with a different source location from its target node. Keep both locations individually valid. | Lookup returns the invalid-citation state. A matched edge and node resolve to the expected repository file and line. |
| GHQ-TS-014 · Preserve legitimate Unicode and spaces | Resolve a valid implementation path such as src/Évidence notes.ts in a graph fixture. | The returned repository path preserves the exact characters and spacing and keeps the one-based line. The canonical-path guard cannot discard this valid result. |

### Go · 11 verified cases

Go owns independent live MCP client behavior using the pinned Graphify server over stdio.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-GO-012 · Bound a disconnected MCP request | Start the pinned server, wait for the MCP handshake, then terminate it and confirm the child exit. Issue a bounded request on the closed session. | The client returns a connection error under its deadline, closes the session, and a new server process answers the same valid request. |
| GHQ-GO-013 · Disambiguate repeated labels | Build a graph with two matching source labels and distinct node IDs and paths. Query the repeated label, then each exact ID. | The bare label returns an ambiguity diagnostic containing both paths. Each exact ID resolves to its own expected path and line. |
| GHQ-GO-014 · Keep simultaneous sessions separate | Start two real Graphify server processes backed by different fixture graphs. Ask each for a shared feature ID whose implementation belongs to a different path. | Both processes respond correctly without returning the other process's source SHA, counts, or citation. |
| GHQ-GO-015 · Surface structured protocol errors | Use a valid MCP session to request an unsupported tool and then run a valid query on the same connection. | The unsupported request produces the documented error shape. A later valid request succeeds and returns only its own response. |

### PowerShell · 11 verified cases

PowerShell owns native Windows invocation, Git checkout boundaries, and receipt verification on Windows.

| Proposed case | Setup | Passing evidence |
| --- | --- | --- |
| GHQ-PS-012 · Reject receipts from a different run or attempt | Use a complete receipt set with the correct case, checkout, and evidence hash. Alter only the run ID, then only the attempt. | Each mismatch independently exits nonzero and gives the correct diagnostic. |
| GHQ-PS-013 · Invoke from a Unicode checkout path | Use a Windows fixture directory with non-ASCII characters, spaces, and brackets. Pass the checkout, catalog, and receipt paths as native arguments. | The verifier reads the correct paths and emits a valid receipt without character replacement. |
| GHQ-PS-014 · Reject an untracked verifier or catalog | Use a clean checkout with a valid tracked verifier and catalog, then pass an otherwise identical untracked copy for each required tracked input. | The tracked bundle passes. The new path is rejected even though its bytes and the remaining options match. |
| GHQ-PS-015 · Verify a real cross-OS artifact handoff | Produce a fixture graph and a v2 receipt on Ubuntu. Verify the same artifact on Windows using the exact run and attempt. Then mutate newline bytes in a copy. | The original artifact passes without newline conversion. The altered file fails even when its decoded text appears equivalent. |

## Languages available for an adopter

These cases become executable when a project exposes the named entry point. Each proposed test attaches to an adopter behavior with its own failure mode.

| Language and entry point | Proposed case | Setup | Passing evidence |
| --- | --- | --- | --- |
| **C++** · Compiler-aware evidence emitter | GHQ-CPP-001 · Distinguish overloads | Compile a C++ fixture with two overloads and adapt the actual emitter to Graphify. | Each signature maps to its own exact declaration or definition line, including where the identifiers are identical. |
| **C++** · Compiler-aware evidence emitter | GHQ-CPP-002 · Respect build configuration | Build two configurations with different conditional source branches and collect evidence per compile configuration. | Each configuration points to its active definition and makes no claim that the inactive definition participated in that build. |
| **C#** · .NET receipt or graph consumer | GHQ-CS-001 · Keep receipt schemas distinct | Deserialize the actual Graphify graph receipt and the actual Lydite test receipt in the same .NET client. | Each reader accepts its own supported schema and rejects the other document with a clear type or schema error. |
| **C#** · .NET receipt or graph consumer | GHQ-CS-002 · Validate case-plan binding | Use real Lydite v2 output and alter only the manifest bytes for a replay. | The .NET verification path accepts the original bundle and rejects the replay under the new plan digest. |
| **F#** · Cross-snapshot analysis | GHQ-FS-001 · Keep file moves distinct from changed evidence | Compare two verified snapshots where a cited file moves and an unrelated feature changes independently. | The comparison reports the known move and the independent feature change against their correct revisions. |
| **F#** · Cross-snapshot analysis | GHQ-FS-002 · Prevent duplicate findings on replay | Feed the same verified snapshot to the adopter's projection twice, then feed a new revision. | Replaying the snapshot adds no duplicate findings. The new revision adds exactly its new results. |
| **Haskell** · Release dependency analysis | GHQ-HS-001 · Order release prerequisites | Supply verified release-derived dependency edges with a disconnected component and a known prerequisite constraint. | All releases appear once and every prerequisite precedes the dependent. |
| **Haskell** · Release dependency analysis | GHQ-HS-002 · Report release dependency cycles | Add a fixture cycle to dependency edges. Preserve ordinary non-dependency links in the graph. | The analyzer identifies the dependency cycle and withholds an invalid execution order. Ordinary graph cycles remain usable evidence. |
| **Java** · JVM MCP client | GHQ-JAVA-001 · Read Unicode source evidence | Query a real stdio MCP fixture for a feature whose citation contains non-ASCII text and a known line. | The JVM client returns the exact text and path from the pinned source and the expected line. |
| **Java** · JVM MCP client | GHQ-JAVA-002 · Keep server logging off the response path | Send two MCP requests to a server that emits documented diagnostic output on stderr. | stderr stays separate from the JSON-RPC stream. Both responses retain their expected request identities and payloads. |
| **Lua** · Editor and source jump integration | GHQ-LUA-001 · Navigate duplicate basenames correctly | Use a real editor adapter and two different folders with identically named files. Supply the verified repo-relative citation. | The active buffer is the full intended repository path and the cursor lands on the expected one-based line. |
| **Lua** · Editor and source jump integration | GHQ-LUA-002 · Preserve buffers on stale evidence | Open an editor buffer with unsaved text. Attempt a jump using a graph for a different source commit. | The stale-source result is surfaced. The open buffer and unsaved content are preserved. |
| **Ruby** · Rake task or adopter CI adapter | GHQ-RB-001 · Fail an adopter task on mismatched evidence | Run the real task with a known-good bundle and then a valid receipt paired with different graph bytes. | The first task succeeds. The second exits nonzero before issuing an adopter pass report or replacing its earlier output. |
| **Ruby** · Rake task or adopter CI adapter | GHQ-RB-002 · Preserve link targets in the report | Generate a report for two commits with different paths and source lines for the same feature. | The report anchors each citation to its own commit and path, including spaces and punctuation after URL encoding. |
| **Rust** · Streaming archive reader | GHQ-RS-001 · Reject a truncated archive atomically | Give the real importer a complete verified archive and a copy truncated before the final validated entry. | A complete import is available to the client. Truncation reports a typed failure and leaves the previous valid archive usable. |
| **Rust** · Streaming archive reader | GHQ-RS-002 · Keep cancellation from publishing partial data | Pause a stream at a controlled boundary and cancel the import. Retry with the complete stream. | Cancellation publishes zero partial results. The retry imports the whole valid archive and yields the expected source and digest. |

## Build order

1. Start with evidence integrity and caller behavior in the active suites. GHQ-JS-013 through GHQ-JS-016 protect the wire format. GHQ-TS-011 through GHQ-TS-013 protect the typed consumer. GHQ-GO-012 and GHQ-PS-012 cover runtime failure and receipt replay.
2. Run the remaining active fixture cases, then verify live provenance and routing with injected evidence isolated from fixture results. Use standard public GitHub-hosted Ubuntu and Windows jobs for public fixtures. GHQ-SH-008 needs an existing private self-hosted runner and a dedicated private fixture.
3. For each adopted language, use a real adopter entry point and add a passing control plus the described boundary. Capture case ID, exact checkout SHA, dependencies, runtime, and runner verdict. When two suites share observation bytes, record matching Lydite v2 case-plan and evidence digests.
