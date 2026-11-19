"""Check the Vault catalog against named results from completed runner commands."""

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from validate_catalog import read_cases

VAULT = Path(__file__).resolve().parent
LINUX = frozenset({"PY", "SH", "JS", "TS", "GO"})
WINDOWS = frozenset({"PS"})
ID = r"GHQ-[A-Z]+-\d{3,}"


def typed_passes(log, source):
    expected = re.findall(r"(?m)^\s*// (GHQ-TS-\d{3,}): TS\d+ at \w+\b", source)
    if not expected or len(expected) != len(set(expected)):
        raise ValueError("missing or repeated compile-time declarations")
    observed = re.findall(r"(?m)^TYPE PASS (GHQ-TS-\d{3,})$", log)
    require_cases(set(expected), observed)
    return observed


def go_outcomes(log):
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
                outcomes.append((match[1], action == "pass"))
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
        outcomes = go_outcomes(log)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("platform", choices=("linux", "windows"))
    parser.add_argument("logs", type=Path)
    args = parser.parse_args()
    try:
        catalog, _ = read_cases(VAULT / "cases.md")
        kinds = WINDOWS if args.platform == "windows" else LINUX
        if any(case.split("-")[1] not in LINUX | WINDOWS for case in catalog):
            raise ValueError("catalog has a case with no runner")
        failures = []
        for kind in sorted(kinds):
            expected = {case for case in catalog if case.startswith("GHQ-" + kind + "-")}
            failed_cases = set()
            try:
                log = (args.logs / (kind.lower() + ".log")).read_text(encoding="utf-8")
                actual = passed_cases(kind, log, failed_cases=failed_cases)
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
        parser.exit(1, f"Test Vault run evidence failed: {error}\n")


if __name__ == "__main__":
    main()
