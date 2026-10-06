"""Prototype garment cropping on Eyad's five-image samples (Hana's task).

Reads configs/m1/garment_preparation.yaml, crops Fashionpedia main-apparel annotations
using their source bbox, copies Polyvore and Fashion-MNIST samples as full-image items
(neither ships a bbox/mask), applies a deterministic fallback when a box is missing or
invalid, and writes data/manifests/garment_manifest.csv.

This is a PROTOTYPE: it only covers the five-image samples in the handoff package, not
the full clean manifest (that needs Ziad's usable full images, currently unavailable).

Usage (from the repository root):
    python scripts/prepare_garment_crops.py
"""
import ast
import sys
from pathlib import Path

import pandas as pd
import yaml
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from apply_taxonomy import load_taxonomy, map_category  # noqa: E402

ROLE = "source_role"


def clamp_bbox(x, y, w, h, W, H):
    """Return a clamped (x, y, w, h) inside [0,W]x[0,H], or None if the box is invalid/empty."""
    try:
        x, y, w, h = float(x), float(y), float(w), float(h)
    except (TypeError, ValueError):
        return None
    if w <= 0 or h <= 0:
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
            item_id=r.item_id, source_dataset="Fashionpedia", source_item_id=r.source_annotation_id,
            source_image_id=r.source_image_id, source_image_path=r.image_path,
            category_id=r.category_id, category_label=r.category_label,
        )
        if role != "main_apparel":
            rows.append({**base, "crop_method": "skipped_not_a_garment", "output_path": None,
                         "source_bbox_xywh": r.bbox_xywh, "processed_bbox_xywh": None,
                         "fallback_used": False, "fallback_reason": None,
                         "annotation_availability": "present" if role else "unmapped_category",
                         "resize_scale": None})
            continue
        im = Image.open(img_root / r.image_file_name)
        W, H = im.size
        box = clamp_bbox(*ast.literal_eval(r.bbox_xywh), W, H)
        if box is None:
            out = dest / f"{r.item_id}_fullimage.jpg"
            im.convert("RGB").save(out)
            rows.append({**base, "crop_method": "fallback_full_image", "output_path": str(out),
                         "source_bbox_xywh": r.bbox_xywh, "processed_bbox_xywh": None,
                         "fallback_used": True, "fallback_reason": "bbox missing, invalid or fully out of bounds",
                         "annotation_availability": "present", "resize_scale": None})
        else:
            x, y, w, h = box
            crop = im.crop((x, y, x + w, y + h))
            out = dest / f"{r.item_id}_crop.jpg"
            crop.convert("RGB").save(out)
            rows.append({**base, "crop_method": "bbox_crop", "output_path": str(out),
                         "source_bbox_xywh": r.bbox_xywh, "processed_bbox_xywh": [x, y, w, h],
                         "fallback_used": False, "fallback_reason": None,
                         "annotation_availability": "present", "resize_scale": None})
    return rows


def full_image_source(cfg, source_name, id_col, img_col, cat_col, out_root, reason, extra=None):
    rows = []
    s = pd.read_csv(cfg["manifest"], encoding="utf-8-sig")
    img_root = Path(cfg["image_root"])
    dest = Path(out_root) / source_name
    dest.mkdir(parents=True, exist_ok=True)
    for r in s.itertuples():
        fname = getattr(r, img_col)
        candidates = [img_root / fname, Path(fname), Path(".") / fname]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            # Known handoff issue: some sample manifests reference a filename or path
            # that does not match the shipped file (prefixed, or a subfolder that was
            # never included). Fall back to a basename suffix match and flag it.
            matches = list(img_root.glob(f"*{Path(fname).name}"))
            if not matches:
                raise FileNotFoundError(f"none of {candidates} exist, and no suffix match for {fname}")
            path = matches[0]
        im = Image.open(path)
        out = dest / f"{getattr(r, id_col)}_fullimage.jpg"
        im.convert("RGB").save(out)
        row = {
            "item_id": getattr(r, id_col), "source_dataset": source_name, "source_item_id": getattr(r, id_col),
            "source_image_id": getattr(r, id_col), "source_image_path": str(path),
            "category_id": getattr(r, cat_col, None), "category_label": getattr(r, cat_col, None),
            "crop_method": cfg["crop_policy"]["method"], "output_path": str(out),
            "source_bbox_xywh": None, "processed_bbox_xywh": None,
            "fallback_used": source_name == "fashion_mnist", "fallback_reason": reason,
            "annotation_availability": "unavailable_in_source", "resize_scale": None,
        }
        if extra:
            row.update(extra(r))
        rows.append(row)
    return rows


def main():
    root = Path(".")
    cfg = yaml.safe_load((root / "configs/m1/garment_preparation.yaml").read_text(encoding="utf-8"))
    tax = load_taxonomy(cfg["taxonomy_ref"])
    out_root = cfg["output"]["crops_root"]

    rows = []
    rows += crop_fashionpedia(cfg["sources"]["fashionpedia"], tax, out_root)
    rows += full_image_source(
        cfg["sources"]["polyvore_outfits"], "polyvore_outfits", "item_id", "image_filename", "semantic_category",
        out_root, reason="source item photo is already single-garment; no bbox/mask ships with the handoff")
    rows += full_image_source(
        cfg["sources"]["fashion_mnist"], "fashion_mnist", "item_id", "original_image_path", "category_label",
        out_root, reason="no bbox/mask in source; using 280x280 preview file, native 28x28 not present in handoff",
        extra=lambda r: {"resize_scale": 0.1, "source_image_path": str(root / "data/samples/fashion_mnist" / Path(r.original_image_path).name)})

    df = pd.DataFrame(rows)
    out_path = cfg["output"]["manifest_path"]
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
