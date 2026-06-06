from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.core.types import ObjectiveFamily, ObjectiveSpec, Stat
from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit
from rune_decrypter_prime.scoring.ngram_hamming.report_only_telemetry import (
    N3CNormalReportTelemetryConfig,
    REPORT_DETAILS_KEY,
)
from tools.benchmarks.periodic_sub_trans.common.scorer_sidecar import append_scorer_report_jsonl
from tools.benchmarks.periodic_sub_trans.common.bench_solve_periodic_columnar_kaeding import (
    _preflight_known_key_roundtrip,
)


class _FakeRawScorer:
    def score(self, pt):
        arr = np.asarray(pt, dtype=np.float64).reshape(-1)
        if arr.size == 0:
            return float("-inf")
        return float(np.mean(arr))


def _make_cipher(period: int = 2, columns: int = 1) -> PeriodicColumnarCipher:
    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        wli_data=[],
        key_length=period * 29 + columns,
        period=period,
        columns=columns,
        alphabet_size=29,
        order="col_then_sub",
        encoding_dir=Direction.LTR,
        device=Device.CPU,
    )
    return PeriodicColumnarCipher(cfg)


def _identity_key(period: int = 2, columns: int = 1) -> np.ndarray:
    blocks = [np.arange(29, dtype=np.int16) for _ in range(period)]
    tail = np.arange(columns, dtype=np.int16)
    return np.concatenate(blocks + [tail], axis=0).astype(np.int16, copy=False)


class _FakePctScorerWithTelemetry:
    objective = ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10)

    def score_with_raw(self, pt, _wli):
        arr = np.asarray(pt, dtype=np.float64).reshape(-1)
        s = float(np.sum(arr))
        return s, s + 1.0

    def telemetry(self):
        return {"impl": "fake_pct", "model_root": Path("assets/lm")}

    def last_stats(self):
        return {"score_mean": 0.0, "score_std": 0.0}


def test_preflight_sidecar_writes_jsonl_report(tmp_path: Path) -> None:
    period, columns = 2, 1
    cipher = _make_cipher(period=period, columns=columns)
    key = _identity_key(period=period, columns=columns)
    pt_true = np.asarray([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.uint8)
    wli = [[i, len(pt_true)] for i in range(len(pt_true))]
    ct = cipher.encrypt_single(plaintext=pt_true, key=key)

    sidecar_path = tmp_path / "scorer_reports.jsonl"
    out = _preflight_known_key_roundtrip(
        cipher=cipher,
        ct_idx=ct,
        key_true=key,
        pt_true=pt_true,
        wli_list=wli,
        raw_full_scorer=_FakeRawScorer(),
        pct_scorer=_FakePctScorerWithTelemetry(),
        tier_name="unit",
        text_id=0,
        key_seed=0,
        scorer_report_jsonl=sidecar_path,
    )

    assert out["preflight_roundtrip_ok"] == 1
    lines = sidecar_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["report"]["objective_spec"]["family"] == "pct"
    assert row["report"]["objective_spec"]["stat"] == "logp"
    assert row["report"]["objective_spec"]["win"] == 10
    assert row["context"]["event"] == "gate0_preflight_oracle"


def test_sidecar_exports_opt_in_report_only_telemetry_without_changing_score(tmp_path: Path) -> None:
    hit = PhraseHit(
        candidate_id="candidate-a",
        chunk_id="chunk-a",
        damage_level="none",
        profile_id="BR_O3_conservative",
        ngram_order=3,
        dictionary_cut="normal",
        phrase_id="phrase-a",
        phrase_count=1,
        phrase_log_count=0.0,
        phrase_token_length=8,
        word_lengths=(1, 3, 4),
        word_hds=(0, 0, 0),
        total_phrase_hd=0,
        max_word_hd=0,
        mean_word_hd=0.0,
        normalised_phrase_hd=0.0,
        hit_start=2,
        hit_end=10,
    )
    expected_score = 12.5
    row = append_scorer_report_jsonl(
        tmp_path / "scorer_reports.jsonl",
        scorer=_FakePctScorerWithTelemetry(),
        score=expected_score,
        n3c_normal_candidate_id="candidate-a",
        n3c_normal_hits=(hit,),
        n3c_normal_report_config=N3CNormalReportTelemetryConfig(
            enabled=True,
            runtime_index_asset_id="runtime-v1",
            compact_asset_id="compact-v1",
            runtime_validation_status="pass",
        ),
    )

    assert row["report"]["score"] == expected_score
    telemetry = row["report"]["details"][REPORT_DETAILS_KEY]
    assert telemetry["hit_count"] == 1
    assert telemetry["production_rank_effect"] == "none"
