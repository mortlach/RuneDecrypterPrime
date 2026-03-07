from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Tuple


def oracle_score_for_stage(
    *,
    pt_idx: Any,
    cipher_cfg: Any,
    scorer_params: Dict[str, Any],
    scoring_config_cls: Any,
    build_scorer_fn: Callable[[Any, Any], Any],
    scorer_objective_summary_fn: Callable[[Dict[str, Any]], str],
) -> Tuple[float, float, str]:
    s_cfg = scoring_config_cls(**scorer_params)
    scorer = build_scorer_fn(cipher_cfg, s_cfg)
    score, raw = scorer.score_with_raw(pt_idx, None)
    return float(score), float(raw), str(scorer_objective_summary_fn(scorer_params))


def append_jsonl_row(
    *,
    path: Path,
    row: Dict[str, Any],
    sanitize_jsonable_fn: Callable[[Any], Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps(
                sanitize_jsonable_fn(row),
                sort_keys=True,
                ensure_ascii=True,
                allow_nan=False,
            )
            + "\n"
        )


def append_iteration_audit_row(
    *,
    audit_csv: Path,
    audit_jsonl: Path,
    prev_chain_hash: str,
    payload: Dict[str, Any],
    sanitize_jsonable_fn: Callable[[Any], Any],
    canonical_json_fn: Callable[[Any], str],
    sha256_text_fn: Callable[[str], str],
    append_csv_row_fn: Callable[[Path, Dict[str, Any]], None],
    append_jsonl_row_fn: Callable[[Path, Dict[str, Any]], None],
) -> str:
    clean_payload = sanitize_jsonable_fn(payload)
    row_hash = sha256_text_fn(canonical_json_fn(clean_payload))
    chain_hash = sha256_text_fn(f"{str(prev_chain_hash)}|{row_hash}")
    row_out = dict(
        **clean_payload,
        row_hash=str(row_hash),
        prev_chain_hash=str(prev_chain_hash),
        chain_hash=str(chain_hash),
    )
    append_csv_row_fn(audit_csv, row_out)
    append_jsonl_row_fn(audit_jsonl, row_out)
    return str(chain_hash)
