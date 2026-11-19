"""Encode the exact bytes shared by the producer, consumer, and transfer job."""

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

PROFILE_PATH = Path(__file__).with_name("handoff-profile.json")
PROFILE = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
HEADER = b"graphify-handoff-v2\n"
CHECKS = {"python-build": "python", "node-consume": "node"}


def read_part(path, maximum, remaining=None):
    with path.open("rb") as stream:
        details = os.fstat(stream.fileno())
        size = details.st_size
        if not stat.S_ISREG(details.st_mode) or size > maximum:
            raise ValueError(f"{path.name} exceeds its byte budget or is not a regular file")
        if remaining is not None and size + len(str(size)) + 1 > remaining:
            raise ValueError(f"{path.name} exceeds the remaining handoff byte budget")
        data = stream.read(size + 1)
        if len(data) != size:
            raise ValueError(f"{path.name} changed size during bounded read")
        return data


def encode_bundle(directory, *, limits=None, maximum=PROFILE["max_bundle_bytes"]):
    limits = {} if limits is None else limits
    parts = [HEADER]
    remaining = maximum - len(HEADER)
    for name, default in PROFILE["files"].items():
        data = read_part(directory / name, limits.get(name, default), remaining)
        prefix = str(len(data)).encode("ascii") + b"\n"
        parts.extend((prefix, data))
        remaining -= len(prefix) + len(data)
    return b"".join(parts)


def check_observation(directory, check, run, attempt, digest):
    path = directory / (CHECKS[check] + ".observation.json")
    observation = json.loads(read_part(path, 8192))
    if not isinstance(observation, dict) or set(observation) != {
        "check_id", "run_id", "attempt", "bundle_sha256",
    }:
        raise ValueError("invalid handoff observation")
    if observation["check_id"] != check:
        raise ValueError("handoff observation belongs to a different check")
    if (observation["run_id"], observation["attempt"]) != (run, attempt):
        raise ValueError("handoff observation is for a different run or attempt")
    if observation["bundle_sha256"] != digest:
        raise ValueError("bundle changed after " + check + " observed it")


def write_observation(directory, producer):
    check, = (key for key, name in CHECKS.items() if name == producer)
    observation = {
        "check_id": check,
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "bundle_sha256": hashlib.sha256(encode_bundle(directory)).hexdigest(),
    }
    (directory / f"{producer}.observation.json").write_text(json.dumps(observation) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--check-observations", action="store_true")
    args = parser.parse_args()
    evidence = args.directory / "evidence.bin"
    if args.check_observations and not args.check:
        parser.error("--check-observations requires --check")
    try:
        expected = encode_bundle(args.directory)
        if args.check:
            if read_part(evidence, PROFILE["max_bundle_bytes"]) != expected:
                parser.error("transferred graph, receipt, source pin or source bytes differs from the observed bundle")
            if args.check_observations:
                digest = hashlib.sha256(expected).hexdigest()
                for check in CHECKS:
                    check_observation(args.directory, check, os.environ["GITHUB_RUN_ID"],
                                      os.environ["GITHUB_RUN_ATTEMPT"], digest)
        else:
            evidence.write_bytes(expected)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
