# Build through the Veraphify project map

The map is generated from the committed idea and feature records on this Provenistem branch. The [category configuration](../map-groups.json) gives both record types a page in Discover, Archive, Verify, Adopt, or Remember. A record with no category appears under Uncategorized. Categories guide browsing and add no relationships to the source records.

## Open the map

1. Open the [Provenistem project map workflow](https://github.com/vixttha/Veraphify/actions/workflows/provenistem-project-map.yml?query=branch%3AProvenistem) and select the successful run for the commit you want to inspect.
2. Download its `veraphify-provenistem-map` artifact, extract it, and open `index.html` in your browser. The viewer works offline. Opening a source link takes you to the pinned file on GitHub.
3. Check `receipt.json` for the input revision and the SHA-256 hashes of the generator, viewer, and outputs. `graph.json` contains the same records and their directed links.

The workflow runs on pushes to Provenistem and keeps each artifact for seven days. It reads the committed catalog and writes derived output to the run artifact.

To generate a copy from a checkout of this branch:

```bash
python3 tools/build_map.py --repo . --rev HEAD --groups map-groups.json \
  --github-repo vixttha/Veraphify --output ../veraphify-provenistem-map
```

Use a new output directory. Supply a full commit SHA instead of `HEAD` to reproduce an older map from the same generator and viewer. Commit changes to the catalog and its category configuration before generating. The portable generator and its companion read the Git snapshot and check the fields and relationships shown in the map.

## Try it on one feature

Start at **Discover → Features → Feature code-to-test and document navigation**. Its [feature record](../features/records/FEAT-000018.json) links to the ideas behind it. Use the following steps as a working example.

| Page | Veraphify next step |
| --- | --- |
| Discover | On a single fixture, choose one feature to trace to its implementation, test, and documentation. Inspect the files behind Graphify's suggestions. |
| Archive | Write down the exact Git commit and keep the graph and receipt used for the lookup. |
| Verify | Add a named check on the Lydite-Test-Vault branch. Check that the known feature returns the expected file and line, and that a missing or stale link produces the expected failure or unresolved result. |
| Adopt | Run the walkthrough from a clean checkout and capture the exact public workflow run. |
| Remember | Link the verified behavior, source, and run from the feature record. Record follow-up ideas separately. |

Use GitHub issues to track implementation. The map shows the statuses in the source records. Its generation receipt covers the generated files and input commit.
