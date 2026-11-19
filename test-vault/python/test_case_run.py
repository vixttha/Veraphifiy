import json
import os
import select
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evidence_bundle import write_observation
from verify_case_run import passed_cases, require_cases, typed_passes


class CaseRunTests(unittest.TestCase):
    def test_GHQ_PY_023_rejects_missing_or_skipped_catalog_cases(self):
        expected = {"GHQ-JS-001", "GHQ-JS-002"}
        log = "ok 1 - GHQ-JS-001 passed\nok 2 - GHQ-JS-002 unavailable # SKIP\n"
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-JS-002"):
            require_cases(expected, passed_cases("JS", log))
        require_cases(expected, passed_cases("JS", log.replace(" # SKIP", "")))

    def test_GHQ_PY_024_rejects_duplicate_and_unexpected_case_reports(self):
        expected = {"GHQ-PS-001"}
        for log, diagnostic in (
            ("PASS GHQ-PS-001 ok\nPASS GHQ-PS-001 repeated\n", "duplicate=.*GHQ-PS-001"),
            ("PASS GHQ-PS-001 ok\nPASS GHQ-PS-002 unexpected\n", "unexpected=.*GHQ-PS-002"),
        ):
            with self.subTest(log=log), self.assertRaisesRegex(ValueError, diagnostic):
                require_cases(expected, passed_cases("PS", log))

    def test_GHQ_PY_025_requires_tsc_to_check_the_annotated_type_fixture(self):
        marker = "// GHQ-TS-001: TS2339 at citations\n"
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-TS-001"):
            typed_passes("citations.types.ts\n", marker)
        self.assertEqual(typed_passes("TYPE PASS GHQ-TS-001\n", marker), ["GHQ-TS-001"])
        with self.assertRaisesRegex(ValueError, "unexpected"):
            typed_passes("TYPE PASS GHQ-TS-002\n", marker)

    @staticmethod
    def go_log(*events):
        return "\n".join(json.dumps({"Package": "graphify-hq/test-vault/mcp", **event}) for event in events)

    def test_GHQ_PY_026_does_not_count_an_overall_go_pass_as_a_subtest_pass(self):
        log = self.go_log(
            {"Action": "pass", "Test": "TestGraphifyMCP/GHQ-GO-001_discover"},
            {"Action": "skip", "Test": "TestGraphifyMCP/GHQ-GO-002_read"},
            {"Action": "pass", "Test": "TestGraphifyMCP"},
            {"Action": "pass"},
        )
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-GO-002"):
            require_cases({"GHQ-GO-001", "GHQ-GO-002"}, passed_cases("GO", log))

    def test_GHQ_PY_027_refuses_to_issue_a_receipt_after_the_observation_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recorder, handoff, receipts = self.handoff_fixture(root)
            (handoff / "graph.json").write_bytes(b"[]\n")
            result = self.invoke_recorder(recorder, handoff, receipts)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bundle changed after node-consume observed it", result.stderr)
            self.assertFalse(receipts.exists())

    def handoff_fixture(self, root):
        upstream = Path(__file__).resolve().parents[1]
        vault = root / "test-vault"
        (vault / "javascript").mkdir(parents=True)
        for name in ("record_handoff.py", "evidence_bundle.py", "source_commit.py", "validate_catalog.py",
                     "verify_receipts.py", "cases.md", "javascript/case.json"):
            shutil.copyfile(upstream / name, vault / name)
        for command in (
            ["init", "-q"], ["add", "test-vault"],
            ["-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
             "-c", "commit.gpgsign=false", "commit", "-qm", "Track receipt tool inputs"],
        ):
            subprocess.run(["git", *command], cwd=root, check=True, capture_output=True)
        handoff = root / "handoff"
        handoff.mkdir()
        for name, value in {"graph.json": b"{}\n", "receipt.json": b"{}\n", "source.txt": b"source\n"}.items():
            (handoff / name).write_bytes(value)
        with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "12", "GITHUB_RUN_ATTEMPT": "1"}):
            for observer in ("python", "node"):
                write_observation(handoff, observer)
        return vault / "record_handoff.py", handoff, root / "receipts"

    @staticmethod
    def invoke_recorder(recorder, handoff, receipts, attempt="1", check="node-consume"):
        return subprocess.run(
            [sys.executable, "-B", str(recorder), check, str(handoff), str(receipts), "--runtime", "Node fixture"],
            cwd=recorder.parents[1], env=dict(os.environ, GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT=attempt),
            capture_output=True, text=True, timeout=10,
        )

    def test_GHQ_PY_032_binds_graph_receipt_and_independent_source_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            for name in ("receipt.json", "source.txt"):
                part = handoff / name
                original = part.read_bytes()
                part.write_bytes(original + b"changed")
                for check in ("python-build", "node-consume"):
                    result = self.invoke_recorder(recorder, handoff, receipts, check=check)
                    self.assertIn("bundle changed", result.stderr)
                    self.assertNotEqual(result.returncode, 0)
                self.assertFalse(receipts.exists())
                part.write_bytes(original)
            for check in ("python-build", "node-consume"):
                result = self.invoke_recorder(recorder, handoff, receipts, check=check)
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(list(receipts.glob("*.json"))), 2)

    def test_GHQ_PY_038_preserves_an_existing_complete_record(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            result = self.invoke_recorder(recorder, handoff, receipts)
            self.assertEqual(result.returncode, 0, result.stderr)
            target = receipts / "node-consume.json"
            recorded = target.read_bytes()
            result = self.invoke_recorder(recorder, handoff, receipts)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot publish receipt", result.stderr)
            self.assertEqual(target.read_bytes(), recorded)
            self.assertEqual(list(receipts.iterdir()), [target])

    def test_GHQ_PY_053_refuses_to_reuse_an_observation_from_an_earlier_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            result = self.invoke_recorder(recorder, handoff, receipts, attempt="2")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("different run or attempt", result.stderr)
            self.assertFalse(receipts.exists())
            with mock.patch.dict(os.environ, {"GITHUB_RUN_ID": "12", "GITHUB_RUN_ATTEMPT": "2"}):
                write_observation(handoff, "node")
            result = self.invoke_recorder(recorder, handoff, receipts, attempt="2")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_GHQ_PY_033_checks_the_real_compiler_error_location(self):
        suite = Path(__file__).resolve().parents[1] / "typescript"
        source = (suite / "citations.types.ts").read_text(encoding="utf-8")
        correct = 'path: "tools/verify_archive.py", line: "L30"'
        self.assertEqual(source.count(correct), 1)
        for fixture, should_pass in (
            (source, True),
            (source.replace(correct, "path: 100, line: 30"), False),
            (source.replace(correct, 'path: "tools/verify_archive.py", line: 30'), False),
        ):
            with self.subTest(should_pass=should_pass, fixture=fixture):
                result = subprocess.run(
                    ["node", str(suite / "check-type-cases.mjs"), "--stdin"],
                    input=fixture, text=True, capture_output=True, timeout=30,
                )
                self.assertEqual(result.returncode == 0, should_pass, result.stderr)
                if should_pass:
                    self.assertIn("GHQ-TS-002", typed_passes(result.stdout, source))
                else:
                    self.assertNotIn("TYPE PASS", result.stdout)

    def test_GHQ_PY_040_rejects_contradictory_native_results(self):
        go_test = {"Test": "TestGraphifyMCP/GHQ-GO-001_discover"}
        for status in ("fail", "skip"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "contradictory terminal outcomes"):
                    passed_cases("GO", self.go_log(
                        {**go_test, "Action": "pass"}, {**go_test, "Action": status}, {"Action": "pass"},
                    ))
        for tail in ("not ok 2 - GHQ-JS-001 failed", "ok 2 - GHQ-JS-001 later # SKIP"):
            with self.subTest(tail=tail), self.assertRaisesRegex(ValueError, "contradictory terminal outcomes"):
                passed_cases("JS", "ok 1 - GHQ-JS-001 first\n" + tail)

    def test_GHQ_PY_046_rejects_blank_runtime_before_writing_receipt(self):
        recorder = Path(__file__).resolve().parents[1] / "record_handoff.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for runtime in ("", "  "):
                with self.subTest(runtime=runtime):
                    result = subprocess.run(
                        [sys.executable, "-B", str(recorder), "node-consume", str(root), str(root / "receipts"),
                         "--runtime", runtime],
                        env=dict(os.environ, GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT="1"),
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("runtime must be nonempty", result.stderr)
                    self.assertFalse((root / "receipts").exists())

    def test_GHQ_PY_051_requires_a_passing_terminal_package_event(self):
        named_pass = {"Action": "pass", "Test": "TestGraphifyMCP/GHQ-GO-001_discover"}
        terminal_pass = {"Action": "pass"}
        self.assertEqual(passed_cases("GO", self.go_log(named_pass, terminal_pass)), ["GHQ-GO-001"])
        for events in ((), ({"Action": "fail"},), (terminal_pass, terminal_pass)):
            with self.subTest(events=events), self.assertRaisesRegex(ValueError, "passing terminal result"):
                passed_cases("GO", self.go_log(named_pass, *events))

    def test_GHQ_PY_056_reports_available_failures_and_missing_suites(self):
        reconciler = Path(__file__).resolve().parents[1] / "verify_case_run.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "js.log").write_text(
                "not ok 1 - GHQ-JS-001 failed\nok 2 - GHQ-JS-002 passed\n", encoding="utf-8",
            )
            (root / "go.log").write_text(self.go_log(
                {"Action": "fail", "Test": "TestGraphifyMCP/GHQ-GO-001_discover"},
                {"Action": "fail"},
            ), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(reconciler), "linux", str(root)],
                capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("JS: failed or skipped cases=['GHQ-JS-001']", result.stderr)
            self.assertIn("GO: failed or skipped cases=['GHQ-GO-001']", result.stderr)
            self.assertIn("SH: no native log, suite unavailable", result.stderr)

    def test_GHQ_PY_041_rejects_malformed_environment_on_specific_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            vault = recorder.parent
            for check in ("python-build", "node-consume"):
                result = self.invoke_recorder(recorder, handoff, receipts, check=check)
                self.assertEqual(result.returncode, 0, result.stderr)
            evidence = handoff / "evidence.bin"
            subprocess.run([sys.executable, "-B", str(vault / "evidence_bundle.py"), str(handoff)], check=True)
            command = [sys.executable, "-B", str(vault / "verify_receipts.py"), "--case",
                       str(vault / "javascript/case.json"), "--receipts", str(receipts), "--evidence",
                       str(evidence), "--run-id", "12", "--attempt", "1"]
            def verify():
                return subprocess.run(command, cwd=vault.parent, text=True, capture_output=True, timeout=10)

            result = verify()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            target = receipts / "node-consume.json"
            valid = json.loads(target.read_bytes())
            for environment in ({"os": "Linux", "runtime": ""}, {"runtime": "node"}, {"os": "Linux", "runtime": 9}):
                with self.subTest(environment=environment):
                    target.write_text(json.dumps(dict(valid, environment=environment)), encoding="utf-8")
                    result = verify()
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn("| node-consume | INVALID |", result.stdout)
                    self.assertIn("environment", result.stdout)
                    self.assertIn("| python-build | PASS |", result.stdout)

    def test_GHQ_PY_047_killed_receipt_writer_does_not_occupy_final_path(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            pause = """
import record_handoff, time
def partial_write(value, output, **kwargs):
    output.write("{")
    output.flush()
    print("staged partial receipt", flush=True)
    time.sleep(120)
record_handoff.json.dump = partial_write
record_handoff.main()
"""
            environment = dict(os.environ, PYTHONPATH=str(recorder.parent), GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT="1")
            with subprocess.Popen(
                [sys.executable, "-B", "-c", pause, "node-consume", str(handoff), str(receipts),
                 "--runtime", "Node fixture"], cwd=recorder.parents[1], env=environment,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ) as process:
                try:
                    ready, _, _ = select.select([process.stdout], [], [], 15)
                    self.assertTrue(ready, "recorder did not reach the partial-write boundary")
                    self.assertEqual(process.stdout.readline().strip(), b"staged partial receipt")
                finally:
                    process.kill()
                    process.communicate(timeout=10)
            self.assertEqual(list(receipts.glob("*.json")), [])
            self.assertEqual([path.read_bytes() for path in receipts.iterdir()], [b"{"])
            retry = self.invoke_recorder(recorder, handoff, receipts)
            self.assertEqual(retry.returncode, 0, retry.stderr)
            published, = receipts.glob("*.json")
            self.assertEqual(json.loads(published.read_bytes())["check_id"], "node-consume")


if __name__ == "__main__":
    unittest.main()
