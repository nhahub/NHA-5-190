# System architecture and contracts

**Status:** Planned module boundaries and draft handoff contracts. The item JSON
below is illustrative until the assigned owners freeze its schema, field shapes,
score meanings and missing-value policy. These documents do not supply model,
loader, scoring or personalization implementations. Follow the milestone pages
and [handoff review requirements](../HANDOFFS.md) for acceptance evidence.
Importable draft types and their proposed conventions are described in
[shared contracts](../CONTRACTS.md). This earlier JSON example omits the proposed
release/provenance fields and is not a complete accepted record.

## Module boundaries

| Module | Owns | Must not own |
|---|---|---|
| `wardiq.data` | Manifests, loaders, transformations, splits, traceability | Model-specific decisions |
| `wardiq.clothing` | Garment preparation, category/attribute inference, color | Outfit ranking |
| `wardiq.representation` | Versioned representation and feature cache | Candidate generation |
| `wardiq.compatibility` | Candidates, features, models, OCS, Top-K | User preference storage |
| `wardiq.personalization` | Preferences, context, reranking, gaps, WUS | Recomputing M2 features |
| `wardiq.evaluation` | Metrics, error analysis, reproducibility reports | Training side effects |

## M1 to M2 contract

Every item preserves stable ID, source dataset/release/index, image and annotation references, available category/attribute/box/mask data, source/project split, and explicit traceability status.

## M2 to M3 contract

Freeze and version the structured representation before compatibility work:

```json
{
  "schema_version": "wardiq.item.v1",
  "item_id": "source_stable_id",
  "category_id": "canonical_or_source_category",
  "category_score": 0.0,
  "attributes": [],
  "attribute_mask": [],
  "color_palette_lab": [],
  "embedding_ref": "artifacts/features/...",
  "source": {"dataset": "...", "split": "..."}
}
```

Missing attributes are masked; they are never converted into negative labels.

## M3 to M4 contract

M3 returns item IDs, structural validity, pairwise probabilities, OCS, model/config versions, and rank. M4 adds preference and context components while retaining the original M3 score.

## Reproducibility

Generated outputs record dataset release, source split, configuration, seed, code revision, and schema/model version. Raw data is immutable and generated artifacts stay outside Git.
