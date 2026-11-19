import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { findImplementation, type EvidenceGraph } from "./citations.ts";

const archive = process.env.GRAPHIFY_HQ_ARCHIVE;
assert.ok(archive, "Set GRAPHIFY_HQ_ARCHIVE to the pinned v0.0.8 graph directory");
const graph: EvidenceGraph = JSON.parse(readFileSync(join(archive, "graph.json"), "utf8"));
const feature = "feature:archive-verification";
const anchor = "implemented_in:tools/verify_archive.py:L30";
const sourceCommit = "062fb633838daa42204289d889850c03e89d45eb";

test("GHQ-TS-004 maps the actual implementation edges to editor locations", () => {
  assert.deepEqual(findImplementation(graph, feature), {
    status: "found",
    sourceCommit,
    citations: [
      { path: ".github/workflows/graphify-hq-template.yml", line: 32 },
      { path: "tools/verify_archive.py", line: 30 },
      { path: "versions/v0.0.8/evidence_map.py", line: 203 },
    ],
  });
});

test("GHQ-TS-005 requires a real feature ID for implementation lookup", () => {
  assert.deepEqual(findImplementation(graph, "feature:unknown"), { status: "feature-not-found" });
  assert.deepEqual(findImplementation(graph, anchor), { status: "feature-not-found" });
});

test("GHQ-TS-006 keeps documentation and test links out of implementation results", () => {
  const links = graph.links.filter((edge) => edge.source !== feature || edge.relation !== "implemented_in");
  assert.ok(links.some((edge) => edge.source === feature && edge.relation === "documented_in"));
  assert.ok(links.some((edge) => edge.source === feature && edge.relation === "tested_by"));
  assert.deepEqual(findImplementation({ ...graph, links }, feature), { status: "no-implementation" });
});

test("GHQ-TS-007 withholds navigation when an implementation line is unusable", () => {
  assert.ok(graph.nodes.some((node) => node.id === anchor));
  for (const source_location of [null, "L0", "30", "L9007199254740992"]) {
    const nodes = graph.nodes.map((node) => node.id === anchor ? { ...node, source_location } : node);
    assert.deepEqual(findImplementation({ ...graph, nodes }, feature), { status: "invalid-citation" });
  }
});

test("GHQ-TS-008 rejects a missing implementation target even when other links are intact", () => {
  const nodes = graph.nodes.filter((node) => node.id !== anchor);
  assert.equal(nodes.length, graph.nodes.length - 1);
  assert.deepEqual(findImplementation({ ...graph, nodes }, feature), { status: "invalid-citation" });
});

test("GHQ-TS-009 does not give an app an implementation citation with an empty path", () => {
  const nodes = graph.nodes.map((node) => node.id === anchor ? { ...node, source_file: "" } : node);
  assert.deepEqual(findImplementation({ ...graph, nodes }, feature), { status: "invalid-citation" });
});
