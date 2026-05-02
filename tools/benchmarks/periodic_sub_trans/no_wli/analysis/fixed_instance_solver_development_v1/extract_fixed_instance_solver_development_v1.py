from __future__ import annotations

import csv
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
    raise RuntimeError(
        "Could not locate repo root from "
        "extract_fixed_instance_solver_development_v1.py"
    )


REPO_ROOT = _find_repo_root()
INPUT_EXTERNAL_REVIEW_PACK_DIR = REPO_ROOT / Path(
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_fixed_panel_v1_external_review_pack_2026-04-14"
)
INPUT_STAGE35_FAMILY_PACK_DIR = REPO_ROOT / Path(
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_fixed_panel_v1_cross_seed_stage35_family_and_1111_focus_family_pack_2026-04-14"
)
INPUT_1111_SUPPLEMENT_PACK_DIR = REPO_ROOT / Path(
    "planning/projects/no_wli/40_review_summaries/"
    "no_wli_fixed_panel_v1_1111_stage35_family_supplement_2026-04-14"
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "fixed_instance_solver_development_v1"
)
PANEL_INVENTORY_CSV = (
    INPUT_EXTERNAL_REVIEW_PACK_DIR
    / "30_run_state_and_events"
    / "20job_panel_inventory.csv"
)
STAGE35_RUN_SUMMARY_CSV = (
    INPUT_STAGE35_FAMILY_PACK_DIR
    / "10_option_a_cross_seed_stage35_family"
    / "00_cross_seed_run_summary.csv"
)
STAGE35_SEED_SUMMARY_CSV = (
    INPUT_STAGE35_FAMILY_PACK_DIR
    / "10_option_a_cross_seed_stage35_family"
    / "01_cross_seed_seed_summary.csv"
)
CROSS_SEED_STAGE35_FAMILY_DIR = (
    INPUT_STAGE35_FAMILY_PACK_DIR
    / "10_option_a_cross_seed_stage35_family"
)
FOCUS_1111_RUN_SUMMARY_CSV = (
    INPUT_STAGE35_FAMILY_PACK_DIR
    / "20_option_b_1111_focus_family_context"
    / "00_1111_focus_family_run_summary.csv"
)
FOCUS_1111_ALL_FAMILY_SUMMARY_CSV = (
    INPUT_STAGE35_FAMILY_PACK_DIR
    / "20_option_b_1111_focus_family_context"
    / "01_1111_all_family_summary.csv"
)
SUPPLEMENT_1111_ALL_JOIN_CSV = (
    INPUT_1111_SUPPLEMENT_PACK_DIR
    / "03_all_1111_stage35_family_join.csv"
)
SUPPLEMENT_1111_RAW_STAGE35_DIR = (
    INPUT_1111_SUPPLEMENT_PACK_DIR
    / "20_raw_stage35_seed_artifacts"
)
SEED1511_STAGE35_FAMILY_DIR = CROSS_SEED_STAGE35_FAMILY_DIR / "seed1511"
SEED1511_ALL_JOIN_CSV = (
    SEED1511_STAGE35_FAMILY_DIR
    / "02_seed1511_all_stage35_family_join.csv"
)
SEED1511_RAW_STAGE35_DIR = (
    SEED1511_STAGE35_FAMILY_DIR
    / "20_raw_stage35_seed_artifacts"
)
SEED611_STAGE35_FAMILY_DIR = CROSS_SEED_STAGE35_FAMILY_DIR / "seed611"
SEED611_ALL_JOIN_CSV = (
    SEED611_STAGE35_FAMILY_DIR
    / "02_seed611_all_stage35_family_join.csv"
)
SEED611_RAW_STAGE35_DIR = (
    SEED611_STAGE35_FAMILY_DIR
    / "20_raw_stage35_seed_artifacts"
)
REQUIRED_INPUT_PATHS = (
    PANEL_INVENTORY_CSV,
    STAGE35_RUN_SUMMARY_CSV,
    STAGE35_SEED_SUMMARY_CSV,
    FOCUS_1111_RUN_SUMMARY_CSV,
    FOCUS_1111_ALL_FAMILY_SUMMARY_CSV,
    SUPPLEMENT_1111_ALL_JOIN_CSV,
    SUPPLEMENT_1111_RAW_STAGE35_DIR,
    SEED1511_ALL_JOIN_CSV,
    SEED1511_RAW_STAGE35_DIR,
    SEED611_ALL_JOIN_CSV,
    SEED611_RAW_STAGE35_DIR,
)
CASE_ROLE_BY_FIXTURE_SEED = {
    1511: "positive_control",
    611: "middle_unsolved_case",
    1111: "conversion_failure_case",
    1411: "caveated_cross_check",
}
FIXTURE_SEED_ORDER = (1511, 611, 1111, 1411)
SEARCH_SEED_ORDER = (7001, 7002, 7003, 7004, 7005)
TRUST_FIELD_NAMES = (
    "word_ngram_judge_trust_score",
    "word_ngram_judge_trust_tier",
    "word_ngram_judge_report_xent",
    "word_ngram_judge_n_positions",
    "word_ngram_judge_active",
)
REQUIRED_PANEL_INVENTORY_COLUMNS = (
    "panel_job_index",
    "source_run_label",
    "fixture_seed",
    "search_seed",
    "status",
    "stop_reason",
    "best_stage",
    "best_match_ratio",
    "stage35_selected",
    "stage35_proof_valid",
    "total_seconds",
    "source_report_dir",
    "copied_report_dir",
)
REQUIRED_STAGE35_RUN_SUMMARY_COLUMNS = (
    "panel_job_index",
    "source_run_label",
    "fixture_seed",
    "search_seed",
    "status",
    "best_stage",
    "best_match_ratio",
    "stage35_selected",
    "source_report_dir",
    "best_path",
    "archive_path",
    "progress_path",
    "archive_seed_row_count",
    "best_stage35_seed_row_count",
    "space_map_stage35_row_count",
    "joined_row_count",
    "distinct_stage35_family_count",
    "dominant_stage35_family_id",
    "dominant_stage35_family_share",
    "focus_stage35_family_id",
    "stage35_family_counts",
)
REQUIRED_STAGE35_SEED_SUMMARY_COLUMNS = (
    "fixture_seed",
    "run_count",
    "solved_run_count",
    "stage35_selected_run_count",
    "zero_family_mapped_stage35_run_count",
    "mean_best_match_ratio",
    "max_best_match_ratio",
    "searches_with_single_family_stage35",
    "searches_with_zero_family_mapped_stage35_rows",
)
REQUIRED_1111_RUN_SUMMARY_COLUMNS = (
    "fixture_seed",
    "search_seed",
    "focus_family_id",
    "focus_family_total_rows",
    "focus_family_stage35_rows",
    "focus_family_selected_rows",
    "focus_family_admitted_rows",
    "focus_family_max_final_score",
    "focus_family_max_final_match",
)
REQUIRED_1111_ALL_FAMILY_SUMMARY_COLUMNS = (
    "search_seed",
    "family_id",
    "row_count",
    "selected_row_count",
    "admitted_row_count",
    "stage35_row_count",
)
REQUIRED_SUPPLEMENT_1111_JOIN_COLUMNS = (
    "fixture_seed",
    "search_seed",
)
REQUIRED_SEED_JOIN_COLUMNS = (
    "panel_job_index",
    "search_seed",
)


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


def _safe_optional_float(value: Any) -> float | None:
    number = _safe_float(value)
    if math.isfinite(number):
        return number
    return None


def _is_finite(value: Any) -> bool:
    return math.isfinite(_safe_float(value))


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = _safe_str(value).strip().lower()
    if text in {"1", "true", "yes"}:
        return True
    if text in {"0", "false", "no", ""}:
        return False
    raise ValueError(f"Unrecognized boolean value: {value!r}")


def _json_default(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _normalize_csv_fieldname(name: str) -> str:
    return name.replace("\ufeff", "").strip().strip('"').strip()


def _read_json(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV file has no header row: {path}")
        normalized = [_normalize_csv_fieldname(name) for name in reader.fieldnames]
        rows: list[dict[str, str]] = []
        for raw_row in reader:
            row: dict[str, str] = {}
            for original_name, normalized_name in zip(reader.fieldnames, normalized):
                row[normalized_name] = raw_row.get(original_name, "") or ""
            rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True, default=_json_default))
            handle.write("\n")


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    fieldnames = list(dict(rows[0]).keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            payload: dict[str, Any] = {}
            for key, value in dict(row).items():
                if isinstance(value, list):
                    payload[key] = "; ".join(str(item) for item in value)
                elif isinstance(value, float) and not math.isfinite(value):
                    payload[key] = ""
                else:
                    payload[key] = value
            writer.writerow(payload)


def _require_input_paths(paths: Sequence[Path]) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing required fixed-instance solver-development inputs: "
            + ", ".join(sorted(missing))
        )


def _require_csv_columns(
    *,
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    required_columns: Sequence[str],
) -> None:
    if not rows:
        raise ValueError(f"CSV file has no data rows: {path}")
    actual_columns = set(dict(rows[0]).keys())
    missing_columns = sorted(
        column for column in required_columns if column not in actual_columns
    )
    if missing_columns:
        raise ValueError(
            f"Missing required columns in {path}: {', '.join(missing_columns)}"
        )


def _require_fixture_seed_coverage(
    *,
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    required_fixture_seeds: Sequence[int],
) -> None:
    seen_fixture_seeds = {
        _safe_int(row.get("fixture_seed"))
        for row in rows
    }
    missing_fixture_seeds = sorted(
        seed for seed in required_fixture_seeds if seed not in seen_fixture_seeds
    )
    if missing_fixture_seeds:
        raise ValueError(
            f"Missing required fixture seeds in {path}: {missing_fixture_seeds}"
        )


def _require_search_seed_coverage(
    *,
    path: Path,
    rows: Sequence[Mapping[str, Any]],
    required_search_seeds: Sequence[int],
) -> None:
    seen_search_seeds = {
        _safe_int(row.get("search_seed"))
        for row in rows
    }
    missing_search_seeds = sorted(
        seed for seed in required_search_seeds if seed not in seen_search_seeds
    )
    if missing_search_seeds:
        raise ValueError(
            f"Missing required search seeds in {path}: {missing_search_seeds}"
        )


def _fixture_seed_order(fixture_seed: int) -> int:
    try:
        return FIXTURE_SEED_ORDER.index(int(fixture_seed))
    except ValueError:
        return len(FIXTURE_SEED_ORDER)


def _search_seed_order(search_seed: int) -> int:
    try:
        return SEARCH_SEED_ORDER.index(int(search_seed))
    except ValueError:
        return len(SEARCH_SEED_ORDER)


def _run_key(*, fixture_seed: Any, search_seed: Any) -> tuple[int, int]:
    return (_safe_int(fixture_seed), _safe_int(search_seed))


def _derive_run_id(source_report_dir: str) -> str:
    return Path(source_report_dir).name


def _best_instance_rel_path(copied_report_dir: str) -> str:
    return f"{copied_report_dir.strip('/')}/best/best_instance.json"


def _benchmark_case_role(fixture_seed: int) -> str:
    try:
        return CASE_ROLE_BY_FIXTURE_SEED[int(fixture_seed)]
    except KeyError as exc:
        raise ValueError(f"Unexpected fixture seed for fixed panel: {fixture_seed}") from exc


def _baseline_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _safe_int(row.get("panel_job_index")),
        _fixture_seed_order(_safe_int(row.get("fixture_seed"))),
        _search_seed_order(_safe_int(row.get("search_seed"))),
        _safe_str(row.get("source_run_label")),
    )


def _build_caveat_flags(row: Mapping[str, Any]) -> list[str]:
    flags: list[str] = []
    archive_seed_row_count = _safe_int(row.get("archive_seed_row_count"))
    best_stage35_seed_row_count = _safe_int(row.get("best_stage35_seed_row_count"))
    space_map_stage35_row_count = _safe_int(row.get("space_map_stage35_row_count"))
    status = _safe_str(row.get("status"))
    best_stage = _safe_str(row.get("best_stage"))
    focus_family_id = _safe_str(row.get("focus_stage35_family_id"))
    dominant_family_id = _safe_str(row.get("dominant_stage35_family_id"))
    fixture_seed = _safe_int(row.get("fixture_seed"))

    if space_map_stage35_row_count == 0:
        flags.append("no_family_mapped_stage35_rows")
    if archive_seed_row_count > 0 and best_stage35_seed_row_count == 0:
        flags.append("archive_only_stage35_seed_rows")
    if archive_seed_row_count > 0 and status == "solved" and best_stage == "stage3_full_refine":
        flags.append("solved_stage3_with_archive_side_stage35_rows")
    if archive_seed_row_count > 0 and space_map_stage35_row_count == 0 and status == "solved":
        flags.append("solved_without_family_mapped_stage35_rows")
    if focus_family_id and dominant_family_id and focus_family_id != dominant_family_id:
        flags.append("focus_family_differs_from_dominant_mapped_stage35_family")
    if fixture_seed == 1411:
        flags.append("fixture_role_caveated_cross_check")
    return flags


def _validate_panel_row_alignment(
    inventory_row: Mapping[str, Any],
    stage35_row: Mapping[str, Any],
    best_instance: Mapping[str, Any],
) -> None:
    inventory_status = _safe_str(inventory_row.get("status"))
    best_status = _safe_str(best_instance.get("status"))
    if best_status and inventory_status and best_status != inventory_status:
        raise ValueError(
            "Status mismatch between inventory and best_instance: "
            f"{inventory_status} != {best_status}"
        )

    inventory_best_stage = _safe_str(inventory_row.get("best_stage"))
    best_stage = _safe_str(best_instance.get("best_stage"))
    if inventory_best_stage and best_stage and inventory_best_stage != best_stage:
        raise ValueError(
            "best_stage mismatch between inventory and best_instance: "
            f"{inventory_best_stage} != {best_stage}"
        )

    inventory_selected = _safe_bool(inventory_row.get("stage35_selected"))
    stage35_selected = _safe_bool(stage35_row.get("stage35_selected"))
    best_selected = _safe_bool(best_instance.get("stage35_selected"))
    if inventory_selected != stage35_selected or inventory_selected != best_selected:
        raise ValueError(
            "stage35_selected mismatch across retained inputs for "
            f"fixture_seed={inventory_row.get('fixture_seed')} "
            f"search_seed={inventory_row.get('search_seed')}"
        )

    inventory_best_match = _safe_float(inventory_row.get("best_match_ratio"))
    best_match = _safe_float(best_instance.get("best_match_ratio"))
    if _is_finite(inventory_best_match) and _is_finite(best_match):
        if abs(inventory_best_match - best_match) > 1e-9:
            raise ValueError(
                "best_match_ratio mismatch between inventory and best_instance: "
                f"{inventory_best_match} != {best_match}"
            )


def build_panel_baseline_rows(
    panel_inventory_rows: Sequence[Mapping[str, Any]],
    stage35_run_summary_rows: Sequence[Mapping[str, Any]],
    best_instances_by_run_key: Mapping[tuple[int, int], Mapping[str, Any]],
    focus_1111_rows_by_run_key: Mapping[tuple[int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    inventory_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in panel_inventory_rows
    }
    stage35_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in stage35_run_summary_rows
    }
    if set(inventory_by_run_key) != set(stage35_by_run_key):
        missing_from_stage35 = sorted(set(inventory_by_run_key) - set(stage35_by_run_key))
        missing_from_inventory = sorted(set(stage35_by_run_key) - set(inventory_by_run_key))
        raise ValueError(
            "Mismatch between panel inventory and stage35 summary run keys: "
            f"missing_from_stage35={missing_from_stage35} "
            f"missing_from_inventory={missing_from_inventory}"
        )
    if set(inventory_by_run_key) != set(best_instances_by_run_key):
        missing_best = sorted(set(inventory_by_run_key) - set(best_instances_by_run_key))
        raise ValueError(f"Missing best_instance inputs for run keys: {missing_best}")

    rows: list[dict[str, Any]] = []
    for run_key in sorted(
        inventory_by_run_key,
        key=lambda item: (_fixture_seed_order(item[0]), _search_seed_order(item[1])),
    ):
        inventory_row = inventory_by_run_key[run_key]
        stage35_row = stage35_by_run_key[run_key]
        best_instance = dict(best_instances_by_run_key[run_key])
        focus_row = dict(focus_1111_rows_by_run_key.get(run_key, {}))

        _validate_panel_row_alignment(inventory_row, stage35_row, best_instance)

        fixture_seed, search_seed = run_key
        source_report_dir = _safe_str(inventory_row.get("source_report_dir"))
        copied_report_dir = _safe_str(inventory_row.get("copied_report_dir"))
        run_id = _derive_run_id(source_report_dir)
        row: dict[str, Any] = {
            "panel_job_index": _safe_int(inventory_row.get("panel_job_index")),
            "run_id": run_id,
            "source_run_label": _safe_str(inventory_row.get("source_run_label")),
            "fixture_seed": fixture_seed,
            "instance_source_key_seed": _safe_int(best_instance.get("instance_source_key_seed"), fixture_seed),
            "instance_fixture_id": _safe_str(best_instance.get("instance_fixture_id")),
            "search_seed": search_seed,
            "benchmark_case_role": _benchmark_case_role(fixture_seed),
            "primary_tuning_target": int(fixture_seed in {1511, 611, 1111}),
            "cross_check_case": int(fixture_seed == 1411),
            "run_type": "fixed_panel_completed_job",
            "status": _safe_str(inventory_row.get("status")) or _safe_str(best_instance.get("status")),
            "stop_reason": _safe_str(inventory_row.get("stop_reason")),
            "best_stage": _safe_str(inventory_row.get("best_stage")) or _safe_str(best_instance.get("best_stage")),
            "best_match_ratio": _safe_float(inventory_row.get("best_match_ratio")),
            "best_score": _safe_float(best_instance.get("best_score")),
            "stage35_selected": int(_safe_bool(inventory_row.get("stage35_selected"))),
            "stage35_proof_valid": _safe_int(inventory_row.get("stage35_proof_valid")),
            "total_seconds": _safe_float(inventory_row.get("total_seconds")),
            "archive_seed_row_count": _safe_int(stage35_row.get("archive_seed_row_count")),
            "best_stage35_seed_row_count": _safe_int(stage35_row.get("best_stage35_seed_row_count")),
            "space_map_stage35_row_count": _safe_int(stage35_row.get("space_map_stage35_row_count")),
            "joined_row_count": _safe_int(stage35_row.get("joined_row_count")),
            "distinct_stage35_family_count": _safe_int(stage35_row.get("distinct_stage35_family_count")),
            "focus_stage35_family_id": _safe_str(stage35_row.get("focus_stage35_family_id")),
            "dominant_stage35_family_id": _safe_str(stage35_row.get("dominant_stage35_family_id")),
            "dominant_stage35_family_share": _safe_optional_float(
                stage35_row.get("dominant_stage35_family_share")
            ),
            "stage35_family_counts": _safe_str(stage35_row.get("stage35_family_counts")),
            "word_ngram_judge_active": int(_safe_bool(best_instance.get("word_ngram_judge_active"))),
            "word_ngram_judge_report_xent": _safe_float(best_instance.get("word_ngram_judge_report_xent")),
            "word_ngram_judge_trust_score": _safe_float(best_instance.get("word_ngram_judge_trust_score")),
            "word_ngram_judge_trust_tier": _safe_str(best_instance.get("word_ngram_judge_trust_tier")),
            "word_ngram_judge_n_positions": _safe_int(best_instance.get("word_ngram_judge_n_positions")),
            "source_report_dir": source_report_dir,
            "copied_report_dir": copied_report_dir,
            "best_instance_rel_path": _best_instance_rel_path(copied_report_dir),
            "source_best_path": _safe_str(stage35_row.get("best_path")),
            "source_archive_path": _safe_str(stage35_row.get("archive_path")),
            "source_progress_path": _safe_str(stage35_row.get("progress_path")),
            "family_summary_available": int(_safe_int(stage35_row.get("space_map_stage35_row_count")) > 0),
            "focus_family_definition": "top_stage35_admitted_row_family",
            "trust_field_names": list(TRUST_FIELD_NAMES),
            "focus_family_total_rows": _safe_int(focus_row.get("focus_family_total_rows"), default=-1),
            "focus_family_stage35_rows": _safe_int(focus_row.get("focus_family_stage35_rows"), default=-1),
            "focus_family_selected_rows": _safe_int(focus_row.get("focus_family_selected_rows"), default=-1),
            "focus_family_admitted_rows": _safe_int(focus_row.get("focus_family_admitted_rows"), default=-1),
            "focus_family_max_final_score": _safe_optional_float(
                focus_row.get("focus_family_max_final_score")
            ),
            "focus_family_max_final_match": _safe_optional_float(
                focus_row.get("focus_family_max_final_match")
            ),
            "family_mapping_caveat": int(
                _safe_str(inventory_row.get("status")) == "solved"
                and _safe_int(stage35_row.get("archive_seed_row_count")) > 0
                and _safe_int(stage35_row.get("space_map_stage35_row_count")) == 0
            ),
        }
        row["caveat_flags"] = _build_caveat_flags(row)
        row["caveat_flag_count"] = len(row["caveat_flags"])
        rows.append(row)

    rows.sort(key=_baseline_sort_key)
    return rows


def _instance_caveat_note(fixture_seed: int) -> str:
    if fixture_seed == 1511:
        return "positive control; solved run is a stage-3 solve and keeps archive-side stage35 rows without family-mapped stage35 rows"
    if fixture_seed == 611:
        return "middle unsolved case; useful tuning target because it is neither dead nor solved"
    if fixture_seed == 1111:
        return "conversion-failure case; focus family and dominant mapped family can diverge across search seeds"
    if fixture_seed == 1411:
        return "caveated cross-check; solved run keeps archive-side stage35 rows but no family-mapped stage35 rows on the best/space_map side"
    return ""


def build_instance_summary_rows(
    baseline_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        grouped[_safe_int(row.get("fixture_seed"))].append(dict(row))

    summary_rows: list[dict[str, Any]] = []
    for fixture_seed in sorted(grouped, key=_fixture_seed_order):
        seed_rows = sorted(grouped[fixture_seed], key=_baseline_sort_key)
        best_row = max(
            seed_rows,
            key=lambda row: (
                _safe_float(row.get("best_match_ratio")),
                -_search_seed_order(_safe_int(row.get("search_seed"))),
            ),
        )
        status_counts = Counter(_safe_str(row.get("status")) for row in seed_rows)
        best_stage_counts = Counter(_safe_str(row.get("best_stage")) for row in seed_rows)
        single_family_searches = [
            _safe_int(row.get("search_seed"))
            for row in seed_rows
            if _safe_int(row.get("space_map_stage35_row_count")) > 0
            and _safe_int(row.get("distinct_stage35_family_count")) == 1
        ]
        zero_family_searches = [
            _safe_int(row.get("search_seed"))
            for row in seed_rows
            if _safe_int(row.get("space_map_stage35_row_count")) == 0
        ]
        summary_row: dict[str, Any] = {
            "fixture_seed": fixture_seed,
            "benchmark_case_role": _benchmark_case_role(fixture_seed),
            "primary_tuning_target": int(fixture_seed in {1511, 611, 1111}),
            "cross_check_case": int(fixture_seed == 1411),
            "run_count": len(seed_rows),
            "solved_run_count": status_counts.get("solved", 0),
            "stalled_run_count": status_counts.get("stalled", 0),
            "unsolved_run_count": status_counts.get("unsolved", 0),
            "stage35_selected_run_count": sum(_safe_int(row.get("stage35_selected")) for row in seed_rows),
            "zero_family_mapped_stage35_run_count": len(zero_family_searches),
            "family_mapping_caveat_run_count": sum(
                _safe_int(row.get("family_mapping_caveat")) for row in seed_rows
            ),
            "mean_best_match_ratio": sum(_safe_float(row.get("best_match_ratio")) for row in seed_rows) / len(seed_rows),
            "max_best_match_ratio": _safe_float(best_row.get("best_match_ratio")),
            "max_best_match_search_seed": _safe_int(best_row.get("search_seed")),
            "mean_archive_seed_row_count": sum(_safe_int(row.get("archive_seed_row_count")) for row in seed_rows) / len(seed_rows),
            "mean_best_stage35_seed_row_count": sum(_safe_int(row.get("best_stage35_seed_row_count")) for row in seed_rows) / len(seed_rows),
            "mean_space_map_stage35_row_count": sum(_safe_int(row.get("space_map_stage35_row_count")) for row in seed_rows) / len(seed_rows),
            "searches_with_single_family_stage35": single_family_searches,
            "searches_with_zero_family_mapped_stage35_rows": zero_family_searches,
            "best_stage_counts": dict(sorted(best_stage_counts.items())),
            "caveat_note": _instance_caveat_note(fixture_seed),
        }
        summary_rows.append(summary_row)
    return summary_rows


def validate_instance_summary_against_seed_summary(
    instance_summary_rows: Sequence[Mapping[str, Any]],
    stage35_seed_summary_rows: Sequence[Mapping[str, Any]],
) -> None:
    expected_by_seed = {
        _safe_int(row.get("fixture_seed")): dict(row)
        for row in stage35_seed_summary_rows
    }
    actual_by_seed = {
        _safe_int(row.get("fixture_seed")): dict(row)
        for row in instance_summary_rows
    }
    if set(expected_by_seed) != set(actual_by_seed):
        raise ValueError(
            "Seed-summary fixture coverage mismatch: "
            f"expected={sorted(expected_by_seed)} actual={sorted(actual_by_seed)}"
        )

    for fixture_seed, expected in expected_by_seed.items():
        actual = actual_by_seed[fixture_seed]
        for field_name in (
            "run_count",
            "solved_run_count",
            "stage35_selected_run_count",
            "zero_family_mapped_stage35_run_count",
        ):
            if _safe_int(actual.get(field_name)) != _safe_int(expected.get(field_name)):
                raise ValueError(
                    f"Seed summary mismatch for fixture_seed={fixture_seed} field={field_name}: "
                    f"{actual.get(field_name)!r} != {expected.get(field_name)!r}"
                )
        for field_name in ("mean_best_match_ratio", "max_best_match_ratio"):
            actual_value = _safe_float(actual.get(field_name))
            expected_value = _safe_float(expected.get(field_name))
            if _is_finite(actual_value) and _is_finite(expected_value):
                if abs(actual_value - expected_value) > 1e-9:
                    raise ValueError(
                        f"Seed summary mismatch for fixture_seed={fixture_seed} field={field_name}: "
                        f"{actual_value} != {expected_value}"
                    )
        actual_single = ", ".join(str(seed) for seed in actual.get("searches_with_single_family_stage35") or [])
        expected_single = _safe_str(expected.get("searches_with_single_family_stage35"))
        if actual_single != expected_single:
            raise ValueError(
                f"Single-family search mismatch for fixture_seed={fixture_seed}: "
                f"{actual_single!r} != {expected_single!r}"
            )
        actual_zero = ", ".join(
            str(seed) for seed in actual.get("searches_with_zero_family_mapped_stage35_rows") or []
        )
        expected_zero = _safe_str(expected.get("searches_with_zero_family_mapped_stage35_rows"))
        if actual_zero != expected_zero:
            raise ValueError(
                f"Zero-family-mapped search mismatch for fixture_seed={fixture_seed}: "
                f"{actual_zero!r} != {expected_zero!r}"
            )


def build_instance_search_matrix_rows(
    baseline_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in baseline_rows:
        grouped[_safe_int(row.get("fixture_seed"))][_safe_int(row.get("search_seed"))] = dict(row)

    matrix_rows: list[dict[str, Any]] = []
    for fixture_seed in sorted(grouped, key=_fixture_seed_order):
        row: dict[str, Any] = {
            "fixture_seed": fixture_seed,
            "benchmark_case_role": _benchmark_case_role(fixture_seed),
        }
        seed_rows = grouped[fixture_seed]
        for search_seed in SEARCH_SEED_ORDER:
            seed_row = seed_rows.get(search_seed)
            prefix = f"search{search_seed}"
            if seed_row is None:
                row[f"{prefix}_status"] = ""
                row[f"{prefix}_best_match_ratio"] = ""
                row[f"{prefix}_best_stage"] = ""
                row[f"{prefix}_stage35_selected"] = ""
                row[f"{prefix}_archive_seed_row_count"] = ""
                row[f"{prefix}_best_stage35_seed_row_count"] = ""
                row[f"{prefix}_space_map_stage35_row_count"] = ""
                row[f"{prefix}_focus_family_id"] = ""
                row[f"{prefix}_dominant_stage35_family_id"] = ""
                row[f"{prefix}_caveat_flags"] = ""
                continue
            row[f"{prefix}_status"] = _safe_str(seed_row.get("status"))
            row[f"{prefix}_best_match_ratio"] = _safe_float(seed_row.get("best_match_ratio"))
            row[f"{prefix}_best_stage"] = _safe_str(seed_row.get("best_stage"))
            row[f"{prefix}_stage35_selected"] = _safe_int(seed_row.get("stage35_selected"))
            row[f"{prefix}_archive_seed_row_count"] = _safe_int(seed_row.get("archive_seed_row_count"))
            row[f"{prefix}_best_stage35_seed_row_count"] = _safe_int(seed_row.get("best_stage35_seed_row_count"))
            row[f"{prefix}_space_map_stage35_row_count"] = _safe_int(seed_row.get("space_map_stage35_row_count"))
            row[f"{prefix}_focus_family_id"] = _safe_str(seed_row.get("focus_stage35_family_id"))
            row[f"{prefix}_dominant_stage35_family_id"] = _safe_str(seed_row.get("dominant_stage35_family_id"))
            row[f"{prefix}_caveat_flags"] = "; ".join(
                _safe_str(flag) for flag in seed_row.get("caveat_flags") or []
            )
        matrix_rows.append(row)
    return matrix_rows


def _summary_sort_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (_fixture_seed_order(_safe_int(row.get("fixture_seed"))), _safe_int(row.get("fixture_seed")))


def _ratio_text(value: Any) -> str:
    number = _safe_float(value)
    if not _is_finite(number):
        return "na"
    return f"{number:.3f}"


def _family_alignment_label(
    *,
    focus_family_id: str,
    dominant_family_id: str,
    final_best_family_id: str,
) -> str:
    same_focus_dominant = bool(focus_family_id and focus_family_id == dominant_family_id)
    same_focus_final = bool(focus_family_id and focus_family_id == final_best_family_id)
    same_dominant_final = bool(
        dominant_family_id and dominant_family_id == final_best_family_id
    )
    if same_focus_dominant and same_focus_final:
        return "all_aligned"
    if same_focus_final:
        return "focus_and_final_best_aligned"
    if same_focus_dominant:
        return "focus_and_dominant_aligned"
    if same_dominant_final:
        return "dominant_and_final_best_aligned"
    return "all_split"


def write_baseline_cases_markdown(
    output_dir: Path,
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    instance_summary_rows: Sequence[Mapping[str, Any]],
) -> None:
    rows_by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in baseline_rows:
        rows_by_seed[_safe_int(row.get("fixture_seed"))].append(dict(row))
    for seed_rows in rows_by_seed.values():
        seed_rows.sort(key=_baseline_sort_key)

    lines: list[str] = [
        "# Fixed-Instance Solver Baseline Cases",
        "",
        "Frozen inputs:",
        f"- `{_relative_path(INPUT_EXTERNAL_REVIEW_PACK_DIR)}`",
        f"- `{_relative_path(INPUT_STAGE35_FAMILY_PACK_DIR)}`",
        f"- `{_relative_path(INPUT_1111_SUPPLEMENT_PACK_DIR)}`",
        "",
        "Primary tuning trio:",
        "- `1511` - positive control",
        "- `611` - middle unsolved case",
        "- `1111` - conversion-failure case",
        "",
        "Cross-check case:",
        "- `1411` - useful but caveated cross-check",
        "",
        "Solved-run caveat:",
        "- `1411/search7003` and `1511/search7001` keep archive-side stage35 rows but no family-mapped stage35 rows on the best/space_map side",
        "",
        "| fixture seed | role | runs | solved | stalled | stage35 selected | mean best match | max best match | note |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary_row in sorted(instance_summary_rows, key=_summary_sort_key):
        lines.append(
            f"| {_safe_int(summary_row.get('fixture_seed'))} | "
            f"{_safe_str(summary_row.get('benchmark_case_role'))} | "
            f"{_safe_int(summary_row.get('run_count'))} | "
            f"{_safe_int(summary_row.get('solved_run_count'))} | "
            f"{_safe_int(summary_row.get('stalled_run_count'))} | "
            f"{_safe_int(summary_row.get('stage35_selected_run_count'))} | "
            f"{_ratio_text(summary_row.get('mean_best_match_ratio'))} | "
            f"{_ratio_text(summary_row.get('max_best_match_ratio'))} | "
            f"{_safe_str(summary_row.get('caveat_note'))} |"
        )
    lines.append("")

    for summary_row in sorted(instance_summary_rows, key=_summary_sort_key):
        fixture_seed = _safe_int(summary_row.get("fixture_seed"))
        lines.append(f"## Seed {fixture_seed}")
        lines.append("")
        lines.append(f"- Role: `{_safe_str(summary_row.get('benchmark_case_role'))}`")
        lines.append(f"- Caveat: {_safe_str(summary_row.get('caveat_note'))}")
        lines.append(
            f"- Range: max `{_ratio_text(summary_row.get('max_best_match_ratio'))}` "
            f"at `search{_safe_int(summary_row.get('max_best_match_search_seed'))}`"
        )
        lines.append("")
        lines.append("| search seed | status | best match | best stage | stage35 selected | archive seed rows | best stage35 seed rows | space-map stage35 rows | focus family | dominant family | caveats |")
        lines.append("| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- | --- | --- |")
        for row in rows_by_seed[fixture_seed]:
            lines.append(
                f"| {_safe_int(row.get('search_seed'))} | "
                f"{_safe_str(row.get('status'))} | "
                f"{_ratio_text(row.get('best_match_ratio'))} | "
                f"{_safe_str(row.get('best_stage'))} | "
                f"{_safe_int(row.get('stage35_selected'))} | "
                f"{_safe_int(row.get('archive_seed_row_count'))} | "
                f"{_safe_int(row.get('best_stage35_seed_row_count'))} | "
                f"{_safe_int(row.get('space_map_stage35_row_count'))} | "
                f"{_safe_str(row.get('focus_stage35_family_id')) or 'na'} | "
                f"{_safe_str(row.get('dominant_stage35_family_id')) or 'na'} | "
                f"{'; '.join(_safe_str(flag) for flag in row.get('caveat_flags') or []) or 'na'} |"
            )
        lines.append("")

    (output_dir / "fixed_instance_solver_baseline_cases.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _load_1111_followup_finish_by_run_key() -> dict[tuple[int, int], dict[str, Any]]:
    followup_by_run_key: dict[tuple[int, int], dict[str, Any]] = {}
    for search_seed in SEARCH_SEED_ORDER:
        progress_path = (
            SUPPLEMENT_1111_RAW_STAGE35_DIR
            / f"seed1111_search{search_seed}"
            / "stage35_progress.jsonl"
        )
        if not progress_path.exists():
            raise FileNotFoundError(f"Missing 1111 stage35 progress artifact: {progress_path}")
        finish_event: dict[str, Any] | None = None
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = dict(json.loads(line))
            if payload.get("event") == "followup_finish":
                finish_event = payload
        if finish_event is None:
            raise ValueError(
                "Could not locate followup_finish event in 1111 stage35 progress artifact: "
                f"{progress_path}"
            )
        followup_by_run_key[(1111, search_seed)] = finish_event
    return followup_by_run_key


def _build_1111_key_stage35_notes(row: Mapping[str, Any]) -> str:
    fragments: list[str] = [
        f"baseline {row.get('baseline_candidate_source') or 'na'}/{row.get('baseline_candidate_lane') or 'na'}",
    ]
    distinct_family_count = _safe_int(row.get("distinct_stage35_family_count"))
    if distinct_family_count <= 1:
        fragments.append("single-family mapped stage35 region")
    else:
        fragments.append(
            f"{distinct_family_count} mapped stage35 families ({row.get('stage35_family_counts') or 'na'})"
        )

    focus_family_id = _safe_str(row.get("focus_family_id"))
    dominant_family_id = _safe_str(row.get("dominant_mapped_stage35_family_id"))
    final_best_family_id = _safe_str(row.get("final_best_stage35_seed_family_id"))
    max_family_id = _safe_str(row.get("max_mapped_family_by_final_match_id"))

    if focus_family_id and dominant_family_id and focus_family_id != dominant_family_id:
        fragments.append("mapped late rows dominated away from focus family")
    if focus_family_id and final_best_family_id and focus_family_id != final_best_family_id:
        fragments.append("final-best stage35 seed family diverges from focus family")
    if max_family_id and max_family_id != focus_family_id:
        fragments.append(f"max mapped final-match family is {max_family_id}")
    if _safe_str(row.get("status")) == "stalled":
        fragments.append("run stalled after stage35 admission")
    return "; ".join(fragments)


def build_1111_conversion_compare_rows(
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    focus_1111_run_summary_rows: Sequence[Mapping[str, Any]],
    focus_1111_all_family_summary_rows: Sequence[Mapping[str, Any]],
    stage35_join_rows: Sequence[Mapping[str, Any]],
    followup_finish_by_run_key: Mapping[tuple[int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in baseline_rows
        if _safe_int(row.get("fixture_seed")) == 1111
    }
    focus_run_by_run_key = {
        (1111, _safe_int(row.get("search_seed"))): dict(row)
        for row in focus_1111_run_summary_rows
    }
    family_rows_by_run_key: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in focus_1111_all_family_summary_rows:
        family_rows_by_run_key[(1111, _safe_int(row.get("search_seed")))].append(dict(row))

    final_best_seed_family_by_run_key: dict[tuple[int, int], dict[str, Any]] = {}
    for row in stage35_join_rows:
        run_key = _run_key(
            fixture_seed=row.get("fixture_seed", 1111),
            search_seed=row.get("search_seed"),
        )
        if run_key[0] != 1111:
            continue
        if (
            _safe_str(row.get("best_seed_source")) == "final_best"
            and _safe_str(row.get("best_space_candidate_hash_match")) == "True"
        ):
            if run_key in final_best_seed_family_by_run_key:
                raise ValueError(f"Duplicate final_best family join rows for run_key={run_key}")
            final_best_seed_family_by_run_key[run_key] = dict(row)

    expected_run_keys = {(1111, search_seed) for search_seed in SEARCH_SEED_ORDER}
    for label, mapping in (
        ("baseline", baseline_by_run_key),
        ("focus_run_summary", focus_run_by_run_key),
        ("followup_finish", followup_finish_by_run_key),
        ("final_best_family_join", final_best_seed_family_by_run_key),
    ):
        if set(mapping) != expected_run_keys:
            raise ValueError(
                f"1111 compare coverage mismatch for {label}: "
                f"expected={sorted(expected_run_keys)} actual={sorted(mapping)}"
            )
    if set(family_rows_by_run_key) != expected_run_keys:
        raise ValueError(
            "1111 compare coverage mismatch for all-family summary: "
            f"expected={sorted(expected_run_keys)} actual={sorted(family_rows_by_run_key)}"
        )

    compare_rows: list[dict[str, Any]] = []
    for search_seed in SEARCH_SEED_ORDER:
        run_key = (1111, search_seed)
        baseline_row = dict(baseline_by_run_key[run_key])
        focus_run_row = dict(focus_run_by_run_key[run_key])
        followup_row = dict(followup_finish_by_run_key[run_key])
        final_best_seed_family_row = dict(final_best_seed_family_by_run_key[run_key])
        family_rows = list(family_rows_by_run_key[run_key])

        finite_family_rows = [
            row for row in family_rows if _is_finite(row.get("max_final_match"))
        ]
        if not finite_family_rows:
            raise ValueError(f"No finite-family summary rows for run_key={run_key}")
        max_final_match_family_row = max(
            finite_family_rows,
            key=lambda row: (
                _safe_float(row.get("max_final_match")),
                _safe_int(row.get("stage35_row_count")),
                _safe_int(row.get("row_count")),
                _safe_str(row.get("family_id")),
            ),
        )

        focus_family_id = _safe_str(focus_run_row.get("focus_family_id"))
        dominant_family_id = _safe_str(baseline_row.get("dominant_stage35_family_id"))
        final_best_family_id = _safe_str(final_best_seed_family_row.get("space_family_id"))
        alignment_label = _family_alignment_label(
            focus_family_id=focus_family_id,
            dominant_family_id=dominant_family_id,
            final_best_family_id=final_best_family_id,
        )

        compare_row: dict[str, Any] = {
            "comparison_group": (
                "core_comparison" if search_seed in {7002, 7003, 7005} else "contrast_case"
            ),
            "panel_job_index": _safe_int(baseline_row.get("panel_job_index")),
            "fixture_seed": 1111,
            "search_seed": search_seed,
            "status": _safe_str(baseline_row.get("status")),
            "best_stage": _safe_str(baseline_row.get("best_stage")),
            "best_match_ratio": _safe_float(baseline_row.get("best_match_ratio")),
            "archive_seed_row_count": _safe_int(baseline_row.get("archive_seed_row_count")),
            "best_stage35_seed_row_count": _safe_int(
                baseline_row.get("best_stage35_seed_row_count")
            ),
            "space_map_stage35_row_count": _safe_int(
                baseline_row.get("space_map_stage35_row_count")
            ),
            "joined_row_count": _safe_int(baseline_row.get("joined_row_count")),
            "distinct_stage35_family_count": _safe_int(
                baseline_row.get("distinct_stage35_family_count")
            ),
            "stage35_family_counts": _safe_str(baseline_row.get("stage35_family_counts")),
            "focus_family_definition": "top_stage35_admitted_row_family",
            "focus_family_id": focus_family_id,
            "dominant_mapped_stage35_family_id": dominant_family_id,
            "dominant_mapped_stage35_family_share": _safe_optional_float(
                baseline_row.get("dominant_stage35_family_share")
            ),
            "final_best_family_definition": (
                "joined_stage35_seed_row_with_best_seed_source_final_best"
            ),
            "final_best_stage35_seed_family_id": final_best_family_id,
            "final_best_stage35_seed_lane": _safe_str(final_best_seed_family_row.get("best_lane")),
            "final_best_stage35_seed_source": _safe_str(
                final_best_seed_family_row.get("best_stage3_source")
            ),
            "final_best_stage35_seed_selection_rank": _safe_int(
                final_best_seed_family_row.get("space_selection_rank")
            ),
            "max_mapped_family_by_final_match_id": _safe_str(
                max_final_match_family_row.get("family_id")
            ),
            "max_mapped_family_by_final_match": _safe_float(
                max_final_match_family_row.get("max_final_match")
            ),
            "max_mapped_family_stage35_row_count": _safe_int(
                max_final_match_family_row.get("stage35_row_count")
            ),
            "max_mapped_family_row_count": _safe_int(max_final_match_family_row.get("row_count")),
            "max_mapped_family_selected_row_count": _safe_int(
                max_final_match_family_row.get("selected_row_count")
            ),
            "max_mapped_family_admitted_row_count": _safe_int(
                max_final_match_family_row.get("admitted_row_count")
            ),
            "focus_family_total_rows": _safe_int(focus_run_row.get("focus_family_total_rows")),
            "focus_family_stage35_rows": _safe_int(
                focus_run_row.get("focus_family_stage35_rows")
            ),
            "focus_family_selected_rows": _safe_int(
                focus_run_row.get("focus_family_selected_rows")
            ),
            "focus_family_admitted_rows": _safe_int(
                focus_run_row.get("focus_family_admitted_rows")
            ),
            "focus_family_max_final_score": _safe_optional_float(
                focus_run_row.get("focus_family_max_final_score")
            ),
            "focus_family_max_final_match": _safe_optional_float(
                focus_run_row.get("focus_family_max_final_match")
            ),
            "baseline_candidate_source": _safe_str(
                followup_row.get("baseline_candidate_source")
            ),
            "baseline_candidate_lane": _safe_str(followup_row.get("baseline_candidate_lane")),
            "baseline_selector": _safe_str(followup_row.get("baseline_selector")),
            "followup_accept_reason": _safe_str(followup_row.get("accept_reason")),
            "followup_accept_passed": _safe_int(followup_row.get("accept_passed")),
            "followup_archive_count_raw": _safe_int(followup_row.get("archive_count")),
            "followup_rounds_completed": _safe_int(followup_row.get("rounds_completed")),
            "followup_runtime_seconds": _safe_float(followup_row.get("runtime_seconds")),
            "word_ngram_judge_active": _safe_int(baseline_row.get("word_ngram_judge_active")),
            "word_ngram_judge_report_xent": _safe_float(
                baseline_row.get("word_ngram_judge_report_xent")
            ),
            "word_ngram_judge_trust_score": _safe_float(
                baseline_row.get("word_ngram_judge_trust_score")
            ),
            "word_ngram_judge_trust_tier": _safe_str(
                baseline_row.get("word_ngram_judge_trust_tier")
            ),
            "word_ngram_judge_n_positions": _safe_int(
                baseline_row.get("word_ngram_judge_n_positions")
            ),
            "focus_family_matches_dominant_mapped_family": int(
                focus_family_id == dominant_family_id
            ),
            "focus_family_matches_final_best_family": int(
                focus_family_id == final_best_family_id
            ),
            "dominant_mapped_family_matches_final_best_family": int(
                dominant_family_id == final_best_family_id
            ),
            "family_alignment_label": alignment_label,
        }
        compare_row["key_stage35_notes"] = _build_1111_key_stage35_notes(compare_row)
        compare_rows.append(compare_row)

    compare_rows.sort(
        key=lambda row: (
            _search_seed_order(_safe_int(row.get("search_seed"))),
            _safe_int(row.get("panel_job_index")),
        )
    )
    return compare_rows


def write_1111_conversion_failure_audit_markdown(
    output_dir: Path,
    *,
    compare_rows: Sequence[Mapping[str, Any]],
) -> None:
    rows_by_seed = {
        _safe_int(row.get("search_seed")): dict(row) for row in compare_rows
    }
    strongest_row = rows_by_seed[7002]
    weak_alignment_rows = [rows_by_seed[7003], rows_by_seed[7005]]
    contrast_rows = [rows_by_seed[7001], rows_by_seed[7004]]

    lines: list[str] = [
        "# 1111 Conversion Failure Audit",
        "",
        "Question:",
        "- why does `1111/7002` look like the cleanest `f0` case while `7003` and `7005` stay weaker, and what do `7001` and `7004` add as contrast cases?",
        "",
        "Locked definitions:",
        "- `focus family = family of the top stage35-admitted row in that run`",
        "- `final-best family = family of the joined stage35 seed row with best_seed_source = final_best`",
        "- keep focus family, dominant mapped stage35 family, and final-best family separate",
        "",
        "Top read:",
        f"- all five `1111` runs admitted stage35, used baseline selector `{_safe_str(strongest_row.get('baseline_selector'))}`, and completed one follow-up round",
        f"- `7002` is the only fully aligned case: focus, dominant mapped, and final-best family all stay `{_safe_str(strongest_row.get('focus_family_id'))}`, with single-family mapped stage35 rows and focus-family max final match `{_ratio_text(strongest_row.get('focus_family_max_final_match'))}`",
        f"- `7001` keeps focus/final-best on `f0`, but the mapped stage35 rows are dominated by `{_safe_str(rows_by_seed[7001].get('dominant_mapped_stage35_family_id'))}`",
        f"- `7004` keeps focus/final-best on `f0`, but the mapped stage35 region fragments across `{_safe_str(rows_by_seed[7004].get('stage35_family_counts'))}` and is dominated by `{_safe_str(rows_by_seed[7004].get('dominant_mapped_stage35_family_id'))}`",
        f"- `7003` and `7005` keep mapped stage35 dominance on `f0`, but the final-best family flips to `{_safe_str(rows_by_seed[7003].get('final_best_stage35_seed_family_id'))}`",
        f"- `7003` is the sharpest weak case: stalled, focus-family max final match only `{_ratio_text(rows_by_seed[7003].get('focus_family_max_final_match'))}`, and the highest mapped family by final-match is off-focus `{_safe_str(rows_by_seed[7003].get('max_mapped_family_by_final_match_id'))}`",
        "",
        "Working diagnosis:",
        "- best current read: `1111` is not failing as one simple same-family weakness. The strongest route is the aligned `f0` case in `7002`; weaker outcomes appear when the mapped late region becomes rival-dominant (`7001`, `7004`) or when the final-best stage35 seed route escapes the otherwise `f0`-centred mapped region (`7003`, `7005`).",
        "",
        "| search seed | status | best match | focus family | dominant mapped family | final-best family | max mapped family by final match | baseline source | baseline lane | focus mapped stage35 rows | focus max final match | alignment | notes |",
        "| --- | --- | ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for search_seed in SEARCH_SEED_ORDER:
        row = rows_by_seed[search_seed]
        lines.append(
            f"| {search_seed} | "
            f"{_safe_str(row.get('status'))} | "
            f"{_ratio_text(row.get('best_match_ratio'))} | "
            f"{_safe_str(row.get('focus_family_id')) or 'na'} | "
            f"{_safe_str(row.get('dominant_mapped_stage35_family_id')) or 'na'} | "
            f"{_safe_str(row.get('final_best_stage35_seed_family_id')) or 'na'} | "
            f"{_safe_str(row.get('max_mapped_family_by_final_match_id')) or 'na'} | "
            f"{_safe_str(row.get('baseline_candidate_source')) or 'na'} | "
            f"{_safe_str(row.get('baseline_candidate_lane')) or 'na'} | "
            f"{_safe_int(row.get('focus_family_stage35_rows'))} | "
            f"{_ratio_text(row.get('focus_family_max_final_match'))} | "
            f"{_safe_str(row.get('family_alignment_label'))} | "
            f"{_safe_str(row.get('key_stage35_notes'))} |"
        )
    lines.extend(
        [
            "",
            "Core comparison set:",
            f"- `7002`: aligned `f0` route, best match `{_ratio_text(strongest_row.get('best_match_ratio'))}`, baseline `{_safe_str(strongest_row.get('baseline_candidate_source'))}/{_safe_str(strongest_row.get('baseline_candidate_lane'))}`",
        ]
    )
    for row in weak_alignment_rows:
        lines.append(
            f"- `search{_safe_int(row.get('search_seed'))}`: mapped `f0` still leads, but final-best family is `{_safe_str(row.get('final_best_stage35_seed_family_id'))}` and the outcome stays at `{_ratio_text(row.get('best_match_ratio'))}`"
        )
    lines.append("")
    lines.append("Contrast cases:")
    for row in contrast_rows:
        lines.append(
            f"- `search{_safe_int(row.get('search_seed'))}`: {_safe_str(row.get('key_stage35_notes'))}"
        )

    (output_dir / "1111_conversion_failure_audit.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _mapped_family_shape_label(
    *,
    family_summary_available: int,
    distinct_stage35_family_count: int,
    dominant_stage35_family_share: float | None,
) -> str:
    if not family_summary_available:
        return "no_family_mapped_stage35_rows"
    if distinct_stage35_family_count <= 1:
        return "single_family"
    if dominant_stage35_family_share is not None and dominant_stage35_family_share >= 0.8:
        return "dominant_family_with_minor_tail"
    return "fragmented"


def _load_seed_followup_finish_by_run_key(
    *,
    fixture_seed: int,
    raw_stage35_dir: Path,
) -> dict[tuple[int, int], dict[str, Any]]:
    followup_by_run_key: dict[tuple[int, int], dict[str, Any]] = {}
    for search_seed in SEARCH_SEED_ORDER:
        progress_path = raw_stage35_dir / f"search{search_seed}" / "stage35_progress.jsonl"
        if not progress_path.exists():
            continue
        finish_event: dict[str, Any] | None = None
        for line in progress_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = dict(json.loads(line))
            if payload.get("event") == "followup_finish":
                finish_event = payload
        if finish_event is None:
            raise ValueError(
                "Could not locate followup_finish event in stage35 progress artifact: "
                f"{progress_path}"
            )
        followup_by_run_key[(fixture_seed, search_seed)] = finish_event
    return followup_by_run_key


def _build_1511_positive_control_note(row: Mapping[str, Any]) -> str:
    if _safe_int(row.get("solved_run_stage3_caveat")) == 1:
        return (
            "solved stage3 run; archive-side stage35 rows exist but family-mapped "
            "stage35 rows are absent"
        )

    fragments = [
        f"baseline {row.get('baseline_candidate_source') or 'na'}/{row.get('baseline_candidate_lane') or 'na'}",
    ]
    shape_label = _safe_str(row.get("mapped_family_shape_label"))
    if shape_label == "single_family":
        fragments.append(
            f"family-mapped stage35 rows stay tight on {row.get('dominant_mapped_stage35_family_id') or 'na'}"
        )
    elif shape_label == "dominant_family_with_minor_tail":
        fragments.append(
            f"mapped family region stays {row.get('dominant_mapped_stage35_family_id') or 'na'}-dominant with a small tail ({row.get('stage35_family_counts') or 'na'})"
        )
    else:
        fragments.append(
            f"mapped family region is {shape_label} ({row.get('stage35_family_counts') or 'na'})"
        )
    if _safe_str(row.get("followup_accept_reason")):
        fragments.append(f"followup {row.get('followup_accept_reason')}")
    return "; ".join(fragments)


def build_1511_positive_control_compare_rows(
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    seed1511_join_rows: Sequence[Mapping[str, Any]],
    followup_finish_by_run_key: Mapping[tuple[int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in baseline_rows
        if _safe_int(row.get("fixture_seed")) == 1511
    }
    final_best_family_by_run_key: dict[tuple[int, int], dict[str, Any]] = {}
    family_counts_by_run_key: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)

    for row in seed1511_join_rows:
        run_key = (1511, _safe_int(row.get("search_seed")))
        family_id = _safe_str(row.get("family_id"))
        if family_id:
            family_counts_by_run_key[run_key][family_id] += 1
        if _safe_str(row.get("join_seed_source")) == "final_best":
            if run_key in final_best_family_by_run_key:
                raise ValueError(f"Duplicate 1511 final_best rows for run_key={run_key}")
            final_best_family_by_run_key[run_key] = dict(row)

    expected_run_keys = {(1511, search_seed) for search_seed in SEARCH_SEED_ORDER}
    if set(baseline_by_run_key) != expected_run_keys:
        raise ValueError(
            "1511 compare coverage mismatch for baseline rows: "
            f"expected={sorted(expected_run_keys)} actual={sorted(baseline_by_run_key)}"
        )
    if set(final_best_family_by_run_key) != expected_run_keys:
        raise ValueError(
            "1511 compare coverage mismatch for final_best family rows: "
            f"expected={sorted(expected_run_keys)} actual={sorted(final_best_family_by_run_key)}"
        )

    compare_rows: list[dict[str, Any]] = []
    for search_seed in SEARCH_SEED_ORDER:
        run_key = (1511, search_seed)
        baseline_row = dict(baseline_by_run_key[run_key])
        final_best_family_row = dict(final_best_family_by_run_key[run_key])
        followup_row = dict(followup_finish_by_run_key.get(run_key, {}))
        family_summary_available = _safe_int(baseline_row.get("family_summary_available"))
        dominant_family_share = _safe_optional_float(
            baseline_row.get("dominant_stage35_family_share")
        )
        compare_row: dict[str, Any] = {
            "comparison_group": (
                "core_comparison" if search_seed in {7001, 7002, 7003, 7005} else "contrast_case"
            ),
            "panel_job_index": _safe_int(baseline_row.get("panel_job_index")),
            "fixture_seed": 1511,
            "search_seed": search_seed,
            "status": _safe_str(baseline_row.get("status")),
            "best_stage": _safe_str(baseline_row.get("best_stage")),
            "best_match_ratio": _safe_float(baseline_row.get("best_match_ratio")),
            "stage35_selected": _safe_int(baseline_row.get("stage35_selected")),
            "archive_seed_row_count": _safe_int(baseline_row.get("archive_seed_row_count")),
            "best_stage35_seed_row_count": _safe_int(
                baseline_row.get("best_stage35_seed_row_count")
            ),
            "space_map_stage35_row_count": _safe_int(
                baseline_row.get("space_map_stage35_row_count")
            ),
            "joined_row_count": _safe_int(baseline_row.get("joined_row_count")),
            "family_summary_available": family_summary_available,
            "distinct_stage35_family_count": _safe_int(
                baseline_row.get("distinct_stage35_family_count")
            ),
            "stage35_family_counts": _safe_str(baseline_row.get("stage35_family_counts")),
            "focus_family_id": _safe_str(baseline_row.get("focus_stage35_family_id")),
            "dominant_mapped_stage35_family_id": _safe_str(
                baseline_row.get("dominant_stage35_family_id")
            ),
            "dominant_mapped_stage35_family_share": dominant_family_share,
            "final_best_family_definition": (
                "joined_stage35_seed_row_with_join_seed_source_final_best"
            ),
            "final_best_stage35_seed_family_id": _safe_str(
                final_best_family_row.get("family_id")
            ),
            "final_best_stage35_seed_source": _safe_str(
                final_best_family_row.get("join_stage3_source")
            ),
            "final_best_stage35_seed_selection_rank": _safe_int(
                final_best_family_row.get("selection_rank")
            ),
            "mapped_family_shape_label": _mapped_family_shape_label(
                family_summary_available=family_summary_available,
                distinct_stage35_family_count=_safe_int(
                    baseline_row.get("distinct_stage35_family_count")
                ),
                dominant_stage35_family_share=dominant_family_share,
            ),
            "followup_accept_reason": _safe_str(followup_row.get("accept_reason")),
            "followup_accept_passed": _safe_int(followup_row.get("accept_passed")),
            "followup_archive_count_raw": _safe_int(followup_row.get("archive_count")),
            "followup_runtime_seconds": _safe_float(followup_row.get("runtime_seconds")),
            "baseline_candidate_source": _safe_str(
                followup_row.get("baseline_candidate_source")
            ),
            "baseline_candidate_lane": _safe_str(followup_row.get("baseline_candidate_lane")),
            "baseline_selector": _safe_str(followup_row.get("baseline_selector")),
            "word_ngram_judge_active": _safe_int(baseline_row.get("word_ngram_judge_active")),
            "word_ngram_judge_report_xent": _safe_float(
                baseline_row.get("word_ngram_judge_report_xent")
            ),
            "word_ngram_judge_trust_score": _safe_float(
                baseline_row.get("word_ngram_judge_trust_score")
            ),
            "word_ngram_judge_trust_tier": _safe_str(
                baseline_row.get("word_ngram_judge_trust_tier")
            ),
            "word_ngram_judge_n_positions": _safe_int(
                baseline_row.get("word_ngram_judge_n_positions")
            ),
            "mapped_family_counter_f0": family_counts_by_run_key[run_key].get("f0", 0),
            "mapped_family_counter_f1": family_counts_by_run_key[run_key].get("f1", 0),
            "solved_run_stage3_caveat": int(
                _safe_str(baseline_row.get("status")) == "solved"
                and _safe_int(baseline_row.get("archive_seed_row_count")) > 0
                and _safe_int(baseline_row.get("space_map_stage35_row_count")) == 0
            ),
        }
        compare_row["key_stage35_notes"] = _build_1511_positive_control_note(compare_row)
        compare_rows.append(compare_row)

    compare_rows.sort(key=lambda row: _search_seed_order(_safe_int(row.get("search_seed"))))
    return compare_rows


def write_1511_positive_control_audit_markdown(
    output_dir: Path,
    *,
    compare_rows: Sequence[Mapping[str, Any]],
) -> None:
    rows_by_seed = {
        _safe_int(row.get("search_seed")): dict(row) for row in compare_rows
    }
    lines: list[str] = [
        "# 1511 Positive-Control Audit",
        "",
        "Question:",
        "- what stays stable in the strong positive control, and how should the solved run be compared to the strongest non-solved routes?",
        "",
        "Top read:",
        "- `1511/7001` is the true solve, but it is not family-comparable in the same way as the non-solved runs because archive-side stage35 rows exist while family-mapped stage35 rows are absent",
        "- the strongest non-solved runs are `7002` and `7003`, both `stage35_substitution_only` and both single-family `f0` cases",
        "- `7004` is also a single-family `f0` case, but its follow-up rejects on `search_score_drop_guard_failed` and the run finishes back at `stage3_full_refine`",
        "- `7005` stays mostly tight on `f0` with only a small `f1` tail",
        "",
        "Working positive-control read:",
        "- best current read: `1511` is a genuinely solvable stage3 instance. When it does not solve, the late mapped region stays unusually tight around `f0`; the main weakness is not fragmentation, but conversion from an otherwise coherent route. The solved run still shows that the current positive result is a stage-3 solve, not a stage35 conversion.",
        "",
        "| search seed | status | best stage | best match | stage35 selected | focus family | dominant mapped family | final-best family | mapped family shape | trust score | followup accept reason | notes |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for search_seed in SEARCH_SEED_ORDER:
        row = rows_by_seed[search_seed]
        lines.append(
            f"| {search_seed} | "
            f"{_safe_str(row.get('status'))} | "
            f"{_safe_str(row.get('best_stage'))} | "
            f"{_ratio_text(row.get('best_match_ratio'))} | "
            f"{_safe_int(row.get('stage35_selected'))} | "
            f"{_safe_str(row.get('focus_family_id')) or 'na'} | "
            f"{_safe_str(row.get('dominant_mapped_stage35_family_id')) or 'na'} | "
            f"{_safe_str(row.get('final_best_stage35_seed_family_id')) or 'na'} | "
            f"{_safe_str(row.get('mapped_family_shape_label'))} | "
            f"{_ratio_text(row.get('word_ngram_judge_trust_score'))} | "
            f"{_safe_str(row.get('followup_accept_reason')) or 'na'} | "
            f"{_safe_str(row.get('key_stage35_notes'))} |"
        )
    lines.extend(
        [
            "",
            "Solved-run caveat:",
            "- `7001` keeps `archive_seed_row_count = 5`, `best_stage35_seed_row_count = 0`, and `space_map_stage35_row_count = 0`, so it remains a positive reference but not a family-comparable stage35 case.",
            "",
            "Non-solved comparison set:",
            "- `7002` and `7003` are the strongest non-solved references: both accept from `phaseB_topk/challenger`, both map entirely to `f0`, and both stay above `0.82` best match.",
            "- `7004` shows that family tightness alone does not guarantee success: it stays single-family `f0` but rejects on `search_score_drop_guard_failed` and falls back to stage 3.",
            "- `7005` stays mostly coherent on `f0`, but the small `f1` tail coincides with a materially weaker result than `7002` and `7003`.",
        ]
    )

    (output_dir / "1511_positive_control_audit.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _build_611_middle_case_note(row: Mapping[str, Any]) -> str:
    fragments = [
        f"baseline {row.get('baseline_candidate_source') or 'na'}/{row.get('baseline_candidate_lane') or 'na'}",
    ]
    shape_label = _safe_str(row.get("mapped_family_shape_label"))
    if shape_label == "single_family":
        fragments.append(
            f"family-mapped stage35 rows stay tight on {row.get('dominant_mapped_stage35_family_id') or 'na'}"
        )
    elif shape_label == "dominant_family_with_minor_tail":
        fragments.append(
            f"mapped family region stays {row.get('dominant_mapped_stage35_family_id') or 'na'}-dominant with a small tail ({row.get('stage35_family_counts') or 'na'})"
        )
    else:
        fragments.append(
            f"mapped family region is {shape_label} ({row.get('stage35_family_counts') or 'na'})"
        )
    if _safe_str(row.get("followup_accept_reason")):
        fragments.append(f"followup {row.get('followup_accept_reason')}")
    if _safe_int(row.get("stage35_selected")) == 0:
        fragments.append("run finishes back at stage 3")
    return "; ".join(fragments)


def build_611_middle_case_compare_rows(
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    seed611_join_rows: Sequence[Mapping[str, Any]],
    followup_finish_by_run_key: Mapping[tuple[int, int], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in baseline_rows
        if _safe_int(row.get("fixture_seed")) == 611
    }
    final_best_family_by_run_key: dict[tuple[int, int], dict[str, Any]] = {}
    family_counts_by_run_key: dict[tuple[int, int], Counter[str]] = defaultdict(Counter)

    for row in seed611_join_rows:
        run_key = (611, _safe_int(row.get("search_seed")))
        family_id = _safe_str(row.get("family_id"))
        if family_id:
            family_counts_by_run_key[run_key][family_id] += 1
        if _safe_str(row.get("join_seed_source")) == "final_best":
            if run_key in final_best_family_by_run_key:
                raise ValueError(f"Duplicate 611 final_best rows for run_key={run_key}")
            final_best_family_by_run_key[run_key] = dict(row)

    expected_run_keys = {(611, search_seed) for search_seed in SEARCH_SEED_ORDER}
    if set(baseline_by_run_key) != expected_run_keys:
        raise ValueError(
            "611 compare coverage mismatch for baseline rows: "
            f"expected={sorted(expected_run_keys)} actual={sorted(baseline_by_run_key)}"
        )
    if set(final_best_family_by_run_key) != expected_run_keys:
        raise ValueError(
            "611 compare coverage mismatch for final_best family rows: "
            f"expected={sorted(expected_run_keys)} actual={sorted(final_best_family_by_run_key)}"
        )

    compare_rows: list[dict[str, Any]] = []
    for search_seed in SEARCH_SEED_ORDER:
        run_key = (611, search_seed)
        baseline_row = dict(baseline_by_run_key[run_key])
        final_best_family_row = dict(final_best_family_by_run_key[run_key])
        followup_row = dict(followup_finish_by_run_key.get(run_key, {}))
        family_summary_available = _safe_int(baseline_row.get("family_summary_available"))
        dominant_family_share = _safe_optional_float(
            baseline_row.get("dominant_stage35_family_share")
        )
        compare_row: dict[str, Any] = {
            "comparison_group": (
                "core_comparison" if search_seed in {7004, 7005} else "supporting_case"
            ),
            "panel_job_index": _safe_int(baseline_row.get("panel_job_index")),
            "fixture_seed": 611,
            "search_seed": search_seed,
            "status": _safe_str(baseline_row.get("status")),
            "best_stage": _safe_str(baseline_row.get("best_stage")),
            "best_match_ratio": _safe_float(baseline_row.get("best_match_ratio")),
            "stage35_selected": _safe_int(baseline_row.get("stage35_selected")),
            "archive_seed_row_count": _safe_int(baseline_row.get("archive_seed_row_count")),
            "best_stage35_seed_row_count": _safe_int(
                baseline_row.get("best_stage35_seed_row_count")
            ),
            "space_map_stage35_row_count": _safe_int(
                baseline_row.get("space_map_stage35_row_count")
            ),
            "joined_row_count": _safe_int(baseline_row.get("joined_row_count")),
            "family_summary_available": family_summary_available,
            "distinct_stage35_family_count": _safe_int(
                baseline_row.get("distinct_stage35_family_count")
            ),
            "stage35_family_counts": _safe_str(baseline_row.get("stage35_family_counts")),
            "focus_family_id": _safe_str(baseline_row.get("focus_stage35_family_id")),
            "dominant_mapped_stage35_family_id": _safe_str(
                baseline_row.get("dominant_stage35_family_id")
            ),
            "dominant_mapped_stage35_family_share": dominant_family_share,
            "final_best_family_definition": (
                "joined_stage35_seed_row_with_join_seed_source_final_best"
            ),
            "final_best_stage35_seed_family_id": _safe_str(
                final_best_family_row.get("family_id")
            ),
            "final_best_stage35_seed_source": _safe_str(
                final_best_family_row.get("join_stage3_source")
            ),
            "final_best_stage35_seed_selection_rank": _safe_int(
                final_best_family_row.get("selection_rank")
            ),
            "mapped_family_shape_label": _mapped_family_shape_label(
                family_summary_available=family_summary_available,
                distinct_stage35_family_count=_safe_int(
                    baseline_row.get("distinct_stage35_family_count")
                ),
                dominant_stage35_family_share=dominant_family_share,
            ),
            "followup_accept_reason": _safe_str(followup_row.get("accept_reason")),
            "followup_accept_passed": _safe_int(followup_row.get("accept_passed")),
            "followup_archive_count_raw": _safe_int(followup_row.get("archive_count")),
            "followup_runtime_seconds": _safe_float(followup_row.get("runtime_seconds")),
            "baseline_candidate_source": _safe_str(
                followup_row.get("baseline_candidate_source")
            ),
            "baseline_candidate_lane": _safe_str(followup_row.get("baseline_candidate_lane")),
            "baseline_selector": _safe_str(followup_row.get("baseline_selector")),
            "word_ngram_judge_active": _safe_int(baseline_row.get("word_ngram_judge_active")),
            "word_ngram_judge_report_xent": _safe_float(
                baseline_row.get("word_ngram_judge_report_xent")
            ),
            "word_ngram_judge_trust_score": _safe_float(
                baseline_row.get("word_ngram_judge_trust_score")
            ),
            "word_ngram_judge_trust_tier": _safe_str(
                baseline_row.get("word_ngram_judge_trust_tier")
            ),
            "word_ngram_judge_n_positions": _safe_int(
                baseline_row.get("word_ngram_judge_n_positions")
            ),
            "mapped_family_counter_f0": family_counts_by_run_key[run_key].get("f0", 0),
            "mapped_family_counter_f1": family_counts_by_run_key[run_key].get("f1", 0),
        }
        compare_row["key_stage35_notes"] = _build_611_middle_case_note(compare_row)
        compare_rows.append(compare_row)

    compare_rows.sort(key=lambda row: _search_seed_order(_safe_int(row.get("search_seed"))))
    return compare_rows


def write_611_middle_case_audit_markdown(
    output_dir: Path,
    *,
    compare_rows: Sequence[Mapping[str, Any]],
) -> None:
    rows_by_seed = {
        _safe_int(row.get("search_seed")): dict(row) for row in compare_rows
    }
    lines: list[str] = [
        "# 611 Middle-Case Audit",
        "",
        "Question:",
        "- why does `611/7004` get materially further than the other runs, and what kind of solver weakness does `611` best expose?",
        "",
        "Top read:",
        "- `611/7004` is the clearest middle-case reference: it reaches `0.762`, accepts from `phaseB_topk/challenger`, and the mapped late region is a single-family `f0` block.",
        "- `611/7005` reaches the same single-family `f0` late region, but it rejects on `search_score_drop_guard_failed` and finishes back at `stage3_full_refine` with a weaker `0.585` result.",
        "- `7001` and `7002` are shallower mixed `f0/f1` cases with only two mapped rows each.",
        "- `7003` reaches a larger mapped region, but it is mostly `f1` rather than `f0` and still does not convert.",
        "",
        "Working middle-case read:",
        "- best current read: `611` is not dead and not heavily fragmented. The stronger late route exists and can stay very tight on `f0`, but the pipeline does not reach or retain that route reliably enough across seeds. The clearest comparison is `7004` versus `7005`: same tight family shape, very different acceptance and final quality.",
        "",
        "| search seed | status | best stage | best match | stage35 selected | focus family | dominant mapped family | final-best family | mapped family shape | trust score | followup accept reason | notes |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for search_seed in SEARCH_SEED_ORDER:
        row = rows_by_seed[search_seed]
        lines.append(
            f"| {search_seed} | "
            f"{_safe_str(row.get('status'))} | "
            f"{_safe_str(row.get('best_stage'))} | "
            f"{_ratio_text(row.get('best_match_ratio'))} | "
            f"{_safe_int(row.get('stage35_selected'))} | "
            f"{_safe_str(row.get('focus_family_id')) or 'na'} | "
            f"{_safe_str(row.get('dominant_mapped_stage35_family_id')) or 'na'} | "
            f"{_safe_str(row.get('final_best_stage35_seed_family_id')) or 'na'} | "
            f"{_safe_str(row.get('mapped_family_shape_label'))} | "
            f"{_ratio_text(row.get('word_ngram_judge_trust_score'))} | "
            f"{_safe_str(row.get('followup_accept_reason')) or 'na'} | "
            f"{_safe_str(row.get('key_stage35_notes'))} |"
        )
    lines.extend(
        [
            "",
            "Key comparison:",
            "- `7004` and `7005` are the most useful pair: both map entirely to `f0`, both start from `phaseB_topk/challenger`, but only `7004` is accepted and only `7004` reaches the upper-band unsolved result.",
            "- `7003` shows a different failure shape: it has six mapped rows, but they are mostly `f1`, not the cleaner `f0` route seen in `7004` and `7005`.",
            "- `7001` and `7002` look more like incomplete arrival than conversion failure: they never build beyond the small mixed two-row family region.",
        ]
    )

    (output_dir / "611_middle_case_audit.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def write_1411_caveat_and_use_note(
    output_dir: Path,
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
) -> None:
    rows_1411 = [
        dict(row)
        for row in baseline_rows
        if _safe_int(row.get("fixture_seed")) == 1411
    ]
    rows_1411.sort(key=lambda row: _search_seed_order(_safe_int(row.get("search_seed"))))
    solved_row = next(row for row in rows_1411 if _safe_int(row.get("search_seed")) == 7003)

    lines = [
        "# 1411 Caveat And Use Note",
        "",
        "Use status:",
        "- `1411` remains in the benchmark as a useful, mixed solvable cross-check case.",
        "- It is not a clean first-line tuning target in v1.",
        "",
        "Why the caveat matters:",
        "- `1411/7003` is a true stage-3 solve.",
        f"- `1411/7003` keeps `archive_seed_row_count = {_safe_int(solved_row.get('archive_seed_row_count'))}`.",
        f"- `1411/7003` keeps `best_stage35_seed_row_count = {_safe_int(solved_row.get('best_stage35_seed_row_count'))}`.",
        f"- `1411/7003` keeps `space_map_stage35_row_count = {_safe_int(solved_row.get('space_map_stage35_row_count'))}`.",
        "- That means archive-side stage35 rows exist, but family-mapped stage35 rows are absent on the `best / space_map` side.",
        "",
        "How to use `1411` in this phase:",
        "- keep it as a context and cross-check case",
        "- use it to test whether the main story from `1511`, `611`, and `1111` still fits",
        "- do not treat it as an equal first-line tuning target while the solved-run family mapping remains incomplete",
        "",
        "Current per-seed read:",
    ]
    for row in rows_1411:
        lines.append(
            f"- `search{_safe_int(row.get('search_seed'))}`: "
            f"status `{_safe_str(row.get('status'))}`, "
            f"best stage `{_safe_str(row.get('best_stage'))}`, "
            f"best match `{_ratio_text(row.get('best_match_ratio'))}`, "
            f"focus family `{_safe_str(row.get('focus_stage35_family_id')) or 'na'}`, "
            f"dominant family `{_safe_str(row.get('dominant_stage35_family_id')) or 'na'}`"
        )

    (output_dir / "1411_caveat_and_use_note.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def write_candidate_solver_change_shortlist(
    output_dir: Path,
    *,
    compare_1111_rows: Sequence[Mapping[str, Any]],
    compare_1511_rows: Sequence[Mapping[str, Any]],
    compare_611_rows: Sequence[Mapping[str, Any]],
) -> None:
    row_1111_7002 = next(row for row in compare_1111_rows if _safe_int(row.get("search_seed")) == 7002)
    row_1111_7003 = next(row for row in compare_1111_rows if _safe_int(row.get("search_seed")) == 7003)
    row_611_7004 = next(row for row in compare_611_rows if _safe_int(row.get("search_seed")) == 7004)
    row_611_7005 = next(row for row in compare_611_rows if _safe_int(row.get("search_seed")) == 7005)
    row_1511_7002 = next(row for row in compare_1511_rows if _safe_int(row.get("search_seed")) == 7002)

    lines = [
        "# Candidate Solver Change Shortlist",
        "",
        "Rule:",
        "- these are narrow candidate areas only; they are not approved runtime changes yet",
        "",
        "Candidate 1 - continuation selection and acceptance around coherent late routes",
        "",
        "Why it follows from the audits:",
        f"- `611/7004` and `611/7005` both stay tight on `{_safe_str(row_611_7004.get('dominant_mapped_stage35_family_id'))}`, but only `7004` is accepted while `7005` fails on `{_safe_str(row_611_7005.get('followup_accept_reason'))}`",
        f"- `1111/7002` is the clean aligned case on `{_safe_str(row_1111_7002.get('focus_family_id'))}`, but `1111/7003` and `1111/7005` show weaker continuation even when mapped rows remain `{_safe_str(row_1111_7003.get('dominant_mapped_stage35_family_id'))}`-dominant",
        "",
        "Targets:",
        "- primary: `611` and `1111`",
        "- guardrail: do not harm the strong non-solved `1511` route shape",
        "",
        "What success would look like:",
        "- `611` keeps more of the `7004` behavior and less of the `7005` fallback shape",
        "- `1111` converts more of the clean `f0` route instead of stalling or flipping away late",
        "",
        "Risk:",
        "- over-favoring one continuation route could hurt useful diversity or damage the stronger `1511` reference pattern",
        "",
        "Candidate 2 - family-aware budget allocation once a coherent focal family appears",
        "",
        "Why it follows from the audits:",
        f"- `1511/7002` shows that a very tight `{_safe_str(row_1511_7002.get('dominant_mapped_stage35_family_id'))}`-only late region can support strong outcomes",
        f"- `1111` keeps a persistent focus family of `{_safe_str(row_1111_7002.get('focus_family_id'))}`, but surrounding family composition varies sharply by seed",
        "- `611` suggests that getting into the right coherent family region is not enough by itself, but it is still a prerequisite for the strongest middle-case behavior",
        "",
        "Targets:",
        "- primary: `1111`",
        "- secondary: `611`",
        "",
        "What success would look like:",
        "- more runs preserve or reinforce the cleaner focal-family route instead of drifting into rival-dominant or weak-tail shapes",
        "- the change improves `1111` or `611` without degrading `1511`",
        "",
        "Risk:",
        "- naive family-aware allocation could just overfit to the current panel or suppress alternative good paths",
    ]

    (output_dir / "candidate_solver_change_shortlist.md").write_text(
        "\n".join(lines).rstrip() + "\n",
        encoding="utf-8",
    )


def _load_best_instances_from_external_pack(
    panel_inventory_rows: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, int], dict[str, Any]]:
    best_instances: dict[tuple[int, int], dict[str, Any]] = {}
    for row in panel_inventory_rows:
        run_key = _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        )
        best_path = INPUT_EXTERNAL_REVIEW_PACK_DIR / _best_instance_rel_path(
            _safe_str(row.get("copied_report_dir"))
        )
        if not best_path.exists():
            raise FileNotFoundError(f"Missing copied best_instance.json: {best_path}")
        best_instances[run_key] = _read_json(best_path)
    return best_instances


def _validate_panel_shape(rows: Sequence[Mapping[str, Any]]) -> None:
    if len(rows) != 20:
        raise ValueError(f"Expected 20 fixed-panel rows, found {len(rows)}")
    seen_keys = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        )
        for row in rows
    }
    expected_keys = {
        (fixture_seed, search_seed)
        for fixture_seed in CASE_ROLE_BY_FIXTURE_SEED
        for search_seed in SEARCH_SEED_ORDER
    }
    if seen_keys != expected_keys:
        raise ValueError(
            "Fixed-panel run coverage mismatch: "
            f"missing={sorted(expected_keys - seen_keys)} "
            f"extra={sorted(seen_keys - expected_keys)}"
        )


def main() -> None:
    _require_input_paths(REQUIRED_INPUT_PATHS)
    panel_inventory_rows = _read_csv_rows(PANEL_INVENTORY_CSV)
    stage35_run_summary_rows = _read_csv_rows(STAGE35_RUN_SUMMARY_CSV)
    stage35_seed_summary_rows = _read_csv_rows(STAGE35_SEED_SUMMARY_CSV)
    focus_1111_run_summary_rows = _read_csv_rows(FOCUS_1111_RUN_SUMMARY_CSV)
    focus_1111_all_family_summary_rows = _read_csv_rows(
        FOCUS_1111_ALL_FAMILY_SUMMARY_CSV
    )
    supplement_1111_join_rows = _read_csv_rows(SUPPLEMENT_1111_ALL_JOIN_CSV)
    seed1511_join_rows = _read_csv_rows(SEED1511_ALL_JOIN_CSV)
    seed611_join_rows = _read_csv_rows(SEED611_ALL_JOIN_CSV)

    _require_csv_columns(
        path=PANEL_INVENTORY_CSV,
        rows=panel_inventory_rows,
        required_columns=REQUIRED_PANEL_INVENTORY_COLUMNS,
    )
    _require_csv_columns(
        path=STAGE35_RUN_SUMMARY_CSV,
        rows=stage35_run_summary_rows,
        required_columns=REQUIRED_STAGE35_RUN_SUMMARY_COLUMNS,
    )
    _require_csv_columns(
        path=STAGE35_SEED_SUMMARY_CSV,
        rows=stage35_seed_summary_rows,
        required_columns=REQUIRED_STAGE35_SEED_SUMMARY_COLUMNS,
    )
    _require_csv_columns(
        path=FOCUS_1111_RUN_SUMMARY_CSV,
        rows=focus_1111_run_summary_rows,
        required_columns=REQUIRED_1111_RUN_SUMMARY_COLUMNS,
    )
    _require_csv_columns(
        path=FOCUS_1111_ALL_FAMILY_SUMMARY_CSV,
        rows=focus_1111_all_family_summary_rows,
        required_columns=REQUIRED_1111_ALL_FAMILY_SUMMARY_COLUMNS,
    )
    _require_csv_columns(
        path=SUPPLEMENT_1111_ALL_JOIN_CSV,
        rows=supplement_1111_join_rows,
        required_columns=REQUIRED_SUPPLEMENT_1111_JOIN_COLUMNS,
    )
    _require_csv_columns(
        path=SEED1511_ALL_JOIN_CSV,
        rows=seed1511_join_rows,
        required_columns=REQUIRED_SEED_JOIN_COLUMNS,
    )
    _require_csv_columns(
        path=SEED611_ALL_JOIN_CSV,
        rows=seed611_join_rows,
        required_columns=REQUIRED_SEED_JOIN_COLUMNS,
    )

    _validate_panel_shape(panel_inventory_rows)
    _validate_panel_shape(stage35_run_summary_rows)
    _require_fixture_seed_coverage(
        path=STAGE35_SEED_SUMMARY_CSV,
        rows=stage35_seed_summary_rows,
        required_fixture_seeds=FIXTURE_SEED_ORDER,
    )
    _require_fixture_seed_coverage(
        path=FOCUS_1111_RUN_SUMMARY_CSV,
        rows=focus_1111_run_summary_rows,
        required_fixture_seeds=(1111,),
    )
    _require_search_seed_coverage(
        path=FOCUS_1111_RUN_SUMMARY_CSV,
        rows=focus_1111_run_summary_rows,
        required_search_seeds=SEARCH_SEED_ORDER,
    )
    _require_search_seed_coverage(
        path=FOCUS_1111_ALL_FAMILY_SUMMARY_CSV,
        rows=focus_1111_all_family_summary_rows,
        required_search_seeds=SEARCH_SEED_ORDER,
    )

    best_instances_by_run_key = _load_best_instances_from_external_pack(panel_inventory_rows)
    focus_1111_rows_by_run_key = {
        _run_key(
            fixture_seed=row.get("fixture_seed"),
            search_seed=row.get("search_seed"),
        ): dict(row)
        for row in focus_1111_run_summary_rows
    }
    followup_finish_by_run_key = _load_1111_followup_finish_by_run_key()
    followup_1511_by_run_key = _load_seed_followup_finish_by_run_key(
        fixture_seed=1511,
        raw_stage35_dir=SEED1511_RAW_STAGE35_DIR,
    )
    followup_611_by_run_key = _load_seed_followup_finish_by_run_key(
        fixture_seed=611,
        raw_stage35_dir=SEED611_RAW_STAGE35_DIR,
    )

    baseline_rows = build_panel_baseline_rows(
        panel_inventory_rows=panel_inventory_rows,
        stage35_run_summary_rows=stage35_run_summary_rows,
        best_instances_by_run_key=best_instances_by_run_key,
        focus_1111_rows_by_run_key=focus_1111_rows_by_run_key,
    )
    instance_summary_rows = build_instance_summary_rows(baseline_rows)
    validate_instance_summary_against_seed_summary(
        instance_summary_rows=instance_summary_rows,
        stage35_seed_summary_rows=stage35_seed_summary_rows,
    )
    instance_search_matrix_rows = build_instance_search_matrix_rows(baseline_rows)
    compare_1111_rows = build_1111_conversion_compare_rows(
        baseline_rows=baseline_rows,
        focus_1111_run_summary_rows=focus_1111_run_summary_rows,
        focus_1111_all_family_summary_rows=focus_1111_all_family_summary_rows,
        stage35_join_rows=supplement_1111_join_rows,
        followup_finish_by_run_key=followup_finish_by_run_key,
    )
    compare_1511_rows = build_1511_positive_control_compare_rows(
        baseline_rows=baseline_rows,
        seed1511_join_rows=seed1511_join_rows,
        followup_finish_by_run_key=followup_1511_by_run_key,
    )
    compare_611_rows = build_611_middle_case_compare_rows(
        baseline_rows=baseline_rows,
        seed611_join_rows=seed611_join_rows,
        followup_finish_by_run_key=followup_611_by_run_key,
    )

    output_dir = OUTPUT_BASE_DIR / (
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        "__fixed_instance_solver_development_v1"
    )
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / "panel_baseline_rows.jsonl", baseline_rows)
    _write_jsonl(output_dir / "instance_summary_rows.jsonl", instance_summary_rows)
    _write_csv(output_dir / "instance_search_matrix.csv", instance_search_matrix_rows)
    _write_csv(output_dir / "1111_conversion_compare_rows.csv", compare_1111_rows)
    _write_csv(output_dir / "1511_positive_control_compare_rows.csv", compare_1511_rows)
    _write_csv(output_dir / "611_middle_case_compare_rows.csv", compare_611_rows)
    write_baseline_cases_markdown(
        output_dir,
        baseline_rows=baseline_rows,
        instance_summary_rows=instance_summary_rows,
    )
    write_1111_conversion_failure_audit_markdown(
        output_dir,
        compare_rows=compare_1111_rows,
    )
    write_1511_positive_control_audit_markdown(
        output_dir,
        compare_rows=compare_1511_rows,
    )
    write_611_middle_case_audit_markdown(
        output_dir,
        compare_rows=compare_611_rows,
    )
    write_1411_caveat_and_use_note(
        output_dir,
        baseline_rows=baseline_rows,
    )
    write_candidate_solver_change_shortlist(
        output_dir,
        compare_1111_rows=compare_1111_rows,
        compare_1511_rows=compare_1511_rows,
        compare_611_rows=compare_611_rows,
    )
    print(
        "[fixed_instance_solver_development_v1] "
        f"runs={len(baseline_rows)} "
        f"instances={len(instance_summary_rows)} "
        f"1111_compare_rows={len(compare_1111_rows)} "
        f"1511_compare_rows={len(compare_1511_rows)} "
        f"611_compare_rows={len(compare_611_rows)} "
        f"output={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
