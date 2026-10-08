from __future__ import annotations

import ast
import importlib
import math
import random
from pathlib import Path
from typing import Any

from .preprocessing import DEFAULT_CONFIG_PATH, build_transforms

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

TRACEABILITY_FIELDS = (
    "source_release",
    "source_split",
    "source_index",
    "source_image_id",
    "original_filename",
    "original_image_reference",
    "annotation_reference",
    "annotation_ids",
    "outfit_ids",
    "traceability_status",
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


def _parse_bool(value: Any) -> bool:
    if _is_missing(value):
        return False
    if isinstance(value, str):
        if value.strip().lower() in {"true", "1"}:
            return True
        if value.strip().lower() in {"false", "0", ""}:
            return False
        raise ValueError(f"Invalid boolean: {value!r}")
    return bool(value)


def _parse_bbox(value: Any) -> list[float] | None:
    if _is_missing(value) or value == "":
        return None

    try:
        parsed = ast.literal_eval(str(value))
        if isinstance(parsed, (list, tuple)) and len(parsed) == 4:
            box = [float(item) for item in parsed]
            return box if all(math.isfinite(x) for x in box) and box[2] > 0 and box[3] > 0 else None
    except (ValueError, SyntaxError, TypeError):
        # Leave malformed annotations unavailable rather than inventing coordinates.
        return None

    return None


def _transform_bbox(
    bbox: list[float] | None,
    original_size: tuple[int, int],
    target_size: tuple[int, int],
    flipped: bool,
) -> list[float] | None:
    """Transform an XYWH bbox to match the processed image."""
    if bbox is None:
        return None

    original_width, original_height = original_size
    target_width, target_height = target_size

    if original_width <= 0 or original_height <= 0:
        raise ValueError("Image dimensions must be positive.")

    x, y, width, height = bbox

    scale_x = target_width / original_width
    scale_y = target_height / original_height

    x *= scale_x
    y *= scale_y
    width *= scale_x
    height *= scale_y

    if flipped:
        x = target_width - x - width

    return [
        round(x, 6),
        round(y, 6),
        round(width, 6),
        round(height, 6),
    ]


def _row_value(row: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(row, name)
    except AttributeError:
        try:
            return row[name]
        except (KeyError, TypeError):
            return default


def _resolve_image_path(
    image_path: Any,
    image_root: str | Path | None,
) -> Path:
    """Resolve an image path against an optional explicit image root."""
    path = Path(str(image_path))

    if path.is_absolute() or image_root is None:
        return path

    return Path(image_root) / path


def _traceability_fields(row: Any) -> dict[str, Any]:
    """Keep source traceability fields without changing their manifest names."""
    return {field: _row_value(row, field) for field in TRACEABILITY_FIELDS}


class WardiqImageDataset:
    """Image-level loader for the M1→M2 data contract."""

    def __init__(
        self,
        manifest: Any,
        split: str,
        transform: Any = None,
        strict_paths: bool = True,
        image_root: str | Path | None = None,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
    ):
        self.df = manifest[manifest.target_split.eq(split)].reset_index(drop=True).copy()

        self.transform_config: dict[str, Any] | None = None

        if transform is None:
            self.transform, self.transform_config = build_transforms(
                train=(split == "train"),
                config_path=config_path,
            )
        else:
            self.transform = transform

        self.strict_paths = strict_paths
        self.image_root = Path(image_root) if image_root is not None else None

        if self.df.empty:
            raise ValueError(f"No records for split={split}")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        Image = importlib.import_module("PIL.Image")

        row = self.df.iloc[idx]
        path = _resolve_image_path(
            _row_value(row, "image_path"),
            self.image_root,
        )

        if not path.exists():
            if self.strict_paths:
                raise FileNotFoundError(f"Image not found for {_row_value(row, 'item_id')}: {path}")
            raise FileNotFoundError(str(path))

        with Image.open(path) as image_file:
            color_mode = "RGB"

            if self.transform_config is not None:
                color_mode = self.transform_config["color_mode"]

            image = image_file.convert(color_mode)

        image = self.transform(image) if self.transform else image

        source_ids = [int(value) for value in _parse_list(_row_value(row, "category_ids"))]
        category_labels = _parse_list(_row_value(row, "category_labels"))
        attributes = _parse_list(_row_value(row, "attribute_ids"))
        common_categories = _parse_list(_row_value(row, "common_categories"))

        sample = {
            "image": image,
            "item_id": str(_row_value(row, "item_id")),
            "source_dataset": str(_row_value(row, "source_dataset")),
            "image_path": str(path),
            "category_label": (category_labels[0] if category_labels else None),
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

        sample.update(_traceability_fields(row))
        return sample


class WardiqGarmentDataset:
    """Garment-level loader built from Hana's annotation manifest."""

    def __init__(
        self,
        garment_manifest: Any,
        split: str,
        transform: Any = None,
        image_root: str | Path | None = None,
        config_path: str | Path = DEFAULT_CONFIG_PATH,
    ):
        df = garment_manifest[
            garment_manifest.target_split.eq(split)
            & garment_manifest.usable_derivative.map(_parse_bool)
        ].copy()

        self.df = df.reset_index(drop=True)

        self.transform_config: dict[str, Any] | None = None

        if transform is None:
            self.transform, self.transform_config = build_transforms(
                train=(split == "train"),
                config_path=config_path,
                include_random_flip=False,
            )
        else:
            self.transform = transform

        self.image_root = Path(image_root) if image_root is not None else None

        if self.df.empty:
            raise ValueError(f"No usable garment derivatives for split={split}")

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        Image = importlib.import_module("PIL.Image")

        row = self.df.iloc[idx]
        path = _resolve_image_path(
            _row_value(row, "image_path"),
            self.image_root,
        )

        if not path.exists():
            raise FileNotFoundError(
                f"Garment derivative not found for {_row_value(row, 'item_id')}: {path}"
            )

        with Image.open(path) as image_file:
            color_mode = "RGB"

            if self.transform_config is not None:
                color_mode = self.transform_config["color_mode"]

            image = image_file.convert(color_mode)

        original_width, original_height = image.size

        crop_method = _row_value(row, "crop_method")

        bbox = None

        if crop_method == "bbox_crop":
            # Hana's derivative is already cropped to the garment.
            bbox = [
                0.0,
                0.0,
                float(original_width),
                float(original_height),
            ]
        else:
            bbox = _parse_bbox(_row_value(row, "processed_bbox_xywh"))

            if bbox is None:
                bbox = _parse_bbox(_row_value(row, "source_bbox_xywh"))

        flipped = False

        if self.transform_config is not None:
            target_height, target_width = self.transform_config["image_size"]

            if self.transform_config["horizontal_flip"]:
                probability = self.transform_config["horizontal_flip_probability"]
                flipped = random.random() < probability

                if flipped:
                    image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)

            bbox = _transform_bbox(
                bbox,
                original_size=(original_width, original_height),
                target_size=(target_width, target_height),
                flipped=flipped,
            )

        image = self.transform(image) if self.transform else image

        category_label = _row_value(row, "category_label")
        category_label = None if _is_missing(category_label) else str(category_label)

        common_category = _row_value(row, "common_category")
        common_category = None if _is_missing(common_category) else str(common_category)

        category_id = _row_value(row, "category_id")

        sample = {
            "image": image,
            "item_id": str(_row_value(row, "item_id")),
            "source_dataset": str(_row_value(row, "source_dataset")),
            "image_path": str(path),
            "category_label": category_label,
            "available_attributes": _parse_list(_row_value(row, "attribute_ids")) or None,
            "bounding_box": bbox,
            "segmentation_mask": None,
            "split": str(_row_value(row, "target_split")),
            "source_category_id": (None if _is_missing(category_id) else int(category_id)),
            "source_category_label": category_label,
            "common_category": common_category,
            "category_mapping_status": _row_value(
                row,
                "category_mapping_status",
            ),
            "crop_method": crop_method,
            "fallback_used": _parse_bool(_row_value(row, "fallback_used", False)),
            "bounding_box_format": ("xywh" if bbox is not None else None),
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

        sample.update(_traceability_fields(row))
        return sample


def load_manifest(path: str | Path) -> Any:
    """Load an integrated image-level manifest."""
    pandas = importlib.import_module("pandas")
    return pandas.read_csv(path, low_memory=False)


def load_garment_manifest(path: str | Path) -> Any:
    """Load Hana's garment manifest."""
    pandas = importlib.import_module("pandas")
    return pandas.read_csv(path, low_memory=False)
