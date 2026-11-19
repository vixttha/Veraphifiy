import { createHash } from "node:crypto";
import { closeSync, fstatSync, openSync, readFileSync, readSync } from "node:fs";
import { join } from "node:path";

export function sha256(bytes) {
  return createHash("sha256").update(bytes).digest("hex");
}

function rejectDuplicateKeys(text, filename) {
  const objects = [];
  let lastString;
  // Native JSON.parse has already validated the syntax. A colon can only
  // follow an object member name, and quoted tokens are consumed whole.
  for (const [token] of text.matchAll(/"(?:[^"\\]|\\.)*"|[{}:\[\]]/g)) {
    switch (token) {
      case "{": objects.push(new Set()); break;
      case "[": objects.push(null); break;
      case "}":
      case "]": objects.pop(); break;
      case ":": {
        const key = JSON.parse(lastString);
        const keys = objects.at(-1);
        if (keys.has(key)) throw new Error("Duplicate JSON key in " + filename);
        keys.add(key);
        break;
      }
      default: lastString = token;
    }
  }
}

function readBytes(path, maxBytes) {
  if (maxBytes === undefined) return readFileSync(path);
  if (!Number.isSafeInteger(maxBytes) || maxBytes < 1) throw new Error("Invalid artifact byte budget");
  const fd = openSync(path, "r");
  try {
    const stat = fstatSync(fd);
    if (!stat.isFile() || stat.size > maxBytes) throw new Error("Artifact exceeds byte budget or is not a regular file");
    const buffer = Buffer.alloc(stat.size);
    let size = 0;
    while (size < buffer.length) {
      const read = readSync(fd, buffer, size, buffer.length - size, null);
      if (!read) break;
      size += read;
    }
    if (readSync(fd, Buffer.alloc(1), 0, 1, null)) {
      throw new Error("Artifact changed size during bounded read");
    }
    return buffer.subarray(0, size);
  } finally {
    closeSync(fd);
  }
}

function readJSON(directory, filename, maxBytes) {
  let raw;
  try {
    raw = readBytes(join(directory, filename), maxBytes);
  } catch (err) {
    throw new Error("Cannot read " + filename + ": " + (err.code ?? err.message));
  }
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(raw);
  } catch {
    throw new Error("Invalid UTF-8 in " + filename);
  }
  let value;
  try {
    value = JSON.parse(text);
  } catch {
    throw new Error("Invalid JSON in " + filename);
  }
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("Expected an object in " + filename);
  }
  rejectDuplicateKeys(text, filename);
  return [raw, value];
}

const relations = new Set(["documented_in", "changed_in", "tested_by", "implemented_in"]);

const structuralRelations = new Set(["contains_feature", "contains_source", "located_in"]);
const digestPattern = /^[a-f0-9]{64}$/;

function ordinaryRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function repositoryPath(path) {
  return typeof path === "string" && path.trim().length > 0 && !/[\\:\p{C}]/u.test(path) &&
    path.split("/").every((part) => part !== "" && part !== "." && part !== ".." && part !== ".git");
}

export function inspectEvidence(directory, sourceCommit, {
  repository, templateVersion, producerVersion, maxGraphBytes, sourceBlobs,
} = {}) {
  const [bytes, graph] = readJSON(directory, "graph.json", maxGraphBytes);
  const [receiptBytes, receipt] = readJSON(directory, "receipt.json");
  if (receipt.schema_version !== 1) throw new Error("Unsupported receipt schema");
  if (!Array.isArray(graph.nodes) || !Array.isArray(graph.links)) throw new Error("Invalid graph shape");
  if (!/^[a-f0-9]{40}$/.test(sourceCommit) || graph.built_at_commit !== sourceCommit ||
      receipt.source_commit !== sourceCommit) throw new Error("Source commit mismatch");
  const digest = sha256(bytes);
  if (receipt.graph_sha256 !== digest) throw new Error("Graph digest mismatch");
  if (receipt.nodes !== graph.nodes.length) throw new Error("Node count mismatch");
  if (receipt.edges !== graph.links.length) throw new Error("Edge count mismatch");
  if (receipt.mcp_verified !== true) throw new Error("Receipt lacks MCP verification");

  if (graph.directed !== true || graph.multigraph !== false) throw new Error("Expected a directed simple graph");
  if (!ordinaryRecord(graph.graph) || graph.graph.scope !== "feature-evidence" ||
      receipt.scope !== graph.graph.scope || (repository !== undefined && receipt.repository !== repository)) {
    throw new Error("Evidence scope or repository mismatch");
  }
  if (typeof receipt.template_version !== "string" || receipt.template_version !== graph.graph.template_version ||
      (templateVersion !== undefined && receipt.template_version !== templateVersion)) {
    throw new Error("Evidence template version mismatch");
  }
  if (producerVersion !== undefined &&
      (receipt.graphify_version !== producerVersion ||
       (graph.graph.graphify_version !== undefined && graph.graph.graphify_version !== producerVersion))) {
    throw new Error("Graphify producer version mismatch");
  }
  if (!Array.isArray(receipt.source_files) || !ordinaryRecord(receipt.source_sha256)) {
    throw new Error("Invalid source inventory");
  }
  const inventory = new Set(receipt.source_files);
  if (inventory.size !== receipt.source_files.length || [...inventory].some((path) => !repositoryPath(path))) {
    throw new Error("Invalid source inventory");
  }
  const nodes = new Map();
  const summaries = new Map();
  for (const node of graph.nodes) {
    if (typeof node?.id !== "string" || !node.id) throw new Error("Invalid node ID");
    if (nodes.has(node.id)) throw new Error("Duplicate node ID: " + node.id);
    if (typeof node.label !== "string" || !node.label.isWellFormed()) throw new Error("Invalid node label");
    nodes.set(node.id, node);
    if (node.id.startsWith("feature:")) summaries.set(node.id, new Map());
  }
  const root = "source:" + sourceCommit;
  if (!nodes.has(root) || [...nodes.keys()].some((id) => id.startsWith("source:") && id !== root)) {
    throw new Error("Source root mismatch");
  }
  const fileNodes = [...nodes.values()].filter((node) => node.id.startsWith("file:"));
  if (fileNodes.length !== inventory.size ||
      fileNodes.some((node) => !inventory.has(node.source_file) || node.id !== "file:" + node.source_file)) {
    throw new Error("Source inventory does not match file nodes");
  }
  const referenced = new Set(inventory);
  const uniqueEdges = new Set();
  const featured = new Set();
  const inventoried = new Set();
  for (const edge of graph.links) {
    if (!nodes.has(edge?.source) || !nodes.has(edge?.target)) throw new Error("Missing edge endpoint");
    const {source, target, relation, confidence_score, weight} = edge;
    if (!relations.has(relation) && !structuralRelations.has(relation)) {
      throw new Error("Unsupported evidence relation");
    }
    if (!Number.isFinite(confidence_score) || !Number.isFinite(weight)) throw new Error("Nonfinite evidence number");
    if (confidence_score < 0 || confidence_score > 1) throw new Error("Confidence score outside the unit interval");
    if (edge.confidence !== "EXTRACTED") throw new Error("Expected extracted evidence confidence");
    const identity = JSON.stringify([source, relation, target]);
    if (uniqueEdges.has(identity)) throw new Error("Duplicate evidence edge");
    uniqueEdges.add(identity);
    if (relation === "contains_source") {
      const path = nodes.get(target).source_file;
      if (source !== root || target !== "file:" + path || !inventory.has(path) || edge.source_file !== path) {
        throw new Error("Invalid source inventory edge");
      }
      inventoried.add(path);
    }
    if (relation === "contains_feature") {
      if (source !== root || !summaries.has(target)) throw new Error("Invalid source feature edge");
      featured.add(target);
    }
    if (relation === "located_in") {
      const origin = nodes.get(source);
      if (target !== "file:" + origin.source_file || !inventory.has(origin.source_file) ||
          edge.source_file !== origin.source_file || ![...relations].some((kind) => source.startsWith(kind + ":"))) {
        throw new Error("Invalid located_in evidence edge");
      }
    }
    if (relations.has(relation)) {
      if (!summaries.has(source) || !target.startsWith(relation + ":")) throw new Error("Invalid evidence anchor");
      if (relation === "implemented_in" && nodes.get(target).file_type !== "code") {
        throw new Error("Invalid implementation target category");
      }
      referenced.add(nodes.get(target).source_file);
      const counts = summaries.get(edge.source);
      counts.set(edge.relation, (counts.get(edge.relation) ?? 0) + 1);
    }
  }
  if (featured.size !== summaries.size || inventoried.size !== inventory.size) {
    throw new Error("Missing source-root attachment");
  }
  for (const path of referenced) {
    const digest = receipt.source_sha256[path];
    if (!repositoryPath(path) || typeof digest !== "string" || !digestPattern.test(digest)) {
      throw new Error("Invalid or missing source digest");
    }
    if (sourceBlobs !== undefined) {
      const blob = sourceBlobs.get(path);
      if (!(blob instanceof Uint8Array) || sha256(blob) !== digest) {
        throw new Error("Pinned source bytes do not match digest: " + path);
      }
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
  const hash = createHash("sha256").update("graphify-handoff-v1\n");
  for (const part of [bytes, receiptBytes, Buffer.from(sourceCommit + "\n", "ascii")]) {
    hash.update(String(part.length) + "\n");
    hash.update(part);
  }
  return { nodes, links: graph.links, digest, bundleDigest: hash.digest("hex") };
}

export function implementationLocation({ nodes, links }, feature, target) {
  const edge = links.find((link) => link.source === feature && link.target === target &&
    link.relation === "implemented_in");
  const node = nodes.get(target);
  if (!edge || !repositoryPath(node?.source_file) || node.source_file !== edge.source_file ||
      typeof node.source_location !== "string" || node.source_location !== edge.source_location ||
      !/^L[1-9][0-9]*$/.test(node.source_location)) {
    return null;
  }
  const line = Number(node.source_location.slice(1));
  return Number.isSafeInteger(line) ? { path: node.source_file, line } : null;
}
