import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseEvidenceObject, readBytes } from "./inspect-evidence.mjs";

const handoff = process.argv[2];
assert.ok(handoff, "Pass the directory containing the downloaded Vault artifact");
if (process.argv[3] === "--actions") {
  const context = parseEvidenceObject(readBytes(join(handoff, "evidence-context.json"), 4096), "evidence context");
  for (const [field, env] of Object.entries({
    checkout_sha: "GITHUB_SHA", github_event_name: "GITHUB_EVENT_NAME", github_ref: "GITHUB_REF",
    github_workflow_ref: "GITHUB_WORKFLOW_REF", github_workflow_sha: "GITHUB_WORKFLOW_SHA",
    github_run_id: "GITHUB_RUN_ID", github_run_attempt: "GITHUB_RUN_ATTEMPT",
  })) {
    assert.ok(process.env[env], `Missing runner context ${env}`);
    assert.equal(context[field], process.env[env], `Archive handoff context mismatch: ${field}`);
  }
  console.log(`Verified handoff context for ${context.github_event_name} run ${context.github_run_id}, attempt ${context.github_run_attempt}, at ${context.checkout_sha}`);
}
const expected = parseEvidenceObject(
  readBytes(join(handoff, "veraphifiy-archive-expectations.json"), 4096), "archive expectations",
);
const entry = fileURLToPath(new URL("../../veraphifiy.mjs", import.meta.url));
assert.equal(expected.project, "example/graphify-fixture");
assert.equal(expected.feature, "feature:export");
assert.deepEqual(expected.versions.map(item => [item.version, item.line]), [["v1.0.0", 3], ["v1.1.0", 4]]);
assert.notEqual(expected.versions[0].source, expected.versions[1].source);

for (const { version, source, line, archive_sha256 } of expected.versions) {
  assert.match(archive_sha256, /^[a-f0-9]{64}$/);
  const args = [entry, "lookup", "--archive", join(handoff, "veraphifiy-archive"),
    "--version", version, "--source", source,
    "--archive-sha256", archive_sha256, "--feature", expected.feature];
  const replay = (project) => JSON.parse(execFileSync(process.execPath, [...args, "--project", project],
    { encoding: "utf8", timeout: 15_000 }));
  const result = replay(expected.project);
  assert.equal(result.project, expected.project);
  assert.equal(result.version, version);
  assert.equal(result.source, source);
  assert.equal(result.archive_sha256, archive_sha256);
  assert.deepEqual(result.citations, [{ path: "src/feature.py", line }]);
  console.log(`Replayed ${result.project} ${version} at ${source}, citation src/feature.py:${line}`);
  const alias = expected.project.toUpperCase();
  assert.notEqual(alias, expected.project);
  assert.deepEqual(replay(alias), result);
  console.log(`Verified case-only project alias for ${version}`);
}
