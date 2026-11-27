# Feedback and preference baseline

Run with normal Python after installing the project dependencies.

```powershell
python -m wardiq.personalization.preferences docs/m4/examples/preference_demo.json
```

The module uses the Python standard library. The repository development and ML checks use the optional dependencies declared in pyproject.toml.

Input bundles contain versioned item feature tokens, outfit membership, a user ID, events and queries. Feature tokens use category:, color: and attribute: prefixes. Preserve canonical item and outfit IDs from upstream data. The included catalog and feedback are synthetic examples.

Feedback v1 supports like, dislike and clear. Feedback v2 also supports save, ignore and integer ratings from 1 through 5. Like maps to 1, dislike to -1, save to 0.5 and ratings to (rating - 3) / 2. Ignore preserves existing preference evidence. Clear removes direct evidence. These are explicit baseline policy choices pending evaluation with real feedback.

Build profiles from complete event history. Events require event_id, user_id, target_type, target_id, action, occurred_at with timezone, source (explicit_user or synthetic), and schema_version. Rating events also require rating. Duplicate IDs must have identical normalized content. The latest timestamp and event ID determine the active feedback per target. An optional as_of cutoff excludes later feedback.

Scores range from 0 through 1. Missing evidence yields null. Direct outfit feedback takes precedence over the mean of available item scores. Feature groups receive configurable weights. Coverage reports how many outfit items have evidence. Profile hashes bind the catalog, configuration and feedback snapshot.

The preference_score is compatible with the optional preference_score field in the existing PersonalizedOutfit contract. Consumers must match by outfit ID and retain the original M3 result. Context scoring, final ranking and wardrobe utility remain downstream owner responsibilities. The CLI returns standalone profiles, validation counts and scores for that handoff.
