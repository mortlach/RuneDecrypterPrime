from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterable, Mapping

from tools.benchmarks.community._campaign_common import load_json
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    validate_scorer_schedule_ids,
)

PIPELINE_DEFAULT = "PIPELINE_DEFAULT"
DEFAULT_RANGES_PATH = Path(__file__).resolve().parent / "ranges_v1_1.json"

DEFAULT_ALLOWED_OVERRIDE_KEYS = (
    "scorer_schedule",
    "stage3_gating",
    "stage12_carry_through",
    "stage1_breadth",
    "stage3_basin_exploration",
    "solver_stage1",
    "solver_stage2",
    "solver_stage3",
)


@dataclass(frozen=True)
class KnobSpec:
    key: str
    label: str
    meaning: str
    value_type: str
    default: Any
    min_value: float | None = None
    max_value: float | None = None
    min_item_value: int | None = None
    max_item_value: int | None = None
    allowed_item_keys: tuple[int, ...] = ()
    mode: str = "basic"


@dataclass(frozen=True)
class KnobRangeCatalog:
    version: str
    knobs: Mapping[str, KnobSpec]
    sampling_spaces: Mapping[str, Any]

    def get(self, key: str) -> KnobSpec:
        if key not in self.knobs:
            raise KeyError(f"Unknown knob key: {key}")
        return self.knobs[key]


@dataclass(frozen=True)
class BenchmarkProfile:
    profile_id: str
    description: str
    scorer_schedule: Mapping[str, Any]
    overrides: Mapping[str, Any]


@dataclass(frozen=True)
class BenchmarkProfileCatalog:
    catalog_version: str
    allowed_override_keys: tuple[str, ...]
    profiles_by_id: Mapping[str, BenchmarkProfile]
    knob_ranges: KnobRangeCatalog

    def get_profile(self, profile_id: str) -> BenchmarkProfile:
        profile = self.profiles_by_id.get(str(profile_id))
        if profile is None:
            raise ValueError(f"profile_id not found in profile catalog: {profile_id}")
        return profile


def _to_int_tuple(values: Iterable[Any]) -> tuple[int, ...]:
    out: list[int] = []
    for value in values:
        out.append(int(value))
    return tuple(out)


def _parse_knob_spec(raw: Mapping[str, Any]) -> KnobSpec:
    return KnobSpec(
        key=str(raw["key"]),
        label=str(raw.get("label", raw["key"])),
        meaning=str(raw.get("meaning", "")),
        value_type=str(raw.get("value_type", "")),
        default=raw.get("default"),
        min_value=(None if raw.get("min_value") is None else float(raw.get("min_value"))),
        max_value=(None if raw.get("max_value") is None else float(raw.get("max_value"))),
        min_item_value=(None if raw.get("min_item_value") is None else int(raw.get("min_item_value"))),
        max_item_value=(None if raw.get("max_item_value") is None else int(raw.get("max_item_value"))),
        allowed_item_keys=_to_int_tuple(raw.get("allowed_item_keys", [])),
        mode=str(raw.get("mode", "basic")),
    )


def load_knob_ranges(path: Path | None = None) -> KnobRangeCatalog:
    source = Path(path) if path is not None else DEFAULT_RANGES_PATH
    data = load_json(source)
    knobs_raw = data.get("knobs", [])
    if not isinstance(knobs_raw, list):
        raise ValueError("knob range catalog must contain a 'knobs' list")
    knobs: dict[str, KnobSpec] = {}
    for item in knobs_raw:
        if not isinstance(item, Mapping):
            raise ValueError("each knob entry must be an object")
        spec = _parse_knob_spec(item)
        if spec.key in knobs:
            raise ValueError(f"duplicate knob key in ranges catalog: {spec.key}")
        knobs[spec.key] = spec
    return KnobRangeCatalog(
        version=str(data.get("version", "unknown")),
        knobs=knobs,
        sampling_spaces=(data.get("sampling_spaces", {}) if isinstance(data.get("sampling_spaces"), Mapping) else {}),
    )


def _validate_scalar_with_bounds(value: float, *, spec: KnobSpec, key: str) -> None:
    if spec.min_value is not None and float(value) < float(spec.min_value):
        raise ValueError(f"{key}={value} below min {spec.min_value}")
    if spec.max_value is not None and float(value) > float(spec.max_value):
        raise ValueError(f"{key}={value} above max {spec.max_value}")


def _validate_map_int_int(
    value: Mapping[Any, Any],
    *,
    spec: KnobSpec,
    key: str,
) -> None:
    for raw_k, raw_v in value.items():
        try:
            kk = int(raw_k)
        except Exception as exc:
            raise ValueError(f"{key} has non-int key: {raw_k!r}") from exc
        try:
            vv = int(raw_v)
        except Exception as exc:
            raise ValueError(f"{key}[{kk}] has non-int value: {raw_v!r}") from exc
        if spec.allowed_item_keys and kk not in spec.allowed_item_keys:
            allowed = ", ".join(str(x) for x in spec.allowed_item_keys)
            raise ValueError(f"{key}[{kk}] key not in allowed set: {allowed}")
        if spec.min_item_value is not None and vv < int(spec.min_item_value):
            raise ValueError(f"{key}[{kk}]={vv} below min {spec.min_item_value}")
        if spec.max_item_value is not None and vv > int(spec.max_item_value):
            raise ValueError(f"{key}[{kk}]={vv} above max {spec.max_item_value}")


def _validate_value_against_spec(value: Any, *, spec: KnobSpec, key: str) -> None:
    if spec.value_type == "float_or_null_or_default":
        if value == PIPELINE_DEFAULT or value is None:
            return
        if not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be float/null/{PIPELINE_DEFAULT}")
        _validate_scalar_with_bounds(float(value), spec=spec, key=key)
        return

    if spec.value_type == "int_or_default":
        if value == PIPELINE_DEFAULT:
            return
        if not isinstance(value, int):
            raise ValueError(f"{key} must be int/{PIPELINE_DEFAULT}")
        _validate_scalar_with_bounds(float(value), spec=spec, key=key)
        return

    if spec.value_type == "int_map_or_default":
        if value == PIPELINE_DEFAULT:
            return
        if not isinstance(value, Mapping):
            raise ValueError(f"{key} must be map/{PIPELINE_DEFAULT}")
        _validate_map_int_int(value, spec=spec, key=key)
        return

    if spec.value_type == "dict_or_default":
        if value == PIPELINE_DEFAULT:
            return
        if not isinstance(value, Mapping):
            raise ValueError(f"{key} must be object/{PIPELINE_DEFAULT}")
        return

    raise ValueError(f"Unsupported knob value_type in catalog for {key}: {spec.value_type}")


def _validate_profile_overrides(
    overrides: Mapping[str, Any],
    *,
    allowed_keys: set[str],
    knob_ranges: KnobRangeCatalog,
) -> None:
    for key in overrides.keys():
        if str(key) not in allowed_keys:
            raise ValueError(f"override key not allowed: {key}")

    stage3 = overrides.get("stage3_gating")
    if isinstance(stage3, Mapping):
        for sub in ("full_entry_score", "probe_entry_score"):
            if sub in stage3:
                knob_key = f"stage3_gating.{sub}"
                spec = knob_ranges.get(knob_key)
                _validate_value_against_spec(stage3[sub], spec=spec, key=knob_key)

    carry = overrides.get("stage12_carry_through")
    if isinstance(carry, Mapping):
        for sub in ("promote_top", "archive_keep"):
            if sub in carry:
                knob_key = f"stage12_carry_through.{sub}"
                spec = knob_ranges.get(knob_key)
                _validate_value_against_spec(carry[sub], spec=spec, key=knob_key)

    stage1 = overrides.get("stage1_breadth")
    if isinstance(stage1, Mapping) and "sub_candidates_by_columns" in stage1:
        knob_key = "stage1_breadth.sub_candidates_by_columns"
        spec = knob_ranges.get(knob_key)
        _validate_value_against_spec(stage1.get("sub_candidates_by_columns"), spec=spec, key=knob_key)

    stage3_basin = overrides.get("stage3_basin_exploration")
    if isinstance(stage3_basin, Mapping) and "initial_keys_by_columns" in stage3_basin:
        knob_key = "stage3_basin_exploration.initial_keys_by_columns"
        spec = knob_ranges.get(knob_key)
        _validate_value_against_spec(stage3_basin.get("initial_keys_by_columns"), spec=spec, key=knob_key)

    for solver_key in ("solver_stage1", "solver_stage2", "solver_stage3"):
        if solver_key in overrides:
            spec = knob_ranges.get(solver_key)
            _validate_value_against_spec(overrides.get(solver_key), spec=spec, key=solver_key)


def load_profile_catalog_from_dict(
    profile_catalog: Mapping[str, Any],
    *,
    knob_ranges: KnobRangeCatalog | None = None,
) -> BenchmarkProfileCatalog:
    ranges = knob_ranges or load_knob_ranges()
    catalog_version = str(profile_catalog.get("catalog_version", "v1.1"))
    allowed_override_keys = tuple(
        str(x) for x in profile_catalog.get("allowed_override_keys", DEFAULT_ALLOWED_OVERRIDE_KEYS)
    )
    allowed_set = set(allowed_override_keys)
    profiles_raw = profile_catalog.get("profiles")
    if not isinstance(profiles_raw, list):
        raise ValueError("profile catalog missing profiles list")
    profiles_by_id: dict[str, BenchmarkProfile] = {}
    for item in profiles_raw:
        if not isinstance(item, Mapping):
            raise ValueError("profile row must be an object")
        profile_id = str(item.get("profile_id", "")).strip()
        if not profile_id:
            raise ValueError("profile missing profile_id")
        if profile_id in profiles_by_id:
            raise ValueError(f"duplicate profile_id in catalog: {profile_id}")
        description = str(item.get("description", ""))
        scorer_schedule = item.get("scorer_schedule", {})
        if not isinstance(scorer_schedule, Mapping):
            raise ValueError(f"profile {profile_id} scorer_schedule must be object")
        scorer_schedule_norm = validate_scorer_schedule_ids(
            scorer_schedule,
            require_all_keys=False,
        )
        overrides = item.get("overrides", {})
        if not isinstance(overrides, Mapping):
            raise ValueError(f"profile {profile_id} overrides must be object")
        _validate_profile_overrides(overrides, allowed_keys=allowed_set, knob_ranges=ranges)
        profiles_by_id[profile_id] = BenchmarkProfile(
            profile_id=profile_id,
            description=description,
            scorer_schedule=scorer_schedule_norm.as_dict(),
            overrides=dict(overrides),
        )

    return BenchmarkProfileCatalog(
        catalog_version=catalog_version,
        allowed_override_keys=allowed_override_keys,
        profiles_by_id=profiles_by_id,
        knob_ranges=ranges,
    )


def load_profile_catalog_from_path(
    path: Path,
    *,
    knob_ranges_path: Path | None = None,
) -> BenchmarkProfileCatalog:
    data = load_json(path)
    ranges = load_knob_ranges(knob_ranges_path)
    return load_profile_catalog_from_dict(data, knob_ranges=ranges)


def _apply_if_present(module: ModuleType, attr: str, value: Any) -> None:
    if hasattr(module, attr):
        setattr(module, attr, value)


def _is_pipeline_default(value: Any) -> bool:
    return value == PIPELINE_DEFAULT


def apply_profile_overrides_to_pipeline_module(module: ModuleType, profile: BenchmarkProfile) -> None:
    overrides = profile.overrides

    stage3_gating = overrides.get("stage3_gating")
    if isinstance(stage3_gating, Mapping):
        if "full_entry_score" in stage3_gating and not _is_pipeline_default(stage3_gating.get("full_entry_score")):
            _apply_if_present(module, "STAGE3_FULL_ENTRY_SCORE", stage3_gating.get("full_entry_score"))
        if "probe_entry_score" in stage3_gating and not _is_pipeline_default(stage3_gating.get("probe_entry_score")):
            _apply_if_present(module, "STAGE3_PROBE_ENTRY_SCORE", stage3_gating.get("probe_entry_score"))
        _apply_if_present(module, "STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS", {})
        _apply_if_present(module, "STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS", {})

    carry = overrides.get("stage12_carry_through")
    if isinstance(carry, Mapping):
        promote = carry.get("promote_top")
        if promote is not None and not _is_pipeline_default(promote):
            _apply_if_present(module, "STAGE12_PROMOTE_TOP", int(promote))
        archive = carry.get("archive_keep")
        if archive is not None and not _is_pipeline_default(archive):
            _apply_if_present(module, "STAGE12_ARCHIVE_KEEP", int(archive))

    stage1_breadth = overrides.get("stage1_breadth")
    if isinstance(stage1_breadth, Mapping):
        sub_by_c = stage1_breadth.get("sub_candidates_by_columns")
        if isinstance(sub_by_c, Mapping) and hasattr(module, "STAGE1_SUB_CANDIDATES_BY_COLUMNS"):
            current = dict(getattr(module, "STAGE1_SUB_CANDIDATES_BY_COLUMNS"))
            for key, value in sub_by_c.items():
                current[int(key)] = int(value)
            setattr(module, "STAGE1_SUB_CANDIDATES_BY_COLUMNS", current)

    stage3_basin = overrides.get("stage3_basin_exploration")
    if isinstance(stage3_basin, Mapping):
        init_by_c = stage3_basin.get("initial_keys_by_columns")
        if isinstance(init_by_c, Mapping) and hasattr(module, "STAGE3_INITIAL_KEYS_BY_COLUMNS"):
            current = dict(getattr(module, "STAGE3_INITIAL_KEYS_BY_COLUMNS"))
            for key, value in init_by_c.items():
                current[int(key)] = int(value)
            setattr(module, "STAGE3_INITIAL_KEYS_BY_COLUMNS", current)

    for key_name, attr in (
        ("solver_stage1", "SOLVER_STAGE1"),
        ("solver_stage2", "SOLVER_STAGE2"),
        ("solver_stage3", "SOLVER_STAGE3"),
    ):
        value = overrides.get(key_name)
        if isinstance(value, Mapping) and hasattr(module, attr):
            current = dict(getattr(module, attr))
            current.update(dict(value))
            setattr(module, attr, current)

