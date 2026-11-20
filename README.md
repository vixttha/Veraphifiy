# Provenistem for Veraphify

Use this permanent branch to record what Veraphify can do, keep track of possible improvements, and recover the context in a later session.

- [**Features**](features/INDEX.md) links implemented and verified capabilities to exact code and evidence.
- [**Proposals and plans**](features/PLANNED.md) tracks work that still needs implementation or approval.
- [**Ideas**](ideas/INDEX.md) preserves questions, design choices, and the discussions behind them.
- [**Source audit**](docs/SOURCE-AUDIT.md) maps the issues and earlier Provenistem entries to these records.
- [**Inventory reconciliation**](docs/INVENTORY-RECONCILIATION.md) records branch, candidate, test and proposal counts and identifies gaps found in review.

## Capture and update records

1. Copy the [idea form](templates/idea.json) or [feature form](templates/feature.json) into the matching `records/` directory and assign the next unused ID.
2. Give ideas a concise origin and attach exact source or validation evidence to capabilities. Add the record to its index.
3. Link the originating ideas with a feature's `idea_ids`. Keep IDs stable when titles and status change. Track defects and approvals in GitHub Issues and PRs.

The qualifying executable baseline recorded in the release tracker is the [v0.0.9 integration snapshot](https://github.com/vixttha/Veraphify/tree/92ec58f3e574efd814f395d2f2bc23948d794b55) under review in [PR #56](https://github.com/vixttha/Veraphify/pull/56). Its [exact public push run](https://github.com/vixttha/Veraphify/actions/runs/44649433106/attempts/1) reconciled 210 Vault cases. The branch contains 37 ideas and 40 feature records, including 21 implemented, 13 proposed and six planned. Each record states its evidence scope. The [release tracker](https://github.com/vixttha/Veraphify/issues/21) owns publication status.

The two starter forms and directory layout come from the pinned [public Provenistem template](https://github.com/vixttha/README-HQ/tree/f6bc7b41af8dca7b7bf0671c851d041a55d77e71). This branch begins with an [empty root commit](https://github.com/vixttha/Veraphify/commit/a2cf6bc14a1e2a8e1b24ed6044d87e475929f285). It works as plain GitHub files and uses Veraphify's own records.
