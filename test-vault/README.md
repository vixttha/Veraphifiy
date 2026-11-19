# Graphify HQ Test Vault

Graphify HQ uses the copy-in starter from [Lydite v0.0.4](https://github.com/vixttha/Lydite-Test-Vault-Template/releases/tag/v0.0.4). The [case catalog](cases.md) lists executable TypeScript, Go, and PowerShell checks. The [initial test plan](PLAN.md) describes the proposed Python, Bash, and JavaScript cases. Use the [case and run receipt form](case-and-receipt.md) to record verified runs.

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

The following files were copied verbatim from the pinned Lydite commit:

| File | Source |
| --- | --- |
| [MIT notice](LICENSE) | [Lydite license](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/LICENSE) |
| [Case and run receipt](case-and-receipt.md) | [Lydite case and receipt form](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/case-and-receipt.md) |
| [Catalog validator](validate_catalog.py) | [Lydite catalog validator](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/validate_catalog.py) |
| [Receipt verifier](verify_receipts.py) | [Lydite receipt verifier](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/verify_receipts.py) |
| [Checkout identity helper](source_commit.py) | [Lydite source commit helper](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/source_commit.py) |

Run the receipt verifier from the intended Git checkout root with a tracked catalog and clean tracked files. For new evidence, use schema v2 and record the SHA-256 of the exact case manifest bytes. Matching v1 manifests and receipts remain supported.

The [upstream receipt guide](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/87d25d80d3154d295052412b64b29a0f0f152c27/starter/test-vault/evidence.md) documents how to bind evidence to the actual checkout, runner, and attempt.

## Graphify HQ scope

Use this Vault for the reusable kit's map generation, Graphify MCP readback, archive reproducibility, GitHub source provenance, and evidence publication. The [checkpoint tracker](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/provenistem/graphify-hq/provenistem) links the project changes to their existing issues, PRs and CI runs. Add only project cases backed by a defined behavior, and attach results once they are run.
