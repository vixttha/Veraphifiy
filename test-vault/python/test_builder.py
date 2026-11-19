"""Run the frozen Graphify builder against committed, disposable inputs."""

import asyncio
import copy
import hashlib
import json
import os
import re
import select
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_bundle import PROFILE, write_observation

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

    def invoke(self, output, *args, manifest=None, checkout=None, locale="C.UTF-8"):
        config = self.root / "manifest.json"
        config.write_text(json.dumps(self.manifest if manifest is None else manifest), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(KIT / "evidence_map.py"), str(config), str(output), *args],
            cwd=checkout or self.repo, capture_output=True, text=True, timeout=45,
            env=dict(os.environ, LC_ALL=locale, PYTHONHASHSEED="0", GRAPHIFY_QUERY_LOG_DISABLE="1"),
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
        if isinstance(message, str):
            self.assertIn(message, result.stderr)
        else:
            self.assertRegex(result.stderr, message)
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
        source_files = {name.removeprefix("source-blobs/") for name in PROFILE["files"] if name.startswith("source-blobs/")}
        self.assertEqual(set(receipt["source_sha256"]), source_files)
        for name in sorted(source_files):
            target = output / "source-blobs" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(
                ["git", "show", f"{self.source}:{name}"], cwd=self.repo,
            ))
        write_observation(output, "python")
        shutil.copytree(output, HANDOFF)

    def test_GHQ_PY_100_archives_and_replays_two_pinned_versions(self):
        cli = Path(__file__).resolve().parents[2] / "veraphifiy.mjs"
        project = self.manifest["repository"]
        archive = self.root / "Veraphifiy archive"
        first = self.root / "first evidence"
        second = self.root / "second evidence"

        def call(command, version, *extra, project_id=project, archive_dir=archive):
            return subprocess.run(
                ["node", str(cli), command, "--archive", str(archive_dir),
                 "--project", project_id, "--version", version, *extra],
                cwd=self.root, capture_output=True, text=True, timeout=30,
            )

        def import_version(version, source, output, project_id=project, archive_dir=archive):
            return call("import", version, "--source", source, "--checkout", str(self.repo),
                        "--evidence", str(output), project_id=project_id, archive_dir=archive_dir)

        def result(command, version, *extra):
            run = call(command, version, *extra)
            self.succeeds(run)
            return json.loads(run.stdout)

        first_source = self.source
        self.succeeds(self.invoke(first))
        imported_first = import_version("v1.0.0", first_source, first)
        self.succeeds(imported_first)
        repeated = import_version("v1.0.0", first_source, first)
        self.succeeds(repeated)
        self.assertEqual(json.loads(repeated.stdout), json.loads(imported_first.stdout))
        old_entry = next(archive.glob("*.json"))
        old_bytes = old_entry.read_bytes()
        first_digest = hashlib.sha256(old_bytes).hexdigest()
        self.assertEqual(json.loads(imported_first.stdout)["archive_sha256"], first_digest)

        # Two distinct version labels may legitimately point to the same source commit.
        shared_archive = self.root / "shared source versions"
        for version in ("v1.0.0", "v1.0.1"):
            self.succeeds(import_version(version, first_source, first, archive_dir=shared_archive))
        shared = {read_json(path)["version"]: path for path in shared_archive.glob("*.json")}
        archived = call("verify", "v1.0.1", "--source", first_source, archive_dir=shared_archive)
        self.succeeds(archived)
        self.assertNotEqual(json.loads(archived.stdout)["archive_sha256"], first_digest)
        shared["v1.0.1"].write_bytes(shared["v1.0.0"].read_bytes())
        swapped = call("verify", "v1.0.1", "--source", first_source, archive_dir=shared_archive)
        self.assertNotEqual(swapped.returncode, 0)
        self.assertIn("does not match the selected project and version", swapped.stderr)

        companion = "example/companion-fixture"
        companion_export = self.root / "companion evidence"
        self.succeeds(self.invoke(companion_export, manifest=dict(self.manifest, repository=companion)))
        self.succeeds(import_version("v1.0.0", first_source, companion_export, project_id=companion,
                                     archive_dir=shared_archive))
        distinct_project = call("verify", "v1.0.0", "--source", first_source, project_id=companion,
                                archive_dir=shared_archive)
        self.succeeds(distinct_project)
        self.assertEqual(json.loads(distinct_project.stdout)["project"], companion)

        self.write("src/feature.py", b"# implementation\n# second version\ndef export():\n    return 'ready-v2'\n")
        self.write("test_sample.py", b"# v2 behavior\ndef test_export():\n    assert True\n")
        self.git("add", "src/feature.py", "test_sample.py")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Change the second fixture version")
        second_source = self.git("rev-parse", "HEAD").strip()
        newer_manifest = dict(self.manifest, source_commit=second_source, features=[
            dict(feature, implemented_in=[{"path": "src/feature.py", "anchor": "return 'ready-v2'"}])
            for feature in self.manifest["features"]
        ])
        self.succeeds(self.invoke(second, manifest=newer_manifest))
        imported_second = import_version("v1.1.0", second_source, second)
        self.succeeds(imported_second)
        second_digest = json.loads(imported_second.stdout)["archive_sha256"]

        for version, source, line, digest in (
            ("v1.0.0", first_source, 3, first_digest), ("v1.1.0", second_source, 4, second_digest),
        ):
            looked_up = result("lookup", version, "--source", source, "--archive-sha256", digest,
                               "--feature", FEATURE)
            self.assertEqual((looked_up["project"], looked_up["version"], looked_up["source"]),
                             (project, version, source))
            self.assertEqual(looked_up["citations"], [{"path": "src/feature.py", "line": line}])
            self.assertEqual(looked_up["archive_sha256"], digest)
            self.assertEqual((looked_up["veraphifiy_version"], looked_up["format"]), ("v0.0.9", 1))
            self.assertEqual(result("verify", version)["graph_sha256"], looked_up["graph_sha256"])

        missing = call("verify", "v1.2.0")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("not archived", missing.stderr)
        wrong_project = import_version("v1.0.0", first_source, first, "example/other-fixture")
        self.assertNotEqual(wrong_project.returncode, 0)
        self.assertIn("repository mismatch", wrong_project.stderr)
        wrong_pin = call("verify", "v1.0.0", "--source", second_source)
        self.assertNotEqual(wrong_pin.returncode, 0)
        self.assertIn("source commit mismatch", wrong_pin.stderr)
        replace = import_version("v1.0.0", second_source, second)
        self.assertNotEqual(replace.returncode, 0)
        self.assertIn("cannot be replaced", replace.stderr)
        self.assertEqual(old_entry.read_bytes(), old_bytes)

        old_entry.write_bytes(old_bytes + b"\n")
        self.succeeds(call("verify", "v1.0.0", "--source", first_source))
        changed_pin = call("verify", "v1.0.0", "--source", first_source, "--archive-sha256", first_digest)
        self.assertNotEqual(changed_pin.returncode, 0)
        self.assertIn("Archive SHA-256 mismatch", changed_pin.stderr)
        old_entry.write_bytes(old_bytes)

        regular_file = old_entry.with_suffix(".saved")
        old_entry.rename(regular_file)
        old_entry.symlink_to(regular_file)
        link_entry = call("verify", "v1.0.0", "--source", first_source)
        self.assertNotEqual(link_entry.returncode, 0)
        self.assertIn("Archive entry must be a regular file", link_entry.stderr)
        old_entry.unlink()
        regular_file.rename(old_entry)

        damaged = read_json(old_entry)
        damaged["receipt_sha256"] = "0" * 64
        old_entry.write_text(json.dumps(damaged), encoding="utf-8")
        changed = call("verify", "v1.0.0")
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn("Receipt digest mismatch", changed.stderr)
        old_entry.write_bytes(old_bytes)
        shutil.copytree(archive, HANDOFF / "veraphifiy-archive")
        (HANDOFF / "veraphifiy-archive-expectations.json").write_text(json.dumps({
            "project": project,
            "feature": FEATURE,
            "versions": [
                {"version": "v1.0.0", "source": first_source, "line": 3, "archive_sha256": first_digest},
                {"version": "v1.1.0", "source": second_source, "line": 4, "archive_sha256": second_digest},
            ],
        }) + "\n", encoding="utf-8")

        replay = cli.parent / "test-vault/javascript/verify-archive-replay.mjs"
        fixture = self.root / "replay context"
        fixture.mkdir()
        env_context = {
            "GITHUB_SHA": first_source, "GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/example",
            "GITHUB_WORKFLOW_REF": "example/project/.github/workflows/test.yml@refs/heads/example",
            "GITHUB_WORKFLOW_SHA": first_source, "GITHUB_RUN_ID": "12", "GITHUB_RUN_ATTEMPT": "2",
        }
        context = {key.lower(): value for key, value in env_context.items() if key != "GITHUB_SHA"}
        context.update(checkout_sha=first_source, github_run_attempt="1")
        (fixture / "evidence-context.json").write_text(json.dumps(context), encoding="utf-8")
        wrong_attempt = subprocess.run(["node", str(replay), str(fixture), "--actions"],
                                       capture_output=True, text=True, timeout=15,
                                       env=dict(os.environ, **env_context))
        self.assertNotEqual(wrong_attempt.returncode, 0)
        self.assertIn("Archive handoff context mismatch: github_run_attempt", wrong_attempt.stderr)

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
            ("invalid.txt", re.compile(r"utf-8", re.IGNORECASE)),
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

    def test_GHQ_PY_029_rebuilds_in_independent_checkouts_and_locales(self):
        clone = self.root / "independent checkout" / "clone"
        self.git("clone", "-q", "--local", str(self.repo), str(clone))
        first, second = self.root / "first", self.root / "second"
        self.succeeds(self.invoke(first, locale="C"))
        self.succeeds(self.invoke(second, checkout=clone, locale="C.UTF-8"))
        for name in PARTS:
            expected = (first / name).read_bytes()
            self.assertEqual(expected, (second / name).read_bytes(), name)
            self.assertNotIn(os.fsencode(self.repo), expected)
            self.assertNotIn(os.fsencode(clone), expected)

    def test_GHQ_PY_030_preserves_committed_line_endings_and_unicode(self):
        self.write(".gitattributes", "anchors/* -text\n".encode())
        originals = {
            "anchors/lf.py": "# résumé\névidence\n".encode(),
            "anchors/crlf.py": "# résumé\r\névidence\r\n".encode(),
        }
        for name, contents in originals.items():
            self.write(name, contents)
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Record both source line endings")
        manifest = copy.deepcopy(self.manifest)
        manifest["source_commit"] = self.git("rev-parse", "HEAD").strip()
        manifest["source_files"].extend(originals)
        manifest["features"][0]["implemented_in"] = [
            {"path": name, "anchor": "évidence"} for name in originals
        ]
        output = self.root / "lines"
        self.succeeds(self.invoke(output, manifest=manifest))
        receipt = read_json(output / "receipt.json")
        anchors = {node["id"] for node in read_json(output / "graph.json")["nodes"]}
        for name, contents in originals.items():
            self.assertEqual(receipt["source_sha256"][name], hashlib.sha256(contents).hexdigest())
            self.assertIn(f"implemented_in:{name}:L2", anchors)

    def test_GHQ_PY_031_does_not_publish_when_interrupted_during_mcp(self):
        output = self.root / "published"
        self.succeeds(self.invoke(output))
        previous = {name: (output / name).read_bytes() for name in PARTS}
        manifest = dict(self.manifest, title="Replacement after retry")
        config = self.root / "manifest.json"
        config.write_text(json.dumps(manifest), encoding="utf-8")
        block = """
import asyncio, evidence_map, sys
async def wait_for_cancellation(graph, receipt):
    print("MCP boundary reached", flush=True)
    await asyncio.Event().wait()
evidence_map.verify_mcp = wait_for_cancellation
evidence_map.main()
"""
        environment = dict(os.environ, PYTHONPATH=str(KIT), PYTHONHASHSEED="0", GRAPHIFY_QUERY_LOG_DISABLE="1")
        with subprocess.Popen(
            [sys.executable, "-c", block, str(config), str(output)], cwd=self.repo,
            env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ) as process:
            try:
                readable, _, _ = select.select([process.stdout], [], [], 15)
                self.assertTrue(readable, "builder never reached MCP boundary")
                self.assertEqual(process.stdout.readline().strip(), b"MCP boundary reached")
            finally:
                process.kill()
                process.communicate(timeout=10)
        self.assertEqual({name: (output / name).read_bytes() for name in PARTS}, previous)
        self.succeeds(self.invoke(output, manifest=manifest))
        self.assertNotEqual((output / "graph.json").read_bytes(), previous["graph.json"])
        self.succeeds(self.invoke(output, "--check", manifest=manifest))

    def test_GHQ_PY_036_keeps_its_explicit_pin_after_head_changes(self):
        self.write("src/feature.py", b"# different source at HEAD\n")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "Move worktree beyond the source pin")
        later = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "--detach", self.source)
        reference = self.root / "reference"
        self.succeeds(self.invoke(reference))
        config = self.root / "manifest.json"
        output = self.root / "moved"
        switch = """
import evidence_map, subprocess, sys
later = sys.argv.pop()
read_original = evidence_map.source_lines
def move_after_first_read(commit, path):
    result = read_original(commit, path)
    evidence_map.source_lines = read_original
    subprocess.run(["git", "checkout", "-q", "--detach", later], check=True)
    return result
evidence_map.source_lines = move_after_first_read
evidence_map.main()
"""
        environment = dict(os.environ, PYTHONPATH=str(KIT), PYTHONHASHSEED="0", GRAPHIFY_QUERY_LOG_DISABLE="1")
        self.succeeds(subprocess.run(
            [sys.executable, "-c", switch, str(config), str(output), later], cwd=self.repo,
            env=environment, capture_output=True, text=True, timeout=45,
        ))
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), later)
        for name in PARTS:
            self.assertEqual((reference / name).read_bytes(), (output / name).read_bytes())

    def test_GHQ_PY_043_requires_an_integer_pr_number_in_the_released_manifest(self):
        for invalid in (True, 1.5):
            with self.subTest(invalid=invalid):
                manifest = dict(self.manifest, pull_request={"number": invalid, "source_branch": "fixture"})
                self.unchanged_failure(manifest, "Expected a positive PR number")
        output = self.root / "valid-pr"
        manifest = dict(self.manifest, pull_request={"number": 12, "source_branch": "fixture"})
        self.succeeds(self.invoke(output, manifest=manifest))
        self.assertEqual(read_json(output / "receipt.json")["pull_request"], manifest["pull_request"])

    def test_GHQ_PY_045_recovers_a_pair_written_by_the_released_builder(self):
        output = self.root / "published"
        self.succeeds(self.invoke(output))
        old = {name: (output / name).read_bytes() for name in PARTS}
        replacement = dict(self.manifest, title="Draft replacement")
        config = self.root / "manifest.json"
        config.write_text(json.dumps(replacement), encoding="utf-8")
        draft = Path(os.environ["GRAPHIFY_HQ_CANDIDATE"]).resolve() / "candidate"
        env = dict(os.environ, PYTHONPATH=str(draft), PYTHONHASHSEED="0", GRAPHIFY_QUERY_LOG_DISABLE="1")
        interruption = """
import evidence_map, os, sys
from pathlib import Path
replace = os.replace
published = Path(sys.argv[2]) / "graph.json"
def interrupted_replace(source, target):
    replace(source, target)
    if Path(target) == published:
        os._exit(47)
evidence_map.os.replace = interrupted_replace
evidence_map.main()
"""
        result = subprocess.run(
            [sys.executable, "-c", interruption, str(config), str(output)],
            cwd=self.repo, env=env, capture_output=True, text=True, timeout=45,
        )
        self.assertEqual(result.returncode, 47, result.stdout + result.stderr)
        self.assertNotEqual((output / "graph.json").read_bytes(), old["graph.json"])
        recovery = "from pathlib import Path; import evidence_map, sys; evidence_map.read_published_pair(Path(sys.argv[1]))"
        self.succeeds(subprocess.run(
            [sys.executable, "-c", recovery, str(output)], env=env, text=True, capture_output=True, timeout=15,
        ))
        self.assertEqual({name: (output / name).read_bytes() for name in PARTS}, old)
        for flags in ([], ["--check"]):
            self.succeeds(subprocess.run(
                [sys.executable, str(draft / "evidence_map.py"), str(config), str(output), *flags],
                cwd=self.repo, env=env, text=True, capture_output=True, timeout=45,
            ))
        self.assertNotEqual((output / "graph.json").read_bytes(), old["graph.json"])
        self.assertEqual(read_json(output / "receipt.json")["source_commit"], self.source)


if __name__ == "__main__":
    unittest.main()
