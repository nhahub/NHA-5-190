#!/usr/bin/env python3
"""Validate committed repository structure and the shared M1 manifest."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from wardiq.data import validate_manifest  # noqa: E402

REQUIRED_PATHS = (
    "README.md",
    "CONTRIBUTING.md",
    "pyproject.toml",
    "data/README.md",
    "data/manifests/raw_manifest.csv",
    "docs/proposal/PROJECT_PROPOSAL.md",
    "docs/architecture/system-overview.md",
    "docs/team/OWNERSHIP.md",
    "docs/milestones/M1.md",
    ".github/workflows/ci.yml",
)


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    if missing:
        print("Missing required repository paths:")
        for path in missing:
            print(f"- {path}")
        return 1
    report = validate_manifest(ROOT / "data/manifests/raw_manifest.csv")
    print(f"Repository structure: OK ({len(REQUIRED_PATHS)} required paths)")
    print(f"Manifest: {report.rows:,} rows, {report.unique_item_ids:,} unique IDs")
    print(f"Datasets: {', '.join(report.datasets)}")
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_artifacts.py")], cwd=ROOT, check=False
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
