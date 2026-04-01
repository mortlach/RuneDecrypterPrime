from __future__ import annotations

from pathlib import Path
from typing import Any, MutableMapping

from rune_decrypter_prime.core.types import ScorerImpl

from tools.benchmarks.periodic_sub_trans.common.core_enums import BenchmarkOrder


def _discover_word_ngram_sqlite_path(*, repo_root: Path | None = None) -> Path | None:
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[4]
    candidates: list[Path] = []
    direct = Path("assets/scoring/word_ngrams_tokenized64_phase2_v1.sqlite")
    if (root / direct).exists():
        candidates.append(direct)
    packed = Path("assets_packed/word_ngrams_tokenized64_phase2_v1.sqlite")
    if (root / packed).exists():
        candidates.append(packed)
    output_root = root / "output/tools/benchmarks/scoring/word_ngrams_sqlite_assets"
    if output_root.exists():
        for fp in output_root.glob("**/word_ngrams_tokenized64_phase2_v1.sqlite"):
            if fp.exists():
                candidates.append(fp.relative_to(root))
    if not candidates:
        return None
    return max(candidates, key=lambda p: (root / p).stat().st_mtime)


def apply_runner_defaults(*, state: MutableMapping[str, Any]) -> None:
    """Populate top-level runner configuration defaults."""
    word_ngram_sqlite_path = _discover_word_ngram_sqlite_path()
    state.update(
        {
            "ALPHABET_SIZE": 29,
            "ORDER": BenchmarkOrder.COL_THEN_SUB.value,
            "PROFILE": "pipeline_no_wli_v1",
            "PIPELINE_RUN_MODE": "adaptive_focus_v1_p7c3_only",
            "ENCODING_DIR": "ltr",
            "NO_WLI_PIPELINE_PROFILE_ID": "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
            "NO_WLI_PIPELINE_PROFILE_ID_PREVIOUS_DEFAULT": "no_wli_a1_m12_b34_stage3avg_fulltext_v1",
            "NO_WLI_LONGRUN3X_PROFILE_ID": "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
            "SCORER_STAGE1_LABEL": "A_char1",
            "SCORER_STAGE2_LABEL": "M_char12",
            "SCORER_STAGE3_LABEL": "B_char34",
            "SCORER_IMPL": ScorerImpl.TORCH.value,
            "SCORER_STAGE3_IMPL_AVG_FULLTEXT": ScorerImpl.TORCH.value,
            "BATCH_EVAL_CHUNK_SIZE": 256,
            "REQUIRE_BATCH_SCORING": True,
            "STAGE2_PROMOTE_BY_STAGE3_JUDGE": True,
            "STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE": True,
            "STAGE2_JUDGE_POLICY": "search_only",
            "REQUIRE_NO_ECDF_FOR_AVG_FULLTEXT": True,
            "ORACLE_ASSIST_SELECTION": False,
            "ORACLE_MODE": "off",
            "SCORING_EXPERIMENT_PROFILE": "c_min_late",
            "SCORING_EXPERIMENT_ENFORCE_LOCKS": True,
            "SCORING_EXPERIMENT_SPAN_ASSETS_DIR": Path(
                "assets/scoring/span_hamming_nose_assets_v1"
            ),
            "SCORING_EXPERIMENT_SPAN_COVERAGE_MIN": 0.05,
            "SCORING_EXPERIMENT_SPAN_QUALITY_MIN": 0.05,
            "SCORING_EXPERIMENT_C_CHAR_PCT_MIN": 0.70,
            # Report-only word-ngram side-channel.
            "WORD_NGRAM_REPORT_ENABLED": bool(word_ngram_sqlite_path is not None),
            "WORD_NGRAM_REPORT_SQLITE_PATH": word_ngram_sqlite_path,
            "WORD_NGRAM_REPORT_ALPHA": 0.4,
            "WORD_NGRAM_REPORT_MISS_LOGP": -20.0,
            "WORD_NGRAM_REPORT_MIN_POSITIONS": 12,
            "WORD_NGRAM_REPORT_PREFIX_TOTAL_THRESHOLDS": (1, 10, 100),
            "WORD_NGRAM_REPORT_DECISION_INFLUENCE": False,
            "STAGE3_PHASEC_ENABLED": True,
            "STAGE3_PHASEC_CFG": {
                "steps": 32,
                "proposals_per_step": 24,
                "three_cycle_prob": 0.15,
            },
            "STAGE3_PHASEC_START_KEYS": 12,
            "STAGE3_PHASEC_SEED_OFFSET": 1200003,
            "STAGE3_PHASEC_WORD_NGRAM_TIEBREAK": True,
            "STAGE35_ENABLED": False,
            "STAGE35_BASELINE_SELECTOR": "legacy",
            "STAGE35_CFG": {
                "seed_keep": 4,
                "beam_width": 4,
                "archive_keep": 16,
                "rounds": 3,
                "mini_search_steps": 2,
                "mini_search_beam_width": 3,
                "mini_search_top_symbols": 10,
                "mini_search_final_keep": 2,
                "mini_search_keep_all_rows": 0,
                "accept_score_min_gain": 0,
                "accept_search_score_max_drop": 0,
            },
            "STAGE3_SPAN_CHAR_PCT_MIN_OVERRIDE": None,
            "STAGE3_SPAN_AUX_ROLE": "off",
            "STAGE3_SPAN_AUX_SCOPE": "basin_rep",
            "STAGE3_SPAN_AUX_PROFILE": "lite",
            "STAGE3_SPAN_AUX_BUDGET_MS": 0.0,
            "STAGE3_SPAN_AUX_TWO_PASS": False,
            "STAGE3_SPAN_AUX_FULL_TOP_M": 0,
            "SPAN_DECISION_ROLE_ENABLED": False,
            "SPAN_REPS_PER_BASIN": 1,
            "SPAN_SELECTION_TOP_K": 0,
            "SPAN_P90_CALL_MS": None,
            "ORACLE_STAGE3_FLOOR_GUARD_EPS": 1e-12,
            "SCAN_TIER_TIME_CAP_SECONDS": 600.0,
            "SCAN_STAGE3_GATE_LOW_MATCH": 0.15,
            "SCAN_STAGE3_GATE_HIGH_MATCH": 0.22,
            "SCAN_STAGE2_CONTINUE_TO_GATE": True,
            "SCAN_STAGE2_CONTINUE_CAP_SECONDS": 900.0,
            "AUDIT_HASH_CHAIN_ENABLED": True,
            "AUDIT_HASH_CHAIN_SEED": "0" * 64,
            "AUDIT_HASH_CHAIN_CSV": "iteration_audit_chain.csv",
            "AUDIT_HASH_CHAIN_JSONL": "iteration_audit_chain.jsonl",
            "AUTOSKIP_PROVEN": True,
            "FORCE_RERUN_PROVEN": True,
        }
    )
    state["SCAN_STAGE3_MIN_STAGE2_MATCH"] = float(state["SCAN_STAGE3_GATE_LOW_MATCH"])
    state["_SCAN_TIER_TIME_CAP_SECONDS_DEFAULT"] = float(state["SCAN_TIER_TIME_CAP_SECONDS"])
    state["_SCAN_STAGE3_GATE_LOW_MATCH_DEFAULT"] = float(state["SCAN_STAGE3_GATE_LOW_MATCH"])
    state["_SCAN_STAGE3_GATE_HIGH_MATCH_DEFAULT"] = float(
        max(state["SCAN_STAGE3_GATE_LOW_MATCH"], state["SCAN_STAGE3_GATE_HIGH_MATCH"])
    )
    state["_SCAN_STAGE3_MIN_STAGE2_MATCH_DEFAULT"] = float(state["SCAN_STAGE3_GATE_LOW_MATCH"])
    state["_SCAN_STAGE2_CONTINUE_TO_GATE_DEFAULT"] = bool(state["SCAN_STAGE2_CONTINUE_TO_GATE"])
    state["_SCAN_STAGE2_CONTINUE_CAP_SECONDS_DEFAULT"] = float(
        state["SCAN_STAGE2_CONTINUE_CAP_SECONDS"]
    )
