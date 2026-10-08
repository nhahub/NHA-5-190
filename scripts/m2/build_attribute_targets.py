import argparse
import ast
import json
from pathlib import Path

import pandas as pd


def parse_attribute_ids(value):
    if pd.isna(value) or str(value).strip() in {"", "[]"}:
        return []

    parsed = ast.literal_eval(str(value))

    if not isinstance(parsed, list):
        raise ValueError(f"Expected a list of attribute IDs, got: {parsed!r}")

    return [int(x) for x in parsed]


def build_target_and_mask(attribute_ids, vocabulary_ids):
    observed = set(attribute_ids)

    unknown_ids = observed - set(vocabulary_ids)
    if unknown_ids:
        raise ValueError(
            f"Observed attribute IDs are not in vocabulary: {sorted(unknown_ids)}"
        )

    target = [1 if attr_id in observed else 0 for attr_id in vocabulary_ids]
    observation_mask = [1 if attr_id in observed else 0 for attr_id in vocabulary_ids]

    return target, observation_mask


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        default="data/manifests/fashionpedia_validation_sample_manifest.csv",
    )
    parser.add_argument(
        "--vocabulary",
        default="configs/m2/attribute_vocabulary_v1.json",
    )
    parser.add_argument(
        "--output",
        default="data/processed/m2/attribute_targets_validation_sample.csv",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    vocabulary_path = Path(args.vocabulary)
    output_path = Path(args.output)

    df = pd.read_csv(manifest_path)

    with vocabulary_path.open("r", encoding="utf-8-sig") as f:
        vocabulary = json.load(f)

    labels = vocabulary["labels"]
    vocabulary_ids = [int(x["attribute_id"]) for x in labels]

    if len(vocabulary_ids) != vocabulary["vector_length"]:
        raise ValueError("Vocabulary vector_length does not match labels length.")

    if len(set(vocabulary_ids)) != len(vocabulary_ids):
        raise ValueError("Vocabulary contains duplicate attribute IDs.")

    rows = []

    for _, row in df.iterrows():
        attribute_ids = parse_attribute_ids(row["attribute_ids"])

        target, observation_mask = build_target_and_mask(
            attribute_ids,
            vocabulary_ids,
        )

        rows.append(
            {
                "item_id": row["item_id"],
                "source_dataset": row["source_dataset"],
                "source_split": row["source_split"],
                "attribute_target": json.dumps(target),
                "observation_mask": json.dumps(observation_mask),
                "observed_positive_count": sum(observation_mask),
                "unknown_count": len(observation_mask) - sum(observation_mask),
                "negative_count": 0,
                "vocabulary_version": vocabulary["vocabulary_version"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)

    print(f"output = {output_path}")
    print(f"rows = {len(rows)}")
    print(f"vector_length = {len(vocabulary_ids)}")
    print(f"vocabulary_version = {vocabulary['vocabulary_version']}")
    print(f"total_observed_positives = {sum(r['observed_positive_count'] for r in rows)}")
    print(f"total_unknown = {sum(r['unknown_count'] for r in rows)}")
    print(f"total_known_negatives = {sum(r['negative_count'] for r in rows)}")


if __name__ == "__main__":
    main()
