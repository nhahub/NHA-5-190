"""Unit tests for pairwise compatibility scoring and OCS aggregation (Milestone 3)."""

from __future__ import annotations

import pytest

from wardiq.compatibility.scoring import (
    compute_pairwise_cosine_similarity,
    score_outfit_candidate,
)


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    sim = compute_pairwise_cosine_similarity(v, v)
    assert sim == 1.0


def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    sim = compute_pairwise_cosine_similarity(v1, v2)
    assert sim == 0.0


def test_score_outfit_candidate():
    item_ids = ["item_top", "item_bottom", "item_shoes"]
    embeddings = {
        "item_top": [1.0, 0.0, 0.0],
        "item_bottom": [1.0, 0.0, 0.0],
        "item_shoes": [0.0, 1.0, 0.0],
    }
    result = score_outfit_candidate(item_ids, embeddings)
    assert result.structurally_valid is True
    assert result.ocs is not None
    assert len(result.pairwise_scores) == 3