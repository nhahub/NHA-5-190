import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from wardiq.clothing.color_extraction import (
    ColorConfig,
    extract_palette,
    lab_to_rgb,
    rgb_to_lab,
    validate_palette,
)

ROOT = Path(__file__).resolve().parents[1]


def test_cie_lab_known_reference_values_and_roundtrip():
    rgb = np.array([[0, 0, 0], [255, 255, 255], [255, 0, 0]], dtype=np.uint8)
    lab = rgb_to_lab(rgb)
    np.testing.assert_allclose(lab[0], [0, 0, 0], atol=1e-9)
    np.testing.assert_allclose(lab[1], [100, 0, 0], atol=1e-9)
    np.testing.assert_allclose(lab[2], [53.24, 80.09, 67.20], atol=0.04)
    np.testing.assert_array_equal(lab_to_rgb(lab), rgb)


def test_solid_color_and_tiny_regions_reduce_cluster_count():
    result = extract_palette(np.array([[[255, 0, 0]]], dtype=np.uint8))
    assert result["status"] == "ok"
    assert result["effective_k"] == 1
    assert result["palette"][0]["proportion"] == 1
    assert result["usable_pixels"] == 1
    validate_palette(result["palette"])


def test_two_colors_population_order_and_exact_proportions():
    rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    rgb[:7] = [255, 0, 0]
    rgb[7:] = [0, 0, 255]
    result = extract_palette(rgb, ColorConfig(k=2), region_method="bbox_crop")
    assert [c["proportion"] for c in result["palette"]] == [0.7, 0.3]
    assert result["palette"][0]["a"] > 70
    assert result["palette"][1]["b"] < -100
    assert result["background_contamination_possible"] is True


def test_mask_takes_precedence_over_box_and_excludes_background():
    rgb = np.full((10, 10, 3), 255, dtype=np.uint8)
    rgb[3:6, 3:6] = [255, 0, 0]
    mask = np.zeros((10, 10), dtype=bool)
    mask[3:6, 3:6] = True
    result = extract_palette(rgb, mask=mask, bbox_xywh=[0, 0, 10, 10])
    assert result["region_method"] == "mask"
    assert result["background_contamination_possible"] is False
    assert result["usable_pixels"] == 9
    assert result["effective_k"] == 1
    assert result["palette"][0]["a"] > 70


def test_box_is_clamped_and_alpha_excludes_invisible_pixels():
    rgba = np.zeros((4, 4, 4), dtype=np.uint8)
    rgba[0, 0] = [0, 255, 0, 255]
    rgba[1, 1] = [255, 0, 0, 255]
    result = extract_palette(rgba, bbox_xywh=[-1, -1, 2, 2])
    assert result["usable_pixels"] == 1
    assert result["palette"][0]["a"] < -80


def test_invalid_mask_uses_valid_bbox_and_records_fallback():
    rgb = np.full((4, 4, 3), 255, dtype=np.uint8)
    result = extract_palette(rgb, mask=np.zeros((4, 4)), bbox_xywh=[0, 0, 2, 2])
    assert result["usable_pixels"] == 4
    assert result["region_method"] == "bbox_crop"
    assert result["fallback_used"] is True
    assert "invalid_or_empty_mask" in result["warnings"]


def test_bad_geometry_can_fallback_or_fail_by_policy():
    rgb = np.zeros((4, 4, 3), dtype=np.uint8)
    fallback = extract_palette(rgb, bbox_xywh=[float("nan"), 0, 1, 1])
    assert fallback["status"] == "ok"
    assert fallback["region_method"] == "full_image_fallback"
    assert fallback["fallback_used"] is True
    failed = extract_palette(
        rgb, ColorConfig(allow_full_image_fallback=False), bbox_xywh=[100, 100, 1, 1]
    )
    assert failed["status"] == "failed"
    assert failed["palette"] is None


def test_full_image_fallback_can_be_disabled_without_geometry():
    result = extract_palette(
        np.zeros((4, 4, 3), dtype=np.uint8), ColorConfig(allow_full_image_fallback=False)
    )
    assert result["status"] == "failed"
    assert result["failure_reason"] == "full_image_fallback_disabled"


@pytest.mark.parametrize(
    "rgb",
    [
        np.zeros((0, 0, 3), dtype=np.uint8),
        np.zeros((4, 4, 4), dtype=np.uint8),
        np.zeros((4, 4, 3), dtype=np.float32),
    ],
)
def test_empty_transparent_and_normalized_input_fail_explicitly(rgb):
    result = extract_palette(rgb)
    assert result["status"] == "failed"
    assert result["failure_reason"]
    assert result["palette"] is None


def test_sampling_is_repeatable_and_all_pixels_are_counted():
    rgb = np.random.default_rng(7).integers(0, 256, (40, 40, 3), dtype=np.uint8)
    config = ColorConfig(k=3, max_pixels=50)
    first = extract_palette(rgb, config)
    assert first == extract_palette(rgb, config)
    assert first["sampled_pixels"] == 50
    assert first["usable_pixels"] == 1600
    validate_palette(first["palette"])


@pytest.mark.parametrize(
    "settings",
    [{"k": 0}, {"seed": -1}, {"max_pixels": False}, {"allow_full_image_fallback": "false"}],
)
def test_invalid_configuration_rejected(settings):
    with pytest.raises(ValueError):
        ColorConfig(**settings)


def test_palette_validation_rejects_bad_proportions_and_nan():
    with pytest.raises(ValueError):
        validate_palette([dict(L=50, a=0, b=0, proportion=0.5)])
    with pytest.raises(ValueError):
        validate_palette([dict(L=float("nan"), a=0, b=0, proportion=1)])


def run_cli(manifest, output_dir):
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/extract_color_palettes.py"),
            "--manifest",
            str(manifest),
            "--output-dir",
            str(output_dir),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_cli_accounts_for_sample_inventory_and_is_repeatable(tmp_path):
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/prepare_garment_crops.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    manifest = ROOT / "artifacts/m1/garment_manifest.csv"
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        result = run_cli(manifest, output)
        assert result.returncode == 0, result.stderr
    assert (outputs[0] / "palettes.jsonl").read_bytes() == (
        outputs[1] / "palettes.jsonl"
    ).read_bytes()
    assert (outputs[0] / "coverage.json").read_bytes() == (
        outputs[1] / "coverage.json"
    ).read_bytes()
    coverage = json.loads((outputs[0] / "coverage.json").read_text())
    assert (
        coverage["input_rows"],
        coverage["successful"],
        coverage["excluded"],
        coverage["failed"],
    ) == (56, 18, 38, 0)
    assert coverage["full_dataset_coverage_claimed"] is False
    records = [
        json.loads(line) for line in (outputs[0] / "palettes.jsonl").read_text().splitlines()
    ]
    assert len({r["item_id"] for r in records}) == 56
    for record in records:
        if record["status"] == "ok":
            validate_palette(record["color"]["palette"])
    with Image.open(outputs[0] / "palette_contact_sheet.png") as sheet:
        assert sheet.width > 0 and sheet.height > 0


def test_cli_missing_image_is_reported_and_returns_failure(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "item_id,source_dataset,usable_derivative,image_path,crop_method\n"
        "missing,Polyvore Outfits,True,missing.png,full_image_source_precropped\n"
    )
    output = tmp_path / "out"
    result = run_cli(manifest, output)
    assert result.returncode == 1
    coverage = json.loads((output / "coverage.json").read_text())
    assert coverage["failed"] == 1
    assert coverage["successful"] == 0
