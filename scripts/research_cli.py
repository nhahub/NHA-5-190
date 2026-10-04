"""Portable command-line defaults for Eyad's existing dataset research scripts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/research/m1.json"
ACTIVE_CONFIG = DEFAULT_CONFIG


def read_settings(path: Path, name: str) -> dict[str, str | int]:
    """Read and validate a versioned research configuration section."""
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("schema_version") != "wardiq.research.v1":
        raise ValueError("Unsupported research configuration schema_version")
    settings = config.get(name)
    if not isinstance(settings, dict) or not settings:
        raise ValueError(f"Missing research configuration section: {name}")
    for key, value in settings.items():
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ValueError(f"Invalid configuration value: {name}.{key}")
        if isinstance(value, int) and value < 1:
            raise ValueError(f"Expected positive integer: {name}.{key}")
        if isinstance(value, str) and not value:
            raise ValueError(f"Expected nonempty path: {name}.{key}")
    return settings


def arguments(name: str) -> argparse.Namespace:
    """Build CLI options from the versioned defaults, resolving paths at repo root."""
    global ACTIVE_CONFIG
    preliminary = argparse.ArgumentParser(add_help=False)
    preliminary.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    known, _ = preliminary.parse_known_args()
    config_path = known.config.resolve()
    try:
        settings = read_settings(config_path, name)
    except (OSError, ValueError) as error:
        preliminary.error(str(error))
    parser = argparse.ArgumentParser(description=f"Reproduce {name}; preserve committed evidence.")
    parser.add_argument("--config", type=Path, default=config_path)
    for key, value in settings.items():
        option = "--" + key.replace("_", "-")
        parser.add_argument(option, type=int if isinstance(value, int) else Path, default=value)
    args = parser.parse_args()
    ACTIVE_CONFIG = config_path
    for key, value in settings.items():
        selected = getattr(args, key)
        if isinstance(value, int):
            if selected < 1:
                parser.error(f"--{key.replace('_', '-')} must be positive")
        else:
            path = Path(selected)
            setattr(
                args, key, (ROOT / path).resolve() if not path.is_absolute() else path.resolve()
            )
    return args


def require_files(*paths: Path) -> None:
    """Fail clearly before generating output when required source files are absent."""
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required raw inputs missing: " + "; ".join(missing))


def protect_evidence(output: Path) -> None:
    """Refuse outputs inside committed evidence or the Python source tree."""
    output = output.resolve()
    protected = ("data/manifests", "data/samples", "docs", "src", "configs")
    for name in protected:
        base = (ROOT / name).resolve()
        if output == base or base in output.parents:
            raise ValueError(f"Output would change protected repository content: {output}")


def run(main: Callable[[], None]) -> None:
    """Give research commands a concise failure message and nonzero exit status."""
    try:
        main()
        if "--help" not in sys.argv and "-h" not in sys.argv:
            log_dir = ROOT / "artifacts/research_runs"
            log_dir.mkdir(parents=True, exist_ok=True)
            revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            dirty = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            record = {
                "schema_version": "wardiq.research_run.v1",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "command": sys.argv,
                "git_commit": revision.stdout.strip() if revision.returncode == 0 else None,
                "working_tree_dirty": bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
                "config_sha256": None,
                "status": "succeeded",
            }
            import hashlib

            record["config_sha256"] = hashlib.sha256(ACTIVE_CONFIG.read_bytes()).hexdigest()
            with (log_dir / "runs.jsonl").open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record) + "\n")
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        raise SystemExit(f"Research command failed: {error}") from None
