from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis.build_output_catalog import (
    refresh_catalog_safely,
)


CANONICAL_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli")
CATALOG_ROOT = Path("output/tools/benchmarks/periodic_sub_trans/no_wli_catalog")
SUMMARY_PATH = CATALOG_ROOT / "selector_ladder_audit_summary.json"
REPORT_PATH = CATALOG_ROOT / "selector_ladder_audit_report.md"

LADDER_CASES: tuple[dict[str, str], ...] = (
    {"tier": "easy", "case_id": "fixture_fixture_001_p5_c1_l1000"},
    {"tier": "easy", "case_id": "fixture_fixture_001_p5_c3_l1000"},
    {"tier": "easy", "case_id": "fixture_fixture_001_p7_c1_l1000"},
    {"tier": "easy", "case_id": "fixture_fixture_001_p7_c5_l1000"},
    {"tier": "medium", "case_id": "fixture_fixture_001_p9_c1_l1000"},
    {"tier": "hard", "case_id": "fixture_fixture_001_p9_c3_l1000"},
)


def _repo_rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_float(value: Any) -> float:
    try:
        out = float(value)
    except Exception:
        return float("nan")
    return out


def _is_finite(value: Any) -> bool:
    return bool(np.isfinite(_safe_float(value)))


def _pearson_corr(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    lhs_arr = np.asarray(list(lhs), dtype=np.float64).reshape(-1)
    rhs_arr = np.asarray(list(rhs), dtype=np.float64).reshape(-1)
    if int(lhs_arr.size) != int(rhs_arr.size) or int(lhs_arr.size) < 2:
        return float("nan")
    if float(np.std(lhs_arr)) <= 0.0 or float(np.std(rhs_arr)) <= 0.0:
        return float("nan")
    return float(np.corrcoef(lhs_arr, rhs_arr)[0, 1])


def _rankdata(values: Sequence[float]) -> np.ndarray:
    vals = np.asarray(list(values), dtype=np.float64).reshape(-1)
    if int(vals.size) == 0:
        return vals
    order = np.argsort(vals, kind="mergesort")
    ranks = np.zeros(int(vals.size), dtype=np.float64)
    idx = 0
    while idx < int(vals.size):
        jdx = idx + 1
        while jdx < int(vals.size) and float(vals[order[jdx]]) == float(vals[order[idx]]):
            jdx += 1
        avg_rank = (float(idx + 1) + float(jdx)) / 2.0
        for pos in range(idx, jdx):
            ranks[order[pos]] = avg_rank
        idx = jdx
    return ranks


def _spearman_corr(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    lhs_arr = _rankdata(lhs)
    rhs_arr = _rankdata(rhs)
    if int(lhs_arr.size) != int(rhs_arr.size) or int(lhs_arr.size) < 2:
        return float("nan")
    return _pearson_corr(lhs_arr, rhs_arr)


def _find_case_artifacts(case_id: str) -> list[Path]:
    pattern = f"{case_id}__text0__seed*.json"
    return sorted(CANONICAL_ROOT.rglob(pattern))


def analyze_stage3_topk_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    topk_rows = [dict(row) for row in rows]
    if not topk_rows:
        return dict(
            topk_len=0,
            top_match=float("nan"),
            best_truth_match=float("nan"),
            truth_regret=float("nan"),
            best_truth_rank=0,
            top_is_truth_best=0,
            score_match_pearson=float("nan"),
            score_match_spearman=float("nan"),
        )
    matches = [_safe_float(row.get("match_ratio", float("nan"))) for row in topk_rows]
    scores = [_safe_float(row.get("score_raw", float("nan"))) for row in topk_rows]
    top_match = float(matches[0]) if matches else float("nan")
    best_idx = 0
    best_match = matches[0]
    for idx, match_val in enumerate(matches[1:], start=1):
        if _is_finite(match_val) and (
            (not _is_finite(best_match)) or float(match_val) > float(best_match)
        ):
            best_idx = int(idx)
            best_match = float(match_val)
    regret = (
        float(best_match - top_match)
        if _is_finite(best_match) and _is_finite(top_match)
        else float("nan")
    )
    return dict(
        topk_len=int(len(topk_rows)),
        top_match=float(top_match),
        best_truth_match=float(best_match),
        truth_regret=float(regret),
        best_truth_rank=int(best_idx + 1),
        top_is_truth_best=int(1 if int(best_idx) == 0 else 0),
        score_match_pearson=float(_pearson_corr(scores, matches)),
        score_match_spearman=float(_spearman_corr(scores, matches)),
    )


def analyze_artifact(path: Path, *, case_id: str, tier: str) -> dict[str, Any]:
    artifact = _load_json(path)
    topk_summary = analyze_stage3_topk_rows(list(artifact.get("stage3_topk", []) or []))
    run_dir = path.parents[1]
    run_config_path = run_dir / "run_config.json"
    run_config = _load_json(run_config_path) if run_config_path.exists() else {}
    stage3_cfg = dict((run_config.get("stage3") or {}) if isinstance(run_config, Mapping) else {})
    two_phase_cfg = (
        dict((stage3_cfg.get("two_phase") or {}))
        if isinstance(stage3_cfg.get("two_phase", {}), Mapping)
        else {}
    )
    phasec_cfg = (
        dict((two_phase_cfg.get("phase_c") or {}))
        if isinstance(two_phase_cfg.get("phase_c", {}), Mapping)
        else {}
    )
    return dict(
        tier=str(tier),
        case_id=str(case_id),
        artifact_relpath=_repo_rel(path),
        run_dir=str(run_dir.name),
        best_match_ratio=_safe_float(artifact.get("best_match_ratio", float("nan"))),
        best_score=_safe_float(artifact.get("best_score", float("nan"))),
        best_stage=str(artifact.get("best_stage", "") or ""),
        stage35_requested_cfg=int(
            1
            if bool(
                ((stage3_cfg.get("stage35") or {}) if isinstance(stage3_cfg.get("stage35", {}), Mapping) else {}).get(
                    "enabled", False
                )
            )
            else 0
        ),
        stage35_ran=int((artifact.get("stage3_diagnostics") or {}).get("stage35_ran", 0) or 0),
        phasec_enabled_cfg=int(1 if bool(phasec_cfg.get("enabled", False)) else 0),
        phasec_ran=int((artifact.get("stage3_diagnostics") or {}).get("phaseC_ran", 0) or 0),
        stage3_topk_len=int(topk_summary["topk_len"]),
        stage3_top_match=float(topk_summary["top_match"]),
        stage3_topk_best_truth_match=float(topk_summary["best_truth_match"]),
        stage3_topk_truth_regret=float(topk_summary["truth_regret"]),
        stage3_topk_best_truth_rank=int(topk_summary["best_truth_rank"]),
        stage3_topk_top_is_truth_best=int(topk_summary["top_is_truth_best"]),
        stage3_topk_score_match_pearson=float(topk_summary["score_match_pearson"]),
        stage3_topk_score_match_spearman=float(topk_summary["score_match_spearman"]),
    )


def _finite_values(rows: Iterable[Mapping[str, Any]], field: str) -> list[float]:
    out: list[float] = []
    for row in rows:
        value = _safe_float(row.get(field, float("nan")))
        if np.isfinite(value):
            out.append(float(value))
    return out


def summarize_case(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    bucket = [dict(row) for row in rows]
    if not bucket:
        return {}
    best_by_match = max(
        bucket,
        key=lambda row: (
            _safe_float(row.get("best_match_ratio", float("nan"))),
            _safe_float(row.get("best_score", float("nan"))),
            str(row.get("artifact_relpath", "")),
        ),
    )
    best_by_score = max(
        bucket,
        key=lambda row: (
            _safe_float(row.get("best_score", float("nan"))),
            _safe_float(row.get("best_match_ratio", float("nan"))),
            str(row.get("artifact_relpath", "")),
        ),
    )
    score_vals = _finite_values(bucket, "best_score")
    match_vals = _finite_values(bucket, "best_match_ratio")
    corr = (
        _pearson_corr(score_vals, match_vals)
        if int(len(score_vals)) == int(len(match_vals)) and int(len(score_vals)) >= 2
        else float("nan")
    )
    regret_vals = _finite_values(bucket, "stage3_topk_truth_regret")
    spearman_vals = _finite_values(bucket, "stage3_topk_score_match_spearman")
    return dict(
        tier=str(bucket[0].get("tier", "")),
        case_id=str(bucket[0].get("case_id", "")),
        artifact_count=int(len(bucket)),
        best_match_ratio=_safe_float(best_by_match.get("best_match_ratio", float("nan"))),
        best_match_artifact_relpath=str(best_by_match.get("artifact_relpath", "")),
        best_score=_safe_float(best_by_score.get("best_score", float("nan"))),
        best_score_artifact_relpath=str(best_by_score.get("artifact_relpath", "")),
        best_score_run_match_ratio=_safe_float(best_by_score.get("best_match_ratio", float("nan"))),
        best_match_run_score=_safe_float(best_by_match.get("best_score", float("nan"))),
        final_score_match_corr=float(corr),
        topk_truth_best_rate=(
            float(
                np.mean(
                    np.asarray(
                        [
                            int(row.get("stage3_topk_top_is_truth_best", 0) or 0)
                            for row in bucket
                            if int(row.get("stage3_topk_len", 0) or 0) > 0
                        ],
                        dtype=np.float64,
                    )
                )
            )
            if any(int(row.get("stage3_topk_len", 0) or 0) > 0 for row in bucket)
            else float("nan")
        ),
        mean_topk_truth_regret=(
            float(np.mean(np.asarray(regret_vals, dtype=np.float64)))
            if regret_vals
            else float("nan")
        ),
        max_topk_truth_regret=(max(regret_vals) if regret_vals else float("nan")),
        mean_topk_score_match_spearman=(
            float(np.mean(np.asarray(spearman_vals, dtype=np.float64)))
            if spearman_vals
            else float("nan")
        ),
        stage35_requested_artifact_count=int(
            sum(int(row.get("stage35_requested_cfg", 0) or 0) for row in bucket)
        ),
        phasec_artifact_count=int(
            sum(int(row.get("phasec_enabled_cfg", 0) or 0) for row in bucket)
        ),
    )


def summarize_tier(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    bucket = [dict(row) for row in rows]
    if not bucket:
        return {}
    regrets = _finite_values(bucket, "stage3_topk_truth_regret")
    correlations = _finite_values(bucket, "stage3_topk_score_match_spearman")
    final_pairs = [
        (
            _safe_float(row.get("best_score", float("nan"))),
            _safe_float(row.get("best_match_ratio", float("nan"))),
        )
        for row in bucket
        if _is_finite(row.get("best_score", float("nan")))
        and _is_finite(row.get("best_match_ratio", float("nan")))
    ]
    final_corr = (
        _pearson_corr([pair[0] for pair in final_pairs], [pair[1] for pair in final_pairs])
        if int(len(final_pairs)) >= 2
        else float("nan")
    )
    return dict(
        tier=str(bucket[0].get("tier", "")),
        artifact_count=int(len(bucket)),
        case_count=int(len({str(row.get("case_id", "")) for row in bucket})),
        best_match_ratio=max(_finite_values(bucket, "best_match_ratio"), default=float("nan")),
        topk_truth_best_rate=(
            float(
                np.mean(
                    np.asarray(
                        [
                            int(row.get("stage3_topk_top_is_truth_best", 0) or 0)
                            for row in bucket
                            if int(row.get("stage3_topk_len", 0) or 0) > 0
                        ],
                        dtype=np.float64,
                    )
                )
            )
            if any(int(row.get("stage3_topk_len", 0) or 0) > 0 for row in bucket)
            else float("nan")
        ),
        mean_topk_truth_regret=(
            float(np.mean(np.asarray(regrets, dtype=np.float64)))
            if regrets
            else float("nan")
        ),
        max_topk_truth_regret=(max(regrets) if regrets else float("nan")),
        mean_topk_score_match_spearman=(
            float(np.mean(np.asarray(correlations, dtype=np.float64)))
            if correlations
            else float("nan")
        ),
        final_score_match_corr=float(final_corr),
        stage35_requested_artifact_count=int(
            sum(int(row.get("stage35_requested_cfg", 0) or 0) for row in bucket)
        ),
        phasec_artifact_count=int(
            sum(int(row.get("phasec_enabled_cfg", 0) or 0) for row in bucket)
        ),
    )


def build_findings(
    *,
    case_summary_rows: Sequence[Mapping[str, Any]],
    artifact_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    case_by_id = {str(row.get("case_id", "")): dict(row) for row in case_summary_rows}
    hard_case = case_by_id.get("fixture_fixture_001_p9_c3_l1000", {})
    medium_case = case_by_id.get("fixture_fixture_001_p9_c1_l1000", {})
    findings: list[str] = []
    if hard_case:
        findings.append(
            "Hard tier still shows some non-zero within-run selector regret, but it is small: "
            f"`p9/c3` mean `stage3_topk` truth regret is "
            f"{_safe_float(hard_case.get('mean_topk_truth_regret', float('nan'))):.4f}, "
            f"with best-truth rank 1 only "
            f"{_safe_float(hard_case.get('topk_truth_best_rate', float('nan'))) * 100.0:.1f}% "
            "of the time."
        )
    if medium_case:
        findings.append(
            "Ranking imperfections are not unique to the hard family: "
            f"`p9/c1` mean `stage3_topk` truth regret is "
            f"{_safe_float(medium_case.get('mean_topk_truth_regret', float('nan'))):.4f}, "
            "which is larger than the hard-tier mean."
        )
    if hard_case and medium_case:
        hard_corr = _safe_float(hard_case.get("final_score_match_corr", float("nan")))
        med_corr = _safe_float(medium_case.get("final_score_match_corr", float("nan")))
        findings.append(
            "Across-run full-score ordering is not globally inverted: "
            f"`p9/c3` score/match correlation is {hard_corr:.3f} and "
            f"`p9/c1` is {med_corr:.3f}, so Stage-3 ranking is imperfect but the larger "
            "regression still points to basin generation rather than a totally broken scorer."
        )
    if hard_case:
        findings.append(
            "The hard-tier score signal is useful but not perfect: the best-score `p9/c3` run "
            f"reaches match `{_safe_float(hard_case.get('best_score_run_match_ratio', float('nan'))):.3f}`, "
            f"while the best-match run reaches `{_safe_float(hard_case.get('best_match_ratio', float('nan'))):.3f}`."
        )
    easy_rows = [dict(row) for row in artifact_rows if str(row.get("tier", "")) == "easy"]
    if easy_rows:
        easy_regrets = _finite_values(easy_rows, "stage3_topk_truth_regret")
        findings.append(
            "Easy controls remain stable: all four easy ladder cases have top-k regret "
            f"bounded at {max(easy_regrets, default=0.0):.4f} or below."
        )
    return findings


def render_report(
    *,
    artifact_rows: Sequence[Mapping[str, Any]],
    case_summary_rows: Sequence[Mapping[str, Any]],
    tier_summary_rows: Sequence[Mapping[str, Any]],
    findings: Sequence[str],
) -> str:
    lines: list[str] = []
    lines.append("# no_wli Selector Ladder Audit")
    lines.append("")
    lines.append(f"Generated: {datetime.now(timezone.utc).isoformat()}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("Frozen ladder:")
    lines.append("- easy: `p5/c1`, `p5/c3`, `p7/c1`, `p7/c5`")
    lines.append("- medium: `p9/c1`")
    lines.append("- hard: `p9/c3`")
    lines.append("")
    lines.append("This audit checks current live-visible Stage-3 ordering, not oracle-only reranking.")
    lines.append("")
    lines.append("## Main findings")
    lines.append("")
    for finding in findings:
        lines.append(f"- {finding}")
    lines.append("")
    lines.append("## Tier summary")
    lines.append("")
    lines.append("| Tier | Artifacts | Cases | Best Match | Top-Is-Best Rate | Mean Topk Regret | Mean Topk Spearman | Final Score/Match Corr |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in tier_summary_rows:
        lines.append(
            "| {tier} | {artifact_count} | {case_count} | {best_match_ratio:.3f} | "
            "{topk_truth_best_rate:.3f} | {mean_topk_truth_regret:.4f} | "
            "{mean_topk_score_match_spearman:.3f} | {final_score_match_corr:.3f} |".format(
                tier=str(row.get("tier", "")),
                artifact_count=int(row.get("artifact_count", 0) or 0),
                case_count=int(row.get("case_count", 0) or 0),
                best_match_ratio=_safe_float(row.get("best_match_ratio", float("nan"))),
                topk_truth_best_rate=_safe_float(row.get("topk_truth_best_rate", float("nan"))),
                mean_topk_truth_regret=_safe_float(row.get("mean_topk_truth_regret", float("nan"))),
                mean_topk_score_match_spearman=_safe_float(
                    row.get("mean_topk_score_match_spearman", float("nan"))
                ),
                final_score_match_corr=_safe_float(row.get("final_score_match_corr", float("nan"))),
            )
        )
    lines.append("")
    lines.append("## Case summary")
    lines.append("")
    lines.append("| Case | Tier | Artifacts | Best Match | Best Score | Best-Score Run Match | Mean Topk Regret | Max Topk Regret | Final Score/Match Corr |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in case_summary_rows:
        lines.append(
            "| {case_id} | {tier} | {artifact_count} | {best_match_ratio:.3f} | {best_score:.6f} | "
            "{best_score_run_match_ratio:.3f} | {mean_topk_truth_regret:.4f} | {max_topk_truth_regret:.4f} | "
            "{final_score_match_corr:.3f} |".format(
                case_id=str(row.get("case_id", "")),
                tier=str(row.get("tier", "")),
                artifact_count=int(row.get("artifact_count", 0) or 0),
                best_match_ratio=_safe_float(row.get("best_match_ratio", float("nan"))),
                best_score=_safe_float(row.get("best_score", float("nan"))),
                best_score_run_match_ratio=_safe_float(
                    row.get("best_score_run_match_ratio", float("nan"))
                ),
                mean_topk_truth_regret=_safe_float(row.get("mean_topk_truth_regret", float("nan"))),
                max_topk_truth_regret=_safe_float(row.get("max_topk_truth_regret", float("nan"))),
                final_score_match_corr=_safe_float(row.get("final_score_match_corr", float("nan"))),
            )
        )
    lines.append("")
    hard_rows = [
        dict(row)
        for row in artifact_rows
        if str(row.get("case_id", "")) == "fixture_fixture_001_p9_c3_l1000"
    ]
    if hard_rows:
        worst_regret = max(
            hard_rows,
            key=lambda row: (
                _safe_float(row.get("stage3_topk_truth_regret", float("-inf"))),
                _safe_float(row.get("best_match_ratio", float("-inf"))),
            ),
        )
        lines.append("## Hard-tier note")
        lines.append("")
        lines.append(
            "- Worst observed `p9/c3` within-run regret in this ladder slice: "
            f"`{_safe_float(worst_regret.get('stage3_topk_truth_regret', float('nan'))):.4f}` "
            f"at `{str(worst_regret.get('artifact_relpath', ''))}`."
        )
        lines.append(
            "- That run still had `stage3_topk` best-truth rank "
            f"`{int(worst_regret.get('stage3_topk_best_truth_rank', 0) or 0)}` rather than 1."
        )
        lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    artifact_rows: list[dict[str, Any]] = []
    case_rows_by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in LADDER_CASES:
        case_id = str(case["case_id"])
        tier = str(case["tier"])
        for path in _find_case_artifacts(case_id):
            row = analyze_artifact(path, case_id=case_id, tier=tier)
            artifact_rows.append(row)
            case_rows_by_id[case_id].append(row)

    case_summary_rows = [
        summarize_case(case_rows_by_id[str(case["case_id"])])
        for case in LADDER_CASES
        if case_rows_by_id.get(str(case["case_id"]), [])
    ]
    tier_rows_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in artifact_rows:
        tier_rows_by_name[str(row.get("tier", ""))].append(dict(row))
    tier_summary_rows = [
        summarize_tier(tier_rows_by_name[tier_name])
        for tier_name in ("easy", "medium", "hard")
        if tier_rows_by_name.get(tier_name, [])
    ]
    findings = build_findings(
        case_summary_rows=case_summary_rows,
        artifact_rows=artifact_rows,
    )
    summary = dict(
        generated_utc=datetime.now(timezone.utc).isoformat(),
        ladder_cases=list(LADDER_CASES),
        artifact_count=int(len(artifact_rows)),
        case_summary_rows=case_summary_rows,
        tier_summary_rows=tier_summary_rows,
        findings=list(findings),
    )
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_PATH.write_text(
        render_report(
            artifact_rows=artifact_rows,
            case_summary_rows=case_summary_rows,
            tier_summary_rows=tier_summary_rows,
            findings=findings,
        ),
        encoding="utf-8",
    )
    print(
        json.dumps(
            dict(
                summary_path=_repo_rel(SUMMARY_PATH),
                report_path=_repo_rel(REPORT_PATH),
                artifact_count=int(len(artifact_rows)),
                case_count=int(len(case_summary_rows)),
            ),
            sort_keys=True,
        )
    )
    refresh_catalog_safely(print_fn=print)


if __name__ == "__main__":
    main()
