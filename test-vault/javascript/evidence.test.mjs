import assert from "node:assert/strict";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { implementationLocation, inspectEvidence, sha256 } from "./inspect-evidence.mjs";

const handoff = process.env.GRAPHIFY_HQ_HANDOFF;
assert.ok(handoff, "Set GRAPHIFY_HQ_HANDOFF to the fresh Python build directory");
const source = readFileSync(join(handoff, "source.txt"), "utf8").trim();
const feature = "feature:export";
const anchor = "implemented_in:src/feature.py:L3";
const graphFile = "graph.json";
const receiptFile = "receipt.json";

function copy(t) {
  const root = mkdtempSync(join(tmpdir(), "graphify-consumer-"));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  cpSync(handoff, root, { recursive: true });
  return root;
}

function change(dir, filename, mutate) {
  const file = join(dir, filename);
  const value = JSON.parse(readFileSync(file, "utf8"));
  mutate(value);
  writeFileSync(file, JSON.stringify(value));
}

function changeGraph(dir, mutate) {
  change(dir, graphFile, mutate);
  change(dir, receiptFile, (receipt) => {
    receipt.graph_sha256 = sha256(readFileSync(join(dir, graphFile)));
  });
}

test("GHQ-JS-001 accepts the fresh Python graph and its receipt", () => {
  const graph = inspectEvidence(handoff, source);
  assert.ok(graph.nodes.has(feature));
  assert.ok(graph.nodes.has("source:" + source));
  writeFileSync(join(handoff, "node.sha256"), graph.digest + "\n");
});

test("GHQ-JS-002 rejects a receipt for a different source", (t) => {
  const dir = copy(t);
  change(dir, receiptFile, (receipt) => { receipt.source_commit = "f".repeat(40); });
  assert.throws(() => inspectEvidence(dir, source), /Source commit mismatch/);
});

test("GHQ-JS-003 hashes the original bytes, including whitespace", (t) => {
  const dir = copy(t);
  const path = join(dir, graphFile);
  writeFileSync(path, readFileSync(path, "utf8") + "\n");
  assert.throws(() => inspectEvidence(dir, source), /Graph digest mismatch/);
});

test("GHQ-JS-004 rejects dangling endpoints even with a fresh digest", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.links[0].target = "absent"; });
  assert.throws(() => inspectEvidence(dir, source), /Missing edge endpoint/);
});

test("GHQ-JS-005 rejects duplicate IDs even with consistent counts", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.nodes.push(graph.nodes[0]); });
  change(dir, receiptFile, (receipt) => { receipt.nodes++; });
  assert.throws(() => inspectEvidence(dir, source), /Duplicate node ID/);
});

test("GHQ-JS-006 requires both companion files", (t) => {
  for (const filename of [graphFile, receiptFile]) {
    const dir = copy(t);
    rmSync(join(dir, filename));
    assert.throws(() => inspectEvidence(dir, source), { message: "Cannot read " + filename + ": ENOENT" });
  }
});

test("GHQ-JS-007 identifies which file contains invalid JSON", (t) => {
  for (const filename of [graphFile, receiptFile]) {
    const dir = copy(t);
    writeFileSync(join(dir, filename), "{");
    assert.throws(() => inspectEvidence(dir, source), { message: "Invalid JSON in " + filename });
  }
});

test("GHQ-JS-008 checks schema and array shape before using graph fields", (t) => {
  for (const schema of [2, undefined]) {
    const dir = copy(t);
    change(dir, receiptFile, (receipt) => { receipt.schema_version = schema; });
    assert.throws(() => inspectEvidence(dir, source), /Unsupported receipt schema/);
  }
  for (const key of ["nodes", "links"]) {
    const dir = copy(t);
    changeGraph(dir, (graph) => { graph[key] = {}; });
    assert.throws(() => inspectEvidence(dir, source), /Invalid graph shape/);
  }
});

test("GHQ-JS-009 checks both node and edge counts", (t) => {
  for (const [key, message] of [["nodes", /Node count mismatch/], ["edges", /Edge count mismatch/]]) {
    const dir = copy(t);
    change(dir, receiptFile, (receipt) => { receipt[key]++; });
    assert.throws(() => inspectEvidence(dir, source), message);
  }
});

test("GHQ-JS-010 requires boolean MCP verification", (t) => {
  for (const value of [false, undefined, "true"]) {
    const dir = copy(t);
    change(dir, receiptFile, (receipt) => { receipt.mcp_verified = value; });
    assert.throws(() => inspectEvidence(dir, source), /lacks MCP verification/);
  }
});

test("GHQ-JS-011 verifies each feature's evidence counts and identity", (t) => {
  const badCount = copy(t);
  change(badCount, receiptFile, (receipt) => { receipt.feature_links[feature].implemented_in++; });
  assert.throws(() => inspectEvidence(badCount, source), /Feature summary mismatch/);
  const unknown = copy(t);
  change(unknown, receiptFile, (receipt) => {
    receipt.feature_links["feature:unknown"] = receipt.feature_links[feature];
    delete receipt.feature_links[feature];
  });
  assert.throws(() => inspectEvidence(unknown, source), /Feature summary mismatch/);
});

test("GHQ-JS-012 resolves a raw citation and withholds an incomplete target", (t) => {
  const checked = inspectEvidence(handoff, source);
  const expected = { path: "src/feature.py", line: 3 };
  assert.deepEqual(implementationLocation(checked, feature, anchor), expected);
  assert.deepEqual(implementationLocation(checked, "feature:preview", anchor), expected);
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.nodes.find(({ id }) => id === anchor).source_location = null; });
  assert.equal(implementationLocation(inspectEvidence(dir, source), feature, anchor), null);
});
