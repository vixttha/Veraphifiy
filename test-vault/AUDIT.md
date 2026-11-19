# Graphify HQ Test Vault audit

The review starts from Graphify-HQ commit [a740fa9](https://github.com/vixttha/Graphify-HQ/commit/a740fa9af32517d67cbcbe3f0cccd0f169605d25) and its [31-check public run](https://github.com/vixttha/Graphify-HQ/actions/runs/44510666971). It uses direct inspection of the workflow, assertions, catalog, archived bytes, Graphify responses, and the pinned Lydite tools.

| Finding | Change and proof |
| --- | --- |
| The catalog was validated as a Markdown table. Removing or skipping a named test could leave the catalog and the overall suite green. | Linux and Windows reconcile named passing results to the catalog. Python regression checks reject skipped, absent, duplicate, and undeclared results. A Go package pass cannot replace a named subtest. Compiler-only cases require an included fixture and an expected diagnostic directive. |
| The graph-consumer workflow used only the frozen archive. It could still pass if the builder stopped producing a usable new pair. | The real Python builder creates a graph from committed fixture files and resolves an implementation location over MCP. Node reads those fresh bytes and verifies the source pin, receipt hash, graph topology, counts, and per-feature evidence. |
| Receipt exercises on Windows used synthetic receipts. The baseline job had no Lydite verdict for independently observed graph bytes. | The fresh Python and Node observations each report their own SHA-256. Lydite v2 checks the named results against the exact Vault checkout, case plan, run, attempt, and shared graph. A regression changes the graph after an observation and checks that recording fails. |
| The TypeScript reference consumer returned an absolute file path as a successful repository citation. | GHQ-TS-010 reproduced the bad result before the fix. Noncanonical source paths now produce an invalid citation. |
| The Go free-text test accepted a path and a relation in unrelated parts of a response. | GHQ-GO-010 requires the actual implementation edge from the expected feature to the expected file and line. |
| The existing workflow had no assertions for Bash fetch, quoting, or error propagation. Recovery and provenance behavior were tracked in the plan. | Bash runs the pinned fetch and install step bodies with disposable Git repositories, exact pins, and injected failure boundaries. Python exercises the BART draft snapshot for recovery, provenance, and runner-mode logic. |

## Source and execution boundaries

- [Released BART v0.0.8 archive](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1) supplies the released builder and the archive used by Go and TypeScript.
- [BART #79 pinned candidate](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/d227b202c7cce1b86a1ee06596d709f3dfee1039) is the draft checkpoint for journal recovery, GitHub provenance, and runner-mode logic. Pull request API inputs are deterministic fixtures. Private execution-mode logic runs in tests, while dispatch to an actual private runner remains unverified.
- [BART #78 pinned workflow](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/2680e03a3d1a7216666554c5baca43b2ec93b944/.github/workflows/obj-mtl-evidence.yml) supplies the Bash step bodies. The fixture executes those bodies with local Git objects. GitHub event scheduling and a live PR API call fall outside those Bash cases.
- [Lydite v0.0.4](https://github.com/vixttha/Lydite-Test-Vault-Template/releases/tag/v0.0.4) supplies the unchanged catalog and receipt verifier. The Windows suite exercises the verifier. The public Linux job verifies the fresh graph handoff.
