"""Check staged or working-tree files for repository artifact-policy violations."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 5 * 1024 * 1024
MANIFEST_PATH = "data/manifests/raw_manifest.csv"
MANIFEST_SHA256 = "84135923763f5fec09471435c0f292730ac19715e6c491d16aceea17f6cca99e"
BLOCKED_DIRS = {
    "data/raw",
    "data/processed",
    "data/cache",
    "data/downloads",
    "artifacts",
    "checkpoints",
    "models",
    "runs",
    "wandb",
    "mlruns",
    ".venv",
    "venv",
    "tmp",
    "temp",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
BLOCKED_SUFFIXES = {".pt", ".pth", ".ckpt", ".onnx", ".pem", ".key", ".pyc", ".pyo"}
PATTERNS = {
    "private-key marker": re.compile(
        rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----"
    ),
    "GitHub token pattern": re.compile(
        rb"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})\b"
    ),
    "AWS access-key pattern": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
}


def inspect_artifact(path: str, content: bytes) -> list[str]:
    """Return safe descriptions of violations; never return matched secret values."""
    posix = PurePosixPath(path)
    lower = posix.as_posix().lower()
    if lower in {"data/raw/.gitkeep", "data/processed/.gitkeep"} and not content:
        return []
    issues = []
    if any(lower == d or lower.startswith(d + "/") for d in BLOCKED_DIRS):
        issues.append("raw/generated/cache directory")
    nested_caches = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
    if any(part.lower() in nested_caches for part in posix.parts):
        if "raw/generated/cache directory" not in issues:
            issues.append("raw/generated/cache directory")
    if posix.suffix.lower() in BLOCKED_SUFFIXES:
        issues.append("weight, key, or bytecode extension")
    name = posix.name.lower()
    if name != ".env.example" and (name == ".env" or name.startswith(".env.")):
        issues.append("local environment file")
    if path == MANIFEST_PATH:
        # Git stores LF while Windows may check out CRLF. Protect the same logical file.
        digest = hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()
        if digest != MANIFEST_SHA256:
            issues.append("existing manifest changed; explicit reviewed policy update required")
    elif len(content) > MAX_BYTES:
        issues.append("file exceeds 5 MiB")
    for label, pattern in PATTERNS.items():
        if pattern.search(content):
            issues.append(label)
    return issues


def git_bytes(*args: str) -> bytes:
    """Read Git output and fail rather than silently skipping an inaccessible check."""
    return subprocess.check_output(["git", *args], cwd=ROOT)


def check_repository(staged: bool = False) -> int:
    """Check all index files, or tracked plus nonignored untracked working files."""
    args = ["ls-files", "-z"]
    if not staged:
        args.extend(["--cached", "--others", "--exclude-standard"])
    paths = sorted(set(p.decode("utf-8") for p in git_bytes(*args).split(b"\0") if p))
    failures = 0
    checked = 0
    for path in paths:
        local_path = ROOT / path
        if not staged and not local_path.exists():
            continue  # Working-tree deletion: no artifact will be read here.
        if not staged and local_path.is_symlink():
            print(f"FAIL {path}: symlink requires explicit review")
            failures += 1
            continue
        content = git_bytes("show", ":" + path) if staged else local_path.read_bytes()
        checked += 1
        issues = inspect_artifact(path, content)
        if issues:
            print(f"FAIL {path}: {'; '.join(issues)}")
            failures += 1
    mode = "index" if staged else "working tree"
    print(f"Artifact policy ({mode}): {checked} files checked, {failures} violations")
    return 1 if failures else 0


def main() -> int:
    """Run the artifact policy from a local command or pre-commit hook."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Read exact Git index contents")
    args = parser.parse_args()
    try:
        return check_repository(staged=args.staged)
    except (OSError, subprocess.CalledProcessError, UnicodeError) as error:
        print(f"Artifact check could not complete ({type(error).__name__}); review access")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
