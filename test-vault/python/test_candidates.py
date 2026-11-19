"""Test draft BART contracts at the candidate pin used by the Vault workflow."""

import base64
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import asynccontextmanager, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

candidate = Path(os.environ["GRAPHIFY_HQ_CANDIDATE"]).resolve()
sys.path[:0] = [str(candidate / "candidate"), str(candidate / "tools")]
import evidence_map
import test_evidence_map as upstream
import test_verify_archive as mode_tests
import verify_archive


def existing_cases(test_class, *methods):
    for method in methods:
        test_class(method).debug()


class CandidateTests(unittest.TestCase):
    def test_GHQ_PY_003_recovers_interrupted_replacement_and_rollback(self):
        existing_cases(upstream.PublicationTests, "test_read_recovers_pair_after_publisher_is_killed",
                       "test_interruption_before_journal_retirement_restores_previous_pair",
                       "test_recovery_can_be_interrupted_and_repeated",
                       "test_retry_republishes_after_interruption")

    def test_GHQ_PY_004_recovers_an_interrupted_first_publish(self):
        existing_cases(upstream.PublicationTests, "test_retry_recovers_after_first_publisher_is_killed")

    def test_GHQ_PY_006_validates_required_fields_and_manifest_boundaries(self):
        fixture = upstream.ManifestTests()
        fixture.setUp()
        existing_cases(upstream.ManifestTests, "test_inventory_rejects_invalid_paths_and_duplicates",
                       "test_source_path_must_stay_inside_commit")
        base = fixture.manifest
        for key in ("documented_in", "changed_in", "tested_by"):
            invalid = copy.deepcopy(base)
            del invalid["features"][0][key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                evidence_map.validate_manifest(invalid)
        invalid = copy.deepcopy(base)
        invalid["features"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate feature"):
            evidence_map.validate_manifest(invalid)
        invalid = copy.deepcopy(base)
        invalid["features"][0]["tested_by"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate source link"):
            evidence_map.validate_manifest(invalid)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            manifest = output / "manifest.json"
            manifest.write_text(json.dumps(invalid), encoding="utf-8")
            old = {output / name: name.encode() for name in ("graph.json", "receipt.json")}
            for path, contents in old.items():
                path.write_bytes(contents)
            with patch.object(sys, "argv", ["builder", str(manifest), str(output)]):
                with self.assertRaisesRegex(ValueError, "duplicate source link"):
                    evidence_map.main()
            self.assertEqual({path: path.read_bytes() for path in old}, old)
        for count in (32, 33):
            manifest = dict(base, features=[dict(base["features"][0], id=f"feature-{i}") for i in range(count)])
            if count == 32:
                evidence_map.validate_manifest(manifest)
            else:
                with self.assertRaisesRegex(ValueError, "32 features"):
                    evidence_map.validate_manifest(manifest)
        for count in (64, 65):
            manifest = dict(base, source_files=[f"path-{i}" for i in range(count)])
            if count == 64:
                evidence_map.validate_manifest(manifest)
            else:
                with self.assertRaisesRegex(ValueError, "64 unique"):
                    evidence_map.validate_manifest(manifest)
        for count in (12, 13):
            manifest = copy.deepcopy(base)
            manifest["features"][0]["tested_by"] = [{"path": "tests.py", "anchor": str(i)} for i in range(count)]
            if count == 12:
                evidence_map.validate_manifest(manifest)
            else:
                with self.assertRaisesRegex(ValueError, "one to twelve"):
                    evidence_map.validate_manifest(manifest)

    def test_GHQ_PY_010_mcp_validation_failure_leaves_the_old_pair_intact(self):
        fixture = upstream.ManifestTests()
        fixture.setUp()
        source = fixture.manifest["source_commit"]
        receipt = {"nodes": 2, "edges": 1, "source_commit": source, "feature_links": {"feature:export": {"tested_by": 1}}}

        @asynccontextmanager
        async def stdio(*_):
            yield None, None

        for stats, tool_error, diagnostic in (
            ("", True, "call failed"),
            ("Nodes: 2\nEdges: 1\nBuilt at commit: " + "f" * 40, False, "statistics or source SHA"),
            ("Nodes: 2\nEdges: 1\nBuilt at commit: " + source, False, "expected 1, found 0"),
        ):
            class FailedSession:
                async def initialize(self):
                    pass

                async def call_tool(self, tool, _):
                    return SimpleNamespace(
                        is_error=tool_error,
                        content=[SimpleNamespace(type="text", text=stats if tool == "graph_stats" else "")],
                    )

            @asynccontextmanager
            async def session(*_):
                yield FailedSession()

            with self.subTest(diagnostic=diagnostic), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest = root / "manifest.json"
                manifest.write_text(json.dumps(fixture.manifest), encoding="utf-8")
                output = root / "published"
                output.mkdir()
                saved = {name: name.encode() for name in ("graph.json", "receipt.json")}
                for name, data in saved.items():
                    (output / name).write_bytes(data)
                graph = root / "candidate.json"
                graph.write_bytes(b"{}")
                with (
                    patch.object(sys, "argv", ["builder", str(manifest), str(output)]),
                    patch.object(evidence_map, "build", return_value=(graph, receipt)),
                    patch.object(evidence_map, "stdio_client", stdio),
                    patch.object(evidence_map, "ClientSession", session),
                    self.assertRaisesRegex(ValueError, diagnostic),
                ):
                    evidence_map.main()
                self.assertEqual({name: (output / name).read_bytes() for name in saved}, saved)

    def test_GHQ_PY_012_rolls_back_write_failures_and_rejects_unsafe_targets(self):
        existing_cases(upstream.PublicationTests, "test_replace_failure_restores_previous_pair",
                       "test_first_publish_failure_does_not_leave_half_pair",
                       "test_unavailable_receipt_target_does_not_replace_graph")

    def test_GHQ_PY_013_excludes_a_competing_writer(self):
        existing_cases(upstream.PublicationTests, "test_contending_publisher_cannot_modify_previous_pair",
                       "test_success_and_repeated_publication")

    def test_GHQ_PY_014_checks_renames_against_repository_identity(self):
        existing_cases(upstream.ProvenanceTests, "test_historical_slug_resolves_to_the_current_repository",
                       "test_same_slug_with_an_unrelated_repository_id_is_rejected",
                       "test_missing_repository_identity_is_rejected",
                       "test_unrelated_repository_or_branch_is_rejected")
        fixture = upstream.ProvenanceTests()
        fixture.setUp()
        fixture.pr["base"]["repo"]["id"] += 1
        with self.assertRaisesRegex(ValueError, "source repository and branch"):
            fixture.verify()

    def test_GHQ_PY_015_checks_historical_membership_on_later_pages(self):
        fixture = upstream.ProvenanceTests()
        fixture.setUp()
        fixture.commits = [{"sha": fixture.head}] * 100
        second = "pulls/3/commits?per_page=100&page=2"
        for members in ([{"sha": fixture.source}], []):
            original = fixture.fetch

            def paged(route):
                return members if route == second else original(route)

            with patch.object(fixture, "fetch", paged):
                if members:
                    self.assertEqual(fixture.verify()["source_relation"], "historical PR commit")
                else:
                    with self.assertRaisesRegex(ValueError, "absent"):
                        fixture.verify()
        fixture.source = fixture.head
        self.assertEqual(fixture.verify()["source_relation"], "current head")

    def test_GHQ_PY_016_counts_only_unsuperseded_approvals_for_the_source(self):
        existing_cases(upstream.ProvenanceTests, "test_superseded_and_later_commit_approvals_are_excluded")
        fixture = upstream.ProvenanceTests()
        fixture.setUp()
        fixture.reviews = [
            {"user": {"id": 1}, "state": "APPROVED", "commit_id": fixture.source},
            {"user": {"id": 1}, "state": "DISMISSED", "commit_id": fixture.source},
        ]
        self.assertEqual(fixture.verify()["exact_commit_approvals"], 0)

    def test_GHQ_PY_017_keeps_review_state_and_merge_sha_separate(self):
        existing_cases(upstream.ProvenanceTests, "test_merge_sha_is_distinct_from_source_sha")
        fixture = upstream.ProvenanceTests()
        fixture.setUp()
        for draft in (True, False):
            fixture.pr["draft"] = draft
            observed = fixture.verify()
            self.assertEqual(observed["pr_state"], "draft" if draft else "open")
            self.assertEqual(observed["source_commit"], fixture.source)
            self.assertIsNone(observed["merge_commit"])

    def test_GHQ_PY_018_resolves_runner_modes_from_verified_event_data(self):
        existing_cases(mode_tests.ExecutionModeTests,
                       "test_local_checkout_ignores_generic_ci_and_repository_variables",
                       "test_public_visibility", "test_private_and_internal_visibility",
                       "test_unknown_visibility_fails_closed")

    def test_GHQ_PY_019_exports_only_public_candidate_bytes(self):
        existing_cases(mode_tests.ExecutionModeTests, "test_nonpublic_modes_do_not_export_evidence_payloads")
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()) as stream:
            root = Path(directory)
            expected = {"graph.json": b"binary \xff" * 1024, "receipt.json": b"{ }\n"}
            for name, contents in expected.items():
                (root / name).write_bytes(contents)
            verify_archive.export_candidate("v0.0.9", "a" * 40, root, "github-public")
        chunks = {name: [] for name in expected}
        for line in stream.getvalue().splitlines():
            if line.startswith("GRAPHIFY_HQ_EXPORT "):
                _, _, name, index, payload = line.split()
                self.assertEqual(int(index), len(chunks[name]))
                chunks[name].append(payload)
        self.assertEqual({name: base64.b64decode("".join(parts), validate=True)
                          for name, parts in chunks.items()}, expected)

    def test_GHQ_PY_020_checks_frozen_history_and_kit_before_installing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            kit = root / "versions/v1.0.0"
            kit.mkdir(parents=True)
            (kit / "self-map.json").write_text("{}\n", encoding="utf-8")

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root, text=True).strip()

            def commit(label):
                git("add", ".")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", label)
                return git("rev-parse", "HEAD")

            git("init", "-q")
            source = commit("original kit")
            good = commit("descendant")
            (kit / "self-map.json").write_text('{"changed": true}\n', encoding="utf-8")
            modified = commit("changed kit")
            # Running the history gates for real is the point of this case.
            def history_only(*args):
                subprocess.run(args, cwd=root, capture_output=True, check=True)

            stage = root / "stage"
            for pinned, head, reaches_install in ((source, good, True), (modified, good, False), (source, modified, False)):
                with self.subTest(head=head, source=pinned), patch.object(
                    verify_archive, "run", side_effect=history_only
                ), patch.object(verify_archive.venv, "create", side_effect=RuntimeError("install boundary")):
                    error = RuntimeError if reaches_install else subprocess.CalledProcessError
                    with self.assertRaises(error) as caught:
                        verify_archive.verify_version("v1.0.0", {"source_commit": pinned, "source_repository": "sample/old"},
                                                      head, stage, "local", "sample/current", None)
                    if reaches_install:
                        self.assertEqual(str(caught.exception), "install boundary")

    def test_GHQ_PY_021_enforces_numeric_archive_order_and_candidate_rules(self):
        versions = {"v0.0.10": {"source_commit": None}, "v0.0.9": {"source_commit": "a" * 40}}
        with patch.dict(os.environ), patch.object(verify_archive.Path, "read_text") as read, patch.object(
            verify_archive, "verify_version"
        ) as verify, patch.object(verify_archive, "git_head", return_value="b" * 40), patch.object(
            verify_archive, "execution_mode", return_value="local"
        ), patch.object(verify_archive, "local_repository", return_value="test/current"), patch.object(
            sys, "argv", ["verify_archive.py"]
        ), redirect_stdout(io.StringIO()):
            read.return_value = json.dumps({"latest": "v0.0.10", "versions": versions})
            verify_archive.main()
            self.assertEqual([call.args[0] for call in verify.call_args_list], ["v0.0.9", "v0.0.10"])
            read.return_value = json.dumps({"latest": "v0.0.9", "versions": versions})
            with self.assertRaisesRegex(ValueError, "highest version"):
                verify_archive.main()
            versions["v0.0.9"]["source_commit"] = None
            read.return_value = json.dumps({"latest": "v0.0.10", "versions": versions})
            with self.assertRaisesRegex(ValueError, "Only the latest"):
                verify_archive.main()

    def test_GHQ_PY_022_keeps_frozen_source_identity_across_a_rename(self):
        existing_cases(mode_tests.ExecutionModeTests, "test_historical_repository_identity_survives_rename")
        with tempfile.TemporaryDirectory() as directory, patch.object(
            verify_archive.Path, "read_text", return_value="{}"
        ), patch.object(verify_archive, "run") as recorded, patch.object(
            verify_archive.venv, "create"
        ), patch.object(verify_archive, "export_candidate"), redirect_stdout(io.StringIO()):
            root = Path(directory)
            for pinned, expected_repo, expected_sha in (
                ("a" * 40, "sample/previous", "a" * 40), (None, "sample/current", "b" * 40),
            ):
                recorded.reset_mock()
                verify_archive.verify_version("v1.0.0", {"source_commit": pinned, "source_repository": "sample/previous"},
                                              "b" * 40, root, "local", "sample/current", None)
                with (root / "manifest.json").open() as manifest:
                    self.assertEqual(json.load(manifest), {"repository": expected_repo, "source_commit": expected_sha})
                calls = [call.args for call in recorded.call_args_list if "evidence_map.py" in str(call.args)]
                if pinned:
                    self.assertEqual([call[-2:] for call in calls], [("graphify/v1.0.0", "--check")])
                else:
                    self.assertEqual([call[-1] for call in calls], [str(root / "candidate"), "--check"])


if __name__ == "__main__":
    unittest.main()
