from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

import numpy as np


def _as_int_list(values: Sequence[int] | np.ndarray | None) -> List[int]:
    if values is None:
        return []
    arr = np.asarray(values)
    if int(arr.size) <= 0:
        return []
    return arr.astype(int, copy=False).reshape(-1).tolist()


def _safe_ratio(correct: int, total: int) -> float:
    if int(total) <= 0:
        return float("nan")
    return float(int(correct)) / float(int(total))


def _count_matches(lhs: Sequence[int], rhs: Sequence[int]) -> Dict[str, int | float]:
    total = int(min(len(lhs), len(rhs)))
    correct = 0
    for idx in range(total):
        if int(lhs[idx]) == int(rhs[idx]):
            correct += 1
    mismatches = int(max(0, total - correct))
    return dict(
        total=int(total),
        correct=int(correct),
        mismatches=int(mismatches),
        match_ratio=float(_safe_ratio(correct, total)),
    )


def _build_residue_match_rows(
    *,
    target_values: Sequence[int],
    candidate_values: Sequence[int],
    modulus: int,
    label: str,
) -> Dict[str, Any]:
    if int(modulus) <= 0:
        return dict(rows=[], worst_residue=None, worst_match_ratio=float("nan"))
    total_n = int(min(len(target_values), len(candidate_values)))
    rows: List[Dict[str, Any]] = []
    for residue in range(int(modulus)):
        idxs = list(range(int(residue), int(total_n), int(modulus)))
        correct = 0
        for idx in idxs:
            if int(candidate_values[idx]) == int(target_values[idx]):
                correct += 1
        total = int(len(idxs))
        rows.append(
            dict(
                kind=str(label),
                residue=int(residue),
                total=int(total),
                correct=int(correct),
                mismatches=int(max(0, total - correct)),
                match_ratio=float(_safe_ratio(correct, total)),
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            float(row.get("match_ratio", float("inf"))),
            -int(row.get("mismatches", 0)),
            int(row.get("residue", 0)),
        ),
    )
    worst = dict(ranked[0]) if ranked else {}
    return dict(
        rows=rows,
        worst_residue=(
            int(worst["residue"]) if isinstance(worst.get("residue"), int) else None
        ),
        worst_match_ratio=float(worst.get("match_ratio", float("nan"))),
    )


def _build_key_slice_rows(
    *,
    target_key_idx: Sequence[int],
    candidate_key_idx: Sequence[int],
    period: int,
    alphabet_size: int,
) -> Dict[str, Any]:
    period_i = int(max(0, int(period)))
    alphabet_i = int(max(0, int(alphabet_size)))
    if period_i <= 0 or alphabet_i <= 0:
        return dict(rows=[], worst_slice=None, worst_mismatches=0)
    rows: List[Dict[str, Any]] = []
    for slice_idx in range(period_i):
        start = int(slice_idx * alphabet_i)
        stop = int(start + alphabet_i)
        target_slice = list(target_key_idx[start:stop])
        candidate_slice = list(candidate_key_idx[start:stop])
        stats = _count_matches(target_slice, candidate_slice)
        rows.append(
            dict(
                slice_idx=int(slice_idx),
                slice_len=int(stats["total"]),
                correct=int(stats["correct"]),
                mismatches=int(stats["mismatches"]),
                match_ratio=float(stats["match_ratio"]),
            )
        )
    ranked = sorted(
        rows,
        key=lambda row: (
            -int(row.get("mismatches", 0)),
            float(row.get("match_ratio", float("inf"))),
            int(row.get("slice_idx", 0)),
        ),
    )
    worst = dict(ranked[0]) if ranked else {}
    return dict(
        rows=rows,
        worst_slice=(
            int(worst["slice_idx"]) if isinstance(worst.get("slice_idx"), int) else None
        ),
        worst_mismatches=int(worst.get("mismatches", 0) or 0),
    )


def _infer_alphabet_size(
    *,
    period: int,
    columns: int,
    target_key_idx: Sequence[int],
    candidate_key_idx: Sequence[int],
) -> int:
    period_i = int(max(0, int(period)))
    columns_i = int(max(0, int(columns)))
    for key_values in (target_key_idx, candidate_key_idx):
        key_len = int(len(key_values))
        sub_len = int(key_len - columns_i)
        if period_i > 0 and sub_len >= 0 and sub_len % period_i == 0:
            return int(sub_len // period_i)
    return 0


def _build_key_truth_summary(
    *,
    target_key_idx: Sequence[int],
    candidate_key_idx: Sequence[int],
    period: int,
    columns: int,
    alphabet_size: int,
) -> Dict[str, Any]:
    target_key = _as_int_list(target_key_idx)
    candidate_key = _as_int_list(candidate_key_idx)
    period_i = int(max(0, int(period)))
    columns_i = int(max(0, int(columns)))
    alphabet_i = int(max(0, int(alphabet_size)))
    total_stats = _count_matches(target_key, candidate_key)
    sub_len = int(max(0, int(period_i * alphabet_i)))
    sub_stats = _count_matches(target_key[:sub_len], candidate_key[:sub_len])
    col_stats = _count_matches(target_key[sub_len:], candidate_key[sub_len:])
    slice_summary = _build_key_slice_rows(
        target_key_idx=target_key,
        candidate_key_idx=candidate_key,
        period=int(period_i),
        alphabet_size=int(alphabet_i),
    )
    return dict(
        key_hamming_total=int(total_stats["mismatches"]),
        key_match_ratio=float(total_stats["match_ratio"]),
        key_hamming_substitution=int(sub_stats["mismatches"]),
        key_match_ratio_substitution=float(sub_stats["match_ratio"]),
        key_hamming_columns=int(col_stats["mismatches"]),
        key_match_ratio_columns=float(col_stats["match_ratio"]),
        key_hamming_by_period_slice=list(slice_summary["rows"]),
        worst_substitution_slice=slice_summary["worst_slice"],
        worst_substitution_slice_mismatches=int(slice_summary["worst_mismatches"]),
    )


def _build_topk_truth_rows(
    *,
    topk_rows: Sequence[Mapping[str, Any]] | None,
    target_key_idx: Sequence[int],
    target_plaintext_idx: Sequence[int],
    period: int,
    columns: int,
    alphabet_size: int,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row_idx, row_obj in enumerate(topk_rows or [], start=1):
        row = dict(row_obj) if isinstance(row_obj, Mapping) else {}
        if not row:
            continue
        key_idx = _as_int_list(row.get("key_idx"))
        pt_idx = _as_int_list(row.get("plaintext_idx"))
        key_summary = _build_key_truth_summary(
            target_key_idx=target_key_idx,
            candidate_key_idx=key_idx,
            period=int(period),
            columns=int(columns),
            alphabet_size=int(alphabet_size),
        )
        period_residue = _build_residue_match_rows(
            target_values=target_plaintext_idx,
            candidate_values=pt_idx,
            modulus=int(period),
            label="period",
        )
        out.append(
            dict(
                rank=int(row.get("rank", row_idx)),
                source=str(row.get("source", "") or ""),
                score_pct=row.get("score_pct"),
                score_judge=row.get("score_judge"),
                match_ratio=row.get("match_ratio"),
                key_hamming_total=int(key_summary["key_hamming_total"]),
                key_hamming_substitution=int(key_summary["key_hamming_substitution"]),
                key_hamming_columns=int(key_summary["key_hamming_columns"]),
                worst_substitution_slice=key_summary["worst_substitution_slice"],
                worst_substitution_slice_mismatches=int(
                    key_summary["worst_substitution_slice_mismatches"]
                ),
                worst_plaintext_period_residue=period_residue["worst_residue"],
                worst_plaintext_period_residue_match_ratio=float(
                    period_residue["worst_match_ratio"]
                ),
            )
        )
    return out


def build_fixture_truth_diagnostics(
    *,
    target_key_idx: Sequence[int] | np.ndarray | None,
    final_best_key_idx: Sequence[int] | np.ndarray | None,
    target_plaintext_idx: Sequence[int] | np.ndarray | None,
    final_best_plaintext_idx: Sequence[int] | np.ndarray | None,
    period: int,
    columns: int,
    stage3_topk_rows: Sequence[Mapping[str, Any]] | None = None,
) -> Dict[str, Any]:
    target_key = _as_int_list(target_key_idx)
    final_key = _as_int_list(final_best_key_idx)
    target_pt = _as_int_list(target_plaintext_idx)
    final_pt = _as_int_list(final_best_plaintext_idx)
    period_i = int(max(0, int(period)))
    columns_i = int(max(0, int(columns)))
    alphabet_i = _infer_alphabet_size(
        period=int(period_i),
        columns=int(columns_i),
        target_key_idx=target_key,
        candidate_key_idx=final_key,
    )
    available = bool(target_key) and bool(final_key) and bool(target_pt) and bool(final_pt)
    if not available:
        return dict(
            available=False,
            period=int(period_i),
            columns=int(columns_i),
            alphabet_size=int(alphabet_i),
            key_hamming_total=None,
            key_hamming_substitution=None,
            key_hamming_columns=None,
            worst_substitution_slice=None,
            worst_substitution_slice_mismatches=None,
            worst_plaintext_period_residue=None,
            worst_plaintext_period_residue_match_ratio=float("nan"),
            worst_plaintext_columns_residue=None,
            worst_plaintext_columns_residue_match_ratio=float("nan"),
            key_hamming_by_period_slice=[],
            plaintext_match_by_period_residue=[],
            plaintext_match_by_columns_residue=[],
            stage3_topk_truth_diagnostics=[],
        )

    key_summary = _build_key_truth_summary(
        target_key_idx=target_key,
        candidate_key_idx=final_key,
        period=int(period_i),
        columns=int(columns_i),
        alphabet_size=int(alphabet_i),
    )
    period_residue = _build_residue_match_rows(
        target_values=target_pt,
        candidate_values=final_pt,
        modulus=int(period_i),
        label="period",
    )
    columns_residue = _build_residue_match_rows(
        target_values=target_pt,
        candidate_values=final_pt,
        modulus=int(columns_i),
        label="columns",
    )
    topk_truth = _build_topk_truth_rows(
        topk_rows=stage3_topk_rows,
        target_key_idx=target_key,
        target_plaintext_idx=target_pt,
        period=int(period_i),
        columns=int(columns_i),
        alphabet_size=int(alphabet_i),
    )
    return dict(
        available=True,
        period=int(period_i),
        columns=int(columns_i),
        alphabet_size=int(alphabet_i),
        key_hamming_total=int(key_summary["key_hamming_total"]),
        key_match_ratio=float(key_summary["key_match_ratio"]),
        key_hamming_substitution=int(key_summary["key_hamming_substitution"]),
        key_match_ratio_substitution=float(key_summary["key_match_ratio_substitution"]),
        key_hamming_columns=int(key_summary["key_hamming_columns"]),
        key_match_ratio_columns=float(key_summary["key_match_ratio_columns"]),
        worst_substitution_slice=key_summary["worst_substitution_slice"],
        worst_substitution_slice_mismatches=int(
            key_summary["worst_substitution_slice_mismatches"]
        ),
        key_hamming_by_period_slice=list(key_summary["key_hamming_by_period_slice"]),
        worst_plaintext_period_residue=period_residue["worst_residue"],
        worst_plaintext_period_residue_match_ratio=float(
            period_residue["worst_match_ratio"]
        ),
        plaintext_match_by_period_residue=list(period_residue["rows"]),
        worst_plaintext_columns_residue=columns_residue["worst_residue"],
        worst_plaintext_columns_residue_match_ratio=float(
            columns_residue["worst_match_ratio"]
        ),
        plaintext_match_by_columns_residue=list(columns_residue["rows"]),
        stage3_topk_truth_diagnostics=topk_truth,
    )
