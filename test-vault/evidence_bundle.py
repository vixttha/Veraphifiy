"""Encode the exact bytes shared by the producer, consumer, and transfer job."""

import argparse
import hashlib
import json
import os
from pathlib import Path

FILES = ("graph.json", "receipt.json", "source.txt")
HEADER = b"graphify-handoff-v1\n"


def encode_bundle(directory):
    parts = [HEADER]
    for name in FILES:
        data = (directory / name).read_bytes()
        parts.extend((str(len(data)).encode("ascii") + b"\n", data))
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
            if evidence.read_bytes() != expected:
                parser.error("transferred graph, receipt or source pin differs from the observed bundle")
        else:
            evidence.write_bytes(expected)
    except OSError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
