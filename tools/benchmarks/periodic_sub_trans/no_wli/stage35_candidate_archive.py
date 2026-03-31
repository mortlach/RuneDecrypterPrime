from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from tools.benchmarks.periodic_sub_trans.no_wli.stage35_ranking import (
    dedupe_stage35_rows,
)


def substitution_prefix_len(*, period: int, alphabet_size: int) -> int:
    return int(max(0, int(period)) * max(0, int(alphabet_size)))


def stable_key_hash(key_vals: Sequence[int]) -> str:
    payload = bytes(int(v) & 0xFF for v in key_vals)
    return hashlib.blake2b(payload, digest_size=8).hexdigest()


def apply_frozen_columns_tail(
    *,
    key_vals: Sequence[int],
    prefix_len: int,
    frozen_tail: Sequence[int],
) -> list[int]:
    prefix_i = int(max(0, int(prefix_len)))
    key_list = list(map(int, key_vals))
    return list(key_list[:prefix_i]) + list(map(int, frozen_tail))


def _phaseb_topk_indexes(
    topk_rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
    by_hash: dict[str, dict[str, Any]] = {}
    by_rank: dict[int, dict[str, Any]] = {}
    for row in topk_rows:
        if str(row.get("source", "") or "") != "phaseB_topk":
            continue
        row_d = dict(row)
        end_hash = str(row_d.get("end_hash", "") or "").strip()
        if end_hash:
            by_hash[end_hash] = row_d
        rank = int(row_d.get("rank", 0) or 0)
        if rank > 0:
            by_rank[rank] = row_d
    return by_hash, by_rank


def build_stage35_seed_archive(
    artifact: Mapping[str, Any],
    *,
    max_phaseb_challengers: int = 4,
    max_phaseb_topk: int = 6,
    max_phasea_topk: int = 2,
    include_final_best: bool = True,
    checkpoint_order_mode: str = "live_safe",
) -> dict[str, Any]:
    period = int(artifact.get("period", 0) or 0)
    alphabet_size = int(artifact.get("alphabet_size", 0) or 0)
    prefix_len = int(
        substitution_prefix_len(period=int(period), alphabet_size=int(alphabet_size))
    )
    topk_rows = [dict(row) for row in list(artifact.get("stage3_topk", []) or [])]
    stage3_diag = dict(artifact.get("stage3_diagnostics", {}) or {})
    start_summaries = [
        dict(row) for row in list(stage3_diag.get("phaseC_start_summaries", []) or [])
    ]

    fixed_key: list[int] = []
    final_best_key = list(map(int, artifact.get("final_best_key_idx", []) or []))
    if include_final_best and len(final_best_key) >= int(prefix_len):
        fixed_key = list(final_best_key)
    elif topk_rows:
        fixed_key = list(map(int, topk_rows[0].get("key_idx", []) or []))
    if not fixed_key or len(fixed_key) < int(prefix_len):
        return dict(
            seed_rows=[],
            prefix_len=int(prefix_len),
            frozen_tail=[],
            frozen_tail_hash="",
            tail_mismatch_count=0,
            seed_source_counts={},
        )
    frozen_tail = list(map(int, fixed_key[int(prefix_len) :]))
    frozen_tail_hash = stable_key_hash(frozen_tail)
    phaseb_by_hash, phaseb_by_rank = _phaseb_topk_indexes(topk_rows)

    out_rows: list[dict[str, Any]] = []
    tail_mismatch_count = 0
    final_best_row: dict[str, Any] | None = None

    def _append_seed(
        *,
        seed_source: str,
        key_vals: Sequence[int],
        candidate_hash: str,
        seed_priority_group: int,
        seed_priority_rank: int,
        source_rank: int = 0,
        lane: str = "",
        stage3_source: str = "",
        stage3_rank: int = 0,
        checkpoint_final_match: float = float("nan"),
        checkpoint_final_score: float = float("nan"),
        checkpoint_rescue_applied: int = 0,
    ) -> None:
        nonlocal tail_mismatch_count
        key_list = list(map(int, key_vals))
        if len(key_list) < int(prefix_len):
            return
        original_tail = list(map(int, key_list[int(prefix_len) :]))
        tail_was_normalized = int(original_tail != list(frozen_tail))
        if int(tail_was_normalized) == 1:
            tail_mismatch_count += 1
        frozen_key = apply_frozen_columns_tail(
            key_vals=key_list,
            prefix_len=int(prefix_len),
            frozen_tail=frozen_tail,
        )
        row_d = dict(
            key_idx=list(frozen_key),
            candidate_hash=str(candidate_hash or stable_key_hash(frozen_key)),
            seed_source=str(seed_source),
            stage3_source=str(stage3_source),
            lane=str(lane),
            source_rank=int(source_rank),
            stage3_rank=int(stage3_rank),
            seed_priority_group=int(seed_priority_group),
            seed_priority_rank=int(seed_priority_rank),
            checkpoint_final_match=float(checkpoint_final_match),
            checkpoint_final_score=float(checkpoint_final_score),
            checkpoint_rescue_applied=int(checkpoint_rescue_applied),
            tail_was_normalized=int(tail_was_normalized),
            fixed_tail_hash=str(frozen_tail_hash),
        )
        out_rows.append(row_d)
        return row_d

    if include_final_best and len(final_best_key) >= int(prefix_len):
        final_best_row = _append_seed(
            seed_source="final_best",
            key_vals=final_best_key,
            candidate_hash=stable_key_hash(final_best_key),
            seed_priority_group=0,
            seed_priority_rank=0,
            lane=str(stage3_diag.get("phaseC_final_winner_lane", "") or ""),
            stage3_source=str(stage3_diag.get("phaseC_final_winner_source", "") or ""),
        )

    checkpoint_phaseb_rows: list[dict[str, Any]] = []
    for row in start_summaries:
        if str(row.get("source", "") or "") != "phaseB_topk":
            continue
        source_rank = int(row.get("source_rank", 0) or 0)
        topk_row = (
            phaseb_by_hash.get(str(row.get("candidate_hash", "") or "").strip())
            or phaseb_by_rank.get(source_rank)
        )
        if topk_row is None:
            continue
        checkpoint_phaseb_rows.append(
            dict(
                summary=dict(row),
                topk=dict(topk_row),
            )
        )
    checkpoint_order_mode_norm = str(checkpoint_order_mode or "live_safe").strip().lower()
    checkpoint_phaseb_rows = sorted(
        checkpoint_phaseb_rows,
        key=lambda row: (
            (
                -float(row["summary"].get("final_match", float("-inf")))
                if checkpoint_order_mode_norm == "offline_truth_match"
                else 0.0
            ),
            -float(row["summary"].get("final_score", float("-inf"))),
            -int(row["summary"].get("rescue_applied", 0) or 0),
            int(row["summary"].get("source_rank", 0) or 0),
            int(row["summary"].get("start_idx", 0) or 0),
            str(row["summary"].get("candidate_hash", "") or ""),
        ),
    )
    for idx, row in enumerate(
        checkpoint_phaseb_rows[: max(0, int(max_phaseb_challengers))],
        start=1,
    ):
        topk_row = dict(row["topk"])
        summary_row = dict(row["summary"])
        _append_seed(
            seed_source="phasec_phaseb_challenger",
            key_vals=topk_row.get("key_idx", []),
            candidate_hash=str(summary_row.get("candidate_hash", "") or topk_row.get("end_hash", "")),
            seed_priority_group=1,
            seed_priority_rank=int(idx),
            source_rank=int(summary_row.get("source_rank", 0) or 0),
            lane=str(summary_row.get("lane", "") or ""),
            stage3_source="phaseB_topk",
            stage3_rank=int(topk_row.get("rank", 0) or 0),
            checkpoint_final_match=float(summary_row.get("final_match", float("nan"))),
            checkpoint_final_score=float(summary_row.get("final_score", float("nan"))),
            checkpoint_rescue_applied=int(summary_row.get("rescue_applied", 0) or 0),
        )

    phaseb_rows = [
        dict(row)
        for row in topk_rows
        if str(row.get("source", "") or "") == "phaseB_topk"
    ]
    phaseb_rows = sorted(
        phaseb_rows,
        key=lambda row: (
            int(row.get("rank", 0) or 0),
            -float(row.get("score_judge", float("-inf"))),
            str(row.get("end_hash", "") or ""),
        ),
    )
    for idx, row in enumerate(phaseb_rows[: max(0, int(max_phaseb_topk))], start=1):
        _append_seed(
            seed_source="stage3_topk_phaseb",
            key_vals=row.get("key_idx", []),
            candidate_hash=str(row.get("end_hash", "") or ""),
            seed_priority_group=2,
            seed_priority_rank=int(idx),
            source_rank=int(row.get("rank", 0) or 0),
            stage3_source="phaseB_topk",
            stage3_rank=int(row.get("rank", 0) or 0),
        )

    phasea_rows = [
        dict(row)
        for row in topk_rows
        if str(row.get("source", "") or "") == "phaseA_topk"
    ]
    phasea_rows = sorted(
        phasea_rows,
        key=lambda row: (
            int(row.get("rank", 0) or 0),
            -float(row.get("score_judge", float("-inf"))),
            str(row.get("end_hash", "") or ""),
        ),
    )
    for idx, row in enumerate(phasea_rows[: max(0, int(max_phasea_topk))], start=1):
        _append_seed(
            seed_source="stage3_topk_phasea",
            key_vals=row.get("key_idx", []),
            candidate_hash=str(row.get("end_hash", "") or row.get("start_hash", "") or ""),
            seed_priority_group=3,
            seed_priority_rank=int(idx),
            source_rank=int(row.get("rank", 0) or 0),
            stage3_source="phaseA_topk",
            stage3_rank=int(row.get("rank", 0) or 0),
        )

    deduped = dedupe_stage35_rows(out_rows)
    if final_best_row is not None:
        final_key_t = tuple(map(int, final_best_row.get("key_idx", []) or []))
        replaced = False
        for idx, row in enumerate(deduped):
            if tuple(map(int, row.get("key_idx", []) or [])) == final_key_t:
                deduped[idx] = dict(final_best_row)
                replaced = True
                break
        if not replaced:
            deduped.append(dict(final_best_row))
    deduped = sorted(
        (dict(row) for row in deduped),
        key=lambda row: (
            int(
                99
                if row.get("seed_priority_group", 99) is None
                else row.get("seed_priority_group", 99)
            ),
            int(
                99
                if row.get("seed_priority_rank", 99) is None
                else row.get("seed_priority_rank", 99)
            ),
            str(row.get("seed_source", "") or ""),
            tuple(map(int, row.get("key_idx", []) or [])),
        ),
    )
    tail_mismatch_count = int(
        sum(int(row.get("tail_was_normalized", 0) or 0) for row in deduped)
    )
    seed_source_counts: dict[str, int] = {}
    for row in deduped:
        seed_source = str(row.get("seed_source", "") or "")
        seed_source_counts[seed_source] = int(seed_source_counts.get(seed_source, 0)) + 1
    return dict(
        seed_rows=deduped,
        prefix_len=int(prefix_len),
        frozen_tail=list(frozen_tail),
        frozen_tail_hash=str(frozen_tail_hash),
        tail_mismatch_count=int(tail_mismatch_count),
        seed_source_counts=seed_source_counts,
    )
