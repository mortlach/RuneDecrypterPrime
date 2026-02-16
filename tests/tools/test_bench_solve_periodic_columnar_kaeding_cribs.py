from __future__ import annotations

import numpy as np
import pytest

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.types import Device
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from tools.benchmarks.bench_solve_periodic_columnar_kaeding_cribs import (
    ALPHABET_SIZE,
    LONG14_DISAPPOINTMENT,
    ORDER,
    Mode,
    _profile,
    _encode_long_plaintext,
    _load_short_allowed_by_len,
    _preflight_oracle_crib,
    _slice_word_aligned,
    build_hard_crib_payload,
)


def test_short_word_tables_include_added_len3_entries():
    tables = _load_short_allowed_by_len(Direction.LTR, lengths=(1, 2, 3))
    s3 = {tuple(int(v) for v in row) for row in tables[3]}
    assert (11, 24, 4) in s3  # JAR
    assert (10, 1, 18) in s3  # IVE


def test_build_payload_short123_long14_real_slice_passes_oracle():
    pt_base, wli_base = _encode_long_plaintext(Direction.LTR)
    pt, wli, _off_used = _slice_word_aligned(pt_base, wli_base, length=300, offset_hint=211)
    mode = Mode(
        name="crib_stage_sparse",
        enforce_long14_word=True,
        fixed_from_long14_offsets=(),
        short_per_word_budget=((1, 1), (2, 1), (3, 1)),
    )
    tables = _load_short_allowed_by_len(Direction.LTR, lengths=(1, 2, 3))
    payload, meta = build_hard_crib_payload(
        mode=mode,
        direction=Direction.LTR,
        pt_idx=pt,
        wli=wli,
        short_allowed_by_len=tables,
    )
    assert payload is not None
    assert int(meta["hard_crib_rule_global_len"]) == 0
    assert int(meta["hard_crib_rule_per_word"]) >= 2
    assert int(meta["hard_crib_short_per_word_count"]) >= 1
    assert int(meta["hard_crib_long14_word_index"]) >= 0
    per_word = payload.get("per_word_allowed", {})
    assert int(meta["hard_crib_long14_word_index"]) in per_word
    assert per_word[int(meta["hard_crib_long14_word_index"])][0] == list(LONG14_DISAPPOINTMENT)
    _preflight_oracle_crib(hard_crib=payload, pt_true=pt, wli=wli)


def test_build_payload_long14_raises_when_slice_has_no_disappointment():
    pt_base, wli_base = _encode_long_plaintext(Direction.LTR)
    pt, wli, _off_used = _slice_word_aligned(pt_base, wli_base, length=300, offset_hint=0)
    mode = Mode(
        name="crib_long14",
        enforce_long14_word=True,
        fixed_from_long14_offsets=(),
    )
    tables = _load_short_allowed_by_len(Direction.LTR, lengths=(1, 2, 3))
    with pytest.raises(ValueError, match="long14 hit"):
        build_hard_crib_payload(
            mode=mode,
            direction=Direction.LTR,
            pt_idx=pt,
            wli=wli,
            short_allowed_by_len=tables,
        )


def test_profile_quick_30m_shape(monkeypatch):
    import tools.benchmarks.bench_solve_periodic_columnar_kaeding_cribs as mod

    monkeypatch.setattr(mod, "BENCH_PROFILE", "cribs_quick_30m")
    tiers, modes, offsets, seeds, solver = _profile()
    assert len(tiers) == 2
    assert [m.name for m in modes] == [
        "none",
        "crib_anchor1",
        "crib_anchor1_seedpool",
        "crib_anchor1_seedfilter",
    ]
    assert offsets == [211]
    assert seeds == [111]
    assert str(solver.name) == "kaeding"


@pytest.mark.tier_a
def test_runapi_with_real_crib_payload_enables_runtime_crib_without_all_reject():
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

    require_full_lm_assets(models=("char",), modes=("ltr",), poses=("nose",), ns=(3, 4), ecdf_stats=("logp",))

    pt_base, wli_base = _encode_long_plaintext(Direction.LTR)
    pt_idx, wli, _off_used = _slice_word_aligned(pt_base, wli_base, length=400, offset_hint=211)
    # Mild, real-data crib: fixed characters at known positions inside the unique long-14 word.
    # This is strong enough to constrain search, but not so strict that every candidate is rejected.
    payload = {
        "enabled": True,
        "mode": "hard",
        "require_wli_for_word_rules": True,
        "fixed_chars": {
            158: [23],  # long14 start in this slice
            163: [13],
            168: [19],
            171: [16],
        },
        "per_word_allowed": {},
        "global_allowed_by_len": {},
    }
    _preflight_oracle_crib(hard_crib=payload, pt_true=pt_idx, wli=wli)

    tier_period, tier_columns = 7, 5
    key_len = tier_period * ALPHABET_SIZE + tier_columns
    rng = np.random.default_rng(111)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=tier_period, A=ALPHABET_SIZE, columns=tier_columns)
    key_true = keyops.random(rng).astype(np.int16, copy=False)
    cipher_cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=tier_period,
        columns=tier_columns,
        alphabet_size=ALPHABET_SIZE,
        key_length=key_len,
        order=ORDER,
        encoding_dir=Direction.LTR,
        wli_data=[],
        device=Device.CPU,
    )
    cipher = PeriodicColumnarCipher(cipher_cfg)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key_true)

    solver = SolverSpec.kaeding(
        steps=50,
        restarts=1,
        seed_restarts=1,
        seed_selection_metric="raw",
        inner_batch=64,
        col_every=8,
        col_batch=24,
        use_raw_score=True,
        top_k=16,
        print_progress=False,
        seed=2026,
    )
    cipher_spec = by_name.cipher(
        "periodic_columnar",
        period=tier_period,
        columns=tier_columns,
        alphabet_size=ALPHABET_SIZE,
        order=ORDER,
    )
    key_spec = KeySpec.periodic_columnar(period=tier_period, columns=tier_columns, alphabet_size=ALPHABET_SIZE)
    sol = run(
        text=ct_idx.tolist(),
        wli_data=wli,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver,
        device=Device.CPU,
        scorer_params={
            "objective": "pct.logp.win10",
            "include_char": True,
            "use_word_breaks": False,
            "char_weights": {3: 0.5, 4: 0.5},
            "wli_weights": {},
            "encoding_dir": Direction.LTR,
            "hard_crib": payload,
            },
            telemetry_on=True,
            encoding_dir=Direction.LTR,
            force_no_wli=False,
            initial_keys=[key_true.astype(np.int16, copy=False).tolist()],
        )
    tel = getattr(sol, "meta", {}).get("telemetry", {})
    hc = getattr(sol, "meta", {}).get("hard_crib", {})
    assert bool(tel.get("crib_enabled", False)) is True
    assert int(tel.get("crib_pass_total", 0) or 0) + int(tel.get("crib_reject_total", 0) or 0) > 0
    assert bool(hc.get("all_rejected", False)) is False
