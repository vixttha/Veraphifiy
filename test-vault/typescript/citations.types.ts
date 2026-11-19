import type { Citation, ImplementationLookup } from "./citations.ts";

export function checkCitationTypes(result: ImplementationLookup): void {
  // GHQ-TS-001: require a success check before accessing a citation.
  // @ts-expect-error An unresolved lookup cannot be used for navigation.
  result.citations[0];
  if (result.status === "found") {
    const first: Citation = result.citations[0];
    void first;
  }

  // GHQ-TS-002: an editor line is a number, not an exported "L30" string.
  // @ts-expect-error The data adapter must convert Graphify's source location first.
  const rawLine: Citation = { path: "tools/verify_archive.py", line: "L30" };
  void rawLine;

  // GHQ-TS-003: a successful lookup guarantees at least one citation.
  // @ts-expect-error An empty list cannot represent successful navigation.
  const empty: ImplementationLookup = { status: "found", sourceCommit: "example", citations: [] };
  void empty;
}
