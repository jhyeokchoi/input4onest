import argparse
import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from input4onest import (
    CestData,
    ConversionError,
    ResidueRecord,
    estimate_error,
    filter_data,
    read_cest_data,
)


ROOT = Path(__file__).parent
SCRIPT = ROOT / "input4onest.py"


class Input4onestTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.directory = Path(self.temp_dir.name)

    def write_tsv(self, name, rows):
        path = self.directory / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, delimiter="\t", lineterminator="\n").writerows(rows)
        return path

    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, arguments)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_example_converts_successfully(self):
        output = self.directory / "example.out"
        result = self.run_cli("-f", ROOT / "example/example_input.tsv", "-o", output)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = output.read_text(encoding="utf-8")
        self.assertIn("#\tA1\tR2a:\t25.0", content)
        self.assertIn("#\tG2\tR2a:\t25.0", content)
        self.assertNotIn("nan", content.lower())

    def test_number_filter_uses_residue_number_not_row_position(self):
        data = read_cest_data(ROOT / "example/input_15hz.tsv")
        args = argparse.Namespace(select_number=[36], select_name=None)
        selected = filter_data(data, args)
        self.assertEqual([record.name for record in selected.records], ["I36"])

    def test_name_filter_matches_code_or_exact_id_only(self):
        data = CestData(
            (100.0, 101.0),
            (
                ResidueRecord("A1", (0.1, 0.2)),
                ResidueRecord("G2", (0.3, 0.4)),
                ResidueRecord("A3", (0.5, 0.6)),
            ),
        )
        by_code = filter_data(data, argparse.Namespace(select_number=None, select_name=["A"]))
        self.assertEqual([record.name for record in by_code.records], ["A1", "A3"])
        by_id = filter_data(data, argparse.Namespace(select_number=None, select_name=["G2"]))
        self.assertEqual([record.name for record in by_id.records], ["G2"])
        with self.assertRaises(ConversionError):
            filter_data(data, argparse.Namespace(select_number=None, select_name=["."]))

    def test_missing_selection_is_an_error_and_creates_no_output(self):
        output = self.directory / "empty.out"
        result = self.run_cli(
            "-f", ROOT / "example/example_input.tsv", "-o", output, "-s", "999"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not found", result.stderr)
        self.assertFalse(output.exists())

    def test_invalid_intensity_does_not_replace_existing_output(self):
        source = self.write_tsv(
            "bad.tsv",
            [["Residue", "100", "101"], ["A1", "0.9", "oops"]],
        )
        output = self.directory / "existing.out"
        output.write_text("keep me", encoding="utf-8")
        result = self.run_cli("-f", source, "-o", output)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("row 2, column 3", result.stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "keep me")

    def test_invalid_offset_is_reported_instead_of_skipped(self):
        source = self.write_tsv(
            "bad-header.tsv",
            [["Residue", "100", "bad"], ["A1", "0.9", "0.8"]],
        )
        result = self.run_cli("-f", source, "-o", self.directory / "bad.out")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("offset header at column 3", result.stderr)

    def test_one_offset_is_rejected(self):
        source = self.write_tsv("short.tsv", [["Residue", "100"], ["A1", "0.9"]])
        result = self.run_cli("-f", source, "-o", self.directory / "short.out")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("at least two offset columns", result.stderr)

    def test_error_estimation_uses_non_overlapping_edges(self):
        values = tuple(range(9)) + tuple(100 + value * 10 for value in range(9))
        self.assertAlmostEqual(estimate_error(values), estimate_error(values[:9]))
        self.assertAlmostEqual(estimate_error((1.0, 2.0)), 2 ** -0.5)

    def test_invalid_positive_parameter_is_rejected(self):
        output = self.directory / "bad-parameter.out"
        result = self.run_cli(
            "-f", ROOT / "example/example_input.tsv", "-o", output, "-mix", "0"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mixing time", result.stderr)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
