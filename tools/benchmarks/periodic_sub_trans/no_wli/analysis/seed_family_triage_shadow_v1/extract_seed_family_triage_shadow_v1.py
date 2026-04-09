from __future__ import annotations

import datetime as dt
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here] + list(here.parents):
        if (parent / "src").exists() and (parent / "tools").exists():
            return parent
    raise RuntimeError("Could not locate repo root from extract_seed_family_triage_shadow_v1.py")


REPO_ROOT = _find_repo_root()
INPUT_SCORE_STOP_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "score_stop_shadow_v2/20260408T142942Z__score_stop_shadow_v2"
)
INPUT_LFQ_V1_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v1/20260408T152322Z__late_family_quality_v1"
)
INPUT_LFQ_V2_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v2/20260408T154637Z__late_family_quality_v2"
)
INPUT_LFQ_V3_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v3/20260408T162219Z__late_family_quality_v3"
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "seed_family_triage_shadow_v1"
)
REQUIRED_STOP_INPUT_FILES = (
    "run_shadow_summary.jsonl",
    "row_scores.jsonl",
    "case_explanations.jsonl",
)
REQUIRED_LFQ_V1_INPUT_FILES = (
    "family_quality_rows.jsonl",
    "family_quality_case_digest.jsonl",
    "family_quality_summary.json",
)
REQUIRED_LFQ_V2_INPUT_FILES = (
    "seed_agreement_rows.jsonl",
    "winner_pairwise_rows.jsonl",
    "agreement_summary.json",
)
REQUIRED_LFQ_V3_INPUT_FILES = (
    "pattern_strength_rows.jsonl",
    "truth_relative_pair_rows.jsonl",
    "pattern_strength_summary.json",
)
TRIAGE_CORE_PANEL_SEEDS = (511, 411, 611, 711, 811, 911, 1011, 1111, 1211)
TRIAGE_PRESSURE_PANEL_SEEDS = (1311, 1411, 1511)
TRIAGE_REVIEW_SEEDS = (
    511, 411, 611, 711, 811, 911, 1011, 1111, 1211,
    1311, 1411, 1511,
)
TRIAGE_FAMILY_ENRICHED_SEEDS = (1111, 1311, 1411, 411, 611, 1011)
TRUTH_PAIR_NAMES = (
    "truth_vs_trust",
    "truth_vs_archive",
    "truth_vs_full_uplift",
    "truth_vs_persistence",
)
SEED_PRIORITY_SCORES = {
    "high": 3,
    "medium": 2,
    "unclear": 1,
    "low": 0,
}
SEED_BUDGET_PROFILES: dict[str, tuple[float, float, float]] = {
    "focus_with_exploration": (0.60, 0.25, 0.15),
    "balanced_portfolio": (0.45, 0.35, 0.20),
    "exploration_heavy": (0.30, 0.30, 0.40),
    "observe_only": (0.20, 0.20, 0.60),
}
SEED_REASON_CODE_SET = {
    "reference_like_strong",
    "accepted_miss_reference_like",
    "pattern_only_but_weak",
    "stop_dump_clean",
    "stop_dump_false_fire_like",
    "quiet_reject",
    "pattern_inconclusive",
    "family_strength_inconclusive",
    "stop_only_fallback",
    "same_family_archive_case",
    "truth_family_strong",
    "truth_family_partial",
    "truth_family_weak",
}
FAMILY_BAND_ORDER = {
    "high": 0,
    "medium": 1,
    "explore_only": 2,
    "low": 3,
}
FAMILY_STRENGTH_ORDER = {
    "strong": 0,
    "partial": 1,
    "weak": 2,
}


def _safe_str(value: Any) -> str:
    return str(value or "")


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_finite(value: Any) -> bool:
    return math.isfinite(_safe_float(value))


def _json_default(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            rows.append(dict(json.loads(text)))
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, default=_json_default))
            handle.write("\n")


def _require_bundle_files(bundle_dir: Path, required_names: Sequence[str], *, label: str) -> dict[str, Path]:
    missing = [name for name in required_names if not (bundle_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required {label} files: {', '.join(sorted(missing))}")
    return {name: bundle_dir / name for name in required_names}


def _seed_order(key_seed: int) -> int:
    try:
        return TRIAGE_REVIEW_SEEDS.index(int(key_seed))
    except ValueError:
        return len(TRIAGE_REVIEW_SEEDS)


def _enriched_seed_order(key_seed: int) -> int:
    try:
        return TRIAGE_FAMILY_ENRICHED_SEEDS.index(int(key_seed))
    except ValueError:
        return len(TRIAGE_FAMILY_ENRICHED_SEEDS)


def _select_review_run_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed not in TRIAGE_REVIEW_SEEDS:
            continue
        if key_seed in indexed:
            raise ValueError(f"Duplicate stop run row for seed {key_seed}")
        indexed[key_seed] = dict(row)
    missing = [seed for seed in TRIAGE_REVIEW_SEEDS if seed not in indexed]
    if missing:
        raise ValueError(f"Missing review seeds from stop input: {missing}")
    return [indexed[seed] for seed in TRIAGE_REVIEW_SEEDS]


def _index_optional_case_rows(rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed in indexed:
            raise ValueError(f"Duplicate case explanation row for seed {key_seed}")
        indexed[key_seed] = dict(row)
    return indexed


def _index_single_rows_by_seed(
    rows: Sequence[Mapping[str, Any]],
    *,
    seed_scope: Sequence[int],
    source_name: str,
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed not in seed_scope:
            continue
        if key_seed in indexed:
            raise ValueError(f"Duplicate {source_name} row for seed {key_seed}")
        indexed[key_seed] = dict(row)
    missing = [seed for seed in seed_scope if seed not in indexed]
    if missing:
        raise ValueError(f"Missing required {source_name} rows for seeds: {missing}")
    return indexed


def _index_family_rows_by_seed(rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, dict[str, Any]]]:
    indexed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed not in TRIAGE_FAMILY_ENRICHED_SEEDS:
            continue
        family_id = _safe_str(row.get("family_id"))
        if not family_id:
            raise ValueError(f"Missing family_id in family_quality_rows for seed {key_seed}")
        if family_id in indexed[key_seed]:
            raise ValueError(f"Duplicate family_quality_rows entry for seed {key_seed} family {family_id}")
        indexed[key_seed][family_id] = dict(row)
    missing = [seed for seed in TRIAGE_FAMILY_ENRICHED_SEEDS if seed not in indexed]
    if missing:
        raise ValueError(f"Missing family_quality_rows for enriched seeds: {missing}")
    return indexed


def _index_pair_rows_by_seed(rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, dict[str, Any]]]:
    indexed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed not in TRIAGE_FAMILY_ENRICHED_SEEDS:
            continue
        pair_name = _safe_str(row.get("pair_name"))
        if not pair_name:
            raise ValueError(f"Missing pair_name in truth_relative_pair_rows for seed {key_seed}")
        if pair_name in indexed[key_seed]:
            raise ValueError(f"Duplicate truth_relative_pair_rows entry for seed {key_seed} pair {pair_name}")
        indexed[key_seed][pair_name] = dict(row)
    missing = [seed for seed in TRIAGE_FAMILY_ENRICHED_SEEDS if seed not in indexed]
    if missing:
        raise ValueError(f"Missing truth_relative_pair_rows for enriched seeds: {missing}")
    for seed in TRIAGE_FAMILY_ENRICHED_SEEDS:
        missing_pairs = [pair_name for pair_name in TRUTH_PAIR_NAMES if pair_name not in indexed[seed]]
        if missing_pairs:
            raise ValueError(f"Missing truth-relative pair rows for seed {seed}: {missing_pairs}")
    return indexed


def _require_enriched_seed_inputs(
    *,
    family_rows_by_seed: Mapping[int, Mapping[str, Mapping[str, Any]]],
    v1_digest_by_seed: Mapping[int, Mapping[str, Any]],
    v2_agreement_by_seed: Mapping[int, Mapping[str, Any]],
    v3_pattern_by_seed: Mapping[int, Mapping[str, Any]],
    v3_pair_by_seed: Mapping[int, Mapping[str, Mapping[str, Any]]],
) -> None:
    for key_seed in TRIAGE_FAMILY_ENRICHED_SEEDS:
        if key_seed not in family_rows_by_seed:
            raise ValueError(f"Missing family rows for enriched seed {key_seed}")
        if key_seed not in v1_digest_by_seed:
            raise ValueError(f"Missing v1 digest for enriched seed {key_seed}")
        if key_seed not in v2_agreement_by_seed:
            raise ValueError(f"Missing v2 agreement row for enriched seed {key_seed}")
        if key_seed not in v3_pattern_by_seed:
            raise ValueError(f"Missing v3 pattern row for enriched seed {key_seed}")
        if key_seed not in v3_pair_by_seed:
            raise ValueError(f"Missing v3 pair rows for enriched seed {key_seed}")


def _label_family_strength(family_row: Mapping[str, Any]) -> str:
    persistence_count = _safe_int(family_row.get("family_persistence_count"))
    reaches_archive = int(_safe_int(family_row.get("family_reaches_archive")) > 0)
    persistence_ok = persistence_count >= 2
    archive_ok = reaches_archive == 1
    if persistence_ok and archive_ok:
        return "strong"
    if persistence_ok != archive_ok:
        return "partial"
    return "weak"


def _is_quiet_reject_like(row: Mapping[str, Any]) -> bool:
    return _safe_int(row.get("would_dump")) == 0 and _safe_str(row.get("run_type")) == "unknown"


def _seed_budget_policy_for_band(seed_priority_band: str) -> str:
    return {
        "high": "focus_with_exploration",
        "medium": "balanced_portfolio",
        "unclear": "exploration_heavy",
        "low": "observe_only",
    }[seed_priority_band]


def _truth_strength_reason_code(truth_strength_label: str) -> str:
    return {
        "strong": "truth_family_strong",
        "partial": "truth_family_partial",
        "weak": "truth_family_weak",
    }.get(truth_strength_label, "family_strength_inconclusive")


def _is_positive_family_pattern(pattern_strength_read_label: str) -> bool:
    return pattern_strength_read_label in {
        "accepted_miss_reference_like",
        "reference_like_strong",
        "reference_like_partial",
        "pattern_only_reference_like_but_strength_weak",
    }


def _seed_reason_codes(row: Mapping[str, Any]) -> list[str]:
    codes: list[str] = []
    pattern_strength_read_label = _safe_str(row.get("pattern_strength_read_label"))
    case_shape_label = _safe_str(row.get("case_shape_label"))
    truth_strength_label = _safe_str(row.get("truth_winner_strength_label"))
    truth_family_id = _safe_str(row.get("truth_winner_family_id"))
    archive_family_id = _safe_str(row.get("archive_uplift_winner_family_id"))

    if pattern_strength_read_label == "reference_like_strong":
        codes.append("reference_like_strong")
    elif pattern_strength_read_label == "accepted_miss_reference_like":
        codes.append("accepted_miss_reference_like")
    elif pattern_strength_read_label == "pattern_only_reference_like_but_strength_weak":
        codes.append("pattern_only_but_weak")
    elif _safe_str(row.get("triage_evidence_tier")) == "family_enriched":
        codes.append("pattern_inconclusive")

    if _safe_int(row.get("would_dump")) == 1:
        if case_shape_label in {"trust_false_fire", "archive_false_fire"}:
            codes.append("stop_dump_false_fire_like")
        else:
            codes.append("stop_dump_clean")
    elif _is_quiet_reject_like(row):
        codes.append("quiet_reject")

    if _safe_str(row.get("triage_evidence_tier")) == "stop_only":
        codes.append("stop_only_fallback")

    if truth_strength_label:
        codes.append(_truth_strength_reason_code(truth_strength_label))
    elif _safe_str(row.get("triage_evidence_tier")) == "family_enriched":
        codes.append("family_strength_inconclusive")

    if truth_family_id and truth_family_id == archive_family_id:
        codes.append("same_family_archive_case")

    deduped: list[str] = []
    for code in codes:
        if code not in SEED_REASON_CODE_SET:
            continue
        if code not in deduped:
            deduped.append(code)
    return deduped[:4]


def _derive_seed_priority_band(row: Mapping[str, Any]) -> str:
    evidence_tier = _safe_str(row.get("triage_evidence_tier"))
    pattern_strength_read_label = _safe_str(row.get("pattern_strength_read_label"))
    case_shape_label = _safe_str(row.get("case_shape_label"))
    would_dump = _safe_int(row.get("would_dump"))

    if evidence_tier == "family_enriched":
        if pattern_strength_read_label in {"accepted_miss_reference_like", "reference_like_strong"}:
            return "high"
        if pattern_strength_read_label in {"reference_like_partial", "pattern_only_reference_like_but_strength_weak"}:
            return "medium"
        if (
            would_dump == 0
            and _is_quiet_reject_like(row)
            and not _is_positive_family_pattern(pattern_strength_read_label)
        ):
            return "low"
        return "unclear"

    if would_dump == 1 and case_shape_label not in {"trust_false_fire", "archive_false_fire"}:
        if _safe_str(row.get("run_type")) in {"solved_control", "stage35_live_win"}:
            return "high"
        return "medium"
    if would_dump == 0 and _is_quiet_reject_like(row):
        return "low"
    return "unclear"


def build_seed_triage_rows(
    stop_run_rows: Sequence[Mapping[str, Any]],
    case_explanations_by_seed: Mapping[int, Mapping[str, Any]],
    v1_case_digest_by_seed: Mapping[int, Mapping[str, Any]],
    v2_agreement_by_seed: Mapping[int, Mapping[str, Any]],
    v3_pattern_by_seed: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stop_run_row in _select_review_run_rows(stop_run_rows):
        key_seed = _safe_int(stop_run_row.get("key_seed"))
        case_row = dict(case_explanations_by_seed.get(key_seed, {}))
        triage_row: dict[str, Any] = {
            "key_seed": key_seed,
            "run_type": _safe_str(stop_run_row.get("run_type")),
            "target_panel_name": _safe_str(stop_run_row.get("target_panel_name")),
            "target_panel_role": _safe_str(stop_run_row.get("target_panel_role")),
            "triage_evidence_tier": (
                "family_enriched" if key_seed in TRIAGE_FAMILY_ENRICHED_SEEDS else "stop_only"
            ),
            "would_dump": _safe_int(stop_run_row.get("would_dump")),
            "would_stop": _safe_int(stop_run_row.get("would_stop")),
            "shadow_rule_id": _safe_str(stop_run_row.get("shadow_rule_id")),
            "case_shape_label": _safe_str(case_row.get("case_shape_label")),
            "decision_axis_label": _safe_str(case_row.get("decision_axis_label")),
            "primary_explanation": _safe_str(case_row.get("primary_explanation")),
            "family_quality_read_label": "",
            "winner_pattern_key": "",
            "split_pattern_label": "",
            "pattern_strength_read_label": "",
            "truth_winner_strength_label": "",
            "truth_winner_family_id": "",
            "archive_uplift_winner_family_id": "",
            "unique_winner_family_count": 0,
            "truth_agreement_count": 0,
        }

        if key_seed in TRIAGE_FAMILY_ENRICHED_SEEDS:
            v1_digest_row = dict(v1_case_digest_by_seed[key_seed])
            v2_agreement_row = dict(v2_agreement_by_seed[key_seed])
            v3_pattern_row = dict(v3_pattern_by_seed[key_seed])
            if (
                _safe_str(v2_agreement_row.get("winner_pattern_key"))
                and _safe_str(v3_pattern_row.get("winner_pattern_key"))
                and _safe_str(v2_agreement_row.get("winner_pattern_key"))
                != _safe_str(v3_pattern_row.get("winner_pattern_key"))
            ):
                raise ValueError(f"winner_pattern_key mismatch across v2/v3 for seed {key_seed}")
            triage_row.update(
                {
                    "family_quality_read_label": _safe_str(v1_digest_row.get("family_quality_read_label")),
                    "winner_pattern_key": (
                        _safe_str(v3_pattern_row.get("winner_pattern_key"))
                        or _safe_str(v2_agreement_row.get("winner_pattern_key"))
                    ),
                    "split_pattern_label": _safe_str(v3_pattern_row.get("split_pattern_label")),
                    "pattern_strength_read_label": _safe_str(v3_pattern_row.get("pattern_strength_read_label")),
                    "truth_winner_strength_label": _safe_str(v3_pattern_row.get("truth_winner_strength_label")),
                    "truth_winner_family_id": _safe_str(v1_digest_row.get("truth_winner_family_id")),
                    "archive_uplift_winner_family_id": _safe_str(v1_digest_row.get("archive_uplift_winner_family_id")),
                    "unique_winner_family_count": _safe_int(v2_agreement_row.get("unique_winner_family_count")),
                    "truth_agreement_count": _safe_int(v2_agreement_row.get("truth_agreement_count")),
                }
            )

        seed_priority_band = _derive_seed_priority_band(triage_row)
        seed_budget_policy_label = _seed_budget_policy_for_band(seed_priority_band)
        primary_share, secondary_share, exploration_share = SEED_BUDGET_PROFILES[seed_budget_policy_label]
        triage_row.update(
            {
                "seed_priority_band": seed_priority_band,
                "seed_priority_score": SEED_PRIORITY_SCORES[seed_priority_band],
                "seed_budget_policy_label": seed_budget_policy_label,
                "recommended_primary_budget_share": primary_share,
                "recommended_secondary_budget_share": secondary_share,
                "recommended_exploration_budget_share": exploration_share,
            }
        )
        triage_row["seed_reason_codes"] = _seed_reason_codes(triage_row)
        rows.append(triage_row)

    rows.sort(key=lambda row: _seed_order(_safe_int(row.get("key_seed"))))
    return rows


def _winner_flags(family_id: str, digest_row: Mapping[str, Any]) -> dict[str, int]:
    return {
        "is_truth_winner": int(family_id == _safe_str(digest_row.get("truth_winner_family_id"))),
        "is_trust_winner": int(family_id == _safe_str(digest_row.get("trust_winner_family_id"))),
        "is_archive_winner": int(family_id == _safe_str(digest_row.get("archive_uplift_winner_family_id"))),
        "is_full_uplift_winner": int(family_id == _safe_str(digest_row.get("full_uplift_winner_family_id"))),
        "is_persistence_winner": int(family_id == _safe_str(digest_row.get("persistence_winner_family_id"))),
    }


def _family_pair_rows_for_alt_winner(
    *,
    family_id: str,
    pair_rows_by_name: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for pair_name in TRUTH_PAIR_NAMES:
        pair_row = dict(pair_rows_by_name[pair_name])
        if _safe_str(pair_row.get("alt_family_id")) == family_id:
            matches.append(pair_row)
    return matches


def _family_is_clearly_weaker_alt(
    *,
    family_strength_label: str,
    alt_pair_rows: Sequence[Mapping[str, Any]],
) -> bool:
    if not alt_pair_rows:
        return False
    if any(_safe_str(pair_row.get("pair_read_label")) == "truth_advantaged" for pair_row in alt_pair_rows):
        return True
    return family_strength_label == "weak"


def _family_reason_codes(
    *,
    family_strength_label: str,
    winner_flags: Mapping[str, int],
    alt_pair_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    codes: list[str] = []
    if _safe_int(winner_flags.get("is_truth_winner")) == 1:
        codes.append("truth_winner")
    elif any(_safe_int(winner_flags.get(name)) == 1 for name in ("is_trust_winner", "is_archive_winner", "is_full_uplift_winner", "is_persistence_winner")):
        codes.append("alt_winner")
        if _family_is_clearly_weaker_alt(family_strength_label=family_strength_label, alt_pair_rows=alt_pair_rows):
            codes.append("alt_winner_clearly_weaker")
        else:
            codes.append("alt_winner_not_clearly_weaker")
    else:
        codes.append("non_winner")
    codes.append(f"strength_{family_strength_label}")
    if family_strength_label != "weak":
        codes.append("archive_reaching" if family_strength_label == "strong" else "partial_archive_signal")
    return codes[:4]


def _derive_family_priority_band(
    *,
    family_strength_label: str,
    winner_flags: Mapping[str, int],
    alt_pair_rows: Sequence[Mapping[str, Any]],
) -> str:
    is_truth_winner = _safe_int(winner_flags.get("is_truth_winner")) == 1
    is_alt_winner = any(
        _safe_int(winner_flags.get(flag_name)) == 1
        for flag_name in ("is_trust_winner", "is_archive_winner", "is_full_uplift_winner", "is_persistence_winner")
    )

    if is_truth_winner and family_strength_label in {"strong", "partial"}:
        return "high"
    if is_truth_winner and family_strength_label == "weak":
        return "medium"
    if is_alt_winner and not _family_is_clearly_weaker_alt(
        family_strength_label=family_strength_label,
        alt_pair_rows=alt_pair_rows,
    ):
        return "medium"
    if is_alt_winner:
        return "low"
    if family_strength_label == "weak":
        return "low"
    return "explore_only"


def _family_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        FAMILY_BAND_ORDER[_safe_str(row.get("family_priority_band"))],
        -_safe_int(row.get("is_truth_winner")),
        FAMILY_STRENGTH_ORDER[_safe_str(row.get("family_strength_label"))],
        -_safe_float(row.get("best_truth")),
        -_safe_int(row.get("boundary_count")),
        _safe_str(row.get("family_id")),
    )


def _allocate_group_shares(
    rows: Sequence[dict[str, Any]],
    *,
    total_share: float,
) -> dict[str, float]:
    if not rows:
        return {}
    per_row_share = total_share / float(len(rows))
    return {_safe_str(row.get("family_id")): per_row_share for row in rows}


def _round_share(value: float) -> float:
    return round(float(value), 6)


def build_family_priority_rows(
    seed_triage_rows: Sequence[Mapping[str, Any]],
    family_rows_by_seed: Mapping[int, Mapping[str, Mapping[str, Any]]],
    v1_case_digest_by_seed: Mapping[int, Mapping[str, Any]],
    v3_pair_by_seed: Mapping[int, Mapping[str, Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seed_triage_by_seed = {
        _safe_int(row.get("key_seed")): dict(row)
        for row in seed_triage_rows
        if _safe_str(row.get("triage_evidence_tier")) == "family_enriched"
    }
    family_priority_rows: list[dict[str, Any]] = []
    budget_rows: list[dict[str, Any]] = []

    for key_seed in TRIAGE_FAMILY_ENRICHED_SEEDS:
        seed_triage_row = dict(seed_triage_by_seed[key_seed])
        digest_row = dict(v1_case_digest_by_seed[key_seed])
        pair_rows_by_name = dict(v3_pair_by_seed[key_seed])
        seed_family_rows: list[dict[str, Any]] = []
        for family_id, family_row in sorted(family_rows_by_seed[key_seed].items()):
            strength_label = _label_family_strength(family_row)
            winner_flags = _winner_flags(family_id, digest_row)
            alt_pair_rows = _family_pair_rows_for_alt_winner(
                family_id=family_id,
                pair_rows_by_name=pair_rows_by_name,
            )
            family_priority_band = _derive_family_priority_band(
                family_strength_label=strength_label,
                winner_flags=winner_flags,
                alt_pair_rows=alt_pair_rows,
            )
            seed_family_rows.append(
                {
                    "key_seed": key_seed,
                    "family_id": family_id,
                    "study_role": _safe_str(family_row.get("study_role")),
                    "family_role_label": _safe_str(family_row.get("family_role_label")),
                    "best_truth": _safe_float(family_row.get("best_truth")),
                    "best_trust": _safe_float(family_row.get("best_trust")),
                    "best_archive_uplift": _safe_float(family_row.get("best_archive_uplift")),
                    "best_full_uplift": _safe_float(family_row.get("best_full_uplift")),
                    "boundary_count": _safe_int(family_row.get("boundary_count")),
                    "boundaries_seen": _safe_str(family_row.get("boundaries_seen")),
                    "family_persistence_count": _safe_int(family_row.get("family_persistence_count")),
                    "family_reaches_archive": int(_safe_int(family_row.get("family_reaches_archive")) > 0),
                    "truth_trend_label": _safe_str(family_row.get("truth_trend_label")),
                    "trust_trend_label": _safe_str(family_row.get("trust_trend_label")),
                    "archive_uplift_trend_label": _safe_str(family_row.get("archive_uplift_trend_label")),
                    "full_uplift_trend_label": _safe_str(family_row.get("full_uplift_trend_label")),
                    "family_strength_label": strength_label,
                    "family_priority_band": family_priority_band,
                    "recommended_family_budget_share": 0.0,
                    "family_reason_codes": _family_reason_codes(
                        family_strength_label=strength_label,
                        winner_flags=winner_flags,
                        alt_pair_rows=alt_pair_rows,
                    ),
                    **winner_flags,
                }
            )

        non_truth_keepers = [
            row for row in seed_family_rows
            if _safe_int(row.get("is_truth_winner")) == 0
            and _safe_str(row.get("family_priority_band")) in {"medium", "explore_only"}
        ]
        if not non_truth_keepers:
            non_truth_candidates = [row for row in seed_family_rows if _safe_int(row.get("is_truth_winner")) == 0]
            if non_truth_candidates:
                non_truth_candidates.sort(
                    key=lambda row: (
                        FAMILY_STRENGTH_ORDER[_safe_str(row.get("family_strength_label"))],
                        -_safe_float(row.get("best_truth")),
                        -_safe_int(row.get("boundary_count")),
                        _safe_str(row.get("family_id")),
                    )
                )
                non_truth_candidates[0]["family_priority_band"] = "explore_only"

        seed_family_rows.sort(key=_family_sort_key)
        for rank, family_row in enumerate(seed_family_rows, start=1):
            family_row["family_priority_rank"] = rank

        primary_total, secondary_total, exploration_total = SEED_BUDGET_PROFILES[
            _safe_str(seed_triage_row.get("seed_budget_policy_label"))
        ]
        primary_family_row = seed_family_rows[0]
        primary_family_id = _safe_str(primary_family_row.get("family_id"))

        exploration_rows = [
            row for row in seed_family_rows[1:]
            if _safe_str(row.get("family_priority_band")) in {"explore_only", "low"}
        ]
        exploration_family_ids = {_safe_str(row.get("family_id")) for row in exploration_rows}
        secondary_rows = [
            row for row in seed_family_rows[1:]
            if _safe_str(row.get("family_id")) not in exploration_family_ids
        ]
        if not exploration_rows and secondary_rows:
            exploration_rows = [secondary_rows.pop(-1)]

        actual_primary_total = primary_total
        actual_secondary_total = secondary_total
        actual_exploration_total = exploration_total
        if not secondary_rows:
            actual_exploration_total += actual_secondary_total
            actual_secondary_total = 0.0
        if not exploration_rows:
            actual_secondary_total += actual_exploration_total
            actual_exploration_total = 0.0
        if not secondary_rows and not exploration_rows:
            actual_primary_total = 1.0
            actual_secondary_total = 0.0
            actual_exploration_total = 0.0

        share_map: dict[str, float] = {primary_family_id: actual_primary_total}
        share_map.update(_allocate_group_shares(secondary_rows, total_share=actual_secondary_total))
        share_map.update(_allocate_group_shares(exploration_rows, total_share=actual_exploration_total))

        ordered_family_ids = [_safe_str(row.get("family_id")) for row in seed_family_rows]
        share_total = 0.0
        for family_id in ordered_family_ids[:-1]:
            rounded = _round_share(share_map.get(family_id, 0.0))
            share_map[family_id] = rounded
            share_total += rounded
        share_map[ordered_family_ids[-1]] = _round_share(1.0 - share_total)

        for family_row in seed_family_rows:
            family_row["recommended_family_budget_share"] = share_map[_safe_str(family_row.get("family_id"))]
            family_priority_rows.append(family_row)

        secondary_family_ids = [_safe_str(row.get("family_id")) for row in secondary_rows]
        exploration_family_ids = [_safe_str(row.get("family_id")) for row in exploration_rows]
        budget_reason_codes = list(seed_triage_row.get("seed_reason_codes") or [])
        if not budget_reason_codes:
            budget_reason_codes = ["stop_only_fallback"]
        budget_rows.append(
            {
                "key_seed": key_seed,
                "primary_family_id": primary_family_id,
                "secondary_family_ids": secondary_family_ids,
                "exploration_family_ids": exploration_family_ids,
                "recommended_primary_budget_share": _round_share(actual_primary_total),
                "recommended_secondary_budget_share_total": _round_share(actual_secondary_total),
                "recommended_exploration_budget_share_total": _round_share(actual_exploration_total),
                "budget_policy_label": _safe_str(seed_triage_row.get("seed_budget_policy_label")),
                "budget_reason_codes": budget_reason_codes[:4],
            }
        )

    family_priority_rows.sort(
        key=lambda row: (
            _enriched_seed_order(_safe_int(row.get("key_seed"))),
            _safe_int(row.get("family_priority_rank")),
            _safe_str(row.get("family_id")),
        )
    )
    budget_rows.sort(key=lambda row: _enriched_seed_order(_safe_int(row.get("key_seed"))))
    return family_priority_rows, budget_rows


def build_triage_summary(
    *,
    seed_triage_rows: Sequence[Mapping[str, Any]],
    family_priority_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    seed_priority_band_counts = Counter(_safe_str(row.get("seed_priority_band")) for row in seed_triage_rows)
    seed_budget_policy_counts = Counter(_safe_str(row.get("seed_budget_policy_label")) for row in seed_triage_rows)
    family_priority_band_counts = Counter(_safe_str(row.get("family_priority_band")) for row in family_priority_rows)
    seeds_by_priority_band: dict[str, list[int]] = defaultdict(list)
    seeds_by_budget_policy: dict[str, list[int]] = defaultdict(list)
    for row in seed_triage_rows:
        key_seed = _safe_int(row.get("key_seed"))
        seeds_by_priority_band[_safe_str(row.get("seed_priority_band"))].append(key_seed)
        seeds_by_budget_policy[_safe_str(row.get("seed_budget_policy_label"))].append(key_seed)
    return {
        "input_score_stop_bundle_dir": _relative_path(INPUT_SCORE_STOP_BUNDLE_DIR),
        "input_lfq_v1_bundle_dir": _relative_path(INPUT_LFQ_V1_BUNDLE_DIR),
        "input_lfq_v2_bundle_dir": _relative_path(INPUT_LFQ_V2_BUNDLE_DIR),
        "input_lfq_v3_bundle_dir": _relative_path(INPUT_LFQ_V3_BUNDLE_DIR),
        "review_seed_count": len(seed_triage_rows),
        "family_enriched_seed_count": len(TRIAGE_FAMILY_ENRICHED_SEEDS),
        "seed_priority_band_counts": dict(sorted(seed_priority_band_counts.items())),
        "seed_budget_policy_counts": dict(sorted(seed_budget_policy_counts.items())),
        "family_priority_band_counts": dict(sorted(family_priority_band_counts.items())),
        "seeds_by_priority_band": {
            band: sorted(seeds)
            for band, seeds in sorted(seeds_by_priority_band.items())
        },
        "seeds_by_budget_policy": {
            policy: sorted(seeds)
            for policy, seeds in sorted(seeds_by_budget_policy.items())
        },
    }


def _metric_display(value: Any, *, integer: bool = False) -> str:
    if integer:
        return str(_safe_int(value))
    number = _safe_float(value)
    if not _is_finite(number):
        return "na"
    return f"{number:.3f}"


def _seed_read_bullets(
    seed_row: Mapping[str, Any],
    *,
    budget_row: Mapping[str, Any] | None,
) -> list[str]:
    band = _safe_str(seed_row.get("seed_priority_band"))
    codes = ", ".join(_safe_str(code) for code in seed_row.get("seed_reason_codes") or [])
    if band == "high":
        why_line = f"priority is high because the current evidence stack is openly positive (`{codes}`)"
    elif band == "medium":
        why_line = f"priority is medium because the read is usable but not yet strong (`{codes}`)"
    elif band == "low":
        why_line = f"priority is low because the current evidence is mostly quiet or reject-like (`{codes}`)"
    else:
        why_line = f"priority stays unclear because the current signals still conflict (`{codes}`)"

    if _safe_str(seed_row.get("triage_evidence_tier")) == "family_enriched":
        family_line = (
            "family evidence is helping by adding the frozen family-quality and pattern-strength context "
            f"(`{_safe_str(seed_row.get('family_quality_read_label')) or 'na'}` / "
            f"`{_safe_str(seed_row.get('pattern_strength_read_label')) or 'na'}`)"
        )
    else:
        family_line = "family evidence is not available here, so this seed is triaged from the stop-side shadow read only"

    if budget_row is None:
        budget_line = (
            "the shadow budget recommendation is to follow the seed-level portfolio only, "
            f"with primary=`{_metric_display(seed_row.get('recommended_primary_budget_share'))}`, "
            f"secondary=`{_metric_display(seed_row.get('recommended_secondary_budget_share'))}`, "
            f"exploration=`{_metric_display(seed_row.get('recommended_exploration_budget_share'))}`"
        )
    else:
        budget_line = (
            "the shadow budget recommendation is to keep primary focus on "
            f"`{_safe_str(budget_row.get('primary_family_id')) or 'na'}` while reserving "
            f"`{_metric_display(budget_row.get('recommended_exploration_budget_share_total'))}` "
            "for alternative-family exploration"
        )
    return [why_line, family_line, budget_line]


def write_triage_cases_markdown(
    output_dir: Path,
    *,
    seed_triage_rows: Sequence[Mapping[str, Any]],
    family_priority_rows: Sequence[Mapping[str, Any]],
    budget_rows: Sequence[Mapping[str, Any]],
) -> None:
    family_rows_by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in family_priority_rows:
        family_rows_by_seed[_safe_int(row.get("key_seed"))].append(dict(row))
    for rows in family_rows_by_seed.values():
        rows.sort(key=lambda row: _safe_int(row.get("family_priority_rank")))
    budget_by_seed = {_safe_int(row.get("key_seed")): dict(row) for row in budget_rows}

    lines: list[str] = ["# Seed Family Triage Shadow v1 Cases", ""]
    for seed_row in seed_triage_rows:
        key_seed = _safe_int(seed_row.get("key_seed"))
        lines.append(f"## Seed {key_seed}")
        lines.append("")
        lines.append(f"- Panel: `{_safe_str(seed_row.get('target_panel_name'))}` (`{_safe_str(seed_row.get('target_panel_role'))}`)")
        lines.append(f"- Evidence tier: `{_safe_str(seed_row.get('triage_evidence_tier'))}`")
        lines.append(
            f"- Current stop verdict: dump=`{_safe_int(seed_row.get('would_dump'))}` "
            f"stop=`{_safe_int(seed_row.get('would_stop'))}` "
            f"rule=`{_safe_str(seed_row.get('shadow_rule_id')) or 'na'}`"
        )
        lines.append(
            f"- Family-quality / pattern-strength read: "
            f"`{_safe_str(seed_row.get('family_quality_read_label')) or 'na'}` / "
            f"`{_safe_str(seed_row.get('pattern_strength_read_label')) or 'na'}`"
        )
        lines.append("")
        lines.append("### Seed Triage")
        lines.append("")
        lines.append(f"- Priority band: `{_safe_str(seed_row.get('seed_priority_band'))}`")
        lines.append(f"- Budget policy: `{_safe_str(seed_row.get('seed_budget_policy_label'))}`")
        lines.append(
            f"- Recommended seed-level split: primary=`{_metric_display(seed_row.get('recommended_primary_budget_share'))}` "
            f"secondary=`{_metric_display(seed_row.get('recommended_secondary_budget_share'))}` "
            f"exploration=`{_metric_display(seed_row.get('recommended_exploration_budget_share'))}`"
        )
        lines.append(f"- Reason codes: `{', '.join(_safe_str(code) for code in seed_row.get('seed_reason_codes') or []) or 'na'}`")
        lines.append("")

        seed_family_rows = family_rows_by_seed.get(key_seed, [])
        if seed_family_rows:
            lines.append("### Families")
            lines.append("")
            lines.append("| family | winner roles | strength | best truth | persistence | boundary count | reaches archive | priority band | recommended share |")
            lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: |")
            for family_row in seed_family_rows:
                winner_roles = [
                    label
                    for field_name, label in (
                        ("is_truth_winner", "truth"),
                        ("is_trust_winner", "trust"),
                        ("is_archive_winner", "archive"),
                        ("is_full_uplift_winner", "full"),
                        ("is_persistence_winner", "persist"),
                    )
                    if _safe_int(family_row.get(field_name)) == 1
                ]
                lines.append(
                    f"| {_safe_str(family_row.get('family_id'))} | "
                    f"{'/'.join(winner_roles) or 'na'} | "
                    f"{_safe_str(family_row.get('family_strength_label')) or 'na'} | "
                    f"{_metric_display(family_row.get('best_truth'))} | "
                    f"{_metric_display(family_row.get('family_persistence_count'), integer=True)} | "
                    f"{_metric_display(family_row.get('boundary_count'), integer=True)} | "
                    f"{_metric_display(family_row.get('family_reaches_archive'), integer=True)} | "
                    f"{_safe_str(family_row.get('family_priority_band')) or 'na'} | "
                    f"{_metric_display(family_row.get('recommended_family_budget_share'))} |"
                )
            lines.append("")

        budget_row = budget_by_seed.get(key_seed)
        for bullet in _seed_read_bullets(seed_row, budget_row=budget_row):
            lines.append(f"- {bullet}")
        lines.append("")

    (output_dir / "triage_cases.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    _require_bundle_files(INPUT_SCORE_STOP_BUNDLE_DIR, REQUIRED_STOP_INPUT_FILES, label="seed_family_triage_shadow_v1 stop bundle")
    _require_bundle_files(INPUT_LFQ_V1_BUNDLE_DIR, REQUIRED_LFQ_V1_INPUT_FILES, label="seed_family_triage_shadow_v1 late_family_quality_v1 bundle")
    _require_bundle_files(INPUT_LFQ_V2_BUNDLE_DIR, REQUIRED_LFQ_V2_INPUT_FILES, label="seed_family_triage_shadow_v1 late_family_quality_v2 bundle")
    _require_bundle_files(INPUT_LFQ_V3_BUNDLE_DIR, REQUIRED_LFQ_V3_INPUT_FILES, label="seed_family_triage_shadow_v1 late_family_quality_v3 bundle")

    stop_run_rows = _select_review_run_rows(_read_jsonl(INPUT_SCORE_STOP_BUNDLE_DIR / "run_shadow_summary.jsonl"))
    _read_jsonl(INPUT_SCORE_STOP_BUNDLE_DIR / "row_scores.jsonl")
    case_explanations_by_seed = _index_optional_case_rows(_read_jsonl(INPUT_SCORE_STOP_BUNDLE_DIR / "case_explanations.jsonl"))

    family_rows_by_seed = _index_family_rows_by_seed(_read_jsonl(INPUT_LFQ_V1_BUNDLE_DIR / "family_quality_rows.jsonl"))
    v1_case_digest_by_seed = _index_single_rows_by_seed(
        _read_jsonl(INPUT_LFQ_V1_BUNDLE_DIR / "family_quality_case_digest.jsonl"),
        seed_scope=TRIAGE_FAMILY_ENRICHED_SEEDS,
        source_name="late_family_quality_v1 family_quality_case_digest",
    )
    _read_json(INPUT_LFQ_V1_BUNDLE_DIR / "family_quality_summary.json")

    v2_agreement_by_seed = _index_single_rows_by_seed(
        _read_jsonl(INPUT_LFQ_V2_BUNDLE_DIR / "seed_agreement_rows.jsonl"),
        seed_scope=TRIAGE_FAMILY_ENRICHED_SEEDS,
        source_name="late_family_quality_v2 seed_agreement_rows",
    )
    _read_jsonl(INPUT_LFQ_V2_BUNDLE_DIR / "winner_pairwise_rows.jsonl")
    _read_json(INPUT_LFQ_V2_BUNDLE_DIR / "agreement_summary.json")

    v3_pattern_by_seed = _index_single_rows_by_seed(
        _read_jsonl(INPUT_LFQ_V3_BUNDLE_DIR / "pattern_strength_rows.jsonl"),
        seed_scope=TRIAGE_FAMILY_ENRICHED_SEEDS,
        source_name="late_family_quality_v3 pattern_strength_rows",
    )
    v3_pair_by_seed = _index_pair_rows_by_seed(_read_jsonl(INPUT_LFQ_V3_BUNDLE_DIR / "truth_relative_pair_rows.jsonl"))
    _read_json(INPUT_LFQ_V3_BUNDLE_DIR / "pattern_strength_summary.json")

    _require_enriched_seed_inputs(
        family_rows_by_seed=family_rows_by_seed,
        v1_digest_by_seed=v1_case_digest_by_seed,
        v2_agreement_by_seed=v2_agreement_by_seed,
        v3_pattern_by_seed=v3_pattern_by_seed,
        v3_pair_by_seed=v3_pair_by_seed,
    )

    seed_triage_rows = build_seed_triage_rows(
        stop_run_rows=stop_run_rows,
        case_explanations_by_seed=case_explanations_by_seed,
        v1_case_digest_by_seed=v1_case_digest_by_seed,
        v2_agreement_by_seed=v2_agreement_by_seed,
        v3_pattern_by_seed=v3_pattern_by_seed,
    )
    family_priority_rows, budget_rows = build_family_priority_rows(
        seed_triage_rows=seed_triage_rows,
        family_rows_by_seed=family_rows_by_seed,
        v1_case_digest_by_seed=v1_case_digest_by_seed,
        v3_pair_by_seed=v3_pair_by_seed,
    )
    summary = build_triage_summary(
        seed_triage_rows=seed_triage_rows,
        family_priority_rows=family_priority_rows,
    )

    output_dir = OUTPUT_BASE_DIR / f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}__seed_family_triage_shadow_v1"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / "seed_triage_rows.jsonl", seed_triage_rows)
    _write_jsonl(output_dir / "family_priority_rows.jsonl", family_priority_rows)
    _write_jsonl(output_dir / "budget_recommendation_rows.jsonl", budget_rows)
    _write_json(output_dir / "triage_summary.json", summary)
    write_triage_cases_markdown(
        output_dir,
        seed_triage_rows=seed_triage_rows,
        family_priority_rows=family_priority_rows,
        budget_rows=budget_rows,
    )
    print(
        "[seed_family_triage_shadow_v1] "
        f"review_seeds={len(seed_triage_rows)} "
        f"family_rows={len(family_priority_rows)} "
        f"budget_rows={len(budget_rows)} "
        f"output={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
