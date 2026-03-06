from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCHEDULE_EARLY_CHAR34_ONLY,
    SCHEDULE_LATE_CHAR34_ONLY,
    SCHEDULE_MIDDLE_CHAR34_ONLY,
    SCHEDULE_MIDDLE_M_CHAR12,
)
from tools.benchmarks.periodic_sub_trans.common.scorer_schedule_apply import (
    apply_col_then_sub_schedule,
    apply_no_wli_schedule,
    apply_sub_then_col_schedule,
)


pytestmark = pytest.mark.tier_a


def test_apply_col_then_sub_schedule_char34_only():
    stage1 = {"objective": "pct.logp.win10", "char_weights": {1: 1.0}, "use_word_breaks": False, "wli_weights": {}}
    stage_full = {
        "objective": "pct.logp.win10",
        "char_weights": {3: 0.3, 4: 0.7},
        "use_word_breaks": True,
        "wli_weights": {3: 0.4, 4: 0.6},
    }
    apply_col_then_sub_schedule(
        scorer_schedule={
            "early": SCHEDULE_EARLY_CHAR34_ONLY,
            "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
            "late": SCHEDULE_LATE_CHAR34_ONLY,
        },
        stage1_cfg=stage1,
        stage_full_cfg=stage_full,
    )
    assert stage1["char_weights"] == {3: 0.2, 4: 0.8}
    assert stage1["use_word_breaks"] is False
    assert stage_full["char_weights"] == {3: 0.2, 4: 0.8}
    assert stage_full["use_word_breaks"] is False
    assert stage_full["wli_weights"] == {}


def test_apply_sub_then_col_schedule_returns_profile_and_applies_late():
    stage_full = {
        "objective": "pct.logp.win10",
        "char_weights": {3: 0.3, 4: 0.7},
        "use_word_breaks": True,
        "wli_weights": {3: 0.4, 4: 0.6},
    }
    profile = apply_sub_then_col_schedule(
        scorer_schedule={
            "early": SCHEDULE_EARLY_CHAR34_ONLY,
            "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
            "late": SCHEDULE_LATE_CHAR34_ONLY,
        },
        stage_full_cfg=stage_full,
        stageab_profile_default="A_char34_wli34",
        stageab_profile_char34="A_char34",
    )
    assert profile == "A_char34"
    assert stage_full["char_weights"] == {3: 0.3, 4: 0.7}
    assert stage_full["use_word_breaks"] is False
    assert stage_full["wli_weights"] == {}


def test_apply_sub_then_col_schedule_rejects_mismatched_pair():
    stage_full = {
        "objective": "pct.logp.win10",
        "char_weights": {3: 0.3, 4: 0.7},
        "use_word_breaks": True,
        "wli_weights": {3: 0.4, 4: 0.6},
    }
    with pytest.raises(ValueError, match="compatible pair"):
        apply_sub_then_col_schedule(
            scorer_schedule={
                "early": SCHEDULE_EARLY_CHAR34_ONLY,
                "middle": "stage2_default_mixed",
                "late": "stage3_default_mixed",
            },
            stage_full_cfg=stage_full,
            stageab_profile_default="A_char34_wli34",
            stageab_profile_char34="A_char34",
        )


def test_apply_col_then_sub_schedule_rejects_m_char12_alias():
    stage1 = {"objective": "pct.logp.win10", "char_weights": {1: 1.0}, "use_word_breaks": False, "wli_weights": {}}
    stage_full = {
        "objective": "pct.logp.win10",
        "char_weights": {3: 0.3, 4: 0.7},
        "use_word_breaks": True,
        "wli_weights": {3: 0.4, 4: 0.6},
    }
    with pytest.raises(ValueError, match="no char1/2-only stage2 equivalent"):
        apply_col_then_sub_schedule(
            scorer_schedule={
                "early": "stage1_default_char1_only",
                "middle": SCHEDULE_MIDDLE_M_CHAR12,
                "late": "stage3_default_mixed",
            },
            stage1_cfg=stage1,
            stage_full_cfg=stage_full,
        )


def test_apply_sub_then_col_schedule_rejects_m_char12_alias():
    stage_full = {
        "objective": "pct.logp.win10",
        "char_weights": {3: 0.3, 4: 0.7},
        "use_word_breaks": True,
        "wli_weights": {3: 0.4, 4: 0.6},
    }
    with pytest.raises(ValueError, match="no char1/2-only stageAB equivalent"):
        apply_sub_then_col_schedule(
            scorer_schedule={
                "early": "stage1_default_char1_only",
                "middle": SCHEDULE_MIDDLE_M_CHAR12,
                "late": "stage3_default_mixed",
            },
            stage_full_cfg=stage_full,
            stageab_profile_default="A_char34_wli34",
            stageab_profile_char34="A_char34",
        )


def test_apply_no_wli_schedule_returns_labels_and_applies_char34():
    stage1 = {"objective": "pct.logp.win10", "char_weights": {1: 1.0}, "use_word_breaks": False, "wli_weights": {}}
    stage2 = {"objective": "pct.logp.win10", "char_weights": {1: 0.4, 2: 0.6}, "use_word_breaks": False, "wli_weights": {}}
    stage3 = {"objective": "pct.logp.win10", "char_weights": {3: 0.2, 4: 0.8}, "use_word_breaks": False, "wli_weights": {}}
    labels = apply_no_wli_schedule(
        scorer_schedule={
            "early": SCHEDULE_EARLY_CHAR34_ONLY,
            "middle": SCHEDULE_MIDDLE_CHAR34_ONLY,
            "late": SCHEDULE_LATE_CHAR34_ONLY,
        },
        stage1_cfg=stage1,
        stage2_cfg=stage2,
        stage3_cfg=stage3,
    )
    assert labels.stage1_label == "A_char34"
    assert labels.stage2_label == "M_char34"
    assert labels.stage3_label == "B_char34"
    assert stage1["char_weights"] == {3: 0.2, 4: 0.8}
    assert stage2["char_weights"] == {3: 0.2, 4: 0.8}
    assert stage3["char_weights"] == {3: 0.2, 4: 0.8}
