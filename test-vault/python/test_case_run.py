import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
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
        marker = "// GHQ-TS-001: first\n// @ts-expect-error narrowing\nresult.citations;\n"
        file_list = "/workspace/test-vault/typescript/citations.types.ts\n"
        with self.assertRaisesRegex(ValueError, "did not check"):
            typed_passes("tsc --noEmit\n", marker)
        self.assertEqual(typed_passes(file_list, marker), ["GHQ-TS-001"])
        self.assertEqual(typed_passes(file_list, marker.replace("@ts-expect-error", "ordinary comment")), [])

    def test_GHQ_PY_026_does_not_count_an_overall_go_pass_as_a_subtest_pass(self):
        log = (
            '{"Action":"pass","Test":"TestGraphifyMCP/GHQ-GO-001_discover"}\n'
            '{"Action":"skip","Test":"TestGraphifyMCP/GHQ-GO-002_read"}\n'
            '{"Action":"pass","Test":"TestGraphifyMCP"}\n'
            '{"Action":"pass","Package":"graphify-hq/test-vault/mcp"}\n'
        )
        with self.assertRaisesRegex(ValueError, "missing=.*GHQ-GO-002"):
            require_cases({"GHQ-GO-001", "GHQ-GO-002"}, passed_cases("GO", log))

    def test_GHQ_PY_027_refuses_to_issue_a_receipt_after_the_observation_changes(self):
        recorder = Path(__file__).resolve().parents[1] / "record_handoff.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipts = root / "receipts"
            (root / "graph.json").write_bytes(b"{}\n")
            (root / "node.sha256").write_text("f" * 64 + "\n", encoding="ascii")
            result = subprocess.run(
                [sys.executable, "-B", str(recorder), "node-consume", str(root), str(receipts), "--runtime", "Node fixture"],
                env=dict(os.environ, GITHUB_RUN_ID="12", GITHUB_RUN_ATTEMPT="1"),
                capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("graph changed after node-consume observed it", result.stderr)
            self.assertFalse(receipts.exists())


if __name__ == "__main__":
    unittest.main()
