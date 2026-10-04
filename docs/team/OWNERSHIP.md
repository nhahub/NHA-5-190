# Team ownership and handoffs

Primary ownership clarifies accountability; it does not prevent collaboration.

| Member | Primary area | M1 | M2 | M3 | M4 | M5 |
|---|---|---|---|---|---|---|
| Eyad Amir | Data / ML | Dataset mapping | ResNet baseline | Compatibility data | Feedback representation | Reproducibility/data docs |
| Hayat Hussein | CV / integration | Preprocessing/loaders | Item representation | Compatibility features | Personalized reranking | M2 evaluation/architecture |
| Ziad Nasser | Models | Quality analysis | CLIP experiments | Logistic regression | Context scoring | Model error analysis |
| Omar Ahmed | Recommendation | Splits | Color pipeline | Candidate generation | Wardrobe gaps | Compatibility evaluation |
| Hana Emad El Din Shazly | Optimization | Garment preparation | Attributes/masks | OCS and Top-K | WUS | Personalization validation |
| Asmaa Tamer | Evaluation / docs | Taxonomy/verification | Comparison/cache | Rule baseline/contract | Integration/output | End-to-end report/demo |

## Review chain

- Ziad and Asmaa verify M1 selection, manifest, paths, images, and annotations.
- Hayat supplies preprocessing outputs to M2 owners.
- Omar, Hana, and Asmaa approve the frozen M2 representation contract.
- Hana and Asmaa verify M3 scoring and ranking for M4.
- Asmaa verifies end-to-end evaluation readiness after M4.

A handoff is ready when the downstream owner can run the documented command, understand the schema, and reproduce the output without private instructions.

See [review routing and pending backup reviewers](REVIEWERS.md) for GitHub review
coordination and the handoff-blocker issue workflow. Existing task assignments remain unchanged.
