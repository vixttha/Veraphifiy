"""Write one v2 Lydite receipt using the digest observed by a passing suite."""

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path

from evidence_bundle import PROFILE_PATH, encode_bundle, read_part
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
    if not args.runtime.strip():
        parser.error("--runtime must be nonempty")

    run = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not RUN_ID.fullmatch(run) or not RUN_ID.fullmatch(attempt):
        parser.error("set GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT to positive decimal strings")
    try:
        actual = hashlib.sha256(encode_bundle(args.handoff)).hexdigest()
        observation_file = args.handoff / (CHECKS[args.check] + ".observation.json")
        observation = json.loads(read_part(observation_file, 8192))
    except (OSError, ValueError) as error:
        parser.error(f"cannot read observed bundle: {error}")
    if not isinstance(observation, dict) or observation.keys() != {"run_id", "attempt", "bundle_sha256"}:
        parser.error("invalid handoff observation")
    if (observation["run_id"], observation["attempt"]) != (run, attempt):
        parser.error("handoff observation is for a different run or attempt")
    if observation["bundle_sha256"] != actual:
        parser.error("bundle changed after " + args.check + " observed it")
    receipt = {
        "schema_version": 2,
        "case_id": "GHQ-JS-001",
        "check_id": args.check,
        "checkout_sha": source_commit(Path.cwd(), (Path(__file__), PLAN, VAULT / "cases.md",
                                                    VAULT / "evidence_bundle.py", PROFILE_PATH)),
        "run_id": run,
        "attempt": attempt,
        "case_plan_sha256": hashlib.sha256(PLAN.read_bytes()).hexdigest(),
        "evidence_sha256": actual,
        "environment": {"os": "Linux", "runtime": args.runtime},
        "status": "pass",
    }
    args.destination.mkdir(exist_ok=True, parents=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.destination, delete=False) as output:
            temporary = Path(output.name)
            json.dump(receipt, output, indent=2)
            output.write("\n")
        os.link(temporary, args.destination / (args.check + ".json"))
    except OSError as error:
        parser.error(f"cannot publish receipt: {error}")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"{args.check} observed bundle SHA-256 {actual}")


if __name__ == "__main__":
    main()
