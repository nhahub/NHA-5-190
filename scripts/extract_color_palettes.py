"""Extract the M2 color component and account for every input manifest row."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import numpy as np
import yaml
from PIL import Image, ImageCms, ImageDraw, ImageFont

# This CLI is intentionally serial. Avoid physical-core probing on Windows hosts
# without WMIC; honor an existing caller resource budget.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from research_cli import protect_evidence  # noqa: E402

from wardiq.clothing.color_extraction import (  # noqa: E402
    EXTRACTOR_VERSION,
    LAB_CONVENTION,
    ColorConfig,
    extract_palette,
    lab_to_rgb,
)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_text(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)


def read_rgb(path):
    """Decode pixels; honor embedded ICC profiles and retain original alpha."""
    with Image.open(path) as source:
        source.load()
        rgba = source.convert("RGBA")
        rgb = source.convert("RGB")
        icc = source.info.get("icc_profile")
        if icc:
            profile = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            rgb = ImageCms.profileToProfile(
                rgb, profile, ImageCms.createProfile("sRGB"), outputMode="RGB"
            )
        values = np.asarray(rgb, dtype=np.uint8)
        alpha = np.asarray(rgba, dtype=np.uint8)[..., 3:4]
        return np.concatenate((values, alpha), axis=2), "ICC_to_sRGB" if icc else "assumed_sRGB"


def contact_sheet(records, image_root, output, limit):
    successful = [r for r in records if r["status"] == "ok"][:limit]
    columns, card_width, card_height = 3, 380, 330
    sheet = Image.new(
        "RGB",
        (columns * card_width, max(1, (len(successful) + columns - 1) // columns) * card_height),
        "#eef1f5",
    )
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 12)
    except OSError:
        font = ImageFont.load_default()
    for index, record in enumerate(successful):
        x, y = index % columns * card_width, index // columns * card_height
        draw.rounded_rectangle(
            (x + 8, y + 8, x + card_width - 8, y + card_height - 8), radius=8, fill="white"
        )
        image_values, _ = read_rgb(image_root / record["image_path"])
        image = Image.fromarray(image_values)
        image.thumbnail((card_width - 32, 190))
        sheet.paste(image, (x + (card_width - image.width) // 2, y + 16), image)
        draw.text((x + 16, y + 212), record["item_id"], fill="#17243a", font=font)
        draw.text((x + 16, y + 231), record["region_method"], fill="#4e5b70", font=font)
        risk = (
            "Background risk: review needed"
            if record["background_contamination_possible"]
            else "Mask-selected pixels"
        )
        draw.text((x + 16, y + 250), risk, fill="#8f4c13", font=font)
        palette = record["color"]["palette"]
        swatches = lab_to_rgb(np.array([[c["L"], c["a"], c["b"]] for c in palette]))
        for i, (color, swatch) in enumerate(zip(palette, swatches)):
            swatch_width = (card_width - 32) / len(palette)
            left = x + 16 + int(i * swatch_width)
            draw.rectangle(
                (left, y + 274, left + int(swatch_width) - 5, y + 293),
                fill=tuple(int(v) for v in swatch),
            )
            if swatch_width >= 40:
                draw.text((left, y + 298), f"{color['proportion']:.1%}", fill="#17243a", font=font)
    sheet.save(output)


def run(manifest, config_path, output_dir, image_root):
    protect_evidence(output_dir)
    settings = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict) or settings.get("schema_version") != "wardiq.color-config.v1":
        raise ValueError("Unsupported color config schema")
    config = ColorConfig(**settings["extractor"])
    excluded = settings.get("excluded_datasets", ["Fashion-MNIST"])
    if not isinstance(excluded, list) or any(not isinstance(value, str) for value in excluded):
        raise ValueError("excluded_datasets must be a list of dataset names")
    review_limit = settings.get("review_sample_limit", 24)
    if not isinstance(review_limit, int) or isinstance(review_limit, bool) or review_limit < 1:
        raise ValueError("review_sample_limit must be a positive integer")
    with manifest.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"item_id", "source_dataset", "usable_derivative", "image_path", "crop_method"}
        if not required <= set(reader.fieldnames or []):
            raise ValueError(
                "Garment manifest missing fields: "
                f"{sorted(required - set(reader.fieldnames or []))}"
            )
        rows = list(reader)
    if not rows or any(not row["item_id"] for row in rows):
        raise ValueError("Input manifest needs nonempty rows and stable item IDs")
    if len({row["item_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate item_id in color manifest")
    records = []
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    implementation = ROOT / "src/wardiq/clothing/color_extraction.py"
    provenance = {
        "manifest_sha256": sha256(manifest),
        "config_sha256": sha256(config_path),
        "implementation_sha256": sha256(implementation),
        "runner_sha256": sha256(Path(__file__)),
        "code_revision": revision,
        "extractor_version": EXTRACTOR_VERSION,
        "lab_convention": LAB_CONVENTION,
        "configuration": asdict(config),
        "scope": settings.get("scope", "explicit_manifest"),
        "numpy_version": np.__version__,
        "numerical_threads": 1,
    }
    import sklearn

    provenance["sklearn_version"] = sklearn.__version__
    for row in rows:
        record = {
            "component_schema_version": "wardiq.color-component.v1",
            **{
                field: row.get(field) or None
                for field in (
                    "item_id",
                    "source_dataset",
                    "source_item_id",
                    "source_image_id",
                    "source_image_path",
                    "image_path",
                    "target_split",
                    "group_id",
                    "omar_join_key",
                    "crop_method",
                    "fallback_reason",
                    "mask_path",
                )
            },
            "color": {"palette": None},
            "status": "excluded",
            "failure_reason": None,
            "exclusion_reason": None,
            "config_sha256": provenance["config_sha256"],
            "extractor_version": EXTRACTOR_VERSION,
        }
        if row["source_dataset"] in excluded:
            record["exclusion_reason"] = "grayscale_smoke_test_source_not_color_evaluation"
        elif row["usable_derivative"].strip().lower() in {"false", "0", ""}:
            record["exclusion_reason"] = "no_usable_garment_derivative"
        elif row["usable_derivative"].strip().lower() not in {"true", "1"}:
            raise ValueError(f"Invalid usable_derivative flag for {row['item_id']}")
        else:
            path = image_root / row["image_path"]
            try:
                values, color_profile = read_rgb(path)
                mask = None
                mask_warning = None
                if row.get("mask_path"):
                    try:
                        with Image.open(image_root / row["mask_path"]) as mask_image:
                            mask = np.asarray(mask_image.convert("L"))
                        record["mask_sha256"] = sha256(image_root / row["mask_path"])
                    except OSError:
                        mask_warning = "mask_file_unavailable"
                region = {
                    "bbox_crop": "bbox_crop",
                    "full_image_source_precropped": "source_product_photo",
                }.get(row["crop_method"], "full_image_fallback")
                result = extract_palette(
                    values,
                    config,
                    mask=mask,
                    region_method=region,
                    fallback_used=row.get("fallback_used", "").lower() in {"true", "1"},
                )
                if mask_warning:
                    result["warnings"].append(mask_warning)
                    result["fallback_used"] = True
                palette = result.pop("palette")
                record.update(
                    result,
                    color={"palette": palette},
                    image_sha256=sha256(path),
                    input_color_profile=color_profile,
                )
            except (OSError, ValueError, ImageCms.PyCMSError) as error:
                record.update(status="failed", failure_reason=f"{type(error).__name__}: {error}")
        records.append(record)
    counts = Counter(record["status"] for record in records)
    image_hashes = [(r["item_id"], r.get("image_sha256"), r.get("mask_sha256")) for r in records]
    signature = hashlib.sha256(json_text([provenance, image_hashes]).encode()).hexdigest()
    summary = {
        **provenance,
        "run_signature": signature,
        "input_rows": len(records),
        "successful": counts["ok"],
        "excluded": counts["excluded"],
        "failed": counts["failed"],
        "by_dataset": {
            source: dict(Counter(r["status"] for r in records if r["source_dataset"] == source))
            for source in sorted({r["source_dataset"] for r in records})
        },
        "review_status": "pending_visual_review",
        "contact_sheet_records": min(counts["ok"], review_limit),
        "full_dataset_coverage_claimed": False,
        "background_risk_records": sum(
            bool(r.get("background_contamination_possible")) for r in records
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "palettes.jsonl").write_text(
        "".join(json_text(r) + "\n" for r in records), encoding="utf-8"
    )
    (output_dir / "coverage.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    contact_sheet(records, image_root, output_dir / "palette_contact_sheet.png", review_limit)
    print(
        f"Color extraction: {len(records)} input rows; {counts['ok']} successful; "
        f"{counts['excluded']} excluded; {counts['failed']} failed"
    )
    print(f"Outputs: {output_dir}")
    return int(bool(counts["failed"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "artifacts/m1/garment_manifest.csv")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/m2/color_extraction.yaml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/m2/color/v1")
    parser.add_argument("--image-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        return run(args.manifest, args.config, args.output_dir, args.image_root)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Color extraction failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
