"""Small behaviour tests for the transparent M3 rule baseline."""

import math

import pytest

from wardiq.compatibility.rule_baseline import (
    MIN_WEIGHT_COVERAGE,
    WEIGHTS,
    PairScore,
    mean_ocs,
    score_pair_features,
    score_rows,
)

FEATURE_NAMES = [
    "category:top|bottom",
    "category:both_mapped",
    "clip:cosine",
    "lab:expected_delta_e76_over_100",
    "lab:both_available",
]


def make_row(
    *,
    cosine: float = 1.0,
    distance: float = 0.0,
    colour: float = 1.0,
    category: float = 1.0,
) -> list[float]:
    return [1.0, category, cosine, distance, colour]


def test_all_perfect_signals_score_exactly_one() -> None:
    result = score_pair_features(
        feature_names=FEATURE_NAMES,
        feature_values=make_row(),
    )
    assert result == PairScore(1.0, "scored", ("embedding", "colour", "category"), 1.0)


@pytest.mark.parametrize(
    ("category_feature", "category_value"),
    [
        ("category:top|bottom", 1.0),
        ("category:bag|top", 0.7),
        ("category:top|top", 0.3),
        ("category:one_piece|top", 0.3),
    ],
)
def test_category_rules_use_the_documented_values(
    category_feature: str, category_value: float
) -> None:
    names = [
        category_feature,
        "category:both_mapped",
        "clip:cosine",
        "lab:expected_delta_e76_over_100",
        "lab:both_available",
    ]
    result = score_pair_features(
        feature_names=names,
        feature_values=[1.0, 1.0, 1.0, 0.0, 1.0],
    )
    assert result.score == pytest.approx(0.25 + 0.35 + 0.40 * category_value)


def test_missing_colour_is_left_out_and_weights_are_renormalised() -> None:
    result = score_pair_features(
        feature_names=FEATURE_NAMES,
        feature_values=make_row(cosine=0.8, colour=0.0, category=1.0),
    )
    expected = (WEIGHTS["embedding"] * 0.8 + WEIGHTS["category"]) / 0.65
    assert result.score == pytest.approx(expected)
    assert result.weight_coverage == pytest.approx(0.65)
    assert result.signals_used == ("embedding", "category")


def test_real_zero_embedding_similarity_stays_zero() -> None:
    result = score_pair_features(
        feature_names=FEATURE_NAMES,
        feature_values=make_row(cosine=0.0, distance=0.0, colour=1.0, category=1.0),
    )
    assert result.score == pytest.approx(0.75)


def test_unknown_category_and_missing_colour_are_insufficient() -> None:
    result = score_pair_features(
        feature_names=FEATURE_NAMES,
        feature_values=make_row(cosine=0.9, colour=0.0, category=0.0),
    )
    assert result.score is None
    assert result.status == "insufficient_evidence"
    assert result.weight_coverage == WEIGHTS["embedding"]
    assert result.weight_coverage < MIN_WEIGHT_COVERAGE


def test_feature_order_does_not_matter() -> None:
    values = make_row(cosine=0.6, distance=0.4)
    first = score_pair_features(feature_names=FEATURE_NAMES, feature_values=values)
    second = score_pair_features(feature_names=FEATURE_NAMES[::-1], feature_values=values[::-1])
    assert first == second


def test_category_score_is_symmetric() -> None:
    names_ab = [
        "category:bottom|top",
        "category:both_mapped",
        "clip:cosine",
        "lab:expected_delta_e76_over_100",
        "lab:both_available",
    ]
    names_ba = [
        "category:top|bottom",
        "category:both_mapped",
        "clip:cosine",
        "lab:expected_delta_e76_over_100",
        "lab:both_available",
    ]
    values = [1, 1, 0.7, 0.2, 1]
    result_ab = score_pair_features(feature_names=names_ab, feature_values=values)
    result_ba = score_pair_features(feature_names=names_ba, feature_values=values)
    assert result_ab == result_ba


def test_scoring_twice_is_identical() -> None:
    row = make_row(cosine=0.4, distance=0.3)
    first = score_pair_features(feature_names=FEATURE_NAMES, feature_values=row)
    second = score_pair_features(feature_names=FEATURE_NAMES, feature_values=row)
    assert first == second


def test_score_rows_keeps_row_order() -> None:
    rows = [make_row(cosine=0.2), make_row(cosine=0.8)]
    results = score_rows(FEATURE_NAMES, rows)
    assert results[0].score < results[1].score


def test_mean_ocs_returns_none_if_any_pair_is_unscored() -> None:
    scored = PairScore(0.8, "scored", ("embedding",), 0.25)
    unscored = PairScore(None, "insufficient_evidence", ("embedding",), 0.25)
    assert mean_ocs([scored, unscored]) is None
    assert mean_ocs([scored, PairScore(0.6, "scored", ("embedding",), 0.25)]) == 0.7
    assert mean_ocs([]) is None


@pytest.mark.parametrize("bad_value", [math.nan, math.inf, -math.inf])
def test_non_finite_values_raise(bad_value: float) -> None:
    values = make_row()
    values[2] = bad_value
    with pytest.raises(ValueError):
        score_pair_features(feature_names=FEATURE_NAMES, feature_values=values)


def test_wrong_length_raises() -> None:
    with pytest.raises(ValueError):
        score_pair_features(feature_names=FEATURE_NAMES, feature_values=[1.0])


def test_duplicate_names_raise() -> None:
    names = FEATURE_NAMES + [FEATURE_NAMES[0]]
    with pytest.raises(ValueError):
        score_pair_features(feature_names=names, feature_values=[1.0] * len(names))


@pytest.mark.parametrize("bad_flag", [-1.0, 0.5, 2.0])
def test_invalid_colour_flag_raises(bad_flag: float) -> None:
    values = make_row()
    values[4] = bad_flag
    with pytest.raises(ValueError):
        score_pair_features(feature_names=FEATURE_NAMES, feature_values=values)


def test_unknown_category_feature_fails_loudly() -> None:
    names = [
        "category:top|unknown",
        "category:both_mapped",
        "clip:cosine",
        "lab:expected_delta_e76_over_100",
        "lab:both_available",
    ]
    with pytest.raises(ValueError):
        score_pair_features(feature_names=names, feature_values=[1, 1, 0.5, 0, 0])


@pytest.mark.parametrize("bad_flag", [-1.0, 0.5, 2.0])
def test_invalid_category_flag_raises(bad_flag: float) -> None:
    values = make_row()
    values[1] = bad_flag
    with pytest.raises(ValueError):
        score_pair_features(
            feature_names=FEATURE_NAMES,
            feature_values=values,
        )
