import unittest
from pathlib import Path

from wardiq.data import validate_manifest


FIXTURES = Path(__file__).parent / "fixtures"


class ManifestValidationTests(unittest.TestCase):
    def test_reports_rows_and_datasets(self):
        report = validate_manifest(FIXTURES / "valid_manifest.csv")
        self.assertEqual(report.rows, 2)
        self.assertEqual(report.unique_item_ids, 2)
        self.assertEqual(report.datasets, ("example",))

    def test_rejects_duplicate_item_ids(self):
        with self.assertRaisesRegex(ValueError, "Duplicate item_id"):
            validate_manifest(FIXTURES / "duplicate_manifest.csv")


if __name__ == "__main__":
    unittest.main()
