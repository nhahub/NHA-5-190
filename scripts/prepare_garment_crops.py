"""Prototype garment cropping on Eyad's five-image samples (Hana's task).

Reads configs/m1/garment_preparation.yaml, crops Fashionpedia main-apparel annotations
using their source bbox, copies Polyvore and Fashion-MNIST samples as full-image items
(neither ships a bbox/mask), applies a deterministic fallback when a box is missing or
invalid, and writes artifacts/m1/garment_manifest.csv.

This is a PROTOTYPE: it only covers the five-image samples in the handoff package, not
the full clean manifest (that needs Ziad's usable full images, currently unavailable).

Usage (from the repository root):
    python scripts/prepare_garment_crops.py
"""

import argparse
import ast
import csv
import math
import sys
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from apply_taxonomy import load_taxonomy, map_category  # noqa: E402
from research_cli import protect_evidence  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ROLE = "source_role"


def parse_bbox(value):
    try:
        parsed = ast.literal_eval(str(value))
        return parsed if isinstance(parsed, (list, tuple)) and len(parsed) == 4 else [None] * 4
    except (ValueError, SyntaxError):
        return [None] * 4


def clamp_bbox(x, y, w, h, W, H):
    """Return a clamped (x, y, w, h) inside [0,W]x[0,H], or None if the box is invalid/empty."""
    try:
        x, y, w, h = float(x), float(y), float(w), float(h)
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (x, y, w, h)) or w <= 0 or h <= 0:
        return None
    x0, y0 = max(0.0, x), max(0.0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x1 <= x0 or y1 <= y0:
        return None
    return (x0, y0, x1 - x0, y1 - y0)


def crop_fashionpedia(cfg, tax, out_root):
    rows = []
    s = pd.read_csv(cfg["manifest"], encoding="utf-8-sig")
    img_root = Path(cfg["image_root"])
    dest = Path(out_root) / "fashionpedia"
    dest.mkdir(parents=True, exist_ok=True)
    for r in s.itertuples():
        m = map_category(tax, "fashionpedia", r.category_id)
        role = m.get(ROLE) if m else None
        base = dict(
            item_id=r.item_id,
            source_dataset="Fashionpedia",
            source_item_id=r.source_annotation_id,
            source_image_id=r.source_image_id,
            source_image_path=str(img_root / r.image_file_name),
            source_split=r.source_split,
            attribute_ids=r.attribute_ids,
            segmentation_present=r.segmentation_present,
            category_id=r.category_id,
            category_label=r.category_label,
        )
        if role != "main_apparel":
            rows.append(
                {
                    **base,
                    "crop_method": "skipped_not_a_garment",
                    "output_path": None,
                    "source_bbox_xywh": r.bbox_xywh,
                    "processed_bbox_xywh": None,
                    "fallback_used": False,
                    "fallback_reason": None,
                    "annotation_availability": "present" if role else "unmapped_category",
                    "resize_scale": None,
                }
            )
            continue
        with Image.open(img_root / r.image_file_name) as source:
            im = source.convert("RGB")
        W, H = im.size
        box = clamp_bbox(*parse_bbox(r.bbox_xywh), W, H)
        if box is None:
            out = dest / f"{r.item_id}_fullimage.jpg"
            im.convert("RGB").save(out)
            rows.append(
                {
                    **base,
                    "crop_method": "fallback_full_image",
                    "output_path": str(out),
                    "source_bbox_xywh": r.bbox_xywh,
                    "processed_bbox_xywh": None,
                    "fallback_used": True,
                    "fallback_reason": "bbox missing, invalid or fully out of bounds",
                    "annotation_availability": "present",
                    "resize_scale": None,
                }
            )
        else:
            x, y, w, h = box
            # Enclose fractional source boxes in actual pixel coordinates.
            crop = im.crop((math.floor(x), math.floor(y), math.ceil(x + w), math.ceil(y + h)))
            out = dest / f"{r.item_id}_crop.jpg"
            crop.convert("RGB").save(out)
            rows.append(
                {
                    **base,
                    "crop_method": "bbox_crop",
                    "output_path": str(out),
                    "source_bbox_xywh": r.bbox_xywh,
                    "processed_bbox_xywh": [0, 0, crop.width, crop.height],
                    "clamped_source_bbox_xywh": [x, y, w, h],
                    "fallback_used": False,
                    "fallback_reason": None,
                    "annotation_availability": "present",
                    "resize_scale": None,
                }
            )
    return rows


def full_image_source(cfg, source_name, id_col, img_col, cat_col, out_root, reason, extra=None):
    rows = []
    s = pd.read_csv(cfg["manifest"], encoding="utf-8-sig")
    img_root = Path(cfg["image_root"])
    dest = Path(out_root) / source_name
    dest.mkdir(parents=True, exist_ok=True)
    for r in s.itertuples():
        fname = getattr(r, img_col)
        candidates = [img_root / fname, ROOT / fname]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            # Known handoff issue: some sample manifests reference a filename or path
            # that does not match the shipped file (prefixed, or a subfolder that was
            # never included). Fall back to a basename suffix match and flag it.
            matches = list(img_root.glob(f"*{Path(fname).name}"))
            if len(matches) != 1:
                raise FileNotFoundError(
                    f"No exact path for {fname}; expected one suffix match, found {len(matches)}"
                )
            path = matches[0]
        with Image.open(path) as source:
            im = source.convert("RGB")
        out = dest / f"{getattr(r, id_col)}_fullimage.jpg"
        im.convert("RGB").save(out)
        row = {
            "item_id": getattr(r, id_col),
            "source_dataset": source_name,
            "source_item_id": getattr(r, id_col),
            "source_image_id": getattr(r, "source_index", getattr(r, id_col)),
            "source_image_path": str(path),
            "category_id": getattr(r, "category_id", None),
            "category_label": getattr(r, cat_col, None),
            "source_split": getattr(r, "source_split", None),
            "source_index": getattr(r, "source_index", None),
            "path_resolution": "exact" if path in candidates else "unique_suffix",
            "crop_method": cfg["crop_policy"]["method"],
            "output_path": str(out),
            "source_bbox_xywh": None,
            "processed_bbox_xywh": None,
            "fallback_used": source_name == "Fashion-MNIST",
            "fallback_reason": reason,
            "annotation_availability": "unavailable_in_source",
            "resize_scale": None,
        }
        if extra:
            row.update(extra(r))
        rows.append(row)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/m1/garment_preparation.yaml")
    args = parser.parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    for source in cfg["sources"].values():
        for field in ("manifest", "image_root"):
            source[field] = str(ROOT / source[field])
    tax = load_taxonomy(ROOT / cfg["taxonomy_ref"])
    out_root = ROOT / cfg["output"]["crops_root"]
    for output in cfg["output"].values():
        protect_evidence(ROOT / output)
    # Preserve delivered project splits; never invent test membership from source splits.
    reference = pd.read_csv(ROOT / cfg["split_reference"], dtype=str, keep_default_na=False)
    if reference.item_id.duplicated().any():
        raise ValueError("Split reference contains duplicate item IDs")
    split_lookup = reference.set_index("item_id").to_dict("index")
    rows = crop_fashionpedia(cfg["sources"]["fashionpedia"], tax, out_root)
    rows += full_image_source(
        cfg["sources"]["polyvore_outfits"],
        "Polyvore Outfits",
        "item_id",
        "image_filename",
        "semantic_category",
        out_root,
        reason="single-item source photo; geometry unavailable",
    )
    rows += full_image_source(
        cfg["sources"]["fashion_mnist"],
        "Fashion-MNIST",
        "item_id",
        "original_image_path",
        "category_label",
        out_root,
        reason="native pixels unavailable; using the delivered upscaled preview",
        extra=lambda r: {
            "resize_scale": 1.0,
            "native_resolution_scale": 0.1,
            "image_size_source": "preview_upscaled",
        },
    )
    mnist_ids = {
        entry["source_label"].replace("/", " "): entry["source_id"]
        for entry in tax["sources"]["fashion_mnist"]["category_map"]
    }
    for row in rows:
        original_id = str(row["item_id"])
        if row["source_dataset"] == "Polyvore Outfits":
            candidates = [
                key for key in split_lookup if key == original_id or key.endswith("_" + original_id)
            ]
            if len(candidates) != 1:
                raise ValueError(f"Ambiguous or missing split join for Polyvore item {original_id}")
            row["item_id"] = split_lookup[candidates[0]]["omar_join_key"]
        identity = split_lookup.get(
            candidates[0] if row["source_dataset"] == "Polyvore Outfits" else original_id, {}
        )
        if not identity.get("source_target_split"):
            raise ValueError(f"Missing delivered target split for {original_id}")
        row["target_split"] = identity.get("source_target_split", "")
        row["source_target_split"] = row["target_split"]
        row["group_id"] = identity.get("leakage_group_id", "")
        row["leakage_group_id"] = row["group_id"]
        if row["source_dataset"] == "Polyvore Outfits":
            row["group_id"] = row["group_id"].split(":")[0]
            row["leakage_group_id"] = row["group_id"]
        row["omar_join_key"] = identity.get("omar_join_key", "")
        row["usable_derivative"] = bool(row["output_path"])
        row["image_path"] = row["output_path"]
        if row["source_dataset"] == "Fashion-MNIST":
            row["category_id"] = mnist_ids[row["category_label"]]
        mapping = map_category(
            tax,
            {
                "Fashionpedia": "fashionpedia",
                "Fashion-MNIST": "fashion_mnist",
                "Polyvore Outfits": "polyvore_outfits",
            }[row["source_dataset"]],
            row["category_id"],
        )
        row["common_category"] = mapping["common_category"] if mapping else None
        row["category_mapping_status"] = mapping["mapping_status"] if mapping else "unmapped"
        for field in ("image_path", "output_path", "source_image_path"):
            if row.get(field):
                path = Path(row[field]).resolve()
                row[field] = (
                    path.relative_to(ROOT).as_posix() if ROOT in path.parents else str(path)
                )
    # Also expose the 15 source images through the image-level loader contract.
    sources = {}
    for row in rows:
        key = row["omar_join_key"]
        current = (row["source_image_path"], row["target_split"], row["group_id"])
        if key in sources and sources[key] != current:
            raise ValueError(f"Conflicting source image/split metadata for {key}")
        sources[key] = current
    image_rows = []
    with (ROOT / "data/manifests/raw_manifest.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        for original in csv.DictReader(stream):
            if original["item_id"] not in sources:
                continue
            path, split, group = sources[original["item_id"]]
            key = {
                "Fashionpedia": "fashionpedia",
                "Fashion-MNIST": "fashion_mnist",
                "Polyvore Outfits": "polyvore_outfits",
            }[original["source_dataset"]]
            mappings = [
                map_category(tax, key, cid) for cid in original["category_ids"].split(";") if cid
            ]
            if any(m is None for m in mappings):
                raise ValueError(f"Unmapped source category for {original['item_id']}")
            original.update(
                image_path=path,
                target_split=split,
                group_id=group,
                category_labels=";".join(m["source_label"] for m in mappings),
                common_categories=";".join(
                    sorted({m["common_category"] for m in mappings if m["common_category"]})
                ),
                direct_common_categories=";".join(
                    sorted(
                        {
                            m["common_category"]
                            for m in mappings
                            if m["common_category"] and m["mapping_status"] == "direct"
                        }
                    )
                ),
            )
            image_rows.append(original)
    if len(image_rows) != len(sources):
        raise ValueError("Some sample source IDs are absent from the raw manifest")
    image_output = ROOT / cfg["output"]["image_manifest_path"]
    image_output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(image_rows).to_csv(image_output, index=False)
    print(f"Sample image manifest: {len(image_rows)} source images written to {image_output}")
    df = pd.DataFrame(rows)
    out_path = ROOT / cfg["output"]["manifest_path"]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)

    print(df.groupby(["source_dataset", "crop_method"]).size().to_string())
    print(f"fallback_used=True rows: {int(df.fallback_used.sum())}")
    print(f"garment manifest written to {out_path}")

    # Self-test: confirm the fallback path triggers on a synthetic invalid box
    # (the 46-annotation Fashionpedia sample has no real invalid box to exercise this on)
    assert clamp_bbox(10, 10, 0, 5, 100, 100) is None
    assert clamp_bbox(-9999, -9999, 5, 5, 100, 100) is None
    assert clamp_bbox("bad", 1, 1, 1, 100, 100) is None
    assert clamp_bbox(90, 90, 20, 20, 100, 100) == (90.0, 90.0, 10.0, 10.0)
    print("Fallback self-test: passed (synthetic invalid/edge boxes correctly rejected or clamped)")


if __name__ == "__main__":
    main()
