"""Regressions for inherited category alignment and validation false passes."""

from unittest.mock import patch

import pytest

from scripts import validate_m1_images
from scripts.check_manifest_duplicates import duplicate_members
from scripts.prepare_clean_manifest import clean_row
from scripts.validate_m1_images import validation_status


def test_categories_resolved_by_id_not_independent_label_position() -> None:
    row = {
        "item_id": "fp_1",
        "source_dataset": "Fashionpedia",
        "category_ids": "0;4",
        "category_labels": "jacket;shirt",
    }
    cleaned = clean_row(row, {"0": "shirt", "4": "jacket"})
    assert cleaned["category_labels"] == "shirt;jacket"
    assert row["category_labels"] == "jacket;shirt"
    assert cleaned["category_ids"] == "0;4"
    assert cleaned["image_validation_scope"] == "manifest_only"


def test_unknown_id_does_not_fabricate_label() -> None:
    with pytest.raises(ValueError, match="Unknown/empty"):
        clean_row(
            {"item_id": "fp_1", "source_dataset": "Fashionpedia", "category_ids": "999"},
            {"0": "shirt"},
        )


def test_other_source_labels_are_preserved() -> None:
    row = {"item_id": "pv_1", "source_dataset": "Polyvore Outfits", "category_labels": "tops"}
    assert clean_row(row, {})["category_labels"] == "tops"


@pytest.mark.parametrize(
    "rows,code",
    [
        ([], 2),
        ([{"valid": "true"}], 0),
        ([{"valid": "false"}], 1),
        ([{"valid": "true"}, {"valid": "false"}], 1),
    ],
)
def test_invalid_or_empty_images_fail_the_gate(rows: list[dict[str, str]], code: int) -> None:
    assert validation_status(rows) == code


def test_reference_duplicates_are_grouped_but_missing_ids_are_not() -> None:
    base = {
        "source_dataset": "example",
        "source_split": "train",
        "source_index": "",
        "source_image_id": "",
        "original_image_reference": "same.jpg",
    }
    rows = [dict(base, item_id="a"), dict(base, item_id="b")]
    result = duplicate_members(rows)
    assert len(result) == 2
    assert {row["item_id"] for row in result} == {"a", "b"}
    assert all(row["duplicate_type"] == "original_reference" for row in result)


def test_empty_directory_cli_returns_clear_failure_without_writing() -> None:
    with (
        patch("sys.argv", ["validate_m1_images.py"]),
        patch.object(validate_m1_images, "sample_paths", return_value=[]),
    ):
        assert validate_m1_images.main() == 2


def test_different_source_splits_do_not_hide_identical_references() -> None:
    base = {
        "source_dataset": "example",
        "source_image_id": "1",
        "source_index": "1",
        "original_image_reference": "same.jpg",
    }
    rows = [
        dict(base, item_id="a", source_split="train"),
        dict(base, item_id="b", source_split="test"),
    ]
    result = duplicate_members(rows)
    assert len(result) == 2
    assert all(row["duplicate_type"] == "original_reference" for row in result)


def test_exact_duplicates_include_rows_with_missing_optional_fields() -> None:
    row = {"item_id": "a", "source_dataset": "example", "source_image_id": ""}
    result = duplicate_members([row, dict(row)])
    assert len([r for r in result if r["duplicate_type"] == "exact_manifest_row"]) == 2
