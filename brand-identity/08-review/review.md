# Review and decisions

| Item | Status | Evidence or next review |
| --- | --- | --- |
| Product positioning | Owner direction recorded | Code memory for each project version. Graphify stays central to the identity. The [public copy](../03-messaging/voice.md) acknowledges support for Graphify and states that Veraphify is developed and maintained independently of Graphify Labs. |
| Product name | Locked | The owner chose the exact spelling **Veraphify** on November 19, 2026. See the [decision record](../01-strategy/creative-decision.json). |
| Slogan | Open | Compare the [draft options](../03-messaging/voice.md). Use the factual descriptor in current public copy. |
| Wordmark | Draft | The candidate uses the locked spelling **Veraphify**. See the [wordmark treatments](../05-wordmark/wordmark.md). |
| Naming screen | Public screening recorded | The [naming record](../02-naming/naming.md) documents exact-name results, nearby brands and why upstream attribution matters. Trademark clearance remains open. |
| Logo and type | Open | [Filed Edge leads the concept review](../04-logo/logo.md). [Index Sans leads the wordmark review](../05-wordmark/wordmark.md). Small-size and light/dark visual review pending. |
| Palette | Draft values checked | [Calculated contrast for the proposed pairs](../06-visual-system/system.md). Actual placement review pending. |
| Artwork and handoff | Pending | [Asset manifest](../09-assets/manifest.json) begins with an empty inventory. |

The exact product name and wordmark lettering have an [owner decision](https://github.com/vixttha/Veraphify/issues/21#product-name-decision). Run `python3 brand-identity/verify.py --ready-for-artwork` to check the creative record before generating candidate artwork. Review exact lettering, 24 px silhouette, clear space, theme variants, transparency, grayscale, visual similarity and usage terms against the candidate exports. Once approved logo and wordmark PNGs are registered, run `python3 brand-identity/verify.py --ready-for-handoff`.

For a later rollout, record the owner decision and confirm the README, repository description and any asset placements being updated. Use the preceding asset or text as the rollback reference.
