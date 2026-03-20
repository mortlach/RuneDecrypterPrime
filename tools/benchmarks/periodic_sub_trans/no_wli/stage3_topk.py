from __future__ import annotations

from typing import Any, Callable, Dict, List, Sequence, Tuple

import numpy as np

from tools.benchmarks.periodic_sub_trans.common.batch_eval import decrypt_and_score_keys_chunked


def append_stage3_topk_from_kaeding(
    *,
    payload: List[Dict[str, Any]],
    kaeding_obj: Any,
    save_enabled: bool,
    save_limit: int,
    key_len: int,
    full_cipher: Any,
    ciphertext: np.ndarray,
    scorer_full_runtime: Any,
    batch_eval_chunk_size: int,
    require_batch_scoring: bool,
    match_ratio_fn: Callable[[Sequence[int], Sequence[int]], float],
    target_plaintext: np.ndarray,
    key_hash_fn: Callable[[Sequence[int]], str] | None = None,
) -> None:
    if (not bool(save_enabled)) or (not isinstance(kaeding_obj, dict)):
        return
    top_keys = kaeding_obj.get("top_keys", [])
    top_raw = kaeding_obj.get("top_raw", [])
    top_pct = kaeding_obj.get("top_pct", [])
    if not isinstance(top_keys, list):
        return
    top_key_records: List[Tuple[int, List[int]]] = []
    for rank_idx, key_vals in enumerate(top_keys[: int(save_limit)], start=1):
        if not isinstance(key_vals, list):
            continue
        key_list = list(map(int, key_vals))
        if len(key_list) != int(key_len):
            continue
        top_key_records.append((int(rank_idx), key_list))
    if not top_key_records:
        return
    eval_keys = [key_list for _rank_idx, key_list in top_key_records]
    pt_batch, judge_scores, _judge_stats = decrypt_and_score_keys_chunked(
        cipher=full_cipher,
        ciphertext=ciphertext,
        keys=eval_keys,
        scorer=scorer_full_runtime,
        wli=None,
        chunk_size=int(batch_eval_chunk_size),
        require_batch=bool(require_batch_scoring),
    )
    for idx, (rank_idx, key_list) in enumerate(top_key_records):
        pt_k = np.asarray(pt_batch[idx], dtype=np.uint8).reshape(-1)
        judge_sc = float(judge_scores[idx]) if idx < int(judge_scores.size) else float("nan")
        payload.append(
            dict(
                rank=int(rank_idx),
                score_raw=(
                    float(top_raw[rank_idx - 1])
                    if isinstance(top_raw, list) and (rank_idx - 1) < len(top_raw)
                    else float("nan")
                ),
                score_pct=(
                    float(top_pct[rank_idx - 1])
                    if isinstance(top_pct, list) and (rank_idx - 1) < len(top_pct)
                    else float("nan")
                ),
                score_judge=float(judge_sc),
                match_ratio=float(match_ratio_fn(pt_k.tolist(), target_plaintext.tolist())),
                key_idx=key_list,
                plaintext_idx=pt_k.astype(int).tolist(),
                end_hash=(
                    str(key_hash_fn(key_list))
                    if callable(key_hash_fn)
                    else ""
                ),
                source="phaseB_topk",
            )
        )


def append_stage3_topk_from_phasea(
    *,
    payload: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    save_enabled: bool,
    save_limit: int,
    key_len: int,
) -> None:
    if (not bool(save_enabled)) or (not rows):
        return
    ranked_rows = sorted(
        rows,
        key=lambda r: (
            float(r.get("end_score_pct", float("-inf"))),
            float(r.get("best_delta_pct", float("-inf"))),
            float(r.get("end_score_raw", float("-inf"))),
            -int(r.get("restart_idx", 0)),
        ),
        reverse=True,
    )
    used_keys: set[Tuple[int, ...]] = set()
    out_rank = 0
    for row in ranked_rows:
        key_list = list(map(int, row.get("end_key", [])))
        if len(key_list) != int(key_len):
            continue
        key_t = tuple(key_list)
        if key_t in used_keys:
            continue
        used_keys.add(key_t)
        out_rank += 1
        payload.append(
            dict(
                rank=int(out_rank),
                score_raw=float(row.get("end_score_raw", float("nan"))),
                score_pct=float(row.get("end_score_pct", float("nan"))),
                score_judge=float(row.get("end_score_pct", float("nan"))),
                match_ratio=float(row.get("end_match", float("nan"))),
                key_idx=key_list,
                plaintext_idx=list(map(int, row.get("end_plaintext", []))),
                start_hash=str(row.get("start_hash", "")),
                end_hash=str(row.get("end_hash", "")),
                source="phaseA_topk",
            )
        )
        if out_rank >= int(save_limit):
            break
