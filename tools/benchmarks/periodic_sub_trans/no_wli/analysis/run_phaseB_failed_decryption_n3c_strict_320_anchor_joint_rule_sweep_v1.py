from __future__ import annotations

import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


PHASE = "phaseB_failed_decryption_n3c_strict_320_anchor_joint_rule_sweep_v1"
INPUT_PHASE = "phaseB_failed_decryption_n3c_strict_320_anchor_lens_quickcheck_v1"
ANALYSIS_ROOT = REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis"
INPUT_PAIRWISE = ANALYSIS_ROOT / INPUT_PHASE / "candidate_anchor_pairwise_rows.csv"
OUTPUT_DIR = ANALYSIS_ROOT / PHASE

REQUIRED_COLUMNS = {
    "lens_name",
    "semantic_pair_id",
    "anchor_winner_id",
    "anchor_pair_result",
    "absolute_score_margin",
}


@dataclass(frozen=True)
class JointRule:
    name: str
    primary_lens: str
    primary_min_margin: float
    confirm_lens: str | None = None
    confirm_min_margin: float = 0.0
    confirm_policy: str = "none"


DEFAULT_RULES = (
    JointRule("hd0_len10_m10", "hd0_len10", 10.0),
    JointRule("hd0_len10_m20", "hd0_len10", 20.0),
    JointRule("hd0_len10_m30", "hd0_len10", 30.0),
    JointRule("hd0_len10_m50", "hd0_len10", 50.0),
    JointRule("hd0_len10_m20__hd0_len12_agree_required", "hd0_len10", 20.0, "hd0_len12", 0.0, "agree_required"),
    JointRule("hd0_len10_m20__hd0_len12_no_conflict", "hd0_len10", 20.0, "hd0_len12", 0.0, "no_conflict"),
    JointRule("hd0_len10_m20__hd0_len12_conflict_only", "hd0_len10", 20.0, "hd0_len12", 0.0, "conflict_only"),
    JointRule(
        "hd0_len10_m20__hd_le1_len12_agree_required",
        "hd0_len10",
        20.0,
        "hd_le1_len12",
        20.0,
        "agree_required",
    ),
    JointRule("hd0_len10_m20__hd_le1_len12_no_conflict", "hd0_len10", 20.0, "hd_le1_len12", 20.0, "no_conflict"),
    JointRule(
        "hd0_len10_m20__hd_le1_len12_conflict_only",
        "hd0_len10",
        20.0,
        "hd_le1_len12",
        20.0,
        "conflict_only",
    ),
    JointRule("hd0_len10_m20__hd0_len8_no_conflict_m50", "hd0_len10", 20.0, "hd0_len8", 50.0, "no_conflict"),
    JointRule("hd0_len10_m20__hd0_len8_conflict_only_m50", "hd0_len10", 20.0, "hd0_len8", 50.0, "conflict_only"),
    JointRule("hd0_len10_m50__hd0_len12_no_conflict", "hd0_len10", 50.0, "hd0_len12", 0.0, "no_conflict"),
    JointRule("hd0_len10_m50__hd_le1_len12_no_conflict", "hd0_len10", 50.0, "hd_le1_len12", 20.0, "no_conflict"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or ())
        if missing:
            raise RuntimeError(f"{repo_relative(path)} missing required columns: {sorted(missing)}")
        return list(reader)


def pivot_rows(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    by_pair: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        pair_id = row["semantic_pair_id"]
        lens = row["lens_name"]
        if pair_id in by_pair and lens in by_pair[pair_id]:
            raise RuntimeError(f"duplicate pair/lens row: {pair_id!r}, {lens!r}")
        by_pair.setdefault(pair_id, {})[lens] = row
    return by_pair


def is_non_tie(row: dict[str, str]) -> bool:
    return row["anchor_winner_id"] not in {"tie", "", "None", "null"}


def margin(row: dict[str, str]) -> float:
    return float(row["absolute_score_margin"])


def qualifies(rule: JointRule, lens_rows: dict[str, dict[str, str]]) -> tuple[bool, str]:
    primary = lens_rows.get(rule.primary_lens)
    if primary is None:
        return False, "missing_primary"
    if margin(primary) < rule.primary_min_margin:
        return False, "primary_margin_below_threshold"
    if not is_non_tie(primary):
        return False, "primary_tie"

    if rule.confirm_policy == "none":
        return True, "primary_only"

    confirm = lens_rows.get(rule.confirm_lens or "")
    if confirm is None:
        if rule.confirm_policy == "no_conflict":
            return True, "confirm_absent_allowed"
        return False, "missing_confirm"

    confirm_available = margin(confirm) >= rule.confirm_min_margin and is_non_tie(confirm)
    if not confirm_available:
        if rule.confirm_policy == "no_conflict":
            return True, "confirm_below_margin_or_tie_allowed"
        return False, "confirm_below_margin_or_tie"

    same_winner = confirm["anchor_winner_id"] == primary["anchor_winner_id"]
    if rule.confirm_policy == "agree_required":
        return same_winner, "confirm_agrees" if same_winner else "confirm_conflicts"
    if rule.confirm_policy == "no_conflict":
        return same_winner, "confirm_agrees" if same_winner else "confirm_conflicts"
    if rule.confirm_policy == "conflict_only":
        return (not same_winner), "confirm_conflicts" if not same_winner else "confirm_agrees"
    raise RuntimeError(f"unknown confirm_policy: {rule.confirm_policy}")


def summarise_rule(rule: JointRule, by_pair: dict[str, dict[str, dict[str, str]]]) -> dict[str, object]:
    counts = {"covered_pair_count": 0, "agree_count": 0, "break_count": 0, "tie_count": 0}
    reason_counts: dict[str, int] = {}
    for pair_id, lens_rows in by_pair.items():
        ok, reason = qualifies(rule, lens_rows)
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if not ok:
            continue
        result = lens_rows[rule.primary_lens]["anchor_pair_result"]
        counts["covered_pair_count"] += 1
        if result == "agree":
            counts["agree_count"] += 1
        elif result == "break":
            counts["break_count"] += 1
        elif result == "tie":
            counts["tie_count"] += 1
        else:
            raise RuntimeError(f"unexpected anchor_pair_result {result!r} for {pair_id}")
    covered = counts["covered_pair_count"]
    return {
        "rule_name": rule.name,
        "primary_lens": rule.primary_lens,
        "primary_min_margin": f"{rule.primary_min_margin:.6f}",
        "confirm_lens": rule.confirm_lens or "",
        "confirm_min_margin": f"{rule.confirm_min_margin:.6f}",
        "confirm_policy": rule.confirm_policy,
        **counts,
        "break_rate": f"{counts['break_count'] / covered if covered else 0.0:.6f}",
        "agree_rate": f"{counts['agree_count'] / covered if covered else 0.0:.6f}",
        "tie_rate": f"{counts['tie_count'] / covered if covered else 0.0:.6f}",
        "reason_counts_json": json.dumps(reason_counts, sort_keys=True),
    }


def build_conflict_table(by_pair: dict[str, dict[str, dict[str, str]]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for primary_margin in (10.0, 20.0, 30.0, 50.0):
        for secondary_lens in ("hd0_len12", "hd_le1_len12", "hd0_len8"):
            for secondary_margin in (0.0, 10.0, 20.0, 50.0):
                counters = {
                    "primary_pairs": 0,
                    "secondary_available": 0,
                    "secondary_agrees_with_primary": 0,
                    "secondary_conflicts_with_primary": 0,
                    "break_when_secondary_agrees": 0,
                    "covered_when_secondary_agrees": 0,
                    "break_when_secondary_conflicts": 0,
                    "covered_when_secondary_conflicts": 0,
                }
                for lens_rows in by_pair.values():
                    primary = lens_rows.get("hd0_len10")
                    secondary = lens_rows.get(secondary_lens)
                    if primary is None or margin(primary) < primary_margin or not is_non_tie(primary):
                        continue
                    counters["primary_pairs"] += 1
                    if secondary is None or margin(secondary) < secondary_margin or not is_non_tie(secondary):
                        continue
                    counters["secondary_available"] += 1
                    same_winner = secondary["anchor_winner_id"] == primary["anchor_winner_id"]
                    if same_winner:
                        counters["secondary_agrees_with_primary"] += 1
                        counters["covered_when_secondary_agrees"] += 1
                        if primary["anchor_pair_result"] == "break":
                            counters["break_when_secondary_agrees"] += 1
                    else:
                        counters["secondary_conflicts_with_primary"] += 1
                        counters["covered_when_secondary_conflicts"] += 1
                        if primary["anchor_pair_result"] == "break":
                            counters["break_when_secondary_conflicts"] += 1
                agree_cov = counters["covered_when_secondary_agrees"]
                conflict_cov = counters["covered_when_secondary_conflicts"]
                rows.append({
                    "primary_lens": "hd0_len10",
                    "primary_margin_threshold": f"{primary_margin:.6f}",
                    "secondary_lens": secondary_lens,
                    "secondary_margin_threshold": f"{secondary_margin:.6f}",
                    **counters,
                    "break_rate_when_secondary_agrees": (
                        f"{counters['break_when_secondary_agrees'] / agree_cov if agree_cov else 0.0:.6f}"
                    ),
                    "break_rate_when_secondary_conflicts": (
                        f"{counters['break_when_secondary_conflicts'] / conflict_cov if conflict_cov else 0.0:.6f}"
                    ),
                })
    return rows


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_sweep() -> dict[str, object]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[{PHASE}] started_utc={utc_now()}")
    print(f"[{PHASE}] input_pairwise={repo_relative(INPUT_PAIRWISE)}")

    input_rows = read_rows(INPUT_PAIRWISE)
    by_pair = pivot_rows(input_rows)
    summary_rows = [summarise_rule(rule, by_pair) for rule in DEFAULT_RULES]
    conflict_rows = build_conflict_table(by_pair)

    write_csv(OUTPUT_DIR / "anchor_joint_rule_summary_rows.csv", summary_rows)
    write_csv(OUTPUT_DIR / "anchor_joint_conflict_rows.csv", conflict_rows)

    manifest = {
        "status": "anchor_joint_rule_sweep_complete",
        "phase": PHASE,
        "input_phase": INPUT_PHASE,
        "finished_utc": utc_now(),
        "input_pairwise": repo_relative(INPUT_PAIRWISE),
        "input_pairwise_rows": len(input_rows),
        "unique_semantic_pairs": len(by_pair),
        "rule_rows": len(summary_rows),
        "conflict_rows": len(conflict_rows),
        "rules": [asdict(rule) for rule in DEFAULT_RULES],
        "outputs": [
            "anchor_joint_rule_summary_rows.csv",
            "anchor_joint_conflict_rows.csv",
            "anchor_joint_manifest.json",
        ],
        "interpretation_note": (
            "Conditional break-risk diagnostics only. These are not calibrated probabilities; "
            "the current fixture has baseline-correct pairs and zero rescue-capable pairs."
        ),
        "production_scoring_change": False,
        "production_ranking_change": False,
        "score_bearing_use_approved": False,
        "report_only": True,
    }
    (OUTPUT_DIR / "anchor_joint_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"[{PHASE}] status=anchor_joint_rule_sweep_complete")
    print(f"[{PHASE}] output_dir={repo_relative(OUTPUT_DIR)}")
    print(f"[{PHASE}] input_pairwise_rows={len(input_rows)}")
    print(f"[{PHASE}] unique_semantic_pairs={len(by_pair)}")
    print(f"[{PHASE}] rule_rows={len(summary_rows)}")
    print(f"[{PHASE}] conflict_rows={len(conflict_rows)}")
    return manifest


def main() -> int:
    run_sweep()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
