from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pytest

# Solve scripts now live under top-level solving/<puzzle>/.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from solving.finster import runic_v3_pipeline as rv3


def _attempt_row(
    *,
    profile: str,
    group: str,
    metric: float,
    seed_index: int,
    period: int | str = "",
    columns: int | str = "",
    order: str = "",
    stage: str = "micro_scout",
) -> rv3.AttemptResult:
    return rv3.AttemptResult(
        row=dict(
            profile=profile,
            hypothesis_group=group,
            threshold_metric=metric,
            seed_index=seed_index,
            period=period,
            columns=columns,
            order=order,
            stage=stage,
        ),
        key=None,
        hypothesis_group=group,
    )


def test_exact_tail_uses_threshold_objective_label() -> None:
    class DummyDevice:
        CPU = "cpu"

    class DummyCipherConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyScoringConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class DummyCipher:
        def __init__(self, cfg):
            self.cfg = cfg

        def decrypt_single(self, ciphertext, key):
            return np.asarray(ciphertext, dtype=np.uint8)

    class DummyScorer:
        def score(self, pt, _):
            return float(np.mean(np.asarray(pt, dtype=np.float64)))

    class DummyR:
        @staticmethod
        def pos_to_latin(xs):
            return "A" * len(xs)

    row = dict(
        profile=rv3.PROFILE_A,
        hypothesis_group="product",
        period=1,
        columns=2,
        order="sub_then_col",
        seed=123,
        seed_index=0,
        seed_offset=0,
        retry_count=0,
        threshold_metric=0.1,
    )
    cand = rv3.AttemptResult(row=row, key=[0, 1, 2, 0, 1], hypothesis_group="product")
    trace: list[dict[str, object]] = []
    out = rv3._run_exact_tail(
        candidate_rows=[cand],
        profile=rv3.PROFILE_A,
        ct_idx=np.asarray([0, 1, 2, 0, 1], dtype=np.uint8),
        direction="ltr",
        alphabet_size=3,
        preview_chars=16,
        Device=DummyDevice,
        PeriodicColumnarCipher=DummyCipher,
        CipherConfig=DummyCipherConfig,
        ScoringConfig=DummyScoringConfig,
        build_scorer=lambda _cfg, _sc: DummyScorer(),
        R=DummyR,
        run_started_ts=time.time(),
        panic_seconds=60.0,
        cipher_id="t",
        decision_trace=trace,
    )
    assert out
    assert out[0].row["threshold_name"] == rv3.THRESHOLD_OBJECTIVE


def test_run_pipeline_restores_stdout_on_forced_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original = sys.stdout
    log_path = tmp_path / "forced.log"

    def _boom(_cfg: rv3.CipherRunConfig) -> None:
        tee = rv3._Tee(log_path)
        sys.stdout = tee  # type: ignore
        print("forced")
        raise RuntimeError("boom")

    monkeypatch.setattr(rv3, "_run_pipeline_v3_impl", _boom)
    cfg = rv3.CipherRunConfig(cipher_id="x", ciphertext_file="runic_a.txt", period_priors=[7], output_root=tmp_path / "out")
    with pytest.raises(RuntimeError):
        rv3.run_pipeline_v3(cfg)
    assert sys.stdout is original
    assert "forced" in log_path.read_text(encoding="utf-8")


def test_candidate_seed_gain_stats_is_candidate_specific() -> None:
    rows = [
        _attempt_row(profile=rv3.PROFILE_A, group="periodic_substitution", metric=0.50, seed_index=0, period=7),
        _attempt_row(profile=rv3.PROFILE_A, group="periodic_substitution", metric=0.50, seed_index=1, period=7),
        _attempt_row(profile=rv3.PROFILE_A, group="product", metric=0.60, seed_index=0, period=7, columns=3, order="sub_then_col"),
        _attempt_row(profile=rv3.PROFILE_A, group="product", metric=0.10, seed_index=1, period=7, columns=3, order="sub_then_col"),
        _attempt_row(profile=rv3.PROFILE_A, group="product", metric=0.20, seed_index=0, period=7, columns=4, order="sub_then_col"),
        _attempt_row(profile=rv3.PROFILE_A, group="product", metric=0.70, seed_index=1, period=7, columns=4, order="sub_then_col"),
    ]
    stats = rv3._candidate_seed_gain_stats(rows, rv3.PROFILE_A)
    assert stats["candidate"] == {"profile": rv3.PROFILE_A, "period": 7, "columns": 4, "order": "sub_then_col"}
    gains = [r["gain"] for r in stats["per_seed"]]
    assert gains == [-0.3, 0.19999999999999996]
    assert stats["stable"] == 0


def test_attempt_key_tuple_counts_unique_attempts() -> None:
    row_a = dict(profile="A", hypothesis="x", period=7, columns=3, order="sub_then_col", seed=1, retry_count=0)
    row_b = dict(profile="A", hypothesis="x", period=7, columns=3, order="sub_then_col", seed=1, retry_count=0, score=-1.0)
    row_c = dict(profile="A", hypothesis="x", period=7, columns=3, order="sub_then_col", seed=1, retry_count=1)
    uniq = {rv3._attempt_key_tuple(row_a), rv3._attempt_key_tuple(row_b), rv3._attempt_key_tuple(row_c)}
    assert len(uniq) == 2


def test_canonical_config_hash_is_deterministic_and_nan_rejected() -> None:
    cfg1 = {"b": 2, "a": [1.2345678901234, {"x": 7}]}
    cfg2 = {"a": [1.2345678901234, {"x": 7}], "b": 2}
    payload1, hash1 = rv3._canonical_config_hash(cfg1)
    payload2, hash2 = rv3._canonical_config_hash(cfg2)
    assert payload1 == payload2
    assert hash1 == hash2
    with pytest.raises(ValueError):
        rv3._canonical_config_hash({"x": float("nan")})
