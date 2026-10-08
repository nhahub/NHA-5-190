# Team ownership and handoffs

Primary ownership clarifies accountability; it does not prevent collaboration.

| Member | Primary area | M1 | M2 | M3 | M4 | M5 |
|---|---|---|---|---|---|---|
| Eyad Amir | Data / ML | Dataset mapping | LAB color extraction / final Polyvore cache | Compatibility data | Feedback representation | Reproducibility/data docs |
| Hayat Hussein | CV / integration | Preprocessing/loaders | CLIP / embeddings | Compatibility features | Personalized reranking | M2 evaluation/architecture |
| Ziad Nasser | Models | Quality analysis | Supported attributes | Logistic regression | Context scoring | Model error analysis |
| Omar Ahmed | Recommendation | Splits | Model comparison / recommendation | Candidate generation | Wardrobe gaps | Compatibility evaluation |
| Hana Emad El Din Shazly | Optimization | Garment preparation | Initial taxonomy/schema / final representation integration | OCS and Top-K | WUS | Personalization validation |
| Asmaa Tamer | Evaluation / docs | Taxonomy/verification | ResNet baseline / fine-tuning / evaluation | Rule baseline/contract | Integration/output | End-to-end report/demo |

M2 assignments above were reconciled on 2026-10-08 against the
[Notion M2 execution phases](https://app.notion.com/p/3dd98a0a49c081bb84f1c46325fb0421).
Color extraction can start from usable garment samples; the final cache waits for
the frozen representation contract and selected components.

## Review chain

- Ziad and Asmaa verify M1 selection, manifest, paths, images, and annotations.
- Hayat supplies preprocessing outputs to M2 owners.
- Omar, Hana, and Asmaa approve the frozen M2 representation contract.
- Hana and Asmaa verify M3 scoring and ranking for M4.
- Asmaa verifies end-to-end evaluation readiness after M4.

A handoff is ready when the downstream owner can run the documented command, understand the schema, and reproduce the output without private instructions.

See [review routing and pending backup reviewers](REVIEWERS.md) for GitHub review
coordination and the handoff-blocker issue workflow. Existing task assignments remain unchanged.
