# Veraphify two-version fixture coverage

Status is **planned**. The matrix expands the [Veraphify product test continuation](LANGUAGE-PLAN.md#veraphify-product-test-continuation) in the original Lydite Vault. It assigns one primary language per assertion and uses the other lanes for independent oracles or distinct client behavior.

The v0.0.9 product code is on [merged main at `ed56500`](https://github.com/vixttha/Veraphify/commit/ed5650085e33cf142a37de695757a4df999a7cf3). Its Git tree matches the tested candidate exactly. The current push workflow filters do not include `main`, so the public product run cited here belongs to the candidate SHA. The exact tested product baseline is [the v0.0.9 integration head `fdef486`](https://github.com/vixttha/Veraphify/commit/fdef4867c87148bdf0782e16de372b584d51588e). Its [catalog](https://github.com/vixttha/Veraphify/blob/fdef4867c87148bdf0782e16de372b584d51588e/test-vault/cases.md) has 211 executable checks, including `GHQ-PY-109` for dot-prefixed repositories. [Public push run 44653386073](https://github.com/vixttha/Veraphify/actions/runs/44653386073/attempts/1) passed Graphify MCP and both archive replay jobs. The [original Vault catalog](cases.md) has 200 cases. These figures are baselines. The numbered rows below describe planned assertions and explicit regression controls. They can extend existing IDs where called out.

## Shared fixture and evidence

Start from the [pinned adopter walkthrough](https://github.com/vixttha/Veraphify/blob/fdef4867c87148bdf0782e16de372b584d51588e/docs/adopter-walkthrough.md) and the [existing independent Node replay](https://github.com/vixttha/Veraphify/blob/fdef4867c87148bdf0782e16de372b584d51588e/test-vault/javascript/verify-archive-replay.mjs). Reuse the synthetic `example/graphify-fixture` repository, pinned Graphify producer and existing archive artifact layout. `feature:export` returns `src/feature.py:3` at `v1.0.0` and `src/feature.py:4` at `v1.1.0`. Preserve distinct full source SHAs, both original archive bytes, and their SHA-256 values before replay. Compare archive bytes with independent reads of the pinned Git blobs. Any mutated copy gets its own disposable archive and explicit control. When a test is intended to reach an inner validator, recompute that copy's outer digest and keep the original trusted digest as a separate check.

The existing walkthrough tests pinned verify and lookup on Linux. Existing artifact replays test pinned lookup on Ubuntu and Windows. `GHQ-PY-100` already covers serial conflicting imports, identical retries and version selection. `GHQ-PY-101` proves physical Git lines, `GHQ-PY-103` covers aliases, `GHQ-PY-105` covers checkout context, `GHQ-PY-106` checks the source-size limit, `GHQ-PY-107` checks repeated flags, and `GHQ-PY-109` covers dot-prefixed names. Extend those cases at their existing boundaries. Assign a new executable ID only when it measures a distinct outcome.

Run implemented cases against the pinned CLI on standard public GitHub-hosted Ubuntu and Windows. For each implemented case, capture the actual operation, native outcome, control, candidate and Vault SHAs, workflow revision, event/ref, run and attempt, job, artifact ID and ZIP SHA-256 when relevant, and expected per-entry pins. Keep synthetic Git bytes and archives within the fixture's declared retention and size policy. For release acceptance, use the [existing qualifying-run rule](https://github.com/vixttha/Veraphify/issues/21#v009-release-evidence-rule).

## Implementation order

1. Extend downloaded-artifact replay in JavaScript and add the independent Git-byte checks in Python. Treat pre-existing walkthrough checks as controls. Require source-only swaps, digest-only swaps, and valid pairs on both versions.
2. Extend the Bash and PowerShell paths through real shells, then connect the actual CLI stdout decoder to the existing TypeScript navigation tests.
3. Add Go races with verified overlap, independently observed winner identity, and before/after entry verification. Keep adjudication independent of the order in which goroutines report results.
4. Add adopter cases as the prerequisites below become real. C# file-sharing checks and the F# model can use the existing CLI directly once their harnesses are available. Use the named integration for adopter-facing work.

## Coverage map

| Language | Planned assertions | Readiness |
| --- | ---: | --- |
| [JavaScript](#javascript) | 15 | Existing CLI or runner boundary |
| [Python](#python) | 16 | Ready to design |
| [Bash](#bash) | 12 | Ready to design |
| [PowerShell](#powershell) | 12 | Ready to design |
| [TypeScript](#typescript) | 15 | Ready to design |
| [Go](#go) | 14 | Ready to design |
| [C++](#c-compiler-evidence) | 12 | Dependency or contract required |
| [C#](#c-windows-file-sharing) | 9 | Dependency or contract required |
| [F#](#f-archive-state-model) | 9 | Dependency or contract required |
| [Haskell](#haskell) | 11 | Dependency or contract required |
| [Java](#java) | 10 | Dependency or contract required |
| [Lua](#lua) | 11 | Dependency or contract required |
| [Ruby](#ruby) | 11 | Dependency or contract required |
| [Rust](#rust) | 11 | Dependency or contract required |

## JavaScript

Pin verification on the downloaded archive, with the real Node CLI. `GHQ-PY-100`, `GHQ-PY-103`, `GHQ-PY-107`, `GHQ-PY-109`, and `verify-archive-replay.mjs` cover serial archive behavior and the original lookup replay.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-JS-01 | Verified replay | Run pinned verify and lookup for both versions from each downloaded handoff. | The shared fields agree, verify emits no citation fields, and lookup returns line 3 or 4 for the selected source. |
| VFY-JS-02 | Swapped source pins | Swap only the source pin in both directions, keeping each version’s correct digest. | Both commands fail with the source-commit diagnostic and emit no success JSON. |
| VFY-JS-03 | Swapped archive pins | Swap only the archive SHA-256 in both directions, keeping each version’s correct source. | Both commands fail with the archive-digest diagnostic and emit no success JSON. |
| VFY-JS-04 | Both pins wrong | Swap both pins, then correct only the digest. | With both wrong the archive-digest check fails first. With only the source wrong, the source diagnostic is exposed. |
| VFY-JS-05 | Pin options | Exercise source-only, digest-only, both, and unpinned verify and lookup. Include a malformed explicit pin. | Supported calls return the same selected entry. An explicitly malformed pin yields its own diagnostic without falling back to unpinned verification. |
| VFY-JS-06 | Portability without input checkout | Replay a copy of the archive without the original fixture checkout, evidence directory, or Git on the child PATH. | Each pin pair and citation still matches and the archive is untouched. |
| VFY-JS-07 | Offline selector isolation | Replay a project alias and an otherwise identical request for another project or an unarchived version. | The alias preserves receipt spelling. Unarchived selectors fail without falling back to an existing entry. Reuse the serial controls when expanding Windows replay. |
| VFY-JS-08 | Feature present in one version | Make a documented derivative that introduces a second feature only in v1.1.0. | Lookup discovers it only in v1.1.0 with the expected source citation. The original feature remains available in both. |
| VFY-JS-09 | Exact feature key | Compare a known feature ID with a case change and a non-feature graph node ID. | The real feature resolves. The other inputs return the feature-selection diagnostic with no citations. |
| VFY-JS-10 | Empty versus missing | Build a valid producer fixture with a known feature backed only by documentation/test links. | A known feature returns an empty implementation list under the current CLI contract. An absent feature fails. The typed consumer handles the difference. |
| VFY-JS-11 | Archive parser stages | In separate disposable copies change archive format, receipt digest, or embedded Base64. Keep a correct outer pin per copy to reach the intended validation. | Each failure is attributed to its intended layer and the original two entries still verify. |
| VFY-JS-12 | Archive envelope identity | Move a genuine entry under a different valid project/version selector in a disposable archive and supply its recomputed outer digest so the CLI reaches the identity check. | The CLI rejects the embedded project/version mismatch and returns no success JSON. |
| VFY-JS-13 | Help and version contract | Run the real top-level help and version commands from a clean working directory. | Help lists import, verify, lookup and their pin options. Version prints the documented CLI version once. Both exit zero. |
| VFY-JS-14 | Graph and receipt pair mismatch | Supply the valid graph bytes from one version with the valid receipt from the other to import into a disposable archive. | The command reports source or graph mismatch and publishes no new entry. Reuniting each graph and receipt restores both successful imports. |
| VFY-JS-15 | Archive reads preserve exact bytes | Repeat verified and failed reads in alternating order from two independent processes and compare raw bytes before and after. | Neither verify nor lookup rewrites receipt, graph or archive bytes, and the original pin pairs keep working. |

## Python

Independent byte and Git-object verification. Extend `GHQ-PY-032`, `GHQ-PY-053`, and `GHQ-PY-100`–`109` where a row deepens an existing oracle. Use Python hashlib, strict Base64 decoding, and Git object reads independent of the Node verifier.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-PY-01 | Archive and embedded digests | Hash each archive file and its decoded graph and receipt separately. Compare against the recorded import outputs and original producer artifacts. | All three byte-level digests match their own pins for both versions. |
| VFY-PY-02 | Complete source inventory | Compare each decoded entry blob against git cat-file using the selected commit, and compare all path/digest claims against the receipt. | There is one match per expected path, including linked-only paths, and no surplus or missing path. |
| VFY-PY-03 | HEAD independence | Advance the checkout, then change an inventoried file in the worktree without committing. Replay original pins and repeat independent reads. | Original blobs and citations still match historical objects, and the test demonstrates the new checkout bytes really differ. |
| VFY-PY-04 | Same bytes across versions | Select one unchanged file and one changed file from the two commits. | The unchanged blob digest agrees across versions, the changed file differs, and the archive digests identify the two entries separately. |
| VFY-PY-05 | Exact source budget | Extend GHQ-PY-106 using otherwise valid producer inputs at 8 MiB minus one, exactly 8 MiB, and plus one across distinct paths. | The first two import and verify. The over-limit import publishes no final entry. |
| VFY-PY-06 | Inventory counting | Use a file referenced by more than one evidence relation and a file cited only by a non-implementation relation. | The first counts once and the linked-only file counts toward the source budget. |
| VFY-PY-07 | Git object type | Reuse the full valid source selector, then supply a same-length object ID that denotes a tree or blob. | Only the commit selects source. Noncommit inputs yield the Git-object diagnostic and leave the archive untouched. |
| VFY-PY-08 | Git file mode coverage | Use regular 100644 and 100755 files, and a nonregular committed entry where fixture support permits. | Regular files match pinned bytes. The nonregular entry yields the ordinary-committed-file diagnostic. |
| VFY-PY-09 | Truncated evidence layers | On isolated copies truncate archive JSON, embedded receipt, or an embedded source blob one at a time. | Each independent oracle detects its layer and the CLI reports failure without modifying any entry. |
| VFY-PY-10 | Reproducible import bytes | Import identical pinned inputs into two clean archive directories using differently located checkouts. | Binary archive contents and reported archive digests match. Earlier checkout paths never become archived identity. |
| VFY-PY-11 | Archived blob shape | Exercise missing entries, duplicate path tuples, and a mismatched path/digest pair independently. | The raw archive audit names the invariant each fixture breaks. The good archive passes both the audit and CLI verify. |
| VFY-PY-12 | Handoff and artifact identity | Compare the downloaded ZIP digest with GitHub metadata before decoding archive entries, then verify the saved run/attempt and inner archive digests independently. | Missing or mismatched metadata fails its own assertion. ZIP, archive, receipt and graph digests remain distinct observations. |
| VFY-PY-13 | Same-sized changes | Alter one committed fixture line in the newer version while keeping byte count unchanged. | Byte-count comparisons alone agree. The independent SHA-256 and pinned citation bytes still distinguish the versions. |
| VFY-PY-14 | Source entry budget precedence | Model the documented graph, receipt, source and envelope caps independently before constructing boundary tests. | Each proposed equality and one-over case identifies the first reachable cap. Combinations blocked by a tighter cap are recorded as unreachable through valid input. |
| VFY-PY-15 | Artifact proof stays independently attributable | Compare exported receipt context, downloaded ZIP metadata, expected archive map and registered native results in one audit. | A source digest, ZIP digest, planned assertion or skipped native result is never substituted for an exact-run product verdict. |
| VFY-PY-16 | Verifier requires retained evidence | Audit a valid exact-run record against a missing or expired artifact and compare with a retained, independently copied ZIP. | Verification records whether the bytes were available and independently checked. GitHub metadata can still identify an expired artifact without standing in for a byte check. |

## Bash

Linux subprocess, walkthrough and pipeline semantics. Keep `GHQ-SH-001`, `GHQ-SH-002`, `GHQ-SH-005`, `GHQ-SH-029`, and the candidate's documented walkthrough as controls. Test actual Bash steps.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-SH-01 | README clean run | Extract the real fenced walkthrough as CI does and run it from a differently named clean Linux checkout. | It completes with both expected lines and preserves the first archive byte-for-byte. |
| VFY-SH-02 | Literal locations | Run with fixture, archive and working directories containing spaces and Unicode. | Commands select the intended paths and write reports only in the fixture output directories. |
| VFY-SH-03 | Missing-version streams | Invoke the documented missing version through Bash with separate stdout/stderr capture. | Native status is nonzero, the diagnostic appears on stderr, and stdout cannot be parsed as a success object. |
| VFY-SH-04 | Pipeline status | Route a deliberate CLI failure through the real Bash pipeline and its log sink. Then run a successful control through the same pipeline. | The failed CLI step remains failed even when the sink succeeds. The valid output is retained and the subsequent step can consume it. |
| VFY-SH-05 | Upstream setup failure | Make the producer prerequisite fail using its supported control input in a disposable walkthrough run. | The nonzero setup result stops the downstream import, verify and lookup steps, and no success handoff is created. |
| VFY-SH-06 | Argument fidelity | Call the CLI with a list of quoted arguments and compare conventional split and equals-style options supported by Node. | Both supported forms select the same existing archive. An omitted value yields an option diagnostic. |
| VFY-SH-07 | Redirect and working directory | Invoke from a sibling directory with separate log destinations and paths resolved by the walkthrough. | The invocation does not rely on current working directory for CLI identity, and log capture does not modify archive bytes. |
| VFY-SH-08 | Pinned extraction | Run the walkthrough using its pinned checkout while a second fetched ref points at changed docs or source. | The executed script and fixture retain the selected commit’s behavior and SHA. Logs state the pin that was used. |
| VFY-SH-09 | Runner failure control | Re-run with a documented invalid selection after a passing independently recorded invocation. | The expected failure remains visible, and the job contributes a named pass only for observing the intended tested failure. |
| VFY-SH-10 | Pre-existing archive directory | Run the pinned walkthrough steps against a prepared writable archive directory with unrelated fixture output present. | The selected imports are correct and existing unrelated fixture files retain their names and hashes. |
| VFY-SH-11 | Input prerequisites | Exercise missing Git and missing producer dependencies in throwaway clean shells before meaningful archive work. | The walkthrough or prerequisite step stops with an attributable failure. An already prepared archive read can still run with Node alone. |
| VFY-SH-12 | Interrupted shell cleanup | Run the walkthrough under its normal cleanup trap and introduce a controlled fixture failure after the first version is recorded. | Temporary files follow the documented cleanup policy. There is no success artifact for the unfinished run. |

## PowerShell

Windows native execution and cross-platform handoff. `GHQ-PS-001`, `GHQ-PS-002`, `GHQ-PS-015`, and `GHQ-PY-108` cover the receipt runner and Windows log reconciliation. Add CLI-level checks using the existing Windows job.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-PS-01 | Native arguments | Call node with an argument array and an archive directory containing spaces, brackets and Unicode. | Import, verify and lookup receive the exact arguments and address the intended directory. |
| VFY-PS-02 | Independent stdout and stderr | Use the actual PowerShell invocation to fail a validly formed lookup with the wrong digest. Capture LASTEXITCODE immediately. | The native result is nonzero, stderr identifies the archive hash mismatch, and no success JSON reaches stdout. |
| VFY-PS-03 | PowerShell pipeline result | Exercise the Windows runner’s real logging pattern with a failed native CLI invocation and with a passing control. | Logged output stays usable and the wrapper propagates the native failure when the downstream log command succeeds. |
| VFY-PS-04 | Hold verified entry across copy | Replay the downloaded Ubuntu archive through both native and PowerShell SHA-256 reads. | Each Windows result equals the producer entry digest and retains the expected physical source line. |
| VFY-PS-05 | Windows-native import | Import the same producer fixture from a Windows Git checkout with platform checkout conversion enabled, then compare all archived bytes to Linux. | Both runner outputs agree for the same committed bytes and version. A CRLF conversion of the evidence artifact fails independently as applicable. |
| VFY-PS-06 | Clean environment after failure | Follow a controlled failed invocation immediately with a valid one in the same PowerShell session. | The second call has a fresh native status, no stale diagnostics, and valid JSON with the intended pin. |
| VFY-PS-07 | Missing version and missing directory | Check absent archive root and present root with absent selected version. | Each observation is observable as a product failure in PowerShell and cannot be counted as a valid replay. |
| VFY-PS-08 | Windows path terms | Exercise absolute and relative paths, drive-qualified absolute paths, and literal square brackets. | Equivalent valid paths resolve the same archive, and the command produces only the expected output under the chosen fixture root. |
| VFY-PS-09 | Handoff freshness | Rerun the Windows read against an otherwise valid earlier-attempt handoff and a same-attempt control. | Context rejects the earlier attempt before treating it as proof. The current attempt opens and replays by artifact ID. |
| VFY-PS-10 | Windows import and retry parity | On a disposable Windows runner import the same request twice, then attempt the conflicting second-version input under the first label. | The retry and conflict outcomes agree with existing serial Linux controls. The already published entry keeps its exact digest. |
| VFY-PS-11 | Cross-platform Git mode fixture | Replay an archive made from a fixture containing an ordinary Git executable path that Windows does not represent as a POSIX permission. | Git object bytes and citations still agree. Host permission representation is recorded independently of Git tree mode. |
| VFY-PS-12 | Windows CRLF redirection semantics | Compare the artifact bytes to native capture output and to explicitly redirected PowerShell strings from one successful replay. | Windows character encoding and terminal newlines in console output stay independent of binary archive identity. |

## TypeScript

Runtime decoder and type-safe navigation from real CLI stdout. `GHQ-TS-001`, `GHQ-TS-003`, `GHQ-TS-015`, `GHQ-TS-017`, and `GHQ-TS-031` cover the typed graph adapter. The planned CLI output decoder has a separate runtime boundary.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-TS-01 | Valid boundary | Parse actual lookup stdout as unknown and decode the selected project, version, source, archive digest and citations. | Only the validated success shape offers navigable results for each fixture version. |
| VFY-TS-02 | Pending or stale source | Delay a real v1.0.0 reply until after the consumer switches to v1.1.0. | A valid-but-stale response cannot replace v1.1.0 navigation. |
| VFY-TS-03 | Pinned digest mismatch | Feed valid JSON with a correct version/source and a digest differing from the independently selected archive. | Runtime marks it unusable and the navigation callback is never called. |
| VFY-TS-04 | Malformed physical lines | Present zero, negative, fractional, unsafe integer and string coordinates through the same decoder. | Each is rejected without coercion, and the real one-based numeric values pass the boundary. |
| VFY-TS-05 | Missing and empty citations | Compare omitted citations, an empty array, wrong element type, and plain verify stdout against real lookup JSON. | The consumer distinguishes invalid payload, known feature without implementation, and navigation-ready output. |
| VFY-TS-06 | Path boundary | Use valid nested Git paths, Unicode and spaces alongside clearly invalid source-coordinate inputs in the decoder. | Valid path identity is preserved and an invalid path cannot reach the navigation callback. |
| VFY-TS-07 | Multiple citations | Extend the existing multiple-source fixture to emit actual CLI stdout with two locations in one file. | These remain individually selectable, with positions preserved and no file-level collapse. |
| VFY-TS-08 | Discriminated union | Compile a fixture that accesses a citation before narrowing, then compile its corrected control. | The expected compiler diagnostic appears at the exact member access and the narrowed version type-checks. |
| VFY-TS-09 | Exhaustive states | Add explicit decoded states for malformed output, stale pins and no implementation, then remove one case in a dedicated compiler fixture. | The exhaustive-switch assertion fails precisely where the new state is unhandled. |
| VFY-TS-10 | Invalid runtime result cannot leak | Supply empty output, two JSON documents or an explicit child-process failure to the consumer adapter. | Each leads to a controlled non-navigation state with the failure reason preserved. |
| VFY-TS-11 | Receipt spelling and selector identity | Decode a real case-alias lookup for a dot-prefixed repo and compare it with an unrelated project result. | The intended alias matches the selected key while preserving displayed receipt spelling. A different project cannot populate current navigation. |
| VFY-TS-12 | Compile-time readonly result | Compile a consumer fixture that attempts to mutate a validated citation or its array, then use a copied derived value in the control. | If the adapter exposes readonly results as designed, the negative compile test names the exact mutation, and the control compiles. |
| VFY-TS-13 | Opaque pin types | Define the decoder’s validated source and archive-pin types and compile a fixture crossing the two boundaries without conversion. | Correctly decoded pins pass. Accidental pin interchange produces its expected targeted diagnostic. |
| VFY-TS-14 | Per-entry readiness for multi-version rows | Decode a valid result and an unusable result side by side in one compare view. | The valid item remains usable and the invalid one cannot share another row’s selection or citations. |
| VFY-TS-15 | Schema evolution discipline | Add an irrelevant extra field to a real response, then remove an essential field from another copy. | The adapter follows its documented policy for additions and reliably reports missing essential evidence. Add a control before making it a required consumer behavior. |

## Go

Concurrent subprocesses around atomic archive publication. `GHQ-GO-007` and `GHQ-GO-026` cover shared MCP transport. `GHQ-PY-100` covers serial conflict. Use the same pinned inputs with synchronized goroutines calling the CLI.

| Plan ID | Assertion | Fixture or action | Observable result |
| --- | --- | --- | --- |
| VFY-GO-01 | Identical import race | Start two or more imports of one key at a shared barrier. Record actual process overlap and resulting archive entries. | All complete successfully with one final file and one digest. Pinned verify passes. |
| VFY-GO-02 | Conflicting import race | Start two valid producers for the same destination key with different source bytes and observe both processes. | Exactly one wins, the other reports conflict, and the surviving entry matches the winning process’s bytes and pins. |
| VFY-GO-03 | Read during publication | Run verify repeatedly around a coordinated import in a new archive. | The absent response is allowed before publication. Successful responses always describe a complete pinned entry and no partial JSON is observed. |
| VFY-GO-04 | Cross-version concurrency | Import v1.0.0 and v1.1.0 into the same newly created archive root at once. | Both succeed and remain independently verifiable with their two expected citations. |
| VFY-GO-05 | Across-project contention | Start two repositories with the same version label concurrently, using independent evidence and the same archive root. | Each key resolves to its own project and both remain verifiable. |
| VFY-GO-06 | Alias contention | Race different casing of one project name with same and then differing source evidence. | Case-only aliases identify one key and preserve the producer spelling. Outcomes follow the identical/conflicting import rules. |
| VFY-GO-07 | Retry after winner | Retry the winning and losing inputs separately after concurrent writers have exited. | Winner retry is byte-identical, the conflicting retry fails, and neither rewrites the published entry. |
| VFY-GO-08 | Bounded subprocess lifecycle | Cancel the harness’s deliberately stalled child in a disposable workflow run and retain process statuses independently. | The harness reports cancellation and exits within its context deadline. Any published final file verifies completely. |
| VFY-GO-09 | Transient staging isolation | Observe the archive directory while multiple writers run and after they leave normally. | Canonical discovery observes only complete published entries, and normal exits clean their staging folders. |
| VFY-GO-10 | Attempt repeatability | Run bounded races over recorded orderings on public Ubuntu and Windows, with deterministic contention evidence and independently computed post-state hashes. | Every observed overlap satisfies the invariant. A scheduler that never overlaps operations is reported as an insufficient test run. |
| VFY-GO-11 | Bounded fan-in at one key | Start a bounded set of identical and conflicting contenders using the reused fixture and log each input identity and result. | Every accepted digest identifies one winning byte sequence, and each legitimate conflict is attributable to its own input. |
| VFY-GO-12 | Parallel writes into existing archive | Preload a third independent project/version before starting concurrent writers. | The preloaded archive remains byte-identical while the new keys settle, and all expected final entries can be replayed. |
| VFY-GO-13 | Concurrent verification with wrong pin | Run one correctly pinned reader and an incorrectly pinned reader while another process imports an independent key. | Each process retains its own exit code and digest outcome. The incorrect reader cannot inherit the correct reader’s result. |
| VFY-GO-14 | Transient failure attribution | Use a disposable invalid input as one contender alongside a genuine input. Coordinate release and wait for both processes. | Only the genuine input may publish. The rejected contender’s own diagnostic and output identify why it failed. |

## C++ compiler evidence

**Prerequisite.** A pinned C++ compiler and a real compiler-evidence fixture mapped into Graphify. Reuse GHQ-PY-101 and its source bytes.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-CPP-01 | Compiler source line | Locate the exported symbol with a compiler record and compare its chosen line and Git blob to both CLI versions. |
| VFY-CPP-02 | Distinct overloads | Give two overloads or namespace-qualified symbols similar names and demonstrate that each feature points only to the explicitly recorded implementation. |
| VFY-CPP-03 | Header and definition | Place declarations and definitions in separate files, then assert the integration’s documented implementation target and corresponding Git path. |
| VFY-CPP-04 | Conditional build | Compile the same fixture under two pinned build flags and check the recorded producer build identity and intended active source location. |
| VFY-CPP-05 | Physical source mapping | Compare the compiler location and the actual bytes through a byte-oriented scanner using CRLF, UTF-8, and an unterminated final line. |
| VFY-CPP-06 | Generated or unmappable source | Exercise the emitter’s documented behavior when a source coordinate cannot be bound to a committed ordinary file, alongside a tracked valid control. |
| VFY-CPP-07 | Macro source provenance | Compile a tracked header and translation unit using a pinned macro configuration. An adapter supporting macro expansion records its documented spelling or expansion coordinate, which maps to a committed Git line. |
| VFY-CPP-08 | Template instantiations | Compile distinct instantiations of one templated function with pinned flags. Compiler identities remain distinguishable where the emitter supports them and resolve to the expected implementation coordinates. |
| VFY-CPP-09 | Translation-unit selection | Reuse a header from two translation units while changing only one source anchor in the newer fixture version. The producer preserves the intended file and build unit association. |
| VFY-CPP-10 | Path remapping in diagnostics | Build identical committed sources from two checkout roots using the compiler emitter’s supported path mapping. Citations contain stable repository-relative paths and correct lines for each root. |
| VFY-CPP-11 | Duplicate source basenames | Place identically named files in two directories and emit distinct implementation anchors. Compiler evidence and CLI citations disambiguate by full repository-relative path. |
| VFY-CPP-12 | Compiler failure attribution | Build one successful pinned compilation and one benign source compilation failure. The adapter cannot present a compiler error or missing semantic evidence as successful citation generation. |

## C# Windows file sharing

**Prerequisite.** A Windows .NET runner and an explicit supported file-sharing contract. A .NET application integration is optional.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-CS-01 | Shared read permitted | Hold the archived entry with a policy allowing the CLI read, and verify both trusted pins and the file identity. |
| VFY-CS-02 | Exclusive hold | Hold the entry in a supported exclusive mode, observe the documented native error, then release and compare original digest and successful replay. |
| VFY-CS-03 | Conflict while reader holds file | Keep a permitted read handle on an existing entry during a conflicting import, then verify the previously published bytes and the contender’s refusal. |
| VFY-CS-04 | Two-reader isolation | Hold a handle for one version and read the other via the real CLI. Only the intended version and source appear in each result. |
| VFY-CS-05 | FileSharing cleanup | Keep a disposable archive in a test-specific Windows directory, dispose every handle after success and forced failure, and verify cleanup with native file operations. |
| VFY-CS-06 | .NET client decode | Feed real UTF-8 verify and lookup output to the adopter’s .NET reader. Validate integer lines, full pins, and reporting of the process failure before exposing results. |
| VFY-CS-07 | File identity diagnostics | Record native .NET outcome and CLI exit status separately when a handle policy causes a denial. Decoded diagnostics point to the affected file and cannot be confused with a wrong-pin failure. |
| VFY-CS-08 | .NET report pin round-trip | Serialize both actual lookup records through the adopter’s typed .NET result object and read them back in a new process. The second process preserves each full source SHA, archive digest, producer spelling and integer citation. Compare with the direct CLI result. |
| VFY-CS-09 | Independent FileStream position | Read both entries with separate handles and interleave partial byte reads during a CLI verification. Hashes and expected versions stay bound to the correct handle, and replays still select both original entries. |

## F# archive state model

**Prerequisite.** A separately testable immutable archive model and the existing fixture inputs. The harness invokes the real CLI for each operation.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-FS-01 | Basic state machine | Generate seeded interleavings of import, verify and lookup and compare each native result and persisted entry set with the reference model. |
| VFY-FS-02 | Idempotent retry | Vary the number and position of identical imports in a trace. Each keeps one byte-identical entry. |
| VFY-FS-03 | Rejected transition | Interleave missing lookups and conflicting imports with successful writes. The model and CLI agree on unchanged state after every rejected operation. |
| VFY-FS-04 | Project identity class | Generate supported casing aliases and distinct projects. The model’s key equivalence classes match CLI selection and preservation of producer spelling. |
| VFY-FS-05 | Independent versions commute | Reorder two independent version imports; both final state maps and per-version byte digests agree. |
| VFY-FS-06 | Shrunk regression trace | When a seed fails, replay and minimize the sequence while preserving the commands, pins and exact first divergence as a portable regression fixture. |
| VFY-FS-07 | Read commands are state-neutral | Generate traces with reordered verify and lookup calls between imports. The final observed file map is independent of read order, and each read result agrees with the modeled state at that step. |
| VFY-FS-08 | Version extensions | Add valid additional version labels that share a source commit, where accepted by the CLI contract. The model and archive agree on separate version keys and corresponding per-entry digests. |
| VFY-FS-09 | Reference model sensitivity | Deliberately invert one outcome rule inside the model test harness. A known fixture detects the oracle defect, proving the comparison can distinguish disagreement. |

## Haskell

**Prerequisite.** A pinned Graphify implementation-relation contract and a producer fixture with multiple linked categories.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-HS-01 | Typed relation model | Derive expected implementation citations from directed feature edges independently of the product reader and compare the whole set to CLI output. |
| VFY-HS-02 | Doc/test isolation | Hold file paths and lines constant while varying the typed relation in valid producer outputs. Only implementation changes navigation. |
| VFY-HS-03 | Multiple anchors | Verify that the reference model preserves two distinct coordinates in the same file and all independent files. |
| VFY-HS-04 | Unrelated graph components | Add another fully attached feature and its valid links. Neither source point contaminates the other feature’s returned citations. |
| VFY-HS-05 | Permutation property | Change only the order of valid nodes and links and compare normalized citation sets. Assert ordering separately when the product contract specifies it. |
| VFY-HS-06 | Empty and absent query | Model a known feature with no implementation and an unknown feature distinctly. Compare the actual empty result and process error respectively. |
| VFY-HS-07 | Shared implementation across features | Give two known feature nodes the same tracked implementation anchor and vary an unrelated edge. Each feature receives the expected shared location independently. |
| VFY-HS-08 | Versioned change semantics | Use two valid graph exports with changed implementation coordinates and stable documentation edges. The independent model explains the exact version change and confirms documentation has no navigation effect. |
| VFY-HS-09 | Reference model self-check | Mutate one fixture annotation used by the model while retaining the original real CLI data. The comparison fails at the intended coordinate, demonstrating that it is independent. |
| VFY-HS-10 | Producer report correlation | Correlate independently queried MCP graph relations with the pinned graph snapshot before comparing to the CLI. Expected decisions come from the versioned source graph, and the report retains both producer and consumer observations. |
| VFY-HS-11 | Declared source-only fixture | Model an inventoried code path with zero linked implementation edges, then compare with a linked control in the same graph. An inventoried file alone yields no citation. Adding the documented implementation relation changes only the corresponding feature. |

## Java

**Prerequisite.** A pinned Java client. CLI subprocess interoperability can run when available. MCP rows require the intended JVM MCP adapter.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-JAVA-01 | ProcessBuilder boundary | Verify actual CLI exit codes, one UTF-8 JSON object and versioned integer citations when invoked with structured arguments. |
| VFY-JAVA-02 | Unicode source identity | Round-trip archive paths with non-ASCII names through the supported Java client without dropping or normalizing fixture bytes. |
| VFY-JAVA-03 | MCP-to-CLI correlation | Use the real JVM MCP discovery for the same selected Graphify graph, then compare source commit and implementation anchors with CLI lookup. |
| VFY-JAVA-04 | Independent sessions | Query the two fixture versions concurrently through separate JVM sessions and require each reply to match its own graph and source. |
| VFY-JAVA-05 | Request attribution | Correlate successful and failed tool results by ID without leaking one pending request into another version’s result. |
| VFY-JAVA-06 | Timeout and closure | Exercise a bounded client timeout and EOF with real process lifecycle management, then open a fresh client and verify the succeeding replay. |
| VFY-JAVA-07 | Process streams under load | Drain native process streams independently for sequential successful verify and expected failure cases. Neither stream blocks child completion, and JSON belongs only to the successful command. |
| VFY-JAVA-08 | Citation line representation | Decode one real CLI result with a JSON library configured for the desired integer policy, then use a synthetic malformed response as control. The real integer survives exact decoding, and the decoder refuses unsafe or fractional navigation coordinates according to its contract. |
| VFY-JAVA-09 | MCP initialization visibility | Negotiate the supported capabilities and request version-specific graph data with the actual JVM client. The adapter observes what the server advertises before discovery and reports mismatches as structured failures. |
| VFY-JAVA-10 | Per-version audit output | Record real client outcome, source pin, archive digest and citations into the adopter’s result shape. Displaying or serializing the outcome retains the complete identifiers and a failed request cannot be reported as verified. |

## Lua

**Prerequisite.** A real headless editor adapter with a documented checkout and citation selection contract.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-LUA-01 | Versioned editor jump | Drive actual CLI matches into the headless editor and assert the buffer path and one-based cursor line for both versions. |
| VFY-LUA-02 | Unresolved navigation | Exercise a missing feature and a known feature with no implementation. Neither opens a new buffer or moves the cursor. |
| VFY-LUA-03 | Stale source view | Select v1.0.0, advance the checked-out file to the fixture’s second version, and assert the editor adapter’s version-aware behavior using the stored source pin. |
| VFY-LUA-04 | Literal filename | Navigate to a fixture file with spaces, Unicode and editor-special characters through the real adapter’s structured file API. |
| VFY-LUA-05 | Multiple targets | Open two available locations with explicit selection and compare buffer/line state to the chosen item. |
| VFY-LUA-06 | Late async response | Return a valid older result after switching the UI selection. The editor retains the currently selected version and reports the stale result according to its contract. |
| VFY-LUA-07 | Different buffers, same basename | Use versioned producer fixtures with two files of the same basename in distinct Git directories. The editor opens the full intended relative path for the chosen citation. |
| VFY-LUA-08 | Already open buffer | Place the target file in an open buffer and track cursor state in another buffer before navigation. Only the intended buffer position changes and the requested one-based line is displayed. |
| VFY-LUA-09 | Versioned buffer reuse | Open the same feature in both versions using the documented version views, then revisit the first. Editor state uses the requested version’s source bytes and restores its original line. |
| VFY-LUA-10 | Process failure status | Have the real adapter request a missing feature or incorrect pin after a valid navigation. An adapter error is surfaced without replacing the previously verified buffer selection. |
| VFY-LUA-11 | Explicit user choice of active window | Open two editor windows showing different fixture versions and direct a lookup to the selected window through the installed adapter. Only the selected window's view navigates. The other window's cursor and selected version remain unchanged. |

## Ruby

**Prerequisite.** A real Rake task or Ruby adopter harness using structured subprocess calls and one shared archive.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-RB-01 | Batch identity | Run a tabular batch of multiple projects and version labels through actual lookups. Every reported row retains its original request and pins. |
| VFY-RB-02 | Continue after row failure | Place a missing version between valid rows and compare per-row exit and aggregate status with the documented batch policy. |
| VFY-RB-03 | Repeatable batch replay | Re-run the same ordered batch in an independently prepared working directory and compare normalized outputs and on-disk archive digests. |
| VFY-RB-04 | CLI invocation fidelity | Pass Unicode and whitespace through the adopter’s actual argument array. Preserve both JSON and nonzero process status without flattening structured inputs. |
| VFY-RB-05 | Mixed project alias | Interleave case-only aliases with distinct projects sharing a version label and compare per-row canonical spelling and citations. |
| VFY-RB-06 | Machine-readable report | Deserialize the real Rake batch report, verify no diagnostic is mistaken for a pass, and preserve disputed row pins in the output. |
| VFY-RB-07 | Batch empty input | Invoke the real adopter task with no rows and with one genuine row as a control. Empty input results follow the documented batch policy and produce no fabricated verification. |
| VFY-RB-08 | Duplicate row identity | Include two identical rows under different caller-supplied row IDs. Returned status remains associated with each input ID, even if the task coalesces identical I/O. |
| VFY-RB-09 | Reordered partial failures | Run the same successful and failed requests in a different order. The per-row outcomes are stable and ordered as documented. Aggregate results reflect the same set of failures. |
| VFY-RB-10 | Independent manifest location | Launch the adopter task from another project directory with an explicit manifest and the same archive. Inputs and output destinations follow the documented arguments, and version identity is unchanged. |
| VFY-RB-11 | Adopter retry with stable identity | Retry only a previously failed row alongside a control using unchanged original input records. The resulting status is tied to the retry’s own row ID and cannot change previously successful report entries. |

## Rust

**Prerequisite.** A separately implemented bounded Rust reader over the actual archive format, with agreement checks against the real CLI.

| Plan ID | Assertion | Fixture and observable result |
| --- | --- | --- |
| VFY-RS-01 | Read archive incrementally | Feed both real archive entries in chunks that cross JSON and encoded-blob boundaries. Match independent checksums and results with the CLI. |
| VFY-RS-02 | Boundary acceptance | Exercise equality and one-over limits for a supported archive component using valid companion fields where feasible. Report intended-limit reachability separately when an outer limit is hit first. |
| VFY-RS-03 | Strict Base64 and UTF-8 | Reject noncanonical encoded content and invalid JSON text, each with a valid recomputed outer digest when needed to reach the parser. |
| VFY-RS-04 | Truncation and EOF | End a read mid-string or mid-blob and verify a bounded error with no success result. A complete capped control passes. |
| VFY-RS-05 | Inventory byte accounting | Compare distinct path identity, decoded bytes and aggregate counts with the Python oracle and CLI on both versions. |
| VFY-RS-06 | Reordered or duplicated inventory | Confirm the reader’s documented handling of a harmless valid reordering, then isolate a repeated path that should be rejected. Verify the control with the same trusted outer-digest procedure. |
| VFY-RS-07 | Chunking invariance | Feed real inputs through a reader using one-byte, odd-sized and standard buffered chunks. Every supported chunk size yields the same decoded bytes, inventory and independently computed digests. |
| VFY-RS-08 | Distinct read failure types | Exercise EOF, an injected benign I/O failure, and successful reading of the same pinned archive. The reader retains the intended failure classification and emits verified results only for complete inputs. |
| VFY-RS-09 | Valid empty blob | Use a valid producer inventory with an ordinary empty file and a nonempty referenced implementation file. Empty bytes retain their independent expected digest, and only the real implementation contributes a navigation coordinate. |
| VFY-RS-10 | Resource accounting evidence | Track bytes read and decoded under deterministic capped fixtures while comparing to the Python independent oracle. The reader reports the correct budget layer and no success is issued for an over-limit input. |
| VFY-RS-11 | Opaque evidence round-trip | Decode and re-encode the embedded evidence of both archives in Rust without interpreting evidence text as a new canonical JSON document. Decoding the re-encoded fields returns original graph, receipt and source bytes exactly, including harmless whitespace. |

## Coverage review

This planning pass evaluated 84 candidate additions against the existing rows and executable catalog. It kept 58 distinct additions and did not assign new IDs to 26 overlapping ideas. The gaps emphasized here are mixed-version producer inputs, byte-neutral reads, cap precedence, OS-specific encoding, independent model sensitivity, and runtime-specific interoperability. Preserve earlier case IDs when extending fixtures across these boundaries.

| Product surface | Primary owner | Cross-check or remaining boundary |
| --- | --- | --- |
| Version selection and trusted pins | JavaScript | Python reads independent Git objects. Bash and PowerShell surface outcomes in their native shells. |
| Byte fidelity and archive limits | Python | Rust supplies a separate bounded reader. C++ checks compiler coordinates against the source bytes. |
| Archive publication and immutability | Go | Existing Python serial controls, F# state transitions, and Windows C# handle behavior. |
| Citation integrity and navigation | TypeScript | Haskell checks graph semantics. Lua verifies actual editor state. |
| Other runtime clients | Java and Ruby | JVM stdio/MCP or CLI subprocesses, and row-level Rake/adopter reporting. |
| Evidence and release attribution | Python and native shell lanes | Independent handoff read, exact-run receipt rules, and public Ubuntu/Windows replay. |

The review covers valid hits, legitimate empty data, invalid selections, exact boundaries, offline reads, historical coordinates, retry, contention, stale replies, platform behavior, and runner proof. Remaining unknowns include real client integrations, platform-specific sharing expectations, and limits that may be hard to reach because another format limit applies first. Treat each as a dependency or an explicit reachability check. Reopen the matrix when a product surface or support contract changes, an adopter ships a new boundary, or a reported failure lacks a matching case. Use named passing runner results to report implemented coverage.
