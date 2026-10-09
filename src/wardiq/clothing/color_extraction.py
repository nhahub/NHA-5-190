"""Deterministic sRGB -> CIE LAB (D65/2-degree) garment color extraction."""

from __future__ import annotations

import importlib
import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

EXTRACTOR_VERSION = "wardiq.color.v1"
LAB_CONVENTION = "CIE_Lab_D65_2deg"
# sRGB linear-light -> XYZ D65 matrix, W3C CSS Color 4 sample conversions.
RGB_TO_XYZ = np.array(
    [
        [506752 / 1228815, 87881 / 245763, 12673 / 70218],
        [87098 / 409605, 175762 / 245763, 12673 / 175545],
        [7918 / 409605, 87881 / 737289, 1001167 / 1053270],
    ],
    dtype=np.float64,
)
WHITE = RGB_TO_XYZ.sum(axis=1)
EPSILON, KAPPA = 216 / 24389, 24389 / 27


@dataclass(frozen=True)
class ColorConfig:
    """Version all settings that can change a palette or its coverage."""

    k: int = 5
    seed: int = 42
    max_pixels: int = 20000
    n_init: int = 10
    max_iter: int = 300
    prediction_batch_size: int = 16384
    alpha_threshold: int = 1
    allow_full_image_fallback: bool = True

    def __post_init__(self) -> None:
        for name in ("k", "max_pixels", "n_init", "max_iter", "prediction_batch_size"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            not isinstance(self.seed, int)
            or isinstance(self.seed, bool)
            or not 0 <= self.seed < 2**32
        ):
            raise ValueError("seed must be an integer in [0, 2**32)")
        if (
            not isinstance(self.alpha_threshold, int)
            or isinstance(self.alpha_threshold, bool)
            or not 1 <= self.alpha_threshold <= 255
        ):
            raise ValueError("alpha_threshold must be an integer in [1, 255]")
        if not isinstance(self.allow_full_image_fallback, bool):
            raise ValueError("allow_full_image_fallback must be boolean")


def rgb_to_lab(rgb: NDArray[Any]) -> NDArray[np.float64]:
    """Convert unnormalized uint8 sRGB (...,3) to physical CIE LAB, D65 white."""
    if rgb.dtype != np.uint8 or rgb.ndim < 1 or rgb.shape[-1] != 3:
        raise ValueError("Expected unnormalized uint8 RGB pixels with last dimension 3")
    values = rgb.astype(np.float64) / 255
    linear = np.where(values <= 0.04045, values / 12.92, ((values + 0.055) / 1.055) ** 2.4)
    xyz = (linear @ RGB_TO_XYZ.T) / WHITE
    f = np.where(xyz > EPSILON, np.cbrt(xyz), (KAPPA * xyz + 16) / 116)
    return np.asarray(
        np.stack(
            (116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])),
            axis=-1,
        ),
        dtype=np.float64,
    )


def lab_to_rgb(lab: NDArray[Any]) -> NDArray[np.uint8]:
    """Inverse conversion for review swatches only; clip display RGB to its gamut."""
    values = np.asarray(lab, dtype=np.float64)
    if values.shape[-1] != 3 or not np.isfinite(values).all():
        raise ValueError("Expected finite LAB triples")
    fy = (values[..., 0] + 16) / 116
    f = np.stack((fy + values[..., 1] / 500, fy, fy - values[..., 2] / 200), axis=-1)
    xyz = np.where(f**3 > EPSILON, f**3, (116 * f - 16) / KAPPA) * WHITE
    linear = xyz @ np.linalg.inv(RGB_TO_XYZ).T
    clipped = np.clip(linear, 0, 1)
    rgb = np.where(clipped <= 0.0031308, clipped * 12.92, 1.055 * clipped ** (1 / 2.4) - 0.055)
    return np.asarray(np.rint(rgb * 255), dtype=np.uint8)


def validate_palette(palette: list[dict[str, float]]) -> None:
    """Validate Hanaa's initial interface; use a stricter sum tolerance of 1e-6."""
    if not palette:
        raise ValueError("A successful palette must contain at least one color")
    for color in palette:
        if set(color) != {"L", "a", "b", "proportion"} or not all(
            math.isfinite(v) for v in color.values()
        ):
            raise ValueError("Palette entries require finite L, a, b, proportion")
        if not (
            0 <= color["L"] <= 100
            and -128 <= color["a"] <= 127
            and -128 <= color["b"] <= 127
            and 0 <= color["proportion"] <= 1
        ):
            raise ValueError("Palette value outside the published interface range")
    if not math.isclose(sum(c["proportion"] for c in palette), 1, abs_tol=1e-6):
        raise ValueError("Palette proportions must sum to one")


def extract_palette(
    rgb: NDArray[Any],
    config: ColorConfig | None = None,
    *,
    mask: NDArray[Any] | None = None,
    bbox_xywh: list[float] | None = None,
    region_method: str = "full_image",
    fallback_used: bool = False,
) -> dict[str, Any]:
    """Return palette/provenance or an explicit failure. Mask > bbox > full image.

    Input is an HxWx3/4 uint8 sRGB array, never model-normalized tensors. Nonzero
    mask pixels select the garment; alpha-zero pixels never contribute. Geometry
    must be in this image's coordinate space. Already prepared crops need no bbox.
    """
    cfg = config or ColorConfig()
    result: dict[str, Any] = {
        "extractor_version": EXTRACTOR_VERSION,
        "lab_convention": LAB_CONVENTION,
        "configuration": asdict(cfg),
        "status": "failed",
        "palette": None,
        "failure_reason": None,
        "region_method": region_method,
        "fallback_used": bool(fallback_used) or region_method == "full_image_fallback",
        "warnings": [],
        "background_contamination_possible": True,
        "usable_pixels": 0,
        "sampled_pixels": 0,
        "effective_k": 0,
    }
    if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[-1] not in (3, 4):
        result["failure_reason"] = "expected_unnormalized_uint8_RGB_or_RGBA"
        return result
    if region_method not in {
        "full_image",
        "full_image_fallback",
        "bbox_crop",
        "source_product_photo",
    }:
        result["failure_reason"] = "unsupported_input_region_method"
        return result
    height, width = rgb.shape[:2]
    selected = np.ones((height, width), dtype=bool)
    if rgb.shape[-1] == 4:
        selected &= rgb[..., 3] >= cfg.alpha_threshold
    geometry_used = False
    if mask is not None:
        numeric_mask = np.issubdtype(mask.dtype, np.number) or mask.dtype == np.bool_
        if (
            numeric_mask
            and mask.shape == (height, width)
            and np.isfinite(mask).all()
            and np.any(mask > 0)
        ):
            selected &= mask > 0
            result["region_method"] = "mask"
            result["background_contamination_possible"] = False
            geometry_used = True
        else:
            result["warnings"].append("invalid_or_empty_mask")
            result["fallback_used"] = True
    if not geometry_used and bbox_xywh is not None:
        valid = (
            len(bbox_xywh) == 4
            and all(math.isfinite(v) for v in bbox_xywh)
            and bbox_xywh[2] > 0
            and bbox_xywh[3] > 0
        )
        if valid:
            x, y, w, h = bbox_xywh
            left, top = max(0, math.floor(x)), max(0, math.floor(y))
            right, bottom = math.ceil(min(width, x + w)), math.ceil(min(height, y + h))
            valid = right > left and bottom > top
        if valid:
            box_mask = np.zeros((height, width), dtype=bool)
            box_mask[top:bottom, left:right] = True
            selected &= box_mask
            result["region_method"] = "bbox_crop"
            geometry_used = True
        else:
            result["warnings"].append("invalid_bbox")
            result["fallback_used"] = True
    if not geometry_used and (mask is not None or bbox_xywh is not None):
        if not cfg.allow_full_image_fallback:
            result["failure_reason"] = "invalid_region_geometry"
            return result
        result["region_method"] = "full_image_fallback"
    if result["region_method"] == "full_image":
        result["region_method"] = "full_image_fallback"
        result["fallback_used"] = True
    if result["region_method"] == "full_image_fallback" and not cfg.allow_full_image_fallback:
        result["failure_reason"] = "full_image_fallback_disabled"
        return result
    pixels = rgb[..., :3][selected]
    total = len(pixels)
    result["usable_pixels"] = total
    if not total:
        result["failure_reason"] = "empty_or_fully_transparent_region"
        return result
    if total > cfg.max_pixels:
        indices = np.random.default_rng(cfg.seed).choice(total, cfg.max_pixels, replace=False)
        sampled = pixels[np.sort(indices)]
    else:
        sampled = pixels
    result["sampled_pixels"] = len(sampled)
    unique, weights = np.unique(sampled, axis=0, return_counts=True)
    k = min(cfg.k, len(unique))
    if k < cfg.k:
        result["warnings"].append("cluster_count_reduced_for_available_colors")
    KMeans = importlib.import_module("sklearn.cluster").KMeans
    threadpool_limits = importlib.import_module("threadpoolctl").threadpool_limits
    with threadpool_limits(limits=1):
        model = KMeans(
            n_clusters=k,
            random_state=cfg.seed,
            n_init=cfg.n_init,
            max_iter=cfg.max_iter,
            algorithm="lloyd",
        )
        model.fit(rgb_to_lab(unique), sample_weight=weights)
        counts = np.zeros(k, dtype=np.int64)
        for start in range(0, total, cfg.prediction_batch_size):
            labels = model.predict(rgb_to_lab(pixels[start : start + cfg.prediction_batch_size]))
            counts += np.bincount(labels, minlength=k)
    colors = []
    for center, count in zip(model.cluster_centers_, counts):
        if count:
            # Correct insignificant floating-point boundary noise, never rescale LAB channels.
            colors.append(
                {
                    "L": float(np.clip(center[0], 0, 100)),
                    "a": float(center[1]),
                    "b": float(center[2]),
                    "proportion": int(count) / total,
                }
            )
    colors.sort(key=lambda c: (-c["proportion"], c["L"], c["a"], c["b"]))
    validate_palette(colors)
    result.update(status="ok", palette=colors, effective_k=len(colors))
    return result
