# Graphify HQ Test Vault

This branch is the Graphify HQ project's adoption of the Lydite Test Vault in `vixttha/Graphify-HQ`. The [case catalog](cases.md) starts at **0 cases**. See the [expanded test plan](PLAN.md) for the proposed Python, Bash, and JavaScript cases. Use the [case and run receipt form](case-and-receipt.md) when test work begins.

## Adoption audit

| Source | Verified finding |
| --- | --- |
| Graphify HQ template | The reference source is [v0.0.8 at `6af3c20`](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1). The frozen kit and archive remain the baseline for the Vault. The [original Test Vault plan](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/4a7d1b202ced1f014371c3df34c926c00ab58bcf/test-vault/PLAN.md) is the starting point for this branch. |
| Lydite Test Vault | [Lydite `main`](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/fe7b00aa17862d7a01dfd15481594be837bc6d9f) carries the [v0.0.3 starter](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/starter/test-vault/README.md). It includes 14 language examples with their own metadata. The [exact-source public run](https://github.com/vixttha/Lydite-Test-Vault-Template/actions/runs/44475200133) passed the inventory and adoption job and the Ubuntu and Windows example jobs. |
| Lydite upgrade status | The [hardening PR](https://github.com/vixttha/Lydite-Test-Vault-Template/pull/22) and [archive mode check](https://github.com/vixttha/Lydite-Test-Vault-Template/pull/32) are drafts. CI for the pinned Lydite revision checks inventory, adoption and examples. Archive rebuild evidence for the hardening belongs to its draft run. |
| BART application Test Vault | The [existing BART `test-vault` branch](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/83f3ca3d520c52d187868ac24e116e8286828a7a) covers the BART application. This branch is scoped to Graphify HQ. |

## Installed files

The following files were copied verbatim from the pinned Lydite commit:

| File | Source |
| --- | --- |
| [MIT notice](LICENSE) | [Lydite license](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/LICENSE) |
| [Case and run receipt](case-and-receipt.md) | [Lydite case and receipt form](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/starter/test-vault/case-and-receipt.md) |
| [Catalog validator](validate_catalog.py) | [Lydite catalog validator](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/starter/test-vault/validate_catalog.py) |
| [Receipt verifier](verify_receipts.py) | [Lydite receipt verifier](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/starter/test-vault/verify_receipts.py) |

The starter validator requires at least one case. Run it after the catalog has its first case. The [upstream receipt guide](https://github.com/vixttha/Lydite-Test-Vault-Template/blob/fe7b00aa17862d7a01dfd15481594be837bc6d9f/starter/test-vault/evidence.md) documents how to bind evidence to the actual checkout, runner, and attempt. Use standard GitHub-hosted public runners for future CI.

## Graphify HQ scope

Use this Vault for the reusable kit's map generation, Graphify MCP readback, archive reproducibility, GitHub source provenance, and evidence publication. The [checkpoint tracker](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/provenistem/graphify-hq/provenistem) links the project changes to their existing issues, PRs and CI runs. Add only project cases backed by a defined behavior, and attach results once they are run.
