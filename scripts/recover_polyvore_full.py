
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

from research_cli import ROOT, run


SOURCE_ROOT = ROOT / "data/raw/polyvore_outfits"
PARQUET_ROOT = SOURCE_ROOT / "data/disjoint"
OUTFIT_ROOT = SOURCE_ROOT / "disjoint"
METADATA_PATH = SOURCE_ROOT / "polyvore_item_metadata.json"

OUTPUT_ROOT = ROOT / "artifacts/polyvore_recovery/v1"
MANIFEST_PATH = OUTPUT_ROOT / "polyvore_full_manifest.csv"
MEMBERSHIPS_PATH = OUTPUT_ROOT / "polyvore_outfit_memberships.csv"
REPORT_PATH = OUTPUT_ROOT / "recovery_report.json"

SPLITS = {
    "train": {
        "parquet": "train.parquet",
        "outfits": "train.json",
    },
    "validation": {
        "parquet": "validation.parquet",
        "outfits": "valid.json",
    },
    "test": {
        "parquet": "test.parquet",
        "outfits": "test.json",
    },
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def build_memberships():
    """
    Build item -> all outfit memberships.
    An item may belong to more than one outfit.
    """
    memberships = []

    for split, files in SPLITS.items():
        outfit_path = OUTFIT_ROOT / files["outfits"]
        outfits = load_json(outfit_path)

        for outfit in outfits:
            outfit_id = str(outfit["set_id"])

            for item in outfit["items"]:
                memberships.append(
                    {
                        "source_split": split,
                        "item_id": str(item["item_id"]),
                        "outfit_id": outfit_id,
                        "outfit_item_index": item["index"],
                    }
                )

    return memberships


def get_image_info(payload):
    """
    Inspect the embedded JPEG bytes without writing the image.
    """
    image_bytes = payload["bytes"]
    image_hash = hashlib.sha256(image_bytes).hexdigest()

    with Image.open(BytesIO(image_bytes)) as image:
        image_format = image.format
        width, height = image.size
        image.verify()

    return {
        "image_sha256": image_hash,
        "image_format": image_format,
        "image_width": width,
        "image_height": height,
    }


def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    required_files = [
        METADATA_PATH,
        *[
            PARQUET_ROOT / files["parquet"]
            for files in SPLITS.values()
        ],
        *[
            OUTFIT_ROOT / files["outfits"]
            for files in SPLITS.values()
        ],
    ]

    missing_files = [
        str(path)
        for path in required_files
        if not path.is_file()
    ]

    if missing_files:
        raise FileNotFoundError(
            "Missing required source files: "
            + "; ".join(missing_files)
        )

    metadata = load_json(METADATA_PATH)
    memberships = build_memberships()

    # Keep all memberships, including repeated item IDs across outfits.
    with MEMBERSHIPS_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "source_split",
                "item_id",
                "outfit_id",
                "outfit_item_index",
            ],
        )
        writer.writeheader()
        writer.writerows(memberships)

    membership_lookup = {}

    for membership in memberships:
        key = (
            membership["source_split"],
            membership["item_id"],
        )

        membership_lookup.setdefault(key, []).append(membership)

    manifest_fields = [
        "source_dataset",
        "source_release",
        "source_split",
        "parquet_row_index",
        "item_id",
        "image_filename",
        "image_source_path",
        "image_sha256",
        "image_format",
        "image_width",
        "image_height",
        "metadata_category_id",
        "semantic_category",
        "metadata_title",
        "metadata_url_name",
        "metadata_description",
        "metadata_categories",
        "outfit_membership_count",
    ]

    split_stats = {}
    category_counts = Counter()
    unique_ids = set()
    missing_metadata = []
    missing_memberships = []
    total_rows = 0

    with MANIFEST_PATH.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=manifest_fields,
        )
        writer.writeheader()

        for split, files in SPLITS.items():
            parquet_path = PARQUET_ROOT / files["parquet"]
            parquet_file = pq.ParquetFile(parquet_path)

            row_count = 0
            split_ids = set()

            for batch in parquet_file.iter_batches(
                columns=["item_id", "image"],
                batch_size=512,
            ):
                for row in batch.to_pylist():
                    row_index = total_rows
                    item_id = str(row["item_id"])
                    payload = row["image"]

                    metadata_record = metadata.get(item_id)

                    if metadata_record is None:
                        missing_metadata.append(
                            {
                                "split": split,
                                "item_id": item_id,
                            }
                        )
                        metadata_record = {}

                    item_memberships = membership_lookup.get(
                        (split, item_id),
                        [],
                    )

                    if not item_memberships:
                        missing_memberships.append(
                            {
                                "split": split,
                                "item_id": item_id,
                            }
                        )

                    image_info = get_image_info(payload)

                    semantic_category = str(
                        metadata_record.get(
                            "semantic_category", ""
                        )
                    )

                    category_counts[semantic_category] += 1
                    unique_ids.add(item_id)
                    split_ids.add(item_id)

                    writer.writerow(
                        {
                            "source_dataset": "polyvore_outfits",
                            "source_release": "disjoint",
                            "source_split": split,
                            "parquet_row_index": row_index,
                            "item_id": item_id,
                            "image_filename": Path(
                                payload.get("path", "")
                            ).name,
                            "image_source_path": payload.get(
                                "path", ""
                            ),
                            **image_info,
                            "metadata_category_id": (
                                metadata_record.get("category_id", "")
                            ),
                            "semantic_category": semantic_category,
                            "metadata_title": metadata_record.get(
                                "title", ""
                            ),
                            "metadata_url_name": metadata_record.get(
                                "url_name", ""
                            ),
                            "metadata_description": metadata_record.get(
                                "description", ""
                            ),
                            "metadata_categories": json.dumps(
                                metadata_record.get("catgeories", []),
                                ensure_ascii=False,
                            ),
                            "outfit_membership_count": len(
                                item_memberships
                            ),
                        }
                    )

                    row_count += 1
                    total_rows += 1

            split_stats[split] = {
                "parquet_rows": parquet_file.metadata.num_rows,
                "processed_rows": row_count,
                "unique_item_ids": len(split_ids),
            }

    report = {
        "schema_version": "wardiq.polyvore_recovery.v1",
        "source": str(SOURCE_ROOT.relative_to(ROOT)),
        "output": str(OUTPUT_ROOT.relative_to(ROOT)),
        "total_parquet_rows": total_rows,
        "unique_item_ids_across_splits": len(unique_ids),
        "metadata_records": len(metadata),
        "missing_metadata_count": len(missing_metadata),
        "missing_metadata_examples": missing_metadata[:20],
        "missing_outfit_membership_count": len(
            missing_memberships
        ),
        "missing_outfit_membership_examples": (
            missing_memberships[:20]
        ),
        "outfit_membership_rows": len(memberships),
        "semantic_category_counts_by_parquet_row": dict(
            category_counts
        ),
        "splits": split_stats,
        "manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "memberships": str(MEMBERSHIPS_PATH.relative_to(ROOT)),
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("POLYVORE RECOVERY FINISHED")
    print(f"TOTAL PARQUET ROWS: {total_rows}")
    print(f"UNIQUE ITEM IDS: {len(unique_ids)}")
    print(f"MISSING METADATA: {len(missing_metadata)}")
    print(
        "MISSING OUTFIT MEMBERSHIPS: "
        f"{len(missing_memberships)}"
    )
    print(f"OUTFIT MEMBERSHIP ROWS: {len(memberships)}")
    print(f"MANIFEST: {MANIFEST_PATH}")
    print(f"MEMBERSHIPS: {MEMBERSHIPS_PATH}")
    print(f"REPORT: {REPORT_PATH}")


if __name__ == "__main__":
    run(main)

