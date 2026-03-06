from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


# Legacy community IDs (kept for compatibility with existing v1.1 profile catalog).
SCHEDULE_EARLY_DEFAULT = "stage1_default_char1_only"
SCHEDULE_EARLY_CHAR34_ONLY = "stage1_char34_only"
SCHEDULE_MIDDLE_DEFAULT = "stage2_default_mixed"
SCHEDULE_MIDDLE_CHAR34_ONLY = "stage2_char34_only"
SCHEDULE_LATE_DEFAULT = "stage3_default_mixed"
SCHEDULE_LATE_CHAR34_ONLY = "stage3_char34_only"

# no-WLI adaptive schedule prototype IDs (A/M/B labels).
SCHEDULE_EARLY_A_CHAR1 = "a_char1"
SCHEDULE_EARLY_A_CHAR34 = "a_char34"
SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT = "a_char1_avg_fulltext"
SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT = "a_char2_avg_fulltext"

SCHEDULE_MIDDLE_M_CHAR12 = "m_char12"
SCHEDULE_MIDDLE_M_CHAR34 = "m_char34"
SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT = "m_char12_avg_fulltext"
SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT = "m_char4_avg_fulltext"

SCHEDULE_LATE_B_CHAR34 = "b_char34"
SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT = "b_char4_avg_fulltext"

SCORER_SCHEDULE_ID_CATALOG: dict[str, frozenset[str]] = {
    "early": frozenset(
        {
            SCHEDULE_EARLY_DEFAULT,
            SCHEDULE_EARLY_CHAR34_ONLY,
            SCHEDULE_EARLY_A_CHAR1,
            SCHEDULE_EARLY_A_CHAR34,
            SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
            SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT,
        }
    ),
    "middle": frozenset(
        {
            SCHEDULE_MIDDLE_DEFAULT,
            SCHEDULE_MIDDLE_CHAR34_ONLY,
            SCHEDULE_MIDDLE_M_CHAR12,
            SCHEDULE_MIDDLE_M_CHAR34,
            SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
            SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT,
        }
    ),
    "late": frozenset(
        {
            SCHEDULE_LATE_DEFAULT,
            SCHEDULE_LATE_CHAR34_ONLY,
            SCHEDULE_LATE_B_CHAR34,
            SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
        }
    ),
}


@dataclass(frozen=True)
class ScorerScheduleDTO:
    """Canonical scorer-schedule object shared across campaign runners."""

    early: str
    middle: str
    late: str

    def as_dict(self) -> dict[str, str]:
        return {
            "early": str(self.early),
            "middle": str(self.middle),
            "late": str(self.late),
        }


DEFAULT_SCORER_SCHEDULE = ScorerScheduleDTO(
    early=SCHEDULE_EARLY_DEFAULT,
    middle=SCHEDULE_MIDDLE_DEFAULT,
    late=SCHEDULE_LATE_DEFAULT,
)


def _normalize_schedule_id(*, value: Any, key: str, default: str) -> str:
    text = default if value is None else str(value).strip().lower()
    if not text:
        raise ValueError(f"scorer_schedule.{key} must be a non-empty string")
    return text


def parse_scorer_schedule(raw: Mapping[str, Any] | None) -> ScorerScheduleDTO:
    """Parse profile/config scorer_schedule into one shared DTO shape."""

    if raw is None:
        return DEFAULT_SCORER_SCHEDULE
    if not isinstance(raw, Mapping):
        raise ValueError("scorer_schedule must be an object mapping")
    return ScorerScheduleDTO(
        early=_normalize_schedule_id(
            value=raw.get("early"),
            key="early",
            default=DEFAULT_SCORER_SCHEDULE.early,
        ),
        middle=_normalize_schedule_id(
            value=raw.get("middle"),
            key="middle",
            default=DEFAULT_SCORER_SCHEDULE.middle,
        ),
        late=_normalize_schedule_id(
            value=raw.get("late"),
            key="late",
            default=DEFAULT_SCORER_SCHEDULE.late,
        ),
    )


def validate_scorer_schedule_ids(
    raw: Mapping[str, Any] | None,
    *,
    require_all_keys: bool = False,
) -> ScorerScheduleDTO:
    """Validate scorer_schedule IDs against the canonical catalog."""

    if raw is None:
        schedule = DEFAULT_SCORER_SCHEDULE
        supplied_keys: set[str] = set()
    else:
        if not isinstance(raw, Mapping):
            raise ValueError("scorer_schedule must be an object mapping")
        supplied_keys = {str(k) for k in raw.keys()}
        unknown_keys = sorted(k for k in supplied_keys if k not in SCORER_SCHEDULE_ID_CATALOG)
        if unknown_keys:
            allowed = ", ".join(sorted(SCORER_SCHEDULE_ID_CATALOG.keys()))
            raise ValueError(
                f"scorer_schedule has unknown keys: {', '.join(unknown_keys)}; allowed keys: {allowed}"
            )
        if require_all_keys:
            missing = [k for k in ("early", "middle", "late") if k not in supplied_keys]
            if missing:
                raise ValueError(
                    f"scorer_schedule missing required keys: {', '.join(missing)}"
                )
        schedule = parse_scorer_schedule(raw)

    checks = (
        ("early", schedule.early),
        ("middle", schedule.middle),
        ("late", schedule.late),
    )
    for key, value in checks:
        allowed_ids = SCORER_SCHEDULE_ID_CATALOG[key]
        if value not in allowed_ids:
            raise ValueError(
                f"unknown scorer_schedule.{key} id={value!r}; "
                f"allowed: {', '.join(sorted(allowed_ids))}"
            )
    return schedule
