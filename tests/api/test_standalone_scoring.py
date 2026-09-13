from __future__ import annotations

import inspect

import numpy as np
import pytest

from rdp import api
from rdp.core.types import Device, Direction
from rdp.data.runeglish import Runeglish
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets


pytestmark = pytest.mark.tier_a


class _RecordingScorer:
    def __init__(self) -> None:
        self.batch_calls: list[tuple[np.ndarray, np.ndarray | None]] = []
        self.scalar_calls: list[tuple[np.ndarray, object]] = []

    def batch_score(self, plaintexts, wlis=None):
        pt_array = np.asarray(plaintexts, dtype=np.uint8)
        wli_array = None if wlis is None else np.asarray(wlis, dtype=np.uint8)
        self.batch_calls.append((pt_array.copy(), None if wli_array is None else wli_array.copy()))
        return np.asarray(
            [float(np.sum(row, dtype=np.int64)) for row in pt_array],
            dtype=np.float64,
        )

    def score(self, plaintext, wli=None):
        pt_array = np.asarray(plaintext, dtype=np.uint8)
        self.scalar_calls.append((pt_array.copy(), wli))
        return float(np.sum(pt_array, dtype=np.int64))


def _patch_scorer(monkeypatch: pytest.MonkeyPatch) -> tuple[_RecordingScorer, list[object]]:
    import rdp.api.scoring as scoring_api

    scorer = _RecordingScorer()
    contexts: list[object] = []

    def fake_build_scorer(context, config):
        contexts.append((context, config))
        return scorer

    monkeypatch.setattr(scoring_api, "build_scorer", fake_build_scorer)
    return scorer, contexts


def test_score_matches_one_item_score_many(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer(monkeypatch)
    candidate = api.RuneInput("THE", format=api.RuneInputFormat.ENGLISH)
    assert api.score(candidate) == api.score_many((candidate,))[0]


def test_public_scoring_signatures_keep_ltr_cpu_defaults() -> None:
    for operation in (api.score, api.score_many):
        signature = inspect.signature(operation)
        assert signature.parameters["text_direction"].default is api.TextDirection.LTR
        assert signature.parameters["compute_device"].default is api.ComputeDevice.CPU


def test_empty_batch_does_not_build_or_load_a_scorer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rdp.api.scoring as scoring_api

    def explode(*_args, **_kwargs):
        raise AssertionError("scorer should not be built for an empty batch")

    monkeypatch.setattr(scoring_api, "build_scorer", explode)
    assert api.score_many(()) == ()


def test_batch_preserves_order_across_lengths_and_wli_shapes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scorer, _ = _patch_scorer(monkeypatch)
    candidates = (
        api.RuneInput((1, 2), word_length_information=((0, 2), (1, 2))),
        api.RuneInput((8, 3, 4)),
        api.RuneInput((5, 6), word_length_information=((0, 1), (0, 1))),
        api.RuneInput((7,)),
    )
    assert api.score_many(
        candidates,
        scoring=api.ScoringConfig(wli_lane_enabled=False),
    ) == (3.0, 15.0, 11.0, 7.0)
    assert len(scorer.batch_calls) == 2
    assert len(scorer.scalar_calls) == 2


def test_all_text_formats_use_the_shared_normalizer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rdp.api.scoring as scoring_api

    normalize = scoring_api.normalize_rune_input
    formats: list[str] = []

    def recording_normalize(*args, **kwargs):
        formats.append(kwargs["input_format"])
        return normalize(*args, **kwargs)

    monkeypatch.setattr(scoring_api, "normalize_rune_input", recording_normalize)
    _patch_scorer(monkeypatch)
    indices, _wli, runes = Runeglish.encode_english_to_runes("THE", direction="ltr")
    values = api.score_many(
        (
            api.RuneInput("THE", format=api.RuneInputFormat.ENGLISH),
            api.RuneInput("TH·E", format=api.RuneInputFormat.RUNE_LATIN),
            api.RuneInput(runes, format=api.RuneInputFormat.RUNES),
            api.RuneInput(indices, word_length_information=((0, 2), (1, 2))),
        )
    )
    assert values == (values[0],) * 4
    assert formats == ["english", "rune_latin", "runes", "indices"]


def test_character_only_scoring_accepts_indices_without_wli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scorer(monkeypatch)
    value = api.score(
        api.RuneInput((1, 2, 3, 4)),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=False,
            character_order_weights={1: 1.0},
            wli_order_weights={},
        ),
    )
    assert value == 10.0


def test_zero_weight_wli_lane_does_not_require_wli(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_scorer(monkeypatch)
    value = api.score(
        api.RuneInput((1, 2, 3, 4)),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=True,
            character_order_weights={1: 1.0},
            wli_order_weights={},
        ),
    )
    assert value == 10.0


def test_default_wli_scoring_rejects_indices_without_wli_before_build(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _scorer, contexts = _patch_scorer(monkeypatch)
    with pytest.raises(ValueError, match="word_length_information"):
        api.score(api.RuneInput((1, 2, 3, 4)))
    assert contexts == []


def test_calibrated_span_scoring_retains_the_no_wli_special_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scorer, _ = _patch_scorer(monkeypatch)
    value = api.score(
        api.RuneInput((1, 2, 3)),
        scoring=api.ScoringConfig(
            span_hamming_mode=api.advanced.SpanHammingMode.CALIBRATED
        ),
    )
    assert value == 6.0
    assert len(scorer.scalar_calls) == 1


def test_direction_and_device_map_to_exact_core_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _scorer, contexts = _patch_scorer(monkeypatch)
    api.score(
        api.RuneInput("READ"),
        text_direction=api.TextDirection.RTL,
        compute_device=api.ComputeDevice.CUDA,
    )
    context, _ = contexts[0]
    assert context.encoding_dir is Direction.RTL
    assert context.device is Device.CUDA


def test_inputs_and_wli_are_not_mutated(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_scorer(monkeypatch)
    candidate = api.RuneInput(
        [1, 2, 3],
        word_length_information=[[0, 3], [1, 3], [2, 3]],
    )
    before = (candidate.value, candidate.word_length_information)
    api.score(candidate)
    assert (candidate.value, candidate.word_length_information) == before


def test_requested_scorer_failure_is_not_silently_replaced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import rdp.api.scoring as scoring_api

    def unavailable(*_args, **_kwargs):
        raise RuntimeError("requested backend unavailable")

    monkeypatch.setattr(scoring_api, "build_scorer", unavailable)
    with pytest.raises(RuntimeError, match="requested backend unavailable"):
        api.score(api.RuneInput("THE"))


@pytest.mark.parametrize(
    ("call", "message"),
    (
        (lambda: api.score((1, 2, 3)), "candidate must be RuneInput"),
        (lambda: api.score_many(item for item in ()), "ordered sequence"),
        (lambda: api.score_many((api.RuneInput("THE"), object())), r"candidates\[1\]"),
        (lambda: api.score_many((), scoring={}), "scoring must be ScoringConfig"),
        (lambda: api.score_many((), text_direction="ltr"), "text_direction must be TextDirection"),
        (lambda: api.score_many((), compute_device="cpu"), "compute_device must be ComputeDevice"),
    ),
)
def test_standalone_scoring_rejects_untyped_inputs(call, message: str) -> None:
    with pytest.raises(TypeError, match=message):
        call()


def _golden_config(*, backend: api.advanced.ScorerBackend) -> api.ScoringConfig:
    return api.ScoringConfig(
        objective=api.advanced.ScoringObjective.average_log_probability(),
        character_lane_enabled=True,
        wli_lane_enabled=False,
        character_order_weights={2: 1.0},
        wli_order_weights={},
        average_window_policy=api.advanced.AverageWindowPolicy.FULL_TEXT,
        backend=backend,
    )


def _golden_candidates() -> tuple[api.RuneInput, api.RuneInput]:
    return (
        api.RuneInput("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG"),
        api.RuneInput("READ THE AETHER AND FOLLOW THE RABBIT"),
    )


@pytest.mark.full_assets
def test_numpy_cpu_golden_values_are_exactly_repeatable() -> None:
    require_full_lm_assets(
        models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=()
    )
    expected = (-6.315650463104248, -6.191677570343018)
    first = api.score_many(
        _golden_candidates(),
        scoring=_golden_config(backend=api.advanced.ScorerBackend.NUMPY),
    )
    second = api.score_many(
        _golden_candidates(),
        scoring=_golden_config(backend=api.advanced.ScorerBackend.NUMPY),
    )
    assert first == second
    assert first == pytest.approx(expected, rel=0.0, abs=1e-12)


@pytest.mark.full_assets
def test_standalone_context_matches_cipher_backed_numpy_scorer() -> None:
    from rdp.core.config.cipher import CipherConfig
    from rdp.core.engine.builders import build_scorer

    require_full_lm_assets(
        models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=()
    )
    candidate = _golden_candidates()[0]
    indices, _wli, _ = Runeglish.encode_english_to_runes(
        str(candidate.value), direction=Direction.LTR
    )
    config = _golden_config(backend=api.advanced.ScorerBackend.NUMPY)
    cipher_scorer = build_scorer(
        CipherConfig(
            ciphertext=indices,
            wli_data=None,
            key_length=None,
            encoding_dir=Direction.LTR,
            device=Device.CPU,
        ),
        config,
    )
    expected = float(cipher_scorer.score(indices, None))
    assert api.score(candidate, scoring=config) == expected


@pytest.mark.full_assets
@pytest.mark.torch
def test_torch_and_numpy_standalone_scores_use_accepted_tolerance() -> None:
    pytest.importorskip("torch")
    require_full_lm_assets(
        models=("char",), modes=("ltr",), poses=("nose",), ns=(2,), ecdf_stats=()
    )
    numpy_values = api.score_many(
        _golden_candidates(),
        scoring=_golden_config(backend=api.advanced.ScorerBackend.NUMPY),
    )
    torch_values = api.score_many(
        _golden_candidates(),
        scoring=_golden_config(backend=api.advanced.ScorerBackend.TORCH),
    )
    np.testing.assert_allclose(torch_values, numpy_values, rtol=0.0001, atol=1e-5)


@pytest.mark.full_assets
def test_wli_batch_is_unambiguous_when_batch_size_equals_plaintext_length() -> None:
    require_full_lm_assets(
        models=("char", "wli"),
        modes=("ltr",),
        poses=("nose",),
        ns=(2,),
        ecdf_stats=("logp",),
    )
    candidates = (
        api.RuneInput((2, 18), word_length_information=((0, 2), (1, 2))),
        api.RuneInput((16, 8), word_length_information=((0, 2), (1, 2))),
    )
    together = api.score_many(candidates)
    separate = tuple(api.score(candidate) for candidate in candidates)
    assert together == separate
