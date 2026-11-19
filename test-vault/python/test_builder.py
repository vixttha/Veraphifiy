"""Run the frozen Graphify builder against committed, disposable inputs."""

import asyncio
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

KIT = Path(os.environ["GRAPHIFY_HQ_ARCHIVE"]).resolve().parents[1] / "versions/v0.0.8"
HANDOFF = Path(os.environ["GRAPHIFY_HQ_HANDOFF"]).resolve()
ANCHOR = "implemented_in:src/feature.py:L3"
FEATURE = "feature:export"
PARTS = ("graph.json", "receipt.json")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class BuilderTests(unittest.TestCase):
    def setUp(self):
        root = tempfile.TemporaryDirectory(prefix="graphify-builder-")
        self.addCleanup(root.cleanup)
        self.root = Path(root.name)
        self.repo = self.root / "source checkout"
        self.repo.mkdir()
        self.git("init", "-q")
        self.write("src/feature.py", b"# implementation\ndef export():\n    return 'ready'\n")
        self.write("notes.md", b"# Export\nstatus: implemented\n")
        self.write("test_sample.py", b"def test_export():\n    pass\n")
        self.write("ambiguous.md", b"shared\nnear match\nshared\n")
        self.write("empty.txt", b"")
        self.write("large.txt", b"x" * 1_000_001)
        self.write("invalid.txt", b"\xff\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Build a pinned fixture")
        self.source = self.git("rev-parse", "HEAD").strip()
        export = {
            "id": "export", "label": "Export evidence",
            "documented_in": [{"path": "notes.md", "anchor": "# Export"}],
            "changed_in": [{"path": "notes.md", "anchor": "status: implemented"}],
            "tested_by": [{"path": "test_sample.py", "anchor": "def test_export():"}],
            "implemented_in": [{"path": "src/feature.py", "anchor": "return 'ready'"}],
        }
        self.manifest = {
            "repository": "example/graphify-fixture", "source_commit": self.source,
            "title": "Pinned test evidence", "source_files": ["src/feature.py"],
            "features": [export, dict(export, id="preview", label="Preview evidence")],
        }

    def write(self, path, data):
        target = self.repo / path
        target.parent.mkdir(exist_ok=True, parents=True)
        target.write_bytes(data)

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.repo, text=True)

    def invoke(self, output, *args, manifest=None):
        config = self.root / "manifest.json"
        config.write_text(json.dumps(self.manifest if manifest is None else manifest), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(KIT / "evidence_map.py"), str(config), str(output), *args],
            cwd=self.repo, capture_output=True, text=True, timeout=45,
            env=dict(os.environ, PYTHONHASHSEED="0", GRAPHIFY_QUERY_LOG_DISABLE="1"),
        )

    def succeeds(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def unchanged_failure(self, manifest, message):
        output = self.root / "saved"
        output.mkdir(exist_ok=True)
        saved = {name: ("previous " + name).encode() for name in PARTS}
        for name, data in saved.items():
            (output / name).write_bytes(data)
        result = self.invoke(output, manifest=manifest)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)
        self.assertEqual({name: (output / name).read_bytes() for name in PARTS}, saved)

    async def neighbors(self, output):
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "graphify.serve", str(output / "graph.json")],
        )
        async with asyncio.timeout(20), stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                result = await session.call_tool("get_neighbors", {"node_id": FEATURE})
                self.assertFalse(result.is_error)
                return "\n".join(item.text for item in result.content if item.type == "text")

    def test_GHQ_PY_001_build_and_discover_exact_source_over_mcp(self):
        output = self.root / "fresh"
        self.succeeds(self.invoke(output))
        receipt = read_json(output / "receipt.json")
        self.assertEqual(receipt["source_commit"], self.source)
        self.assertIs(receipt["mcp_verified"], True)
        self.assertIn("src/feature.py L3 [implemented_in]", asyncio.run(self.neighbors(output)))
        observed = hashlib.sha256((output / "graph.json").read_bytes()).hexdigest()
        self.assertEqual(receipt["graph_sha256"], observed)
        (output / "python.sha256").write_text(observed + "\n", encoding="ascii")
        # Pass the independently known Git identity to the downstream consumer.
        (output / "source.txt").write_text(self.source + "\n", encoding="ascii")
        shutil.copytree(output, HANDOFF)

    def test_GHQ_PY_002_rebuilds_identical_graph_and_receipt(self):
        first, second = self.root / "first", self.root / "second"
        self.succeeds(self.invoke(first))
        reordered = dict(self.manifest, features=list(reversed(self.manifest["features"])))
        self.succeeds(self.invoke(second, manifest=reordered))
        for name in PARTS:
            self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(), name)
        self.succeeds(self.invoke(first, "--check"))

    def test_GHQ_PY_005_reads_committed_bytes_after_worktree_edits(self):
        committed = (self.repo / "notes.md").read_bytes()
        self.write("notes.md", b"Uncommitted replacement\n")
        self.write("src/feature.py", b"Uncommitted implementation\n")
        output = self.root / "map"
        self.succeeds(self.invoke(output))
        receipt = read_json(output / "receipt.json")
        self.assertNotIn("notes.md", receipt["source_files"])
        self.assertEqual(receipt["source_sha256"]["notes.md"], hashlib.sha256(committed).hexdigest())
        nodes = {node["id"] for node in read_json(output / "graph.json")["nodes"]}
        self.assertIn(ANCHOR, nodes)

    def test_GHQ_PY_007_requires_a_unique_line(self):
        for anchor, count in (("near", 0), ("shared", 2)):
            with self.subTest(anchor=anchor):
                manifest = copy.deepcopy(self.manifest)
                manifest["features"][0]["documented_in"] = [{"path": "ambiguous.md", "anchor": anchor}]
                self.unchanged_failure(manifest, f"found {count}")
        output = self.root / "unique"
        self.succeeds(self.invoke(output))
        self.assertIn(ANCHOR, {node["id"] for node in read_json(output / "graph.json")["nodes"]})

    def test_GHQ_PY_008_links_shared_anchors_to_inventory_and_supports_legacy_manifests(self):
        output = self.root / "linked"
        self.succeeds(self.invoke(output))
        links = read_json(output / "graph.json")["links"]
        self.assertEqual(
            {edge["source"] for edge in links if edge["target"] == ANCHOR},
            {FEATURE, "feature:preview"},
        )
        self.assertEqual(
            [(edge["target"], edge["relation"]) for edge in links if edge["source"] == ANCHOR],
            [("file:src/feature.py", "located_in")],
        )
        manifest = copy.deepcopy(self.manifest)
        del manifest["source_files"]
        for entry in manifest["features"]:
            del entry["implemented_in"]
        self.succeeds(self.invoke(output, manifest=manifest))
        self.assertNotIn("implemented_in", read_json(output / "receipt.json")["feature_links"][FEATURE])

    def test_GHQ_PY_009_rejects_unusable_git_objects_before_publication(self):
        blob = self.git("rev-parse", "HEAD:notes.md").strip()
        self.unchanged_failure(dict(self.manifest, source_commit=blob), "must identify a commit")
        for path, error in (
            ("missing.md", "missing.md"), ("src", "Expected a source blob"),
            ("empty.txt", "blob is empty"), ("large.txt", "exceeds the size limit"),
            ("invalid.txt", "UnicodeDecodeError"),
        ):
            with self.subTest(path=path):
                manifest = copy.deepcopy(self.manifest)
                manifest["source_files"] = [path]
                self.unchanged_failure(manifest, error)

    def test_GHQ_PY_011_check_rejects_archive_drift_without_repairing_it(self):
        output = self.root / "archive"
        self.succeeds(self.invoke(output))
        original = {name: (output / name).read_bytes() for name in PARTS}
        for name in PARTS:
            with self.subTest(name=name):
                expected = dict(original)
                expected[name] += b"\n"
                (output / name).write_bytes(expected[name])
                result = self.invoke(output, "--check")
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn("Deterministic rebuild differs: " + name, result.stderr)
                self.assertEqual({part: (output / part).read_bytes() for part in PARTS}, expected)
                (output / name).write_bytes(original[name])


if __name__ == "__main__":
    unittest.main()
