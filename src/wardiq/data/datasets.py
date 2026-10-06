from __future__ import annotations

import ast
import importlib
import math
from pathlib import Path
from typing import Any

from .preprocessing import build_transforms

M1_M2_FIELDS = (
    "item_id",
    "source_dataset",
    "image_path",
    "category_label",
    "available_attributes",
    "bounding_box",
    "segmentation_mask",
    "split",
)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(math.isnan(value))
    except (TypeError, ValueError):
        return False


def _parse_list(value: Any) -> list[Any]:
    if _is_missing(value) or value == "":
        return []
    if isinstance(value, (list, tuple)):
        return list(value)

    text = str(value).strip()
    if text.startswith("["):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple)):
                return list(parsed)
        except (ValueError, SyntaxError, TypeError):
            # Some manifest cells are plain strings, so fall back to semicolons.
            return [item for item in text.split(";") if item]

    return [item for item in text.split(";") if item]


def _parse_bbox(value: Any) -> list[float] | None:
    if _is_missing(value) or value == "":
        return None

    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, (list, tuple)) and len(parsed) == 4:
            return [float(item) for item in parsed]
    except (ValueError, SyntaxError, TypeError):
        # Fashionpedia bboxes can arrive as malformed strings; leave them unavailable.
        return None

    return None


def _row_value(row: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(row, name)
    except AttributeError:
        try:
            return row[name]
        except (KeyError, TypeError):
            return default


class WardiqImageDataset:
    """Image-level loader. Keeps the M1→M2 fields present even when data is missing."""

    def __init__(self, manifest: Any, split: str, transform: Any = None, strict_paths: bool = True):

        self.df = manifest[manifest.target_split.eq(split)].reset_index(drop=True).copy()
        self.transform = transform or build_transforms(train=(split == "train"))
        self.strict_paths = strict_paths

        if self.df.empty:
            raise ValueError(f"No records for split={split}")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        Image = importlib.import_module("PIL.Image")

        row = self.df.iloc[idx]
        path = Path(str(_row_value(row, "image_path")))

        if not path.exists():
            if self.strict_paths:
                raise FileNotFoundError(f"Image not found for {_row_value(row, 'item_id')}: {path}")
            raise FileNotFoundError(str(path))

        with Image.open(path) as image_file:
            image = image_file.convert("RGB")

        image = self.transform(image) if self.transform else image

        source_ids = [int(value) for value in _parse_list(_row_value(row, "category_ids"))]
        category_labels = _parse_list(_row_value(row, "category_labels"))
        attributes = _parse_list(_row_value(row, "attribute_ids"))
        common_categories = _parse_list(_row_value(row, "common_categories"))

        return {
            "image": image,
            "item_id": str(_row_value(row, "item_id")),
            "source_dataset": str(_row_value(row, "source_dataset")),
            "image_path": str(path),
            "category_label": category_labels[0] if category_labels else None,
            "available_attributes": attributes or None,
            "bounding_box": None,
            "segmentation_mask": None,
            "split": str(_row_value(row, "target_split")),
            "source_category_ids": source_ids,
            "source_category_labels": category_labels,
            "common_categories": common_categories,
            "direct_common_categories": _parse_list(_row_value(row, "direct_common_categories")),
            "attribute_ids": attributes,
            "group_id": (
                None
                if _is_missing(_row_value(row, "group_id"))
                else str(_row_value(row, "group_id"))
            ),
        }


class WardiqGarmentDataset:
    """Garment-level loader built from Hana's annotation manifest."""

    def __init__(self, garment_manifest: Any, split: str, transform: Any = None):
        df = garment_manifest[
            garment_manifest.target_split.eq(split) & garment_manifest.usable_derivative.eq(True)
        ].copy()
        self.df = df.reset_index(drop=True)
        self.transform = transform or build_transforms(train=(split == "train"))

        if self.df.empty:
            raise ValueError(f"No usable garment derivatives for split={split}")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        Image = importlib.import_module("PIL.Image")

        row = self.df.iloc[idx]
        path = Path(str(_row_value(row, "image_path")))

        if not path.exists():
            raise FileNotFoundError(
                f"Garment derivative not found for {_row_value(row, 'item_id')}: {path}"
            )

        with Image.open(path) as image_file:
            image = image_file.convert("RGB")

        image = self.transform(image) if self.transform else image

        bbox = _parse_bbox(_row_value(row, "processed_bbox_xywh"))
        bbox_format = "xywh" if bbox is not None else None
        if bbox is None:
            bbox = _parse_bbox(_row_value(row, "source_bbox_xywh"))
            bbox_format = "xywh" if bbox is not None else None

        category_label = _row_value(row, "category_label")
        category_label = None if _is_missing(category_label) else str(category_label)
        common_category = _row_value(row, "common_category")
        common_category = None if _is_missing(common_category) else str(common_category)

        category_id = _row_value(row, "category_id")
        return {
            "image": image,
            "item_id": str(_row_value(row, "item_id")),
            "source_dataset": str(_row_value(row, "source_dataset")),
            "image_path": str(path),
            "category_label": category_label,
            "available_attributes": None,
            "bounding_box": bbox,
            "segmentation_mask": None,
            "split": str(_row_value(row, "target_split")),
            "source_category_id": None if _is_missing(category_id) else int(category_id),
            "source_category_label": category_label,
            "common_category": common_category,
            "category_mapping_status": _row_value(row, "category_mapping_status"),
            "crop_method": _row_value(row, "crop_method"),
            "fallback_used": bool(_row_value(row, "fallback_used", False)),
            "bounding_box_format": bbox_format,
            "group_id": (
                None
                if _is_missing(_row_value(row, "group_id"))
                else str(_row_value(row, "group_id"))
            ),
            "source_image_id": (
                None
                if _is_missing(_row_value(row, "source_image_id"))
                else str(_row_value(row, "source_image_id"))
            ),
        }


def load_manifest(path: str | Path) -> Any:
    """Load an integrated image-level manifest without changing its source data."""
    pandas = importlib.import_module("pandas")

    return pandas.read_csv(path, low_memory=False)


def load_garment_manifest(path: str | Path) -> Any:
    """Load Hana's garment manifest without changing its source data."""
    pandas = importlib.import_module("pandas")

    return pandas.read_csv(path, low_memory=False)
