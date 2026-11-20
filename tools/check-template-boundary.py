"""Check the product-side tree in the Veraphify boundary pilot."""

import subprocess
import sys
import unicodedata
from pathlib import Path, PurePosixPath


PILOT_ONLY = ("tools/check-template-boundary.py", ".github/workflows/template-boundary-pilot.yml")
TEMPLATE_HEADS = {"lydite-test-vault", "graphify-hq-test-vault", "graphify-hq-brand-identity"}
WORKSPACE_NAMES = TEMPLATE_HEADS | {"brand-identity", "test-vault", "brand identity", "test vault"}
MARKERS = (("01-strategy", "creative-decision.json"), ("test-vault", "cases.md"),
           ("python", "test_builder.py"), ("docs", "veraphify-mechanical-proof.md"))


def git(*args):
    return subprocess.check_output(["git", *args])


def normalized(value):
    return unicodedata.normalize("NFKC", value).casefold()


def main():
    base, candidate, head_ref, summary = sys.argv[1:]
    tree = git("rev-parse", f"{candidate}^{{tree}}").decode().strip()
    violations = []
    if normalized(head_ref) in TEMPLATE_HEADS:
        violations.append(f"Template source branch {head_ref!r} targets the product pilot.")
    for raw in git("ls-tree", "-r", "-z", "--name-only", candidate).split(b"\0"):
        if not raw:
            continue
        path = raw.decode("utf-8", "surrogateescape")
        parts = PurePosixPath(normalized(path)).parts
        if any(part in WORKSPACE_NAMES for part in parts) or parts[-2:] in MARKERS:
            violations.append(f"Workspace path {path!r}")
    changed_policy = git("diff", "--name-only", base, candidate, "--", *PILOT_ONLY).decode().strip()
    if changed_policy:
        violations.append("The proposed tree changes the pilot workflow or checker.")
    verdict = "FAIL" if violations else "PASS"
    report = [
        f"Boundary verdict: {verdict}",
        f"Base: {base}",
        f"Candidate: {candidate}",
        f"Candidate tree: {tree}",
        f"Head ref: {head_ref!r}",
        *violations,
    ]
    print("\n".join(report))
    with Path(summary).open("a", encoding="utf-8") as output:
        output.write("\n".join(report) + "\n")
    return int(bool(violations))


if __name__ == "__main__":
    sys.exit(main())
