"""Build separate, traceable Polyvore M3 inventories and compatibility examples.

No source file, M1 assignment, taxonomy, or M2 cache is modified. Generated
negatives are assumptions, not human compatibility annotations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
from apply_taxonomy import load_taxonomy, map_category  # noqa: E402
from research_cli import protect_evidence  # noqa: E402

VERSION = "wardiq.m3.compatibility-data.v1"
SPLITS = ("train", "validation", "test")
SOURCE_NAMES = {"train": "train", "validation": "valid", "test": "test"}


def sha256(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    rows = list(rows)
    if not rows:
        raise ValueError(f"Refusing an empty inventory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")


def source_paths(root):
    result = {
        "metadata": root / "polyvore_item_metadata.json",
        "source_categories": root / "categories.csv",
    }
    for split, short in SOURCE_NAMES.items():
        result[split + "_images"] = root / f"data/disjoint/{split}.parquet"
        result[split + "_outfits"] = root / f"disjoint/{short}.json"
        result[split + "_compatibility"] = root / f"disjoint/compatibility_{short}.txt"
        result[split + "_fitb"] = root / f"disjoint/fill_in_blank_{short}.json"
    return result


def scan_items(paths, taxonomy):
    """Hash actual embedded bytes; do not trust the older audit's eligibility CSV."""
    metadata = read_json(paths["metadata"])
    with paths["source_categories"].open(encoding="utf-8", newline="") as stream:
        source_categories = {row[0]: row for row in csv.reader(stream)}
    result = {}
    for split in SPLITS:
        items = {}
        parquet = pq.ParquetFile(paths[split + "_images"])
        for batch in parquet.iter_batches(batch_size=128, columns=["item_id", "image"]):
            for row in batch.to_pylist():
                key = str(row["item_id"])
                if key in items or key not in metadata:
                    raise ValueError(f"Duplicate item or missing source metadata: {split}/{key}")
                payload = row["image"]["bytes"]
                with Image.open(io.BytesIO(payload)) as image:
                    width, height = image.size
                    image.verify()
                source = metadata[key]
                category = str(source["category_id"])
                if category not in source_categories:
                    raise ValueError(f"Category absent from official source vocabulary: {category}")
                mapped = map_category(taxonomy, "polyvore_outfits", category)
                items[key] = {
                    "item_id": f"polyvore_outfits_disjoint_{split}_{key}",
                    "source_item_id": key,
                    "source_split": split,
                    "source_dataset": "Polyvore Outfits",
                    "image_sha256": hashlib.sha256(payload).hexdigest(),
                    "width": width,
                    "height": height,
                    "source_category_id": category,
                    "source_label": source.get("semantic_category", ""),
                    "common_category": mapped["common_category"] if mapped else "",
                    "mapping_status": mapped["mapping_status"] if mapped else "unmapped",
                    "category_supported": bool(mapped and mapped["common_category"]),
                }
        if not items:
            raise ValueError(f"Empty source image population: {split}")
        result[split] = items
        print(f"Hashed {split}: {len(items)} image records", flush=True)
    return result


def split_eligibility(items):
    """Preserve test; filter validation against test and train against both originals."""
    eligible, exclusions = {}, []
    for split, heldout in (
        ("test", ()),
        ("validation", ("test",)),
        ("train", ("validation", "test")),
    ):
        held_ids = {key for other in heldout for key in items[other]}
        held_hashes = {row["image_sha256"] for other in heldout for row in items[other].values()}
        eligible[split] = set()
        for key, row in items[split].items():
            reasons = []
            if key in held_ids:
                reasons.append("source_item_id_in_heldout")
            if row["image_sha256"] in held_hashes:
                reasons.append("exact_image_bytes_in_heldout")
            if reasons:
                exclusions.append(
                    {"source_split": split, "source_item_id": key, "reason": ";".join(reasons)}
                )
            else:
                eligible[split].add(key)
    for left, right in itertools.combinations(SPLITS, 2):
        if eligible[left] & eligible[right]:
            raise ValueError("Eligible source item IDs cross splits")
        hashes_left = {items[left][key]["image_sha256"] for key in eligible[left]}
        hashes_right = {items[right][key]["image_sha256"] for key in eligible[right]}
        if hashes_left & hashes_right:
            raise ValueError("Eligible exact image hashes cross splits")
    return eligible, exclusions


def load_outfits(path, items):
    outfits = read_json(path)
    references, groups = {}, set()
    for outfit in outfits:
        group = str(outfit["set_id"])
        if group in groups:
            raise ValueError(f"Duplicate outfit ID: {group}")
        groups.add(group)
        for member in outfit["items"]:
            key, position = str(member["item_id"]), str(member["index"])
            reference = f"{group}_{position}"
            if key not in items or reference in references:
                raise ValueError(f"Unresolved or duplicated outfit member: {reference}")
            references[reference] = key
    return outfits, references, groups


def filter_examples(paths, items, eligible, output):
    retained, all_outfits, summaries, removed = {}, {}, {}, []
    groups_by_split = {}
    for split in SPLITS:
        outfits, references, groups = load_outfits(paths[split + "_outfits"], items[split])
        all_outfits[split] = outfits
        groups_by_split[split] = groups
        kept = [o for o in outfits if all(str(i["item_id"]) in eligible[split] for i in o["items"])]
        retained[split] = kept
        kept_groups = {str(o["set_id"]) for o in kept}
        removed.extend(
            {
                "source_split": split,
                "kind": "outfit",
                "source_reference": str(o["set_id"]),
                "reason": "ineligible_member",
            }
            for o in outfits
            if str(o["set_id"]) not in kept_groups
        )
        write_json(output / split / "outfits.json", kept)

        def resolve(tokens):
            try:
                return [references[token] for token in tokens]
            except KeyError as error:
                raise ValueError(f"Unresolved {split} outfit reference: {error}") from error

        lines = paths[split + "_compatibility"].read_text(encoding="utf-8").splitlines()
        compatible = []
        for index, line in enumerate(lines):
            label, *tokens = line.split()
            if label not in {"0", "1"} or len(tokens) < 2:
                raise ValueError(f"Invalid compatibility row: {split}/{index}")
            keys = resolve(tokens)
            if all(key in eligible[split] for key in keys):
                compatible.append(line)
            else:
                removed.append(
                    {
                        "source_split": split,
                        "kind": "compatibility",
                        "source_reference": str(index),
                        "reason": "ineligible_member",
                    }
                )
        (output / split / "compatibility.txt").write_text(
            "\n".join(compatible) + "\n", encoding="utf-8"
        )
        fitb = read_json(paths[split + "_fitb"])
        retained_fitb = []
        for index, question in enumerate(fitb):
            if not question["question"] or not question["answers"]:
                raise ValueError(f"Empty FITB question or answers: {split}/{index}")
            if len({token.rsplit("_", 1)[0] for token in question["question"]}) != 1:
                raise ValueError(f"FITB question mixes source outfits: {split}/{index}")
            tokens = [*question["question"], *question["answers"]]
            keys = resolve(tokens)
            correct = (
                question["question"][0].rsplit("_", 1)[0] + "_" + str(question["blank_position"])
            )
            if question["answers"].count(correct) != 1:
                raise ValueError(f"FITB needs exactly one source correct answer: {split}/{index}")
            if all(key in eligible[split] for key in keys):
                retained_fitb.append(question)
            else:
                removed.append(
                    {
                        "source_split": split,
                        "kind": "fitb",
                        "source_reference": str(index),
                        "reason": "ineligible_member",
                    }
                )
        write_json(output / split / "fitb.json", retained_fitb)
        summaries[split] = {
            "source_items": len(items[split]),
            "eligible_items": len(eligible[split]),
            "source_outfits": len(outfits),
            "eligible_outfits": len(kept),
            "eligible_compatibility_examples": len(compatible),
            "eligible_fitb_questions": len(retained_fitb),
            "source_outfits_repeating_item_ids": sum(
                len(o["items"]) != len({str(i["item_id"]) for i in o["items"]}) for o in outfits
            ),
        }
    for left, right in itertools.combinations(SPLITS, 2):
        if groups_by_split[left] & groups_by_split[right]:
            raise ValueError("Source outfit IDs cross splits; grouping policy needs review")
    write_jsonl(output / "excluded_examples.jsonl", removed)
    return retained, all_outfits, summaries


def unordered_pair(left, right):
    return tuple(sorted((left, right)))


def make_pairs(items, outfits, all_outfits, split, seed):
    """Use only this split's source positives when avoiding false-negative collisions."""
    rng = random.Random(seed)
    known_ids, known_hashes = set(), set()
    memberships = defaultdict(set)
    for outfit in all_outfits:
        keys = sorted({str(member["item_id"]) for member in outfit["items"]})
        group = str(outfit["set_id"])
        for key in keys:
            memberships[key].add(group)
        for left, right in itertools.combinations(keys, 2):
            known_ids.add(unordered_pair(left, right))
            known_hashes.add(
                unordered_pair(items[left]["image_sha256"], items[right]["image_sha256"])
            )
    pools, positives = defaultdict(set), {}
    for outfit in sorted(outfits, key=lambda o: str(o["set_id"])):
        keys = sorted({str(member["item_id"]) for member in outfit["items"]})
        for key in keys:
            pools[items[key]["source_category_id"]].add(key)
        for left, right in itertools.combinations(keys, 2):
            if items[left]["source_category_id"] == items[right]["source_category_id"]:
                continue
            if items[left]["image_sha256"] == items[right]["image_sha256"]:
                continue
            positives.setdefault((left, right), []).append(str(outfit["set_id"]))
    pools = {category: sorted(keys) for category, keys in pools.items()}
    records, negatives, unmatched = [], set(), 0
    for (left, right), groups in sorted(positives.items()):
        record = {
            "split": split,
            "left_item_id": items[left]["item_id"],
            "right_item_id": items[right]["item_id"],
            "label": 1,
            "label_origin": "source_outfit_cooccurrence",
            "source_outfit_ids": sorted(set(groups)),
            "replaced_item_id": None,
        }
        records.append(record)
        pool = pools[items[right]["source_category_id"]]
        replacement = None
        for candidate in rng.sample(pool, min(256, len(pool))):
            pair = unordered_pair(left, candidate)
            hashes = unordered_pair(items[left]["image_sha256"], items[candidate]["image_sha256"])
            if candidate in {left, right} or pair in known_ids or pair in negatives:
                continue
            if memberships[candidate] & set(groups) or hashes in known_hashes:
                continue
            if items[candidate]["image_sha256"] in {
                items[left]["image_sha256"],
                items[right]["image_sha256"],
            }:
                continue
            replacement = candidate
            negatives.add(pair)
            break
        if replacement is None:
            unmatched += 1
            continue
        records.append(
            {
                **record,
                "right_item_id": items[replacement]["item_id"],
                "label": 0,
                "label_origin": "assumed_category_preserving_replacement",
                "replacement_source_outfit_ids": sorted(memberships[replacement]),
                "replaced_item_id": items[right]["item_id"],
            }
        )
    return records, {
        "positive_pairs": len(positives),
        "negative_pairs": len(negatives),
        "positives_without_negative": unmatched,
    }


def cache_coverage(cache_path, items, pairs):
    """Inventory actual cached IDs; unresolved training items are never called ready."""
    available = {}
    if cache_path.is_file():
        with cache_path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row["item_id"] in available:
                    raise ValueError("Duplicate cache item ID")
                available[row["item_id"]] = row["split"]["target_split"]
    result, missing = {}, []
    for split in SPLITS:
        required = {
            row[field] for row in pairs[split] for field in ("left_item_id", "right_item_id")
        }
        by_id = {row["item_id"]: row for row in items[split].values()}
        for key in sorted(required):
            if key not in by_id:
                raise ValueError(f"Pair does not resolve to item inventory: {key}")
            if key in available and available[key] != split:
                raise ValueError(f"Cache split mismatch: {key}")
            if key not in available:
                missing.append(
                    {"item_id": key, "split": split, "reason": "feature_cache_record_missing"}
                )
        covered = sum(key in available for key in required)
        result[split] = {
            "required_items": len(required),
            "cached_items": covered,
            "missing_items": len(required) - covered,
        }
    return result, missing


def prepare_training_images(request_path, source_root, output):
    """Verify Hayat's request and reuse Hana's existing product-photo preparation."""
    from prepare_garment_crops import full_image_source

    request = read_json(request_path)
    if request.get("version") != "wardiq.m3.training-feature-request.v1":
        raise ValueError("Unsupported training feature request version")
    filename = request["items_file"]
    if Path(filename).name != filename:
        raise ValueError("Feature request must name a CSV in its own directory")
    inventory = request_path.parent / filename
    if sha256(inventory) != request["items_sha256"]:
        raise ValueError("Training request inventory checksum mismatch")
    with inventory.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_source = {row["source_item_id"]: row for row in rows}
    if not rows or len(by_source) != len(rows) or len(rows) != request["item_count"]:
        raise ValueError("Training request needs unique items and matching counts")
    if len({row["item_id"] for row in rows}) != len(rows):
        raise ValueError("Training request contains duplicate canonical IDs")
    if any(row["source_split"] != "train" or not row["source_item_id"].isdecimal() for row in rows):
        raise ValueError("Training feature request must contain training items only")
    parquet = source_root / "data/disjoint/train.parquet"
    if sha256(parquet) != request["source_parquet_sha256"]:
        raise ValueError("Training parquet checksum differs from the verified request")
    output = output.resolve()
    protect_evidence(output)
    if output.exists() or any(
        output == p.resolve() or output in p.resolve().parents
        for p in (parquet, inventory, request_path)
    ):
        raise ValueError("Feature-input output exists or overlaps an input")
    source_images = output / "source_images"
    source_images.mkdir(parents=True)
    found = set()
    for batch in pq.ParquetFile(parquet).iter_batches(batch_size=128, columns=["item_id", "image"]):
        for entry in batch.to_pylist():
            key = str(entry["item_id"])
            if key not in by_source:
                continue
            payload = entry["image"]["bytes"]
            if (
                key in found
                or hashlib.sha256(payload).hexdigest() != by_source[key]["image_sha256"]
            ):
                raise ValueError(f"Duplicate or changed training image: {key}")
            (source_images / f"{key}.jpg").write_bytes(payload)
            found.add(key)
    if found != set(by_source):
        raise ValueError("Training parquet does not resolve every requested item")
    source_manifest = output / "source_manifest.csv"
    write_csv(
        source_manifest,
        [
            {
                "item_id": row["item_id"],
                "image_filename": row["source_item_id"] + ".jpg",
                "source_index": row["source_item_id"],
                "source_split": "train",
                "category_id": row["source_category_id"],
                "semantic_category": row["source_label"],
            }
            for row in rows
        ],
    )
    prepared = full_image_source(
        {
            "manifest": str(source_manifest),
            "image_root": str(source_images),
            "crop_policy": {"method": "full_image_source_precropped"},
        },
        "Polyvore Outfits",
        "item_id",
        "image_filename",
        "semantic_category",
        output / "prepared",
        "single-item source photo; geometry unavailable",
    )
    by_id = {row["item_id"]: row for row in rows}
    for row in prepared:
        original = by_id[row["item_id"]]
        row.update(
            source_item_id=original["source_item_id"],
            source_image_id=original["source_item_id"],
            target_split="train",
            source_target_split="train",
            usable_derivative=True,
            image_path=row["output_path"],
            source_image_sha256=original["image_sha256"],
            image_sha256=sha256(row["output_path"]),
            common_category=original["common_category"] or None,
            category_mapping_status=original["mapping_status"],
        )
    manifest = output / "garment_manifest.csv"
    write_csv(manifest, prepared)
    if sha256(parquet) != request["source_parquet_sha256"]:
        raise ValueError("Training parquet changed during image preparation")
    result = {
        "version": "wardiq.m3.training-inputs.v1",
        "item_count": len(prepared),
        "source_parquet_sha256": request["source_parquet_sha256"],
        "request_sha256": sha256(request_path),
        "manifest_sha256": sha256(manifest),
        "preparation_implementation_sha256": sha256(ROOT / "scripts/prepare_garment_crops.py"),
        "manifest": str(manifest),
        "features_extracted": False,
    }
    write_json(output / "preparation_report.json", result)
    print(json.dumps(result, indent=2))
    return result


def write_feature_request(output, items, pairs, paths, provenance):
    from wardiq.representation.clip_embeddings import CLIP_MODEL_ID, CLIP_MODEL_REVISION

    directory = output / "feature_request"
    for split in ("train", "validation"):
        required = {
            row[field] for row in pairs[split] for field in ("left_item_id", "right_item_id")
        }
        rows = [
            row
            for row in sorted(items[split].values(), key=lambda r: r["item_id"])
            if row["item_id"] in required
        ]
        if rows:
            write_csv(directory / f"{split}_required_items.csv", rows)
    training_inventory = directory / "train_required_items.csv"
    if training_inventory.is_file():
        with training_inventory.open(encoding="utf-8", newline="") as stream:
            count = sum(1 for _ in csv.DictReader(stream))
        write_json(
            directory / "training_request.json",
            {
                "version": "wardiq.m3.training-feature-request.v1",
                "items_file": training_inventory.name,
                "item_count": count,
                "items_sha256": sha256(training_inventory),
                "source_parquet": "data/disjoint/train.parquet",
                "source_parquet_sha256": provenance[str(paths["train_images"].resolve())],
                "model_id": CLIP_MODEL_ID,
                "model_revision": CLIP_MODEL_REVISION,
                "embedding_dimension": 512,
                "dtype": "float32",
                "normalized": True,
                "preparation": "Hana's full_image_source product-photo preparation",
                "status": "development_features_not_final_model_acceptance",
            },
        )


def build(args):
    paths = source_paths(args.source_root)
    paths["taxonomy"] = args.taxonomy
    output = args.output.resolve()
    protect_evidence(output)
    protected = [args.source_root.resolve(), args.cache_records.resolve()]
    if any(
        output == path or output in path.parents or path in output.parents for path in protected
    ):
        raise ValueError("Output overlaps source data or the existing cache")
    if output.exists():
        raise ValueError("Output already exists; use a new version directory")
    if args.seed < 0:
        raise ValueError("Seed must be nonnegative")
    provenance = {str(path.resolve()): sha256(path) for path in paths.values()}
    taxonomy = load_taxonomy(args.taxonomy)
    items = scan_items(paths, taxonomy)
    eligible, exclusions = split_eligibility(items)
    output.mkdir(parents=True)
    retained, original, summary = filter_examples(paths, items, eligible, output)
    write_jsonl(output / "excluded_items.jsonl", exclusions)
    inventory = []
    for split in SPLITS:
        for key, row in sorted(items[split].items()):
            inventory.append({**row, "split_eligible": key in eligible[split]})
    write_csv(output / "item_inventory.csv", inventory)
    unknown = {
        split: sum(not row["category_supported"] for row in items[split].values())
        for split in SPLITS
    }
    report = {
        "version": VERSION,
        "status": "provisional_development_not_team_accepted",
        "policy": "preserve_test_filter_validation_then_train_against_heldout",
        "taxonomy_version": taxonomy["taxonomy_version"],
        "category_policy": "preserve_source_ids_unmapped_common_category_empty",
        "seed": args.seed,
        "implementation_sha256": sha256(Path(__file__)),
        "category_lookup_implementation_sha256": sha256(ROOT / "scripts/apply_taxonomy.py"),
        "negative_category_matching": "exact_original_source_category_id",
        "split_summary": summary,
        "unsupported_category_items": unknown,
        "source_files_sha256": provenance,
        "source_files_unchanged": False,
        "item_id_overlap": 0,
        "exact_image_hash_overlap": 0,
        "source_outfit_id_overlap": 0,
        "near_duplicate_product_leakage_verified": False,
        "training_ready": False,
        "handoff_ready": False,
    }
    if args.stage == "pairs":
        pairs, pair_summary = {}, {}
        for split in SPLITS:
            pairs[split], pair_summary[split] = make_pairs(
                items[split],
                retained[split],
                original[split],
                split,
                args.seed,
            )
            write_jsonl(output / split / "pairs.jsonl", pairs[split])
        coverage, missing = cache_coverage(args.cache_records, items, pairs)
        write_jsonl(output / "missing_feature_items.jsonl", missing)
        write_feature_request(output, items, pairs, paths, provenance)
        report.update(
            pair_summary=pair_summary,
            cache_coverage=coverage,
            required_train_validation_cache_coverage_complete=all(
                coverage[s]["missing_items"] == 0
                and pair_summary[s]["positive_pairs"] > 0
                and pair_summary[s]["negative_pairs"] > 0
                for s in ("train", "validation")
            ),
        )
    else:
        report["scope"] = "split_inventory_audit_only"
    for path, expected in provenance.items():
        if sha256(path) != expected:
            raise ValueError(f"Source changed during preparation: {path}")
    report["source_files_unchanged"] = True
    report["outputs_sha256"] = {
        path.relative_to(output).as_posix(): sha256(path)
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    write_json(output / "report.json", report)
    print(
        json.dumps(
            {
                "split_summary": summary,
                "unsupported_category_items": unknown,
                "training_ready": report["training_ready"],
            },
            indent=2,
        )
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT / "data/raw/polyvore_outfits")
    parser.add_argument("--taxonomy", type=Path, default=ROOT / "configs/m1/taxonomy.json")
    parser.add_argument(
        "--cache-records",
        type=Path,
        default=ROOT / "artifacts/m2/polyvore_full/v1/cache/records.jsonl",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/m3/compatibility_data/v1")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--stage", choices=("audit", "pairs", "training-images"), default="audit")
    parser.add_argument("--request", type=Path, help="Verified training feature-request JSON")
    args = parser.parse_args()
    try:
        if args.stage == "training-images":
            if args.request is None:
                parser.error("training-images requires --request")
            prepare_training_images(args.request, args.source_root, args.output)
        else:
            build(args)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Compatibility preparation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
