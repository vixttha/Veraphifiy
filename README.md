# README HQ for Veraphify

This branch is the workspace for designing and validating Veraphify’s repository homepage.

- [README template](TEMPLATE.md)
- [Veraphify main-branch README plan and project facts](VERAPHIFY-MAIN-PLAN.md)
- [README technique learning log](LEARNING.md)

## Trial baseline

Use README HQ `v0.0.6.67` from the [exact repair candidate](https://github.com/vixttha/README-HQ/commit/8d50caec2bc6fcb998994a1fd302294a029325f9). The upstream [draft PR #68](https://github.com/vixttha/README-HQ/pull/68) records the combined candidate. Its [public runner attempt 1](https://github.com/vixttha/README-HQ/actions/runs/44538439592/attempts/1) passed the Ubuntu reader check, Windows reader check, and Graphify job at that SHA.

The [candidate audit](https://github.com/vixttha/README-HQ/tree/6d6dc0a4a744f5700078fa936ce635c4bd45ed91) adds an audit script and workflow to that baseline. The [next repair plan](https://github.com/vixttha/README-HQ/blob/ac07987cfe11d6592b8def2ff16b72a6b2c0a203/plans/v0.0.6.68-to-v0.0.6.77/README.md) and [subsequent repair plan](https://github.com/vixttha/README-HQ/blob/4457fc1e82f2cff0225536ff1c43e3e565fb46db/plans/v0.0.6.78-to-v0.0.6.128/README.md) describe planned work. The upstream pull request records remaining checkpoint acceptance and merge-queue verification.

The template here is an original adaptation of the [pinned README guide](https://github.com/vixttha/README-HQ/blob/8d50caec2bc6fcb998994a1fd302294a029325f9/README-GUIDE.md). The [audit workflow](https://github.com/vixttha/README-HQ/blob/8d50caec2bc6fcb998994a1fd302294a029325f9/audits/README.md), [technique library](https://github.com/vixttha/README-HQ/blob/8d50caec2bc6fcb998994a1fd302294a029325f9/techniques/README.md), and [validator](https://github.com/vixttha/README-HQ/blob/8d50caec2bc6fcb998994a1fd302294a029325f9/tools/check_readme_hq.py) are available from the same upstream revision. Follow the upstream [reuse terms](https://github.com/vixttha/README-HQ/blob/8d50caec2bc6fcb998994a1fd302294a029325f9/REUSE.md) if distributing upstream material.

## Use this workspace

1. Record the product ref and full commit SHA. Read the product files, entry point, and workflows at that revision.
2. Use the template to draft a homepage in a review branch containing the product files. Use the plan for the first reader task and supporting evidence.
3. Record observations from the trial in the learning log and reuse the upstream technique IDs.
4. Validate the draft against the selected product checkout. Use the pinned README HQ audit as one check and record the observed result of running the actual first-use commands on public GitHub-hosted runners.
5. After homepage approval, check the published GitHub view and record its commit and supporting runs.
