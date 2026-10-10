"""Exploratory zero-shot CLIP classification for WARDIQ M2."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
import torch
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score, recall_score
from transformers import CLIPModel, CLIPProcessor

ROOT = Path(__file__).resolve().parents[2]
TAXONOMY_PATH = ROOT / "configs/m1/taxonomy.json"
MANIFEST_PATH = ROOT / "artifacts/m1/garment_manifest.csv"
OUTPUT_DIR = ROOT / "artifacts/m2/clip_zero_shot"

MODEL_ID = "openai/clip-vit-base-patch32"

REQUIRED_COLUMNS = {
    "item_id",
    "source_dataset",
    "image_path",
    "target_split",
    "usable_derivative",
    "common_category",
    "category_mapping_status",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run exploratory zero-shot CLIP classification.")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    if args.batch_size < 1:
        parser.error("--batch-size must be positive")

    taxonomy = json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))
    categories = taxonomy["common_categories"]
    category_names = list(categories)
    prompts = [
        f"a photo of a {description.lower()} garment or fashion item"
        for description in categories.values()
    ]

    manifest = pd.read_csv(MANIFEST_PATH)
    missing_columns = REQUIRED_COLUMNS - set(manifest.columns)
    if missing_columns:
        raise ValueError(f"Manifest missing columns: {sorted(missing_columns)}")

    eligible = manifest[
        manifest["usable_derivative"].astype(str).str.strip().str.lower().eq("true")
        & manifest["category_mapping_status"].isin(["direct", "approximate"])
        & manifest["common_category"].isin(category_names)
        & manifest["target_split"].astype(str).str.lower().isin(["validation", "val"])
        & manifest["source_dataset"].isin(["Fashionpedia", "Polyvore Outfits"])
    ].copy()

    if eligible.empty:
        raise ValueError("No eligible validation items found.")

    eligible["resolved_image_path"] = eligible["image_path"].map(
        lambda value: (
            (ROOT / str(value)).resolve()
            if not Path(str(value)).is_absolute()
            else Path(str(value)).resolve()
        )
    )

    missing_images = [str(path) for path in eligible["resolved_image_path"] if not path.is_file()]
    if missing_images:
        raise FileNotFoundError(
            f"{len(missing_images)} eligible image(s) are missing; "
            f"first missing path: {missing_images[0]}"
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID).to(device)
    model.eval()

    text_inputs = processor(
        text=prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
    )
    text_inputs = {key: value.to(device) for key, value in text_inputs.items()}

    with torch.no_grad():
        text_features = model.get_text_features(**text_inputs)
        if not isinstance(text_features, torch.Tensor):
            text_features = text_features.pooler_output
        text_features = torch.nn.functional.normalize(text_features, dim=-1)

    records = []

    for start in range(0, len(eligible), args.batch_size):
        batch = eligible.iloc[start : start + args.batch_size]
        images = []

        try:
            for path in batch["resolved_image_path"]:
                with Image.open(path) as image:
                    images.append(image.convert("RGB"))

            inputs = processor(images=images, return_tensors="pt")
            inputs = {key: value.to(device) for key, value in inputs.items()}

            with torch.no_grad():
                image_features = model.get_image_features(**inputs)
                if not isinstance(image_features, torch.Tensor):
                    image_features = image_features.pooler_output
                image_features = torch.nn.functional.normalize(image_features, dim=-1)
                scores = image_features @ text_features.T

            predictions = scores.argmax(dim=1).cpu().tolist()
            score_values = scores.cpu().tolist()

            for (_, row), prediction, row_scores in zip(
                batch.iterrows(),
                predictions,
                score_values,
                strict=True,
            ):
                predicted_category = category_names[prediction]
                records.append(
                    {
                        "item_id": row["item_id"],
                        "source_dataset": row["source_dataset"],
                        "target_split": row["target_split"],
                        "true_category": row["common_category"],
                        "mapping_status": row["category_mapping_status"],
                        "predicted_category": predicted_category,
                        "correct": (predicted_category == row["common_category"]),
                        "similarity_scores": json.dumps(
                            dict(zip(category_names, row_scores, strict=True))
                        ),
                    }
                )
        finally:
            for image in images:
                image.close()

    results = pd.DataFrame(records)
    y_true = results["true_category"]
    y_pred = results["predicted_category"]

    observed_categories = [category for category in category_names if (y_true == category).any()]
    absent_categories = [category for category in category_names if not (y_true == category).any()]

    # Macro-F1 averages only categories represented in the ground truth.
    macro_f1 = f1_score(
        y_true,
        y_pred,
        labels=observed_categories,
        average="macro",
        zero_division=0,
    )
    recalls = recall_score(
        y_true,
        y_pred,
        labels=observed_categories,
        average=None,
        zero_division=0,
    )

    per_class = {}
    for category, recall in zip(observed_categories, recalls, strict=True):
        support = int((y_true == category).sum())
        correct = int(((y_true == category) & (y_pred == category)).sum())
        per_class[category] = {
            "support": support,
            "correct": correct,
            "recall": float(recall),
        }

    for category in absent_categories:
        per_class[category] = {
            "support": 0,
            "correct": 0,
            "recall": None,
            "note": "No ground-truth examples in this sample.",
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results.to_csv(OUTPUT_DIR / "predictions.csv", index=False)

    summary = {
        "status": "exploratory_only",
        "taxonomy_version": taxonomy["taxonomy_version"],
        "taxonomy_status": taxonomy["status"],
        "model_id": MODEL_ID,
        "model_revision": None,
        "experiment": "zero_shot_clip",
        "candidate_categories": category_names,
        "item_count": len(results),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1_observed_categories": float(macro_f1),
        "per_class_recall": per_class,
        "observed_categories": observed_categories,
        "absent_categories": absent_categories,
        "metrics_note": (
            "Macro-F1 is averaged over categories present in the ground "
            "truth; absent categories are excluded from that average and "
            "their recall is null. These metric conventions are provisional "
            "pending Omar/Asmaa approval."
        ),
        "mapping_note": (
            "Uses existing direct and approximate taxonomy mappings. "
            "Taxonomy remains pending lead review."
        ),
        "evaluation_limitations": [
            "Small sample; metrics are not final evaluation results.",
            "Fashionpedia crops from the same source image may be correlated.",
            "Source-image grouping and independence have not been enforced.",
            "Model revision is not pinned or recorded.",
            "No prompt tuning or training was performed.",
        ],
        "source_counts": {
            str(key): int(value) for key, value in results["source_dataset"].value_counts().items()
        },
    }

    (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Saved predictions: {OUTPUT_DIR / 'predictions.csv'}")
    print(f"Saved summary: {OUTPUT_DIR / 'summary.json'}")
    print(f"Items evaluated: {len(results)}")
    print(f"Accuracy: {summary['accuracy']:.3f}")
    print(f"Macro-F1 (observed categories): {macro_f1:.3f}")
    print(f"Categories represented: {len(observed_categories)}/{len(category_names)}")
    print("Per-class recall:")
    for category, metrics in per_class.items():
        recall = metrics["recall"]
        display = "N/A" if recall is None else f"{recall:.3f}"
        print(f"  {category}: recall={display}, support={metrics['support']}")
    print("Exploratory results only; no prompt tuning was performed.")


if __name__ == "__main__":
    main()
