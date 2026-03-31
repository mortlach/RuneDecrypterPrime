from __future__ import annotations

from typing import Any, Mapping, Sequence


_PHASEC_BASE_REQUIRED_KEYS: tuple[str, ...] = (
    "phaseC_enabled_cfg",
    "phaseC_enabled_effective",
    "phaseC_ran",
    "phaseC_start_keys_used",
    "phaseC_start_policy",
    "phaseC_candidate_pool_count",
    "phaseC_candidate_pool_unique_keys",
    "phaseC_candidate_pool_unique_end_hash",
    "phaseC_candidate_pool_source_counts",
    "phaseC_start_source_counts",
    "phaseC_start_unique_end_hash",
    "phaseC_checkpoint_jsonl_name",
    "phaseC_checkpoint_rows_written",
    "phaseC_final_winner_lane",
    "phaseC_final_winner_source",
    "phaseC_start_summaries",
)

_PHASEC_START_SUMMARY_CAPTURE_KEYS: tuple[str, ...] = (
    "candidate_hash",
    "init_key_idx",
    "init_plaintext_idx",
    "final_key_idx",
    "final_plaintext_idx",
)

_PHASEC_NOVEL_REQUIRED_KEYS: tuple[str, ...] = (
    "phaseC_novel_view_id",
    "phaseC_anchor_candidate_hash",
    "phaseC_candidate_pool_eligible_novel_count",
    "phaseC_candidate_pool_eligible_novel_row_count",
    "phaseC_candidate_pool_eligible_novel_source_counts",
    "phaseC_start_eligible_novel_count",
    "phaseC_selected_novel_challenger_count",
    "phaseC_eligible_novel_not_selected_count",
    "phaseC_selected_novel_challenger_hashes",
)

_PHASEC_NOVEL_START_SUMMARY_REQUIRED_KEYS: tuple[str, ...] = (
    "candidate_hash",
    "selection_bucket",
    "selected_by_novel_policy",
    "eligible_novel_challenger",
    "novelty_distance_to_anchor",
    "novelty_min_distance_to_selected_challenger",
)


def _is_truthy_int(value: Any) -> bool:
    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return bool(value)


def _require_keys(
    payload: Mapping[str, Any],
    *,
    keys: Sequence[str],
    context: str,
    reason: str,
) -> None:
    missing = [str(key) for key in keys if key not in payload]
    if missing:
        raise KeyError(
            f"{context}: missing {reason} key(s): {', '.join(missing)}"
        )


def require_phasec_diagnostics_contract(
    payload: Mapping[str, Any],
    *,
    context: str,
) -> None:
    phasec_known = any(
        key in payload
        for key in (
            "phaseC_enabled_cfg",
            "phaseC_enabled_effective",
            "phaseC_ran",
            "phaseC_start_policy",
        )
    )
    if not phasec_known:
        return

    phasec_enabled = _is_truthy_int(payload.get("phaseC_enabled_cfg", 0)) or _is_truthy_int(
        payload.get("phaseC_enabled_effective", 0)
    )
    phasec_ran = _is_truthy_int(payload.get("phaseC_ran", 0))
    if not (phasec_enabled or phasec_ran):
        return

    _require_keys(
        payload,
        keys=_PHASEC_BASE_REQUIRED_KEYS,
        context=context,
        reason="Phase-C diagnostics",
    )

    if not phasec_ran:
        return

    start_summaries = payload["phaseC_start_summaries"]
    if isinstance(start_summaries, (str, bytes)) or not isinstance(start_summaries, Sequence):
        raise TypeError(
            f"{context}: phaseC_start_summaries must be a sequence for Phase-C diagnostics"
        )
    for idx, row in enumerate(start_summaries):
        if not isinstance(row, Mapping):
            raise TypeError(
                f"{context}: phaseC_start_summaries[{idx}] must be a mapping for Phase-C diagnostics"
            )
        _require_keys(
            row,
            keys=_PHASEC_START_SUMMARY_CAPTURE_KEYS,
            context=f"{context}.phaseC_start_summaries[{idx}]",
            reason="Phase-C start-summary capture",
        )

    phasec_start_policy = str(payload["phaseC_start_policy"]).strip().lower()
    if phasec_start_policy != "novel_challenger_v1":
        return

    _require_keys(
        payload,
        keys=_PHASEC_NOVEL_REQUIRED_KEYS,
        context=context,
        reason="Phase-C novel-challenger diagnostics",
    )

    for idx, row in enumerate(start_summaries):
        _require_keys(
            row,
            keys=_PHASEC_NOVEL_START_SUMMARY_REQUIRED_KEYS,
            context=f"{context}.phaseC_start_summaries[{idx}]",
            reason="Phase-C novel-challenger start-summary",
        )
