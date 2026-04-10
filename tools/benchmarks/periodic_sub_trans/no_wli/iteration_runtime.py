from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping

import numpy as np

from rune_decrypter_prime.api import Direction
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import Device
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_io import (
    validate_fixed_instance_payload,
)
from tools.benchmarks.periodic_sub_trans.no_wli.fixed_instance_models import (
    FixedCipherInstanceSpec,
)


def _coerce_fixed_instance_spec(
    fixed_instance_spec: FixedCipherInstanceSpec | Mapping[str, Any] | None,
) -> FixedCipherInstanceSpec:
    if fixed_instance_spec is None:
        raise ValueError(
            "fixed_instance_spec is required when INSTANCE_INPUT_MODE='fixed_ciphertext'"
        )
    if isinstance(fixed_instance_spec, FixedCipherInstanceSpec):
        return fixed_instance_spec
    return validate_fixed_instance_payload(
        dict(fixed_instance_spec),
        source="iteration_runtime.fixed_instance_spec",
    )


def _build_cipher_configs(
    *,
    tier_period: int,
    tier_columns: int,
    alphabet_size: int,
    order: str,
    direction: Direction,
) -> tuple[int, CipherConfig, CipherConfig]:
    key_len = int(int(tier_period) * int(alphabet_size) + int(tier_columns))
    cfg_full = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=int(tier_period),
        columns=int(tier_columns),
        alphabet_size=int(alphabet_size),
        key_length=int(key_len),
        order=str(order),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    cfg_sub = CipherConfig(
        name="periodic_substitution",
        ciphertext=[],
        period=int(tier_period),
        alphabet_size=int(alphabet_size),
        key_length=int(tier_period) * int(alphabet_size),
        encoding_dir=direction,
        wli_data=[],
        device=Device.CPU,
    )
    return int(key_len), cfg_full, cfg_sub


def build_iteration_runtime(
    *,
    tier_period: int,
    tier_columns: int,
    pt_idx: np.ndarray,
    key_seed: int,
    alphabet_size: int,
    order: str,
    direction: Direction,
    scorer_stage1_base: Mapping[str, Any],
    scorer_stage2_base: Mapping[str, Any],
    scorer_impl: str,
    pipeline_run_mode: str,
    stage3_two_phase_enabled: bool,
    scoring_experiment_profile: str,
    span_assets_dir: Path,
    stage2_judge_policy_value: str,
    stage2_exact_max_columns: int,
    stage2_exact_two_pass: bool,
    stage2_pass1_primary_char_weights: Mapping[int, float],
    stage2_pass1_fallback_char_weights: Mapping[int, float],
    canonical_run_mode_fn: Callable[[str | None], str],
    is_adaptive_focus_mode_fn: Callable[[str | None], bool],
    stage3_search_cfg_fn: Callable[..., Dict[str, Any]],
    build_stage3_experiment_cfg_fn: Callable[..., Dict[str, Any]],
    build_word_ngram_report_cfg_fn: Callable[..., Dict[str, Any] | None],
    guard_no_ecdf_usage_fn: Callable[..., None],
    instance_input_mode: str = "generated",
    fixed_instance_spec: FixedCipherInstanceSpec | Mapping[str, Any] | None = None,
    search_seed: int | None = None,
) -> Dict[str, Any]:
    mode = str(instance_input_mode).strip().lower()
    pt_idx_runtime = np.asarray(pt_idx, dtype=np.uint8).reshape(-1)
    wli_runtime: list[list[int]] | None = None
    instance_fixture_id = ""
    instance_source_key_seed = int(key_seed)
    search_seed_value = int(search_seed if search_seed is not None else key_seed)

    if mode == "generated":
        key_len, cfg_full, cfg_sub = _build_cipher_configs(
            tier_period=int(tier_period),
            tier_columns=int(tier_columns),
            alphabet_size=int(alphabet_size),
            order=str(order),
            direction=direction,
        )
        rng = np.random.default_rng(int(key_seed))
        keyops = PeriodicStructuredMatrixKeyOps(
            K=int(key_len),
            period=int(tier_period),
            A=int(alphabet_size),
            columns=int(tier_columns),
        )
        key_true = keyops.random(rng).astype(np.int16, copy=False)
        full_cipher = PeriodicColumnarCipher(cfg_full)
        sub_cipher = PeriodicSubstitutionCipher(cfg_sub)
        ct_idx = full_cipher.encrypt_single(
            plaintext=np.asarray(pt_idx_runtime, dtype=np.uint8),
            key=key_true,
        )
    elif mode == "fixed_ciphertext":
        spec = _coerce_fixed_instance_spec(fixed_instance_spec)
        spec_direction = Direction(str(spec.direction))
        if int(spec.period) != int(tier_period):
            raise ValueError(
                f"Fixed instance period mismatch: spec={spec.period} tier={tier_period}"
            )
        if int(spec.columns) != int(tier_columns):
            raise ValueError(
                f"Fixed instance columns mismatch: spec={spec.columns} tier={tier_columns}"
            )
        if int(spec.alphabet_size) != int(alphabet_size):
            raise ValueError(
                "Fixed instance alphabet_size mismatch: "
                f"spec={spec.alphabet_size} runtime={alphabet_size}"
            )
        if str(spec.order) != str(order):
            raise ValueError(
                f"Fixed instance order mismatch: spec={spec.order!r} runtime={order!r}"
            )
        if spec_direction != direction:
            raise ValueError(
                "Fixed instance direction mismatch: "
                f"spec={spec.direction!r} runtime={direction.value!r}"
            )
        if not np.array_equal(
            pt_idx_runtime,
            np.asarray(spec.target_plaintext_idx, dtype=np.uint8),
        ):
            raise ValueError(
                "Fixed instance target_plaintext_idx does not match runtime pt_idx"
            )
        key_len, cfg_full, cfg_sub = _build_cipher_configs(
            tier_period=int(spec.period),
            tier_columns=int(spec.columns),
            alphabet_size=int(spec.alphabet_size),
            order=str(spec.order),
            direction=spec_direction,
        )
        key_true = np.asarray(spec.true_key_idx, dtype=np.int16).reshape(-1)
        full_cipher = PeriodicColumnarCipher(cfg_full)
        sub_cipher = PeriodicSubstitutionCipher(cfg_sub)
        pt_idx_runtime = np.asarray(spec.target_plaintext_idx, dtype=np.uint8).reshape(-1)
        ct_idx = np.asarray(spec.ciphertext_idx, dtype=np.uint8).reshape(-1)
        wli_runtime = [[int(a), int(b)] for a, b in spec.target_wli]
        instance_fixture_id = str(spec.instance_fixture_id)
        instance_source_key_seed = int(spec.source_key_seed)
        roundtrip_plaintext = np.asarray(
            full_cipher.decrypt_single(ciphertext=ct_idx, key=key_true),
            dtype=np.uint8,
        ).reshape(-1)
        if not np.array_equal(roundtrip_plaintext, pt_idx_runtime):
            raise RuntimeError(
                "Fixed instance roundtrip failed: decrypt(ciphertext,true_key) "
                "did not match stored target_plaintext_idx"
            )
        calc_ct_idx = np.asarray(
            full_cipher.encrypt_single(plaintext=pt_idx_runtime, key=key_true),
            dtype=np.uint8,
        ).reshape(-1)
        if not np.array_equal(calc_ct_idx, ct_idx):
            raise RuntimeError(
                "Fixed instance roundtrip failed: encrypt(target_plaintext_idx,true_key) "
                "did not match stored ciphertext_idx"
            )
    else:
        raise ValueError(
            f"Unsupported INSTANCE_INPUT_MODE={instance_input_mode!r}; "
            "expected generated|fixed_ciphertext"
        )

    sub_len = int(int(tier_period) * int(alphabet_size))
    true_sub = key_true[:sub_len].astype(np.int16, copy=False)
    pt_stage1_oracle = np.asarray(
        sub_cipher.decrypt_single(ciphertext=ct_idx, key=true_sub),
        dtype=np.uint8,
    ).reshape(-1)

    scorer_stage1 = dict(scorer_stage1_base, encoding_dir=direction)
    scorer_stage2 = dict(scorer_stage2_base, encoding_dir=direction)

    mode_canonical_runtime = str(canonical_run_mode_fn(pipeline_run_mode))
    stage3_phase_switch_enabled = bool(
        bool(is_adaptive_focus_mode_fn(mode_canonical_runtime))
        and bool(stage3_two_phase_enabled)
    )
    stage3_phaseA_experiment = str(scoring_experiment_profile or "off").strip().lower()
    stage3_phaseB_experiment = str(scoring_experiment_profile or "off").strip().lower()
    if bool(stage3_phase_switch_enabled):
        stage3_phaseA_experiment = "a_baseline"
        stage3_phaseB_experiment = "c_min_late"

    scorer_stage3_search = stage3_search_cfg_fn(direction=direction)
    scorer_full = build_stage3_experiment_cfg_fn(
        profile_name=stage3_phaseB_experiment,
        direction=direction,
        span_assets_dir=span_assets_dir,
        disable_char_pct_gate=bool(stage3_phase_switch_enabled),
    )
    scorer_basin_judge = build_stage3_experiment_cfg_fn(
        profile_name=stage3_phaseB_experiment,
        direction=direction,
        span_assets_dir=span_assets_dir,
        disable_char_pct_gate=True,
    )
    scorer_stage3_phaseA = dict(scorer_stage3_search)
    scorer_stage3_phaseB = dict(scorer_stage3_search)

    scorer_stage1_runtime = build_scorer(cfg_sub, ScoringConfig(**scorer_stage1))
    scorer_stage2_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_stage2))
    scorer_stage3_search_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_stage3_search))
    scorer_full_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_full))
    scorer_basin_judge_runtime = build_scorer(cfg_full, ScoringConfig(**scorer_basin_judge))
    scorer_word_ngram_report_runtime = None
    scorer_word_ngram_report_cfg = build_word_ngram_report_cfg_fn(
        base_cfg=dict(scorer_basin_judge),
        direction=direction,
    )
    if scorer_word_ngram_report_cfg is not None:
        scorer_word_ngram_report_runtime = build_scorer(
            cfg_full,
            ScoringConfig(**scorer_word_ngram_report_cfg),
        )
    scorer_stage3_phaseA_runtime = scorer_stage3_search_runtime

    stage2_judge_policy = str(stage2_judge_policy_value).strip().lower()
    if stage2_judge_policy not in {"search_only", "stage3_judge"}:
        raise ValueError(
            f"Unsupported STAGE2_JUDGE_POLICY={stage2_judge_policy_value!r}; "
            "expected search_only|stage3_judge"
        )
    if stage2_judge_policy == "search_only":
        scorer_stage2_judge_runtime = scorer_stage2_runtime
        scorer_stage2_judge_cfg = dict(scorer_stage2)
    else:
        scorer_stage2_judge_runtime = scorer_full_runtime
        scorer_stage2_judge_cfg = dict(scorer_full)

    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_stage1_runtime,
        scorer_cfg=scorer_stage1,
        stage_label="stage1",
    )
    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_stage2_runtime,
        scorer_cfg=scorer_stage2,
        stage_label="stage2",
    )
    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_stage3_search_runtime,
        scorer_cfg=scorer_stage3_search,
        stage_label="stage3_search",
    )
    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_stage2_judge_runtime,
        scorer_cfg=scorer_stage2_judge_cfg,
        stage_label="stage2_judge",
    )
    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_stage3_phaseA_runtime,
        scorer_cfg=scorer_stage3_phaseA,
        stage_label="stage3_phaseA",
    )
    guard_no_ecdf_usage_fn(
        scorer_runtime=scorer_basin_judge_runtime,
        scorer_cfg=scorer_basin_judge,
        stage_label="stage3_basin_judge",
    )
    if scorer_word_ngram_report_runtime is not None:
        guard_no_ecdf_usage_fn(
            scorer_runtime=scorer_word_ngram_report_runtime,
            scorer_cfg=scorer_word_ngram_report_cfg,
            stage_label="word_ngram_report",
        )

    scorer_stage2_pass1_primary_runtime = None
    scorer_stage2_pass1_fallback_runtime = None
    if int(tier_columns) <= int(stage2_exact_max_columns) and bool(stage2_exact_two_pass):
        stage2_objective = str(scorer_stage2.get("objective", "pct.logp.win10"))
        stage2_avg_policy = scorer_stage2.get("avg_window_policy", None)
        scorer_stage2_pass1_primary = dict(
            objective=stage2_objective,
            include_char=True,
            use_word_breaks=False,
            char_weights=dict(stage2_pass1_primary_char_weights),
            wli_weights={},
            encoding_dir=direction,
            impl=scorer_impl,
        )
        if stage2_avg_policy is not None:
            scorer_stage2_pass1_primary["avg_window_policy"] = str(stage2_avg_policy)
        scorer_stage2_pass1_primary_runtime = build_scorer(
            cfg_full,
            ScoringConfig(**scorer_stage2_pass1_primary),
        )
        guard_no_ecdf_usage_fn(
            scorer_runtime=scorer_stage2_pass1_primary_runtime,
            scorer_cfg=scorer_stage2_pass1_primary,
            stage_label="stage2_pass1_primary",
        )
        if dict(stage2_pass1_fallback_char_weights) and (
            dict(stage2_pass1_fallback_char_weights)
            != dict(stage2_pass1_primary_char_weights)
        ):
            scorer_stage2_pass1_fallback = dict(
                objective=stage2_objective,
                include_char=True,
                use_word_breaks=False,
                char_weights=dict(stage2_pass1_fallback_char_weights),
                wli_weights={},
                encoding_dir=direction,
                impl=scorer_impl,
            )
            if stage2_avg_policy is not None:
                scorer_stage2_pass1_fallback["avg_window_policy"] = str(
                    stage2_avg_policy
                )
            scorer_stage2_pass1_fallback_runtime = build_scorer(
                cfg_full,
                ScoringConfig(**scorer_stage2_pass1_fallback),
            )
            guard_no_ecdf_usage_fn(
                scorer_runtime=scorer_stage2_pass1_fallback_runtime,
                scorer_cfg=scorer_stage2_pass1_fallback,
                stage_label="stage2_pass1_fallback",
            )

    return dict(
        instance_input_mode=str(mode),
        instance_fixture_id=str(instance_fixture_id),
        instance_source_key_seed=int(instance_source_key_seed),
        search_seed=int(search_seed_value),
        key_len=int(key_len),
        key_true=key_true,
        cfg_full=cfg_full,
        cfg_sub=cfg_sub,
        full_cipher=full_cipher,
        sub_cipher=sub_cipher,
        ct_idx=ct_idx,
        pt_idx=np.asarray(pt_idx_runtime, dtype=np.uint8).copy(),
        wli=(list(wli_runtime) if wli_runtime is not None else None),
        sub_len=int(sub_len),
        true_sub=true_sub,
        pt_stage1_oracle=pt_stage1_oracle,
        scorer_stage1=scorer_stage1,
        scorer_stage2=scorer_stage2,
        stage3_phase_switch_enabled=bool(stage3_phase_switch_enabled),
        stage3_phaseA_experiment=str(stage3_phaseA_experiment),
        stage3_phaseB_experiment=str(stage3_phaseB_experiment),
        scorer_stage3_search=scorer_stage3_search,
        scorer_full=scorer_full,
        scorer_basin_judge=scorer_basin_judge,
        scorer_stage3_phaseA=scorer_stage3_phaseA,
        scorer_stage3_phaseB=scorer_stage3_phaseB,
        scorer_stage1_runtime=scorer_stage1_runtime,
        scorer_stage2_runtime=scorer_stage2_runtime,
        scorer_stage3_search_runtime=scorer_stage3_search_runtime,
        scorer_full_runtime=scorer_full_runtime,
        scorer_basin_judge_runtime=scorer_basin_judge_runtime,
        scorer_word_ngram_report_runtime=scorer_word_ngram_report_runtime,
        scorer_stage3_phaseA_runtime=scorer_stage3_phaseA_runtime,
        stage2_judge_policy=str(stage2_judge_policy),
        scorer_stage2_judge_runtime=scorer_stage2_judge_runtime,
        scorer_stage2_judge_cfg=scorer_stage2_judge_cfg,
        scorer_stage2_pass1_primary_runtime=scorer_stage2_pass1_primary_runtime,
        scorer_stage2_pass1_fallback_runtime=scorer_stage2_pass1_fallback_runtime,
    )
