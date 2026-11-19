"""Write one v2 Lydite receipt using the digest observed by a passing suite."""

import argparse
import hashlib
import json
import os
from pathlib import Path

from source_commit import source_commit
from verify_receipts import RUN_ID

VAULT = Path(__file__).resolve().parent
PLAN = VAULT / "javascript/case.json"
CHECKS = {"python-build": "python", "node-consume": "node"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=CHECKS)
    parser.add_argument("handoff", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--runtime", required=True)
    args = parser.parse_args()

    run = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not RUN_ID.fullmatch(run) or not RUN_ID.fullmatch(attempt):
        parser.error("set GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT to positive decimal strings")
    with (args.handoff / "graph.json").open("rb") as graph:
        actual = hashlib.file_digest(graph, "sha256").hexdigest()
    observed = (args.handoff / (CHECKS[args.check] + ".sha256")).read_text(encoding="ascii").strip()
    if observed != actual:
        parser.error("the graph changed after " + args.check + " observed it")
    receipt = {
        "schema_version": 2,
        "case_id": "GHQ-JS-001",
        "check_id": args.check,
        "checkout_sha": source_commit(Path.cwd(), (Path(__file__), PLAN, VAULT / "cases.md")),
        "run_id": run,
        "attempt": attempt,
        "case_plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "evidence_sha256": observed,
        "environment": {"os": "Linux", "runtime": args.runtime},
        "status": "pass",
    }
    args.destination.mkdir(exist_ok=True, parents=True)
    with (args.destination / (args.check + ".json")).open("x", encoding="utf-8") as output:
        json.dump(receipt, output, indent=2)
        output.write("\n")
    print(f"{args.check} observed graph SHA-256 {observed}")


if __name__ == "__main__":
    main()
