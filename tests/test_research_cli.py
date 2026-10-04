"""Checks for portable research-command configuration and evidence protection."""

import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "research_cli", Path(__file__).parents[1] / "scripts/research_cli.py"
)
assert SPEC is not None and SPEC.loader is not None
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


class ResearchCommandTests(unittest.TestCase):
    def test_versioned_defaults_load(self) -> None:
        settings = CLI.read_settings(CLI.DEFAULT_CONFIG, "export_fashion_mnist_samples")
        self.assertEqual(settings["count"], 5)

    def test_invalid_schema_rejected(self) -> None:
        with patch.object(Path, "read_text", return_value='{"schema_version":"unknown"}'):
            with self.assertRaisesRegex(ValueError, "schema_version"):
                CLI.read_settings(CLI.DEFAULT_CONFIG, "build_raw_manifest")

    def test_invalid_count_rejected(self) -> None:
        config = {"schema_version": "wardiq.research.v1", "example": {"count": 0}}
        with patch.object(Path, "read_text", return_value=json.dumps(config)):
            with self.assertRaisesRegex(ValueError, "positive"):
                CLI.read_settings(CLI.DEFAULT_CONFIG, "example")

    def test_committed_evidence_cannot_be_output(self) -> None:
        for relative in ("data/manifests/raw_manifest.csv", "data/samples/new", "docs/new"):
            with self.subTest(relative=relative):
                with self.assertRaisesRegex(ValueError, "protected"):
                    CLI.protect_evidence(CLI.ROOT / relative)
        CLI.protect_evidence(CLI.ROOT / "artifacts/m1/new.csv")
