from __future__ import annotations

from dataclasses import asdict as dataclass_asdict
import pytest
from types import SimpleNamespace

from rune_decrypter_prime.core.config import CipherConfig, RunConfig, SolverConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.solvers.two_period_cribs import profile_contract_hash
from rune_decrypter_prime.solvers.solver_base import SolverBase

pytestmark = pytest.mark.tier_a


def _assert_effective_models_equal(left, right) -> None:
    assert [(channel, n) for channel, n, _weight in left] == [
        (channel, n) for channel, n, _weight in right
    ]
    assert [weight for _channel, _n, weight in left] == pytest.approx(
        [weight for _channel, _n, weight in right]
    )


def test_default_weight_mode_preserves_pre_a3_effective_default() -> None:
    cfg = ScoringConfig()
    assert cfg.weight_mode == "default"
    assert cfg.weights is None
    assert cfg.char_weights is None
    assert cfg.wli_weights is None
    assert cfg.effective_lm_model_weights() == (
        ("char", 2, 0.5),
        ("wli", 2, 0.5),
    )


def test_explicit_legacy_pair_is_honoured() -> None:
    cfg = ScoringConfig(weights=(0.25, 0.75), n_char=2, n_wli=3)
    assert cfg.weight_mode == "legacy_pair"
    assert cfg.char_weights is None
    assert cfg.wli_weights is None
    assert cfg.effective_lm_model_weights() == (
        ("char", 2, 0.25),
        ("wli", 3, 0.75),
    )


def test_legacy_pair_supports_one_channel_and_renormalises_after_channel_selection() -> None:
    char_only = ScoringConfig(weights=(1.0, 0.0), n_char=3)
    assert char_only.effective_lm_model_weights() == (("char", 3, 1.0),)

    wli_only = ScoringConfig(weights=(0.0, 2.0), n_wli=4)
    assert wli_only.effective_lm_model_weights() == (("wli", 4, 1.0),)

    cfg = ScoringConfig(weights=(1.0, 3.0), n_char=2, n_wli=2)
    assert cfg.effective_lm_model_weights(use_wli=False) == (("char", 2, 1.0),)


def test_per_order_map_mode_is_canonical_and_derives_channel_totals() -> None:
    cfg = ScoringConfig(
        char_weights={1: 0.1, 2: 0.2},
        wli_weights={2: 0.3, 3: 0.4},
    )
    assert cfg.weight_mode == "per_order"
    assert cfg.weights is None
    models = cfg.effective_lm_model_weights()
    assert [(channel, n) for channel, n, _weight in models] == [
        ("char", 1), ("char", 2), ("wli", 2), ("wli", 3)
    ]
    assert [weight for _channel, _n, weight in models] == pytest.approx([0.1, 0.2, 0.3, 0.4])


def test_pair_and_map_inputs_are_explicitly_ambiguous() -> None:
    with pytest.raises(ValueError, match="cannot be combined"):
        ScoringConfig(weights=(0.25, 0.75), char_weights={2: 1.0})
    with pytest.raises(ValueError, match="cannot be combined"):
        ScoringConfig(weights=(0.25, 0.75), wli_weights={2: 1.0})


def test_legacy_pair_with_explicitly_empty_maps_remains_unambiguous() -> None:
    cfg = ScoringConfig(
        weights=(0.25, 0.75),
        char_weights={},
        wli_weights={},
        n_char=2,
        n_wli=3,
    )
    assert cfg.weight_mode == "legacy_pair"
    assert cfg.effective_lm_model_weights() == (
        ("char", 2, 0.25),
        ("wli", 3, 0.75),
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"weights": (-1.0, 2.0)},
        {"weights": (0.0, 0.0)},
        {"weights": (1.0,)},
        {"char_weights": {2: -0.1}},
        {"char_weights": {2: 0.0}, "wli_weights": {}},
    ],
)
def test_invalid_weight_configurations_fail_at_construction(kwargs) -> None:
    with pytest.raises((TypeError, ValueError)):
        ScoringConfig(**kwargs)


@pytest.mark.parametrize(
    "cfg",
    [
        ScoringConfig(),
        ScoringConfig(weights=(2.0, 6.0), n_char=2, n_wli=3),
        ScoringConfig(char_weights={1: 0.2, 2: 0.3}, wli_weights={2: 0.5}),
    ],
)
def test_scoring_asdict_is_constructor_roundtrippable(cfg: ScoringConfig) -> None:
    payload = cfg.asdict()
    assert "weight_mode" not in payload
    assert "effective_lm_models" not in payload
    rebuilt = ScoringConfig(**payload)
    assert rebuilt.weight_mode == cfg.weight_mode
    _assert_effective_models_equal(
        rebuilt.effective_lm_model_weights(), cfg.effective_lm_model_weights()
    )


def test_generic_dataclass_asdict_does_not_leak_derived_weight_state() -> None:
    configs = (
        ScoringConfig(),
        ScoringConfig(weights=(1.0, 3.0)),
        ScoringConfig(char_weights={1: 0.2, 2: 0.3}, wli_weights={2: 0.5}),
    )
    for cfg in configs:
        payload = dataclass_asdict(cfg)
        assert "weight_mode" not in payload
        rebuilt = ScoringConfig(**payload)
        assert rebuilt.weight_mode == cfg.weight_mode
        _assert_effective_models_equal(
            rebuilt.effective_lm_model_weights(), cfg.effective_lm_model_weights()
        )


def test_retained_development_scoring_adapter_removes_stale_redundant_pair() -> None:
    from cipher_development.two_period_overlay.benchmark import (
        _scoring_kwargs as two_period_scoring_kwargs,
    )
    from cipher_development.two_period_overlay.scorer_profiles import S2
    from rune_decrypter_prime.core.types import Direction

    s2_contract = S2.scoring_contract()
    # The scientific contract retains its historical aggregate field for
    # provenance, while the runtime adapter materialises the effective maps only.
    assert s2_contract["weights"] == [0.0, 1.0]
    assert s2_contract["char_weights"] == {}
    assert s2_contract["wli_weights"] == {1: 0.5, 2: 0.5}
    kwargs = two_period_scoring_kwargs(Direction, None, s2_contract)
    assert "weights" not in kwargs
    assert ScoringConfig(**kwargs).weight_mode == "per_order"


def test_weight_contract_reports_requested_mode_and_effective_models() -> None:
    cfg = ScoringConfig(weights=(2.0, 6.0), n_char=2, n_wli=3)
    payload = cfg.weight_contract()
    assert payload["mode"] == "legacy_pair"
    assert payload["requested"] == {"weights": [2.0, 6.0]}
    assert payload["effective_lm_models"] == [
        {"channel": "char", "n": 2, "weight": 0.25},
        {"channel": "wli", "n": 3, "weight": 0.75},
    ]


def test_run_config_roundtrip_preserves_weight_intent() -> None:
    for scoring in (
        ScoringConfig(),
        ScoringConfig(weights=(1.0, 3.0)),
        ScoringConfig(char_weights={1: 0.2, 2: 0.3}, wli_weights={2: 0.5}),
    ):
        run = RunConfig(
            cipher=CipherConfig(ciphertext=[0, 1], wli_data=[], key_length=1),
            scorer_name="rune",
            scorer_params=scoring,
            solver=SolverConfig(name="beam", params={"beam_width": 1}),
            seed=0,
        )
        rebuilt = RunConfig.from_dict(run.asdict())
        assert rebuilt.scorer_params.weight_mode == scoring.weight_mode
        _assert_effective_models_equal(
            rebuilt.scorer_params.effective_lm_model_weights(),
            scoring.effective_lm_model_weights(),
        )


def test_a2_two_period_profile_contract_hashes_are_unchanged() -> None:
    assert profile_contract_hash("S2") == "cfd406a753ef41ec8d217fafe0fb9a75ee902f4d07a135f14c754dc361ef9e51"
    assert profile_contract_hash("B1") == "025e8c6825f4597b540c05982f6c8be9d2b59f02cc3856cbe9a838fd90611613"
    assert profile_contract_hash("F1") == "56773006f1d252022952b026212e8df8bd991d6bcd268bf22f3a90405bb88fd8"


def test_progress_model_label_reports_effective_legacy_pair_models() -> None:
    cfg = ScoringConfig(weights=(1.0, 3.0), n_char=2, n_wli=3)
    solver = object.__new__(SolverBase)
    solver.problem = SimpleNamespace(
        s_cfg=cfg,
        scorer=SimpleNamespace(objective=cfg.objective),
    )
    label = solver._progress_model_label()
    assert "char2" in label
    assert "cw{2:0.25}" in label
    assert "wli3" in label
    assert "ww{3:0.75}" in label


def test_numpy_and_torch_model_selection_share_canonical_weight_contract() -> None:
    """Development-machine backend parity without loading LM assets."""
    pytest.importorskip("zstandard")
    pytest.importorskip("torch", reason="Torch backend required for parity test")
    from rune_decrypter_prime.scoring.rune_scorer_impl import RuneScorer
    from rune_decrypter_prime.scoring.torch_rune_scorer import RuneScorerTorch

    configs = (
        ScoringConfig(),
        ScoringConfig(weights=(1.0, 3.0), n_char=3, n_wli=4),
        ScoringConfig(char_weights={1: 0.2, 2: 0.3}, wli_weights={2: 0.5}),
    )
    for cfg in configs:
        numpy_scorer = object.__new__(RuneScorer)
        numpy_scorer._effective_model_weights = cfg.effective_lm_model_weights
        numpy_scorer.use_word_breaks = bool(cfg.use_word_breaks)
        numpy_models = [
            (channel.value, n, weight)
            for channel, n, weight in numpy_scorer._active_models()
        ]

        torch_scorer = object.__new__(RuneScorerTorch)
        torch_scorer._effective_model_weights = cfg.effective_lm_model_weights
        torch_models = torch_scorer._active_models(bool(cfg.use_word_breaks))

        _assert_effective_models_equal(numpy_models, torch_models)
