"""Validate independent source samples; failures return nonzero to callers."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.research_cli import protect_evidence  # noqa: E402

FIELDS = ("path", "valid", "width", "height", "format", "mode", "error")


def inspect_image(path: Path) -> dict[str, str]:
    """Verify file structure and actually decode pixels, with explicit failure data."""
    from PIL import Image

    row = dict.fromkeys(FIELDS, "")
    row.update(path=path.as_posix(), valid="false")
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            row.update(
                valid="true",
                width=str(image.width),
                height=str(image.height),
                format=image.format or "",
                mode=image.mode,
            )
    except (OSError, ValueError, Image.DecompressionBombError) as exc:
        row["error"] = str(exc)
    return row


def sample_paths(root: Path) -> list[Path]:
    """Exclude annotated previews and contact sheets from independent source counts."""
    return sorted(
        p
        for p in root.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        and "annotated" not in p.relative_to(root).parts
        and "contact_sheet" not in p.stem.lower()
    )


def validation_status(rows: list[dict[str, str]]) -> int:
    """No input is an error; any corrupt image fails the validation gate."""
    if not rows:
        return 2
    return int(any(row["valid"] != "true" for row in rows))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, default=ROOT / "data/samples")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/m1/quality/sample_image_validation.csv"
    )
    args = parser.parse_args()
    try:
        protect_evidence(args.output)
        paths = sample_paths(args.samples)
        if not paths:
            print("No source sample images found; check --samples.", file=sys.stderr)
            return 2
        rows = [inspect_image(path) for path in paths]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        failures = sum(row["valid"] != "true" for row in rows)
        print(f"Source samples: {len(rows)}; valid: {len(rows) - failures}; invalid: {failures}")
        return validation_status(rows)
    except (OSError, ValueError, ImportError) as exc:
        print(f"Image validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
