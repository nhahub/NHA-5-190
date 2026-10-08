from __future__ import annotations

import importlib
import math
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "configs/m1/preprocessing.yaml"


def load_preprocessing_config(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """Load the M1 preprocessing configuration."""
    with Path(config_path).open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError(f"Invalid preprocessing config: {config_path}")

    return config


def build_transforms(
    train: bool = False,
    config: dict[str, Any] | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    include_random_flip: bool = True,
) -> tuple[Any, dict[str, Any]]:
    """Build image transforms from the M1 preprocessing configuration."""
    if config is None:
        config = load_preprocessing_config(config_path)

    size = config.get("image_size", [224, 224])
    if (
        not isinstance(size, (list, tuple))
        or len(size) != 2
        or any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in size)
    ):
        raise ValueError("image_size must be [height, width] with positive integers")
    if str(config.get("color_mode", "RGB")).upper() != "RGB":
        raise ValueError("M1 preprocessing requires RGB images")
    normalization = config.get("normalization", {})
    mean, std = normalization.get("mean", []), normalization.get("std", [])
    if (
        len(mean) != 3
        or len(std) != 3
        or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in [*mean, *std])
        or any(v <= 0 for v in std)
    ):
        raise ValueError("RGB normalization requires three finite means and positive std values")
    probability = config.get("train", {}).get("horizontal_flip_probability", 0.5)
    if not isinstance(probability, (int, float)) or not 0 <= probability <= 1:
        raise ValueError("horizontal_flip_probability must be between 0 and 1")
    transforms = importlib.import_module("torchvision.transforms")
    interpolation_modes = transforms.InterpolationMode

    image_size = tuple(config.get("image_size", [224, 224]))

    interpolation_name = str(config.get("interpolation", "bilinear")).upper()

    interpolation = getattr(
        interpolation_modes,
        interpolation_name,
    )

    color_mode = str(config.get("color_mode", "RGB")).upper()

    operations = [
        transforms.Resize(
            image_size,
            interpolation=interpolation,
        ),
    ]

    train_config = config.get("train", {})

    horizontal_flip = train and train_config.get(
        "random_horizontal_flip",
        False,
    )

    horizontal_flip_probability = (
        float(
            train_config.get(
                "horizontal_flip_probability",
                0.5,
            )
        )
        if horizontal_flip
        else 0.0
    )

    if horizontal_flip and include_random_flip:
        operations.append(
            transforms.RandomHorizontalFlip(
                p=horizontal_flip_probability,
            )
        )

    operations.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(
                config["normalization"]["mean"],
                config["normalization"]["std"],
            ),
        ]
    )

    return transforms.Compose(operations), {
        "image_size": image_size,
        "interpolation": interpolation_name,
        "color_mode": color_mode,
        "horizontal_flip": horizontal_flip,
        "horizontal_flip_probability": horizontal_flip_probability,
    }
