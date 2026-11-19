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
  assert.deepEqual(readFileSync(join(handoff, "source.txt")), Buffer.from(source + "\n", "ascii"));
  writeFileSync(join(handoff, "node.sha256"), graph.digest + "\n");
  writeFileSync(join(handoff, "node.observation.json"), JSON.stringify({
    run_id: process.env.GITHUB_RUN_ID ?? "",
    attempt: process.env.GITHUB_RUN_ATTEMPT ?? "",
    bundle_sha256: graph.bundleDigest,
  }) + "\n");
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

test("GHQ-JS-013 rejects ambiguous JSON keys even when the last value is valid", (t) => {
  for (const key of ["source_commit", "source_\\u0063ommit"]) {
    const dir = copy(t);
    const path = join(dir, receiptFile);
    const original = readFileSync(path, "utf8");
    writeFileSync(path, '{"' + key + '":"different",' + original.trimStart().slice(1));
    assert.throws(() => inspectEvidence(dir, source), /Duplicate JSON key in receipt.json/);
  }
});

test("GHQ-JS-014 rejects invalid UTF-8 in a graph with a matching digest", (t) => {
  const dir = copy(t);
  const path = join(dir, graphFile);
  const raw = Buffer.from(readFileSync(path, "utf8").replace("Export evidence", "Export é"));
  raw[raw.indexOf(Buffer.from("é"))] = 0xff;
  writeFileSync(path, raw);
  change(dir, receiptFile, (receipt) => { receipt.graph_sha256 = sha256(raw); });
  assert.throws(() => inspectEvidence(dir, source), /Invalid UTF-8 in graph.json/);
});

test("GHQ-JS-015 binds topology to the requested source root", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => {
    const original = "source:" + source;
    const replacement = "source:" + "f".repeat(40);
    graph.nodes.find((node) => node.id === original).id = replacement;
    for (const edge of graph.links) {
      if (edge.source === original) edge.source = replacement;
    }
  });
  assert.throws(() => inspectEvidence(dir, source), /Source root mismatch/);
});

test("GHQ-JS-016 reconciles inventory with actual file nodes", (t) => {
  const dir = copy(t);
  change(dir, receiptFile, (receipt) => { receipt.source_files = ["notes.md"]; });
  assert.throws(() => inspectEvidence(dir, source), /Source inventory does not match/);
});

test("GHQ-JS-017 rejects a repeated logical edge with matching graph counts", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.links.push(graph.links.find((edge) => edge.relation === "contains_feature")); });
  change(dir, receiptFile, (receipt) => { receipt.edges++; });
  assert.throws(() => inspectEvidence(dir, source), /Duplicate evidence edge/);
});

test("GHQ-JS-018 requires the directed simple-graph contract", (t) => {
  for (const [key, value] of [["directed", false], ["multigraph", true]]) {
    const dir = copy(t);
    changeGraph(dir, (graph) => { graph[key] = value; });
    assert.throws(() => inspectEvidence(dir, source), /Expected a directed simple graph/);
  }
});

test("GHQ-JS-019 requires valid digests for inventoried and cited files", (t) => {
  for (const [path, digest] of [["src/feature.py", undefined], ["notes.md", "g".repeat(64)]]) {
    const dir = copy(t);
    change(dir, receiptFile, (receipt) => { receipt.source_sha256[path] = digest; });
    assert.throws(() => inspectEvidence(dir, source), /Invalid or missing source digest/);
  }
});

test("GHQ-JS-020 rejects unknown relation names", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.links[0].relation = "unrelated"; });
  assert.throws(() => inspectEvidence(dir, source), /Unsupported evidence relation/);
});

test("GHQ-JS-021 binds the expected repository and graph scope", (t) => {
  const expected = { repository: "example/graphify-fixture" };
  assert.ok(inspectEvidence(handoff, source, expected));
  assert.throws(() => inspectEvidence(handoff, source, { repository: "example/other" }), /scope or repository mismatch/);
  const dir = copy(t);
  change(dir, receiptFile, (receipt) => { receipt.scope = "unrelated"; });
  assert.throws(() => inspectEvidence(dir, source, expected), /scope or repository mismatch/);
});

test("GHQ-JS-022 matches each inventory anchor with its actual file", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => {
    graph.links.find((edge) => edge.relation === "located_in").target = feature;
  });
  assert.throws(() => inspectEvidence(dir, source), /Invalid located_in evidence edge/);
});

test("GHQ-JS-023 rejects features without source-root attachments", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => {
    graph.links = graph.links.filter((edge) => edge.relation !== "contains_feature" || edge.target !== feature);
  });
  change(dir, receiptFile, (receipt) => { receipt.edges--; });
  assert.throws(() => inspectEvidence(dir, source), /Missing source-root attachment/);
});

test("GHQ-JS-024 supports zero-feature exports and checks their counts", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => {
    graph.nodes = graph.nodes.filter((node) => node.id.startsWith("source:"));
    graph.links = [];
  });
  change(dir, receiptFile, (receipt) => {
    Object.assign(receipt, { nodes: 1, edges: 0, feature_links: {}, source_files: [], source_sha256: {} });
  });
  assert.equal(inspectEvidence(dir, source).nodes.size, 1);
  change(dir, receiptFile, (receipt) => { receipt.nodes++; });
  assert.throws(() => inspectEvidence(dir, source), /Node count mismatch/);
});

function replaceCitationPath(graph, path) {
  return {
    ...graph,
    nodes: new Map(graph.nodes).set(anchor, { ...graph.nodes.get(anchor), source_file: path }),
    links: graph.links.map((edge) => edge.target === anchor ? { ...edge, source_file: path } : edge),
  };
}

test("GHQ-JS-025 requires a canonical repository citation path", () => {
  const graph = inspectEvidence(handoff, source);
  for (const path of ["../src/feature.py", "src//feature.py", ".git/config"]) {
    assert.equal(implementationLocation(replaceCitationPath(graph, path), feature, anchor), null);
  }
  assert.deepEqual(implementationLocation(graph, feature, anchor), { path: "src/feature.py", line: 3 });
});

test("GHQ-JS-026 checks the category of implementation targets", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.nodes.find((node) => node.id === anchor).file_type = "concept"; });
  assert.throws(() => inspectEvidence(dir, source), /Invalid implementation target category/);
});

test("GHQ-JS-027 rejects mismatched template versions", (t) => {
  const dir = copy(t);
  const expected = { templateVersion: "v0.0.8" };
  assert.ok(inspectEvidence(dir, source, expected));
  change(dir, receiptFile, (receipt) => { receipt.template_version = "v0.0.9"; });
  assert.throws(() => inspectEvidence(dir, source, expected), /Evidence template version mismatch/);
});

test("GHQ-JS-028 rejects numbers that overflow during JSON decoding", (t) => {
  const dir = copy(t);
  const path = join(dir, graphFile);
  const raw = readFileSync(path, "utf8").replace(/("confidence_score"\s*:\s*)[\d.]+/, "$1" + "1e900");
  assert.ok(raw.includes("1e900"));
  writeFileSync(path, raw);
  change(dir, receiptFile, (receipt) => { receipt.graph_sha256 = sha256(raw); });
  assert.throws(() => inspectEvidence(dir, source), /Nonfinite evidence number/);
});

test("GHQ-JS-029 requires string labels", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.nodes[0].label = { text: "invalid" }; });
  assert.throws(() => inspectEvidence(dir, source), /Invalid node label/);
});

test("GHQ-JS-031 enforces the direction of source inventory edges", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => {
    const edge = graph.links.find((item) => item.relation === "contains_source");
    [edge.source, edge.target] = [edge.target, edge.source];
  });
  assert.throws(() => inspectEvidence(dir, source), /Invalid source inventory edge/);
});

test("GHQ-JS-033 accepts Unicode scalar values and rejects unmatched surrogates", (t) => {
  const dir = copy(t);
  changeGraph(dir, (graph) => { graph.nodes[0].label = "𝄞"; });
  assert.ok([...inspectEvidence(dir, source).nodes.values()].some((node) => node.label === "𝄞"));
  changeGraph(dir, (graph) => { graph.nodes[0].label = String.fromCharCode(0xd800); });
  assert.throws(() => inspectEvidence(dir, source), /Invalid node label/);
});

test("GHQ-JS-037 rejects a numeric path even when the endpoint and edge agree", () => {
  const graph = inspectEvidence(handoff, source);
  assert.equal(implementationLocation(replaceCitationPath(graph, 204), feature, anchor), null);
  assert.deepEqual(implementationLocation(graph, feature, anchor), { path: "src/feature.py", line: 3 });
});

test("GHQ-JS-036 preserves exact graph identities across Unicode normalization", (t) => {
  const dir = copy(t);
  const composed = "diagnostic:\u00e9";
  const decomposed = "diagnostic:e\u0301";
  assert.notEqual(composed, decomposed);
  assert.equal(composed.normalize(), decomposed.normalize());
  changeGraph(dir, (graph) => {
    graph.nodes.push({ id: composed, label: "composed" }, { id: decomposed, label: "decomposed" });
  });
  change(dir, receiptFile, (receipt) => { receipt.nodes += 2; });
  const graph = inspectEvidence(dir, source);
  assert.equal(graph.nodes.get(composed).label, "composed");
  assert.equal(graph.nodes.get(decomposed).label, "decomposed");
  changeGraph(dir, (payload) => {
    payload.links[0].target = decomposed + "x";
  });
  assert.throws(() => inspectEvidence(dir, source), /Missing edge endpoint/);
});

test("GHQ-JS-030 enforces both confidence score boundaries", (t) => {
  for (const [score, valid] of [[0, true], [1, true], [-0.01, false], [1.01, false]]) {
    const dir = copy(t);
    changeGraph(dir, (graph) => { graph.links[0].confidence_score = score; });
    if (valid) inspectEvidence(dir, source);
    else assert.throws(() => inspectEvidence(dir, source), /Confidence score outside the unit interval/);
  }
});

test("GHQ-JS-032 bounds the reference consumer graph read by bytes", (t) => {
  const dir = copy(t);
  const bytes = readFileSync(join(dir, graphFile)).length;
  assert.ok(inspectEvidence(dir, source, { maxGraphBytes: bytes }).nodes.has(feature));
  // Also make the input invalid JSON. The byte budget must reject it before parsing.
  writeFileSync(join(dir, graphFile), Buffer.alloc(bytes + 1, 0x78));
  assert.throws(() => inspectEvidence(dir, source, { maxGraphBytes: bytes }), /Artifact exceeds byte budget/);
});

test("GHQ-JS-034 validates confidence categories independently of valid scores", (t) => {
  const dir = copy(t);
  inspectEvidence(dir, source);
  changeGraph(dir, (graph) => { graph.links[0].confidence = "UNKNOWN_CATEGORY"; });
  assert.throws(() => inspectEvidence(dir, source), /Expected extracted evidence confidence/);
});

test("GHQ-JS-035 checks the producer version independently of the template schema", (t) => {
  const dir = copy(t);
  const pinned = "0.9.109"; // Graphify producer in the frozen BART v0.0.8 lock.
  inspectEvidence(dir, source, { producerVersion: pinned });
  change(dir, receiptFile, (receipt) => { receipt.graphify_version = "0.0.0"; });
  assert.throws(() => inspectEvidence(dir, source, { producerVersion: pinned }), /Graphify producer version mismatch/);
});

test("GHQ-JS-038 validates the raw Git blobs against the receipt", (t) => {
  const dir = copy(t);
  const receipt = JSON.parse(readFileSync(join(dir, receiptFile), "utf8"));
  const sourceBlobs = new Map(Object.keys(receipt.source_sha256).map((path) =>
    [path, readFileSync(join(dir, ".source-blobs", path))]));
  assert.ok(inspectEvidence(dir, source, { sourceBlobs }).nodes.has(feature));
  change(dir, receiptFile, (value) => { value.source_sha256["src/feature.py"] = "f".repeat(64); });
  assert.throws(() => inspectEvidence(dir, source, { sourceBlobs }), /Pinned source bytes do not match digest/);
});
