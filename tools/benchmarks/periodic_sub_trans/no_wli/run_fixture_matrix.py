from __future__ import annotations

"""Internal no-WLI fixture-matrix launcher.

Purpose:
- Reuse community fixture definitions/grid metadata.
- Keep no_wli outside public community manifest/order contracts.
- Sweep adaptive staged no-WLI runs with configurable scorer schedules
  and scoring experiment profiles (default: no span-hamming).

Usage:
- Edit hardcoded knobs below.
- Run: `python tools/benchmarks/periodic_sub_trans/no_wli/run_fixture_matrix.py`
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
import sys
import json
import time

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tools.benchmarks.community._campaign_common import load_json, write_json
from tools.benchmarks.config.no_wli_pipeline_profiles import get_no_wli_pipeline_profile
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCORER_SCHEDULE_ID_CATALOG,
    SCHEDULE_EARLY_A_CHAR1,
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT,
    SCHEDULE_EARLY_DEFAULT,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_LATE_DEFAULT,
    SCHEDULE_MIDDLE_M_CHAR12,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_DEFAULT,
    validate_scorer_schedule_ids,
)
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule_apply import (
    apply_no_wli_schedule,
)
from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli


# Fixture source (community-style config file; no_wli remains internal).
CAMPAIGN_CONFIG_PATH = Path("tools/benchmarks/community/examples/campaign_config_v1_1.json")
FIXTURE_IDS: tuple[str, ...] | None = None
# Force all resolved fixtures to this length when set (internal sweep control).
FIXTURE_LENGTH_OVERRIDE: int | None = 1000

# Grid source.
USE_CAMPAIGN_GRID = False
PERIODS_OVERRIDE: tuple[int, ...] | None = (5, 7, 9, 11, 13)
COLUMNS_OVERRIDE_BY_PERIOD: dict[int, tuple[int, ...]] = {
    5: (1, 3),
    7: (1, 3, 5),
    9: (1, 3, 5, 7),
    11: (1, 3, 5, 7, 9),
    13: (1, 3, 5, 7, 9, 11, 13),
}

# no_wli runtime config.
RUN_MODE = "adaptive_fixture_v1"  # full | adaptive_fixture_v1 | others from no_wli runner
NO_WLI_PROFILE_ID = "no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1"
RUN_SEEDS = (111,)
TEXT_OFFSETS = (0,)
HEARTBEAT_SECONDS = 3600
SCORER_IMPL = "numpy"
SCORER_STAGE3_IMPL_AVG_FULLTEXT = "numpy"

# Scoring experiment profile sweep.
# Default "off" keeps span-hamming disabled.
SCORING_EXPERIMENT_PROFILES = ("c_min_late",)

# Schedule sweep policy:
# - minimal_all_ids: compact sweep that covers every early/middle/late ID at least once.
# - minimal_avg_ids: compact sweep that covers all avg-friendly no-WLI IDs.
# - cartesian_all: full early x middle x late cartesian sweep.
# - explicit: use EXPLICIT_SCHEDULES exactly.
SCHEDULE_COVERAGE_MODE = "explicit"  # minimal_avg_ids | minimal_all_ids | cartesian_all | explicit
EXPLICIT_SCHEDULES: tuple[dict[str, str], ...] = (
    dict(
        early=str(SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT),
        middle=str(SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT),
        late=str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
    ),
)
# Golden-rule guard for this problem class.
REQUIRE_NO_WIN10_OBJECTIVES = True
REQUIRE_FULL_TEXT_EFFECTIVE = True

# Execution controls.
DISABLE_STAGE3_SPAN_BASIN_K_SWEEP = False
STAGE3_SPAN_BASIN_K_SWEEP_VALUES: tuple[int, ...] = (96,)
DRY_RUN_ONLY = False
STOP_ON_ERROR = True
MAX_JOBS: int | None = None
# No hard wallclock cap by default; operator stops manually when needed.
MAX_WALLCLOCK_SECONDS: float | None = None

# Durable progress checkpoints for interruption-safe long runs.
RUN_STATE_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_state_latest.json"
)
RUN_EVENTS_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_run_events_latest.jsonl"
)
RESUME_SKIP_COMPLETED = True

PLAN_OUTPUT_PATH = Path(
    "output/tools/benchmarks/periodic_sub_trans/no_wli/fixture_matrix_plan_latest.json"
)
WRITE_PLAN_JSON = True


@dataclass(frozen=True)
class FixtureSpec:
    fixture_id: str
    length: int
    source_path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": str(self.fixture_id),
            "length": int(self.length),
            "source_path": (None if self.source_path is None else str(self.source_path)),
        }


@dataclass(frozen=True)
class NoWliFixtureJob:
    fixture_id: str
    period: int
    columns: int
    length: int
    run_seed: int
    run_mode: str
    profile_id: str
    heartbeat_seconds: int
    text_offsets: tuple[int, ...]
    scorer_impl: str
    scorer_stage3_impl_avg_fulltext: str
    scoring_experiment_profile: str
    schedule_early: str
    schedule_middle: str
    schedule_late: str

    def scorer_schedule(self) -> dict[str, str]:
        return {
            "early": str(self.schedule_early),
            "middle": str(self.schedule_middle),
            "late": str(self.schedule_late),
        }

    def tier_name(self) -> str:
        return (
            f"fixture_{self.fixture_id}_p{int(self.period)}"
            f"_c{int(self.columns)}_l{int(self.length)}"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": str(self.fixture_id),
            "period": int(self.period),
            "columns": int(self.columns),
            "length": int(self.length),
            "run_seed": int(self.run_seed),
            "run_mode": str(self.run_mode),
            "profile_id": str(self.profile_id),
            "heartbeat_seconds": int(self.heartbeat_seconds),
            "text_offsets": [int(x) for x in self.text_offsets],
            "scorer_impl": str(self.scorer_impl),
            "scorer_stage3_impl_avg_fulltext": str(self.scorer_stage3_impl_avg_fulltext),
            "scoring_experiment_profile": str(self.scoring_experiment_profile),
            "scorer_schedule": self.scorer_schedule(),
            "tier_name": self.tier_name(),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_key(job: NoWliFixtureJob) -> str:
    return "|".join(
        (
            str(job.fixture_id),
            f"p{int(job.period)}",
            f"c{int(job.columns)}",
            f"l{int(job.length)}",
            f"seed{int(job.run_seed)}",
            str(job.run_mode),
            str(job.profile_id),
            str(job.scoring_experiment_profile),
            str(job.schedule_early),
            str(job.schedule_middle),
            str(job.schedule_late),
        )
    )


def _load_run_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = load_json(path)
    if not isinstance(payload, Mapping):
        return {}
    return {str(k): v for k, v in payload.items()}


def _append_event_row(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(dict(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        )
        handle.write("\n")


def _unique_sorted_ints(values: Iterable[int]) -> tuple[int, ...]:
    seen: set[int] = set()
    out: list[int] = []
    for raw in values:
        value = int(raw)
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    out.sort()
    return tuple(out)


def _fixture_length_from_metadata(
    *,
    fixture_row: Mapping[str, Any],
    repo_root: Path,
) -> int:
    for key in ("length", "text_length", "plaintext_length"):
        value = fixture_row.get(key)
        if isinstance(value, int) and value > 0:
            return int(value)

    rel_path = fixture_row.get("path")
    if isinstance(rel_path, str) and rel_path.strip():
        fixture_path = (repo_root / rel_path).resolve()
        if fixture_path.exists():
            payload = load_json(fixture_path)
            if isinstance(payload, Mapping):
                for key in ("length", "text_length", "plaintext_length"):
                    value = payload.get(key)
                    if isinstance(value, int) and value > 0:
                        return int(value)

    raise ValueError(
        f"fixture {fixture_row.get('text_fixture_id', '')!r} missing length metadata "
        "(expected length/text_length/plaintext_length or path payload with one of those fields)"
    )


def load_fixture_specs(
    *,
    campaign_config: Mapping[str, Any],
    repo_root: Path,
    fixture_ids: Sequence[str] | None = None,
    fixture_length_override: int | None = None,
) -> list[FixtureSpec]:
    rows = campaign_config.get("fixtures")
    if not isinstance(rows, list) or not rows:
        raise ValueError("campaign_config.fixtures must be a non-empty list")

    selected: set[str] | None = None
    if fixture_ids is not None:
        selected = {str(x) for x in fixture_ids}

    out: list[FixtureSpec] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("each fixtures row must be an object")
        fixture_id = str(row.get("text_fixture_id", "")).strip()
        if not fixture_id:
            raise ValueError("fixtures row missing text_fixture_id")
        if selected is not None and fixture_id not in selected:
            continue
        length = _fixture_length_from_metadata(fixture_row=row, repo_root=repo_root)
        if fixture_length_override is not None:
            override = int(fixture_length_override)
            if override <= 0:
                raise ValueError(
                    f"fixture_length_override must be > 0, got {fixture_length_override}"
                )
            length = int(override)
        src = row.get("path")
        source_path = (str(src).strip() if isinstance(src, str) and str(src).strip() else None)
        out.append(
            FixtureSpec(
                fixture_id=fixture_id,
                length=int(length),
                source_path=source_path,
            )
        )

    if not out:
        if selected is not None:
            raise ValueError(
                "fixture filter matched zero rows; "
                f"requested={sorted(selected)}"
            )
        raise ValueError("no fixtures resolved")
    return out


def resolve_period_columns(
    *,
    campaign_config: Mapping[str, Any],
    use_campaign_grid: bool,
    periods_override: Sequence[int] | None,
    columns_override_by_period: Mapping[int, Sequence[int]] | None,
) -> dict[int, tuple[int, ...]]:
    grid = campaign_config.get("grid", {})
    if not isinstance(grid, Mapping):
        grid = {}

    period_min = int(grid.get("period_min", 0) or 0)
    period_max = int(grid.get("period_max", 0) or 0)
    columns_min = int(grid.get("columns_min", 0) or 0)
    columns_max = int(grid.get("columns_max", 0) or 0)

    if periods_override is not None:
        periods = _unique_sorted_ints(int(x) for x in periods_override)
    elif use_campaign_grid:
        if period_min <= 0 or period_max < period_min:
            raise ValueError("campaign grid period_min/period_max are invalid")
        periods = tuple(range(period_min, period_max + 1))
    else:
        raise ValueError("no periods source configured (set PERIODS_OVERRIDE or USE_CAMPAIGN_GRID)")

    if not periods:
        raise ValueError("resolved periods is empty")

    out: dict[int, tuple[int, ...]] = {}
    override = columns_override_by_period or {}
    for period in periods:
        per_cols_raw = override.get(int(period))
        if per_cols_raw is not None:
            cols = _unique_sorted_ints(int(x) for x in per_cols_raw)
        else:
            if not use_campaign_grid:
                raise ValueError(
                    f"columns not provided for period={int(period)} while USE_CAMPAIGN_GRID=False"
                )
            if columns_min <= 0 or columns_max < columns_min:
                raise ValueError("campaign grid columns_min/columns_max are invalid")
            cols = tuple(range(columns_min, columns_max + 1))
        if not cols:
            raise ValueError(f"resolved columns empty for period={int(period)}")
        out[int(period)] = cols
    return out


def build_schedule_matrix(
    *,
    mode: str,
    explicit_schedules: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, str]]:
    m = str(mode).strip().lower()
    early_ids = sorted(SCORER_SCHEDULE_ID_CATALOG["early"])
    middle_ids = sorted(SCORER_SCHEDULE_ID_CATALOG["middle"])
    late_ids = sorted(SCORER_SCHEDULE_ID_CATALOG["late"])

    rows: list[dict[str, str]] = []
    if m == "cartesian_all":
        for early in early_ids:
            for middle in middle_ids:
                for late in late_ids:
                    rows.append(dict(early=str(early), middle=str(middle), late=str(late)))
    elif m == "minimal_all_ids":
        base = dict(
            early=str(SCHEDULE_EARLY_A_CHAR1),
            middle=str(SCHEDULE_MIDDLE_M_CHAR12),
            late=str(SCHEDULE_LATE_B_CHAR34),
        )
        rows.append(dict(base))
        for early in early_ids:
            rows.append(dict(early=str(early), middle=base["middle"], late=base["late"]))
        for middle in middle_ids:
            rows.append(dict(early=base["early"], middle=str(middle), late=base["late"]))
        for late in late_ids:
            rows.append(dict(early=base["early"], middle=base["middle"], late=str(late)))
    elif m == "minimal_avg_ids":
        early_avg_ids = (
            str(SCHEDULE_EARLY_DEFAULT),
            str(SCHEDULE_EARLY_A_CHAR1),
            str(SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT),
            str(SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT),
        )
        middle_avg_ids = (
            str(SCHEDULE_MIDDLE_DEFAULT),
            str(SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT),
            str(SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT),
        )
        late_avg_ids = (
            str(SCHEDULE_LATE_DEFAULT),
            str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
        )
        base = dict(
            early=str(SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT),
            middle=str(SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT),
            late=str(SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT),
        )
        rows.append(dict(base))
        for early in early_avg_ids:
            rows.append(dict(early=str(early), middle=base["middle"], late=base["late"]))
        for middle in middle_avg_ids:
            rows.append(dict(early=base["early"], middle=str(middle), late=base["late"]))
        for late in late_avg_ids:
            rows.append(dict(early=base["early"], middle=base["middle"], late=str(late)))
    elif m == "explicit":
        if explicit_schedules is None or len(explicit_schedules) == 0:
            raise ValueError("explicit schedule mode requires EXPLICIT_SCHEDULES entries")
        for raw in explicit_schedules:
            if not isinstance(raw, Mapping):
                raise ValueError("explicit schedule rows must be objects")
            rows.append(
                dict(
                    early=str(raw.get("early", "")).strip(),
                    middle=str(raw.get("middle", "")).strip(),
                    late=str(raw.get("late", "")).strip(),
                )
            )
    else:
        raise ValueError(
            f"unknown schedule coverage mode={mode!r}; "
            "expected minimal_avg_ids|minimal_all_ids|cartesian_all|explicit"
        )

    dedup: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        norm = validate_scorer_schedule_ids(row, require_all_keys=True)
        key = (str(norm.early), str(norm.middle), str(norm.late))
        if key in seen:
            continue
        seen.add(key)
        dedup.append(dict(early=key[0], middle=key[1], late=key[2]))
    return dedup


def resolve_stage_objectives_for_schedule(
    *,
    profile_id: str,
    schedule: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    profile = get_no_wli_pipeline_profile(str(profile_id))
    stage1 = profile.scorer_schedule.stage1_a.to_params()
    stage2 = profile.scorer_schedule.stage2_m.to_params()
    stage3 = profile.scorer_schedule.stage3_b.to_params()
    apply_no_wli_schedule(
        scorer_schedule=schedule,
        stage1_cfg=stage1,
        stage2_cfg=stage2,
        stage3_cfg=stage3,
    )
    def _summary(cfg: Mapping[str, Any]) -> dict[str, str]:
        return {
            "objective": str(cfg.get("objective", "")).strip().lower(),
            "avg_window_policy": str(cfg.get("avg_window_policy", "")).strip().lower(),
        }

    return {
        "stage1": _summary(stage1),
        "stage2": _summary(stage2),
        "stage3": _summary(stage3),
    }


def validate_schedule_contract(
    *,
    profile_id: str,
    schedule: Mapping[str, str],
) -> None:
    scoring = resolve_stage_objectives_for_schedule(
        profile_id=str(profile_id),
        schedule=schedule,
    )
    if bool(REQUIRE_NO_WIN10_OBJECTIVES):
        offenders = [
            stage_name
            for stage_name, info in scoring.items()
            if "win10" in str(info.get("objective", ""))
        ]
        if offenders:
            raise ValueError(
                "REQUIRE_NO_WIN10_OBJECTIVES violated: "
                f"profile={profile_id} schedule={schedule} scoring={scoring}"
            )
    if bool(REQUIRE_FULL_TEXT_EFFECTIVE):
        offenders = [
            stage_name
            for stage_name, info in scoring.items()
            if str(info.get("avg_window_policy", "")) != "full_text"
        ]
        if offenders:
            raise ValueError(
                "REQUIRE_FULL_TEXT_EFFECTIVE violated: "
                f"profile={profile_id} schedule={schedule} scoring={scoring}"
            )


def build_fixture_jobs(
    *,
    fixtures: Sequence[FixtureSpec],
    period_columns: Mapping[int, Sequence[int]],
    run_seeds: Sequence[int],
    run_mode: str,
    profile_id: str,
    heartbeat_seconds: int,
    text_offsets: Sequence[int],
    scorer_impl: str,
    scorer_stage3_impl_avg_fulltext: str,
    scoring_experiment_profiles: Sequence[str],
    schedules: Sequence[Mapping[str, str]],
) -> list[NoWliFixtureJob]:
    seeds = _unique_sorted_ints(int(x) for x in run_seeds)
    if not seeds:
        raise ValueError("RUN_SEEDS resolved empty")

    exp_profiles = [str(x).strip().lower() for x in scoring_experiment_profiles if str(x).strip()]
    if not exp_profiles:
        raise ValueError("SCORING_EXPERIMENT_PROFILES resolved empty")

    offsets = tuple(int(x) for x in text_offsets)
    if not offsets:
        raise ValueError("TEXT_OFFSETS resolved empty")

    jobs: list[NoWliFixtureJob] = []
    validated_schedules: list[dict[str, str]] = []
    for schedule in schedules:
        norm = validate_scorer_schedule_ids(schedule, require_all_keys=True)
        resolved = dict(early=str(norm.early), middle=str(norm.middle), late=str(norm.late))
        validate_schedule_contract(
            profile_id=str(profile_id),
            schedule=resolved,
        )
        validated_schedules.append(resolved)

    for fixture in fixtures:
        for period in sorted(int(k) for k in period_columns.keys()):
            columns = _unique_sorted_ints(int(x) for x in period_columns[period])
            for column in columns:
                for run_seed in seeds:
                    for exp_profile in exp_profiles:
                        for schedule in validated_schedules:
                            jobs.append(
                                NoWliFixtureJob(
                                    fixture_id=str(fixture.fixture_id),
                                    period=int(period),
                                    columns=int(column),
                                    length=int(fixture.length),
                                    run_seed=int(run_seed),
                                    run_mode=str(run_mode),
                                    profile_id=str(profile_id),
                                    heartbeat_seconds=int(heartbeat_seconds),
                                    text_offsets=offsets,
                                    scorer_impl=str(scorer_impl),
                                    scorer_stage3_impl_avg_fulltext=str(scorer_stage3_impl_avg_fulltext),
                                    scoring_experiment_profile=str(exp_profile),
                                    schedule_early=str(schedule["early"]),
                                    schedule_middle=str(schedule["middle"]),
                                    schedule_late=str(schedule["late"]),
                                )
                            )
    return jobs


def apply_job(job: NoWliFixtureJob) -> None:
    if bool(DISABLE_STAGE3_SPAN_BASIN_K_SWEEP):
        no_wli.RUN_STAGE3_SPAN_BASIN_K_SWEEP = False
    else:
        no_wli.RUN_STAGE3_SPAN_BASIN_K_SWEEP = True
        no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES = [
            int(x) for x in STAGE3_SPAN_BASIN_K_SWEEP_VALUES
        ]
        if no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES:
            no_wli.STAGE3_SPAN_BASIN_JUDGE_K = int(
                no_wli.STAGE3_SPAN_BASIN_K_SWEEP_VALUES[0]
            )

    no_wli.configure_campaign_run(
        run_seed=int(job.run_seed),
        period=int(job.period),
        columns=int(job.columns),
        length=int(job.length),
        tier_name=str(job.tier_name()),
        run_mode=str(job.run_mode),
        profile_name=str(job.profile_id),
        heartbeat_seconds=int(job.heartbeat_seconds),
        autoskip_proven=False,
        force_rerun_proven=True,
        avoid_repeat_fail=False,
        text_offsets=[int(x) for x in job.text_offsets],
        tiers_regex_override=None,
        scorer_impl=str(job.scorer_impl),
        scorer_stage3_impl_avg_fulltext=str(job.scorer_stage3_impl_avg_fulltext),
        scorer_schedule=job.scorer_schedule(),
    )
    no_wli.SCORING_EXPERIMENT_PROFILE = str(job.scoring_experiment_profile)


def run_job(job: NoWliFixtureJob) -> None:
    apply_job(job)
    no_wli.main()


def _resolve_path(path_like: Path) -> Path:
    path = Path(path_like)
    if not path.is_absolute():
        path = (_ROOT / path).resolve()
    else:
        path = path.resolve()
    return path


def main() -> None:
    campaign_path = _resolve_path(CAMPAIGN_CONFIG_PATH)
    campaign_config = load_json(campaign_path)
    if not isinstance(campaign_config, Mapping):
        raise ValueError(f"campaign config must be an object: {campaign_path}")

    fixtures = load_fixture_specs(
        campaign_config=campaign_config,
        repo_root=_ROOT,
        fixture_ids=FIXTURE_IDS,
        fixture_length_override=FIXTURE_LENGTH_OVERRIDE,
    )
    period_columns = resolve_period_columns(
        campaign_config=campaign_config,
        use_campaign_grid=bool(USE_CAMPAIGN_GRID),
        periods_override=PERIODS_OVERRIDE,
        columns_override_by_period=COLUMNS_OVERRIDE_BY_PERIOD,
    )
    schedules = build_schedule_matrix(
        mode=str(SCHEDULE_COVERAGE_MODE),
        explicit_schedules=EXPLICIT_SCHEDULES,
    )
    jobs = build_fixture_jobs(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=RUN_SEEDS,
        run_mode=RUN_MODE,
        profile_id=NO_WLI_PROFILE_ID,
        heartbeat_seconds=HEARTBEAT_SECONDS,
        text_offsets=TEXT_OFFSETS,
        scorer_impl=SCORER_IMPL,
        scorer_stage3_impl_avg_fulltext=SCORER_STAGE3_IMPL_AVG_FULLTEXT,
        scoring_experiment_profiles=SCORING_EXPERIMENT_PROFILES,
        schedules=schedules,
    )
    if MAX_JOBS is not None:
        jobs = jobs[: max(0, int(MAX_JOBS))]

    plan_payload = {
        "campaign_config_path": str(campaign_path),
        "run_mode": str(RUN_MODE),
        "profile_id": str(NO_WLI_PROFILE_ID),
        "schedule_coverage_mode": str(SCHEDULE_COVERAGE_MODE),
        "schedule_count": int(len(schedules)),
        "fixture_count": int(len(fixtures)),
        "job_count": int(len(jobs)),
        "scoring_experiment_profiles": [str(x) for x in SCORING_EXPERIMENT_PROFILES],
        "require_no_win10_objectives": bool(REQUIRE_NO_WIN10_OBJECTIVES),
        "require_full_text_effective": bool(REQUIRE_FULL_TEXT_EFFECTIVE),
        "disable_stage3_span_basin_k_sweep": bool(DISABLE_STAGE3_SPAN_BASIN_K_SWEEP),
        "stage3_span_basin_k_sweep_values": [int(x) for x in STAGE3_SPAN_BASIN_K_SWEEP_VALUES],
        "dry_run_only": bool(DRY_RUN_ONLY),
        "max_wallclock_seconds": (None if MAX_WALLCLOCK_SECONDS is None else float(MAX_WALLCLOCK_SECONDS)),
        "resume_skip_completed": bool(RESUME_SKIP_COMPLETED),
        "run_state_path": str(_resolve_path(RUN_STATE_PATH)),
        "run_events_path": str(_resolve_path(RUN_EVENTS_PATH)),
        "fixture_length_override": (
            None if FIXTURE_LENGTH_OVERRIDE is None else int(FIXTURE_LENGTH_OVERRIDE)
        ),
        "fixtures": [fx.as_dict() for fx in fixtures],
        "period_columns": {str(k): [int(c) for c in v] for k, v in period_columns.items()},
        "jobs": [job.as_dict() for job in jobs],
    }
    if WRITE_PLAN_JSON:
        write_json(_resolve_path(PLAN_OUTPUT_PATH), plan_payload)

    print(
        f"[no_wli_fixture_matrix] fixtures={len(fixtures)} periods={len(period_columns)} "
        f"schedules={len(schedules)} jobs={len(jobs)} dry_run={int(bool(DRY_RUN_ONLY))}",
        flush=True,
    )
    if not jobs:
        print("[no_wli_fixture_matrix] no jobs to run", flush=True)
        return
    if DRY_RUN_ONLY:
        print("[no_wli_fixture_matrix] dry-run complete (no runner executions)", flush=True)
        return

    run_state_path = _resolve_path(RUN_STATE_PATH)
    run_events_path = _resolve_path(RUN_EVENTS_PATH)
    run_state = _load_run_state(run_state_path)
    completed_job_keys: set[str] = {
        str(x) for x in run_state.get("completed_job_keys", []) if str(x).strip()
    }
    plan_job_keys = {_job_key(job) for job in jobs}
    # Keep only keys from the current plan to avoid cross-plan contamination.
    completed_job_keys.intersection_update(plan_job_keys)
    if bool(RESUME_SKIP_COMPLETED):
        jobs = [job for job in jobs if _job_key(job) not in completed_job_keys]
    skipped_precompleted = int(plan_payload["job_count"]) - len(jobs)
    if skipped_precompleted > 0:
        print(
            f"[no_wli_fixture_matrix] resume: skipping {skipped_precompleted} pre-completed jobs",
            flush=True,
        )

    run_state_base: dict[str, Any] = dict(
        started_utc=str(run_state.get("started_utc") or _utc_now_iso()),
        updated_utc=_utc_now_iso(),
        campaign_config_path=str(campaign_path),
        run_mode=str(RUN_MODE),
        profile_id=str(NO_WLI_PROFILE_ID),
        schedule_coverage_mode=str(SCHEDULE_COVERAGE_MODE),
        scoring_experiment_profiles=[str(x) for x in SCORING_EXPERIMENT_PROFILES],
        total_jobs=int(plan_payload["job_count"]),
        remaining_jobs=int(len(jobs)),
        skipped_precompleted=int(skipped_precompleted),
        completed_jobs=int(len(completed_job_keys)),
        completed_job_keys=sorted(completed_job_keys),
        stopped_early=0,
        run_state_version="v1",
    )
    write_json(run_state_path, run_state_base)

    wallclock_start = time.time()
    completed_this_session = 0
    stopped_early = False
    for idx, job in enumerate(jobs, start=1):
        job_key = _job_key(job)
        if MAX_WALLCLOCK_SECONDS is not None:
            elapsed = float(time.time() - wallclock_start)
            if elapsed >= float(MAX_WALLCLOCK_SECONDS):
                print(
                    f"[no_wli_fixture_matrix] wallclock cap reached; "
                    f"elapsed={elapsed:.1f}s cap={float(MAX_WALLCLOCK_SECONDS):.1f}s "
                    f"completed_jobs={idx-1}",
                    flush=True,
                )
                stopped_early = True
                break
        print(
            f"[no_wli_fixture_matrix] run {idx}/{len(jobs)} "
            f"fixture={job.fixture_id} p={job.period} c={job.columns} seed={job.run_seed} "
            f"exp={job.scoring_experiment_profile} "
            f"schedule=({job.schedule_early},{job.schedule_middle},{job.schedule_late})",
            flush=True,
        )
        _append_event_row(
            run_events_path,
            dict(
                timestamp_utc=_utc_now_iso(),
                event="job_started",
                run_mode=str(RUN_MODE),
                profile_id=str(NO_WLI_PROFILE_ID),
                index=int(idx),
                total=int(len(jobs)),
                job_key=str(job_key),
                job=job.as_dict(),
            ),
        )
        t0_job = time.time()
        try:
            run_job(job)
        except Exception as exc:
            print(
                f"[no_wli_fixture_matrix] error fixture={job.fixture_id} p={job.period} c={job.columns} "
                f"seed={job.run_seed} err={type(exc).__name__}:{exc}",
                flush=True,
            )
            _append_event_row(
                run_events_path,
                dict(
                    timestamp_utc=_utc_now_iso(),
                    event="job_error",
                    run_mode=str(RUN_MODE),
                    profile_id=str(NO_WLI_PROFILE_ID),
                    index=int(idx),
                    total=int(len(jobs)),
                    job_key=str(job_key),
                    elapsed_seconds=float(time.time() - t0_job),
                    error_type=str(type(exc).__name__),
                    error=str(exc),
                ),
            )
            run_state_base.update(
                updated_utc=_utc_now_iso(),
                last_error=dict(
                    index=int(idx),
                    job_key=str(job_key),
                    error_type=str(type(exc).__name__),
                    error=str(exc),
                ),
                stopped_early=1,
                completed_jobs=int(len(completed_job_keys)),
                completed_job_keys=sorted(completed_job_keys),
                remaining_jobs=int(max(0, len(jobs) - idx + 1)),
            )
            write_json(run_state_path, run_state_base)
            if bool(STOP_ON_ERROR):
                raise
            continue

        completed_job_keys.add(str(job_key))
        completed_this_session += 1
        job_elapsed = float(time.time() - t0_job)
        _append_event_row(
            run_events_path,
            dict(
                timestamp_utc=_utc_now_iso(),
                event="job_completed",
                run_mode=str(RUN_MODE),
                profile_id=str(NO_WLI_PROFILE_ID),
                index=int(idx),
                total=int(len(jobs)),
                job_key=str(job_key),
                elapsed_seconds=float(job_elapsed),
            ),
        )
        run_state_base.update(
            updated_utc=_utc_now_iso(),
            completed_jobs=int(len(completed_job_keys)),
            completed_job_keys=sorted(completed_job_keys),
            last_completed=dict(
                index=int(idx),
                job_key=str(job_key),
                elapsed_seconds=float(job_elapsed),
            ),
            remaining_jobs=int(max(0, len(jobs) - idx)),
        )
        write_json(run_state_path, run_state_base)

    run_state_base.update(
        updated_utc=_utc_now_iso(),
        completed_utc=_utc_now_iso(),
        stopped_early=int(bool(stopped_early)),
        completed_jobs=int(len(completed_job_keys)),
        completed_job_keys=sorted(completed_job_keys),
        remaining_jobs=int(0 if not stopped_early else run_state_base.get("remaining_jobs", 0)),
    )
    write_json(run_state_path, run_state_base)
    print(
        f"[no_wli_fixture_matrix] completed session_completed_jobs={completed_this_session} "
        f"total_completed_jobs={len(completed_job_keys)}",
        flush=True,
    )


if __name__ == "__main__":
    main()
