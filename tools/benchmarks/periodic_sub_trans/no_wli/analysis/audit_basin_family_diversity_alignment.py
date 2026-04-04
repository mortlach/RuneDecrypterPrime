from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (  # noqa: E402
    refresh_catalog_safely,
)
from tools.benchmarks.periodic_sub_trans.no_wli.family_views import (  # noqa: E402
    FAMILY_VIEWS as SHARED_FAMILY_VIEWS,
    cluster_family_ids as shared_cluster_family_ids,
)


CATALOG_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli_catalog")
SUMMARY_PATH = CATALOG_ROOT / "basin_family_diversity_audit_summary.json"
REPORT_PATH = CATALOG_ROOT / "basin_family_diversity_audit_report.md"

COMPARISON_RUNS: tuple[dict[str, str], ...] = (
    {
        "label": "seed511_recovery",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260321T190828084704Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
        ),
    },
    {
        "label": "seed511_stage35_win",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260322T001521766633Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed511.json"
        ),
    },
    {
        "label": "seed211_current_preserve",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260324T004559684950Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
        ),
    },
    {
        "label": "seed211_old_best",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260309T092929767920Z__bench_solve_pipeline_no_wli__97536a2/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed211.json"
        ),
    },
    {
        "label": "seed411_current_preserve",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260324T040609368464Z__bench_solve_pipeline_no_wli__55b7159/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
        ),
    },
    {
        "label": "seed411_old_best",
        "path": (
            "output/tools/benchmarks/periodic_sub_trans/no_wli/"
            "20260312T020424363346Z__bench_solve_pipeline_no_wli__5961d3e/"
            "final_instances/fixture_fixture_001_p9_c3_l1000__text0__seed411.json"
        ),
    },
)

POOL_ORDER: tuple[str, ...] = (
    "stage2_topk",
    "stage2_promoted",
    "stage3_init3",
    "stage3_topk",
    "phasec_start",
    "stage35_seed_archive",
    "stage35_archive",
)

POOL_PRIORITY_FOR_CLASSIFICATION: tuple[str, ...] = (
    "stage35_archive",
    "stage35_seed_archive",
    "phasec_start",
    "stage3_topk",
    "stage2_promoted",
    "stage2_topk",
)

FAMILY_VIEWS: tuple[dict[str, Any], ...] = SHARED_FAMILY_VIEWS

CLASSIFICATION_VIEW_PRIORITY: tuple[str, ...] = (
    "prefix_hamming_le_24",
    "near_tail_h1",
    "exact_tail",
    "exact_key",
)

POOL_SIGNAL_PRIORITY: dict[str, tuple[str, ...]] = {
    "stage2_topk": ("score_judge", "score_stage2"),
    "stage2_promoted": ("score_judge", "score"),
    "stage3_topk": ("score_judge", "score_pct", "score_raw"),
    "phasec_start": ("final_score", "score_final"),
    "stage35_seed_archive": ("checkpoint_final_score", "score", "search_score"),
    "stage35_archive": ("score", "search_score"),
}

TOP_BAND_RANK = 4
REFERENCE_GAP_MIN = 0.05
COLLAPSE_GAP_MIN = 0.05
UNDERVALUE_GAP_MIN = 0.05
NOT_EXPLOITED_GAP_MIN = 0.05
REFERENCE_SUCCESS_EPS = 0.01


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _is_finite(value: Any) -> bool:
    return bool(np.isfinite(_safe_float(value)))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _truth_from_plaintext(
    plaintext_idx: Sequence[Any] | None, target_plaintext_idx: Sequence[Any] | None
) -> float:
    if plaintext_idx is None or target_plaintext_idx is None:
        return float("nan")
    pt = np.asarray(list(plaintext_idx), dtype=np.int64).reshape(-1)
    target = np.asarray(list(target_plaintext_idx), dtype=np.int64).reshape(-1)
    size = min(int(pt.size), int(target.size))
    if size <= 0:
        return float("nan")
    return float(np.mean(pt[:size] == target[:size]))


def _as_key_tuple(value: Sequence[Any] | None) -> tuple[int, ...] | None:
    if value is None:
        return None
    try:
        seq = tuple(int(v) for v in value)
    except Exception:
        return None
    return seq if seq else None


def _tail_tuple(key_idx: Sequence[int] | None, *, columns: int) -> tuple[int, ...] | None:
    if key_idx is None or columns <= 0:
        return None
    key_t = tuple(int(v) for v in key_idx)
    if len(key_t) < int(columns):
        return None
    return key_t[-int(columns) :]


def _prefix_tuple(key_idx: Sequence[int] | None, *, columns: int) -> tuple[int, ...] | None:
    if key_idx is None:
        return None
    key_t = tuple(int(v) for v in key_idx)
    if columns <= 0:
        return key_t if key_t else None
    if len(key_t) <= int(columns):
        return None
    return key_t[: -int(columns)]


def _hamming_distance(lhs: Sequence[int], rhs: Sequence[int]) -> int:
    if len(lhs) != len(rhs):
        return max(len(lhs), len(rhs))
    return int(sum(1 for x, y in zip(lhs, rhs) if int(x) != int(y)))


def _make_row(
    *,
    pool_name: str,
    row_id: str,
    key_idx: Sequence[Any] | None = None,
    candidate_hash: str = "",
    source: str = "",
    truth_match: Any = float("nan"),
    score_stage2: Any = float("nan"),
    score_judge: Any = float("nan"),
    score_raw: Any = float("nan"),
    score_pct: Any = float("nan"),
    score: Any = float("nan"),
    search_score: Any = float("nan"),
    final_score: Any = float("nan"),
    score_final: Any = float("nan"),
    checkpoint_final_score: Any = float("nan"),
) -> dict[str, Any]:
    key_t = _as_key_tuple(key_idx)
    return {
        "pool_name": str(pool_name),
        "row_id": str(row_id),
        "candidate_hash": str(candidate_hash or ""),
        "source": str(source or ""),
        "key_idx": list(key_t) if key_t is not None else None,
        "truth_match": _safe_float(truth_match),
        "score_stage2": _safe_float(score_stage2),
        "score_judge": _safe_float(score_judge),
        "score_raw": _safe_float(score_raw),
        "score_pct": _safe_float(score_pct),
        "score": _safe_float(score),
        "search_score": _safe_float(search_score),
        "final_score": _safe_float(final_score),
        "score_final": _safe_float(score_final),
        "checkpoint_final_score": _safe_float(checkpoint_final_score),
    }


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _extract_pool_rows(
    artifact: Mapping[str, Any],
    *,
    artifact_path: Path,
    bundle_dir: Path | None,
) -> dict[str, list[dict[str, Any]]]:
    pools: dict[str, list[dict[str, Any]]] = defaultdict(list)
    target_plaintext_idx = list(artifact.get("target_plaintext_idx", []) or [])

    for idx, row in enumerate(list(artifact.get("stage2_topk", []) or []), start=1):
        pools["stage2_topk"].append(
            _make_row(
                pool_name="stage2_topk",
                row_id=f"stage2_topk:{idx}",
                key_idx=row.get("key_idx", row.get("key")),
                candidate_hash=row.get("candidate_hash", ""),
                source=row.get("source", row.get("tag", "")),
                truth_match=row.get("truth_match_ratio", row.get("match_ratio", row.get("match"))),
                score_stage2=row.get("score_stage2"),
                score_judge=row.get("score_judge", row.get("judge_score")),
                score=row.get("score"),
            )
        )

    if bundle_dir is not None:
        stage2_resume_path = bundle_dir / "stage2_resume.json"
        if stage2_resume_path.exists():
            stage2_resume = _load_json(stage2_resume_path)
            for idx, row in enumerate(list(stage2_resume.get("stage2_promoted", []) or []), start=1):
                pools["stage2_promoted"].append(
                    _make_row(
                        pool_name="stage2_promoted",
                        row_id=f"stage2_promoted:{idx}",
                        key_idx=row.get("key_idx", row.get("key")),
                        candidate_hash=row.get("candidate_hash", ""),
                        source=row.get("source", row.get("tag", "")),
                        truth_match=row.get("truth_match_ratio", row.get("match_ratio", row.get("match"))),
                        score_stage2=row.get("score_stage2"),
                        score_judge=row.get("score_judge", row.get("judge_score")),
                        score=row.get("score"),
                    )
                )

        stage3_prep_path = bundle_dir / "stage3_prep.json"
        if stage3_prep_path.exists():
            stage3_prep = _load_json(stage3_prep_path)
            for idx, row in enumerate(list(stage3_prep.get("init3", []) or []), start=1):
                pools["stage3_init3"].append(
                    _make_row(
                        pool_name="stage3_init3",
                        row_id=f"stage3_init3:{idx}",
                        key_idx=row,
                    )
                )

        stage35_seed_archive_path = bundle_dir / "stage35_seed_archive.json"
        if stage35_seed_archive_path.exists():
            stage35_seed_archive = _load_json(stage35_seed_archive_path)
            for idx, row in enumerate(list(stage35_seed_archive.get("seed_rows", []) or []), start=1):
                truth_match = row.get("checkpoint_final_match", row.get("truth_match_ratio"))
                if not _is_finite(truth_match):
                    truth_match = _truth_from_plaintext(
                        row.get("plaintext_idx"), target_plaintext_idx
                    )
                pools["stage35_seed_archive"].append(
                    _make_row(
                        pool_name="stage35_seed_archive",
                        row_id=f"stage35_seed_archive:{idx}",
                        key_idx=row.get("key_idx", row.get("key")),
                        candidate_hash=row.get("candidate_hash", ""),
                        source=row.get("seed_source", row.get("source", "")),
                        truth_match=truth_match,
                        checkpoint_final_score=row.get("checkpoint_final_score"),
                        score=row.get("score"),
                        search_score=row.get("search_score"),
                    )
                )

    for idx, row in enumerate(list(artifact.get("stage3_topk", []) or []), start=1):
        truth_match = row.get("truth_match_ratio", row.get("match_ratio"))
        if not _is_finite(truth_match):
            truth_match = _truth_from_plaintext(row.get("plaintext_idx"), target_plaintext_idx)
        pools["stage3_topk"].append(
            _make_row(
                pool_name="stage3_topk",
                row_id=f"stage3_topk:{idx}",
                key_idx=row.get("key_idx", row.get("key")),
                candidate_hash=row.get("candidate_hash", ""),
                source=row.get("source", row.get("tag", "")),
                truth_match=truth_match,
                score_judge=row.get("score_judge", row.get("judge_score")),
                score_raw=row.get("score_raw"),
                score_pct=row.get("score_pct"),
                score=row.get("score"),
            )
        )

    checkpoint_rows = _read_jsonl_rows(artifact_path.parents[1] / "phasec_start_checkpoints.jsonl")
    for idx, row in enumerate(checkpoint_rows, start=1):
        pools["phasec_start"].append(
            _make_row(
                pool_name="phasec_start",
                row_id=f"phasec_start:{idx}",
                candidate_hash=row.get("candidate_hash", ""),
                source=row.get("source", ""),
                truth_match=row.get("final_match", row.get("match_final")),
                final_score=row.get("final_score"),
                score_final=row.get("score_final"),
            )
        )

    for idx, row in enumerate(list(artifact.get("stage35_archive", []) or []), start=1):
        truth_match = row.get("truth_match_ratio", row.get("checkpoint_final_match"))
        if not _is_finite(truth_match):
            truth_match = _truth_from_plaintext(row.get("plaintext_idx"), target_plaintext_idx)
        pools["stage35_archive"].append(
            _make_row(
                pool_name="stage35_archive",
                row_id=f"stage35_archive:{idx}",
                key_idx=row.get("key_idx", row.get("key")),
                candidate_hash=row.get("candidate_hash", ""),
                source=row.get("seed_source", row.get("source", "")),
                truth_match=truth_match,
                score=row.get("score"),
                search_score=row.get("search_score"),
                checkpoint_final_score=row.get("checkpoint_final_score"),
            )
        )

    return {str(name): list(rows) for name, rows in pools.items()}


def _live_score_field(pool_name: str, rows: Sequence[Mapping[str, Any]]) -> str | None:
    priorities = POOL_SIGNAL_PRIORITY.get(str(pool_name), ())
    for field in priorities:
        if any(_is_finite(row.get(field)) for row in rows):
            return str(field)
    return None


def _select_top_band_row_ids(
    rows: Sequence[Mapping[str, Any]], *, pool_name: str
) -> list[str]:
    field = _live_score_field(pool_name, rows)
    if field is None:
        return []
    scored = [
        (float(row[field]), str(row["row_id"]))
        for row in rows
        if _is_finite(row.get(field))
    ]
    scored.sort(key=lambda item: (-float(item[0]), str(item[1])))
    return [row_id for _, row_id in scored[: min(TOP_BAND_RANK, len(scored))]]


def _row_key_tuple(row: Mapping[str, Any]) -> tuple[int, ...] | None:
    key_idx = row.get("key_idx")
    if key_idx is None:
        return None
    return tuple(int(v) for v in key_idx)


def _row_tail_tuple(row: Mapping[str, Any], *, columns: int) -> tuple[int, ...] | None:
    return _tail_tuple(_row_key_tuple(row), columns=columns)


def _row_prefix_tuple(row: Mapping[str, Any], *, columns: int) -> tuple[int, ...] | None:
    return _prefix_tuple(_row_key_tuple(row), columns=columns)


def _component_ids(edge_pairs: Iterable[tuple[int, int]], *, size: int) -> list[int]:
    parent = list(range(size))

    def _find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def _union(lhs: int, rhs: int) -> None:
        left_root = _find(lhs)
        right_root = _find(rhs)
        if left_root == right_root:
            return
        if left_root < right_root:
            parent[right_root] = left_root
        else:
            parent[left_root] = right_root

    for lhs, rhs in edge_pairs:
        _union(int(lhs), int(rhs))

    roots: dict[int, int] = {}
    ids: list[int] = []
    next_id = 0
    for idx in range(size):
        root = _find(idx)
        if root not in roots:
            roots[root] = next_id
            next_id += 1
        ids.append(int(roots[root]))
    return ids


def cluster_family_ids(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_view: Mapping[str, Any],
    columns: int,
) -> tuple[dict[str, str], int]:
    return shared_cluster_family_ids(
        rows,
        family_view=family_view,
        columns=columns,
    )


def _effective_family_count(counts: Sequence[int]) -> float:
    counts_arr = np.asarray(list(counts), dtype=np.float64).reshape(-1)
    total = float(np.sum(counts_arr))
    if total <= 0.0:
        return 0.0
    probs = counts_arr / total
    denom = float(np.sum(probs * probs))
    if denom <= 0.0:
        return 0.0
    return float(1.0 / denom)


def summarize_family_block(
    rows: Sequence[Mapping[str, Any]],
    *,
    family_view: Mapping[str, Any],
    columns: int,
    selected_row_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    selected_ids = {str(row_id) for row_id in list(selected_row_ids or [])}
    assignments, unassigned_rows = cluster_family_ids(rows, family_view=family_view, columns=columns)
    family_members: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        row_id = str(row["row_id"])
        family_id = assignments.get(row_id)
        if family_id is not None:
            family_members[family_id].append(row_id)

    family_sizes = [len(member_ids) for member_ids in family_members.values()]
    assigned_rows = int(sum(family_sizes))
    total_rows = int(len(rows))
    largest_family_share = (
        float(max(family_sizes) / assigned_rows) if assigned_rows > 0 and family_sizes else 0.0
    )
    selected_family_ids = sorted(
        {
            assignments[row_id]
            for row_id in selected_ids
            if row_id in assignments
        }
    )
    selected_family_sizes = [len(family_members[fam_id]) for fam_id in selected_family_ids]
    selected_family_selected_counts = Counter(
        assignments[row_id] for row_id in selected_ids if row_id in assignments
    )
    selected_assigned_rows = int(
        sum(1 for row_id in selected_ids if row_id in assignments)
    )
    selected_largest_family_share = (
        float(max(selected_family_selected_counts.values()) / selected_assigned_rows)
        if selected_assigned_rows > 0 and selected_family_selected_counts
        else 0.0
    )
    top_band_family_mass_share = (
        float(sum(selected_family_sizes) / assigned_rows)
        if assigned_rows > 0
        else 0.0
    )
    return {
        "family_view_id": str(family_view["id"]),
        "row_count": total_rows,
        "assigned_rows": assigned_rows,
        "unassigned_rows": int(unassigned_rows),
        "family_count": int(len(family_members)),
        "effective_family_count": float(_effective_family_count(family_sizes)),
        "largest_family_share": float(largest_family_share),
        "selected_top_band_row_count": int(len(selected_ids)),
        "selected_top_band_assigned_rows": selected_assigned_rows,
        "selected_top_band_family_count": int(len(selected_family_ids)),
        "selected_top_band_effective_family_count": float(
            _effective_family_count(list(selected_family_selected_counts.values()))
        ),
        "selected_top_band_largest_family_share": float(selected_largest_family_share),
        "top_band_family_count": int(len(selected_family_ids)),
        "top_band_family_mass_share": float(top_band_family_mass_share),
    }


def summarize_pool_alignment(
    rows: Sequence[Mapping[str, Any]],
    *,
    pool_name: str,
    family_view: Mapping[str, Any],
    columns: int,
) -> dict[str, Any]:
    signal_field = _live_score_field(pool_name, rows)
    if signal_field is None:
        return {
            "family_view_id": str(family_view["id"]),
            "signal_field": None,
            "row_count": int(len(rows)),
            "scored_row_count": 0,
            "truth_row_count": int(sum(1 for row in rows if _is_finite(row.get("truth_match")))),
            "best_row_truth": float("nan"),
            "selected_row_truth": float("nan"),
            "selected_family_truth": float("nan"),
            "best_family_truth": float("nan"),
            "within_family_regret": float("nan"),
            "between_family_regret": float("nan"),
        }
    scored_rows = [row for row in rows if _is_finite(row.get(signal_field))]
    scored_rows.sort(
        key=lambda row: (-float(row[signal_field]), str(row.get("row_id", "")))
    )
    assignments, _ = cluster_family_ids(rows, family_view=family_view, columns=columns)
    selected_row = scored_rows[0] if scored_rows else None
    best_row_truth = float(
        max(
            (_safe_float(row.get("truth_match")) for row in rows if _is_finite(row.get("truth_match"))),
            default=float("nan"),
        )
    )
    selected_row_truth = (
        _safe_float(selected_row.get("truth_match")) if selected_row is not None else float("nan")
    )

    family_truths: dict[str, float] = {}
    for row in rows:
        row_id = str(row["row_id"])
        family_id = assignments.get(row_id)
        truth_match = _safe_float(row.get("truth_match"))
        if family_id is None or not np.isfinite(truth_match):
            continue
        family_truths[family_id] = max(float(family_truths.get(family_id, float("-inf"))), truth_match)

    selected_family_truth = float("nan")
    if selected_row is not None:
        selected_family_id = assignments.get(str(selected_row["row_id"]))
        if selected_family_id is not None and selected_family_id in family_truths:
            selected_family_truth = float(family_truths[selected_family_id])
    best_family_truth = (
        float(max(family_truths.values())) if family_truths else float("nan")
    )
    within_family_regret = (
        float(selected_family_truth - selected_row_truth)
        if np.isfinite(selected_family_truth) and np.isfinite(selected_row_truth)
        else float("nan")
    )
    between_family_regret = (
        float(best_family_truth - selected_family_truth)
        if np.isfinite(best_family_truth) and np.isfinite(selected_family_truth)
        else float("nan")
    )
    return {
        "family_view_id": str(family_view["id"]),
        "signal_field": str(signal_field),
        "row_count": int(len(rows)),
        "scored_row_count": int(len(scored_rows)),
        "truth_row_count": int(sum(1 for row in rows if _is_finite(row.get("truth_match")))),
        "best_row_truth": float(best_row_truth),
        "selected_row_truth": float(selected_row_truth),
        "selected_family_truth": float(selected_family_truth),
        "best_family_truth": float(best_family_truth),
        "within_family_regret": float(within_family_regret),
        "between_family_regret": float(between_family_regret),
    }


def best_family_truth(alignment_summary: Mapping[str, Any]) -> float:
    """Best family truth is the maximum truth match over families in a pool."""
    return _safe_float(alignment_summary.get("best_family_truth", float("nan")))


def _classification_view_for_pool(
    rows: Sequence[Mapping[str, Any]], *, columns: int
) -> dict[str, Any] | None:
    for view_id in CLASSIFICATION_VIEW_PRIORITY:
        family_view = next(view for view in FAMILY_VIEWS if str(view["id"]) == view_id)
        assignments, _ = cluster_family_ids(rows, family_view=family_view, columns=columns)
        if assignments:
            return family_view
    return None


def classify_run_summary(
    *,
    final_best_match: float,
    latest_alignment: Mapping[str, Any] | None,
    best_seen_truth: float,
    earliest_best_truth: float,
    latest_best_truth: float,
    reference_best_match: float,
    is_reference_success: bool,
) -> dict[str, Any]:
    if is_reference_success:
        return {
            "primary_failure_mode": None,
            "secondary_failure_mode": None,
            "classification_confidence": 1.0,
            "reason": "reference_success",
        }

    latest_between = _safe_float(
        (latest_alignment or {}).get("between_family_regret", float("nan"))
    )
    latest_within = _safe_float(
        (latest_alignment or {}).get("within_family_regret", float("nan"))
    )
    reference_gap = float(reference_best_match - best_seen_truth) if np.isfinite(best_seen_truth) else float("nan")
    collapse_gap = (
        float(earliest_best_truth - latest_best_truth)
        if np.isfinite(earliest_best_truth) and np.isfinite(latest_best_truth)
        else float("nan")
    )
    exploitation_gap = (
        float(best_seen_truth - final_best_match)
        if np.isfinite(best_seen_truth) and np.isfinite(final_best_match)
        else float("nan")
    )

    primary: str | None = None
    secondary: str | None = None
    driver_gap = 0.0
    reason = ""

    if np.isfinite(latest_between) and latest_between >= UNDERVALUE_GAP_MIN:
        primary = "good_family_undervalued"
        driver_gap = float(latest_between)
        reason = "latest_pool_between_family_regret"
        if np.isfinite(reference_gap) and reference_gap >= REFERENCE_GAP_MIN:
            secondary = "good_family_absent"
    elif np.isfinite(collapse_gap) and collapse_gap >= COLLAPSE_GAP_MIN:
        primary = "good_family_collapsed"
        driver_gap = float(collapse_gap)
        reason = "earlier_pool_best_truth_exceeds_latest_pool_best_truth"
        if np.isfinite(reference_gap) and reference_gap >= REFERENCE_GAP_MIN:
            secondary = "good_family_absent"
    elif np.isfinite(reference_gap) and reference_gap >= REFERENCE_GAP_MIN:
        primary = "good_family_absent"
        driver_gap = float(reference_gap)
        reason = "best_seen_family_truth_below_reference_seed_target"
    elif (
        np.isfinite(exploitation_gap)
        and exploitation_gap >= NOT_EXPLOITED_GAP_MIN
    ) or (np.isfinite(latest_within) and latest_within >= NOT_EXPLOITED_GAP_MIN):
        primary = "good_family_not_exploited"
        driver_gap = max(
            float(exploitation_gap) if np.isfinite(exploitation_gap) else 0.0,
            float(latest_within) if np.isfinite(latest_within) else 0.0,
        )
        reason = "selected_family_not_fully_exploited"

    if primary is None:
        return {
            "primary_failure_mode": None,
            "secondary_failure_mode": None,
            "classification_confidence": 0.0,
            "reason": "no_failure_mode_crossed_threshold",
        }

    confidence = min(0.99, 0.55 + (float(driver_gap) * 3.5))
    return {
        "primary_failure_mode": str(primary),
        "secondary_failure_mode": str(secondary) if secondary else None,
        "classification_confidence": float(confidence),
        "reason": str(reason),
    }


def analyze_run(run_spec: Mapping[str, str], reference_best_by_seed: Mapping[int, float]) -> dict[str, Any]:
    artifact_path = REPO_ROOT / str(run_spec["path"])
    artifact = _load_json(artifact_path)
    bundle_dir = artifact_path.parents[1] / "resume_handoffs" / artifact_path.stem
    pools = _extract_pool_rows(
        artifact,
        artifact_path=artifact_path,
        bundle_dir=bundle_dir if bundle_dir.exists() else None,
    )
    columns = _safe_int(artifact.get("columns", 0))
    key_seed = _safe_int(artifact.get("key_seed", artifact.get("seed", 0)))
    final_best_match = _safe_float(artifact.get("best_match_ratio", float("nan")))
    final_best_score = _safe_float(artifact.get("best_score", float("nan")))
    reference_best_match = _safe_float(reference_best_by_seed.get(key_seed, float("nan")))
    is_reference_success = (
        np.isfinite(reference_best_match)
        and np.isfinite(final_best_match)
        and abs(float(reference_best_match - final_best_match)) <= REFERENCE_SUCCESS_EPS
    )

    pool_summaries: dict[str, Any] = {}
    best_seen_truth = float("nan")
    earliest_best_truth = float("nan")
    latest_alignment: dict[str, Any] | None = None
    latest_best_truth = float("nan")

    for pool_name in POOL_ORDER:
        rows = list(pools.get(pool_name, []) or [])
        if not rows:
            continue
        top_band_ids = _select_top_band_row_ids(rows, pool_name=pool_name)
        diversity_views: dict[str, Any] = {}
        for family_view in FAMILY_VIEWS:
            diversity_views[str(family_view["id"])] = summarize_family_block(
                rows,
                family_view=family_view,
                columns=columns,
                selected_row_ids=top_band_ids,
            )

        class_view = _classification_view_for_pool(rows, columns=columns)
        alignment = None
        if class_view is not None:
            alignment = summarize_pool_alignment(
                rows,
                pool_name=pool_name,
                family_view=class_view,
                columns=columns,
            )
            best_truth = best_family_truth(alignment)
            if np.isfinite(best_truth):
                if not np.isfinite(best_seen_truth) or best_truth > best_seen_truth:
                    best_seen_truth = float(best_truth)
                if not np.isfinite(earliest_best_truth):
                    earliest_best_truth = float(best_truth)
                latest_best_truth = float(best_truth)
                latest_alignment = dict(alignment)

        pool_summaries[pool_name] = {
            "row_count": int(len(rows)),
            "selected_top_band_row_count": int(len(top_band_ids)),
            "selected_vs_available": diversity_views,
            "classification_view_id": str(class_view["id"]) if class_view is not None else None,
            "alignment": alignment,
        }

    for pool_name in POOL_PRIORITY_FOR_CLASSIFICATION:
        summary = pool_summaries.get(pool_name)
        alignment = summary.get("alignment") if summary else None
        if alignment is not None and alignment.get("signal_field") is not None:
            latest_alignment = dict(summary["alignment"])
            latest_best_truth = best_family_truth(latest_alignment)
            break

    classification = classify_run_summary(
        final_best_match=final_best_match,
        latest_alignment=latest_alignment,
        best_seen_truth=best_seen_truth,
        earliest_best_truth=earliest_best_truth,
        latest_best_truth=latest_best_truth,
        reference_best_match=reference_best_match,
        is_reference_success=is_reference_success,
    )

    return {
        "run_label": str(run_spec["label"]),
        "artifact_relpath": _repo_rel(artifact_path),
        "key_seed": int(key_seed),
        "final_best_match": float(final_best_match),
        "final_best_score": float(final_best_score),
        "best_stage": str(artifact.get("best_stage", "")),
        "reference_best_match_for_seed": float(reference_best_match),
        "run_role": "reference" if is_reference_success else "comparison",
        "best_seen_family_truth": float(best_seen_truth),
        "latest_best_family_truth": float(latest_best_truth),
        "classification": classification,
        "pool_summaries": pool_summaries,
    }


def build_summary() -> dict[str, Any]:
    runs: list[dict[str, Any]] = []
    reference_best_by_seed: dict[int, float] = {}

    for run_spec in COMPARISON_RUNS:
        artifact = _load_json(REPO_ROOT / str(run_spec["path"]))
        key_seed = _safe_int(artifact.get("key_seed", artifact.get("seed", 0)))
        best_match = _safe_float(artifact.get("best_match_ratio", float("nan")))
        if not np.isfinite(best_match):
            continue
        reference_best_by_seed[key_seed] = max(
            float(reference_best_by_seed.get(key_seed, float("-inf"))),
            float(best_match),
        )

    for run_spec in COMPARISON_RUNS:
        runs.append(analyze_run(run_spec, reference_best_by_seed))

    failure_mode_counts = Counter(
        str(run["classification"]["primary_failure_mode"])
        for run in runs
        if run["classification"]["primary_failure_mode"]
    )
    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "comparison_runs": list(COMPARISON_RUNS),
        "family_views": list(FAMILY_VIEWS),
        "top_band_rank": int(TOP_BAND_RANK),
        "best_family_truth_definition": (
            "For a given pool and family view, best_family_truth is the maximum truth-match "
            "value attained by any row inside the strongest family in that pool."
        ),
        "classification_thresholds": {
            "reference_gap_min": float(REFERENCE_GAP_MIN),
            "collapse_gap_min": float(COLLAPSE_GAP_MIN),
            "undervalue_gap_min": float(UNDERVALUE_GAP_MIN),
            "not_exploited_gap_min": float(NOT_EXPLOITED_GAP_MIN),
            "reference_success_eps": float(REFERENCE_SUCCESS_EPS),
        },
        "reference_best_by_seed": {
            str(seed): float(score) for seed, score in sorted(reference_best_by_seed.items())
        },
        "run_summaries": runs,
        "failure_mode_counts": dict(failure_mode_counts),
    }


def render_report(summary: Mapping[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Basin-Family Diversity and Alignment Audit")
    lines.append("")
    lines.append(
        "This is an offline first-pass audit of basin-family diversity and score-truth alignment "
        "across strong and weak hard-seed `p9/c3` runs."
    )
    lines.append("")
    lines.append("Definition:")
    lines.append(
        f"- `best_family_truth`: {summary['best_family_truth_definition']}"
    )
    lines.append("")
    lines.append("Family views:")
    for view in summary["family_views"]:
        lines.append(f"- `{view['id']}`")
    lines.append("")
    lines.append("Failure-mode counts:")
    for key, count in sorted((summary.get("failure_mode_counts") or {}).items()):
        lines.append(f"- `{key}`: {count}")
    if not summary.get("failure_mode_counts"):
        lines.append("- none")
    lines.append("")

    for run in summary["run_summaries"]:
        lines.append(f"## {run['run_label']}")
        lines.append("")
        lines.append(f"- artifact: `{run['artifact_relpath']}`")
        lines.append(
            f"- final best: match `{run['final_best_match']:.3f}`, score `{run['final_best_score']:.6f}`, stage `{run['best_stage']}`"
        )
        lines.append(
            f"- seed reference best: `{run['reference_best_match_for_seed']:.3f}`"
        )
        classification = run["classification"]
        if run["run_role"] == "reference":
            lines.append("- classification: `reference_success`")
        elif classification["primary_failure_mode"]:
            lines.append(f"- classification: `{classification['primary_failure_mode']}`")
        else:
            lines.append("- classification: `no_failure_mode_crossed_threshold`")
        if classification["secondary_failure_mode"]:
            lines.append(
                f"- secondary: `{classification['secondary_failure_mode']}`"
            )
        lines.append(
            f"- classification_confidence: `{classification['classification_confidence']:.2f}`"
        )
        lines.append(f"- reason: `{classification['reason']}`")
        lines.append("")
        lines.append("Stage pools:")
        for pool_name in POOL_ORDER:
            pool = run["pool_summaries"].get(pool_name)
            if not pool:
                continue
            lines.append(
                f"- `{pool_name}`: rows `{pool['row_count']}`, selected-top-band `{pool['selected_top_band_row_count']}`, classification view `{pool['classification_view_id']}`"
            )
            alignment = pool.get("alignment")
            if alignment:
                lines.append(
                    f"  best family truth `{alignment['best_family_truth']:.3f}`, selected family truth `{alignment['selected_family_truth']:.3f}`, between-family regret `{alignment['between_family_regret']:.3f}`"
                )
            sel_block = pool["selected_vs_available"].get("prefix_hamming_le_24")
            if sel_block is None:
                sel_block = next(iter(pool["selected_vs_available"].values()))
            lines.append(
                f"  selected-vs-available `{sel_block['family_view_id']}`: available families `{sel_block['family_count']}`, selected families `{sel_block['selected_top_band_family_count']}`, top-band family mass `{sel_block['top_band_family_mass_share']:.3f}`"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> dict[str, Any]:
    summary = build_summary()
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    REPORT_PATH.write_text(render_report(summary), encoding="utf-8")
    refresh_catalog_safely()
    return summary


if __name__ == "__main__":
    main()
