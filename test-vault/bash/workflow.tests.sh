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
printf '#!/bin/sh\nexit 0\n' > "$seed/versions/v0.0.8/fixture-tool"
chmod +x "$seed/versions/v0.0.8/fixture-tool"
TEMPLATE_COMMIT=$(commit template)
mkdir "$seed/candidate"
printf 'pinned verifier\n' > "$seed/candidate/github_provenance.py"
PROVENANCE_COMMIT=$(commit provenance)
export TEMPLATE_COMMIT PROVENANCE_COMMIT
printf 'new tip kit\n' > "$seed/versions/v0.0.8/requirements.txt"
chmod -x "$seed/versions/v0.0.8/fixture-tool"
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

if PIP_FAIL=install PATH="$root/bin:$PATH" step install | tee "$root/dependency-output"; then
  printf 'Install failed but its CI-style logging pipeline reported success\n' >&2
  exit 1
fi
[[ "$(hashes)" == "$before" ]]
echo 'PASS GHQ-SH-010 preserves a failure when the log sink succeeds'

fresh_staging
step stage > "$root/archive-mode"
original_mode=$(git -C "$checkout" ls-tree "$TEMPLATE_COMMIT" versions/v0.0.8/fixture-tool)
tip_mode=$(git -C "$checkout" ls-tree "$tip" versions/v0.0.8/fixture-tool)
[[ "$original_mode" == 100755* && "$tip_mode" == 100644* ]]
[[ "$(cut -d' ' -f3 <<< "$original_mode")" == "$(cut -d' ' -f3 <<< "$tip_mode")" ]]
[[ -x "$RUNNER_TEMP/versions/v0.0.8/fixture-tool" ]]
echo 'PASS GHQ-SH-018 preserves the pinned file mode for identical blobs'

if PIP_FAIL=unused PATH="$root/bin:$PATH" step install | tee "$RUNNER_TEMP" > "$root/bad-sink" 2> "$root/sink-error"; then
  printf 'A failed tee destination yielded pipeline success\n' >&2
  exit 1
fi
grep -Fq 'Is a directory' "$root/sink-error"
PIP_FAIL=unused PATH="$root/bin:$PATH" step install | tee "$root/writable-sink" > /dev/null
echo 'PASS GHQ-SH-022 propagates a log write failure from an otherwise successful step'

fresh_staging
TEMPLATE_COMMIT="$tip" PROVENANCE_COMMIT="$source" must_fail stage
grep -Fq 'pathspec' "$root/stderr"
[[ -s "$RUNNER_TEMP/versions/v0.0.8/requirements.txt" && ! -e "$RUNNER_TEMP/candidate/github_provenance.py" ]]
grep -qx 'new tip kit' "$RUNNER_TEMP/versions/v0.0.8/requirements.txt"
step stage > "$root/retry"
expect_extracted
echo 'PASS GHQ-SH-032 retries staged inputs safely after a second extraction failure'

for mode in false true; do
  textured="$root/crlf-$mode"
  git -c core.autocrlf="$mode" clone -q "file://$remote" "$textured"
  mkdir "$textured/$EVIDENCE_PATH"
  (
    checkout="$textured"
    manifest "$source"
    RUNNER_TEMP="$root/staged-$mode"
    mkdir "$RUNNER_TEMP"
    step stage > "$root/text-conversion-$mode"
    git -C "$checkout" show "$TEMPLATE_COMMIT:versions/v0.0.8/requirements.txt" |
      cmp - "$RUNNER_TEMP/versions/v0.0.8/requirements.txt"
    git -C "$checkout" show "$PROVENANCE_COMMIT:candidate/github_provenance.py" |
      cmp - "$RUNNER_TEMP/candidate/github_provenance.py"
  )
done
if cmp -s "$root/crlf-false/README.md" "$root/crlf-true/README.md"; then
  printf 'The fixture did not produce distinct working-tree line endings\n' >&2
  exit 1
fi
cmp "$root/staged-false/versions/v0.0.8/requirements.txt" "$root/staged-true/versions/v0.0.8/requirements.txt"
echo 'PASS GHQ-SH-029 stages Git objects independently of worktree line-ending conversion'

before_parallel="$RUNNER_TEMP"
for lane in abandoned continuing; do
  git clone -q "file://$remote" "$root/parallel-$lane"
  mkdir "$root/parallel-$lane/$EVIDENCE_PATH" "$root/stage-$lane"
done
(
  checkout="$root/parallel-abandoned"
  manifest "$source"
  RUNNER_TEMP="$root/stage-abandoned" step stage > "$root/abandoned.log"
  touch "$root/abandoned-ready"
  exec sleep 30
) &
abandoned=$!
(
  checkout="$root/parallel-continuing"
  manifest "$tip"
  RUNNER_TEMP="$root/stage-continuing" TEMPLATE_COMMIT="$tip" step stage > "$root/continuing.log"
) &
continuing=$!
for attempt in {1..100}; do
  [[ -f "$root/abandoned-ready" ]] && break
  if ! kill -0 "$abandoned" 2>/dev/null; then break; fi
  sleep 0.05
done
if [[ ! -f "$root/abandoned-ready" ]]; then
  kill "$abandoned" 2>/dev/null || true
  wait "$abandoned" || true
  wait "$continuing" || true
  exit 1
fi
kill "$abandoned"
wait "$abandoned" 2>/dev/null || true
wait "$continuing"
rm -rf -- "$root/stage-abandoned"
grep -qx 'new tip kit' "$root/stage-continuing/versions/v0.0.8/requirements.txt"
grep -qx "Application source SHA: $source" "$root/abandoned.log"
grep -qx "Application source SHA: $tip" "$root/continuing.log"
[[ "$RUNNER_TEMP" == "$before_parallel" && "$(hashes)" == "$before" ]]
echo 'PASS GHQ-SH-012 keeps simultaneous staging and logs separate after interruption'

export VAULT_WHEELHOUSE="$root/wheels"
mkdir -p "$VAULT_WHEELHOUSE"
"${GRAPHIFY_HQ_PYTHON:-python}" - <<'PY'
import os
from pathlib import Path
from zipfile import ZipFile

root = Path(os.environ["VAULT_WHEELHOUSE"])
for name, version, extra in (
    ("vault_dependency", "0.1", ""),
    ("vault_probe", "0.1", "Requires-Dist: vault_dependency==0.1\n"),
    ("vault_future", "0.1", "Requires-Python: >=99\n"),
):
    stem = f"{name}-{version}"
    metadata = f"{stem}.dist-info"
    contents = {
        f"{name}.py": "# isolated dependency fixture\n",
        f"{metadata}/WHEEL": "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{metadata}/METADATA": f"Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n{extra}\n",
    }
    contents[f"{metadata}/RECORD"] = "".join(f"{path},,\n" for path in [*contents, f"{metadata}/RECORD"])
    with ZipFile(root / f"{stem}-py3-none-any.whl", "w") as output:
        for path, value in contents.items():
            output.writestr(path, value)
PY
export PIP_NO_INDEX=1 PIP_FIND_LINKS="$VAULT_WHEELHOUSE" PIP_DISABLE_PIP_VERSION_CHECK=1
"${GRAPHIFY_HQ_PYTHON:-python}" -m venv "$root/dependencies"
export PATH="$root/dependencies/bin:$PATH"
requirements="$RUNNER_TEMP/versions/v0.0.8/requirements.txt"
entry() {
  local name=$1 digest
  digest=$(sha256sum "$VAULT_WHEELHOUSE/$name-0.1-py3-none-any.whl")
  printf '%s==0.1 --hash=sha256:%s\n' "$name" "${digest%% *}"
}

entry vault_probe > "$requirements"
must_fail install
grep -Eiq 'vault.probe.*requires vault.dependency|vault.dependency.*not installed' "$root/stdout" "$root/stderr"
entry vault_dependency >> "$requirements"
step install > "$root/complete-wheel-set"
grep -Fq 'No broken requirements found' "$root/complete-wheel-set"
echo 'PASS GHQ-SH-020 lets the real dependency check reject an incomplete lock'

entry vault_future > "$requirements"
must_fail install
grep -Eiq 'requires a different Python|not in.*>=99' "$root/stdout" "$root/stderr"
entry vault_probe > "$requirements"
entry vault_dependency >> "$requirements"
step install > "$root/compatible-wheel-set"
echo 'PASS GHQ-SH-025 distinguishes a compatible lock from an incompatible interpreter'

entry vault_dependency > "$requirements"
wheel="$VAULT_WHEELHOUSE/vault_dependency-0.1-py3-none-any.whl"
cp "$wheel" "$root/original-wheel.whl"
printf 'changed on-disk bytes\n' >> "$wheel"
PIP_FORCE_REINSTALL=1 must_fail install
grep -Eiq 'do not match the hashes|expected sha256' "$root/stdout" "$root/stderr"
cp "$root/original-wheel.whl" "$wheel"
PIP_FORCE_REINSTALL=1 step install > "$root/restored-wheel"
grep -Fq 'No broken requirements found' "$root/restored-wheel"
echo 'PASS GHQ-SH-009 rejects a changed wheel against a fixed hash'
