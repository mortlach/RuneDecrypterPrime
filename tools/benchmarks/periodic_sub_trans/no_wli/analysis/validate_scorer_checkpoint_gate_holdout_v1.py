from __future__ import annotations

import csv
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


RUN_LABEL = "scorer_checkpoint_gate_holdout_validation_v1"

PAIR_DECISIONS_CSV = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_simulation_v1/scorer_checkpoint_gate_simulation_pair_decisions.csv"
)
SPLIT_VALIDATION_SUMMARY_CSV = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_split_validation_v1/"
    "scorer_checkpoint_gate_split_validation_rule_summary.csv"
)
OUTPUT_DIR = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "scorer_checkpoint_gate_holdout_validation_v1"
)

CANDIDATE_RULE_IDS = (
    "exact_span_and_repeated3_m0.02",
    "long_span_count_m0.02_t5",
    "long_span_count_m0.05_t5",
    "exact_span_and_repeated3_m0.01",
)

LOW_BREAK_MAX_BREAKS = 10
LOW_BREAK_MAX_UNIQUE_BREAKS = 5
LOW_BREAK_MIN_RESCUES = 30
LOW_BREAK_MIN_UNIQUE_RESCUES = 10


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
    return {
        "pair_count": len(rows),
        "gate_fired_count": len(fired_rows),
        "rescue_count": counts["rescue"],
        "break_count": counts["break"],
        "net_count": counts["rescue"] - counts["break"],
        "same_correct_count": counts["same_correct"],
        "same_wrong_count": counts["same_wrong"],
        "unique_text_pair_count": len({str(row.get("text_pair_key", "")) for row in rows} - {""}),
        "unique_candidate_pair_count": len({str(row.get("candidate_pair_key", "")) for row in rows} - {""}),
        "unique_misranked_rescue_pair_count": len(
            {str(row.get("text_pair_key", "")) for row in rescue_rows} - {""}
        ),
        "unique_control_break_pair_count": len(
            {str(row.get("text_pair_key", "")) for row in break_rows} - {""}
        ),
    }


def _group_rows(rows: list[dict[str, str]], key_fn) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(row)
    return dict(grouped)


def _heldout_split_rows(rule_id: str, rows: list[dict[str, str]], split_type: str, key_fn) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for split_key, split_rows in sorted(_group_rows(rows, key_fn).items()):
        metrics = _metrics(split_rows)
        fired = int(metrics["gate_fired_count"])
        net = int(metrics["net_count"])
        breaks = int(metrics["break_count"])
        if fired == 0:
            status = "no_decision"
        elif net >= 0:
            status = "nonnegative"
        else:
            status = "negative"
        out.append(
            {
                "rule_id": rule_id,
                "split_type": split_type,
                "split_key": split_key,
                **metrics,
                "heldout_negative": int(fired > 0 and net < 0),
                "heldout_break_only": int(fired > 0 and breaks > 0 and int(metrics["rescue_count"]) == 0),
                "heldout_status": status,
            }
        )
    return out


def _rule_status(aggregate: dict[str, Any], split_rows: list[dict[str, Any]]) -> str:
    low_break = (
        int(aggregate["break_count"]) <= LOW_BREAK_MAX_BREAKS
        and int(aggregate["unique_control_break_pair_count"]) <= LOW_BREAK_MAX_UNIQUE_BREAKS
        and int(aggregate["rescue_count"]) >= LOW_BREAK_MIN_RESCUES
        and int(aggregate["unique_misranked_rescue_pair_count"]) >= LOW_BREAK_MIN_UNIQUE_RESCUES
    )
    if not low_break:
        return "aggregate_not_low_break"
    negative_fixture = any(
        row["split_type"] == "fixture_search" and int(row["heldout_negative"]) == 1
        for row in split_rows
    )
    negative_artifact = any(
        row["split_type"] == "artifact" and int(row["heldout_negative"]) == 1
        for row in split_rows
    )
    if negative_fixture or negative_artifact:
        return "heldout_negative_cell"
    return "strict_holdout_pass"


def _summarise_rule(
    rule_id: str,
    rows: list[dict[str, str]],
    prior_split_summary: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    aggregate = _metrics(rows)
    split_rows = [
        *_heldout_split_rows(rule_id, rows, "fixture_search", _fixture_search_cell),
        *_heldout_split_rows(rule_id, rows, "artifact", _artifact_cell),
    ]
    negative_fixture_rows = [
        row for row in split_rows if row["split_type"] == "fixture_search" and int(row["heldout_negative"]) == 1
    ]
    negative_artifact_rows = [
        row for row in split_rows if row["split_type"] == "artifact" and int(row["heldout_negative"]) == 1
    ]
    break_only_rows = [row for row in split_rows if int(row["heldout_break_only"]) == 1]
    status = _rule_status(aggregate, split_rows)
    return (
        {
            "rule_id": rule_id,
            "prior_review_status": prior_split_summary.get("review_status", ""),
            "prior_split_stable_candidate": prior_split_summary.get("split_stable_candidate", ""),
            **aggregate,
            "fixture_search_split_count": sum(1 for row in split_rows if row["split_type"] == "fixture_search"),
            "artifact_split_count": sum(1 for row in split_rows if row["split_type"] == "artifact"),
            "negative_fixture_search_split_count": len(negative_fixture_rows),
            "negative_artifact_split_count": len(negative_artifact_rows),
            "break_only_split_count": len(break_only_rows),
            "worst_fixture_search_net": min(
                (int(row["net_count"]) for row in split_rows if row["split_type"] == "fixture_search"),
                default=0,
            ),
            "worst_artifact_net": min(
                (int(row["net_count"]) for row in split_rows if row["split_type"] == "artifact"),
                default=0,
            ),
            "holdout_status": status,
        },
        split_rows,
    )


def run() -> dict[str, Any]:
    started = time.perf_counter()
    root = _repo_root()
    output_dir = _rel(root, OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    decisions = _read_csv(_rel(root, PAIR_DECISIONS_CSV))
    prior_rows = _read_csv(_rel(root, SPLIT_VALIDATION_SUMMARY_CSV))
    prior_by_rule = {row["rule_id"]: row for row in prior_rows}

    decision_by_rule = _group_rows(decisions, lambda row: str(row.get("rule_id", "")))
    missing_candidate_rules = [rule_id for rule_id in CANDIDATE_RULE_IDS if rule_id not in decision_by_rule]
    if missing_candidate_rules:
        raise RuntimeError("missing candidate rule decisions: " + ", ".join(missing_candidate_rules))

    rule_summary_rows: list[dict[str, Any]] = []
    all_split_rows: list[dict[str, Any]] = []
    total = len(CANDIDATE_RULE_IDS)
    for index, rule_id in enumerate(CANDIDATE_RULE_IDS, start=1):
        print(
            f"[{RUN_LABEL}] rule {index}/{total} {rule_id}",
            flush=True,
        )
        summary_row, split_rows = _summarise_rule(
            rule_id,
            decision_by_rule[rule_id],
            prior_by_rule.get(rule_id, {}),
        )
        rule_summary_rows.append(summary_row)
        all_split_rows.extend(split_rows)

    rule_fields = [
        "rule_id",
        "prior_review_status",
        "prior_split_stable_candidate",
        "holdout_status",
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
        "fixture_search_split_count",
        "artifact_split_count",
        "negative_fixture_search_split_count",
        "negative_artifact_split_count",
        "break_only_split_count",
        "worst_fixture_search_net",
        "worst_artifact_net",
    ]
    split_fields = [
        "rule_id",
        "split_type",
        "split_key",
        "heldout_status",
        "heldout_negative",
        "heldout_break_only",
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
    _write_csv(
        output_dir / "scorer_checkpoint_gate_holdout_validation_rule_summary.csv",
        rule_summary_rows,
        rule_fields,
    )
    _write_csv(
        output_dir / "scorer_checkpoint_gate_holdout_validation_split_rows.csv",
        all_split_rows,
        split_fields,
    )

    status_counts = Counter(str(row["holdout_status"]) for row in rule_summary_rows)
    strict_pass_rows = [row for row in rule_summary_rows if row["holdout_status"] == "strict_holdout_pass"]
    elapsed = time.perf_counter() - started
    summary = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "output_dir": OUTPUT_DIR,
        "report_only": True,
        "runtime_changed": False,
        "truth_fields_are_evaluation_only": True,
        "candidate_rule_count": len(CANDIDATE_RULE_IDS),
        "candidate_rule_ids": list(CANDIDATE_RULE_IDS),
        "rule_status_counts": dict(sorted(status_counts.items())),
        "strict_holdout_pass_count": len(strict_pass_rows),
        "strict_holdout_pass_rules": [row["rule_id"] for row in strict_pass_rows],
        "rule_summaries": rule_summary_rows,
        "caveats": [
            "This is a stricter held-out-slice validation over existing S1 shadow decisions.",
            "It is not fresh solver-pool validation.",
            "It does not tune rules or fit learned weights.",
            "Truth labels are evaluation-only.",
            "No runtime solver behaviour changed.",
        ],
    }
    (output_dir / "scorer_checkpoint_gate_holdout_validation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_readout(output_dir / "scorer_checkpoint_gate_holdout_validation_readout.md", summary)
    return summary


def _table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No rules were evaluated."]
    out = [
        "| rule | status | rescues | breaks | net | unique rescues | unique breaks | neg fixtures | neg artifacts | worst fixture net | worst artifact net |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        out.append(
            "| "
            f"{row['rule_id']} | {row['holdout_status']} | "
            f"{row['rescue_count']} | {row['break_count']} | {row['net_count']} | "
            f"{row['unique_misranked_rescue_pair_count']} | {row['unique_control_break_pair_count']} | "
            f"{row['negative_fixture_search_split_count']} | {row['negative_artifact_split_count']} | "
            f"{row['worst_fixture_search_net']} | {row['worst_artifact_net']} |"
        )
    return out


def _write_readout(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Scorer Checkpoint Gate Holdout Validation v1",
        "",
        "## Purpose",
        "",
        "Apply stricter held-out artifact and fixture/search slice checks to the four Stage 2 split-stable checkpoint candidates.",
        "",
        "## Status",
        "",
        f"- candidate rules: {summary['candidate_rule_count']}",
        f"- strict holdout pass rules: {summary['strict_holdout_pass_count']}",
        f"- elapsed seconds: {summary['elapsed_seconds']:.3f}",
        "",
        "## Rule Results",
        "",
        *_table(list(summary["rule_summaries"])),
        "",
        "## Interpretation",
        "",
    ]
    if summary["strict_holdout_pass_count"]:
        lines.append("At least one rule passed strict held-out-slice checks. Passing this check still only justifies fresh solver-pool or shadow-selector validation, not runtime promotion.")
    else:
        lines.append("No candidate passed strict held-out-slice checks. The Stage 2 rules remain useful diagnostics, but they should not advance directly to runtime promotion from this evidence.")
    lines.extend(
        [
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
        f"{RUN_LABEL}: candidates={out['candidate_rule_count']} "
        f"strict_pass={out['strict_holdout_pass_count']} output_dir={out['output_dir']}",
        flush=True,
    )
