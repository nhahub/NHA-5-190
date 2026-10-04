"""Draft handoff types only; no loaders, models, scoring, or runtime validation.

These proposed interfaces require producer and downstream reviewer approval.
The raw manifest type describes existing CSV text; other types are not frozen.
"""

from typing import Literal, TypedDict


class RawManifestRow(TypedDict):
    """Existing image-level CSV columns, before any parsing or transformation."""

    item_id: str
    source_dataset: str
    source_release: str
    source_split: str
    source_index: str
    source_image_id: str
    original_filename: str
    original_image_reference: str
    annotation_reference: str
    category_ids: str
    category_labels: str
    attribute_ids: str
    annotation_ids: str
    outfit_ids: str
    image_width: str
    image_height: str
    traceability_status: str


class SourceIdentity(TypedDict):
    """Original source identity, kept separately from any project split."""

    dataset: str
    release: str
    split: str


class RunIdentity(TypedDict):
    """References to the versioned inputs that produced an output."""

    code_revision: str
    config_ref: str
    model_version: str
    cache_version: str


class ItemRepresentation(TypedDict):
    """Proposed M2 item record; attribute ordering is externally versioned."""

    schema_version: Literal["wardiq.item.v1"]
    item_id: str
    category_id: str | None
    category_score: float | None
    attributes: list[float | None]
    attribute_mask: list[bool]
    color_palette_lab: list[tuple[float, float, float]]
    embedding_ref: str | None
    source: SourceIdentity
    provenance: RunIdentity


class PairwiseScore(TypedDict):
    """Probability for an explicitly identified pair, without a scoring formula."""

    left_item_id: str
    right_item_id: str
    probability: float


class RankedOutfit(TypedDict):
    """Proposed M3 output; OCS, ranking and structural policy are owner decisions."""

    schema_version: Literal["wardiq.outfit.v1"]
    outfit_id: str
    item_ids: list[str]
    structurally_valid: bool
    rejection_reasons: list[str]
    pairwise_scores: list[PairwiseScore]
    ocs: float | None
    rank: int | None
    provenance: RunIdentity


class PersonalizedOutfit(TypedDict):
    """Proposed M4 wrapper retaining the full original M3 record."""

    schema_version: Literal["wardiq.personalized-outfit.v1"]
    original: RankedOutfit
    profile_version: str
    context_ref: str
    preference_score: float | None
    context_score: float | None
    final_score: float | None
    new_rank: int | None
    config_ref: str


class WardrobeUtility(TypedDict):
    """Named WUS outputs only; no approved weights or normalization implied."""

    schema_version: Literal["wardiq.wardrobe-utility.v1"]
    wardrobe_ref: str
    candidate_item_id: str
    gain: float | None
    avg_ocs: float | None
    preference: float | None
    context: float | None
    redundancy: float | None
    wus: float | None
    config_ref: str
