"""Score plaintext candidates without constructing a cipher or solver."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from rdp.api.normalize import normalize_rune_input
from rdp.api.run_spec import RuneInput
from rdp.core.config.scorer_context import ScorerContext
from rdp.core.config.scoring import ScoringConfig, SpanHammingMode
from rdp.core.engine.builders import build_scorer
from rdp.core.types import ComputeDevice, Device, Direction, TextDirection


def _materialize_candidate(
    candidate: RuneInput,
    *,
    text_direction: TextDirection,
) -> tuple[np.ndarray, list[list[int]] | None]:
    if candidate.format is None:
        raise RuntimeError("RuneInput format was not resolved")
    return normalize_rune_input(
        candidate.value,
        input_format=candidate.format.value,
        direction=text_direction,
        wli_data=candidate.word_length_information,
    )


def score(
    candidate: RuneInput,
    *,
    scoring: ScoringConfig | None = None,
    text_direction: TextDirection = TextDirection.LTR,
    compute_device: ComputeDevice = ComputeDevice.CPU,
) -> float:
    """Score one plaintext candidate without a cipher, key space, or solver.

    A score ranks candidates under the selected configuration; it is not a
    probability that a candidate is correct.
    """
    if not isinstance(candidate, RuneInput):
        raise TypeError("candidate must be RuneInput")
    return score_many(
        (candidate,),
        scoring=scoring,
        text_direction=text_direction,
        compute_device=compute_device,
    )[0]


def score_many(
    candidates: Sequence[RuneInput],
    *,
    scoring: ScoringConfig | None = None,
    text_direction: TextDirection = TextDirection.LTR,
    compute_device: ComputeDevice = ComputeDevice.CPU,
) -> tuple[float, ...]:
    """Score candidates and return one float per input in input order.

    Candidate lengths and word boundaries may differ. Inputs are not mutated.
    An empty sequence returns immediately without loading scorer assets.
    """
    if not isinstance(candidates, Sequence) or isinstance(
        candidates, (str, bytes, bytearray)
    ):
        raise TypeError("candidates must be an ordered sequence of RuneInput")
    if scoring is not None and not isinstance(scoring, ScoringConfig):
        raise TypeError("scoring must be ScoringConfig or None")
    if not isinstance(text_direction, TextDirection):
        raise TypeError("text_direction must be TextDirection")
    if not isinstance(compute_device, ComputeDevice):
        raise TypeError("compute_device must be ComputeDevice")

    values = tuple(candidates)
    for index, candidate in enumerate(values):
        if not isinstance(candidate, RuneInput):
            raise TypeError(f"candidates[{index}] must be RuneInput")
    if not values:
        return ()

    config = scoring if scoring is not None else ScoringConfig()
    materialized = tuple(
        _materialize_candidate(candidate, text_direction=text_direction)
        for candidate in values
    )
    calibrated = config.span_hamming_mode is SpanHammingMode.CALIBRATED
    requires_wli = not calibrated and any(
        channel == "wli"
        for channel, _order, _weight in config.effective_lm_model_weights()
    )
    for index, (_, wli) in enumerate(materialized):
        if wli is None and requires_wli:
            raise ValueError(
                f"candidates[{index}].word_length_information is required "
                "when the WLI lane is enabled"
            )

    context = ScorerContext(
        encoding_dir=(
            Direction.LTR if text_direction is TextDirection.LTR else Direction.RTL
        ),
        device=(Device.CPU if compute_device is ComputeDevice.CPU else Device.CUDA),
    )
    scorer = build_scorer(context, config)
    results = [0.0] * len(values)
    groups: dict[
        tuple[int, bool],
        list[tuple[int, np.ndarray, list[list[int]] | None]],
    ] = {}

    for index, (indices, wli) in enumerate(materialized):
        if wli is None and calibrated:
            results[index] = float(scorer.score(indices, None))
            continue
        groups.setdefault((len(indices), wli is not None), []).append(
            (index, indices, wli)
        )

    for group in groups.values():
        # The legacy NumPy batch API cannot distinguish shared (L, 2) WLI from
        # per-item (B, L, 2) WLI when B == L. Score that rare shape itemwise.
        if group[0][2] is not None and len(group) == len(group[0][1]):
            scores = [
                scorer.score(indices, np.asarray(wli, dtype=np.uint8))
                for _, indices, wli in group
            ]
            for (index, _, _), value in zip(group, scores):
                results[index] = float(value)
            continue
        plaintexts = np.asarray(
            [indices for _, indices, _ in group], dtype=np.uint8
        )
        wlis = None
        if group[0][2] is not None:
            wlis = np.asarray([wli for _, _, wli in group], dtype=np.uint8)
        scores = scorer.batch_score(plaintexts, wlis)
        for (index, _, _), value in zip(group, scores):
            results[index] = float(value)

    return tuple(results)


__all__ = ["score", "score_many"]
