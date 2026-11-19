import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function readJSON(directory, filename) {
  let raw;
  try {
    raw = readFileSync(join(directory, filename));
  } catch (err) {
    throw new Error("Cannot read " + filename + ": " + err.code);
  }
  let value;
  try {
    value = JSON.parse(raw);
  } catch {
    throw new Error("Invalid JSON in " + filename);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Expected an object in " + filename);
  }
  return [raw, value];
}

const relations = new Set(["documented_in", "changed_in", "tested_by", "implemented_in"]);

export function inspectEvidence(directory, sourceCommit) {
  const [bytes, graph] = readJSON(directory, "graph.json");
  const [, receipt] = readJSON(directory, "receipt.json");
  if (receipt.schema_version !== 1) throw new Error("Unsupported receipt schema");
  if (!Array.isArray(graph.nodes) || !Array.isArray(graph.links)) throw new Error("Invalid graph shape");
  if (!/^[a-f0-9]{40}$/.test(sourceCommit) || graph.built_at_commit !== sourceCommit ||
      receipt.source_commit !== sourceCommit) throw new Error("Source commit mismatch");
  const digest = sha256(bytes);
  if (receipt.graph_sha256 !== digest) throw new Error("Graph digest mismatch");
  if (receipt.nodes !== graph.nodes.length) throw new Error("Node count mismatch");
  if (receipt.edges !== graph.links.length) throw new Error("Edge count mismatch");
  if (receipt.mcp_verified !== true) throw new Error("Receipt lacks MCP verification");

  const nodes = new Map();
  const summaries = new Map();
  for (const node of graph.nodes) {
    if (typeof node?.id !== "string" || !node.id) throw new Error("Invalid node ID");
    if (nodes.has(node.id)) throw new Error("Duplicate node ID: " + node.id);
    nodes.set(node.id, node);
    if (node.id.startsWith("feature:")) summaries.set(node.id, new Map());
  }
  for (const edge of graph.links) {
    if (!nodes.has(edge?.source) || !nodes.has(edge?.target)) throw new Error("Missing edge endpoint");
    if (summaries.has(edge.source) && relations.has(edge.relation)) {
      const counts = summaries.get(edge.source);
      counts.set(edge.relation, (counts.get(edge.relation) ?? 0) + 1);
    }
  }
  if (!receipt.feature_links || typeof receipt.feature_links !== "object" ||
      Array.isArray(receipt.feature_links) || Object.keys(receipt.feature_links).length !== summaries.size) {
    throw new Error("Feature summary mismatch");
  }
  for (const [id, counts] of summaries) {
    const claimed = receipt.feature_links[id];
    if (!claimed || typeof claimed !== "object" || Array.isArray(claimed) ||
        Object.keys(claimed).length !== counts.size ||
        [...counts].some(([relation, count]) => claimed[relation] !== count)) {
      throw new Error("Feature summary mismatch: " + id);
    }
  }
  return { nodes, links: graph.links, digest };
}

export function implementationLocation({ nodes, links }, feature, target) {
  const edge = links.find((link) => link.source === feature && link.target === target &&
    link.relation === "implemented_in");
  const node = nodes.get(target);
  if (!edge || !node?.source_file || node.source_file !== edge.source_file ||
      node.source_location !== edge.source_location || !/^L[1-9][0-9]*$/.test(node.source_location)) {
    return null;
  }
  const line = Number(node.source_location.slice(1));
  return Number.isSafeInteger(line) ? { path: node.source_file, line } : null;
}
