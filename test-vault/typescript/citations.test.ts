import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { decodeEvidenceGraph, findImplementation, type EvidenceGraph } from "./citations.ts";

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

test("GHQ-TS-010 withholds paths the Graphify builder would never emit", () => {
  for (const source_file of ["/tmp/file.py", "../file.py", "src/../file.py", "C:\\file.py", "src//file.py", ".git/config"]) {
    const nodes = graph.nodes.map((node) => node.id === anchor ? { ...node, source_file } : node);
    assert.deepEqual(findImplementation({ ...graph, nodes }, feature), { status: "invalid-citation" }, source_file);
  }
});

test("GHQ-TS-011 decodes external graph data before using the typed lookup", () => {
  const external: unknown = structuredClone(graph);
  const checked = decodeEvidenceGraph(external);
  assert.ok(checked);
  assert.deepEqual(findImplementation(checked, feature), findImplementation(graph, feature));
  assert.equal(decodeEvidenceGraph({ ...graph, nodes: [null] }), null);
  assert.equal(decodeEvidenceGraph({ ...graph, links: [{ ...graph.links[0], target: 42 }] }), null);
});

test("GHQ-TS-013 rejects contradictory edge and node coordinates", () => {
  const links = graph.links.map((edge) => edge.target === anchor ? { ...edge, source_location: "L31" } : edge);
  assert.deepEqual(findImplementation({ ...graph, links }, feature), { status: "invalid-citation" });
});

function remapAnchor(source_file: string, source_location: string): EvidenceGraph {
  return {
    ...graph,
    nodes: graph.nodes.map((node) => node.id === anchor ? { ...node, source_file, source_location } : node),
    links: graph.links.map((edge) => edge.target === anchor ? { ...edge, source_file, source_location } : edge),
  };
}

test("GHQ-TS-014 preserves Unicode and whitespace in repository paths", () => {
  const path = "docs/évidence map.py";
  const result = findImplementation(remapAnchor(path, "L42"), feature);
  assert.equal(result.status, "found");
  assert.ok(result.citations.some((citation) => citation.path === path && citation.line === 42));
});

test("GHQ-TS-015 rejects a non-string coordinate without coercion", () => {
  const coordinate = ["L30"] as unknown as string;
  const invalid = remapAnchor("tools/verify_archive.py", coordinate);
  assert.equal(decodeEvidenceGraph(invalid), null);
  assert.deepEqual(findImplementation(invalid, feature), { status: "invalid-citation" });
});

test("GHQ-TS-016 refuses a repeated evidence node identity", () => {
  const target = graph.nodes.find((node) => node.id === anchor);
  assert.ok(target);
  const nodes = [...graph.nodes, { ...target, source_location: "L31" }];
  assert.deepEqual(findImplementation({ ...graph, nodes }, feature), { status: "invalid-citation" });
});

test("GHQ-TS-017 keeps distinct coordinates in the same implementation file", () => {
  const target = graph.nodes.find((node) => node.id === anchor);
  const edge = graph.links.find((entry) => entry.source === feature && entry.target === anchor);
  assert.ok(target && edge);
  const newId = "implemented_in:tools/verify_archive.py:L31";
  const result = findImplementation({
    ...graph,
    nodes: [...graph.nodes, { ...target, id: newId, source_location: "L31" }],
    links: [...graph.links, { ...edge, target: newId, source_location: "L31" }],
  }, feature);
  assert.equal(result.status, "found");
  assert.deepEqual(result.citations.filter((citation) => citation.path === target.source_file).map(({ line }) => line), [30, 31]);
});

test("GHQ-TS-018 returns a stable citation order for equivalent graph exports", () => {
  assert.deepEqual(findImplementation({ ...graph, links: [...graph.links].reverse() }, feature),
    findImplementation(graph, feature));
});

test("GHQ-TS-019 keeps a returned citation independent of later input changes", () => {
  const original = structuredClone(graph);
  const previous = findImplementation(original, feature);
  const node = original.nodes.find((entry) => entry.id === anchor);
  assert.ok(node);
  node.source_file = "different.py";
  assert.deepEqual(previous, findImplementation(graph, feature));
  assert.deepEqual(findImplementation(original, feature), { status: "invalid-citation" });
});

test("GHQ-TS-027 rejects mixed valid and invalid implementation citations", () => {
  const links = graph.links.map((edge) => edge.target === anchor ? { ...edge, source_file: "unrelated.py" } : edge);
  assert.deepEqual(findImplementation({ ...graph, links }, feature), { status: "invalid-citation" });
  assert.equal(findImplementation(graph, feature).status, "found");
});

test("GHQ-TS-031 withholds navigable results for an invalid graph source pin", () => {
  for (const built_at_commit of ["short-sha", "", sourceCommit.toUpperCase()]) {
    assert.deepEqual(findImplementation({ ...graph, built_at_commit }, feature), { status: "invalid-citation" });
  }
  assert.equal(findImplementation(graph, feature).status, "found");
});
