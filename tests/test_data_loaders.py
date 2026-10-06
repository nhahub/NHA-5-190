from wardiq.data.datasets import M1_M2_FIELDS, _parse_bbox, _parse_list


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
