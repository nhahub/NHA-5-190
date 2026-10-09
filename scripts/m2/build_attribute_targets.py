"""Build positive-only targets; unknown labels remain masked, never known negatives."""

import argparse
import json

import pandas as pd
from attribute_common import (
    DEFAULT_MANIFEST,
    DEFAULT_TARGETS,
    DEFAULT_VOCABULARY,
    build_target_and_mask,
    load_vocabulary,
    parse_attribute_ids,
    read_manifest,
    run,
    safe_output,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--vocabulary", default=DEFAULT_VOCABULARY)
    parser.add_argument("--output", default=DEFAULT_TARGETS)
    args = parser.parse_args()
    output = safe_output(args.output, args.manifest, args.vocabulary)
    vocabulary = load_vocabulary(args.vocabulary)
    source = read_manifest(args.manifest)
    ids = [label["attribute_id"] for label in vocabulary["labels"]]
    rows = []
    for row in source.itertuples():
        target, mask = build_target_and_mask(parse_attribute_ids(row.attribute_ids), ids)
        rows.append(
            {
                "item_id": row.item_id,
                "source_dataset": row.source_dataset,
                "source_split": row.source_split,
                "attribute_target": json.dumps(target),
                "observation_mask": json.dumps(mask),
                "observed_positive_count": sum(mask),
                "unknown_count": len(mask) - sum(mask),
                "negative_count": 0,
                "vocabulary_version": vocabulary["vocabulary_version"],
            }
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False, lineterminator="\n")
    print(f"output = {output}")
    print(f"rows = {len(rows)}")
    print(f"vector_length = {len(ids)}")
    print(f"vocabulary_version = {vocabulary['vocabulary_version']}")
    print(f"total_observed_positives = {sum(row['observed_positive_count'] for row in rows)}")
    print(f"total_unknown = {sum(row['unknown_count'] for row in rows)}")
    print("total_known_negatives = 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(run(main))
