from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_LABEL = "scorer_checkpoint_gate_split_validation_v1"

PAIR_DECISIONS_CSV = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_simulation_v1/scorer_checkpoint_gate_simulation_pair_decisions.csv"
)
RULE_SUMMARY_CSV = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_simulation_v1/scorer_checkpoint_gate_simulation_rule_summary.csv"
)
OUTPUT_DIR = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_split_validation_v1"
)

LOW_BREAK_MAX_BREAKS = 10
LOW_BREAK_MAX_UNIQUE_BREAKS = 5
LOW_BREAK_MIN_RESCUES = 30
LOW_BREAK_MIN_UNIQUE_RESCUES = 10
MAX_DOMINANT_OVERRIDE_FRACTION = 0.20
SPLIT_STABLE_MAX_RESCUE_ARTIFACT_FRACTION = 0.25
SPLIT_STABLE_MAX_RESCUE_FIXTURE_SEARCH_FRACTION = 0.60
SPLIT_STABLE_MIN_RESCUE_ARTIFACTS = 8
SPLIT_STABLE_MIN_RESCUE_FIXTURE_SEARCH_CELLS = 4


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _rel(root: Path, rel_path: str) -> Path:
    return root / rel_path


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip()
    if not text:
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _artifact_cell(row: dict[str, str]) -> str:
    return str(row.get("artifact_path", "") or "missing_artifact")


def _fixture_search_cell(row: dict[str, str]) -> str:
    fixture = str(row.get("fixture_seed", "") or row.get("fixture_id", "") or "missing_fixture")
    search = str(row.get("search_seed", "") or "missing_search")
    return f"{fixture}/search{search}"


def _metrics(rows: list[dict[str, str]]) -> dict[str, Any]:
    counts = Counter(str(row.get("outcome", "")) for row in rows)
    fired_rows = [row for row in rows if _safe_int(row.get("gate_fired")) == 1]
    rescue_rows = [row for row in rows if row.get("outcome") == "rescue"]
    break_rows = [row for row in rows if row.get("outcome") == "break"]
    unique_text_pairs = {str(row.get("text_pair_key", "")) for row in rows}
    unique_candidate_pairs = {str(row.get("candidate_pair_key", "")) for row in rows}
    return {
        "pair_count": len(rows),
        "gate_fired_count": len(fired_rows),
        "rescue_count": counts["rescue"],
        "break_count": counts["break"],
        "net_count": counts["rescue"] - counts["break"],
        "same_correct_count": counts["same_correct"],
        "same_wrong_count": counts["same_wrong"],
        "unique_text_pair_count": len(unique_text_pairs - {""}),
        "unique_candidate_pair_count": len(unique_candidate_pairs - {""}),
        "unique_misranked_rescue_pair_count": len({str(row.get("text_pair_key", "")) for row in rescue_rows}),
        "unique_control_break_pair_count": len({str(row.get("text_pair_key", "")) for row in break_rows}),
    }


def _group_rows(rows: list[dict[str, str]], key_fn) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    return dict(grouped)


def _max_fraction(rows: list[dict[str, str]], key_fn, outcome: str | None = None, fired_only: bool = False) -> tuple[int, float, str]:
    selected = rows
    if outcome is not None:
        selected = [row for row in selected if row.get("outcome") == outcome]
    if fired_only:
        selected = [row for row in selected if _safe_int(row.get("gate_fired")) == 1]
    if not selected:
        return 0, 0.0, ""
    counts = Counter(key_fn(row) for row in selected)
    key, count = counts.most_common(1)[0]
    return count, count / len(selected), str(key)


def _rule_robustness(rule_rows: list[dict[str, str]], base_summary: dict[str, str]) -> dict[str, Any]:
    metrics = _metrics(rule_rows)
    by_artifact = _group_rows(rule_rows, _artifact_cell)
    by_fixture = _group_rows(rule_rows, _fixture_search_cell)
    artifact_metrics = {key: _metrics(value) for key, value in by_artifact.items()}
    fixture_metrics = {key: _metrics(value) for key, value in by_fixture.items()}

    artifact_rescue_count = sum(1 for value in artifact_metrics.values() if int(value["rescue_count"]) > 0)
    artifact_break_count = sum(1 for value in artifact_metrics.values() if int(value["break_count"]) > 0)
    fixture_rescue_count = sum(1 for value in fixture_metrics.values() if int(value["rescue_count"]) > 0)
    fixture_break_count = sum(1 for value in fixture_metrics.values() if int(value["break_count"]) > 0)

    max_fired_artifact_count, max_fired_artifact_fraction, max_fired_artifact_key = _max_fraction(
        rule_rows, _artifact_cell, fired_only=True
    )
    max_rescue_artifact_count, max_rescue_artifact_fraction, max_rescue_artifact_key = _max_fraction(
        rule_rows, _artifact_cell, outcome="rescue"
    )
    max_break_artifact_count, max_break_artifact_fraction, max_break_artifact_key = _max_fraction(
        rule_rows, _artifact_cell, outcome="break"
    )
    max_rescue_fixture_count, max_rescue_fixture_fraction, max_rescue_fixture_key = _max_fraction(
        rule_rows, _fixture_search_cell, outcome="rescue"
    )
    max_break_fixture_count, max_break_fixture_fraction, max_break_fixture_key = _max_fraction(
        rule_rows, _fixture_search_cell, outcome="break"
    )

    leave_one_artifact_net_values = [
        int(metrics["net_count"]) - int(value["net_count"]) for value in artifact_metrics.values()
    ]
    leave_one_artifact_rescue_values = [
        int(metrics["rescue_count"]) - int(value["rescue_count"]) for value in artifact_metrics.values()
    ]
    leave_one_artifact_break_values = [
        int(metrics["break_count"]) - int(value["break_count"]) for value in artifact_metrics.values()
    ]
    leave_one_fixture_net_values = [
        int(metrics["net_count"]) - int(value["net_count"]) for value in fixture_metrics.values()
    ]
    leave_one_fixture_rescue_values = [
        int(metrics["rescue_count"]) - int(value["rescue_count"]) for value in fixture_metrics.values()
    ]
    leave_one_fixture_break_values = [
        int(metrics["break_count"]) - int(value["break_count"]) for value in fixture_metrics.values()
    ]
    low_break_signal = (
        int(metrics["break_count"]) <= LOW_BREAK_MAX_BREAKS
        and int(metrics["unique_control_break_pair_count"]) <= LOW_BREAK_MAX_UNIQUE_BREAKS
        and int(metrics["rescue_count"]) >= LOW_BREAK_MIN_RESCUES
        and int(metrics["unique_misranked_rescue_pair_count"]) >= LOW_BREAK_MIN_UNIQUE_RESCUES
        and float(base_summary.get("dominant_override_pair_fraction", 0) or 0) <= MAX_DOMINANT_OVERRIDE_FRACTION
    )
    split_stable_candidate = (
        low_break_signal
        and artifact_rescue_count >= SPLIT_STABLE_MIN_RESCUE_ARTIFACTS
        and fixture_rescue_count >= SPLIT_STABLE_MIN_RESCUE_FIXTURE_SEARCH_CELLS
        and max_rescue_artifact_fraction <= SPLIT_STABLE_MAX_RESCUE_ARTIFACT_FRACTION
        and max_rescue_fixture_fraction <= SPLIT_STABLE_MAX_RESCUE_FIXTURE_SEARCH_FRACTION
    )
    return {
        "rule_id": base_summary["rule_id"],
        "family": base_summary.get("family", ""),
        **metrics,
        "artifact_count": len(artifact_metrics),
        "fixture_search_count": len(fixture_metrics),
        "artifact_with_rescue_count": artifact_rescue_count,
        "artifact_with_break_count": artifact_break_count,
        "fixture_search_with_rescue_count": fixture_rescue_count,
        "fixture_search_with_break_count": fixture_break_count,
        "max_fired_artifact_count": max_fired_artifact_count,
        "max_fired_artifact_fraction": max_fired_artifact_fraction,
        "max_fired_artifact_key": max_fired_artifact_key,
        "max_rescue_artifact_count": max_rescue_artifact_count,
        "max_rescue_artifact_fraction": max_rescue_artifact_fraction,
        "max_rescue_artifact_key": max_rescue_artifact_key,
        "max_break_artifact_count": max_break_artifact_count,
        "max_break_artifact_fraction": max_break_artifact_fraction,
        "max_break_artifact_key": max_break_artifact_key,
        "max_rescue_fixture_search_count": max_rescue_fixture_count,
        "max_rescue_fixture_search_fraction": max_rescue_fixture_fraction,
        "max_rescue_fixture_search_key": max_rescue_fixture_key,
        "max_break_fixture_search_count": max_break_fixture_count,
        "max_break_fixture_search_fraction": max_break_fixture_fraction,
        "max_break_fixture_search_key": max_break_fixture_key,
        "leave_one_artifact_min_net": min(leave_one_artifact_net_values) if leave_one_artifact_net_values else 0,
        "leave_one_artifact_min_rescues": min(leave_one_artifact_rescue_values) if leave_one_artifact_rescue_values else 0,
        "leave_one_artifact_max_breaks": max(leave_one_artifact_break_values) if leave_one_artifact_break_values else 0,
        "leave_one_fixture_search_min_net": min(leave_one_fixture_net_values) if leave_one_fixture_net_values else 0,
        "leave_one_fixture_search_min_rescues": min(leave_one_fixture_rescue_values) if leave_one_fixture_rescue_values else 0,
        "leave_one_fixture_search_max_breaks": max(leave_one_fixture_break_values) if leave_one_fixture_break_values else 0,
        "global_dominant_override_pair_fraction": _safe_float(base_summary.get("dominant_override_pair_fraction")),
        "low_break_signal": int(low_break_signal),
        "split_stable_candidate": int(split_stable_candidate),
        "review_status": _review_status(
            metrics=metrics,
            base_summary=base_summary,
            low_break_signal=low_break_signal,
            split_stable_candidate=split_stable_candidate,
            artifact_rescue_count=artifact_rescue_count,
            fixture_rescue_count=fixture_rescue_count,
            max_rescue_artifact_fraction=max_rescue_artifact_fraction,
            max_rescue_fixture_fraction=max_rescue_fixture_fraction,
        ),
    }


def _review_status(
    metrics: dict[str, Any],
    base_summary: dict[str, str],
    low_break_signal: bool | None = None,
    split_stable_candidate: bool | None = None,
    artifact_rescue_count: int | None = None,
    fixture_rescue_count: int | None = None,
    max_rescue_artifact_fraction: float | None = None,
    max_rescue_fixture_fraction: float | None = None,
) -> str:
    breaks = int(metrics["break_count"])
    rescues = int(metrics["rescue_count"])
    unique_breaks = int(metrics["unique_control_break_pair_count"])
    unique_rescues = int(metrics["unique_misranked_rescue_pair_count"])
    dominant = _safe_float(base_summary.get("dominant_override_pair_fraction"))
    if low_break_signal is None:
        low_break_signal = (
            breaks <= LOW_BREAK_MAX_BREAKS
            and unique_breaks <= LOW_BREAK_MAX_UNIQUE_BREAKS
            and rescues >= LOW_BREAK_MIN_RESCUES
            and unique_rescues >= LOW_BREAK_MIN_UNIQUE_RESCUES
            and dominant <= MAX_DOMINANT_OVERRIDE_FRACTION
        )
    if split_stable_candidate is None:
        artifact_rescue_count = 0 if artifact_rescue_count is None else artifact_rescue_count
        fixture_rescue_count = 0 if fixture_rescue_count is None else fixture_rescue_count
        max_rescue_artifact_fraction = 0.0 if max_rescue_artifact_fraction is None else max_rescue_artifact_fraction
        max_rescue_fixture_fraction = 0.0 if max_rescue_fixture_fraction is None else max_rescue_fixture_fraction
        split_stable_candidate = (
            low_break_signal
            and artifact_rescue_count >= SPLIT_STABLE_MIN_RESCUE_ARTIFACTS
            and fixture_rescue_count >= SPLIT_STABLE_MIN_RESCUE_FIXTURE_SEARCH_CELLS
            and max_rescue_artifact_fraction <= SPLIT_STABLE_MAX_RESCUE_ARTIFACT_FRACTION
            and max_rescue_fixture_fraction <= SPLIT_STABLE_MAX_RESCUE_FIXTURE_SEARCH_FRACTION
        )
    if rescues == 0:
        return "no_signal"
    if dominant > MAX_DOMINANT_OVERRIDE_FRACTION:
        return "dominance_risk"
    if low_break_signal:
        if split_stable_candidate:
            return "split_stable_candidate"
        return "low_break_split_concentration_risk"
    if breaks <= LOW_BREAK_MAX_BREAKS and unique_breaks <= LOW_BREAK_MAX_UNIQUE_BREAKS:
        return "clean_but_sparse"
    if breaks <= 25:
        return "moderate_break_review"
    return "too_many_breaks"


def _split_rows(rule_rows_by_id: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule_id, rule_rows in sorted(rule_rows_by_id.items()):
        for split_type, key_fn in (("artifact", _artifact_cell), ("fixture_search", _fixture_search_cell)):
            grouped = _group_rows(rule_rows, key_fn)
            for split_key, split_rule_rows in sorted(grouped.items()):
                rows.append(
                    {
                        "rule_id": rule_id,
                        "split_type": split_type,
                        "split_key": split_key,
                        **_metrics(split_rule_rows),
                    }
                )
    return rows


def run() -> dict[str, Any]:
    root = _repo_root()
    output_dir = _rel(root, OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions = _read_csv(_rel(root, PAIR_DECISIONS_CSV))
    base_summary_rows = _read_csv(_rel(root, RULE_SUMMARY_CSV))
    base_by_rule = {row["rule_id"]: row for row in base_summary_rows}

    rule_rows_by_id = _group_rows(decisions, lambda row: str(row.get("rule_id", "")))
    missing_summary_rules = sorted(set(rule_rows_by_id) - set(base_by_rule))
    dropped_summary_rules = sorted(set(base_by_rule) - set(rule_rows_by_id))

    robustness_rows = [
        _rule_robustness(rule_rows, base_by_rule[rule_id])
        for rule_id, rule_rows in sorted(rule_rows_by_id.items())
        if rule_id in base_by_rule
    ]
    robustness_rows.sort(
        key=lambda row: (
            -int(row["split_stable_candidate"]),
            -int(row["low_break_signal"]),
            -int(row["net_count"]),
            int(row["break_count"]),
            -int(row["rescue_count"]),
            str(row["rule_id"]),
        )
    )
    split_rows = _split_rows(rule_rows_by_id)

    expected_decision_rows = len(base_summary_rows) * int(base_summary_rows[0]["pair_count"]) if base_summary_rows else 0
    row_conservation_ok = expected_decision_rows == len(decisions)
    status_counts = Counter(str(row["review_status"]) for row in robustness_rows)
    top_split_stable_candidates = [row for row in robustness_rows if int(row["split_stable_candidate"]) == 1][:20]
    low_break_signals = [row for row in robustness_rows if int(row["low_break_signal"]) == 1]

    rule_fields = [
        "rule_id",
        "family",
        "review_status",
        "low_break_signal",
        "split_stable_candidate",
        "pair_count",
        "gate_fired_count",
        "rescue_count",
        "break_count",
        "net_count",
        "same_correct_count",
        "same_wrong_count",
        "unique_text_pair_count",
        "unique_candidate_pair_count",
        "unique_misranked_rescue_pair_count",
        "unique_control_break_pair_count",
        "artifact_count",
        "fixture_search_count",
        "artifact_with_rescue_count",
        "artifact_with_break_count",
        "fixture_search_with_rescue_count",
        "fixture_search_with_break_count",
        "max_fired_artifact_count",
        "max_fired_artifact_fraction",
        "max_fired_artifact_key",
        "max_rescue_artifact_count",
        "max_rescue_artifact_fraction",
        "max_rescue_artifact_key",
        "max_break_artifact_count",
        "max_break_artifact_fraction",
        "max_break_artifact_key",
        "max_rescue_fixture_search_count",
        "max_rescue_fixture_search_fraction",
        "max_rescue_fixture_search_key",
        "max_break_fixture_search_count",
        "max_break_fixture_search_fraction",
        "max_break_fixture_search_key",
        "leave_one_artifact_min_net",
        "leave_one_artifact_min_rescues",
        "leave_one_artifact_max_breaks",
        "leave_one_fixture_search_min_net",
        "leave_one_fixture_search_min_rescues",
        "leave_one_fixture_search_max_breaks",
        "global_dominant_override_pair_fraction",
    ]
    split_fields = [
        "rule_id",
        "split_type",
        "split_key",
        "pair_count",
        "gate_fired_count",
        "rescue_count",
        "break_count",
        "net_count",
        "same_correct_count",
        "same_wrong_count",
        "unique_text_pair_count",
        "unique_candidate_pair_count",
        "unique_misranked_rescue_pair_count",
        "unique_control_break_pair_count",
    ]
    _write_csv(output_dir / "scorer_checkpoint_gate_split_validation_rule_summary.csv", robustness_rows, rule_fields)
    _write_csv(output_dir / "scorer_checkpoint_gate_split_validation_split_rows.csv", split_rows, split_fields)

    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": OUTPUT_DIR,
        "report_only": True,
        "runtime_changed": False,
        "truth_fields_are_evaluation_only": True,
        "decision_row_count": len(decisions),
        "rule_count": len(base_summary_rows),
        "rules_with_decisions_count": len(rule_rows_by_id),
        "expected_decision_row_count": expected_decision_rows,
        "row_conservation_ok": row_conservation_ok,
        "missing_summary_rules": missing_summary_rules,
        "dropped_summary_rules": dropped_summary_rules,
        "review_status_counts": dict(sorted(status_counts.items())),
        "low_break_signal_count": len(low_break_signals),
        "split_stable_candidate_count": len(top_split_stable_candidates),
        "top_low_break_signals": low_break_signals[:10],
        "top_split_stable_candidates": top_split_stable_candidates[:10],
        "caveats": [
            "This validates the existing Stage 2 shadow decisions; it does not fit or tune new rules.",
            "Truth labels are evaluation-only.",
            "This is split/dominance validation on the same historical S1 evidence, not fresh held-out solver data.",
            "All Stage 2 rules remain in the output tables.",
        ],
    }
    (output_dir / "scorer_checkpoint_gate_split_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_readout(
        output_dir / "scorer_checkpoint_gate_split_validation_readout.md",
        summary,
        top_split_stable_candidates,
        low_break_signals,
    )
    return summary


def _table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No rules met the low-break candidate filter."]
    out = [
        "| rule | family | status | rescues | breaks | net | unique rescues | unique breaks | rescue artifacts | rescue fixtures | max rescue artifact frac |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            "| "
            f"{row['rule_id']} | {row['family']} | {row['review_status']} | "
            f"{row['rescue_count']} | {row['break_count']} | {row['net_count']} | "
            f"{row['unique_misranked_rescue_pair_count']} | {row['unique_control_break_pair_count']} | "
            f"{row['artifact_with_rescue_count']} | {row['fixture_search_with_rescue_count']} | "
            f"{float(row['max_rescue_artifact_fraction']):.3f} |"
        )
    return out


def _write_readout(
    path: Path,
    summary: dict[str, Any],
    split_stable_candidates: list[dict[str, Any]],
    low_break_signals: list[dict[str, Any]],
) -> None:
    lines = [
        "# Scorer Checkpoint Gate Split Validation v1",
        "",
        "## Purpose",
        "",
        "Validate Stage 2 report-only gate simulations by split coverage, dominance, and low-break discipline.",
        "",
        "## Row Conservation",
        "",
        f"- decision rows: {summary['decision_row_count']}",
        f"- expected decision rows: {summary['expected_decision_row_count']}",
        f"- row conservation ok: `{summary['row_conservation_ok']}`",
        f"- rules: {summary['rule_count']}",
        f"- rules with decisions: {summary['rules_with_decisions_count']}",
        "",
        "## Review Status Counts",
        "",
    ]
    for key, value in sorted(summary["review_status_counts"].items()):
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            "## Split-Stable Candidates",
            "",
            *_table(split_stable_candidates[:15]),
            "",
            "## Low-Break Signals With Split Caveats",
            "",
            *_table(low_break_signals[:15]),
            "",
            "## Interpretation",
            "",
            "Split-stable candidates are candidates for stricter held-out or shadow-selector validation, not runtime promotion. Low-break signals that are not split-stable must be treated as concentration risks.",
            "",
            "## Caveats",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["caveats"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    out = run()
    print(
        f"{RUN_LABEL}: rows={out['decision_row_count']} rules={out['rule_count']} "
        f"split_stable_candidates={out['split_stable_candidate_count']} "
        f"output_dir={out['output_dir']}"
    )
