"""Eyad's M4 feedback processing and explicit preference baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "wardiq.preferences.v1"
FEEDBACK_VERSION = "wardiq.feedback.v2"
ACTIONS: dict[str, float | None] = {
    "like": 1.0,
    "dislike": -1.0,
    "save": 0.5,
    "ignore": None,
    "rating": None,
    "clear": None,
}
KINDS = ("category", "color", "attribute")
EVENT_FIELDS = (
    "event_id",
    "user_id",
    "target_type",
    "target_id",
    "action",
    "occurred_at",
    "source",
    "schema_version",
)


def digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a nonempty string without surrounding whitespace")
    return value


def timestamp(value: Any) -> datetime:
    result = datetime.fromisoformat(text(value, "timestamp").replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return result.astimezone(timezone.utc)


def object_value(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def reject_constant(value: str) -> Any:
    raise ValueError(f"Non-finite JSON number is unsupported: {value}")


class Preferences:
    def __init__(
        self,
        items: dict[str, list[str]],
        outfits: dict[str, list[str]],
        *,
        catalog_version: str,
        feature_schema_version: str,
        feature_weights: dict[str, float] | None = None,
    ) -> None:
        self.catalog_version = text(catalog_version, "catalog_version")
        self.feature_schema_version = text(feature_schema_version, "feature_schema_version")
        weights = (
            {kind: 1.0 for kind in KINDS}
            if feature_weights is None
            else object_value(feature_weights, "feature_weights")
        )
        if not weights or set(weights) - set(KINDS):
            raise ValueError("feature_weights needs supported category/color/attribute keys")
        self.weights: dict[str, float] = {}
        for kind, value in weights.items():
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value < 0
            ):
                raise ValueError("Feature weights must be finite, nonnegative numbers")
            self.weights[kind] = float(value)
        weight_total = sum(self.weights.values())
        if not math.isfinite(weight_total) or weight_total <= 0:
            raise ValueError("Feature weights must have a finite, positive total")
        self.items: dict[str, list[str]] = {}
        self.outfits: dict[str, list[str]] = {}
        for item_id, features in object_value(items, "items").items():
            text(item_id, "item_id")
            if not isinstance(features, list):
                raise ValueError(f"{item_id}: features must be a list")
            for feature in features:
                text(feature, "feature")
                kind, separator, label = feature.partition(":")
                if (
                    not separator
                    or kind not in KINDS
                    or not label.strip()
                    or label != label.strip()
                ):
                    raise ValueError(f"Unsupported feature token: {feature}")
            self.items[item_id] = sorted(set(features))
        for outfit_id, ids in object_value(outfits, "outfits").items():
            text(outfit_id, "outfit_id")
            if not isinstance(ids, list) or not ids:
                raise ValueError(f"{outfit_id}: item IDs must be a nonempty list")
            for item_id in ids:
                text(item_id, "item_id")
                if item_id not in self.items:
                    raise ValueError(f"{outfit_id}: unknown item {item_id}")
            if len(set(ids)) != len(ids):
                raise ValueError(f"{outfit_id}: duplicate items")
            self.outfits[outfit_id] = sorted(ids)
        self.catalog_hash = digest({"items": self.items, "outfits": self.outfits})

    def build(
        self, user_id: str, events: list[dict[str, Any]], *, as_of: str | None = None
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Rebuild from full event history, optionally through an inclusive cutoff."""
        text(user_id, "user_id")
        if not isinstance(events, list):
            raise ValueError("events must be a list")
        cutoff = timestamp(as_of) if as_of is not None else None
        seen: dict[str, dict[str, Any]] = {}
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        duplicate_count = other_user_count = excluded_count = 0
        for row_number, original in enumerate(events, 1):
            try:
                original = object_value(original, "event")
                owner = text(original.get("user_id"), "user_id")
                if owner != user_id:
                    other_user_count += 1
                    continue
                event: dict[str, Any] = {key: text(original.get(key), key) for key in EVENT_FIELDS}
                if event["schema_version"] not in {"wardiq.feedback.v1", FEEDBACK_VERSION}:
                    raise ValueError("Unsupported feedback schema")
                if event["target_type"] not in {"item", "outfit"}:
                    raise ValueError("target_type must be item or outfit")
                if event["action"] not in ACTIONS:
                    raise ValueError(
                        "Unsupported action: like/dislike/save/ignore/rating/clear required"
                    )
                if event["source"] not in {"explicit_user", "synthetic"}:
                    raise ValueError("Unsupported feedback source")
                if event["schema_version"] == "wardiq.feedback.v1" and event["action"] not in {
                    "like",
                    "dislike",
                    "clear",
                }:
                    raise ValueError("save/ignore/rating require feedback schema v2")
                if event["action"] == "rating":
                    rating = original.get("rating")
                    if (
                        isinstance(rating, bool)
                        or not isinstance(rating, int)
                        or not 1 <= rating <= 5
                    ):
                        raise ValueError("rating must be an integer from 1 to 5")
                    event["rating"] = rating
                elif "rating" in original:
                    raise ValueError("rating is only permitted for rating events")
                occurred = timestamp(event["occurred_at"])
                event["occurred_at"] = occurred.isoformat(timespec="microseconds")
                event_id = event["event_id"]
                if event_id in seen:
                    if seen[event_id] != event:
                        raise ValueError(f"Conflicting duplicate event ID: {event_id}")
                    duplicate_count += 1
                    continue
                seen[event_id] = event
                if cutoff is not None and occurred > cutoff:
                    excluded_count += 1
                    continue
                catalog = self.items if event["target_type"] == "item" else self.outfits
                if event["target_id"] not in catalog:
                    raise ValueError(f"Unknown target: {event['target_id']}")
                if event["action"] == "ignore":
                    continue  # Lack of interaction is not dislike and cannot erase a preference.
                key = (event["target_type"], event["target_id"])
                order = (event["occurred_at"], event_id)
                if key not in latest or order > (
                    latest[key]["occurred_at"],
                    latest[key]["event_id"],
                ):
                    latest[key] = event
            except ValueError as exc:
                raise ValueError(f"Event {row_number}: {exc}") from exc

        item_feedback, outfit_feedback = {}, {}
        evidence: dict[str, list[float]] = defaultdict(list)
        for event in latest.values():
            value = (
                (event["rating"] - 3) / 2
                if event["action"] == "rating"
                else ACTIONS[event["action"]]
            )
            if value is None:
                continue
            if event["target_type"] == "outfit":
                outfit_feedback[event["target_id"]] = value
            else:
                item_id = event["target_id"]
                item_feedback[item_id] = value
                for feature in self.items[item_id]:
                    evidence[feature].append(value)
        profile: dict[str, Any] = {
            "schema_version": VERSION,
            "user_id": user_id,
            "catalog_version": self.catalog_version,
            "feature_schema_version": self.feature_schema_version,
            "catalog_hash": self.catalog_hash,
            "feature_weights": self.weights.copy(),
            "as_of": cutoff.isoformat(timespec="microseconds") if cutoff else None,
            "item_feedback": item_feedback,
            "outfit_feedback": outfit_feedback,
            "features": {
                key: {"mean": sum(values) / len(values), "count": len(values)}
                for key, values in evidence.items()
            },
            "latest_events": sorted(latest.values(), key=lambda e: e["event_id"]),
            "feedback_policy_version": "explicit-feedback-baseline-v1",
            "ignored_events": sorted(
                [
                    e
                    for e in seen.values()
                    if e["action"] == "ignore"
                    and (cutoff is None or timestamp(e["occurred_at"]) <= cutoff)
                ],
                key=lambda e: e["event_id"],
            ),
            "contains_synthetic": any(
                e["source"] == "synthetic"
                for e in seen.values()
                if cutoff is None or timestamp(e["occurred_at"]) <= cutoff
            ),
        }
        profile["profile_version"] = digest(profile)
        report = {
            "unique_events": len(seen),
            "included_unique_events": len(seen) - excluded_count,
            "duplicate_events": duplicate_count,
            "other_user_events": other_user_count,
            "excluded_after_cutoff": excluded_count,
            "ignored_events": len(profile["ignored_events"]),
        }
        return profile, report

    def _check(self, profile: dict[str, Any]) -> None:
        object_value(profile, "profile")
        expected = (
            VERSION,
            self.catalog_version,
            self.feature_schema_version,
            self.catalog_hash,
            self.weights,
        )
        actual = tuple(
            profile.get(k)
            for k in (
                "schema_version",
                "catalog_version",
                "feature_schema_version",
                "catalog_hash",
                "feature_weights",
            )
        )
        if actual != expected:
            raise ValueError("Profile/catalog/config mismatch; rebuild the profile")
        payload = {k: v for k, v in profile.items() if k != "profile_version"}
        if digest(payload) != profile.get("profile_version"):
            raise ValueError("Profile content changed; rebuild it")

    def _item(self, item_id: str, profile: dict[str, Any]) -> tuple[float | None, str]:
        text(item_id, "item_id")
        if item_id not in self.items:
            raise ValueError(f"Unknown item: {item_id}")
        if item_id in profile["item_feedback"]:
            return float((profile["item_feedback"][item_id] + 1) / 2), "direct_item"
        groups: dict[str, list[float]] = defaultdict(list)
        for feature in self.items[item_id]:
            kind = feature.split(":", 1)[0]
            if feature in profile["features"] and self.weights.get(kind, 0) > 0:
                groups[kind].append(profile["features"][feature]["mean"])
        if not groups:
            return None, "no_evidence"
        denominator = sum(self.weights[kind] for kind in groups)
        raw = (
            sum((sum(values) / len(values)) * self.weights[kind] for kind, values in groups.items())
            / denominator
        )
        return (max(-1.0, min(1.0, raw)) + 1) / 2, "weighted_feature_groups"

    def score(self, target_type: str, target_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        self._check(profile)
        text(target_id, "target_id")
        if target_type == "item":
            score, method = self._item(target_id, profile)
            scored, total = int(score is not None), 1
        elif target_type == "outfit":
            if target_id not in self.outfits:
                raise ValueError(f"Unknown outfit: {target_id}")
            ids = self.outfits[target_id]
            optional_values = [self._item(item_id, profile)[0] for item_id in ids]
            values = [v for v in optional_values if v is not None]
            scored, total = len(values), len(ids)
            if target_id in profile["outfit_feedback"]:
                score = (profile["outfit_feedback"][target_id] + 1) / 2
                method = "direct_outfit"
            else:
                score = sum(values) / len(values) if values else None
                method = "mean_available_items" if values else "no_evidence"
        else:
            raise ValueError("target_type must be item or outfit")
        return {
            "schema_version": "wardiq.preference-score.v1",
            "user_id": profile["user_id"],
            "target_type": target_type,
            "target_id": target_id,
            "preference_score": score,
            "method": method,
            "scored_items": scored,
            "total_items": total,
            "item_evidence_coverage": scored / total,
            "profile_version": profile["profile_version"],
            "catalog_version": self.catalog_version,
            "feature_schema_version": self.feature_schema_version,
            "algorithm_version": VERSION,
            "as_of": profile["as_of"],
            "contains_synthetic": profile["contains_synthetic"],
        }


def run_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    object_value(bundle, "input")
    required = {
        "items",
        "outfits",
        "catalog_version",
        "feature_schema_version",
        "user_id",
        "events",
        "queries",
    }
    missing = required - bundle.keys()
    if missing:
        raise ValueError(f"Missing input fields: {', '.join(sorted(missing))}")
    engine = Preferences(
        bundle["items"],
        bundle["outfits"],
        catalog_version=bundle["catalog_version"],
        feature_schema_version=bundle["feature_schema_version"],
        feature_weights=bundle.get("feature_weights"),
    )
    profile, report = engine.build(bundle["user_id"], bundle["events"], as_of=bundle.get("as_of"))
    if not isinstance(bundle["queries"], list):
        raise ValueError("queries must be a list")
    scores = []
    for query in bundle["queries"]:
        object_value(query, "query")
        scores.append(
            engine.score(
                text(query.get("target_type"), "target_type"),
                text(query.get("target_id"), "target_id"),
                profile,
            )
        )
    return {"profile": profile, "validation": report, "scores": scores}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="JSON input bundle")
    parser.add_argument(
        "--output", help="New UTF-8 JSON file; existing files are never overwritten"
    )
    args = parser.parse_args()
    try:
        bundle = json.loads(
            Path(args.input).read_text(encoding="utf-8-sig"), parse_constant=reject_constant
        )
        result = run_bundle(bundle)
        rendered = json.dumps(result, indent=2, sort_keys=True, allow_nan=False)
        if args.output:
            with Path(args.output).open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(rendered + "\n")
        else:
            print(rendered)
    except (ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
