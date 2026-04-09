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
    raise RuntimeError("Could not locate repo root from extract_late_family_quality_v3.py")


REPO_ROOT = _find_repo_root()
INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v1/20260408T152322Z__late_family_quality_v1"
)
INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR = REPO_ROOT / Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "late_family_quality_v2/20260408T154637Z__late_family_quality_v2"
)
OUTPUT_BASE_DIR = (
    REPO_ROOT
    / "output"
    / "tools"
    / "benchmarks"
    / "periodic_sub_trans"
    / "no_wli"
    / "analysis"
    / "late_family_quality_v3"
)
REQUIRED_V1_INPUT_FILES = (
    "family_quality_rows.jsonl",
    "family_quality_case_digest.jsonl",
    "family_quality_summary.json",
)
REQUIRED_V2_INPUT_FILES = (
    "seed_agreement_rows.jsonl",
    "winner_pairwise_rows.jsonl",
    "agreement_summary.json",
)
LATE_FAMILY_QUALITY_V3_DISCRIMINATOR_SEEDS = (1111, 1311, 1411)
LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS = (411, 611, 1011)
LATE_FAMILY_QUALITY_V3_STUDY_SEEDS = (
    1111, 1311, 1411,
    411, 611, 1011,
)
ALTERNATIVE_WINNER_TYPES = ("trust", "archive", "full_uplift", "persistence")
WINNER_TYPES = ("truth",) + ALTERNATIVE_WINNER_TYPES
TRUTH_PAIR_ORDER = tuple(f"truth_vs_{winner_type}" for winner_type in ALTERNATIVE_WINNER_TYPES)
CLEAR_TRUTH_GAP = 0.10
CLEAR_PERSISTENCE_GAP = 1
BOUNDARY_ORDER = {
    "phaseC_start": 1,
    "stage35_seed": 2,
    "stage35_archive": 3,
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
    resolved: dict[str, Path] = {}
    missing = [name for name in required_names if not (bundle_dir / name).exists()]
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise FileNotFoundError(f"Missing required {label} files: {missing_list}")
    for name in required_names:
        resolved[name] = bundle_dir / name
    return resolved


def _read_family_quality_rows(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / "family_quality_rows.jsonl")


def _read_family_quality_case_digest(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / "family_quality_case_digest.jsonl")


def _read_seed_agreement_rows(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / "seed_agreement_rows.jsonl")


def _read_winner_pairwise_rows(bundle_dir: Path) -> list[dict[str, Any]]:
    return _read_jsonl(bundle_dir / "winner_pairwise_rows.jsonl")


def _seed_order(key_seed: int) -> int:
    try:
        return LATE_FAMILY_QUALITY_V3_STUDY_SEEDS.index(int(key_seed))
    except ValueError:
        return len(LATE_FAMILY_QUALITY_V3_STUDY_SEEDS)


def _select_study_seed_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    source_name: str,
) -> list[dict[str, Any]]:
    selected = [dict(row) for row in rows if _safe_int(row.get("key_seed")) in LATE_FAMILY_QUALITY_V3_STUDY_SEEDS]
    present = {_safe_int(row.get("key_seed")) for row in selected}
    missing = [seed for seed in LATE_FAMILY_QUALITY_V3_STUDY_SEEDS if seed not in present]
    if missing:
        raise ValueError(f"Missing v3 study seeds from {source_name}: {missing}")
    selected.sort(key=lambda row: (_seed_order(_safe_int(row.get("key_seed"))), _safe_str(row.get("family_id"))))
    return selected


def _index_rows_by_seed(rows: Sequence[Mapping[str, Any]], *, source_name: str) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        if key_seed in indexed:
            raise ValueError(f"Duplicate {source_name} row for seed {key_seed}")
        indexed[key_seed] = dict(row)
    missing = [seed for seed in LATE_FAMILY_QUALITY_V3_STUDY_SEEDS if seed not in indexed]
    if missing:
        raise ValueError(f"Missing v3 study seeds from {source_name}: {missing}")
    return indexed


def _index_family_rows_by_seed_and_family(
    rows: Sequence[Mapping[str, Any]],
) -> dict[int, dict[str, dict[str, Any]]]:
    indexed: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        key_seed = _safe_int(row.get("key_seed"))
        family_id = _safe_str(row.get("family_id"))
        if not family_id:
            raise ValueError(f"Missing family_id in family_quality_rows for seed {key_seed}")
        if family_id in indexed[key_seed]:
            raise ValueError(f"Duplicate family_quality_rows entry for seed {key_seed} family {family_id}")
        indexed[key_seed][family_id] = dict(row)
    missing = [seed for seed in LATE_FAMILY_QUALITY_V3_STUDY_SEEDS if seed not in indexed]
    if missing:
        raise ValueError(f"Missing family rows for v3 study seeds: {missing}")
    return indexed


def _parse_boundaries(boundaries_seen: Any) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                part.strip()
                for part in _safe_str(boundaries_seen).split("|")
                if part.strip()
            },
            key=lambda boundary: BOUNDARY_ORDER.get(boundary, 0),
        )
    )


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


def _boundary_overlap_label(
    truth_family_row: Mapping[str, Any],
    alt_family_row: Mapping[str, Any],
) -> tuple[int, str]:
    truth_boundaries = set(_parse_boundaries(truth_family_row.get("boundaries_seen")))
    alt_boundaries = set(_parse_boundaries(alt_family_row.get("boundaries_seen")))
    overlap_count = len(truth_boundaries & alt_boundaries)
    if overlap_count == 0:
        return 0, "none"
    if (
        overlap_count == _safe_int(truth_family_row.get("boundary_count"))
        and overlap_count == _safe_int(alt_family_row.get("boundary_count"))
    ):
        return overlap_count, "identical"
    return overlap_count, "partial"


def _winner_prefix(winner_type: str) -> str:
    if winner_type == "archive":
        return "archive_winner"
    return f"{winner_type}_winner"


def _winner_family_id_field(winner_type: str) -> str:
    if winner_type == "archive":
        return "archive_uplift_winner_family_id"
    return f"{winner_type}_winner_family_id"


def _copy_winner_family_fields(
    prefix: str,
    family_row: Mapping[str, Any],
    *,
    target: dict[str, Any],
) -> None:
    target[f"{prefix}_family_id"] = _safe_str(family_row.get("family_id"))
    target[f"{prefix}_best_truth"] = _safe_float(family_row.get("best_truth"))
    target[f"{prefix}_best_trust"] = _safe_float(family_row.get("best_trust"))
    target[f"{prefix}_best_archive_uplift"] = _safe_float(family_row.get("best_archive_uplift"))
    target[f"{prefix}_best_full_uplift"] = _safe_float(family_row.get("best_full_uplift"))
    target[f"{prefix}_boundary_count"] = _safe_int(family_row.get("boundary_count"))
    target[f"{prefix}_boundaries_seen"] = _safe_str(family_row.get("boundaries_seen"))
    target[f"{prefix}_family_persistence_count"] = _safe_int(family_row.get("family_persistence_count"))
    target[f"{prefix}_family_reaches_archive"] = int(_safe_int(family_row.get("family_reaches_archive")) > 0)
    target[f"{prefix}_family_role_label"] = _safe_str(family_row.get("family_role_label"))
    target[f"{prefix}_truth_trend_label"] = _safe_str(family_row.get("truth_trend_label"))
    target[f"{prefix}_trust_trend_label"] = _safe_str(family_row.get("trust_trend_label"))
    target[f"{prefix}_archive_uplift_trend_label"] = _safe_str(family_row.get("archive_uplift_trend_label"))
    target[f"{prefix}_full_uplift_trend_label"] = _safe_str(family_row.get("full_uplift_trend_label"))
    target[f"{prefix}_strength_label"] = _label_family_strength(family_row)


def _compute_truth_relative_pair(
    *,
    seed_row: Mapping[str, Any],
    truth_family_row: Mapping[str, Any],
    alt_family_row: Mapping[str, Any],
    pair_name: str,
) -> dict[str, Any]:
    _, _, alt_type = pair_name.partition("truth_vs_")
    truth_family_id = _safe_str(truth_family_row.get("family_id"))
    alt_family_id = _safe_str(alt_family_row.get("family_id"))
    same_family = int(bool(truth_family_id) and truth_family_id == alt_family_id)
    overlap_count, overlap_label = _boundary_overlap_label(truth_family_row, alt_family_row)
    pair_row: dict[str, Any] = {
        "key_seed": _safe_int(seed_row.get("key_seed")),
        "study_role": _safe_str(seed_row.get("study_role")),
        "target_panel_name": _safe_str(seed_row.get("target_panel_name")),
        "target_panel_role": _safe_str(seed_row.get("target_panel_role")),
        "pair_name": pair_name,
        "truth_family_id": truth_family_id,
        "alt_family_id": alt_family_id,
        "same_family": same_family,
        "truth_winner_strength_label": _label_family_strength(truth_family_row),
        "alt_winner_strength_label": _label_family_strength(alt_family_row),
        "truth_minus_alt_best_truth": _safe_float(truth_family_row.get("best_truth")) - _safe_float(alt_family_row.get("best_truth")),
        "truth_minus_alt_persistence_count": (
            _safe_int(truth_family_row.get("family_persistence_count"))
            - _safe_int(alt_family_row.get("family_persistence_count"))
        ),
        "truth_minus_alt_boundary_count": (
            _safe_int(truth_family_row.get("boundary_count"))
            - _safe_int(alt_family_row.get("boundary_count"))
        ),
        "archive_reach_diff": (
            int(_safe_int(truth_family_row.get("family_reaches_archive")) > 0)
            - int(_safe_int(alt_family_row.get("family_reaches_archive")) > 0)
        ),
        "boundary_overlap_count": overlap_count,
        "boundary_overlap_label": overlap_label,
        "pair_read_label": "",
    }
    pair_row["pair_read_label"] = _label_pair_read(pair_row)
    return pair_row


def _label_pair_read(pair_row: Mapping[str, Any]) -> str:
    if _safe_int(pair_row.get("same_family")) == 1:
        return "same_family"
    truth_gap = _safe_float(pair_row.get("truth_minus_alt_best_truth"))
    persistence_gap = _safe_int(pair_row.get("truth_minus_alt_persistence_count"))
    boundary_overlap_label = _safe_str(pair_row.get("boundary_overlap_label"))
    alt_strength_label = _safe_str(pair_row.get("alt_winner_strength_label"))
    if not _is_finite(truth_gap):
        return "inconclusive"
    if (
        truth_gap >= CLEAR_TRUTH_GAP
        and (
            persistence_gap >= CLEAR_PERSISTENCE_GAP
            or boundary_overlap_label == "none"
            or alt_strength_label == "weak"
        )
    ):
        return "truth_advantaged"
    if alt_strength_label == "weak":
        return "weak_alt_but_same_pattern"
    return "alt_not_clearly_weaker"


def _label_split_pattern(seed_row: Mapping[str, Any]) -> str:
    truth_family_id = _safe_str(seed_row.get("truth_winner_family_id"))
    if not truth_family_id:
        return "inconclusive"
    differing: list[str] = []
    for winner_type in ALTERNATIVE_WINNER_TYPES:
        alt_family_id = _safe_str(seed_row.get(_winner_family_id_field(winner_type)))
        if not alt_family_id:
            return "inconclusive"
        if alt_family_id != truth_family_id:
            differing.append(winner_type)
    if not differing:
        return "all_agree"
    if len(differing) == 1:
        if differing[0] == "trust":
            return "truth_trust_split"
        if differing[0] == "archive":
            return "truth_archive_split"
        if differing[0] == "full_uplift":
            return "truth_full_uplift_split"
        if differing[0] == "persistence":
            return "truth_persistence_split"
    return "multi_split"


def _label_pattern_strength_read(
    seed_row: Mapping[str, Any],
    *,
    reference_patterns: set[str],
) -> str:
    key_seed = _safe_int(seed_row.get("key_seed"))
    winner_pattern_key = _safe_str(seed_row.get("winner_pattern_key"))
    pattern_reference_like = winner_pattern_key in reference_patterns
    truth_strength_label = _safe_str(seed_row.get("truth_winner_strength_label"))
    truth_minus_trust = _safe_float(seed_row.get("truth_minus_trust_winner_best_truth"))
    truth_minus_archive = _safe_float(seed_row.get("truth_minus_archive_winner_best_truth"))
    truth_minus_trust_persistence = _safe_int(seed_row.get("truth_minus_trust_winner_persistence_count"))
    truth_minus_archive_persistence = _safe_int(seed_row.get("truth_minus_archive_winner_persistence_count"))
    truth_vs_trust_overlap = _safe_str(seed_row.get("truth_vs_trust_boundary_overlap_label"))
    truth_vs_archive_overlap = _safe_str(seed_row.get("truth_vs_archive_boundary_overlap_label"))
    trust_strength_label = _safe_str(seed_row.get("trust_winner_strength_label"))
    archive_strength_label = _safe_str(seed_row.get("archive_winner_strength_label"))
    truth_family_id = _safe_str(seed_row.get("truth_winner_family_id"))
    trust_family_id = _safe_str(seed_row.get("trust_winner_family_id"))
    archive_family_id = _safe_str(seed_row.get("archive_uplift_winner_family_id"))

    if (
        key_seed == 1111
        and pattern_reference_like
        and truth_strength_label in {"strong", "partial"}
        and _is_finite(truth_minus_trust)
        and _is_finite(truth_minus_archive)
        and truth_minus_trust > -CLEAR_TRUTH_GAP
        and truth_minus_archive > -CLEAR_TRUTH_GAP
    ):
        return "accepted_miss_reference_like"
    if (
        key_seed == 1311
        and truth_family_id
        and trust_family_id
        and truth_family_id != trust_family_id
        and _is_finite(truth_minus_trust)
        and truth_minus_trust >= CLEAR_TRUTH_GAP
        and (
            truth_minus_trust_persistence >= CLEAR_PERSISTENCE_GAP
            or truth_vs_trust_overlap == "none"
            or trust_strength_label == "weak"
        )
    ):
        return "trust_false_fire_suspicious"
    if (
        key_seed == 1411
        and truth_family_id
        and archive_family_id
        and truth_family_id != archive_family_id
        and _is_finite(truth_minus_archive)
        and truth_minus_archive >= CLEAR_TRUTH_GAP
        and (
            truth_minus_archive_persistence >= CLEAR_PERSISTENCE_GAP
            or truth_vs_archive_overlap == "none"
            or archive_strength_label == "weak"
        )
    ):
        return "archive_false_fire_suspicious"
    if key_seed in LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS and pattern_reference_like and truth_strength_label == "strong":
        return "reference_like_strong"
    if key_seed in LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS and pattern_reference_like and truth_strength_label == "partial":
        return "reference_like_partial"
    if pattern_reference_like and truth_strength_label == "weak":
        return "pattern_only_reference_like_but_strength_weak"
    return "inconclusive"


def _winner_row_for_seed(
    *,
    family_rows_by_seed: Mapping[int, Mapping[str, Mapping[str, Any]]],
    digest_row: Mapping[str, Any],
    key_seed: int,
    winner_type: str,
) -> dict[str, Any]:
    family_id = _safe_str(digest_row.get(_winner_family_id_field(winner_type)))
    if not family_id:
        raise ValueError(f"Missing {winner_type} winner family id for seed {key_seed}")
    try:
        return dict(family_rows_by_seed[key_seed][family_id])
    except KeyError as exc:
        raise ValueError(
            f"Winner family {family_id!r} for seed {key_seed} not found in frozen v1 family rows"
        ) from exc


def _build_pattern_strength_rows(
    *,
    family_rows: Sequence[Mapping[str, Any]],
    case_digest_rows: Sequence[Mapping[str, Any]],
    seed_agreement_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    family_rows_by_seed = _index_family_rows_by_seed_and_family(family_rows)
    digest_by_seed = _index_rows_by_seed(case_digest_rows, source_name="v1 family_quality_case_digest")
    agreement_by_seed = _index_rows_by_seed(seed_agreement_rows, source_name="v2 seed_agreement_rows")
    reference_patterns = {
        _safe_str(row.get("winner_pattern_key"))
        for row in seed_agreement_rows
        if _safe_int(row.get("key_seed")) in LATE_FAMILY_QUALITY_V3_REFERENCE_WIN_SEEDS
    }
    pattern_rows: list[dict[str, Any]] = []
    for key_seed in LATE_FAMILY_QUALITY_V3_STUDY_SEEDS:
        digest_row = digest_by_seed[key_seed]
        agreement_row = agreement_by_seed[key_seed]
        truth_winner_row = _winner_row_for_seed(
            family_rows_by_seed=family_rows_by_seed,
            digest_row=digest_row,
            key_seed=key_seed,
            winner_type="truth",
        )
        trust_winner_row = _winner_row_for_seed(
            family_rows_by_seed=family_rows_by_seed,
            digest_row=digest_row,
            key_seed=key_seed,
            winner_type="trust",
        )
        archive_winner_row = _winner_row_for_seed(
            family_rows_by_seed=family_rows_by_seed,
            digest_row=digest_row,
            key_seed=key_seed,
            winner_type="archive",
        )
        full_uplift_winner_row = _winner_row_for_seed(
            family_rows_by_seed=family_rows_by_seed,
            digest_row=digest_row,
            key_seed=key_seed,
            winner_type="full_uplift",
        )
        persistence_winner_row = _winner_row_for_seed(
            family_rows_by_seed=family_rows_by_seed,
            digest_row=digest_row,
            key_seed=key_seed,
            winner_type="persistence",
        )
        row: dict[str, Any] = {
            "artifact_path": _safe_str(truth_winner_row.get("artifact_path")),
            "run_id": _safe_str(truth_winner_row.get("run_id")),
            "key_seed": key_seed,
            "study_role": _safe_str(digest_row.get("study_role")),
            "target_panel_name": _safe_str(digest_row.get("target_panel_name")),
            "target_panel_role": _safe_str(digest_row.get("target_panel_role")),
            "run_type": _safe_str(digest_row.get("run_type")),
            "would_dump": _safe_int(digest_row.get("would_dump")),
            "would_stop": _safe_int(digest_row.get("would_stop")),
            "shadow_rule_id": _safe_str(digest_row.get("shadow_rule_id")),
            "case_shape_label": _safe_str(digest_row.get("case_shape_label")),
            "family_quality_read_label": _safe_str(digest_row.get("family_quality_read_label")),
            "winner_pattern_key": _safe_str(agreement_row.get("winner_pattern_key")),
            "pattern_bucket_label": _safe_str(agreement_row.get("pattern_bucket_label")),
            "unique_winner_family_count": _safe_int(agreement_row.get("unique_winner_family_count")),
            "truth_agreement_count": _safe_int(agreement_row.get("truth_agreement_count")),
            "pattern_reference_like": int(_safe_str(agreement_row.get("winner_pattern_key")) in reference_patterns),
        }
        for winner_type, family_row in (
            ("truth", truth_winner_row),
            ("trust", trust_winner_row),
            ("archive", archive_winner_row),
            ("full_uplift", full_uplift_winner_row),
            ("persistence", persistence_winner_row),
        ):
            prefix = _winner_prefix(winner_type)
            _copy_winner_family_fields(prefix, family_row, target=row)
            row[_winner_family_id_field(winner_type)] = _safe_str(digest_row.get(_winner_family_id_field(winner_type)))

        for alt_type, alt_row in (
            ("trust", trust_winner_row),
            ("archive", archive_winner_row),
            ("full_uplift", full_uplift_winner_row),
            ("persistence", persistence_winner_row),
        ):
            prefix = _winner_prefix(alt_type)
            row[f"truth_minus_{prefix}_best_truth"] = _safe_float(row.get("truth_winner_best_truth")) - _safe_float(row.get(f"{prefix}_best_truth"))
            row[f"truth_minus_{prefix}_persistence_count"] = (
                _safe_int(row.get("truth_winner_family_persistence_count"))
                - _safe_int(row.get(f"{prefix}_family_persistence_count"))
            )
            row[f"truth_minus_{prefix}_boundary_count"] = (
                _safe_int(row.get("truth_winner_boundary_count"))
                - _safe_int(row.get(f"{prefix}_boundary_count"))
            )
            row[f"truth_vs_{alt_type}_archive_reach_diff"] = (
                _safe_int(row.get("truth_winner_family_reaches_archive"))
                - _safe_int(row.get(f"{prefix}_family_reaches_archive"))
            )
            overlap_count, overlap_label = _boundary_overlap_label(truth_winner_row, alt_row)
            row[f"truth_vs_{alt_type}_boundary_overlap_count"] = overlap_count
            row[f"truth_vs_{alt_type}_boundary_overlap_label"] = overlap_label

        row["split_pattern_label"] = _label_split_pattern(row)
        row["pattern_strength_read_label"] = _label_pattern_strength_read(row, reference_patterns=reference_patterns)
        pattern_rows.append(row)
    return pattern_rows


def _build_truth_relative_pair_rows(
    pattern_strength_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pair_rows: list[dict[str, Any]] = []
    for seed_row in pattern_strength_rows:
        for alt_type in ALTERNATIVE_WINNER_TYPES:
            prefix = _winner_prefix(alt_type)
            pair_row = {
                "key_seed": _safe_int(seed_row.get("key_seed")),
                "study_role": _safe_str(seed_row.get("study_role")),
                "target_panel_name": _safe_str(seed_row.get("target_panel_name")),
                "target_panel_role": _safe_str(seed_row.get("target_panel_role")),
                "pair_name": f"truth_vs_{alt_type}",
                "truth_family_id": _safe_str(seed_row.get("truth_winner_family_id")),
                "alt_family_id": _safe_str(seed_row.get(_winner_family_id_field(alt_type))),
                "same_family": int(
                    _safe_str(seed_row.get("truth_winner_family_id"))
                    and _safe_str(seed_row.get("truth_winner_family_id")) == _safe_str(seed_row.get(_winner_family_id_field(alt_type)))
                ),
                "truth_winner_strength_label": _safe_str(seed_row.get("truth_winner_strength_label")),
                "alt_winner_strength_label": _safe_str(seed_row.get(f"{prefix}_strength_label")),
                "truth_minus_alt_best_truth": _safe_float(seed_row.get(f"truth_minus_{prefix}_best_truth")),
                "truth_minus_alt_persistence_count": _safe_int(seed_row.get(f"truth_minus_{prefix}_persistence_count")),
                "truth_minus_alt_boundary_count": _safe_int(seed_row.get(f"truth_minus_{prefix}_boundary_count")),
                "archive_reach_diff": _safe_int(seed_row.get(f"truth_vs_{alt_type}_archive_reach_diff")),
                "boundary_overlap_count": _safe_int(seed_row.get(f"truth_vs_{alt_type}_boundary_overlap_count")),
                "boundary_overlap_label": _safe_str(seed_row.get(f"truth_vs_{alt_type}_boundary_overlap_label")),
                "pair_read_label": "",
            }
            pair_row["pair_read_label"] = _label_pair_read(pair_row)
            pair_rows.append(pair_row)
    return pair_rows


def _build_pattern_strength_summary(
    pattern_strength_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    study_role_counts = Counter(_safe_str(row.get("study_role")) for row in pattern_strength_rows)
    split_pattern_counts = Counter(_safe_str(row.get("split_pattern_label")) for row in pattern_strength_rows)
    truth_winner_strength_counts = Counter(_safe_str(row.get("truth_winner_strength_label")) for row in pattern_strength_rows)
    pattern_strength_read_counts = Counter(_safe_str(row.get("pattern_strength_read_label")) for row in pattern_strength_rows)
    seeds_by_read: dict[str, list[int]] = defaultdict(list)
    for row in pattern_strength_rows:
        seeds_by_read[_safe_str(row.get("pattern_strength_read_label"))].append(_safe_int(row.get("key_seed")))
    return {
        "input_v1_bundle_dir": _relative_path(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR),
        "input_v2_bundle_dir": _relative_path(INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR),
        "study_seed_count": len(LATE_FAMILY_QUALITY_V3_STUDY_SEEDS),
        "study_role_counts": dict(sorted(study_role_counts.items())),
        "split_pattern_counts": dict(sorted(split_pattern_counts.items())),
        "truth_winner_strength_counts": dict(sorted(truth_winner_strength_counts.items())),
        "pattern_strength_read_counts": dict(sorted(pattern_strength_read_counts.items())),
        "seeds_by_pattern_strength_read": {
            key: sorted(values)
            for key, values in sorted(seeds_by_read.items())
        },
    }


def _metric_display(value: Any, *, integer: bool = False) -> str:
    if integer:
        return str(_safe_int(value))
    number = _safe_float(value)
    if not _is_finite(number):
        return "na"
    return f"{number:.3f}"


def _winner_table_row(seed_row: Mapping[str, Any], winner_type: str) -> str:
    prefix = _winner_prefix(winner_type)
    family_id = _safe_str(seed_row.get(f"{prefix}_family_id"))
    if winner_type == "truth":
        best_value = _metric_display(seed_row.get("truth_winner_best_truth"))
        trend = _safe_str(seed_row.get("truth_winner_truth_trend_label")) or "na"
    elif winner_type == "trust":
        best_value = _metric_display(seed_row.get("trust_winner_best_trust"))
        trend = _safe_str(seed_row.get("trust_winner_trust_trend_label")) or "na"
    elif winner_type == "archive":
        best_value = _metric_display(seed_row.get("archive_winner_best_archive_uplift"))
        trend = _safe_str(seed_row.get("archive_winner_archive_uplift_trend_label")) or "na"
    elif winner_type == "full_uplift":
        best_value = _metric_display(seed_row.get("full_uplift_winner_best_full_uplift"))
        trend = _safe_str(seed_row.get("full_uplift_winner_full_uplift_trend_label")) or "na"
    elif winner_type == "persistence":
        best_value = _metric_display(seed_row.get("persistence_winner_family_persistence_count"), integer=True)
        trend = "na"
    else:
        raise KeyError(winner_type)
    label = {
        "truth": "truth",
        "trust": "trust",
        "archive": "archive uplift",
        "full_uplift": "full uplift",
        "persistence": "persistence",
    }[winner_type]
    return (
        f"| {label} | {family_id or 'na'} | {_safe_str(seed_row.get(f'{prefix}_strength_label')) or 'na'} | "
        f"{best_value} | {_metric_display(seed_row.get(f'{prefix}_best_truth'))} | "
        f"{_metric_display(seed_row.get(f'{prefix}_family_persistence_count'), integer=True)} | "
        f"{_metric_display(seed_row.get(f'{prefix}_boundary_count'), integer=True)} | "
        f"{_metric_display(seed_row.get(f'{prefix}_family_reaches_archive'), integer=True)} | "
        f"{_safe_str(seed_row.get(f'{prefix}_family_role_label')) or 'na'} | {trend} | "
        f"{_safe_str(seed_row.get(f'{prefix}_boundaries_seen')) or 'na'} |"
    )


def _pair_table_row(pair_row: Mapping[str, Any]) -> str:
    pair_label = _safe_str(pair_row.get("pair_name")).replace("truth_vs_", "truth vs ").replace("_", " ")
    return (
        f"| {pair_label} | {_safe_int(pair_row.get('same_family'))} | "
        f"{_metric_display(pair_row.get('truth_minus_alt_best_truth'))} | "
        f"{_metric_display(pair_row.get('truth_minus_alt_persistence_count'), integer=True)} | "
        f"{_metric_display(pair_row.get('truth_minus_alt_boundary_count'), integer=True)} | "
        f"{_metric_display(pair_row.get('archive_reach_diff'), integer=True)} | "
        f"{_safe_str(pair_row.get('boundary_overlap_label')) or 'na'} | "
        f"{_safe_str(pair_row.get('pair_read_label')) or 'na'} |"
    )


def _read_bullets(seed_row: Mapping[str, Any]) -> list[str]:
    pattern_reference_like = bool(_safe_int(seed_row.get("pattern_reference_like")))
    truth_strength = _safe_str(seed_row.get("truth_winner_strength_label")) or "na"
    pattern_strength_read = _safe_str(seed_row.get("pattern_strength_read_label")) or "na"
    if pattern_reference_like and pattern_strength_read in {"reference_like_strong", "reference_like_partial", "accepted_miss_reference_like"}:
        pattern_line = "pattern is reference-like and the combined read stays reference-compatible"
    elif pattern_reference_like:
        pattern_line = "pattern is reference-like, but the strength reconciliation does not fully support it"
    else:
        pattern_line = "pattern is not reference-like under the frozen win-side patterns"
    if truth_strength == "strong":
        truth_line = "truth-winning family looks strong on persistence plus archive reach"
    elif truth_strength == "partial":
        truth_line = "truth-winning family looks partially strong but not fully locked in"
    else:
        truth_line = "truth-winning family still looks weak on the v3 strength view"
    interpretation_map = {
        "accepted_miss_reference_like": "accepted miss now looks reference-like once family strength is included",
        "trust_false_fire_suspicious": "trust false-fire remains suspicious after truth-relative family comparison",
        "archive_false_fire_suspicious": "archive false-fire remains suspicious after truth-relative family comparison",
        "reference_like_strong": "reference win stays acceptable under the combined pattern-plus-strength read",
        "reference_like_partial": "reference win stays acceptable but only with partial truth-family strength",
        "pattern_only_reference_like_but_strength_weak": "pattern membership alone looks insufficient because the truth family is weak",
        "inconclusive": "combined read stays inconclusive at v3",
    }
    return [
        pattern_line,
        truth_line,
        interpretation_map.get(pattern_strength_read, "combined read stays inconclusive at v3"),
    ]


def _write_cases_markdown(
    output_dir: Path,
    pattern_strength_rows: Sequence[Mapping[str, Any]],
    truth_relative_pair_rows: Sequence[Mapping[str, Any]],
) -> None:
    pair_rows_by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in truth_relative_pair_rows:
        pair_rows_by_seed[_safe_int(row.get("key_seed"))].append(dict(row))
    for rows in pair_rows_by_seed.values():
        rows.sort(key=lambda row: TRUTH_PAIR_ORDER.index(_safe_str(row.get("pair_name"))))

    lines: list[str] = ["# Late Family Quality v3 Cases", ""]
    for seed_row in pattern_strength_rows:
        key_seed = _safe_int(seed_row.get("key_seed"))
        lines.append(f"## Seed {key_seed}")
        lines.append("")
        lines.append(f"- Study role: `{_safe_str(seed_row.get('study_role'))}`")
        lines.append(
            f"- Current stop-harness verdict: dump=`{_safe_int(seed_row.get('would_dump'))}` "
            f"stop=`{_safe_int(seed_row.get('would_stop'))}` "
            f"rule=`{_safe_str(seed_row.get('shadow_rule_id')) or 'na'}`"
        )
        lines.append(f"- v1 family-quality read: `{_safe_str(seed_row.get('family_quality_read_label')) or 'na'}`")
        lines.append(f"- v2 winner-pattern key: `{_safe_str(seed_row.get('winner_pattern_key')) or 'na'}`")
        lines.append("")
        lines.append("| winner type | family id | strength | best value | best truth | persistence | boundary count | reaches archive | role | trend | boundaries seen |")
        lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |")
        for winner_type in WINNER_TYPES:
            lines.append(_winner_table_row(seed_row, winner_type))
        lines.append("")
        lines.append("| comparison | same family | truth gap | persistence gap | boundary gap | archive reach diff | overlap | read |")
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")
        for pair_row in pair_rows_by_seed.get(key_seed, []):
            lines.append(_pair_table_row(pair_row))
        lines.append("")
        for bullet in _read_bullets(seed_row):
            lines.append(f"- {bullet}")
        lines.append("")
    (output_dir / "pattern_strength_cases.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    _require_bundle_files(
        INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR,
        REQUIRED_V1_INPUT_FILES,
        label="late_family_quality_v3 v1 bundle",
    )
    _require_bundle_files(
        INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR,
        REQUIRED_V2_INPUT_FILES,
        label="late_family_quality_v3 v2 bundle",
    )
    family_rows = _select_study_seed_rows(
        _read_family_quality_rows(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR),
        source_name="v1 family_quality_rows",
    )
    case_digest_rows = _select_study_seed_rows(
        _read_family_quality_case_digest(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR),
        source_name="v1 family_quality_case_digest",
    )
    seed_agreement_rows = _select_study_seed_rows(
        _read_seed_agreement_rows(INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR),
        source_name="v2 seed_agreement_rows",
    )
    _read_json(INPUT_LATE_FAMILY_QUALITY_V1_BUNDLE_DIR / "family_quality_summary.json")
    _read_json(INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR / "agreement_summary.json")
    _optional_v2_pairwise_rows = _select_study_seed_rows(
        _read_winner_pairwise_rows(INPUT_LATE_FAMILY_QUALITY_V2_BUNDLE_DIR),
        source_name="v2 winner_pairwise_rows",
    )
    pattern_strength_rows = _build_pattern_strength_rows(
        family_rows=family_rows,
        case_digest_rows=case_digest_rows,
        seed_agreement_rows=seed_agreement_rows,
    )
    truth_relative_pair_rows = _build_truth_relative_pair_rows(pattern_strength_rows)
    summary = _build_pattern_strength_summary(pattern_strength_rows)

    output_dir = OUTPUT_BASE_DIR / f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')}__late_family_quality_v3"
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / "pattern_strength_rows.jsonl", pattern_strength_rows)
    _write_jsonl(output_dir / "truth_relative_pair_rows.jsonl", truth_relative_pair_rows)
    _write_json(output_dir / "pattern_strength_summary.json", summary)
    _write_cases_markdown(output_dir, pattern_strength_rows, truth_relative_pair_rows)
    print(
        "[late_family_quality_v3] "
        f"seeds={len(pattern_strength_rows)} "
        f"pairs={len(truth_relative_pair_rows)} "
        f"output={_relative_path(output_dir)}"
    )


if __name__ == "__main__":
    main()
