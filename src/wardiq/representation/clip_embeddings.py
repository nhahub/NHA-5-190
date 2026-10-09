"""CLIP image embedding extraction and artifact validation for WARDIQ."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

CLIP_MODEL_ID = "openai/clip-vit-base-patch32"
CLIP_MODEL_REVISION: str | None = None
CLIP_EMBEDDING_VERSION = "wardiq.clip_embedding.v1"
EXPECTED_EMBEDDING_DIMENSION = 512

REQUIRED_MANIFEST_COLUMNS = (
    "item_id",
    "source_dataset",
    "image_path",
    "target_split",
    "usable_derivative",
)


@dataclass(frozen=True)
class ClipEmbeddingMetadata:
    """Describe the CLIP embedding representation."""

    model_id: str = CLIP_MODEL_ID
    embedding_version: str = CLIP_EMBEDDING_VERSION
    embedding_dimension: int = EXPECTED_EMBEDDING_DIMENSION
    dtype: str = "float32"
    normalized: bool = True
    image_size: int = 224
    device: str = "cpu"


def load_usable_manifest(
    manifest_path: str | Path,
    image_root: str | Path | None = None,
) -> pd.DataFrame:
    """Load usable manifest rows and validate their image paths."""
    manifest_path = Path(manifest_path)

    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest file does not exist: {manifest_path}")

    manifest = pd.read_csv(manifest_path)

    missing_columns = [
        column for column in REQUIRED_MANIFEST_COLUMNS if column not in manifest.columns
    ]
    if missing_columns:
        raise ValueError(f"Manifest is missing required columns: {missing_columns}")

    usable = manifest[
        manifest["usable_derivative"].astype(str).str.strip().str.lower().eq("true")
    ].copy()

    if usable.empty:
        raise ValueError("Manifest contains no usable image derivatives.")

    if usable["item_id"].isna().any():
        raise ValueError("Usable manifest rows contain missing item IDs.")

    if usable["item_id"].duplicated().any():
        duplicates = usable.loc[usable["item_id"].duplicated(keep=False), "item_id"].tolist()
        raise ValueError(f"Duplicate item IDs found: {duplicates}")

    if usable["image_path"].isna().any():
        raise ValueError("Usable manifest rows contain missing image paths.")

    root = Path(image_root) if image_root is not None else Path.cwd()
    resolved_paths: list[str] = []

    for raw_path in usable["image_path"]:
        path = Path(str(raw_path))

        if not path.is_absolute():
            path = root / path

        path = path.resolve()

        if not path.is_file():
            raise FileNotFoundError(f"Referenced usable image does not exist: {path}")

        resolved_paths.append(str(path))

    usable["resolved_image_path"] = resolved_paths
    usable.reset_index(drop=True, inplace=True)

    return usable


def normalize_embeddings(
    embeddings: NDArray[Any],
    expected_dimension: int = EXPECTED_EMBEDDING_DIMENSION,
) -> NDArray[np.float32]:
    """Validate embeddings and return L2-normalized float32 vectors."""
    values = np.asarray(embeddings)

    if values.ndim != 2:
        raise ValueError(f"Embeddings must be two-dimensional; received shape {values.shape}.")

    if values.shape[1] != expected_dimension:
        raise ValueError(
            f"Expected embedding dimension {expected_dimension}; received {values.shape[1]}."
        )

    if values.shape[0] == 0:
        raise ValueError("Cannot normalize an empty embedding array.")

    if not np.isfinite(values).all():
        raise ValueError("Embeddings must contain only finite values.")

    values = values.astype(np.float32, copy=False)
    norms = np.linalg.norm(values, axis=1, keepdims=True)

    if np.any(norms <= 0):
        raise ValueError(
            "Embeddings must have nonzero norms; zero-length vectors cannot be normalized."
        )

    normalized = values / norms
    return normalized.astype(np.float32, copy=False)


def validate_embedding_artifact(
    embeddings: NDArray[Any],
    metadata: ClipEmbeddingMetadata,
    item_count: int,
) -> None:
    """Validate embedding shape, dtype, finite values, and vector norms."""
    values = np.asarray(embeddings)
    expected_shape = (item_count, metadata.embedding_dimension)

    if values.shape != expected_shape:
        raise ValueError(f"Expected embedding shape {expected_shape}; received {values.shape}.")

    if values.dtype != np.float32:
        raise ValueError(f"Expected float32 embeddings; received {values.dtype}.")

    if not np.isfinite(values).all():
        raise ValueError("Embedding artifact contains non-finite values.")

    if metadata.normalized:
        norms = np.linalg.norm(values, axis=1)

        if not np.allclose(norms, 1.0, atol=1e-4):
            raise ValueError("Expected all normalized embedding vectors to have unit norm.")


def extract_clip_embeddings(
    manifest_path: str | Path,
    output_dir: str | Path,
    image_root: str | Path | None = None,
    batch_size: int = 8,
) -> dict[str, Any]:
    """Extract CLIP image embeddings and save a prototype artifact."""
    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPProcessor

    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise ValueError("batch_size must be a positive integer.")

    manifest = load_usable_manifest(
        manifest_path=manifest_path,
        image_root=image_root,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"

    load_options: dict[str, Any] = {}
    if CLIP_MODEL_REVISION is not None:
        load_options["revision"] = CLIP_MODEL_REVISION

    processor = CLIPProcessor.from_pretrained(
        CLIP_MODEL_ID,
        **load_options,
    )
    model = CLIPModel.from_pretrained(
        CLIP_MODEL_ID,
        **load_options,
    ).to(device)

    model.eval()

    batches: list[NDArray[np.float32]] = []
    image_paths = manifest["resolved_image_path"].tolist()

    for start in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[start : start + batch_size]
        images = []

        for image_path in batch_paths:
            with Image.open(image_path) as image:
                images.append(image.convert("RGB"))

        inputs = processor(
            images=images,
            return_tensors="pt",
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}

        with torch.inference_mode():
            outputs = model.get_image_features(**inputs)

        if outputs is None:
            raise RuntimeError("CLIP returned no image features.")

        # Support output structures used by different Transformers versions.
        if hasattr(outputs, "image_embeds"):
            outputs = outputs.image_embeds
        elif hasattr(outputs, "pooler_output"):
            outputs = outputs.pooler_output

        if outputs is None or not isinstance(outputs, torch.Tensor):
            raise RuntimeError("CLIP did not return image features as a tensor.")

        batches.append(outputs.detach().cpu().numpy().astype(np.float32))

    raw_embeddings = np.concatenate(batches, axis=0)
    embeddings = normalize_embeddings(raw_embeddings)

    metadata = ClipEmbeddingMetadata(device=device)

    validate_embedding_artifact(
        embeddings=embeddings,
        metadata=metadata,
        item_count=len(manifest),
    )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    embedding_path = output_dir / "clip_embeddings.npy"
    inventory_path = output_dir / "clip_inventory.csv"
    metadata_path = output_dir / "metadata.json"

    inventory = manifest.copy()
    inventory.insert(
        0,
        "embedding_row",
        np.arange(len(inventory), dtype=np.int64),
    )

    image_processor = getattr(processor, "image_processor", None)
    processor_size = getattr(image_processor, "size", None)

    metadata_record = asdict(metadata)
    metadata_record.update(
        {
            "model_revision": (CLIP_MODEL_REVISION or getattr(model.config, "_commit_hash", None)),
            "processor_size": processor_size,
            "item_count": len(manifest),
            "source_manifest": str(Path(manifest_path)),
            "embedding_file": embedding_path.name,
            "inventory_file": inventory_path.name,
            "prototype_only": True,
        }
    )

    temporary_embedding_path = output_dir / "clip_embeddings.tmp.npy"
    temporary_inventory_path = output_dir / "clip_inventory.tmp.csv"
    temporary_metadata_path = output_dir / "metadata.tmp.json"

    try:
        np.save(temporary_embedding_path, embeddings)
        inventory.to_csv(temporary_inventory_path, index=False)

        temporary_metadata_path.write_text(
            json.dumps(metadata_record, indent=2, default=str),
            encoding="utf-8",
        )

        temporary_embedding_path.replace(embedding_path)
        temporary_inventory_path.replace(inventory_path)
        temporary_metadata_path.replace(metadata_path)

    finally:
        for temporary_path in (
            temporary_embedding_path,
            temporary_inventory_path,
            temporary_metadata_path,
        ):
            if temporary_path.exists():
                temporary_path.unlink()

    return {
        "item_count": len(manifest),
        "embedding_shape": embeddings.shape,
        "embedding_dtype": str(embeddings.dtype),
        "device": device,
        "embedding_file": str(embedding_path),
        "inventory_file": str(inventory_path),
        "metadata_file": str(metadata_path),
    }
