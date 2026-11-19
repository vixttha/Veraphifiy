"""Check the Vault catalog against named results from completed runner commands."""

import argparse
from html import escape
import os
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from validate_catalog import read_cases

VAULT = Path(__file__).resolve().parent
LINUX = frozenset({"PY", "SH", "JS", "TS", "GO"})
WINDOWS = frozenset({"PS"})
ID = r"GHQ-[A-Z]+-\d{3,}"
TAP_RESULT = re.compile(r"^(ok|not ok) (\d+)(?: - (.*))?$")
TAP_SUMMARY = re.compile(
    r"(?m)^1\.\.(\d+)\n# tests (\d+)\n# suites \d+\n# pass (\d+)\n"
    r"# fail (\d+)\n# cancelled (\d+)\n# skipped (\d+)\n# todo (\d+)\n"
    r"# duration_ms \d+(?:\.\d+)?\s*\Z"
)


UNITTEST_TOTAL = re.compile(r"(?m)^Ran (\d+) tests? in \d+(?:\.\d+)?s$")
UNITTEST_START = re.compile(r"(?m)^test_\w+ \([^\r\n]*\) \.\.\.(?: |$)")
UNITTEST_OK = re.compile(r"OK(?: \((?:skipped|expected failures)=\d+(?:, (?:skipped|expected failures)=\d+)*\))?")


def typed_passes(log, source):
    expected = re.findall(r"(?m)^\s*// (GHQ-TS-\d{3,}): TS\d+ at \w+\b", source)
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("missing or repeated compile-time declarations")
    observed = re.findall(r"(?m)^TYPE PASS (GHQ-TS-\d{3,})$", log)
    require_cases(set(expected), observed)
    return observed


def go_outcomes(log, failed_cases):
    packages = set()
    terminal = defaultdict(list)
    outcomes = []
    for line in log.splitlines():
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError("invalid Go test event")
        package = event.get("Package")
        action = event.get("Action")
        if not isinstance(package, str) or not package:
            # Build messages can carry ImportPath instead of Package.
            if action in {"build-output", "build-fail"}:
                if action == "build-fail":
                    raise ValueError("Go package build failed")
                continue
            raise ValueError("Go test event lacks a package")
        packages.add(package)
        if action not in {"pass", "fail", "skip"}:
            continue
        test = event.get("Test")
        if test is None:
            terminal[package].append(action)
        elif isinstance(test, str):
            match = re.match(r"TestGraphifyMCP/(GHQ-GO-\d{3,})(?:_|$)", test)
            if match:
                passed = action == "pass"
                outcomes.append((match[1], passed))
                if failed_cases is not None and not passed:
                    failed_cases.add(match[1])
        else:
            raise ValueError("invalid Go test name")
    if not packages or any(terminal[package] != ["pass"] for package in packages):
        raise ValueError("each Go package must have one passing terminal result")
    return outcomes


def passed_cases(kind, log, *, failed_cases=None):
    if kind == "PY":
        matches = re.findall(
            r"(?m)^test_(GHQ_PY_\d{3,})_\w+ \(.*\) \.\.\. (ok|FAIL|ERROR|skipped[^\n]*)$",
            log,
        )
        outcomes = [(name.replace("_", "-"), status == "ok") for name, status in matches]
    elif kind == "GO":
        outcomes = go_outcomes(log, failed_cases)
    elif kind in {"TS", "JS"}:
        outcomes = []
        for line in log.splitlines():
            match = re.match(r"(ok|not ok) \d+ - (" + ID + r")\s", line)
            if match:
                skipped = re.search(r"\s#\s*(?:SKIP|TODO)\b", line, re.IGNORECASE)
                outcomes.append((match[2], match[1] == "ok" and not skipped))
    else:
        outcomes = [(case, status == "PASS") for status, case in re.findall(
            r"(?m)^(PASS|FAIL|SKIP) (" + ID + r")\s", log,
        )]
    failed = {case for case, passed in outcomes if not passed}
    if failed_cases is not None:
        failed_cases.update(failed)
    passes = [case for case, passed in outcomes if passed]
    contradictory = sorted(failed.intersection(passes))
    if contradictory:
        raise ValueError(f"contradictory terminal outcomes: {contradictory}")
    return passes


def require_cases(expected, actual):
    counts = Counter(actual)
    missing = sorted(expected - counts.keys())
    unexpected = sorted(counts.keys() - expected)
    duplicate = sorted(case for case, count in counts.items() if count > 1)
    if missing or unexpected or duplicate:
        raise ValueError(f"missing={missing}, unexpected={unexpected}, duplicate={duplicate}")


def require_complete_tap(log):
    lines = log.splitlines()
    results = [match for line in lines if (match := TAP_RESULT.fullmatch(line))]
    for mode, _, title in (match.groups() for match in results):
        if mode == "not ok" and not re.search(r"\s#\s*TODO\b", title or "", re.IGNORECASE):
            name = title or "unnamed result"
            if not re.match(ID + r"(?:\s|$)", name):
                raise ValueError(f"uncataloged TAP failure: {name}")
    summary = TAP_SUMMARY.search(log)
    if lines.count("TAP version 13") != 1 or summary is None:
        raise ValueError("missing or incomplete native TAP summary")
    plan, tests, passed, failed, cancelled, skipped, todo = map(int, summary.groups())
    if failed or cancelled:
        raise ValueError(f"native TAP suite failed: failures={failed}, cancelled={cancelled}")
    if not plan or len(results) != plan or any(int(match[2]) != index for index, match in enumerate(results, 1)):
        raise ValueError("native TAP plan does not match the terminal results")
    # Node counts nested tests in its summary and only top-level results in its plan.
    if tests < plan or tests != passed + skipped + todo:
        raise ValueError("native TAP summary totals do not reconcile")


def require_complete_unittest(log):
    totals = list(UNITTEST_TOTAL.finditer(log))
    if len(totals) != 1 or not log[:totals[0].start()].endswith("-" * 70 + "\n"):
        raise ValueError("missing or repeated native unittest summary")
    total = totals[0]
    verdict = log[total.end():].strip()
    if verdict.startswith("FAILED"):
        raise ValueError("native unittest suite failed: " + verdict.splitlines()[0])
    if not UNITTEST_OK.fullmatch(verdict):
        raise ValueError("missing successful native unittest verdict")
    # A skipped subtest may have its own indented line. Count only top-level test starts.
    records = UNITTEST_START.findall(log, 0, total.start())
    if not records or len(records) != int(total[1]):
        raise ValueError("native unittest total does not match the verbose test records")


def catalog_lanes(cases):
    lanes = defaultdict(set)
    for case in sorted(cases):
        match = re.fullmatch(r"GHQ-([A-Z]+)-\d{3,}", case)
        if not match or match[1] not in LINUX | WINDOWS:
            raise ValueError(f"catalog case has no supported runner: {case}")
        lanes[match[1]].add(case)
    return lanes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("linux", "windows"))
    parser.add_argument("logs", type=Path)
    args = parser.parse_args()
    try:
        catalog, _ = read_cases(VAULT / "cases.md")
        kinds = WINDOWS if args.platform == "windows" else LINUX
        lanes = catalog_lanes(catalog)
        failures = []
        for kind in sorted(kinds):
            expected = lanes[kind]
            failed_cases = set()
            try:
                log = (args.logs / (kind.lower() + ".log")).read_text(encoding="utf-8")
                actual = passed_cases(kind, log, failed_cases=failed_cases)
                if kind in {"TS", "JS"}:
                    require_complete_tap(log)
                elif kind == "PY":
                    require_complete_unittest(log)
                if kind == "TS":
                    actual += typed_passes(log, (VAULT / "typescript/citations.types.ts").read_text(encoding="utf-8"))
                require_cases(expected, actual)
                print(f"{kind}: {len(expected)} catalog checks accounted for")
            except FileNotFoundError:
                failures.append(f"{kind}: no native log, suite unavailable")
            except (OSError, ValueError) as error:
                failures.append(f"{kind}: failed or skipped cases={sorted(failed_cases)}; {error}")
        if failures:
            raise ValueError("\n" + "\n".join(failures))
    except (OSError, ValueError) as error:
        if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
            heading = f"### Test Vault {args.platform} reconciliation failed\n\n"
            # Escape report text and bound the retained summary independently of the logs.
            diagnostic = escape(str(error)[:4096])
            with Path(summary).open("a", encoding="utf-8") as output:
                output.write(heading + "<pre>" + diagnostic + "</pre>\n")
        parser.exit(1, f"Test Vault run evidence failed: {error}\n")


if __name__ == "__main__":
    main()
