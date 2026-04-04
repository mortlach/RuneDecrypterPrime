from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, Mapping


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
    stage3_tuning_preset_id: str = "base"
    span_ab_case_id: str = "none"
    span_decision_role_enabled: bool = False

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
            "stage3_tuning_preset_id": str(self.stage3_tuning_preset_id),
            "span_ab_case_id": str(self.span_ab_case_id),
            "span_decision_role_enabled": bool(self.span_decision_role_enabled),
            "scorer_schedule": self.scorer_schedule(),
            "tier_name": self.tier_name(),
        }


@dataclass(frozen=True)
class MatrixControlFiles:
    experiment_run_id: str
    base_dir: Path

    @classmethod
    def for_experiment(
        cls,
        *,
        experiment_run_id: str,
        base_dir: str | Path,
    ) -> "MatrixControlFiles":
        normalized_id = str(experiment_run_id).strip()
        if not normalized_id:
            raise ValueError("experiment_run_id must be non-empty")
        return cls(
            experiment_run_id=normalized_id,
            base_dir=Path(base_dir),
        )

    @property
    def run_state_path(self) -> Path:
        return self.base_dir / f"fixture_matrix_run_state_{self.experiment_run_id}.json"

    @property
    def run_events_path(self) -> Path:
        return self.base_dir / f"fixture_matrix_run_events_{self.experiment_run_id}.jsonl"

    @property
    def plan_output_path(self) -> Path:
        return self.base_dir / f"fixture_matrix_plan_{self.experiment_run_id}.json"


@dataclass(frozen=True)
class Stage3TuningPreset:
    preset_id: str
    force_stage1_seed_restarts: int | None = None
    force_stage1_seed_total: int | None = None
    force_stage1_scout_min_steps: int | None = None
    force_stage12_archive_keep: int | None = None
    force_word_ngram_decision_influence: bool | None = None
    force_word_ngram_report_min_positions: int | None = None
    force_stage12_promote_top: int | None = None
    force_stage3_initial_keys: int | None = None
    force_stage3_initial_keys_by_columns: dict[int, int] | None = None
    force_stage3_init_keys_cap: int | None = None
    force_stage3_entry_allocation_policy: str | None = None
    force_stage3_entry_mutations_per_promoted: int | None = None
    force_solver_stage3_overrides: dict[str, Any] | None = None
    force_stage3_span_basin_judge_tie_eps: float | None = None
    force_stage3_span_basin_judge_tie_max_seeds: int | None = None
    force_stage3_two_phase: bool | None = None
    force_stage3_phasea_cfg: dict[str, int] | None = None
    force_stage3_phaseb_top_n: int | None = None
    force_stage3_phaseb_cfg: dict[str, int] | None = None
    force_stage3_phaseb_gate_delta_floor: float | None = None
    force_stage3_phaseb_gate_end_gain_floor: float | None = None
    force_stage3_phaseb_family_preservation_policy: str | None = None
    force_stage3_phaseb_family_view_id: str | None = None
    force_stage3_phaseb_family_reserved_slots: int | None = None
    force_stage3_phasec_enabled: bool | None = None
    force_stage3_phasec_start_keys: int | None = None
    force_stage3_phasec_seed_offset: int | None = None
    force_stage3_phasec_word_ngram_tiebreak: bool | None = None
    force_stage3_phasec_start_policy: str | None = None
    force_stage3_phasec_cfg: dict[str, Any] | None = None
    force_stage35_enabled: bool | None = None
    force_stage35_baseline_selector: str | None = None
    force_stage35_cfg: dict[str, Any] | None = None
    stage3_span_basin_k_sweep_values: tuple[int, ...] | None = None

    @classmethod
    def from_mapping(
        cls,
        *,
        preset_id: str,
        raw: Mapping[str, Any] | None,
    ) -> "Stage3TuningPreset":
        normalized_id = str(preset_id).strip().lower()
        if not normalized_id:
            raise ValueError("stage3 tuning preset id must be non-empty")
        payload = raw or {}
        if not isinstance(payload, Mapping):
            raise TypeError(
                f"stage3 tuning preset '{normalized_id}' must be a mapping, "
                f"got {type(payload).__name__}"
            )

        allowed = {field.name for field in fields(cls) if field.name != "preset_id"}
        unknown = sorted(
            str(key)
            for key in payload.keys()
            if str(key) not in allowed
        )
        if unknown:
            raise KeyError(
                f"unknown stage3 tuning preset field(s) for '{normalized_id}': "
                + ", ".join(unknown)
            )

        def _opt_int(name: str) -> int | None:
            value = payload.get(name)
            return None if value is None else int(value)

        def _opt_bool(name: str) -> bool | None:
            value = payload.get(name)
            return None if value is None else bool(value)

        def _opt_float(name: str) -> float | None:
            value = payload.get(name)
            return None if value is None else float(value)

        def _opt_str(name: str) -> str | None:
            value = payload.get(name)
            if value is None:
                return None
            normalized = str(value).strip().lower()
            return normalized or None

        def _opt_dict_str_any(name: str) -> dict[str, Any] | None:
            value = payload.get(name)
            if value is None:
                return None
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"stage3 tuning preset '{normalized_id}' field '{name}' "
                    f"must be a mapping"
                )
            return {str(k): v for k, v in value.items()}

        def _opt_dict_str_int(name: str) -> dict[str, int] | None:
            value = payload.get(name)
            if value is None:
                return None
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"stage3 tuning preset '{normalized_id}' field '{name}' "
                    f"must be a mapping"
                )
            return {str(k): int(v) for k, v in value.items()}

        def _opt_dict_int_int(name: str) -> dict[int, int] | None:
            value = payload.get(name)
            if value is None:
                return None
            if not isinstance(value, Mapping):
                raise TypeError(
                    f"stage3 tuning preset '{normalized_id}' field '{name}' "
                    f"must be a mapping"
                )
            return {int(k): int(v) for k, v in value.items()}

        def _opt_tuple_int(name: str) -> tuple[int, ...] | None:
            value = payload.get(name)
            if value is None:
                return None
            return tuple(int(x) for x in value)

        return cls(
            preset_id=normalized_id,
            force_stage1_seed_restarts=_opt_int("force_stage1_seed_restarts"),
            force_stage1_seed_total=_opt_int("force_stage1_seed_total"),
            force_stage1_scout_min_steps=_opt_int("force_stage1_scout_min_steps"),
            force_stage12_archive_keep=_opt_int("force_stage12_archive_keep"),
            force_word_ngram_decision_influence=_opt_bool(
                "force_word_ngram_decision_influence"
            ),
            force_word_ngram_report_min_positions=_opt_int(
                "force_word_ngram_report_min_positions"
            ),
            force_stage12_promote_top=_opt_int("force_stage12_promote_top"),
            force_stage3_initial_keys=_opt_int("force_stage3_initial_keys"),
            force_stage3_initial_keys_by_columns=_opt_dict_int_int(
                "force_stage3_initial_keys_by_columns"
            ),
            force_stage3_init_keys_cap=_opt_int("force_stage3_init_keys_cap"),
            force_stage3_entry_allocation_policy=_opt_str(
                "force_stage3_entry_allocation_policy"
            ),
            force_stage3_entry_mutations_per_promoted=_opt_int(
                "force_stage3_entry_mutations_per_promoted"
            ),
            force_solver_stage3_overrides=_opt_dict_str_any(
                "force_solver_stage3_overrides"
            ),
            force_stage3_span_basin_judge_tie_eps=_opt_float(
                "force_stage3_span_basin_judge_tie_eps"
            ),
            force_stage3_span_basin_judge_tie_max_seeds=_opt_int(
                "force_stage3_span_basin_judge_tie_max_seeds"
            ),
            force_stage3_two_phase=_opt_bool("force_stage3_two_phase"),
            force_stage3_phasea_cfg=_opt_dict_str_int("force_stage3_phasea_cfg"),
            force_stage3_phaseb_top_n=_opt_int("force_stage3_phaseb_top_n"),
            force_stage3_phaseb_cfg=_opt_dict_str_int("force_stage3_phaseb_cfg"),
            force_stage3_phaseb_gate_delta_floor=_opt_float(
                "force_stage3_phaseb_gate_delta_floor"
            ),
            force_stage3_phaseb_gate_end_gain_floor=_opt_float(
                "force_stage3_phaseb_gate_end_gain_floor"
            ),
            force_stage3_phaseb_family_preservation_policy=_opt_str(
                "force_stage3_phaseb_family_preservation_policy"
            ),
            force_stage3_phaseb_family_view_id=_opt_str(
                "force_stage3_phaseb_family_view_id"
            ),
            force_stage3_phaseb_family_reserved_slots=_opt_int(
                "force_stage3_phaseb_family_reserved_slots"
            ),
            force_stage3_phasec_enabled=_opt_bool("force_stage3_phasec_enabled"),
            force_stage3_phasec_start_keys=_opt_int(
                "force_stage3_phasec_start_keys"
            ),
            force_stage3_phasec_seed_offset=_opt_int(
                "force_stage3_phasec_seed_offset"
            ),
            force_stage3_phasec_word_ngram_tiebreak=_opt_bool(
                "force_stage3_phasec_word_ngram_tiebreak"
            ),
            force_stage3_phasec_start_policy=_opt_str(
                "force_stage3_phasec_start_policy"
            ),
            force_stage3_phasec_cfg=_opt_dict_str_any("force_stage3_phasec_cfg"),
            force_stage35_enabled=_opt_bool("force_stage35_enabled"),
            force_stage35_baseline_selector=_opt_str(
                "force_stage35_baseline_selector"
            ),
            force_stage35_cfg=_opt_dict_str_any("force_stage35_cfg"),
            stage3_span_basin_k_sweep_values=_opt_tuple_int(
                "stage3_span_basin_k_sweep_values"
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}

        def _set(name: str, value: Any) -> None:
            if value is not None:
                out[name] = value

        _set("force_stage1_seed_restarts", self.force_stage1_seed_restarts)
        _set("force_stage1_seed_total", self.force_stage1_seed_total)
        _set("force_stage1_scout_min_steps", self.force_stage1_scout_min_steps)
        _set("force_stage12_archive_keep", self.force_stage12_archive_keep)
        _set(
            "force_word_ngram_decision_influence",
            self.force_word_ngram_decision_influence,
        )
        _set(
            "force_word_ngram_report_min_positions",
            self.force_word_ngram_report_min_positions,
        )
        _set("force_stage12_promote_top", self.force_stage12_promote_top)
        _set("force_stage3_initial_keys", self.force_stage3_initial_keys)
        _set(
            "force_stage3_initial_keys_by_columns",
            (
                None
                if self.force_stage3_initial_keys_by_columns is None
                else {
                    int(k): int(v)
                    for k, v in self.force_stage3_initial_keys_by_columns.items()
                }
            ),
        )
        _set("force_stage3_init_keys_cap", self.force_stage3_init_keys_cap)
        _set(
            "force_stage3_entry_allocation_policy",
            self.force_stage3_entry_allocation_policy,
        )
        _set(
            "force_stage3_entry_mutations_per_promoted",
            self.force_stage3_entry_mutations_per_promoted,
        )
        _set(
            "force_solver_stage3_overrides",
            (
                None
                if self.force_solver_stage3_overrides is None
                else {str(k): v for k, v in self.force_solver_stage3_overrides.items()}
            ),
        )
        _set(
            "force_stage3_span_basin_judge_tie_eps",
            self.force_stage3_span_basin_judge_tie_eps,
        )
        _set(
            "force_stage3_span_basin_judge_tie_max_seeds",
            self.force_stage3_span_basin_judge_tie_max_seeds,
        )
        _set("force_stage3_two_phase", self.force_stage3_two_phase)
        _set(
            "force_stage3_phasea_cfg",
            (
                None
                if self.force_stage3_phasea_cfg is None
                else {str(k): int(v) for k, v in self.force_stage3_phasea_cfg.items()}
            ),
        )
        _set("force_stage3_phaseb_top_n", self.force_stage3_phaseb_top_n)
        _set(
            "force_stage3_phaseb_cfg",
            (
                None
                if self.force_stage3_phaseb_cfg is None
                else {str(k): int(v) for k, v in self.force_stage3_phaseb_cfg.items()}
            ),
        )
        _set(
            "force_stage3_phaseb_gate_delta_floor",
            self.force_stage3_phaseb_gate_delta_floor,
        )
        _set(
            "force_stage3_phaseb_gate_end_gain_floor",
            self.force_stage3_phaseb_gate_end_gain_floor,
        )
        _set(
            "force_stage3_phaseb_family_preservation_policy",
            self.force_stage3_phaseb_family_preservation_policy,
        )
        _set(
            "force_stage3_phaseb_family_view_id",
            self.force_stage3_phaseb_family_view_id,
        )
        _set(
            "force_stage3_phaseb_family_reserved_slots",
            self.force_stage3_phaseb_family_reserved_slots,
        )
        _set("force_stage3_phasec_enabled", self.force_stage3_phasec_enabled)
        _set("force_stage3_phasec_start_keys", self.force_stage3_phasec_start_keys)
        _set("force_stage3_phasec_seed_offset", self.force_stage3_phasec_seed_offset)
        _set(
            "force_stage3_phasec_word_ngram_tiebreak",
            self.force_stage3_phasec_word_ngram_tiebreak,
        )
        _set("force_stage3_phasec_start_policy", self.force_stage3_phasec_start_policy)
        _set(
            "force_stage3_phasec_cfg",
            (
                None
                if self.force_stage3_phasec_cfg is None
                else {str(k): v for k, v in self.force_stage3_phasec_cfg.items()}
            ),
        )
        _set("force_stage35_enabled", self.force_stage35_enabled)
        _set(
            "force_stage35_baseline_selector",
            self.force_stage35_baseline_selector,
        )
        _set(
            "force_stage35_cfg",
            (
                None
                if self.force_stage35_cfg is None
                else {str(k): v for k, v in self.force_stage35_cfg.items()}
            ),
        )
        _set("stage3_span_basin_k_sweep_values", self.stage3_span_basin_k_sweep_values)
        return out


@dataclass(frozen=True)
class FixtureMatrixMainflowConfig:
    campaign_config_path: Path
    fixture_ids: tuple[str, ...] | None
    fixture_length_override: int | None
    use_campaign_grid: bool
    periods_override: tuple[int, ...] | None
    columns_override_by_period: dict[int, tuple[int, ...]]
    run_mode: str
    no_wli_profile_id: str
    run_seeds: tuple[int, ...]
    text_offsets: tuple[int, ...]
    heartbeat_seconds: int
    scorer_impl: str
    scorer_stage3_impl_avg_fulltext: str
    enable_acceptance_harness_500x5: bool
    acceptance_harness_fixture_count: int
    acceptance_harness_length: int
    scoring_experiment_profiles: tuple[str, ...]
    enable_span_ab_pair: bool
    span_ab_decision_role: str
    schedule_coverage_mode: str
    explicit_schedules: tuple[dict[str, str], ...]
    require_no_win10_objectives: bool
    require_full_text_effective: bool
    disable_stage3_span_basin_k_sweep: bool
    stage3_span_basin_k_sweep_values: tuple[int, ...]
    stage3_tuning_preset_ids: tuple[str, ...]
    stage3_tuning_presets: dict[str, Stage3TuningPreset]
    dry_run_only: bool
    stop_on_error: bool
    max_jobs: int | None
    max_wallclock_seconds: float | None
    resume_skip_completed: bool
    control_files: MatrixControlFiles
    write_plan_json: bool

    def to_state(
        self,
        *,
        utc_now_iso_fn: Any,
    ) -> dict[str, Any]:
        return {
            "CAMPAIGN_CONFIG_PATH": Path(self.campaign_config_path),
            "FIXTURE_IDS": self.fixture_ids,
            "FIXTURE_LENGTH_OVERRIDE": self.fixture_length_override,
            "USE_CAMPAIGN_GRID": bool(self.use_campaign_grid),
            "PERIODS_OVERRIDE": self.periods_override,
            "COLUMNS_OVERRIDE_BY_PERIOD": {
                int(k): tuple(int(x) for x in v)
                for k, v in self.columns_override_by_period.items()
            },
            "RUN_MODE": str(self.run_mode),
            "NO_WLI_PROFILE_ID": str(self.no_wli_profile_id),
            "RUN_SEEDS": tuple(int(x) for x in self.run_seeds),
            "TEXT_OFFSETS": tuple(int(x) for x in self.text_offsets),
            "HEARTBEAT_SECONDS": int(self.heartbeat_seconds),
            "SCORER_IMPL": str(self.scorer_impl),
            "SCORER_STAGE3_IMPL_AVG_FULLTEXT": str(
                self.scorer_stage3_impl_avg_fulltext
            ),
            "ENABLE_ACCEPTANCE_HARNESS_500X5": bool(
                self.enable_acceptance_harness_500x5
            ),
            "ACCEPTANCE_HARNESS_FIXTURE_COUNT": int(
                self.acceptance_harness_fixture_count
            ),
            "ACCEPTANCE_HARNESS_LENGTH": int(self.acceptance_harness_length),
            "SCORING_EXPERIMENT_PROFILES": tuple(
                str(x) for x in self.scoring_experiment_profiles
            ),
            "ENABLE_SPAN_AB_PAIR": bool(self.enable_span_ab_pair),
            "SPAN_AB_DECISION_ROLE": str(self.span_ab_decision_role),
            "SCHEDULE_COVERAGE_MODE": str(self.schedule_coverage_mode),
            "EXPLICIT_SCHEDULES": tuple(dict(x) for x in self.explicit_schedules),
            "REQUIRE_NO_WIN10_OBJECTIVES": bool(self.require_no_win10_objectives),
            "REQUIRE_FULL_TEXT_EFFECTIVE": bool(self.require_full_text_effective),
            "DISABLE_STAGE3_SPAN_BASIN_K_SWEEP": bool(
                self.disable_stage3_span_basin_k_sweep
            ),
            "STAGE3_SPAN_BASIN_K_SWEEP_VALUES": tuple(
                int(x) for x in self.stage3_span_basin_k_sweep_values
            ),
            "STAGE3_TUNING_PRESET_IDS": tuple(
                str(x) for x in self.stage3_tuning_preset_ids
            ),
            "STAGE3_TUNING_PRESETS": {
                str(k): preset.as_dict()
                for k, preset in self.stage3_tuning_presets.items()
            },
            "DRY_RUN_ONLY": bool(self.dry_run_only),
            "STOP_ON_ERROR": bool(self.stop_on_error),
            "MAX_JOBS": (None if self.max_jobs is None else int(self.max_jobs)),
            "MAX_WALLCLOCK_SECONDS": (
                None
                if self.max_wallclock_seconds is None
                else float(self.max_wallclock_seconds)
            ),
            "RUN_STATE_PATH": Path(self.control_files.run_state_path),
            "RUN_EVENTS_PATH": Path(self.control_files.run_events_path),
            "RESUME_SKIP_COMPLETED": bool(self.resume_skip_completed),
            "PLAN_OUTPUT_PATH": Path(self.control_files.plan_output_path),
            "WRITE_PLAN_JSON": bool(self.write_plan_json),
            "EXPERIMENT_RUN_ID": str(self.control_files.experiment_run_id),
            "_utc_now_iso": utc_now_iso_fn,
        }
