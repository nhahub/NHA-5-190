import importlib.util
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest
import torch
from PIL import Image

from wardiq.data.datasets import WardiqGarmentDataset, WardiqImageDataset, _parse_bbox, _parse_bool
from wardiq.data.preprocessing import build_transforms

ROOT = Path(__file__).resolve().parents[1]


def script_module(name):
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("box", ["", "bad", "[1, 2]", "[1,2,-3,4]", "[1e309,2,3,4]"])
def test_invalid_geometry_uses_full_image_fallback(tmp_path, box):
    crops = script_module("prepare_garment_crops")
    taxonomy = script_module("apply_taxonomy").load_taxonomy(ROOT / "configs/m1/taxonomy.json")
    Image.new("RGB", (20, 30)).save(tmp_path / "source.png")
    manifest = tmp_path / "annotations.csv"
    pd.DataFrame(
        [
            dict(
                item_id="demo",
                source_annotation_id=1,
                source_image_id=2,
                image_path="source.png",
                image_file_name="source.png",
                category_id=0,
                category_label="shirt, blouse",
                bbox_xywh=box,
                source_split="validation",
                attribute_ids="[1]",
                segmentation_present=False,
            )
        ]
    ).to_csv(manifest, index=False)
    rows = crops.crop_fashionpedia(
        {"manifest": manifest, "image_root": tmp_path}, taxonomy, tmp_path / "out"
    )
    assert rows[0]["crop_method"] == "fallback_full_image"
    assert rows[0]["fallback_used"] is True
    with Image.open(rows[0]["output_path"]) as result:
        assert result.size == (20, 30)


def test_training_flip_and_non_square_geometry_are_synchronized(tmp_path, monkeypatch):
    image = Image.new("RGB", (100, 50), "black")
    image.paste("white", (0, 0, 20, 50))
    image.save(tmp_path / "image.png")
    config = tmp_path / "config.yaml"
    config.write_text(
        "image_size: [50, 100]\nnormalization:\n  mean: [0, 0, 0]\n"
        "  std: [1, 1, 1]\ntrain:\n  random_horizontal_flip: true\n"
        "  horizontal_flip_probability: 1\n"
    )
    frame = pd.DataFrame(
        [
            dict(
                item_id="demo",
                target_split="train",
                usable_derivative="True",
                image_path="image.png",
                source_dataset="Fashionpedia",
                processed_bbox_xywh="[0,0,20,50]",
                fallback_used="False",
            )
        ]
    )
    monkeypatch.setattr("wardiq.data.datasets.random.random", lambda: 0)
    sample = WardiqGarmentDataset(frame, "train", image_root=tmp_path, config_path=config)[0]
    assert sample["image"].shape == (3, 50, 100)
    assert sample["bounding_box"] == [80, 0, 20, 50]
    assert torch.all(sample["image"][:, :, 80:] == 1)
    assert torch.all(sample["image"][:, :, :80] == 0)
    assert sample["fallback_used"] is False


def test_sample_pipeline_outputs_load_in_pytorch(tmp_path):
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/prepare_garment_crops.py")],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    frame = pd.read_csv(ROOT / "artifacts/m1/garment_manifest.csv")
    images = pd.read_csv(ROOT / "artifacts/m1/sample_image_manifest.csv")
    assert len(images) == 15
    for split, count in [("train", 5), ("validation", 10)]:
        source_dataset = WardiqImageDataset(images, split, image_root=ROOT)
        assert len(source_dataset) == count
        for sample in source_dataset:
            assert sample["image"].shape == (3, 224, 224)
            assert torch.isfinite(sample["image"]).all()
            assert sample["source_release"]
    assert len(frame) == 56
    assert frame.usable_derivative.sum() == 23
    assert (frame.target_split == frame.source_target_split).all()
    assignments = pd.read_csv(ROOT / "data/manifests/split_manifest.csv").set_index("item_id")
    for row in frame.itertuples():
        assert row.target_split == assignments.loc[row.omar_join_key, "target_split"]
    for split, count in [("train", 5), ("validation", 18)]:
        dataset = WardiqGarmentDataset(frame, split, image_root=ROOT)
        assert len(dataset) == count
        for sample in dataset:
            assert sample["image"].shape == (3, 224, 224)
            assert torch.isfinite(sample["image"]).all()
            if sample["crop_method"] == "bbox_crop":
                assert sample["bounding_box"] == [0, 0, 224, 224]


def test_unknown_taxonomy_category_does_not_crash(tmp_path):
    manifest = tmp_path / "manifest.csv"
    pd.DataFrame(
        [dict(source_dataset="Fashionpedia", category_ids="999", category_labels="unknown")]
    ).to_csv(manifest, index=False)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/apply_taxonomy.py"),
            "--manifest",
            str(manifest),
            "--out",
            str(tmp_path / "coverage.csv"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "missing from taxonomy: 1" in result.stdout
    assert "Traceback" not in result.stderr


def test_invalid_bbox_and_string_boolean():
    assert _parse_bbox("[1e309, 0, 1, 1]") is None
    assert _parse_bbox("[0, 0, -1, 1]") is None
    assert _parse_bool("False") is False


def test_fractional_box_produces_nonempty_crop(tmp_path):
    crops = script_module("prepare_garment_crops")
    taxonomy = script_module("apply_taxonomy").load_taxonomy(ROOT / "configs/m1/taxonomy.json")
    Image.new("RGB", (20, 30)).save(tmp_path / "source.png")
    manifest = tmp_path / "annotations.csv"
    pd.DataFrame(
        [
            dict(
                item_id="tiny",
                source_annotation_id=1,
                source_image_id=2,
                image_path="source.png",
                image_file_name="source.png",
                category_id=0,
                category_label="shirt, blouse",
                bbox_xywh="[1.1, 2.1, 0.1, 0.1]",
                source_split="validation",
                attribute_ids="[1]",
                segmentation_present=False,
            )
        ]
    ).to_csv(manifest, index=False)
    row = crops.crop_fashionpedia(
        {"manifest": manifest, "image_root": tmp_path}, taxonomy, tmp_path / "out"
    )[0]
    with Image.open(row["output_path"]) as result:
        assert result.size == (1, 1)
    assert row["processed_bbox_xywh"] == [0, 0, 1, 1]
    assert row["fallback_used"] is False


def test_invalid_preprocessing_config_is_rejected():
    with pytest.raises(ValueError, match="image_size"):
        build_transforms(config={"image_size": [0, 224]})
