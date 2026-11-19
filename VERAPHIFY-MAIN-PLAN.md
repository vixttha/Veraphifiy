# Veraphify main-branch README plan

**Status** · Planning draft. README HQ baseline: [v0.0.6.67 trial](README.md#trial-baseline).

The [observed main commit](https://github.com/vixttha/Veraphify/commit/2e43c950b564d525161e966a2a86de378c62d950) contains a one-line `# Graphify-HQ` README. The runnable [v0.0.9 draft](https://github.com/vixttha/Veraphify/pull/48) targets `graphify-hq-test-vault`. The CLI, walkthrough, and Test Vault links below refer to [the draft product commit](https://github.com/vixttha/Veraphify/commit/35c463cf063a9a52dc7397491978a25284743556).

## Opening copy

> **Veraphify**
>
> Archive evidence for each project version and trace a feature back to the exact Git commit, file, and line that implement it.

Use two links near the top: **Try the two-version walkthrough** and **See the verification evidence**. While the product lives on the draft branch, label the link **Try the v0.0.9 candidate** and point to a pinned draft revision. Once the product files are on the publication branch, use relative links and the supported checkout instructions for that revision.

## Page structure

| Section | Content | Evidence |
| --- | --- | --- |
| Overview and status | Use the Veraphify spelling, the opening sentence, and one line with the current release or preview status. | [Release tracker](https://github.com/vixttha/Veraphify/issues/21) |
| Quickstart | Start with Git and Node.js 24, then run `node veraphifiy.mjs --help` in the selected checkout. Follow it with the real first success: build and import two disposable versions, verify both, and look up the same feature. State the Bash, CPython 3.12, and Linux x86-64 requirements next to the builder walkthrough. | [Candidate README](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/README.md) · [Walkthrough](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/docs/adopter-walkthrough.md) |
| Example result | Show the same feature at `src/feature.py:3` in `v1.0.0` and `src/feature.py:4` in `v1.1.0`. Include the version and source commit in any output excerpt. | [Walkthrough assertions](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/docs/adopter-walkthrough.md) |
| How it works | Explain the input pair `graph.json` and `receipt.json`, then show what `import`, `verify`, and `lookup` each return. Explain why a trusted source SHA and archive digest identify the exact archived entry. Keep the Graphify producer pin and private archive storage guidance beside the relevant task. | [Candidate CLI](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/veraphifiy.mjs) · [Candidate README](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/README.md) |
| Verification | Link to the exact hosted run and the Test Vault. State separately which steps built the Graphify fixture and which replayed an existing archive. | [Public runner attempt 1](https://github.com/vixttha/Veraphify/actions/runs/44631263772/attempts/1) · [Test Vault](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/test-vault/README.md) |
| Project links | Add issue reporting, the verified applicable reuse terms, and Graphify attribution. Keep the historical CLI filename where users need to type it. | [Issues](https://github.com/vixttha/Veraphify/issues) · [Candidate README](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/README.md) |

Use a plain text heading for the first publication candidate. The [draft asset manifest](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/brand-identity/09-assets/manifest.json) contains zero exports. A small table of the two real citation results can do the work of the first visual.

## Techniques from established projects

| Source | Technique to apply |
| --- | --- |
| [uv README](https://github.com/astral-sh/uv) | Put a one-sentence definition and a short list of actions near the front, with commands and documentation routes within reach. For Veraphify, lead with archive, verify, and look up. |
| [ripgrep README](https://github.com/BurntSushi/ripgrep) | Use concrete examples and explain cases where the tool is a poor fit. For Veraphify, state what evidence must already exist and bind each example to a project version. |
| [Pandoc README](https://github.com/jgm/pandoc) | Route readers from a concise overview to the guide, examples, and demo. Give Veraphify’s complete two-version procedure one maintained home. |
| [Google README guidance](https://google.github.io/styleguide/docguide/READMEs.html) and [GitHub README guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes) | Describe project status and how to begin. Use descriptive link text and relative links to same-ref files. |
| [Diátaxis](https://diataxis.fr/) | Write the first-use example as a tutorial. Put command options and archive fields in reference documentation. |

## Review before publication

- Replay the published quickstart on a clean public Ubuntu runner. Verify both fixture versions, different source commits, distinct citation lines, and unchanged bytes for the earlier archive. If documenting Windows, run the advertised Windows commands independently. The existing Windows replay is evidence for replay.
- Record the exact commit, workflow, run, attempt, and artifact ID and digest where applicable. Check that status and evidence links describe the same product stage.
- Verify the rendered homepage, relative links, and anchors on the proposed publication branch. Open it at desktop and narrow widths.
- Check the product name, Graphify attribution, asset status, and product-level reuse terms at the publication revision. Route homepage publication through a separate review.
