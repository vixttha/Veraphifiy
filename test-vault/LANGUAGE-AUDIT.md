# Graphify HQ language audit

The audited checkout is [424d86c](https://github.com/vixttha/Graphify-HQ/commit/424d86c6581b496bac7feb590b1512eeb11ac569). The [public workflow](https://github.com/vixttha/Graphify-HQ/actions/runs/44514338567) completed successfully. Its logs account for 66 named results on Ubuntu and 11 on Windows. The Ubuntu handoff recorded identical graph SHA-256 values from Python and Node and a passing Lydite v2 verdict for the exact audited checkout and run.

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
| BART draft recovery | The pinned candidate recovery routine removed both fixture evidence files when an empty pending journal directory was present. The probe covers an incomplete journal, outside the healthy-journal interruption cases already in CI. | GHQ-PY-035 |

The proposed cases describe the target behavior. The reproduced cases are queued for implementation and verification.

## Coverage by language

| Language | Executable cases | Baseline actually exercised | Proposed |
| --- | ---: | --- | ---: |
| Python | 27 | Real build and MCP handoff, reproducibility, Git blobs, released builder behavior, simulated provenance, pinned draft journaling and test-run gate. | 12 |
| Bash | 6 | Pinned workflow step bodies, staged Git fetch and extraction in fixtures, quoting, and simulated dependency failures. Live Graphify workflow routing remains open. | 12 |
| JavaScript | 12 | Fresh graph and companion receipt inspection, exact graph digest, identity, counts, endpoint integrity and source anchors. | 12 |
| TypeScript | 10 | Three compiler checks and seven runtime citation checks at the current reference adapter. The type gate accounts for included expect-error annotations. | 12 |
| Go | 11 | Real MCP stdio client against pinned Graphify with discovery, lookup, directed routes, concurrency and stale warnings. | 12 |
| PowerShell | 11 | Windows CLI subprocess results, environment handling, v1 and v2 Lydite receipts, exact graph bytes and Git checkout checks. | 12 |
| C++ | 0 | Pinned Lydite C++20 sample. Graphify work requires a compiler-backed adopter emitter. | 6 |
| C# | 0 | Pinned Lydite .NET sample. Graphify work requires an actual receipt or graph consumer. | 6 |
| F# | 0 | Pinned Lydite F# Interactive sample. Graphify work requires a cross-snapshot analyzer. | 6 |
| Haskell | 0 | Pinned Lydite runghc sample. Graphify work requires a release dependency analyzer. | 6 |
| Java | 0 | Pinned Lydite Java source launcher sample. Graphify work requires a JVM MCP client. | 6 |
| Lua | 0 | Pinned Lydite Lua sample. Graphify work requires an editor adapter. | 6 |
| Ruby | 0 | Pinned Lydite Ruby sample. Graphify work requires an adopter task with a machine-readable verdict. | 6 |
| Rust | 0 | Pinned Lydite rustc harness sample. Graphify work requires a streaming archive importer. | 6 |
| **Total** | **77** | **Six active Graphify tracks.** | **120** |

The pinned released builder, candidate code, and staged workflow are distinct audit targets. Fresh builds use the [BART v0.0.8 release fixture](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1). The evidence-loss probe concerns the [BART draft candidate](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/d227b202c7cce1b86a1ee06596d709f3dfee1039/candidate/evidence_map.py). Bash uses bodies from the [pinned OBJ/MTL workflow](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/2680e03a3d1a7216666554c5baca43b2ec93b944/.github/workflows/obj-mtl-evidence.yml). Live private dispatch and live GitHub PR provenance remain unverified. The eight adopter tracks remain conditional on a real entry point and native named outcome reconciliation.

See the [expanded language plan](LANGUAGE-PLAN.md) for fixtures and expected outcomes.
