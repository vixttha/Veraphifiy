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
from evidence_bundle import PROFILE, encode_bundle, write_observation
from validate_catalog import HEADER, read_cases
from verify_case_run import (
    POWERSHELL_COMPLETE, passed_cases, require_cases, require_complete_tap, require_complete_unittest, typed_passes,
)


class CaseRunTests(unittest.TestCase):
    def test_GHQ_PY_108_requires_successful_powershell_completion_on_replay(self):
        vault = Path(__file__).resolve().parents[1]
        catalog, _ = read_cases(vault / "cases.md")
        cases = sorted(case for case in catalog if case.startswith("GHQ-PS-"))
        records = "".join(f"PASS {case} fixture passed\n" for case in cases)
        complete = f"{records}{POWERSHELL_COMPLETE}\n"
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "ps.log"
            for content, diagnostic in (
                (complete, None),
                (records, "PowerShell completion record"),
                (records + "Late failure before completion\n", "PowerShell completion record"),
                (complete + "Late failure after completion\n", "PowerShell completion record"),
                (complete + POWERSHELL_COMPLETE + "\n", "PowerShell completion record"),
                (complete.replace(f"PASS {cases[0]}", f"SKIP {cases[0]}"), f"missing=['{cases[0]}'"),
            ):
                with self.subTest(diagnostic=diagnostic, length=len(content)):
                    log.write_text(content, encoding="utf-8")
                    run = subprocess.run(
                        [sys.executable, "-B", str(vault / "verify_case_run.py"), "windows", directory],
                        capture_output=True, text=True, timeout=10,
                    )
                    if diagnostic is None:
                        self.assertEqual(run.returncode, 0, run.stderr)
                        self.assertIn(f"PS: {len(cases)} catalog checks accounted for", run.stdout)
                    else:
                        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
                        self.assertIn(diagnostic, run.stderr)

    def test_GHQ_PY_023_rejects_missing_or_skipped_catalog_cases(self):
        expected = {"GHQ-JS-001", "GHQ-JS-002"}
        log = "ok 1 - GHQ-JS-001 passed\nok 2 - GHQ-JS-002 unavailable # SKIP\n"
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-JS-002"):
            require_cases(expected, passed_cases("JS", log))
        require_cases(expected, passed_cases("JS", log.replace(" # SKIP", "")))

        typed_expected = {"GHQ-TS-001", "GHQ-TS-004"}
        complete = "ok 1 - GHQ-TS-001 control\nok 2 - GHQ-TS-004 implementation coordinates\n"
        require_cases(typed_expected, passed_cases("TS", complete))
        omitted = complete.replace("GHQ-TS-004 implementation coordinates", "unrelated passing assertion")
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-TS-004"):
            require_cases(typed_expected, passed_cases("TS", omitted))

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
                     "verify_receipts.py", "cases.md", "javascript/case.json", "handoff-profile.json"):
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
        for name in PROFILE["files"]:
            if name.startswith("source-blobs/"):
                path = handoff / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic source\n")
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
            for name in ("receipt.json", "source.txt", "source-blobs/src/feature.py"):
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
            path = handoff / "node.observation.json"
            original = path.read_text(encoding="utf-8")
            observation = json.loads(original)
            observation["check_id"] = "python-build"
            path.write_text(json.dumps(observation), encoding="utf-8")
            wrong_check = self.invoke_recorder(recorder, handoff, receipts, attempt="2")
            self.assertNotEqual(wrong_check.returncode, 0)
            self.assertIn("belongs to a different check", wrong_check.stderr)
            self.assertFalse(receipts.exists())
            path.write_text(original, encoding="utf-8")
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
            summary = root / "summary.md"
            result = subprocess.run(
                [sys.executable, "-B", str(reconciler), "linux", str(root)],
                env=dict(os.environ, GITHUB_STEP_SUMMARY=str(summary)),
                capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("JS: failed or skipped cases=['GHQ-JS-001']", result.stderr)
            self.assertIn("GO: failed or skipped cases=['GHQ-GO-001']", result.stderr)
            self.assertIn("SH: no native log, suite unavailable", result.stderr)
            retained = summary.read_text(encoding="utf-8")
            self.assertIn("GHQ-JS-001", retained)
            self.assertIn("no native log", retained)

    def test_GHQ_PY_057_requires_complete_native_tap_and_rejects_unnamed_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "fixture.test.mjs"
            command = ["node", "--test", "--test-reporter=tap", str(fixture)]
            for assertion in ("", 'throw new Error("fixture failure");'):
                with self.subTest(assertion=assertion):
                    fixture.write_text(
                        'import { test } from "node:test";\n'
                        'test("GHQ-JS-001 registered control", () => {});\n'
                        f'test("ordinary assertion", () => {{ {assertion} }});\n',
                        encoding="utf-8",
                    )
                    result = subprocess.run(command, capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, int(bool(assertion)), result.stderr)
                    require_cases({"GHQ-JS-001"}, passed_cases("JS", result.stdout))
                    if assertion:
                        with self.assertRaisesRegex(ValueError, "uncataloged TAP failure: ordinary assertion"):
                            require_complete_tap(result.stdout)
                    else:
                        require_complete_tap(result.stdout)
                        with self.assertRaisesRegex(ValueError, "incomplete native TAP summary"):
                            require_complete_tap(result.stdout.split("# tests", 1)[0])
                        with self.assertRaisesRegex(ValueError, "plan does not match"):
                            require_complete_tap(result.stdout.replace("1..2\n", "1..3\n"))

    def test_GHQ_PY_104_requires_complete_native_unittest_output(self):
        fixture = """
import unittest

class Fixture(unittest.TestCase):
    def test_GHQ_PY_001_control(self):
        pass

    def test_ordinary_assertion(self):
        OUTCOME

    @unittest.skip("optional fixture")
    def test_optional_assertion(self):
        pass

if __name__ == "__main__":
    unittest.main(verbosity=2)
"""
        command = [sys.executable, "-B", "-"]
        for outcome in ("pass", "self.fail('ordinary assertion')"):
            with self.subTest(outcome=outcome):
                native = subprocess.run(command, input=fixture.replace("OUTCOME", outcome),
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(native.returncode, int(outcome != "pass"), native.stderr)
                log = native.stderr
                require_cases({"GHQ-PY-001"}, passed_cases("PY", log))
                if outcome != "pass":
                    with self.assertRaisesRegex(ValueError, "native unittest suite failed"):
                        require_complete_unittest(log)
                else:
                    require_complete_unittest(log)
                    for incomplete, error in (
                        (log.split("Ran ", 1)[0], "unittest summary"),
                        (log.split("OK (", 1)[0], "unittest verdict"),
                        (log.replace("Ran 3 tests", "Ran 4 tests"), "does not match"),
                        (log + log, "unittest summary"),
                    ):
                        with self.assertRaisesRegex(ValueError, error):
                            require_complete_unittest(incomplete)

    def test_GHQ_PY_058_keeps_only_visible_well_formed_case_tables(self):
        heading = "| " + " | ".join(HEADER) + " |\n"
        divider = "| --- | --- | --- | --- | --- |\n"
        row = "| GHQ-JS-001 | Graph | P0 | Read graph | Source verified |\n"
        second = row.replace("JS-001", "JS-002")
        table = heading + divider + row
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "cases.md"
            example = '<PRE class="example">\n' + heading + divider + second + "</pRe>\n"
            catalog.write_text(example + "\n" + table, encoding="utf-8")
            self.assertEqual(read_cases(catalog)[0], {"GHQ-JS-001"})
            catalog.write_text(table + "\n" + heading + divider + second, encoding="utf-8")
            self.assertEqual(read_cases(catalog)[0], {"GHQ-JS-001", "GHQ-JS-002"})
            for suffix, diagnostic in (
                (heading.replace("Area", "Scope").replace("Expected outcome", "Proof") + divider + second,
                 "invalid case table header"),
                (second, "case row outside a case table"),
                (heading + divider + second.replace("Source verified", "<!-- Source verified -->"), "invalid case row"),
            ):
                with self.subTest(diagnostic=diagnostic):
                    catalog.write_text(table + "\n" + suffix, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, diagnostic):
                        read_cases(catalog)

    def test_GHQ_PY_059_bounds_the_bundle_before_recording_or_replaying_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder, handoff, receipts = self.handoff_fixture(Path(directory))
            bundle = encode_bundle(handoff)
            self.assertEqual(encode_bundle(handoff, maximum=len(bundle)), bundle)
            with self.assertRaisesRegex(ValueError, "remaining handoff byte budget"):
                encode_bundle(handoff, maximum=len(bundle) - 1)
            for name in PROFILE["files"]:
                with self.subTest(part=name), self.assertRaisesRegex(ValueError, "exceeds its byte budget"):
                    encode_bundle(handoff, limits={name: 1})
            pin = handoff / "source.txt"
            original = pin.read_bytes()
            pin.write_bytes(b"x" * (PROFILE["files"]["source.txt"] + 1))
            failed = self.invoke_recorder(recorder, handoff, receipts, "1", "python-build")
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("source.txt exceeds its byte budget", failed.stderr)
            self.assertFalse(receipts.exists())
            pin.write_bytes(original)
            valid = self.invoke_recorder(recorder, handoff, receipts, "1", "python-build")
            self.assertEqual(valid.returncode, 0, valid.stderr)

    def test_GHQ_PY_060_rejects_an_executable_case_outside_the_supported_namespaces(self):
        with tempfile.TemporaryDirectory() as directory:
            vault = Path(directory)
            actual_vault = Path(__file__).resolve().parents[1]
            for name in ("verify_case_run.py", "validate_catalog.py", "cases.md"):
                shutil.copyfile(actual_vault / name, vault / name)
            catalog = vault / "cases.md"
            original = catalog.read_text(encoding="utf-8")
            for foreign_id in ("ALT-PY-001", "GHQ-JAVA-001", "GHQ-PY-SUB-001"):
                with self.subTest(case=foreign_id):
                    catalog.write_text(original + f"| {foreign_id} | Fixture | P1 | Invoke | Pass |\n", encoding="utf-8")
                    self.assertIn(foreign_id, read_cases(catalog)[0])
                    result = subprocess.run(
                        [sys.executable, "-B", str(vault / "verify_case_run.py"), "linux", str(vault)],
                        capture_output=True, text=True, timeout=10,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(f"catalog case has no supported runner: {foreign_id}", result.stderr)

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
