"""Check inline Markdown file links; retain an explicit counted Phase 0 baseline."""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "configs/ci/link-baseline.json"


def local_targets(markdown: str) -> list[str]:
    """Extract inline local links outside fenced code, ignoring URLs and anchors."""
    lines = []
    fence = ""
    for line in markdown.splitlines():
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker = match.group(1)[0]
            if not fence:
                fence = marker
            elif marker == fence:
                fence = ""
            continue
        if not fence:
            lines.append(line)
    targets = []
    pattern = r"\[[^\]\n]*\]\((<[^>\n]+>|[^\s)]+)(?:\s+[^)]+)?\)"
    for match in re.finditer(pattern, "\n".join(lines)):
        target = match.group(1).strip("<>")
        parsed = urlsplit(target)
        if not parsed.scheme and not parsed.netloc and parsed.path:
            targets.append(unquote(parsed.path))
    return targets


def baseline_changes(
    actual: Counter[tuple[str, str]], baseline: Counter[tuple[str, str]]
) -> tuple[Counter[tuple[str, str]], Counter[tuple[str, str]]]:
    """Reject new occurrences and require removal of fixed baseline entries."""
    return actual - baseline, baseline - actual


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    files = sorted(set(result.stdout.decode("utf-8").strip("\0").split("\0")))
    broken: Counter[tuple[str, str]] = Counter()
    checked = 0
    for filename in files:
        path = ROOT / filename
        if path.suffix != ".md" or not path.is_file():
            continue
        checked += 1
        for target in local_targets(path.read_text(encoding="utf-8")):
            destination = (
                ROOT / target.lstrip("/") if target.startswith("/") else path.parent / target
            )
            if not destination.exists():
                broken[(filename, target)] += 1
    entries = json.loads(BASELINE.read_text(encoding="utf-8"))
    baseline = Counter({(row["file"], row["target"]): row["count"] for row in entries})
    added, fixed = baseline_changes(broken, baseline)
    for label, changes in (("New broken link", added), ("Remove fixed baseline", fixed)):
        for (filename, target), count in sorted(changes.items()):
            print(f"{label}: {filename} -> {target} ({count} occurrences)")
    print(f"Checked {checked} Markdown files; {sum(broken.values())} baseline broken links remain.")
    return int(bool(added or fixed))


if __name__ == "__main__":
    raise SystemExit(main())
