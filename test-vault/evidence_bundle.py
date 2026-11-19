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


def write_observation(directory, producer):
    observation = {
        "run_id": os.environ.get("GITHUB_RUN_ID", ""),
        "attempt": os.environ.get("GITHUB_RUN_ATTEMPT", ""),
        "bundle_sha256": hashlib.sha256(encode_bundle(directory)).hexdigest(),
    }
    (directory / f"{producer}.observation.json").write_text(json.dumps(observation) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    evidence = args.directory / "evidence.bin"
    try:
        expected = encode_bundle(args.directory)
        if args.check:
            if read_part(evidence, PROFILE["max_bundle_bytes"]) != expected:
                parser.error("transferred graph, receipt, source pin or source bytes differs from the observed bundle")
        else:
            evidence.write_bytes(expected)
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
