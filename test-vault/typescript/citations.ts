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

export function findImplementation(graph: EvidenceGraph, feature: string): ImplementationLookup {
  const nodes = new Map(graph.nodes.map((node) => [node.id, node]));
  if (!feature.startsWith("feature:") || !nodes.has(feature)) {
    return { status: "feature-not-found" };
  }

  const citations: Citation[] = [];
  for (const edge of graph.links) {
    if (edge.source !== feature || edge.relation !== "implemented_in") {
      continue;
    }
    const target = nodes.get(edge.target);
    if (!target || !isRepositoryPath(target.source_file) || !target.source_location ||
        !/^L[1-9][0-9]*$/.test(target.source_location)) {
      return { status: "invalid-citation" };
    }
    const line = Number(target.source_location.slice(1));
    if (!Number.isSafeInteger(line)) {
      return { status: "invalid-citation" };
    }
    citations.push({ path: target.source_file, line });
  }

  const [first, ...rest] = citations;
  return first
    ? { status: "found", sourceCommit: graph.built_at_commit, citations: [first, ...rest] }
    : { status: "no-implementation" };
}
