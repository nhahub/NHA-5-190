"""Regression checks for repository infrastructure, not milestone implementation."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_artifacts", Path(__file__).parents[1] / "scripts" / "check_artifacts.py"
)
assert SPEC is not None and SPEC.loader is not None
ARTIFACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACTS)


class ArtifactPolicyTests(unittest.TestCase):
    def test_small_source_file_allowed(self) -> None:
        self.assertEqual(ARTIFACTS.inspect_artifact("src/wardiq/example.py", b"pass\n"), [])
        self.assertEqual(ARTIFACTS.inspect_artifact("configs/models/.gitkeep", b""), [])

    def test_unexpected_large_file_rejected(self) -> None:
        self.assertIn(
            "file exceeds 5 MiB",
            ARTIFACTS.inspect_artifact("data/manifests/new.csv", b"x" * (ARTIFACTS.MAX_BYTES + 1)),
        )

    def test_raw_placeholder_requires_empty_content(self) -> None:
        self.assertEqual(ARTIFACTS.inspect_artifact("data/raw/.gitkeep", b""), [])
        self.assertTrue(ARTIFACTS.inspect_artifact("data/raw/.gitkeep", b"source data"))

    def test_raw_data_and_weight_paths_rejected(self) -> None:
        for path in ("data/raw/image.jpg", "data/processed/result.csv", "model.pth"):
            with self.subTest(path=path):
                self.assertTrue(ARTIFACTS.inspect_artifact(path, b"example"))

    def test_env_example_allowed_but_local_env_rejected(self) -> None:
        self.assertEqual(ARTIFACTS.inspect_artifact(".env.example", b"SETTING=example"), [])
        self.assertTrue(ARTIFACTS.inspect_artifact(".env", b"SETTING=value"))

    def test_secret_detection_does_not_report_value(self) -> None:
        value = b"gh" + b"p_" + b"a" * 36
        result = ARTIFACTS.inspect_artifact("settings.txt", value)
        self.assertEqual(result, ["GitHub token pattern"])
        self.assertNotIn(value.decode(), str(result))

    def test_changed_manifest_rejected(self) -> None:
        self.assertTrue(ARTIFACTS.inspect_artifact(ARTIFACTS.MANIFEST_PATH, b"changed"))

    def test_existing_manifest_allows_lf_and_crlf(self) -> None:
        path = Path(__file__).parents[1] / ARTIFACTS.MANIFEST_PATH
        lf = path.read_bytes().replace(b"\r\n", b"\n")
        for content in (lf, lf.replace(b"\n", b"\r\n")):
            self.assertEqual(ARTIFACTS.inspect_artifact(ARTIFACTS.MANIFEST_PATH, content), [])
