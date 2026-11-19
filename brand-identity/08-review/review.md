# Review and decisions

| Item | Status | Evidence or next review |
| --- | --- | --- |
| Dedicated identity branch | Requested | Owner wants a separate identity and flagged the overlap with Graphify's name. |
| Product name | Selected | The owner chose **GEvidence** on November 19, 2026. See the [decision record](../01-strategy/creative-decision.json). |
| Wordmark | Draft | The candidate uses **GEvidence** as its lettering. See the [wordmark treatments](../05-wordmark/wordmark.md). |
| Naming screen | Earlier candidates reviewed | [Earlier shortlist and observed overlaps](../02-naming/naming.md). GEvidence screening pending. |
| Symbol and type | Proposed | [Filed Edge leads the concept review](../04-logo/logo.md). [Index Sans leads the wordmark review](../05-wordmark/wordmark.md). Small-size and light/dark visual review pending. |
| Palette | Draft values checked | [Calculated contrast for the proposed pairs](../06-visual-system/system.md). Actual placement review pending. |
| Artwork and handoff | Pending | [Asset manifest](../09-assets/manifest.json) begins with an empty inventory. |

After the owner confirms the exact product name and wordmark text, record a publishable decision reference and run `python3 brand-identity/verify.py --ready-for-artwork`. Review exact lettering, 24 px silhouette, clear space, theme variants, transparency, grayscale, visual similarity and usage terms against the candidate exports. Once approved logo and wordmark PNGs are registered, run `python3 brand-identity/verify.py --ready-for-handoff`.

For a later rollout, record the owner decision and confirm the README, repository description and any asset placements being updated. Use the preceding asset or text as the rollback reference.
