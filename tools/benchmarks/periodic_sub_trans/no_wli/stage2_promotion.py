from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence, Tuple


def is_better_match_first(
    *,
    cand_match: float,
    cand_score: float,
    best_match: float,
    best_score: float,
) -> bool:
    c_match_ok = bool(math.isfinite(float(cand_match)))
    b_match_ok = bool(math.isfinite(float(best_match)))
    if c_match_ok and b_match_ok:
        if float(cand_match) > float(best_match):
            return True
        if float(cand_match) < float(best_match):
            return False
    elif c_match_ok and (not b_match_ok):
        return True
    elif (not c_match_ok) and b_match_ok:
        return False

    c_score_ok = bool(math.isfinite(float(cand_score)))
    b_score_ok = bool(math.isfinite(float(best_score)))
    if c_score_ok and b_score_ok:
        return float(cand_score) > float(best_score)
    if c_score_ok and (not b_score_ok):
        return True
    return False


def is_better_score_first(
    *,
    cand_score: float,
    cand_match: float,
    best_score: float,
    best_match: float,
) -> bool:
    c_score_ok = bool(math.isfinite(float(cand_score)))
    b_score_ok = bool(math.isfinite(float(best_score)))
    if c_score_ok and b_score_ok:
        if float(cand_score) > float(best_score):
            return True
        if float(cand_score) < float(best_score):
            return False
    elif c_score_ok and (not b_score_ok):
        return True
    elif (not c_score_ok) and b_score_ok:
        return False

    c_match_ok = bool(math.isfinite(float(cand_match)))
    b_match_ok = bool(math.isfinite(float(best_match)))
    if c_match_ok and b_match_ok:
        return float(cand_match) > float(best_match)
    if c_match_ok and (not b_match_ok):
        return True
    return False


def is_solved_match(*, match_ratio: float, solve_threshold: float) -> bool:
    return bool(
        math.isfinite(float(match_ratio))
        and float(match_ratio) >= float(solve_threshold)
    )


def is_better_stage3_candidate_preserving_solve(
    *,
    cand_score: float,
    cand_match: float,
    best_score: float,
    best_match: float,
    solve_threshold: float,
    score_first: bool,
) -> bool:
    cand_solved = is_solved_match(
        match_ratio=float(cand_match), solve_threshold=float(solve_threshold)
    )
    best_solved = is_solved_match(
        match_ratio=float(best_match), solve_threshold=float(solve_threshold)
    )
    if cand_solved and (not best_solved):
        return True
    if best_solved and (not cand_solved):
        return False
    if score_first:
        return is_better_score_first(
            cand_score=float(cand_score),
            cand_match=float(cand_match),
            best_score=float(best_score),
            best_match=float(best_match),
        )
    return is_better_match_first(
        cand_match=float(cand_match),
        cand_score=float(cand_score),
        best_match=float(best_match),
        best_score=float(best_score),
    )


def entry_key_tuple(entry: Dict[str, Any]) -> Tuple[int, ...]:
    key_vals = entry.get("key", [])
    if not isinstance(key_vals, list) or (not key_vals):
        return tuple()
    return tuple(int(x) for x in key_vals)


def ensure_best_entry_in_ranked(
    *,
    ranked_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    out = list(ranked_entries)
    if best_entry is None:
        return out
    best_t = entry_key_tuple(best_entry)
    if not best_t:
        return out
    ranked_key_set = {entry_key_tuple(ent) for ent in out}
    if best_t not in ranked_key_set:
        out.insert(0, best_entry)
    return out


def ensure_best_entry_in_promoted(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_entry: Dict[str, Any] | None,
    promote_top: int,
) -> Tuple[List[Dict[str, Any]], bool]:
    out = list(promoted_entries)
    if best_entry is None:
        return out, False
    best_t = entry_key_tuple(best_entry)
    if not best_t:
        return out, False
    promoted_key_set = {entry_key_tuple(ent) for ent in out}
    if best_t in promoted_key_set:
        return out, True
    top_n = int(max(1, promote_top))
    if len(out) >= top_n:
        out = out[: top_n - 1]
    out.append(best_entry)
    return out, True


def build_stage3_promoted_keys(
    *,
    promoted_entries: Sequence[Dict[str, Any]],
    best_key: Sequence[int] | None,
    key_len: int,
) -> List[List[int]]:
    out: List[List[int]] = []
    seen: set[Tuple[int, ...]] = set()
    if best_key is not None:
        best_list = [int(x) for x in best_key]
        if len(best_list) == int(key_len):
            best_t = tuple(best_list)
            if best_t not in seen:
                seen.add(best_t)
                out.append(best_list)
    for ent in promoted_entries:
        key_vals = ent.get("key", [])
        if not isinstance(key_vals, list):
            continue
        k = [int(x) for x in key_vals]
        if len(k) != int(key_len):
            continue
        kt = tuple(k)
        if kt in seen:
            continue
        seen.add(kt)
        out.append(k)
    return out
