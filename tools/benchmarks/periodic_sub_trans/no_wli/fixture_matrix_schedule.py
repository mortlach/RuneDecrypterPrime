from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


def build_schedule_matrix(
    *,
    mode: str,
    explicit_schedules: Sequence[Mapping[str, Any]] | None,
    scorer_schedule_id_catalog: Mapping[str, Sequence[str]],
    schedule_early_a_char1: str,
    schedule_middle_m_char12: str,
    schedule_late_b_char34: str,
    schedule_early_default: str,
    schedule_early_a_char1_avg_fulltext: str,
    schedule_early_a_char2_avg_fulltext: str,
    schedule_middle_default: str,
    schedule_middle_m_char12_avg_fulltext: str,
    schedule_middle_m_char4_avg_fulltext: str,
    schedule_late_default: str,
    schedule_late_b_char4_avg_fulltext: str,
    validate_scorer_schedule_ids_fn: Callable[..., Any],
) -> list[dict[str, str]]:
    m = str(mode).strip().lower()
    early_ids = sorted(scorer_schedule_id_catalog["early"])
    middle_ids = sorted(scorer_schedule_id_catalog["middle"])
    late_ids = sorted(scorer_schedule_id_catalog["late"])

    rows: list[dict[str, str]] = []
    if m == "cartesian_all":
        for early in early_ids:
            for middle in middle_ids:
                for late in late_ids:
                    rows.append(dict(early=str(early), middle=str(middle), late=str(late)))
    elif m == "minimal_all_ids":
        base = dict(
            early=str(schedule_early_a_char1),
            middle=str(schedule_middle_m_char12),
            late=str(schedule_late_b_char34),
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
            str(schedule_early_default),
            str(schedule_early_a_char1),
            str(schedule_early_a_char1_avg_fulltext),
            str(schedule_early_a_char2_avg_fulltext),
        )
        middle_avg_ids = (
            str(schedule_middle_default),
            str(schedule_middle_m_char12_avg_fulltext),
            str(schedule_middle_m_char4_avg_fulltext),
        )
        late_avg_ids = (
            str(schedule_late_default),
            str(schedule_late_b_char4_avg_fulltext),
        )
        base = dict(
            early=str(schedule_early_a_char1_avg_fulltext),
            middle=str(schedule_middle_m_char12_avg_fulltext),
            late=str(schedule_late_b_char4_avg_fulltext),
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
        norm = validate_scorer_schedule_ids_fn(row, require_all_keys=True)
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
    get_profile_fn: Callable[[str], Any],
    apply_no_wli_schedule_fn: Callable[..., None],
) -> dict[str, dict[str, str]]:
    profile = get_profile_fn(str(profile_id))
    stage1 = profile.scorer_schedule.stage1_a.to_params()
    stage2 = profile.scorer_schedule.stage2_m.to_params()
    stage3 = profile.scorer_schedule.stage3_b.to_params()
    apply_no_wli_schedule_fn(
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
    resolve_stage_objectives_for_schedule_fn: Callable[..., dict[str, dict[str, str]]],
    require_no_win10_objectives: bool,
    require_full_text_effective: bool,
) -> None:
    scoring = resolve_stage_objectives_for_schedule_fn(
        profile_id=str(profile_id),
        schedule=schedule,
    )
    if bool(require_no_win10_objectives):
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
    if bool(require_full_text_effective):
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
