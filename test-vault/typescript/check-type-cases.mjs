import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";

const root = dirname(fileURLToPath(import.meta.url));
const fixture = resolve(root, "citations.types.ts");
const config = resolve(root, "tsconfig.json");
const options = ts.getParsedCommandLineOfConfigFile(config, {}, {
  ...ts.sys,
  onUnRecoverableConfigFileDiagnostic(diagnostic) {
    throw new Error(ts.flattenDiagnosticMessageText(diagnostic.messageText, "\n"));
  },
});
if (options.errors.length) {
  throw new Error(ts.formatDiagnosticsWithColorAndContext(options.errors, ts.createCompilerHost(options.options)));
}

function diagnostics(source) {
  const host = ts.createCompilerHost(options.options);
  const original = host.getSourceFile;
  host.getSourceFile = (path, languageVersion, ...args) =>
    resolve(path) === fixture
      ? ts.createSourceFile(path, source, languageVersion)
      : original(path, languageVersion, ...args);
  return ts.getPreEmitDiagnostics(ts.createProgram(options.fileNames, options.options, host));
}

function verify(source) {
  const near = /^\s*\/\/ (GHQ-TS-\d+): TS(\d+) at ([\w]+)\b/;
  const lines = source.split(/\r?\n/);
  const cases = new Map();
  for (const [index, line] of lines.entries()) {
    const [, id, code, token] = near.exec(line) ?? [];
    if (!id) continue;
    const assertion = lines[index + 2];
    const column = assertion?.search(new RegExp("\\b" + token + "\\b")) ?? -1;
    if (cases.has(id) || !/^\s*\/\/ @ts-expect-error\b/.test(lines[index + 1] ?? "") || column < 0) {
      throw new Error("Invalid compile-time assertion: " + id);
    }
    cases.set(id, { code: Number(code), line: index + 2, column });
    lines[index + 1] = "";
  }
  if (!cases.size) throw new Error("No compile-time cases declared");
  const suppressed = diagnostics(source);
  if (suppressed.length) throw new Error("Baseline type check failed: " + suppressed.map(({code}) => code).join(", "));
  const actual = diagnostics(lines.join("\n"));
  const expected = [...cases.values()];
  if (actual.length !== expected.length || actual.some(diagnostic => {
    if (!diagnostic.file || resolve(diagnostic.file.fileName) !== fixture || diagnostic.start === undefined) return true;
    const { line, character } = diagnostic.file.getLineAndCharacterOfPosition(diagnostic.start);
    const position = expected.findIndex(entry =>
      entry.code === diagnostic.code && entry.line === line && entry.column === character);
    if (position < 0) return true;
    expected.splice(position, 1);
    return false;
  })) {
    throw new Error("Compile-time cases did not produce their exact diagnostics");
  }
  return cases.keys();
}

const source = process.argv[2] === "--stdin" ? readFileSync(0, "utf8") : readFileSync(fixture, "utf8");
for (const id of verify(source)) console.log("TYPE PASS " + id);
