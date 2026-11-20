# Veraphify main-branch README plan

**Status** · Drafted in [PR #55](https://github.com/vixttha/Veraphify/pull/55). The [public runner](https://github.com/vixttha/Veraphify/actions/runs/44642589173/attempts/1) verified the exact README commit `88d5d08cd8c80de3927858685878e51b6d7c69b8`. The product evidence below records the inputs to the original plan. README HQ baseline: [v0.0.6.67 trial](README.md#trial-baseline).

The [observed main commit](https://github.com/vixttha/Veraphify/commit/2e43c950b564d525161e966a2a86de378c62d950) contains a one-line `# Graphify-HQ` README. The runnable [v0.0.9 draft](https://github.com/vixttha/Veraphify/pull/48) targets `graphify-hq-test-vault`. The CLI, walkthrough, and Test Vault links below refer to [the draft product commit](https://github.com/vixttha/Veraphify/commit/35c463cf063a9a52dc7397491978a25284743556).

## Project information for the template

| Field | Verified input |
| --- | --- |
| Name and positioning | **Veraphify**. The approved positioning is **code memory for each project version**. It helps a maintainer or coding agent identify the source commit, file, and physical line that implement a feature in a selected project version. [Product name and scope](https://github.com/vixttha/Veraphify/issues/21#product-name-decision) |
| Target release and checkout | `v0.0.9` is the release target. The runnable candidate is draft PR #48 at `35c463cf063a9a52dc7397491978a25284743556`, with no published GitHub Release observed. The observed default branch contains the placeholder README. [Draft PR](https://github.com/vixttha/Veraphify/pull/48) · [Release list](https://github.com/vixttha/Veraphify/releases) |
| Input and result | The pinned Graphify producer supplies `graph.json` and `receipt.json`. Veraphify imports evidence against the claimed Git commit, preserves the archive, verifies it, and returns version-specific implementation citations. [CLI](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/veraphifiy.mjs) · [Candidate README](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/README.md) |
| First reader task | Run the disposable two-version walkthrough, then compare the same feature’s citations at `src/feature.py:3` and `src/feature.py:4`. The Ubuntu workflow extracted and executed the walkthrough block from the candidate documentation. [Walkthrough](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/docs/adopter-walkthrough.md) · [Workflow step](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/.github/workflows/test-vault.yml#L64-L75) |
| Prerequisites | Git and Node.js 24 for the CLI entry point. The documented build walkthrough uses Bash, CPython 3.12 with venv, and Linux x86-64. Retain the literal CLI filename `veraphifiy.mjs` where a reader types it. [Candidate README](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/README.md) · [Walkthrough](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/docs/adopter-walkthrough.md) |
| Attribution | Preserve the approved wording: “We use and support the open-source Graphify project. Veraphify is developed and maintained independently of Graphify Labs.” [Rebrand and homepage acceptance](https://github.com/vixttha/Veraphify/issues/22) |
| Support, assets, and reuse | Use GitHub Issues for support and a text heading for the homepage preview. The candidate artwork manifest has no exports. First-party reuse terms are awaiting an owner decision, and the imported notices apply to their respective materials. [Issues](https://github.com/vixttha/Veraphify/issues) · [Asset manifest](https://github.com/vixttha/Veraphify/blob/35c463cf063a9a52dc7397491978a25284743556/brand-identity/09-assets/manifest.json) · [Reuse decision](https://github.com/vixttha/Veraphify/issues/29) |

## Proposed positioning

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

## Candidate evidence for the future homepage

| Evidence | Observed result |
| --- | --- |
| Exact candidate push | [Test Vault attempt 1](https://github.com/vixttha/Veraphify/actions/runs/44631263772/attempts/1) passed all three standard public GitHub-hosted jobs at `35c463cf063a9a52dc7397491978a25284743556`. The [release evidence rule](https://github.com/vixttha/Veraphify/issues/21#v009-release-evidence-rule) defines which run the owner reviews. |
| Ubuntu producer | The [producer job](https://github.com/vixttha/Veraphify/actions/runs/44631263772/job/135938191720) ran the documented adopter walkthrough and built the fixture evidence. |
| Independent replay | [Ubuntu replay](https://github.com/vixttha/Veraphify/actions/runs/44631263772/job/135939704958) and [Windows replay](https://github.com/vixttha/Veraphify/actions/runs/44631263772/job/135939704952) independently verified and replayed both archives from the retained handoff. Use the Windows result to support replay coverage. |
| Handoff | [Artifact 14580608620](https://github.com/vixttha/Veraphify/actions/runs/44631263772/artifacts/14580608620), ZIP SHA-256 `624c6568a85c8d864d8ac3c35f0468fb9f3698d7bb58222960237c92fba7969c`. Keep the ID and digest in the evidence record because artifact availability depends on retention. |
| PR integration | [PR run attempt 1](https://github.com/vixttha/Veraphify/actions/runs/44631272272/attempts/1) passed at merge SHA `779a2c2bc90fe430126a3c09d5c268199318a545`. Use it as evidence for integration review. |

## Techniques and learning

The [learning log](LEARNING.md) groups the researched techniques by reader task and maps them to the existing README HQ registry. Use the selected combinations when drafting the public README.

## Review before publication

- Replay the proposed homepage quickstart on a clean public Ubuntu runner. Verify both fixture versions, different source commits, distinct citation lines, and unchanged bytes for the earlier archive. If documenting Windows, run the advertised Windows commands independently. The existing Windows replay is evidence for replay.
- Record the exact commit, workflow, run, attempt, and artifact ID and digest where applicable. Check that status and evidence links describe the same product stage.
- Verify the rendered homepage, relative links, and anchors on the proposed publication branch. Open it at desktop and narrow widths.
- Check the product name, Graphify attribution, asset status, and product-level reuse terms at the publication revision. Route homepage publication through a separate review.
