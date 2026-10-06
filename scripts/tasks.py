"""Cross-platform quality commands using the caller's normal Python interpreter."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = [
    "src",
    "tests",
    "scripts/tasks.py",
    "scripts/validate_repository.py",
    "scripts/check_artifacts.py",
    "scripts/research_cli.py",
    "scripts/check_research_samples.py",
    "scripts/compare_manifest.py",
    "scripts/check_links.py",
    "scripts/prepare_clean_manifest.py",
    "scripts/check_manifest_duplicates.py",
    "scripts/validate_m1_images.py",
    "scripts/inspect_m1_manifest.py",
]


def main() -> int:
    """Run one explicit quality command and preserve its exit status."""
    commands = {
        "setup": ["-m", "pip", "install", "-e", ".[dev]"],
        "lint": ["-m", "ruff", "check", *SCOPE],
        "format": ["-m", "ruff", "format", *SCOPE],
        "format-check": ["-m", "ruff", "format", "--check", *SCOPE],
        "typecheck": ["-m", "mypy"],
        "test": ["-m", "pytest"],
        "validate": ["scripts/validate_repository.py"],
        "artifacts": ["scripts/check_artifacts.py"],
        "samples": ["scripts/check_research_samples.py"],
        "links": ["scripts/check_links.py"],
        "clean-manifest": ["scripts/prepare_clean_manifest.py"],
        "duplicates": ["scripts/check_manifest_duplicates.py"],
        "m1-images": ["scripts/validate_m1_images.py"],
        "m1-eda": ["scripts/inspect_m1_manifest.py"],
    }
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=commands)
    args = parser.parse_args()
    return subprocess.run([sys.executable, *commands[args.task]], cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
