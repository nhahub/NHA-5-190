import json
from pathlib import Path

import pandas as pd

VOCAB_PATH = Path("configs/m2/attribute_vocabulary_v1.json")
OUTPUT_PATH = Path("reports/m2/attribute_support_v1.csv")

with VOCAB_PATH.open("r", encoding="utf-8-sig") as f:
    vocabulary = json.load(f)

rows = []

for label in vocabulary["labels"]:
    rows.append(
        {
            "vocabulary_version": vocabulary["vocabulary_version"],
            "attribute_index": label["index"],
            "attribute_id": label["attribute_id"],
            "attribute_name": label["name"],
            "support_mask": 0,
            "support_status": "unsupported_pending_training_data",
            "source": "Fashionpedia",
            "evidence_scope": "validation_only",
            "reason": (
                "No Fashionpedia training split is available in the current "
                "handoff; validation evidence alone is insufficient to claim "
                "training support."
            ),
        }
    )

report = pd.DataFrame(rows)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
report.to_csv(OUTPUT_PATH, index=False)

print(f"output = {OUTPUT_PATH}")
print(f"rows = {len(report)}")
print(f"supported = {(report['support_mask'] == 1).sum()}")
print(f"unsupported = {(report['support_mask'] == 0).sum()}")
print(f"status = PASS")
