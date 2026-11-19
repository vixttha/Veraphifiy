import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { parseEvidenceObject, readBytes } from "./inspect-evidence.mjs";

const handoff = process.argv[2];
assert.ok(handoff, "Pass the directory containing the downloaded Vault artifact");
const expected = parseEvidenceObject(
  readBytes(join(handoff, "veraphifiy-archive-expectations.json"), 4096), "archive expectations",
);
const entry = fileURLToPath(new URL("../../veraphifiy.mjs", import.meta.url));
assert.equal(expected.project, "example/graphify-fixture");
assert.equal(expected.feature, "feature:export");
assert.deepEqual(expected.versions.map(item => [item.version, item.line]), [["v1.0.0", 3], ["v1.1.0", 4]]);
assert.notEqual(expected.versions[0].source, expected.versions[1].source);

for (const { version, source, line } of expected.versions) {
  const args = [entry, "lookup", "--archive", join(handoff, "veraphifiy-archive"),
    "--project", expected.project, "--version", version, "--source", source,
    "--feature", expected.feature];
  const result = JSON.parse(execFileSync(process.execPath, args, { encoding: "utf8", timeout: 15_000 }));
  assert.equal(result.project, expected.project);
  assert.equal(result.version, version);
  assert.equal(result.source, source);
  assert.deepEqual(result.citations, [{ path: "src/feature.py", line }]);
  console.log(`Replayed ${result.project} ${version} at ${source}, citation src/feature.py:${line}`);
}
