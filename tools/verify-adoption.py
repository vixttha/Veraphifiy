"""Verify a pinned public adopter through Graphify and the Veraphify archive CLI."""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

root = Path.cwd()
run = Path(os.environ["RUNNER_TEMP"])
source = os.environ["ADOPTER_SHA"]
veraphify = os.environ["VERAPHIFY_SHA"]
producer = os.environ["PRODUCER_SHA"]
repository = os.environ["GITHUB_REPOSITORY"]
path = os.environ["ADOPTER_FILE"]
anchor = os.environ["ADOPTER_ANCHOR"]
worktree = root / "adopter"
proof = run / "veraphify-adoption"
proof.mkdir()

for directory, expected in (("adopter", source), ("veraphify", veraphify), ("producer", producer)):
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError(f"Expected a full Git SHA for {directory}")
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root / directory, text=True).strip()
    if actual != expected:
        raise ValueError(f"{directory} checkout {actual} differs from {expected}")

blob = subprocess.check_output(["git", "show", f"{source}:{path}"], cwd=worktree)
lines = [i for i, line in enumerate(blob.decode("utf-8").split("\n"), 1) if anchor and anchor in line]
if len(lines) != 1:
    raise ValueError(f"Expected one implementation anchor in {path}, found {len(lines)}")
manifest = run / "veraphify-adoption-manifest.json"
manifest.write_text(json.dumps({
    "repository": repository,
    "source_commit": source,
    "title": "Veraphify v0.0.9 adopter evidence",
    "source_files": [path],
    "features": [{
        "id": "adoption-check",
        "label": "Pinned implementation citation",
        "implemented_in": [{"path": path, "anchor": anchor}],
    }],
}), encoding="utf-8")
kit = root / "producer/versions/v0.0.8/evidence_map.py"
evidence = run / "veraphify-graph"
subprocess.run(["python", str(kit), str(manifest), str(evidence)], cwd=worktree, check=True)
receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
if receipt["source_commit"] != source or not receipt["mcp_verified"]:
    raise ValueError("Graphify did not verify the selected source")

cli = root / "veraphify/veraphifiy.mjs"
archive = run / "veraphify-local-archive"
version = "v0.0.0.1"
identity = ["--archive", str(archive), "--project", repository, "--version", version, "--source", source]

def invoke(command, *options):
    output = subprocess.check_output(["node", str(cli), command, *identity, *options], text=True)
    return json.loads(output)

imported = invoke("import", "--checkout", str(worktree), "--evidence", str(evidence))
entries = list(archive.glob("*.json"))
if len(entries) != 1:
    raise ValueError("Expected exactly one archive entry")
digest = hashlib.sha256(entries[0].read_bytes()).hexdigest()
if imported["archive_sha256"] != digest or imported["veraphifiy_version"] != "v0.0.9":
    raise ValueError("Archive digest or CLI version differs")
pin = ("--archive-sha256", digest)
verified = invoke("verify", *pin)
if verified != imported:
    raise ValueError("Independent archive verification differs from import")
lookup = invoke("lookup", *pin, "--feature", "feature:adoption-check")
if lookup != {**verified, "feature": "feature:adoption-check", "citations": [{"path": path, "line": lines[0]}]}:
    raise ValueError(f"Unexpected implementation citation: {lookup}")

report = {
    "caller_repository": repository,
    "caller_ref": os.environ["GITHUB_REF"],
    "caller_sha": os.environ["GITHUB_SHA"],
    "run_id": os.environ["GITHUB_RUN_ID"],
    "run_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
    "veraphify_checkout": veraphify,
    "graphify_producer_checkout": producer,
    "graphify_mcp_verified": receipt["mcp_verified"],
    "archived_lookup": lookup,
}
(proof / "adoption.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
message = f"Veraphify v0.0.9 verified {repository}${{source} at {path}:{lines[0]}"
print(message)
with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
    print(message, file=summary)
