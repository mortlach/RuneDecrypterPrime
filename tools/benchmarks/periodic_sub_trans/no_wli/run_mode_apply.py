from __future__ import annotations

from typing import Any, Callable, Mapping, MutableMapping


def apply_run_mode_overrides(
    *,
    state: MutableMapping[str, Any],
    overrides: Mapping[str, Any],
    build_tier_fn: Callable[[str, int, int, int], Any],
) -> None:
    if not overrides:
        return

    def _assign(name: str, cast: Callable[[Any], Any]) -> None:
        if name in overrides:
            state[name] = cast(overrides[name])

    _assign("PROFILE", str)
    _assign("HEARTBEAT_SECONDS", int)
    _assign("STAGE2_PROMOTE_BY_STAGE3_JUDGE", bool)
    _assign("STAGE2_ENTRY_BAND_BY_STAGE3_JUDGE", bool)
    _assign("ORACLE_ASSIST_SELECTION", bool)
    _assign("STAGE3_CONTINUE_AFTER_SOLVE", bool)
    _assign("SCORING_EXPERIMENT_PROFILE", str)
    _assign("SCAN_TIER_TIME_CAP_SECONDS", float)
    _assign("SCAN_STAGE2_CONTINUE_TO_GATE", bool)
    _assign("SCAN_STAGE2_CONTINUE_CAP_SECONDS", float)
    _assign("SCAN_STAGE3_GATE_LOW_MATCH", float)
    _assign("SCAN_STAGE3_GATE_HIGH_MATCH", float)
    _assign("SCAN_STAGE3_MIN_STAGE2_MATCH", float)
    _assign("STAGE1_SEED_RESTARTS", int)
    _assign("STAGE1_SEED_TOTAL", int)
    _assign("STAGE1_SCOUT_MIN_STEPS", int)
    _assign("STAGE12_ARCHIVE_KEEP", int)
    _assign("STAGE12_PROMOTE_TOP", int)
    _assign("STAGE1_SCOUT_NO_IMPROVE_PATIENCE", int)
    _assign("STAGE1_SCOUT_MIN_NEW_ARCHIVE", int)
    _assign("STAGE1_SCOUT_EARLY_STOP_MIN_SCOUTS", int)
    _assign("STAGE3_INITIAL_KEYS", int)
    _assign("STAGE3_C1_INIT_KEYS", int)
    _assign("STAGE3_C1_PHASEA_STEPS", int)
    _assign("STAGE3_C1_PHASEB_STEPS", int)
    _assign("STAGE3_C1_PHASEB_TOP_N", int)
    _assign("STAGE3_PHASEB_TOP_N", int)
    _assign("STAGE3_PHASEB_GATE_DELTA_FLOOR", float)
    _assign("STAGE3_PHASEB_GATE_END_GAIN_FLOOR", float)
    _assign("STAGE3_PHASEC_ENABLED", bool)
    _assign("STAGE3_PHASEC_START_KEYS", int)
    _assign("STAGE3_PHASEC_SEED_OFFSET", int)
    _assign("STAGE3_PHASEC_WORD_NGRAM_TIEBREAK", bool)
    _assign("STAGE35_ENABLED", bool)
    _assign("STAGE3_INIT_KEYS_CAP", int)

    if "TEXT_OFFSETS" in overrides:
        state["TEXT_OFFSETS"][:] = [int(x) for x in list(overrides["TEXT_OFFSETS"])]
    if "KEY_SEEDS" in overrides:
        state["KEY_SEEDS"][:] = [int(x) for x in list(overrides["KEY_SEEDS"])]
    if "STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS" in overrides:
        state["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"] = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE2_EXACT_SUB_CANDIDATES_BY_COLUMNS"]).items()
        }
    if "STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS" in overrides:
        state["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"] = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE2_EXACT_PASS1_TOP_TAILS_BY_COLUMNS"]).items()
        }
    if "STAGE3_INITIAL_KEYS_BY_COLUMNS" in overrides:
        state["STAGE3_INITIAL_KEYS_BY_COLUMNS"] = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE3_INITIAL_KEYS_BY_COLUMNS"]).items()
        }
    if "STAGE3_DYNAMIC_BANDS" in overrides:
        state["STAGE3_DYNAMIC_BANDS"] = [
            dict(b) for b in list(overrides["STAGE3_DYNAMIC_BANDS"])
        ]
    if "STAGE3_PHASEB_CFG" in overrides:
        state["STAGE3_PHASEB_CFG"] = dict(overrides["STAGE3_PHASEB_CFG"])
    if "STAGE3_PHASEC_CFG" in overrides:
        state["STAGE3_PHASEC_CFG"] = dict(overrides["STAGE3_PHASEC_CFG"])
    if "STAGE35_CFG" in overrides:
        state["STAGE35_CFG"] = dict(overrides["STAGE35_CFG"])
    if "STAGE3_PERIOD_INIT_MULT_BY_PERIOD" in overrides:
        state["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"] = {
            int(k): float(v)
            for k, v in dict(overrides["STAGE3_PERIOD_INIT_MULT_BY_PERIOD"]).items()
        }
    if "STAGE3_PERIOD_STEP_MULT_BY_PERIOD" in overrides:
        state["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"] = {
            int(k): float(v)
            for k, v in dict(overrides["STAGE3_PERIOD_STEP_MULT_BY_PERIOD"]).items()
        }
    if "STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD" in overrides:
        state["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"] = {
            int(k): int(v)
            for k, v in dict(overrides["STAGE3_PERIOD_RESTART_BONUS_BY_PERIOD"]).items()
        }
    if "TIERS" in overrides:
        state["TIERS"][:] = [
            build_tier_fn(str(name), int(period), int(columns), int(length))
            for name, period, columns, length in list(overrides["TIERS"])
        ]
