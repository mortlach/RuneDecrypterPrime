from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.benchmarks.periodic_sub_trans.col_then_sub import runner as col_runner
from tools.benchmarks.periodic_sub_trans.common.runner_types import Tier
from tools.benchmarks.periodic_sub_trans.sub_then_col import runner as sub_runner


pytestmark = pytest.mark.tier_a


class _FakePeriodicCipher:
    def __init__(self, _cfg):
        pass

    def encrypt_single(self, plaintext, key):
        pt = np.asarray(plaintext, dtype=np.uint8).reshape(-1)
        return np.asarray((pt + 1) % 29, dtype=np.uint8)

    def decrypt_single(self, ciphertext, key):
        ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
        return np.asarray((ct - 1) % 29, dtype=np.uint8)


class _FakeKeyOps:
    def __init__(self, K: int, period: int, A: int, columns: int):
        self._k = int(K)
        self._a = int(A)

    def random(self, rng):
        vals = rng.integers(0, self._a, size=self._k)
        return np.asarray(vals, dtype=np.int16)


def _fake_run(*, text, initial_keys=None, **_kwargs):
    key = list(map(int, (initial_keys[0] if initial_keys else [0, 1, 2, 3])))
    score = float(sum(key)) / float(max(1, len(key)))
    return SimpleNamespace(
        key=key,
        plaintext_idx=list(map(int, text)),
        score=score,
        meta={"work": {"evals": 1}, "top_keys": [key]},
    )


def _fake_decrypt_and_score_keys_chunked(*, ciphertext, keys, **_kwargs):
    ct = np.asarray(ciphertext, dtype=np.uint8).reshape(-1)
    pts = []
    scores = []
    for key in keys:
        k = list(map(int, key))
        pts.append(np.asarray((ct + (sum(k) % 3)) % 29, dtype=np.uint8))
        scores.append(float(sum(k)) / float(max(1, len(k))))
    return np.asarray(pts, dtype=np.uint8), np.asarray(scores, dtype=float), {"evals": len(keys)}


def _fake_score_plaintexts_chunked(*, plaintexts, **_kwargs):
    scores = [float(np.asarray(pt, dtype=np.uint8).sum() % 101) / 101.0 for pt in plaintexts]
    return np.asarray(scores, dtype=float), {"evals": len(plaintexts)}


def _patch_common_runner_surface(monkeypatch: pytest.MonkeyPatch, module, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(module, "_apply_run_mode", lambda: None)
    monkeypatch.setattr(module, "_apply_runtime_overrides", lambda: None)
    if hasattr(module, "_resolve_stageab_scorer_profile"):
        monkeypatch.setattr(module, "_resolve_stageab_scorer_profile", lambda: None)
    monkeypatch.setattr(module, "_repo_root", lambda: run_dir.parent)
    monkeypatch.setattr(module, "_git_short", lambda: "test")
    monkeypatch.setattr(module, "make_flavor_run_dir", lambda **_kwargs: run_dir)
    monkeypatch.setattr(module, "_load_proven_solved_index", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(module, "_append_csv_row_common", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module, "write_stage_engine_contract_artifacts", lambda **_kwargs: {"stage_specs_path": run_dir / "stage_specs.json", "policy_spec_path": run_dir / "policy_spec.json"})
    monkeypatch.setattr(module, "make_stage_engine_trace_emitter", lambda **_kwargs: (lambda **__kwargs: None))
    monkeypatch.setattr(module, "PeriodicColumnarCipher", _FakePeriodicCipher)
    monkeypatch.setattr(module, "PeriodicSubstitutionCipher", _FakePeriodicCipher)
    monkeypatch.setattr(module, "PeriodicStructuredMatrixKeyOps", _FakeKeyOps)
    monkeypatch.setattr(module, "build_scorer", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(module, "run", _fake_run)
    monkeypatch.setattr(module, "decrypt_and_score_keys_chunked", _fake_decrypt_and_score_keys_chunked)
    if hasattr(module, "score_plaintexts_chunked"):
        monkeypatch.setattr(module, "score_plaintexts_chunked", _fake_score_plaintexts_chunked)
    monkeypatch.setattr(module.base, "_require_assets", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(module.base, "_encode_long_plaintext", lambda _direction: (np.asarray([1, 2, 3, 4, 5, 6, 7, 8] * 8, dtype=np.uint8), np.asarray([[0, 1]], dtype=np.uint8)))
    monkeypatch.setattr(
        module.base,
        "_slice_word_aligned",
        lambda pt_base, _wli_base, length, offset_hint: (np.asarray(pt_base[: int(length)], dtype=np.uint8), [[0, int(length)]], int(offset_hint)),
    )
    monkeypatch.setattr(module.base, "_match_ratio", lambda *_args, **_kwargs: 0.125)
    if hasattr(module, "_preview_latin"):
        monkeypatch.setattr(module, "_preview_latin", lambda pt, _wli: " ".join(map(str, list(pt)[:12])))
    if hasattr(module, "_print_stage_preview"):
        monkeypatch.setattr(module, "_print_stage_preview", lambda **_kwargs: None)
    if hasattr(module, "_oracle_score_for_stage"):
        monkeypatch.setattr(module, "_oracle_score_for_stage", lambda **_kwargs: (0.2, -1.0, "pct.logp.win10"))
    monkeypatch.setattr(module, "FORCE_RERUN_PROVEN", True)
    monkeypatch.setattr(module, "AUTOSKIP_PROVEN", False)
    monkeypatch.setattr(module, "TIERS", [Tier("parity_tier", 5, 1, 24)])
    monkeypatch.setattr(module, "TEXT_OFFSETS", [0])
    monkeypatch.setattr(module, "KEY_SEEDS", [111])


def _run_and_load_summary(module, run_dir: Path) -> dict:
    module.main()
    summary_path = run_dir / "summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def test_sub_then_col_runner_fixed_seed_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(sub_runner, "enumerate_column_permutations", lambda *_args, **_kwargs: [(0,)])
    monkeypatch.setattr(sub_runner, "undo_columnar_with_perm", lambda ct, perm: np.asarray(ct, dtype=np.uint8))
    monkeypatch.setattr(sub_runner, "make_periodic_seed_pool", lambda *_args, **_kwargs: [[0] * (5 * 29)])
    run1 = tmp_path / "sub_run_1"
    _patch_common_runner_surface(monkeypatch, sub_runner, run1)
    s1 = _run_and_load_summary(sub_runner, run1)

    run2 = tmp_path / "sub_run_2"
    _patch_common_runner_surface(monkeypatch, sub_runner, run2)
    s2 = _run_and_load_summary(sub_runner, run2)
    assert s1 == s2


def test_col_then_sub_runner_fixed_seed_parity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(col_runner, "make_periodic_seed_pool_col_then_sub", lambda *_args, **_kwargs: [[0] * (5 * 29)])
    monkeypatch.setattr(col_runner, "make_tail_seed_pool", lambda *_args, **_kwargs: [[0]])
    run1 = tmp_path / "col_run_1"
    _patch_common_runner_surface(monkeypatch, col_runner, run1)
    monkeypatch.setattr(col_runner, "TIERS", [Tier("parity_tier", 5, 1, 24)])
    s1 = _run_and_load_summary(col_runner, run1)

    run2 = tmp_path / "col_run_2"
    _patch_common_runner_surface(monkeypatch, col_runner, run2)
    monkeypatch.setattr(col_runner, "TIERS", [Tier("parity_tier", 5, 1, 24)])
    s2 = _run_and_load_summary(col_runner, run2)
    assert s1 == s2
