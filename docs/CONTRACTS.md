# Draft shared Python contracts

`src/wardiq/contracts.py` supplies importable `TypedDict` definitions for agreement
between producers and consumers. These are draft interfaces, not team feature
implementations or runtime validators. They do not change the existing manifest,
serialize JSON, train a model, calculate scores, or enforce numeric ranges.
Import a type explicitly, for example `from wardiq.contracts import ItemRepresentation`.

| Type | Boundary | Status |
|---|---|---|
| `RawManifestRow` | Existing raw CSV inventory | Matches the existing 17 text columns; no parsing |
| `SourceIdentity`, `RunIdentity` | Identity and output provenance | Proposed shared vocabulary |
| `ItemRepresentation` | M2 to M3 | Draft requiring Hayat and downstream approval |
| `PairwiseScore`, `RankedOutfit` | M3 to M4 | Draft requiring scoring/ranking owners and reviewers |
| `PersonalizedOutfit`, `WardrobeUtility` | M4 to M5 | Draft requiring personalization/WUS owners and reviewers |

## Proposed conventions for review

All typed keys are required, but a nullable value explicitly represents unavailable
information. An empty attribute vector represents no configured attributes; a
nonempty vector and its mask should have equal length, in the versioned attribute
order. The proposed mask uses `True` for available and `False` for missing; a
missing entry is `None`, not a negative label. Owners must approve whether present
values represent labels, scores, or probabilities before freezing the schema.

LAB entries are triples; palette weights, color-space conventions, embedding
dimension/dtype and model/cache semantics remain pending. Python tuples become
JSON arrays only through an owner-provided serializer; no serializer is supplied.
Source identity keeps the original split. Project-split mapping remains a separate
owner-produced artifact, not a replacement for original source identity.

Outfits explicitly identify each scored pair and retain structural rejection
reasons. Rejected/unscored candidates may have `None` scores/ranks. Score ranges,
OCS aggregation, rank base, ties, candidate rules and unresolved-item handling
remain owner decisions. Personalization wraps the original M3 record to preserve
its score/rank; WUS fields name the existing planned components without defining
their mathematics. Missing context does not imply a fabricated default score.

## Freeze process

1. Producer and downstream reviewer settle the open choices in the
   [handoff register](HANDOFFS.md), with real example records and field shapes.
2. Update the draft types and architecture example together in the owner's PR.
3. Record the accepted version, conversion/migration rules and actual producer/load
   commands. New incompatible shapes require a new version.
4. Implement validation and serialization in the assigned owner's work, with checks
   at the boundary where an invalid record would break downstream processing.

Strict package Mypy checks these definitions for Python 3.10 compatibility. A
`TypedDict` alone does not verify file existence, item references, equal vector
lengths, probability bounds, or formula correctness. CI passing does not freeze
these drafts or supply any pending teammate implementation.
