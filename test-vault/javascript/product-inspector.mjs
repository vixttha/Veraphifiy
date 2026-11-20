import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const product = process.env.VERAPHIFY_PRODUCT_ROOT;
assert.ok(product, "Set VERAPHIFY_PRODUCT_ROOT to the pinned product checkout");
const runtime = join(product, "lib/inspect-evidence.mjs");
const historical = join(product, "test-vault/javascript/inspect-evidence.mjs");

// Historical product revisions shipped their runtime with the test workspace.
export const { implementationLocation, inspectEvidence, inspectHandoff, parseEvidenceObject, readBytes, sha256 } =
  await import(pathToFileURL(existsSync(runtime) ? runtime : historical).href);
