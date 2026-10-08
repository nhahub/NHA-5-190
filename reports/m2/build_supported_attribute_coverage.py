import ast
import json
from collections import Counter
from pathlib import Path

import pandas as pd


VOCAB_PATH = Path("configs/m2/attribute_vocabulary_v1.json")
MANIFEST_PATH = Path("data/manifests/fashionpedia_validation_sample_manifest.csv")
OUTPUT_PATH = Path("reports/m2/supported_attribute_coverage_v1.csv")


with VOCAB_PATH.open("r", encoding="utf-8-sig") as f:
    vocabulary = json.load(f)

df = pd.read_csv(MANIFEST_PATH)

counts = Counter()

for value in df["attribute_ids"]:
    if pd.isna(value) or str(value).strip() in {"", "[]"}:
        continue

    ids = ast.literal_eval(str(value))
    counts.update(int(x) for x in ids)


rows = []

for label in vocabulary["labels"]:
    attribute_id = int(label["attribute_id"])
    count = counts[attribute_id]

    rows.append(
        {
            "vocabulary_version": vocabulary["vocabulary_version"],
            "attribute_index": label["index"],
            "attribute_id": attribute_id,
            "attribute_name": label["name"],
            "observed_positive_count": count,
            "support_status": "provisional_validation_only",
            "training_supported": False,
            "source": "Fashionpedia validation sample",
            "source_rows": len(df),
            "reason": (
                "Observed in validation sample, but Fashionpedia training split "
                "is unavailable in the current handoff; therefore this label is "
                "not claimed as training-supported."
            ),
        }
    )


report = pd.DataFrame(rows)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
report.to_csv(OUTPUT_PATH, index=False)

print(f"output = {OUTPUT_PATH}")
print(f"rows = {len(report)}")
print(f"vocabulary_version = {vocabulary['vocabulary_version']}")
print(f"validation_annotations = {len(df)}")
print(f"labels_with_observed_evidence = {(report['observed_positive_count'] > 0).sum()}")
print(f"labels_without_observed_evidence = {(report['observed_positive_count'] == 0).sum()}")
print(f"training_supported_labels = {report['training_supported'].sum()}")
print(f"max_observed_positive_count = {report['observed_positive_count'].max()}")
