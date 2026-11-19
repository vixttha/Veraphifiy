"""Check the Vault catalog against named results from completed runner commands."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from validate_catalog import read_cases

VAULT = Path(__file__).resolve().parent
LINUX = frozenset({"PY", "SH", "JS", "TS", "GO"})
WINDOWS = frozenset({"PS"})
ID = r"GHQ-[A-Z]+-\d{3,}"


def typed_passes(log, source):
    # The surrounding npm command checks tsc's exit status. Its native file
    # list must include the source binding each negative case to its directive.
    if not any(line.strip().endswith("/test-vault/typescript/citations.types.ts") for line in log.splitlines()):
        raise ValueError("tsc did not check citations.types.ts")
    return re.findall(r"(?m)^[ \t]*// (GHQ-TS-\d{3,}):.*\n[ \t]*// @ts-expect-error\b", source)


def passed_cases(kind, log):
    if kind == "PY":
        names = re.findall(r"(?m)^test_(GHQ_PY_\d{3,})_\w+ \(.*\) \.\.\. ok$", log)
        return [name.replace("_", "-") for name in names]
    if kind == "GO":
        cases = []
        for line in log.splitlines():
            event = json.loads(line)
            if event.get("Action") == "pass":
                match = re.match(r"TestGraphifyMCP/(GHQ-GO-\d{3,})(?:_|$)", event.get("Test", ""))
                if match:
                    cases.append(match.group(1))
        return cases
    if kind in {"TS", "JS"}:
        cases = []
        for line in log.splitlines():
            match = re.match(r"ok \d+ - (" + ID + r")\s", line)
            if match and not re.search(r"\s#\s*(?:SKIP|TODO)\b", line, re.IGNORECASE):
                cases.append(match.group(1))
        return cases
    return re.findall(r"(?m)^PASS (" + ID + r")\s", log)


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
        for kind in sorted(kinds):
            expected = {case for case in catalog if case.startswith("GHQ-" + kind + "-")}
            log = (args.logs / (kind.lower() + ".log")).read_text(encoding="utf-8")
            actual = passed_cases(kind, log)
            if kind == "TS":
                actual += typed_passes(log, (VAULT / "typescript/citations.types.ts").read_text(encoding="utf-8"))
            require_cases(expected, actual)
            print(f"{kind}: {len(expected)} catalog checks accounted for")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Test Vault run evidence failed: {error}\n")


if __name__ == "__main__":
    main()
