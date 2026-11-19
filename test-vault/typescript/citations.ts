// Test-only reference consumer for Graphify's feature-to-implementation navigation.
export type EvidenceGraph = {
  built_at_commit: string;
  nodes: readonly {
    id: string;
    source_file: string;
    source_location: string | null;
  }[];
  links: readonly {
    source: string;
    target: string;
    relation: string;
    source_file: string;
    source_location: string | null;
  }[];
};

export type Citation = Readonly<{ path: string; line: number }>;

export type ImplementationLookup =
  | {
      status: "found";
      sourceCommit: string;
      citations: readonly [Citation, ...Citation[]];
    }
  | { status: "feature-not-found" }
  | { status: "no-implementation" }
  | { status: "invalid-citation" };

function isRepositoryPath(path: string): boolean {
  return typeof path === "string" && path.trim().length > 0 && !/[\\:\p{C}]/u.test(path) &&
    path.split("/").every((part) => part !== "" && part !== "." && part !== ".." && part !== ".git");
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function validPin(value: unknown): value is string {
  return typeof value === "string" && /^[a-f0-9]{40}$/.test(value);
}

function validLocation(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

export function decodeEvidenceGraph(value: unknown): EvidenceGraph | null {
  if (!record(value) || !validPin(value.built_at_commit) ||
      !Array.isArray(value.nodes) || !Array.isArray(value.links)) return null;
  if (!value.nodes.every((node: unknown) => record(node) &&
      typeof node.id === "string" && typeof node.source_file === "string" &&
      validLocation(node.source_location))) return null;
  if (!value.links.every((edge: unknown) => record(edge) &&
      typeof edge.source === "string" && typeof edge.target === "string" &&
      typeof edge.relation === "string" && typeof edge.source_file === "string" &&
      validLocation(edge.source_location))) return null;
  return { built_at_commit: value.built_at_commit, nodes: value.nodes, links: value.links };
}

export function findImplementation(graph: EvidenceGraph, feature: string): ImplementationLookup {
  if (!validPin(graph.built_at_commit)) return { status: "invalid-citation" };
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]));
  if (nodes.size !== graph.nodes.length) return { status: "invalid-citation" };
  if (!feature.startsWith("feature:") || !nodes.has(feature)) {
    return { status: "feature-not-found" };
  }

  const citations: Citation[] = [];
  for (const edge of graph.links) {
    if (edge.source !== feature || edge.relation !== "implemented_in") {
      continue;
    }
    const target = nodes.get(edge.target);
    if (!target || !isRepositoryPath(target.source_file) ||
        typeof target.source_location !== "string" || target.source_file !== edge.source_file ||
        target.source_location !== edge.source_location ||
        !/^L[1-9][0-9]*$/.test(target.source_location)) {
      return { status: "invalid-citation" };
    }
    const line = Number(target.source_location.slice(1));
    if (!Number.isSafeInteger(line)) {
      return { status: "invalid-citation" };
    }
    citations.push({ path: target.source_file, line });
  }

  citations.sort((left, right) => left.path === right.path
    ? left.line - right.line
    : left.path < right.path ? -1 : 1);
  const [first, ...rest] = citations;
  return first
    ? { status: "found", sourceCommit: graph.built_at_commit, citations: [first, ...rest] }
    : { status: "no-implementation" };
}
