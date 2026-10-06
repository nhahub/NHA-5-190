import pandas as pd
from PIL import Image

from wardiq.data.datasets import (
    M1_M2_FIELDS,
    WardiqGarmentDataset,
    _parse_bbox,
    _parse_list,
    _transform_bbox,
)


def test_m1_m2_contract_fields_are_stable():
    assert M1_M2_FIELDS == (
        "item_id",
        "source_dataset",
        "image_path",
        "category_label",
        "available_attributes",
        "bounding_box",
        "segmentation_mask",
        "split",
    )


def test_parse_list_handles_manifest_formats():
    assert _parse_list('["shirt", "pants"]') == ["shirt", "pants"]
    assert _parse_list("shirt;pants") == ["shirt", "pants"]
    assert _parse_list("") == []


def test_parse_bbox_handles_xywh_and_bad_values():
    assert _parse_bbox("[1, 2, 30, 40]") == [1.0, 2.0, 30.0, 40.0]
    assert _parse_bbox("not-a-bbox") is None


def test_transform_bbox_resizes_xywh():
    bbox = _transform_bbox(
        [10.0, 20.0, 30.0, 40.0],
        original_size=(100, 200),
        target_size=(200, 400),
        flipped=False,
    )

    assert bbox == [20.0, 40.0, 60.0, 80.0]


def test_transform_bbox_flips_xywh():
    bbox = _transform_bbox(
        [20.0, 10.0, 30.0, 20.0],
        original_size=(100, 100),
        target_size=(100, 100),
        flipped=True,
    )

    assert bbox == [50.0, 10.0, 30.0, 20.0]


def test_garment_loader_preserves_traceability_and_bbox(tmp_path):
    image_path = tmp_path / "garment.png"
    Image.new("RGB", (100, 200)).save(image_path)

    manifest = pd.DataFrame(
        [
            {
                "item_id": "item-1",
                "source_dataset": "fashionpedia",
                "target_split": "validation",
                "usable_derivative": True,
                "image_path": "garment.png",
                "crop_method": "bbox_crop",
                "processed_bbox_xywh": "[10, 20, 30, 40]",
                "source_bbox_xywh": "[10, 20, 30, 40]",
                "category_label": "shirt",
                "category_id": 1,
                "category_mapping_status": "mapped",
                "fallback_used": False,
                "group_id": "group-1",
                "source_image_id": "image-1",
                "source_release": "release-1",
                "source_split": "validation",
                "source_index": 7,
                "original_filename": "original.jpg",
                "original_image_reference": "original-ref",
                "annotation_reference": "annotation-ref",
                "annotation_ids": "[1]",
                "outfit_ids": "[2]",
                "traceability_status": "complete",
            }
        ]
    )

    dataset = WardiqGarmentDataset(
        manifest,
        split="validation",
        image_root=tmp_path,
    )

    sample = dataset[0]

    assert sample["item_id"] == "item-1"
    assert sample["source_release"] == "release-1"
    assert sample["source_split"] == "validation"
    assert sample["source_index"] == 7
    assert sample["source_image_id"] == "image-1"
    assert sample["original_filename"] == "original.jpg"
    assert sample["annotation_reference"] == "annotation-ref"
    assert sample["traceability_status"] == "complete"
    assert sample["bounding_box"] == [0.0, 0.0, 224.0, 224.0]
    assert sample["segmentation_mask"] is None


def test_garment_loader_resolves_relative_image_root(tmp_path):
    image_path = tmp_path / "garment.png"
    Image.new("RGB", (100, 100)).save(image_path)

    manifest = pd.DataFrame(
        [
            {
                "item_id": "item-1",
                "source_dataset": "fashion-mnist",
                "target_split": "validation",
                "usable_derivative": True,
                "image_path": "garment.png",
                "crop_method": "full_image",
                "category_label": "shirt",
                "category_id": 1,
                "fallback_used": True,
            }
        ]
    )

    dataset = WardiqGarmentDataset(
        manifest,
        split="validation",
        image_root=tmp_path,
    )

    sample = dataset[0]

    assert sample["image"].shape == (3, 224, 224)
