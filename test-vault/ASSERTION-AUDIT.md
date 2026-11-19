# Graphify HQ assertion durability audit

## Audited baseline

The audit used direct inspection and controlled execution at [ae04181](https://github.com/vixttha/Graphify-HQ/commit/ae041812022fcf3c06bed6eaef50eef9f2884199). It covered the [77 registered cases](cases.md), the [320 proposals](LANGUAGE-PLAN.md), the [pinned Lydite v0.0.4 inventory](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/87d25d80d3154d295052412b64b29a0f0f152c27/languages), and the [public Ubuntu and Windows run](https://github.com/vixttha/Graphify-HQ/actions/runs/44524700213). It compared the tests with the needs documented in the [Vault scope](README.md) and checked the released BART archive, pinned candidate, and staged workflow separately.

A fresh Linux checkout run reconciled all 77 named checks with Python 3.12.14, Node 24.22.3, TypeScript 5.9.3, Go 1.25.5, Bash, and PowerShell 7.6.10. The local PowerShell execution tested the shell and verifier on Linux. The linked hosted job supplies actual Windows evidence. A fresh local graph build and Node read recorded the same SHA-256 and passed the Lydite verifier with synthetic run metadata. The hosted run separately recorded its exact CI metadata and had zero downloadable artifacts. Independent download and cross-OS artifact verification remain open.

## What the suites detected

The six baseline controls passed. Each paired probe changed one behavior in a disposable copy, then ran the existing assertion without changing it. This targeted use of mutation testing sampled one consequence per language. It provides direct evidence for those assertions. [Mutation testing method](https://pitest.org/)

| Language | Existing case | Deliberate change | Observed signal |
| --- | --- | --- | --- |
| Python | GHQ-PY-024 | Accept duplicate named check results in the reconciler. | The duplicate-control subtest failed because it expected a rejection. |
| Bash | GHQ-SH-006 | Remove hash enforcement from the pinned dependency-install step in a workflow copy. | The fixture stopped when the hash-enforcement argument was absent. The tracer confirmed that assertion was the failing step. |
| JavaScript | GHQ-JS-003 | Remove the graph digest check in the copied inspector. | The stale-digest case failed because it expected a rejection. |
| TypeScript | GHQ-TS-006 | Let documentation links qualify as implementation citations. | The existing test observed a different lookup status and failed. |
| Go | GHQ-GO-003 | Remove an expected implementation edge from a copied archive supplied to the real Graphify MCP server. | The implementation-edge and exact-citation checks failed. |
| PowerShell | GHQ-PS-009 | Remove exact case-plan digest comparison in the verifier copied by the fixture. | The PowerShell case failed because a receipt for the original plan passed after the plan bytes changed. |

## Where assertions need maintenance

| Finding | Evidence | Decision |
| --- | --- | --- |
| Compiler attribution can succeed for the wrong error. | The pinned compiler returned exit 0 when GHQ-TS-002's annotated error was replaced by a different field error. The named gate still attributed all three IDs. Correcting both fields made compiler exit 2 surface the unused directive, while attribution by the parser alone still returned the same IDs. | Implement GHQ-PY-033 against the actual diagnostic field or source span and expected code. A diagnostic code alone would miss the reproduced wrong-field substitution. [TypeScript expected-error behavior](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-9.html) |
| Named Go passes can survive a failed or absent final package result. | The audited Go log had 11 valid named results. Standalone reconciliation accepted all 11 after the terminal package event was changed to fail or removed. The public workflow separately gates the Go command's exit through Bash pipefail. | Treat the reconciler as supplemental while CI checks the command exit. Use GHQ-PY-051 before standalone log reconciliation can certify a complete Go run. [Go test event format](https://pkg.go.dev/cmd/test2json) · [Workflow](../.github/workflows/test-vault.yml) |
| The Python invalid-input check depends on exception spelling. | A clearer invalid UTF-8 diagnostic left rejection and prior-archive preservation intact. GHQ-PY-009 failed on the old exception name. A companion run expecting the new diagnostic passed with the same rejection and preservation assertions. | Keep the case. Use a stable diagnostic category, nonzero exit, and unchanged output as the contract. Keep exact names only where the versioned CLI promises them. |
| The Go statistics check expects the frozen fixture exactly. | A disposable graph with an extra unrelated node failed GHQ-GO-002 on the literal total of 33. GHQ-GO-003 and GHQ-GO-004 still passed against that graph. | Keep the historical snapshot check. A rolling compatibility check should compare reported counts with an independent reading of the selected archive and still prove the expected relationships and citations. |
| The Bash dependency test proves command configuration and failure propagation. | It caught loss of the required flag via a fixture command. Its installer is a stand-in. The public workflow separately performs a real locked install. | Keep GHQ-SH-006 for shell wiring and use GHQ-SH-009 when proving that the real installer rejects changed wheel bytes under the selected lock. Keep exact step names and flags scoped to the workflow fixture. |
| The logs prove a Linux graph handoff and Windows verifier coverage. | The same graph digest appears in the two Ubuntu observers. The Windows job uses fixture receipts, and the run exposes no downloadable artifact. | Keep the fast local proof. Reserve GHQ-PS-015 and GHQ-SH-027 for actual transferred bytes and an independent receiving job. [GitHub artifact behavior](https://docs.github.com/en/actions/tutorials/store-and-share-data#validating-artifacts) |

## Test value by language

The six active tracks account for 77 executable cases and 161 proposals. The eight adopter tracks account for 159 proposals. Their language inventory entries prove availability in the Lydite template. Project coverage requires each track's named Graphify integration and a test that exercises its own observable behavior.

| Language | Executable | Proposed | Durable requirement and future-proofing decision |
| --- | ---: | ---: | --- |
| Python | 27 | 28 | Keep source truth, same-input reproducibility, current evidence identity, and safe recovery permanent. Scope archive migrations and PR API checks to their version or deployment. |
| Bash | 6 | 27 | Keep exact input selection and failure propagation. Treat runner routing, triggers, permissions, dependency flags, and transfer as checks of the workflow currently in service. |
| JavaScript | 12 | 26 | Keep exact bytes, graph consistency, and usable source links. Require explicit format definitions before installing a score interval, artifact size cap, or producer-version range. |
| TypeScript | 10 | 26 | Keep unusable citations out of navigation and prove the intended compiler rejection. Defer view, link-builder, cache, and async behavior until an actual caller owns those contracts. |
| Go | 11 | 27 | Keep query correctness, source identity, and precise request correlation. Label frozen statistics and text checks with their archive and server profile. Exercise structured output or list-change behavior when Graphify adopts it. |
| PowerShell | 11 | 27 | Keep Windows argument handling, native verdicts, and receipt binding. Maintain v1 as a compatibility case while v1 is supported. Require the real handoff when asserting inter-OS evidence. |
| C++ | 0 | 20 | Compiler-derived source truth matters once Graphify consumes compiler output. Use real translation units and independently known source anchors. Enable module, overlay, and column cases only for supported configurations. |
| C# | 0 | 20 | Cross-runtime schema agreement matters once a .NET consumer supplies evidence. Test the actual receipt fields and wire profile. Exercise oversized numeric IDs only if that contract accepts numeric IDs and specifies their range. |
| F# | 0 | 20 | Accurate revision attribution matters if a snapshot analyzer becomes authoritative. Exercise real Git histories and keep synthetic replay outcomes tied to the chosen projection rules. |
| Haskell | 0 | 20 | Prerequisite ordering matters if an actual release planner depends on that output. Verify constraints independently of tie order unless a stable tie order is part of the planner contract. |
| Java | 0 | 20 | Complete, correctly correlated source replies matter if a JVM client is adopted. Use the deployed client, with stream fixtures for runtime-specific failure modes. |
| Lua | 0 | 20 | Opening the correct source without disrupting editing matters if an editor adapter is adopted. Limit tab, quickfix, and byte-column expectations to supported editor behavior. |
| Ruby | 0 | 19 | Truthful adopter verdicts matter if a Ruby adapter reports CI evidence. Remove duplicate shell-level coverage when it has no Ruby-specific consequence. |
| Rust | 0 | 20 | Complete imports and preservation of the last good archive matter if a Rust importer is adopted. Choose the supported archive, filesystem, and durability profile before imposing checksum or generation behavior. |

## Proposal decisions before implementation

- Keep GHQ-PY-029 scoped to fixed source bytes, dependency pins, and archive receipts. Lydite execution receipts intentionally carry different run and attempt metadata. Keep that distinction when defining deterministic comparisons.
- Keep GHQ-PY-035, GHQ-PY-052, GHQ-PY-053, and GHQ-JS-037 as regression targets. The earlier audit reproduced evidence loss on a damaged journal, inconsistent archive read/write policy, receipt reuse across attempts, and invalid source path typing. These protect archive recovery and evidence trust directly. [Prior reproductions](LANGUAGE-AUDIT.md#reproduced-gaps)
- Merge GHQ-PS-019 into GHQ-PS-009 as a line-ending fixture unless a deployed transport adds a distinct conversion risk. GHQ-PS-015 has the distinct transport boundary. GHQ-JS-016, GHQ-JS-019, and GHQ-JS-038 can share one fixture family with separate checks for presence, syntax, and truth of the source digest.
- Reuse one MCP negotiation fixture for GHQ-GO-025, GHQ-GO-031, and GHQ-GO-038 while keeping separate assertions for capability, version, and operation order. Keep GHQ-GO-036 and GHQ-GO-037 conditional on the negotiated tool contract. [MCP tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- Clarify GHQ-SH-007 against the event actually supported. The Vault currently runs on pushes to its branch. The pinned BART workflow has push and pull-request triggers. A manual dispatch is a separate capability. Treat GHQ-SH-007 and GHQ-SH-033 as companion assertions from the same hosted fixture when possible. [Vault workflow](../.github/workflows/test-vault.yml) · [Pinned BART workflow](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/2680e03a3d1a7216666554c5baca43b2ec93b944/.github/workflows/obj-mtl-evidence.yml)
- In GHQ-TS-035 distinguish the compiler option, already enabled in the reference suite, from application behavior when a user selects an invalid index. In GHQ-PS-038 distinguish interpreter selection from receipt generation. The current Windows verifier consumes fixture receipts. Only a real recorder can prove the emitted runtime identity.
- Treat presentation wording, exact snapshot counts, vendor-specific API limits, protocol versions, and deprecated formats as maintained compatibility evidence. A behavior can outlive a tool or format revision, while the fixture or assertion syntax changes. Retain the historical fixture if the project still promises to verify that release.

## Summary

The six active suites detect material regressions in the sampled assertions, and all 77 current checks reconcile. The controlled probes also identified fragile assertions and incomplete log evidence. The 320 proposals remain a planning baseline. Build permanent coverage around source truth, graph integrity, usable citations, safe recovery, and verifiable execution. Use pinned compatibility checks and real adopter integrations where those observable boundaries add distinct proof.
