import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from wardiq.personalization.preferences import Preferences, run_bundle


def event(
    action="like", target="a", kind="item", event_id="e1", when="2026-11-16T10:00:00Z", user="u"
):
    return dict(
        schema_version="wardiq.feedback.v1",
        event_id=event_id,
        user_id=user,
        target_type=kind,
        target_id=target,
        action=action,
        occurred_at=when,
        source="synthetic",
    )


class PreferenceTests(unittest.TestCase):
    def setUp(self):
        self.engine = Preferences(
            {"a": ["category:top"], "b": ["category:top"], "c": []},
            {"outfit": ["b", "c"]},
            catalog_version="demo-v1",
            feature_schema_version="demo-features-v1",
        )

    def score(self, events, kind="item", target="a"):
        profile, _ = self.engine.build("u", events)
        return self.engine.score(kind, target, profile)

    def test_cold_start_and_direct_feedback(self):
        self.assertIsNone(self.score([])["preference_score"])
        self.assertEqual(self.score([event()])["preference_score"], 1.0)
        self.assertEqual(self.score([event("dislike")])["preference_score"], 0.0)

    def test_clear_and_order_independence(self):
        rows = [event(), event("clear", event_id="e2", when="2026-11-16T11:00:00Z")]
        self.assertIsNone(self.score(rows)["preference_score"])
        left, _ = self.engine.build("u", rows)
        right, _ = self.engine.build("u", rows[::-1])
        self.assertEqual(left, right)

    def test_duplicates_and_conflicts(self):
        profile, report = self.engine.build("u", [event(), event()])
        single, _ = self.engine.build("u", [event()])
        self.assertEqual(profile, single)
        self.assertEqual(report["duplicate_events"], 1)
        with self.assertRaises(ValueError):
            self.engine.build("u", [event(), event("dislike")])

    def test_user_isolation(self):
        self.assertIsNone(self.score([event(user="someone-else")])["preference_score"])

    def test_partial_coverage(self):
        result = self.score([event()], "outfit", "outfit")
        self.assertEqual(result["preference_score"], 1.0)
        self.assertEqual(result["item_evidence_coverage"], 0.5)

    def test_outfit_dislike_does_not_label_items(self):
        rows = [event("dislike", target="outfit", kind="outfit")]
        self.assertEqual(self.score(rows, "outfit", "outfit")["preference_score"], 0)
        self.assertIsNone(self.score(rows, "item", "b")["preference_score"])

    def test_balanced_evidence_is_not_missing(self):
        rows = [event(), event("dislike", target="b", event_id="e2")]
        profile, _ = self.engine.build("u", rows)
        self.assertEqual(profile["features"]["category:top"], {"mean": 0, "count": 2})

    def test_bad_events_are_rejected(self):
        bad = [event(target="unknown"), event(action="click"), event(when="2026-11-16T10:00:00")]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.engine.build("u", [row])

    def test_ties_are_deterministic(self):
        rows = [event(), event("dislike", event_id="e2")]
        self.assertEqual(self.score(rows)["preference_score"], 0)
        self.assertEqual(self.score(rows[::-1])["preference_score"], 0)

    def test_profile_tampering_and_catalog_changes(self):
        profile, _ = self.engine.build("u", [event()])
        altered = copy.deepcopy(profile)
        altered["item_feedback"]["a"] = -1
        with self.assertRaises(ValueError):
            self.engine.score("item", "a", altered)
        changed = Preferences(
            {"a": []}, {}, catalog_version="demo-v1", feature_schema_version="demo-features-v1"
        )
        with self.assertRaises(ValueError):
            changed.score("item", "a", profile)


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.engine = Preferences(
            {"a": ["category:top"], "b": ["category:top"], "c": []},
            {"outfit": ["b", "c"]},
            catalog_version="demo-v1",
            feature_schema_version="demo-features-v1",
        )

    def test_cutoff_blocks_future_feedback(self):
        rows = [event(), event("dislike", event_id="e2", when="2026-11-17T10:00:00Z")]
        profile, report = self.engine.build("u", rows, as_of="2026-11-16T10:00:00Z")
        self.assertEqual(report["excluded_after_cutoff"], 1)
        self.assertEqual(self.engine.score("item", "a", profile)["preference_score"], 1)

    def test_cutoff_can_exclude_unknown_future_target(self):
        profile, report = self.engine.build(
            "u",
            [event(target="new-future-item", when="2026-11-17T10:00:00Z")],
            as_of="2026-11-16T10:00:00Z",
        )
        self.assertEqual(report["included_unique_events"], 0)
        self.assertIsNone(self.engine.score("item", "a", profile)["preference_score"])

    def test_equivalent_timezones_and_fractional_order(self):
        same = event(when="2026-11-16T12:00:00+02:00")
        profile, report = self.engine.build("u", [event(), same])
        self.assertEqual(report["duplicate_events"], 1)
        later = event("dislike", event_id="e2", when="2026-11-16T10:00:00.000001Z")
        profile, _ = self.engine.build("u", [later, event()])
        self.assertEqual(self.engine.score("item", "a", profile)["preference_score"], 0)

    def test_feature_group_weights_prevent_tag_count_bias(self):
        engine = Preferences(
            {
                "a": ["category:top"],
                "b": ["attribute:x", "attribute:y"],
                "probe": ["category:top", "attribute:x", "attribute:y"],
            },
            {},
            catalog_version="v1",
            feature_schema_version="f1",
        )
        profile, _ = engine.build("u", [event(), event("dislike", target="b", event_id="e2")])
        self.assertAlmostEqual(engine.score("item", "probe", profile)["preference_score"], 0.5)

    def test_explicit_group_weights(self):
        engine = Preferences(
            {"a": ["category:top"], "b": ["color:red"], "probe": ["category:top", "color:red"]},
            {},
            catalog_version="v1",
            feature_schema_version="f1",
            feature_weights={"category": 3, "color": 1},
        )
        profile, _ = engine.build("u", [event(), event("dislike", target="b", event_id="e2")])
        self.assertAlmostEqual(engine.score("item", "probe", profile)["preference_score"], 0.75)

    def test_invalid_weights(self):
        for weights in (
            {},
            {"color": 0},
            {"color": -1},
            {"color": True},
            {"color": float("nan")},
            {"unknown": 1},
            {"color": float("inf")},
            [],
        ):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                Preferences(
                    {}, {}, catalog_version="v", feature_schema_version="f", feature_weights=weights
                )

    def test_malformed_inputs_fail_with_value_error(self):
        for events in (None, {}, [None], [dict(event(), user_id=" u")]):
            with self.subTest(events=events), self.assertRaises(ValueError):
                self.engine.build("u", events)
        for bundle in ([], {}, {"items": None}):
            with self.subTest(bundle=bundle), self.assertRaises(ValueError):
                run_bundle(bundle)

    def test_invalid_catalogs(self):
        for items, outfits in (
            ([], {}),
            ({"a": "category:top"}, {}),
            ({"a": [None]}, {}),
            ({"a": ["weather:hot"]}, {}),
            ({"a": ["color:"]}, {}),
            ({"a": []}, {"o": []}),
            ({"a": []}, {"o": ["missing"]}),
            ({"a": []}, {"o": ["a", "a"]}),
        ):
            with self.subTest(items=items, outfits=outfits), self.assertRaises(ValueError):
                Preferences(items, outfits, catalog_version="v", feature_schema_version="f")

    def test_no_input_mutation_and_json_roundtrip(self):
        rows = [event()]
        before = copy.deepcopy(rows)
        profile, _ = self.engine.build("u", rows)
        self.assertEqual(rows, before)
        restored = json.loads(json.dumps(profile))
        self.assertEqual(
            self.engine.score("item", "a", profile), self.engine.score("item", "a", restored)
        )

    def test_configuration_mismatch(self):
        profile, _ = self.engine.build("u", [event()])
        other = Preferences(
            self.engine.items,
            self.engine.outfits,
            catalog_version="demo-v1",
            feature_schema_version="demo-features-v1",
            feature_weights={"category": 2},
        )
        with self.assertRaises(ValueError):
            other.score("item", "a", profile)

    def test_clear_retains_indirect_evidence_from_other_items(self):
        rows = [
            event(),
            event(target="b", event_id="e2"),
            event("clear", event_id="e3", when="2026-11-16T11:00:00Z"),
        ]
        profile, _ = self.engine.build("u", rows)
        result = self.engine.score("item", "a", profile)
        self.assertEqual(result["method"], "weighted_feature_groups")
        self.assertEqual(result["preference_score"], 1)

    def test_unknown_query_is_rejected(self):
        profile, _ = self.engine.build("u", [])
        for kind, target in (("item", "missing"), ("outfit", "missing"), ("other", "a")):
            with self.subTest(kind=kind, target=target), self.assertRaises(ValueError):
                self.engine.score(kind, target, profile)

    def test_repeat_feature_tokens_do_not_double_evidence(self):
        engine = Preferences(
            {"a": ["color:red", "color:red"]}, {}, catalog_version="v", feature_schema_version="f"
        )
        profile, _ = engine.build("u", [event()])
        self.assertEqual(profile["features"]["color:red"]["count"], 1)


class CliTests(unittest.TestCase):
    def test_cli_json_output_and_overwrite_protection(self):
        root = Path(__file__).resolve().parents[1]
        script = root / "src" / "wardiq" / "personalization" / "preferences.py"
        demo = root / "docs" / "m4" / "examples" / "preference_demo.json"
        with tempfile.TemporaryDirectory(prefix="m4-test-", dir=root) as folder:
            output = Path(folder) / "result.json"
            command = [sys.executable, str(script), str(demo), "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(data["scores"][1]["item_evidence_coverage"], 0.5)
            before = output.read_bytes()
            repeated = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(repeated.returncode, 2)
            self.assertEqual(output.read_bytes(), before)

    def test_cli_malformed_json(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="m4-test-", dir=root) as folder:
            malformed = Path(folder) / "bad.json"
            malformed.write_text('{"items": NaN}', encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(root / "src" / "wardiq" / "personalization" / "preferences.py"),
                    str(malformed),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("Non-finite", result.stderr)
            self.assertNotIn("Traceback", result.stderr)


class FeedbackV2Tests(PreferenceTests):
    def test_save_ignore_and_rating(self):
        saved = dict(event("save"), schema_version="wardiq.feedback.v2")
        self.assertEqual(self.score([saved])["preference_score"], 0.75)
        ignored = dict(event("ignore", event_id="e2"), schema_version="wardiq.feedback.v2")
        self.assertEqual(self.score([saved, ignored])["preference_score"], 0.75)
        for rating in range(1, 6):
            rated = dict(event("rating"), schema_version="wardiq.feedback.v2", rating=rating)
            self.assertEqual(self.score([rated])["preference_score"], (rating - 1) / 4)

    def test_invalid_ratings_and_legacy_actions(self):
        for rating in (True, 0, 6, 2.5, None):
            rated = dict(event("rating"), schema_version="wardiq.feedback.v2", rating=rating)
            with self.assertRaises(ValueError):
                self.score([rated])
        with self.assertRaises(ValueError):
            self.score([event("save")])


if __name__ == "__main__":
    unittest.main()
