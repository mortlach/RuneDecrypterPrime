from __future__ import annotations

import pytest
from rdp import api


def test_default_weights_preserve_balanced_character_and_word_length_lanes() -> None:
    cfg = api.ScoringConfig()
    assert cfg.effective_lm_model_weights() == (
        ("char", 2, 0.5),
        ("wli", 2, 0.5),
    )


def test_base_lane_weights_are_normalized_after_lane_selection() -> None:
    cfg = api.ScoringConfig(
        base_lane_weights=(1.0, 3.0),
        character_ngram_order=2,
        word_length_ngram_order=3,
    )
    assert cfg.effective_lm_model_weights() == (
        ("char", 2, 0.25),
        ("wli", 3, 0.75),
    )
    assert cfg.effective_lm_model_weights(use_word_lengths=False) == (("char", 2, 1.0),)


def test_per_order_weights_are_canonical_and_normalized() -> None:
    cfg = api.ScoringConfig(
        character_order_weights={1: 0.1, 2: 0.2},
        word_length_order_weights={2: 0.3, 3: 0.4},
    )
    models = cfg.effective_lm_model_weights()
    assert [(channel, order) for channel, order, _weight in models] == [
        ("char", 1),
        ("char", 2),
        ("wli", 2),
        ("wli", 3),
    ]
    assert [weight for _channel, _order, weight in models] == pytest.approx(
        [0.1, 0.2, 0.3, 0.4]
    )


def test_base_and_per_order_weights_cannot_be_combined() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        api.ScoringConfig(
            base_lane_weights=(0.25, 0.75),
            character_order_weights={2: 1.0},
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_lane_weights": (-1.0, 2.0)},
        {"base_lane_weights": (0.0, 0.0)},
        {"base_lane_weights": (1.0,)},
        {"character_order_weights": {2: -0.1}},
        {
            "character_order_weights": {2: 0.0},
            "word_length_order_weights": {},
        },
    ],
)
def test_invalid_weight_configurations_fail_at_construction(
    kwargs: dict[str, object],
) -> None:
    with pytest.raises((TypeError, ValueError)):
        api.ScoringConfig(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "cfg",
    [
        api.ScoringConfig(),
        api.ScoringConfig(base_lane_weights=(2.0, 6.0)),
        api.ScoringConfig(
            character_order_weights={1: 0.2, 2: 0.3},
            word_length_order_weights={2: 0.5},
        ),
    ],
)
def test_public_serialization_roundtrips_weight_intent(
    cfg: api.ScoringConfig,
) -> None:
    payload = cfg.to_dict()
    rebuilt = api.ScoringConfig.from_dict(payload)
    assert rebuilt == cfg
    assert rebuilt.effective_lm_model_weights() == cfg.effective_lm_model_weights()


def test_weight_contract_uses_canonical_requested_field_names() -> None:
    cfg = api.ScoringConfig(base_lane_weights=(2.0, 6.0))
    payload = cfg.weight_contract()
    assert payload["requested"] == {
        "base_lane_weights": [2.0, 6.0],
        "character_order_weights": {},
        "word_length_order_weights": {},
    }
    assert payload["effective_lm_models"] == [
        {"channel": "char", "n": 2, "weight": 0.25},
        {"channel": "wli", "n": 2, "weight": 0.75},
    ]
