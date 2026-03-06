from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .scorer_schedule import (
    SCHEDULE_EARLY_CHAR34_ONLY,
    SCHEDULE_EARLY_DEFAULT,
    SCHEDULE_EARLY_A_CHAR1,
    SCHEDULE_EARLY_A_CHAR34,
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT,
    SCHEDULE_LATE_CHAR34_ONLY,
    SCHEDULE_LATE_DEFAULT,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_CHAR34_ONLY,
    SCHEDULE_MIDDLE_DEFAULT,
    SCHEDULE_MIDDLE_M_CHAR12,
    SCHEDULE_MIDDLE_M_CHAR34,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT,
    parse_scorer_schedule,
)


def apply_col_then_sub_schedule(
    *,
    scorer_schedule: Mapping[str, Any] | None,
    stage1_cfg: dict[str, Any],
    stage_full_cfg: dict[str, Any],
) -> None:
    schedule = parse_scorer_schedule(scorer_schedule)
    early_default_ids = {SCHEDULE_EARLY_DEFAULT, SCHEDULE_EARLY_A_CHAR1}
    early_char34_ids = {SCHEDULE_EARLY_CHAR34_ONLY, SCHEDULE_EARLY_A_CHAR34}
    middle_default_ids = {SCHEDULE_MIDDLE_DEFAULT}
    middle_char34_ids = {SCHEDULE_MIDDLE_CHAR34_ONLY, SCHEDULE_MIDDLE_M_CHAR34}
    late_default_ids = {SCHEDULE_LATE_DEFAULT}
    late_char34_ids = {SCHEDULE_LATE_CHAR34_ONLY, SCHEDULE_LATE_B_CHAR34}

    if schedule.early in early_default_ids:
        pass
    elif schedule.early in early_char34_ids:
        stage1_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={},
        )
    else:
        raise ValueError(f"unsupported col_then_sub scorer_schedule.early={schedule.early!r}")

    middle_default = schedule.middle in middle_default_ids
    middle_char34 = schedule.middle in middle_char34_ids
    late_default = schedule.late in late_default_ids
    late_char34 = schedule.late in late_char34_ids

    if middle_default and late_default:
        return
    if middle_char34 and late_char34:
        stage_full_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={},
        )
        return

    if schedule.middle == SCHEDULE_MIDDLE_M_CHAR12:
        raise ValueError(
            "unsupported col_then_sub scorer_schedule.middle='m_char12': "
            "runner has no char1/2-only stage2 equivalent"
        )
    if not (middle_default or middle_char34):
        raise ValueError(f"unsupported col_then_sub scorer_schedule.middle={schedule.middle!r}")
    if not (late_default or late_char34):
        raise ValueError(f"unsupported col_then_sub scorer_schedule.late={schedule.late!r}")
    raise ValueError(
        "col_then_sub uses one stage2/stage3 scorer config; "
        "scorer_schedule.middle and scorer_schedule.late must select the same family"
    )


def apply_sub_then_col_schedule(
    *,
    scorer_schedule: Mapping[str, Any] | None,
    stage_full_cfg: dict[str, Any],
    stageab_profile_default: str,
    stageab_profile_char34: str,
) -> str:
    schedule = parse_scorer_schedule(scorer_schedule)
    early_default_ids = {SCHEDULE_EARLY_DEFAULT, SCHEDULE_EARLY_A_CHAR1}
    early_char34_ids = {SCHEDULE_EARLY_CHAR34_ONLY, SCHEDULE_EARLY_A_CHAR34}
    middle_default_ids = {SCHEDULE_MIDDLE_DEFAULT}
    middle_char34_ids = {SCHEDULE_MIDDLE_CHAR34_ONLY, SCHEDULE_MIDDLE_M_CHAR34}
    late_default_ids = {SCHEDULE_LATE_DEFAULT}
    late_char34_ids = {SCHEDULE_LATE_CHAR34_ONLY, SCHEDULE_LATE_B_CHAR34}

    if schedule.early in early_default_ids and schedule.middle in middle_default_ids:
        stageab_profile = str(stageab_profile_default)
    elif schedule.early in early_char34_ids and schedule.middle in middle_char34_ids:
        stageab_profile = str(stageab_profile_char34)
    else:
        if schedule.early not in early_default_ids.union(early_char34_ids):
            raise ValueError(f"unsupported sub_then_col scorer_schedule.early={schedule.early!r}")
        if schedule.middle == SCHEDULE_MIDDLE_M_CHAR12:
            raise ValueError(
                "unsupported sub_then_col scorer_schedule.middle='m_char12': "
                "runner has no char1/2-only stageAB equivalent"
            )
        if schedule.middle not in middle_default_ids.union(middle_char34_ids):
            raise ValueError(f"unsupported sub_then_col scorer_schedule.middle={schedule.middle!r}")
        raise ValueError(
            "sub_then_col shares a single stageAB scorer profile; "
            "scorer_schedule.early and scorer_schedule.middle must use a compatible pair"
        )

    if schedule.late in late_default_ids:
        return stageab_profile
    if schedule.late in late_char34_ids:
        stage_full_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.3, 4: 0.7},
            wli_weights={},
        )
        return stageab_profile
    raise ValueError(f"unsupported sub_then_col scorer_schedule.late={schedule.late!r}")


@dataclass(frozen=True)
class NoWliScorerLabels:
    stage1_label: str | None = None
    stage2_label: str | None = None
    stage3_label: str | None = None


def apply_no_wli_schedule(
    *,
    scorer_schedule: Mapping[str, Any] | None,
    stage1_cfg: dict[str, Any],
    stage2_cfg: dict[str, Any],
    stage3_cfg: dict[str, Any],
) -> NoWliScorerLabels:
    schedule = parse_scorer_schedule(scorer_schedule)
    labels = NoWliScorerLabels()

    if schedule.early in {SCHEDULE_EARLY_DEFAULT, SCHEDULE_EARLY_A_CHAR1}:
        pass
    elif schedule.early in {SCHEDULE_EARLY_CHAR34_ONLY, SCHEDULE_EARLY_A_CHAR34}:
        labels = NoWliScorerLabels(
            stage1_label="A_char34",
            stage2_label=labels.stage2_label,
            stage3_label=labels.stage3_label,
        )
        stage1_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={},
        )
    elif schedule.early == SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT:
        labels = NoWliScorerLabels(
            stage1_label="A_char1_avg_fulltext",
            stage2_label=labels.stage2_label,
            stage3_label=labels.stage3_label,
        )
        stage1_cfg.update(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={1: 1.0},
            wli_weights={},
            avg_window_policy="full_text",
        )
    elif schedule.early == SCHEDULE_EARLY_A_CHAR2_AVG_FULLTEXT:
        labels = NoWliScorerLabels(
            stage1_label="A_char2_avg_fulltext",
            stage2_label=labels.stage2_label,
            stage3_label=labels.stage3_label,
        )
        stage1_cfg.update(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={2: 1.0},
            wli_weights={},
            avg_window_policy="full_text",
        )
    else:
        raise ValueError(f"unsupported no_wli scorer_schedule.early={schedule.early!r}")

    if schedule.middle == SCHEDULE_MIDDLE_DEFAULT:
        pass
    elif schedule.middle == SCHEDULE_MIDDLE_M_CHAR12:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label="M_char12",
            stage3_label=labels.stage3_label,
        )
        stage2_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={1: 0.4, 2: 0.6},
            wli_weights={},
        )
    elif schedule.middle in {SCHEDULE_MIDDLE_CHAR34_ONLY, SCHEDULE_MIDDLE_M_CHAR34}:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label="M_char34",
            stage3_label=labels.stage3_label,
        )
        stage2_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={},
        )
    elif schedule.middle == SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label="M_char12_avg_fulltext",
            stage3_label=labels.stage3_label,
        )
        stage2_cfg.update(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={1: 0.4, 2: 0.6},
            wli_weights={},
            avg_window_policy="full_text",
        )
    elif schedule.middle == SCHEDULE_MIDDLE_M_CHAR4_AVG_FULLTEXT:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label="M_char4_avg_fulltext",
            stage3_label=labels.stage3_label,
        )
        stage2_cfg.update(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            avg_window_policy="full_text",
        )
    else:
        raise ValueError(f"unsupported no_wli scorer_schedule.middle={schedule.middle!r}")

    if schedule.late == SCHEDULE_LATE_DEFAULT:
        return labels
    if schedule.late in {SCHEDULE_LATE_CHAR34_ONLY, SCHEDULE_LATE_B_CHAR34}:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label=labels.stage2_label,
            stage3_label="B_char34",
        )
        stage3_cfg.update(
            objective="pct.logp.win10",
            include_char=True,
            use_word_breaks=False,
            char_weights={3: 0.2, 4: 0.8},
            wli_weights={},
        )
        return labels
    if schedule.late == SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT:
        labels = NoWliScorerLabels(
            stage1_label=labels.stage1_label,
            stage2_label=labels.stage2_label,
            stage3_label="B_char4_avg_fulltext",
        )
        stage3_cfg.update(
            objective="avg.logp.win20",
            include_char=True,
            use_word_breaks=False,
            char_weights={4: 1.0},
            wli_weights={},
            avg_window_policy="full_text",
        )
        return labels
    raise ValueError(f"unsupported no_wli scorer_schedule.late={schedule.late!r}")
