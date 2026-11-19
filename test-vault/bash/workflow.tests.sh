#!/usr/bin/env bash
set -euo pipefail

: "${GRAPHIFY_HQ_BART_WORKFLOW:?set the path to the pinned OBJ/MTL workflow}"
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
export GRAPHIFY_HQ_STEPS="$root/steps"
mkdir "$GRAPHIFY_HQ_STEPS"
"${GRAPHIFY_HQ_PYTHON:-python}" - <<'PY'
import os
from pathlib import Path

from yaml import safe_load

steps = safe_load(Path(os.environ["GRAPHIFY_HQ_BART_WORKFLOW"]).read_text(encoding="utf-8"))["jobs"]["verify"]["steps"]
names = (
    "Fetch the source commit and extract the pinned Graphify HQ kit",
    "Install hash-locked Graphify wheels",
    "Rebuild graph and verify the archived bytes and PR provenance",
)
selected = [next(step for step in steps if step.get("name") == name) for name in names]
assert [steps.index(step) for step in selected] == sorted(steps.index(step) for step in selected)
for filename, step in zip(("stage.sh", "install.sh", "check.sh"), selected, strict=True):
    assert step.get("shell") == "bash" and "if" not in step and "continue-on-error" not in step
    Path(os.environ["GRAPHIFY_HQ_STEPS"], filename).write_text(step["run"], encoding="utf-8")
PY

seed="$root/source"
remote="$root/fixture remote"
checkout="$root/worktree"
export RUNNER_TEMP="$root/staging"
export EVIDENCE_PATH='saved evidence'
git init -q --initial-branch=main "$seed"
commit() {
  git -C "$seed" add .
  git -C "$seed" -c user.name=Fixture -c user.email=fixture@example.invalid -c commit.gpgsign=false commit -qm "$1"
  git -C "$seed" rev-parse HEAD
}
printf 'application\n' > "$seed/README.md"
source=$(commit application)
mkdir -p "$seed/versions/v0.0.8"
printf 'pinned kit\n' > "$seed/versions/v0.0.8/requirements.txt"
TEMPLATE_COMMIT=$(commit template)
mkdir "$seed/candidate"
printf 'pinned verifier\n' > "$seed/candidate/github_provenance.py"
PROVENANCE_COMMIT=$(commit provenance)
export TEMPLATE_COMMIT PROVENANCE_COMMIT
printf 'new tip kit\n' > "$seed/versions/v0.0.8/requirements.txt"
printf 'new tip verifier\n' > "$seed/candidate/github_provenance.py"
tip=$(commit "branch tip")
git clone -q --bare "$seed" "$remote"
git clone -q --depth=1 "file://$remote" "$checkout"
mkdir "$checkout/$EVIDENCE_PATH"
printf 'prior graph\n' > "$checkout/$EVIDENCE_PATH/graph.json"
printf 'prior receipt\n' > "$checkout/$EVIDENCE_PATH/receipt.json"

manifest() {
  printf '{"source_commit": "%s"}\n' "$1" > "$checkout/$EVIDENCE_PATH/manifest.json"
}
hashes() {
  sha256sum "$checkout/$EVIDENCE_PATH/graph.json" "$checkout/$EVIDENCE_PATH/receipt.json"
}
before=$(hashes)
fresh_staging() {
  rm -rf -- "$RUNNER_TEMP"
  mkdir "$RUNNER_TEMP"
}
step() (
  cd "$checkout"
  bash --noprofile --norc -eo pipefail "$GRAPHIFY_HQ_STEPS/$1.sh"
)
must_fail() {
  if step "$1" > "$root/stdout" 2> "$root/stderr"; then
    printf 'Expected the %s workflow step to fail\n' "$1" >&2
    return 1
  fi
  [[ "$(hashes)" == "$before" ]]
}
expect_extracted() {
  printf 'pinned kit\n' | cmp - "$RUNNER_TEMP/versions/v0.0.8/requirements.txt"
  printf 'pinned verifier\n' | cmp - "$RUNNER_TEMP/candidate/github_provenance.py"
}

fresh_staging
manifest "$source"
if git -C "$checkout" cat-file -e "$source" 2>/dev/null; then
  printf 'The shallow checkout already contains the source test object\n' >&2
  exit 1
fi
step stage > "$root/identity"
expect_extracted
[[ "$(git -C "$checkout" cat-file -t "$source")" == "commit" ]]
grep -qx "HQ checkout SHA: $tip" "$root/identity"
grep -qx "Application source SHA: $source" "$root/identity"
[[ "$(hashes)" == "$before" ]]
echo 'PASS GHQ-SH-001 extracts bytes from distinct exact pins'

mkdir "$root/paths with spaces"
mv "$checkout" "$root/work tree"
checkout="$root/work tree"
before=$(hashes)
RUNNER_TEMP="$root/paths with spaces/new stage"
fresh_staging
step stage > "$root/quoted"
expect_extracted
[[ "$(hashes)" == "$before" ]]
echo 'PASS GHQ-SH-002 preserves literal paths in the checkout and staging'

fresh_staging
manifest ffffffffffffffffffffffffffffffffffffffff
must_fail stage
[[ -z "$(ls -A "$RUNNER_TEMP")" ]]
echo 'PASS GHQ-SH-003 stops at a missing SHA before extraction'

fresh_staging
manifest main
GIT_TRACE="$root/git-trace" must_fail stage
grep -Fq 'must pin a full source SHA' "$root/stderr"
[[ ! -s "$root/git-trace" && -z "$(ls -A "$RUNNER_TEMP")" ]]
echo 'PASS GHQ-SH-004 refuses malformed source pins before fetching'

manifest "$source"
mkdir "$root/bin"
cat > "$root/bin/tar" <<'SH'
#!/usr/bin/env bash
cat > /dev/null
SH
chmod +x "$root/bin/tar"
fresh_staging
PATH="$root/bin:$PATH" TEMPLATE_COMMIT="$source" must_fail stage
grep -Fq 'pathspec' "$root/stderr"
[[ -z "$(ls -A "$RUNNER_TEMP")" ]]
fresh_staging
rmdir "$RUNNER_TEMP"
touch "$RUNNER_TEMP"
must_fail stage
grep -Fq 'Not a directory' "$root/stderr"
echo 'PASS GHQ-SH-005 propagates both upstream archive and downstream tar failures'

export PIP_LOG="$root/pip-log"
cat > "$root/bin/python" <<'SH'
#!/usr/bin/env bash
printf '%s\n' "$@" >> "$PIP_LOG"
[[ "$3" != "$PIP_FAIL" ]]
SH
chmod +x "$root/bin/python"
fresh_staging
step stage > "$root/for-install"
PIP_FAIL=install PATH="$root/bin:$PATH" must_fail install
grep -qx -- '--require-hashes' "$PIP_LOG"
grep -qx -- '--no-deps' "$PIP_LOG"
grep -qx -- '--only-binary=:all:' "$PIP_LOG"
grep -Fqx -- "$RUNNER_TEMP/versions/v0.0.8/requirements.txt" "$PIP_LOG"
if grep -qx 'check' "$PIP_LOG"; then
  printf 'pip check ran despite an install failure\n' >&2
  exit 1
fi
: > "$PIP_LOG"
PIP_FAIL=check PATH="$root/bin:$PATH" must_fail install
grep -qx 'install' "$PIP_LOG"
grep -qx 'check' "$PIP_LOG"
echo 'PASS GHQ-SH-006 fails when either locked dependency step fails'

# Exercise the pinned final step using a deterministic provenance response and
# a sentry for the archive-check call. The ordinary evidence pair stays intact.
cat > "$RUNNER_TEMP/candidate/github_provenance.py" <<'PY'
import os

def verify_pull_request(repository, source, review):
    return {"pull_request": "https://github.com/" + os.environ["FIXTURE_PR_REPOSITORY"] + "/pull/1"}
PY
cat > "$RUNNER_TEMP/versions/v0.0.8/evidence_map.py" <<'PY'
import os
import sys
from pathlib import Path

assert sys.argv[-1] == "--check"
Path(os.environ["ARCHIVE_CHECK_MARKER"]).touch()
PY
export ARCHIVE_CHECK_MARKER="$root/checked"
export GITHUB_REPOSITORY=example/graphify
printf '{"source_commit":"%s","repository":"example/graphify","pull_request":{}}\n' "$source" > "$checkout/$EVIDENCE_PATH/manifest.json"
FIXTURE_PR_REPOSITORY=example/unrelated must_fail check
grep -q 'PR belongs to a different repository' "$root/stderr"
[[ ! -e "$ARCHIVE_CHECK_MARKER" ]]
FIXTURE_PR_REPOSITORY=example/graphify step check > "$root/repository-check"
[[ -f "$ARCHIVE_CHECK_MARKER" && "$(hashes)" == "$before" ]]
echo 'PASS GHQ-SH-031 rejects an unrelated PR repository before archive checking'
