from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

import numpy as np

from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_candidates import (
    apply_slice_pair_swap,
    target_slice_active_positions,
)
from tools.benchmarks.periodic_sub_trans.no_wli.phasec_rescue_selector import (
    landing_sort_key,
    rank_rows,
)


def run_slice_local_mini_search(
    *,
    current_key: Sequence[int],
    current_pt: np.ndarray,
    current_score: float,
    current_search_score: float,
    current_match: float,
    probe_key: Sequence[int],
    probe_pt: np.ndarray,
    probe_score: float,
    probe_search_score: float,
    probe_match: float,
    target_slice: int,
    ciphertext_idx: np.ndarray | Sequence[int],
    period: int,
    alphabet_size: int,
    top_symbols: int,
    beam_width: int,
    steps: int,
    final_keep: int,
    keep_all_rows: bool,
    score_key_rows_fn: Callable[[Sequence[Sequence[int]]], Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    active_positions = target_slice_active_positions(
        ciphertext_idx=np.asarray(ciphertext_idx, dtype=np.uint8).reshape(-1),
        period=int(period),
        target_slice=int(target_slice),
        alphabet_size=int(alphabet_size),
        current_key=current_key,
        probe_key=probe_key,
        top_symbols=int(top_symbols),
    )
    seed_rows: list[dict[str, Any]] = [
        dict(
            key=list(map(int, current_key)),
            pt=np.asarray(current_pt, dtype=np.uint8).reshape(-1).copy(),
            score=float(current_score),
            search_score=float(current_search_score),
            match=float(current_match),
            landing_type="current_seed",
            mini_search_step=0,
            mini_search_parent_type="current_seed",
            mini_search_swap_a=None,
            mini_search_swap_b=None,
        )
    ]
    probe_key_list = list(map(int, probe_key))
    probe_pt_arr = np.asarray(probe_pt, dtype=np.uint8).reshape(-1)
    if (
        int(probe_pt_arr.size) > 0
        and tuple(map(int, probe_key_list)) != tuple(map(int, current_key))
    ):
        seed_rows.append(
            dict(
                key=list(map(int, probe_key_list)),
                pt=probe_pt_arr.copy(),
                score=float(probe_score),
                search_score=float(probe_search_score),
                match=float(probe_match),
                landing_type="probe_seed",
                mini_search_step=0,
                mini_search_parent_type="probe_seed",
                mini_search_swap_a=None,
                mini_search_swap_b=None,
            )
        )
    beam_width_i = int(max(1, int(beam_width)))
    frontier = rank_rows(seed_rows, limit=int(beam_width_i))
    collected: dict[tuple[int, ...], dict[str, Any]] = {}
    seen: set[tuple[int, ...]] = {
        tuple(map(int, row.get("key", []) or [])) for row in frontier
    }
    total_evals = 0
    expanded_steps = 0
    for step_idx in range(1, int(max(0, int(steps))) + 1):
        proposals: list[list[int]] = []
        proposal_meta: list[dict[str, Any]] = []
        for parent in frontier:
            parent_key = list(map(int, parent.get("key", []) or []))
            for pos_i_idx, pos_i in enumerate(active_positions):
                for pos_j in active_positions[int(pos_i_idx) + 1 :]:
                    cand = apply_slice_pair_swap(
                        key_vals=parent_key,
                        target_slice=int(target_slice),
                        pos_a=int(pos_i),
                        pos_b=int(pos_j),
                        alphabet_size=int(alphabet_size),
                    )
                    cand_t = tuple(map(int, cand))
                    if cand_t in seen:
                        continue
                    seen.add(cand_t)
                    proposals.append(list(cand))
                    proposal_meta.append(
                        dict(
                            parent_type=str(
                                parent.get("landing_type", "current_seed")
                                or "current_seed"
                            ),
                            swap_a=int(pos_i),
                            swap_b=int(pos_j),
                            mini_search_step=int(step_idx),
                        )
                    )
        if not proposals:
            break
        expanded_steps = int(step_idx)
        total_evals += int(len(proposals))
        step_rows = [dict(row) for row in score_key_rows_fn(proposals)]
        enriched_rows: list[dict[str, Any]] = []
        for row_idx, base_row in enumerate(step_rows):
            meta = proposal_meta[row_idx]
            enriched_rows.append(
                dict(
                    base_row,
                    landing_type="mini_search",
                    target_slice=int(target_slice),
                    mini_search_step=int(meta["mini_search_step"]),
                    mini_search_parent_type=str(meta["parent_type"]),
                    mini_search_swap_a=int(meta["swap_a"]),
                    mini_search_swap_b=int(meta["swap_b"]),
                    mini_search_active_position_count=int(len(active_positions)),
                )
            )
        for row in enriched_rows:
            key_t = tuple(map(int, row.get("key", []) or []))
            prev = collected.get(key_t, None)
            if prev is None or landing_sort_key(row) < landing_sort_key(prev):
                collected[key_t] = dict(row)
        frontier = rank_rows(enriched_rows, limit=int(beam_width_i))
        if not frontier:
            break
    collected_rows = sorted(
        (dict(row) for row in collected.values()),
        key=landing_sort_key,
    )
    if bool(keep_all_rows):
        ranked_rows = list(collected_rows)
    else:
        ranked_rows = rank_rows(
            collected_rows,
            limit=int(max(1, int(final_keep))),
        )
    return dict(
        rows=ranked_rows,
        collected_rows=collected_rows,
        collected_row_count=int(len(collected_rows)),
        evals=int(total_evals),
        expanded_steps=int(expanded_steps),
        active_positions=list(map(int, active_positions)),
        seed_count=int(len(seed_rows)),
    )
