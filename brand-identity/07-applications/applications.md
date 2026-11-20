# Applications

| Placement | Use | Size and crop | Accessible text and fallback |
| --- | --- | --- | --- |
| GitHub README | First public surface. Left-align the lockup above the one-line description. | Check at 320 px viewport width and 120 px rendered lockup width. Keep clear space inside the artwork. | Use a real heading for the name. Treat the adjacent lockup as decorative when the heading already supplies the accessible name. Launch with text if artwork review is pending. |
| Repository or project avatar | Square symbol where the name is already displayed. | Review at 24 px and 48 px. Keep all paths inside a centered safe square. | The platform supplies the project name beside the avatar. |
| Evidence walkthrough | One real example showing a feature through to a file and a receipt. | Let the example stack vertically at narrow widths. | Include the path, line and receipt as real text links next to any diagram. |

## Export plan

Keep the symbol and the exact-name wordmark as separate transparent PNG assets. Candidate export families are `symbol-light-r01.png`, `symbol-dark-r01.png`, `wordmark-light-r01.png` and `wordmark-dark-r01.png`. Register the actual native size, provenance and review state in the [asset manifest](../09-assets/manifest.json). Preview the composition in GitHub's light and dark modes before any live rollout.

See the [review record](../08-review/review.md).
