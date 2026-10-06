"""Report reference-level duplication; this is not visual or cross-split leakage proof."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.research_cli import protect_evidence  # noqa: E402


def duplicate_members(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Report duplicate source references while keeping different datasets separate."""
    output = []
    checks = {
        "item_id": ("item_id",),
        "exact_manifest_row": tuple(sorted(rows[0])) if rows else (),
        "source_identity": ("source_dataset", "source_split", "source_index"),
        "source_image_id": ("source_dataset", "source_split", "source_image_id"),
        "original_reference": ("source_dataset", "original_image_reference"),
    }
    for kind, fields in checks.items():
        groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
        for row in rows:
            key = tuple(row.get(field, "") for field in fields)
            if kind == "exact_manifest_row" or all(key):
                groups[key].append(row["item_id"])
        for key, members in sorted(groups.items()):
            if len(members) > 1:
                for item_id in members:
                    output.append(
                        {"duplicate_type": kind, "group_key": repr(key), "item_id": item_id}
                    )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/manifests/raw_manifest.csv")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "artifacts/m1/quality/duplicate_groups.csv"
    )
    args = parser.parse_args()
    try:
        protect_evidence(args.output)
        with args.input.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = {
                "item_id",
                "source_dataset",
                "source_split",
                "source_index",
                "source_image_id",
                "original_image_reference",
            }
            if not required <= set(reader.fieldnames or []):
                raise ValueError("Missing duplicate-check columns")
            rows = list(reader)
        if not rows:
            raise ValueError("Input contains no rows")
        groups = duplicate_members(rows)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=["duplicate_type", "group_key", "item_id"], lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(groups)
        print(f"Checked {len(rows)} records; {len(groups)} duplicate memberships")
        return int(bool(groups))
    except (OSError, ValueError, KeyError) as exc:
        print(f"Duplicate validation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
