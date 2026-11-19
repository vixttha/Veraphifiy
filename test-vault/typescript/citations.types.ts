import type { Citation, ImplementationLookup } from "./citations.ts";

export function checkCitationTypes(result: ImplementationLookup): void {
  // GHQ-TS-001: TS2339 at citations · require a success check before accessing a citation.
  // @ts-expect-error An unresolved lookup cannot be used for navigation.
  result.citations[0];
  if (result.status === "found") {
    const first: Citation = result.citations[0];
    void first;
  }

  // GHQ-TS-002: TS2322 at line · an editor line is a number, not an exported "L30" string.
  // @ts-expect-error The data adapter must convert Graphify's source location first.
  const rawLine: Citation = { path: "tools/verify_archive.py", line: "L30" };
  void rawLine;

  // GHQ-TS-003: TS2322 at citations · a successful lookup guarantees at least one citation.
  // @ts-expect-error An empty list cannot represent successful navigation.
  const empty: ImplementationLookup = { status: "found", sourceCommit: "example", citations: [] };
  void empty;
}

export function exhaustive(result: ImplementationLookup): string {
  switch (result.status) {
    case "found":
    case "feature-not-found":
    case "no-implementation":
    case "invalid-citation":
    case "stale-source":
      return result.status;
    default: {
      const complete: never = result;
      return complete;
    }
  }
}

export function missingStatus(result: ImplementationLookup): string {
  switch (result.status) {
    case "found":
    case "feature-not-found":
    case "no-implementation":
    case "invalid-citation":
      return result.status;
    default: {
      // GHQ-TS-012: TS2322 at incomplete · omitting a lookup state leaves a reachable default branch.
      // @ts-expect-error The stale-source state remains.
      const incomplete: never = result;
      return incomplete;
    }
  }
}

export function uncheckedCitation(result: ImplementationLookup, index: number): Citation | undefined {
  if (result.status !== "found") return undefined;
  // GHQ-TS-035: TS2322 at unguarded · runtime indexes need an absent-value guard.
  // @ts-expect-error A dynamically selected citation may be undefined.
  const unguarded: Citation = result.citations[index];
  return unguarded;
}
