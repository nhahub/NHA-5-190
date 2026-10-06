"""Portable entry point for Ziad's manifest EDA; no image validation is implied."""

from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    import pandas as pd

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/manifests/raw_manifest.csv")
    args = parser.parse_args()
    frame = pd.read_csv(args.input, low_memory=False)
    print("Shape:", frame.shape)
    print("Dataset counts:\n", frame["source_dataset"].value_counts())
    print("Split counts:\n", frame.groupby(["source_dataset", "source_split"]).size())
    print("Unique item IDs:", frame["item_id"].nunique())
    print("Duplicate item IDs:", frame["item_id"].duplicated().sum())
    print("Exact duplicate rows:", frame.duplicated().sum())
    print("Missing values:\n", frame.isna().sum())
    print(
        "Dimensions:\n",
        frame.groupby("source_dataset")[["image_width", "image_height"]].agg(
            ["count", "min", "max", "mean"]
        ),
    )
    mnist = frame[frame["source_dataset"] == "Fashion-MNIST"]
    print("Fashion-MNIST classes:\n", mnist["category_labels"].value_counts().sort_index())
    fashionpedia = frame[frame["source_dataset"] == "Fashionpedia"].copy()
    fields = ["annotation_ids", "category_ids", "attribute_ids"]
    for field in fields:
        fashionpedia[f"n_{field}"] = (
            fashionpedia[field]
            .fillna("")
            .astype(str)
            .apply(lambda value: len(value.split(";")) if value else 0)
        )
    print("Fashionpedia manifest coverage:\n", fashionpedia[[f"n_{x}" for x in fields]].describe())
    print("Manifest metadata is not full source image/annotation validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
