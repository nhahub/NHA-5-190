
from __future__ import annotations

import csv
import hashlib
from io import BytesIO
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

from research_cli import ROOT, run


SOURCE_ROOT = ROOT / "data/raw/polyvore_outfits"
PARQUET_ROOT = SOURCE_ROOT / "data/disjoint"

MANIFEST_PATH = (
    ROOT
    / "artifacts/polyvore_recovery/v1/polyvore_full_manifest.csv"
)

IMAGE_ROOT = (
    ROOT
    / "artifacts/polyvore_recovery/v1/images"
)

SPLITS = [
    "train",
    "validation",
    "test",
]


def main():
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            f"Manifest not found: {MANIFEST_PATH}"
        )

    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)

    # Read the recovered manifest and keep unique item IDs.
    unique_items = {}

    with MANIFEST_PATH.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            item_id = row["item_id"]

            if item_id not in unique_items:
                unique_items[item_id] = row

    expected_count = len(unique_items)

    print(f"UNIQUE ITEMS TO EXTRACT: {expected_count}")

    extracted = 0
    skipped = 0
    failed = []

    # Build item ID -> image payload from the source Parquet files.
    for split in SPLITS:
        parquet_path = PARQUET_ROOT / f"{split}.parquet"
        parquet_file = pq.ParquetFile(parquet_path)

        for batch in parquet_file.iter_batches(
            columns=["item_id", "image"],
            batch_size=512,
        ):
            for row in batch.to_pylist():
                item_id = str(row["item_id"])

                if item_id not in unique_items:
                    continue

                output_path = IMAGE_ROOT / f"{item_id}.jpg"

                if output_path.exists():
                    skipped += 1
                    del unique_items[item_id]
                    continue

                try:
                    image_bytes = row["image"]["bytes"]

                    with Image.open(
                        BytesIO(image_bytes)
                    ) as image:
                        image = image.convert("RGB")
                        image.save(
                            output_path,
                            format="JPEG",
                            quality=95,
                        )

                    extracted += 1
                    del unique_items[item_id]

                except Exception as error:
                    failed.append(
                        {
                            "item_id": item_id,
                            "split": split,
                            "error": str(error),
                        }
                    )

        print(
            f"FINISHED SPLIT: {split} | "
            f"EXTRACTED: {extracted} | "
            f"SKIPPED: {skipped}"
        )

    remaining = len(unique_items)

    print("\nEXTRACTION FINISHED")
    print(f"EXPECTED UNIQUE IMAGES: {expected_count}")
    print(f"EXTRACTED THIS RUN: {extracted}")
    print(f"ALREADY EXISTED: {skipped}")
    print(f"FAILED: {len(failed)}")
    print(f"NOT FOUND IN SOURCE: {remaining}")
    print(f"IMAGE DIRECTORY: {IMAGE_ROOT}")

    if failed:
        print("\nFAILED ITEMS:")
        for item in failed[:20]:
            print(item)


if __name__ == "__main__":
    run(main)

