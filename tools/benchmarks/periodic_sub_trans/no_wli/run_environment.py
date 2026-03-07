from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Mapping


def prepare_run_environment(
    *,
    encoding_dir: str,
    direction_ltr: Any,
    direction_rtl: Any,
    require_assets_fn: Callable[..., None],
    encode_long_plaintext_fn: Callable[[Any], tuple[Any, Any]],
    repo_root_fn: Callable[[], Path],
    make_flavor_run_dir_fn: Callable[..., Path],
    audit_csv_name: str,
    audit_jsonl_name: str,
    audit_chain_seed: str,
    autoskip_proven: bool,
    force_rerun_proven: bool,
    autoskip_proven_min_match: float,
    load_proven_index_fn: Callable[..., Mapping[Any, Any]],
    build_run_mode_info_fn: Callable[[str | None], Any],
    run_mode: str,
    oracle_mode_normalized_fn: Callable[[], str],
    oracle_assist_selection_requested: bool,
) -> Dict[str, Any]:
    direction_txt = str(encoding_dir).strip().lower()
    if direction_txt == "ltr":
        direction = direction_ltr
    elif direction_txt == "rtl":
        direction = direction_rtl
    else:
        raise ValueError(
            f"Unsupported ENCODING_DIR={encoding_dir!r}; expected 'ltr' or 'rtl'"
        )
    print("[pipeline_no_wli] bootstrap: checking char LM assets...", flush=True)
    require_assets_fn(direction, ns=(1, 3, 4), need_wli=False)
    pt_base, wli_base = encode_long_plaintext_fn(direction)

    root = repo_root_fn()
    run_dir = make_flavor_run_dir_fn(flavor="no_wli", run_prefix="bench_solve_pipeline_no_wli")
    best_dir = run_dir / "best"
    best_dir.mkdir(parents=True, exist_ok=True)
    final_dir = run_dir / "final_instances"
    final_dir.mkdir(parents=True, exist_ok=True)
    audit_csv = run_dir / str(audit_csv_name)
    audit_jsonl = run_dir / str(audit_jsonl_name)
    audit_prev_chain_hash = str(audit_chain_seed)
    audit_rows_written = 0

    hist = root / "tools" / "benchmarks" / "solve_proof" / "proven_solve_pipeline_no_wli_log.csv"
    hist.parent.mkdir(parents=True, exist_ok=True)
    autoskip_effective = bool(autoskip_proven) and (not bool(force_rerun_proven))
    proven_index = (
        load_proven_index_fn(hist, min_match=float(autoskip_proven_min_match))
        if autoskip_effective
        else {}
    )
    history_rows_written = 0

    mode_info = build_run_mode_info_fn(run_mode)
    mode_raw = str(mode_info.mode_raw)
    mode_canonical = str(mode_info.mode_canonical)
    mode_intent = str(mode_info.intent)
    stage3_can_skip = bool(mode_info.stage3_can_skip)
    oracle_mode = str(oracle_mode_normalized_fn())
    oracle_decision_paths_enabled = bool(oracle_mode == "benchmark_only")
    oracle_assist_selection_effective = bool(
        oracle_decision_paths_enabled and bool(oracle_assist_selection_requested)
    )

    return dict(
        direction=direction,
        pt_base=pt_base,
        wli_base=wli_base,
        root=root,
        run_dir=run_dir,
        best_dir=best_dir,
        final_dir=final_dir,
        audit_csv=audit_csv,
        audit_jsonl=audit_jsonl,
        audit_prev_chain_hash=str(audit_prev_chain_hash),
        audit_rows_written=int(audit_rows_written),
        hist=hist,
        autoskip_effective=bool(autoskip_effective),
        proven_index=dict(proven_index),
        history_rows_written=int(history_rows_written),
        mode_raw=str(mode_raw),
        mode_canonical=str(mode_canonical),
        mode_intent=str(mode_intent),
        stage3_can_skip=bool(stage3_can_skip),
        oracle_mode=str(oracle_mode),
        oracle_decision_paths_enabled=bool(oracle_decision_paths_enabled),
        oracle_assist_selection_effective=bool(oracle_assist_selection_effective),
        oracle_consulted_in_decisions=False,
    )
