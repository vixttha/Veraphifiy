# Graphify HQ Test Vault

Graphify HQ uses the copy-in starter from [Lydite v0.0.4](https://github.com/vixttha/Lydite-Test-Vault-Template/releases/tag/v0.0.4). The [case catalog](cases.md) lists executable checks across Python, Bash, JavaScript, TypeScript, Go, and PowerShell. The [coverage plan](PLAN.md) records the original 40 scenarios. The [language plan](LANGUAGE-PLAN.md) maps the next cases across all 14 Lydite languages. The [language audit](LANGUAGE-AUDIT.md) records the gap probes and the boundaries of the baseline. The [audit](AUDIT.md) records the gaps and the checks that address them.

## Run the suites

From the repository root, with Python 3.12 available, run `python test-vault/validate_catalog.py` to check the Lydite catalog. The [Test Vault workflow](../.github/workflows/test-vault.yml) runs the suites on standard public GitHub-hosted Ubuntu and Windows runners.

For TypeScript and Go, use the [pinned BART archive checkout](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1). The Go staleness check needs the archive inside its Git checkout. The archive checkout SHA and the graph's original source SHA are separate.

```bash
git init _archive
git -C _archive fetch --depth=1 https://github.com/vixttha/Blender-Agent-Refinement-Toolkit.git 6af3c2025be3f51e02dca4e4502088c526aae6d1
git -C _archive checkout --detach FETCH_HEAD
export GRAPHIFY_HQ_ARCHIVE="$PWD/_archive/graphify/v0.0.8"

# Node 24 and the locked TypeScript compiler
npm --prefix test-vault/typescript ci --ignore-scripts --no-audit --no-fund
npm --prefix test-vault/typescript test

# CPython 3.12 on Linux x64 and Go 1.25.5
python -m venv .venv
.venv/bin/python -m pip install --require-hashes --no-deps --only-binary=:all: -r _archive/versions/v0.0.8/requirements.txt
.venv/bin/python -m pip check
export GRAPHIFY_HQ_PYTHON="$PWD/.venv/bin/python"
(cd test-vault/go && go test -v -count=1 -mod=readonly ./...)
```

Run the builder, JavaScript, and Bash suites with the same locked Linux dependencies. The Python suite creates the graph consumed by Node. Draft recovery and provenance checks use the pinned BART candidate.

```bash
vault_tmp=$(mktemp -d)
candidate=d227b202c7cce1b86a1ee06596d709f3dfee1039
workflow=2680e03a3d1a7216666554c5baca43b2ec93b944
git -C _archive fetch --no-tags --depth=1 https://github.com/vixttha/Blender-Agent-Refinement-Toolkit.git "$candidate" "$workflow"
export GRAPHIFY_HQ_CANDIDATE="$vault_tmp/candidate"
export GRAPHIFY_HQ_BART_WORKFLOW="$vault_tmp/obj-mtl-evidence.yml"
export GRAPHIFY_HQ_HANDOFF="$vault_tmp/graph-handoff"
mkdir "$GRAPHIFY_HQ_CANDIDATE"
git -C _archive archive "$candidate" candidate tools | tar -x -C "$GRAPHIFY_HQ_CANDIDATE"
git -C _archive show "$workflow:.github/workflows/obj-mtl-evidence.yml" > "$GRAPHIFY_HQ_BART_WORKFLOW"
"$GRAPHIFY_HQ_PYTHON" -B -m unittest discover -s test-vault/python -v
node --test test-vault/javascript/evidence.test.mjs
bash test-vault/bash/workflow.tests.sh
```

The workflow compares named native results with the catalog, including the TypeScript diagnostic code and token position and the final Go package result. Install the locked TypeScript dependencies before running the Python suite because its compiler regression invokes the pinned compiler.

Ubuntu records two Lydite v2 receipts for the independently observed graph, Graphify receipt, source pin, and three allowlisted synthetic Git blobs. The tracked [handoff profile](handoff-profile.json) specifies the producer version, the bundle order, and byte limits for both readers. The v2 handoff bundle caps its encoded size at 20 MiB and uses a per-file cap before loading each part. For implementation citations, the Node inspector compares source coordinates with the verified blob using the frozen producer's UTF-8 line rules.

Windows downloads the exact artifact by ID, revalidates the producer and pinned source blobs with Node, and independently checks the Python bundle and Lydite verdict against the current checkout, run, and attempt. Newline conversion invalidates the bundle. If Windows receives an earlier Ubuntu attempt, rerun all jobs to produce a fresh handoff. The Git attribute on the tracked case plan preserves its exact bytes on both runners. Public artifacts contain only the explicitly listed synthetic fixture files and are retained for seven days. For a local shared receipt test, set positive decimal `GITHUB_RUN_ID` and `GITHUB_RUN_ATTEMPT` before running the observer suites, then use the workflow's recorder and verification commands.

Run the PowerShell suite with PowerShell 7, Git, and Python 3.12 on the path. It copies the pinned verifier and its helpers into a temporary Git checkout with a tracked catalog. Its synthetic manifests, receipts, and Actions summary files live beside that checkout.

```powershell
pwsh -NoProfile -File test-vault/powershell/verify-receipts.tests.ps1
```

The TypeScript code is a reference consumer for typed source navigation. Go talks to the real pinned Graphify server over stdio. PowerShell covers process arguments, status, environment, and shared evidence on Windows. Cases for an application viewer or Windows graph publishing need those entry points.

## Adoption audit

| Source | Verified finding |
| --- | --- |
| Graphify HQ template | The reference source is [v0.0.8 at `6af3c20`](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1). The frozen kit and archive remain the baseline for the Vault. The [original Test Vault plan](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/4a7d1b202ced1f014371c3df34c926c00ab58bcf/test-vault/PLAN.md) is the starting point for this branch. |
| Lydite Test Vault | [Release v0.0.4 at `87d25d8`](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/87d25d80d3154d295052412b64b29a0f0f152c27) supplies the catalog and receipt tools. The [release's public runner](https://github.com/vixttha/Lydite-Test-Vault-Template/actions/runs/44506598515) verified the starter adoption. |
| BART application Test Vault | The [existing BART `test-vault` branch](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/83f3ca3d520c52d187868ac24e116e8286828a7a) covers the BART application. This branch is scoped to Graphify HQ. |

## Installed files

These files originate at the pinned Lydite commit:

| File | Installed copy | Source |
| --- | --- | --- |
| [MIT notice](LICENSE) | Verbatim | [Lydite license](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/LICENSE) |
| [Case and run receipt](case-and-receipt.md) | Verbatim | [Lydite case and receipt form](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/case-and-receipt.md) |
| [Catalog validator](validate_catalog.py) | Veraphifiy validates visible case rows and malformed table headers ([#33](https://github.com/vixttha/Veraphifiy/issues/33)). | [Lydite catalog validator](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/validate_catalog.py) |
| [Receipt verifier](verify_receipts.py) | Veraphifiy requires lowercase receipt extensions (GHQ-PS-035), tracked verifier modules and a tracked plan in CI ([#32](https://github.com/vixttha/Veraphifiy/issues/32)). | [Lydite receipt verifier](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/verify_receipts.py) |
| [Checkout identity helper](source_commit.py) | Verbatim | [Lydite source commit helper](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/source_commit.py) |

Run the receipt verifier from the intended Git checkout root with a tracked catalog, tracked verifier modules, and clean tracked files. Both CI jobs pass `--require-tracked-case` for the committed handoff plan. Disposable fixture checks can supply an external plan, and their verdict identifies it as caller-supplied. For new evidence, use schema v2 and record the SHA-256 of the exact case manifest bytes. Matching v1 manifests and receipts remain supported.

The [upstream receipt guide](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/evidence.md) documents how to bind evidence to the actual checkout, runner, and attempt.

## Graphify HQ scope

The [case catalog](cases.md) is the executable inventory. The [language plan](LANGUAGE-PLAN.md) preserves the original 320-case planning baseline. Implemented proposal IDs appear in both files. [The adoption issue](https://github.com/vixttha/Veraphifiy/issues/15) tracks the eight language tracks that require integrations and active-lane cases awaiting a deployed boundary.

Use this Vault for the reusable kit's map generation, Graphify MCP readback, archive reproducibility, GitHub source provenance, and evidence publication. The [checkpoint tracker](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/provenistem/graphify-hq/provenistem) links the project changes to their existing issues, PRs and CI runs. Add only project cases backed by a defined behavior, and attach results once they are run.


## Proposal checkpoint

The executable catalog accounts for 114 of the 320 proposals. The original proposals remain visible in the language plan. The remaining 47 active-lane cases include additional fixture work, pinned upstream behavior, and hosted deployment checks. The 159 adopter cases depend on the project integrations described in their individual plan rows. [Implementation tracker](https://github.com/vixttha/Veraphifiy/issues/15)

The Go protocol checks use the pinned SDK and an isolated stdio subprocess when the frozen Graphify server cannot produce a particular protocol response. Server lifecycle, checkout freshness, and simultaneous archive identity are also exercised against the real pinned Graphify runtime. The Node source-blob check reads exact Git bytes from the disposable builder fixture. The Bash wheel checks use an isolated local wheelhouse and the real pinned install step. The PowerShell verifier considers lowercase `.json` receipt files on both hosts and uses literal paths for native logs.
