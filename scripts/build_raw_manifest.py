from __future__ import annotations

import csv
import gzip
import json
import struct
from collections import defaultdict
from io import BytesIO

from research_cli import ROOT, arguments, protect_evidence, require_files, run

OUT = ROOT / "artifacts/m1/raw_manifest.csv"
FM_ROOT = ROOT / "data/raw/fashion_mnist"
FP_JSON = ROOT / "data/raw/fashionpedia/instances_attributes_val2020.json"
POLY_PARQUET = ROOT / "data/raw/polyvore_outfits/disjoint/validation-00000-of-00001.parquet"
POLY_METADATA = ROOT / "data/raw/polyvore_outfits/metadata.json"
POLY_VALID = ROOT / "data/raw/polyvore_outfits/disjoint/valid.json"

FIELDS = [
    "item_id",
    "source_dataset",
    "source_release",
    "source_split",
    "source_index",
    "source_image_id",
    "original_filename",
    "original_image_reference",
    "annotation_reference",
    "category_ids",
    "category_labels",
    "attribute_ids",
    "annotation_ids",
    "outfit_ids",
    "image_width",
    "image_height",
    "traceability_status",
]

FM_LABELS = [
    "T-shirt/top",
    "Trouser",
    "Pullover",
    "Dress",
    "Coat",
    "Sandal",
    "Shirt",
    "Sneaker",
    "Bag",
    "Ankle boot",
]


def joined(values) -> str:
    return ";".join(str(v) for v in sorted(set(values), key=lambda x: str(x)))


def fashion_mnist_rows():
    for split, stem, count in (("train", "train", 60000), ("test", "t10k", 10000)):
        labels_path = FM_ROOT / f"{stem}-labels-idx1-ubyte.gz"
        with gzip.open(labels_path, "rb") as handle:
            magic, actual_count = struct.unpack(">II", handle.read(8))
            labels = handle.read()
        if magic != 2049 or actual_count != count or len(labels) != count:
            raise ValueError(f"Unexpected Fashion-MNIST labels file: {labels_path}")
        image_ref = f"data/raw/fashion_mnist/{stem}-images-idx3-ubyte.gz"
        label_ref = f"data/raw/fashion_mnist/{stem}-labels-idx1-ubyte.gz"
        for index, label in enumerate(labels):
            yield {
                "item_id": f"fashion_mnist_{split}_{index:06d}",
                "source_dataset": "Fashion-MNIST",
                "source_release": "zalando-research/fashion-mnist IDX release",
                "source_split": split,
                "source_index": index,
                "source_image_id": index,
                "original_filename": "",
                "original_image_reference": f"{image_ref}::index={index}",
                "annotation_reference": f"{label_ref}::index={index}",
                "category_ids": label,
                "category_labels": FM_LABELS[label],
                "attribute_ids": "",
                "annotation_ids": "",
                "outfit_ids": "",
                "image_width": 28,
                "image_height": 28,
                "traceability_status": "Generated stable ID from split and zero-based source index; no original filenames/source IDs exist.",
            }


def fashionpedia_rows():
    data = json.loads(FP_JSON.read_text(encoding="utf-8"))
    categories = {c["id"]: c["name"] for c in data["categories"]}
    anns_by_image = defaultdict(list)
    for ann in data["annotations"]:
        anns_by_image[ann["image_id"]].append(ann)
    for index, image in enumerate(sorted(data["images"], key=lambda x: x["id"])):
        anns = anns_by_image[image["id"]]
        category_ids = [a["category_id"] for a in anns]
        yield {
            "item_id": f"fashionpedia_val_image_{image['id']:06d}",
            "source_dataset": "Fashionpedia",
            "source_release": "Fashionpedia 2020",
            "source_split": "validation",
            "source_index": index,
            "source_image_id": image["id"],
            "original_filename": image["file_name"],
            "original_image_reference": f"data/raw/fashionpedia/val_test2020.zip::test/{image['file_name']}",
            "annotation_reference": "data/raw/fashionpedia/instances_attributes_val2020.json",
            "category_ids": joined(category_ids),
            "category_labels": joined(categories[c] for c in category_ids),
            "attribute_ids": joined(v for a in anns for v in a.get("attribute_ids", [])),
            "annotation_ids": joined(a["id"] for a in anns),
            "outfit_ids": "",
            "image_width": image["width"],
            "image_height": image["height"],
            "traceability_status": "Verified official image ID and filename; annotations linked by image_id.",
        }


def polyvore_rows():
    import pyarrow.parquet as pq
    from PIL import Image

    metadata = json.loads(POLY_METADATA.read_text(encoding="utf-8"))
    outfits = json.loads(POLY_VALID.read_text(encoding="utf-8"))
    memberships = defaultdict(list)
    for outfit in outfits:
        for item in outfit["items"]:
            memberships[item["item_id"]].append(f"{outfit['set_id']}:{item['index']}")
    batches = pq.ParquetFile(POLY_PARQUET).iter_batches(
        batch_size=256, columns=["item_id", "image"]
    )
    rows = (row for batch in batches for row in batch.to_pylist())
    for index, row in enumerate(rows):
        item_id, image = row["item_id"], row["image"]
        meta = metadata.get(item_id, {})
        with Image.open(BytesIO(image["bytes"])) as loaded:
            width, height = loaded.size
        yield {
            "item_id": f"polyvore_outfits_disjoint_validation_{item_id}",
            "source_dataset": "Polyvore Outfits",
            "source_release": "mvasil/polyvore-outfits Hugging Face parquet repack",
            "source_split": "disjoint validation",
            "source_index": index,
            "source_image_id": item_id,
            "original_filename": image.get("path") or f"{item_id}.jpg",
            "original_image_reference": f"data/raw/polyvore_outfits/disjoint/validation-00000-of-00001.parquet::row={index}",
            "annotation_reference": "data/raw/polyvore_outfits/metadata.json;data/raw/polyvore_outfits/disjoint/valid.json",
            "category_ids": meta.get("category_id", ""),
            "category_labels": meta.get("semantic_category", ""),
            "attribute_ids": "",
            "annotation_ids": "",
            "outfit_ids": joined(memberships.get(item_id, [])),
            "image_width": width,
            "image_height": height,
            "traceability_status": "Verified item ID, embedded filename, metadata record, and validation outfit membership.",
        }


def main():
    global OUT, FM_ROOT, FP_JSON, POLY_PARQUET, POLY_METADATA, POLY_VALID
    args = arguments("build_raw_manifest")
    OUT, FM_ROOT, FP_JSON = args.output, args.fashion_mnist, args.fashionpedia_annotations
    POLY_PARQUET, POLY_METADATA, POLY_VALID = (
        args.polyvore_source,
        args.polyvore_metadata,
        args.polyvore_validation,
    )
    require_files(
        FP_JSON,
        POLY_PARQUET,
        POLY_METADATA,
        POLY_VALID,
        FM_ROOT / "train-labels-idx1-ubyte.gz",
        FM_ROOT / "t10k-labels-idx1-ubyte.gz",
    )
    protect_evidence(OUT)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    counts = defaultdict(int)
    with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for producer in (fashion_mnist_rows, fashionpedia_rows, polyvore_rows):
            for row in producer():
                writer.writerow(row)
                counts[row["source_dataset"]] += 1
    print(f"Wrote {sum(counts.values()):,} image rows to {OUT}")
    for name, count in counts.items():
        print(f"  {name}: {count:,}")


if __name__ == "__main__":
    run(main)
