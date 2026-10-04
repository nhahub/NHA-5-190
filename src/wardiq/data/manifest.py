"""Validation helpers for the shared image-level raw manifest."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REQUIRED_COLUMNS = (
    "item_id",
    "source_dataset",
    "source_release",
    "source_split",
    "source_index",
    "source_image_id",
    "original_filename",
    "original_image_reference",
    "annotation_reference",
    "category_ids",
    "category_labels",
    "attribute_ids",
    "annotation_ids",
    "outfit_ids",
    "image_width",
    "image_height",
    "traceability_status",
)


@dataclass(frozen=True)
class ManifestReport:
    path: Path
    rows: int
    unique_item_ids: int
    datasets: tuple[str, ...]


def validate_manifest(path: str | Path) -> ManifestReport:
    """Validate schema, non-empty stable IDs, and uniqueness without loading all rows."""
    manifest_path = Path(path)
    seen: set[str] = set()
    datasets: set[str] = set()
    rows = 0

    with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Manifest is missing required columns: {', '.join(missing)}")

        for line_number, row in enumerate(reader, start=2):
            item_id = (row.get("item_id") or "").strip()
            if not item_id:
                raise ValueError(f"Blank item_id at CSV line {line_number}")
            if item_id in seen:
                raise ValueError(f"Duplicate item_id {item_id!r} at CSV line {line_number}")
            source_dataset = (row.get("source_dataset") or "").strip()
            if not source_dataset:
                raise ValueError(f"Blank source_dataset at CSV line {line_number}")
            seen.add(item_id)
            datasets.add(source_dataset)
            rows += 1

    if rows == 0:
        raise ValueError("Manifest contains no data rows")
    return ManifestReport(manifest_path, rows, len(seen), tuple(sorted(datasets)))
