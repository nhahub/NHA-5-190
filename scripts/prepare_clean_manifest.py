"""Reproduce a manifest-only clean handoff; never rewrite the source manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.research_cli import protect_evidence  # noqa: E402
from wardiq.data import validate_manifest  # noqa: E402

STATUS_COLUMNS = (
    "cleaning_status",
    "exclusion_reason",
    "image_validation_scope",
    "notes",
    "category_label_resolution",
)


def clean_row(row: dict[str, str], categories: dict[str, str]) -> dict[str, str]:
    """Keep source IDs; align Fashionpedia names using its official ID lookup."""
    result = dict(row)
    resolution = "source_labels_preserved"
    if row["source_dataset"] == "Fashionpedia":
        ids = row["category_ids"].split(";")
        if not all(ids) or any(value not in categories for value in ids):
            raise ValueError(f"Unknown/empty Fashionpedia category ID for {row['item_id']}")
        result["category_labels"] = ";".join(categories[value] for value in ids)
        resolution = "source_id_lookup"
    result.update(
        cleaning_status="retained",
        exclusion_reason="",
        image_validation_scope="manifest_only",
        notes="Source image decoding, geometry and visual duplication are not validated here.",
        category_label_resolution=resolution,
    )
    return result


def generate(raw: Path, mapping: Path, output_dir: Path) -> dict[str, object]:
    """Write deterministic outputs, provenance and log to an uncommitted directory."""
    protect_evidence(output_dir)
    validate_manifest(raw)
    config = json.loads(mapping.read_text(encoding="utf-8"))
    if config.get("schema_version") != "wardiq.source-categories.v1":
        raise ValueError("Unsupported category mapping schema")
    if config.get("dataset") != "Fashionpedia":
        raise ValueError("Category mapping must describe Fashionpedia")
    categories = config["categories"]
    if not isinstance(categories, dict) or not all(
        isinstance(k, str) and isinstance(v, str) and v for k, v in categories.items()
    ):
        raise ValueError("Category lookup must map string IDs to nonempty source names")
    # Preflight all rows before replacing any generated output.
    datasets: Counter[str] = Counter()
    changed = 0
    with raw.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = list(reader.fieldnames or [])
        if any(name in fields for name in STATUS_COLUMNS):
            raise ValueError("Input must be the raw manifest, not an already cleaned output")
        for row in reader:
            cleaned = clean_row(row, categories)
            datasets[row["source_dataset"]] += 1
            changed += cleaned["category_labels"] != row["category_labels"]
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "clean_manifest.csv"
    with (
        raw.open(encoding="utf-8-sig", newline="") as stream,
        output.open("w", encoding="utf-8", newline="") as target,
    ):
        writer = csv.DictWriter(
            target, fieldnames=fields + list(STATUS_COLUMNS), lineterminator="\n"
        )
        writer.writeheader()
        for row in csv.DictReader(stream):
            writer.writerow(clean_row(row, categories))
    summary: dict[str, object] = {
        "schema_version": "wardiq.cleaning-report.v1",
        "raw_sha256": hashlib.sha256(raw.read_bytes()).hexdigest(),
        "mapping_sha256": hashlib.sha256(mapping.read_bytes()).hexdigest(),
        "clean_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "rows": sum(datasets.values()),
        "datasets": dict(sorted(datasets.items())),
        "category_label_rows_changed": changed,
        "retained": sum(datasets.values()),
        "excluded": 0,
        "scope": "Manifest-only validation; no image/geometry/visual-leakage acceptance.",
    }
    (output_dir / "cleaning_report.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "cleaning_log.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["check", "result", "records", "scope"])
        writer.writerow(["schema_and_unique_item_ids", "PASS", summary["rows"], "manifest"])
        writer.writerow(["fashionpedia_id_lookup", "PASS", changed, "changed label-list rows"])
        writer.writerow(["source_image_decoding", "NOT_RUN", summary["rows"], "not inspected"])
        writer.writerow(
            ["geometry_and_visual_duplicates", "NOT_RUN", summary["rows"], "not inspected"]
        )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/manifests/raw_manifest.csv")
    parser.add_argument(
        "--categories", type=Path, default=ROOT / "configs/m1/fashionpedia_categories.json"
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/m1/quality")
    args = parser.parse_args()
    try:
        print(json.dumps(generate(args.input, args.categories, args.output_dir), indent=2))
    except (OSError, ValueError, KeyError) as exc:
        print(f"Clean handoff failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
