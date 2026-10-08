import ast
import json
import pandas as pd

src = pd.read_csv("data/manifests/fashionpedia_validation_sample_manifest.csv")
out = pd.read_csv("data/processed/m2/attribute_targets_validation_sample.csv")

with open("configs/m2/attribute_vocabulary_v1.json", encoding="utf-8-sig") as f:
    vocabulary = json.load(f)

ids = [x["attribute_id"] for x in vocabulary["labels"]]

errors = []

if len(src) != len(out):
    errors.append(f"row count mismatch: source={len(src)}, output={len(out)}")

for _, row in src.iterrows():
    matches = out[out["item_id"] == row["item_id"]]

    if len(matches) != 1:
        errors.append(f"item_id mismatch: {row['item_id']}")
        continue

    result = matches.iloc[0]
    attributes = set(ast.literal_eval(str(row["attribute_ids"])))

    target = json.loads(result["attribute_target"])
    mask = json.loads(result["observation_mask"])

    if len(target) != len(ids):
        errors.append(f"target length mismatch: {row['item_id']}")

    if len(mask) != len(ids):
        errors.append(f"mask length mismatch: {row['item_id']}")

    for i, attribute_id in enumerate(ids):
        expected = 1 if attribute_id in attributes else 0

        if mask[i] != expected:
            errors.append(
                f"mask mismatch: {row['item_id']} attribute={attribute_id}"
            )

        if target[i] != mask[i]:
            errors.append(
                f"target/mask mismatch: {row['item_id']} attribute={attribute_id}"
            )

print("source_rows =", len(src))
print("output_rows =", len(out))
print("validation_errors =", len(errors))
print("status =", "PASS" if not errors else "FAIL")

if errors:
    print("first_errors:")
    for error in errors[:10]:
        print("-", error)
