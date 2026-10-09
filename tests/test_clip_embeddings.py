"""Tests for CLIP embedding validation and manifest loading."""

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from wardiq.representation.clip_embeddings import (
    ClipEmbeddingMetadata,
    load_usable_manifest,
    normalize_embeddings,
    validate_embedding_artifact,
)


def test_normalize_embeddings_returns_unit_float32_vectors():
    values = np.array([[3.0, 4.0], [5.0, 12.0]], dtype=np.float64)

    result = normalize_embeddings(values, expected_dimension=2)

    assert result.dtype == np.float32
    np.testing.assert_allclose(np.linalg.norm(result, axis=1), [1.0, 1.0])


def test_normalize_embeddings_rejects_invalid_values():
    with pytest.raises(ValueError, match="two-dimensional"):
        normalize_embeddings(np.array([1.0, 2.0]), expected_dimension=2)

    with pytest.raises(ValueError, match="finite"):
        normalize_embeddings(np.array([[np.nan, 1.0]]), expected_dimension=2)

    with pytest.raises(ValueError, match="nonzero"):
        normalize_embeddings(np.array([[0.0, 0.0]]), expected_dimension=2)


def test_normalize_embeddings_rejects_wrong_dimension():
    with pytest.raises(ValueError, match="dimension"):
        normalize_embeddings(np.ones((2, 3)), expected_dimension=2)


def test_validate_artifact_checks_shape_dtype_and_norms():
    metadata = ClipEmbeddingMetadata(embedding_dimension=2)
    valid = np.array([[0.6, 0.8]], dtype=np.float32)

    validate_embedding_artifact(valid, metadata, item_count=1)

    with pytest.raises(ValueError, match="shape"):
        validate_embedding_artifact(valid, metadata, item_count=2)

    with pytest.raises(ValueError, match="normalized"):
        validate_embedding_artifact(
            np.array([[3.0, 4.0]], dtype=np.float32), metadata, item_count=1
        )


def test_load_usable_manifest_filters_and_resolves_paths(tmp_path):
    image_path = tmp_path / "image.jpg"
    Image.new("RGB", (8, 8), color="red").save(image_path)

    manifest_path = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {
                "item_id": "usable-1",
                "source_dataset": "test",
                "image_path": "image.jpg",
                "target_split": "validation",
                "usable_derivative": True,
            },
            {
                "item_id": "unusable-1",
                "source_dataset": "test",
                "image_path": "missing.jpg",
                "target_split": "validation",
                "usable_derivative": False,
            },
        ]
    ).to_csv(manifest_path, index=False)

    result = load_usable_manifest(manifest_path, image_root=tmp_path)

    assert len(result) == 1
    assert result.loc[0, "item_id"] == "usable-1"
    assert result.loc[0, "resolved_image_path"] == str(image_path.resolve())


def test_load_usable_manifest_rejects_missing_image(tmp_path):
    manifest_path = tmp_path / "manifest.csv"
    pd.DataFrame(
        [
            {
                "item_id": "usable-1",
                "source_dataset": "test",
                "image_path": "missing.jpg",
                "target_split": "validation",
                "usable_derivative": True,
            }
        ]
    ).to_csv(manifest_path, index=False)

    with pytest.raises(FileNotFoundError, match="usable image"):
        load_usable_manifest(manifest_path, image_root=tmp_path)
