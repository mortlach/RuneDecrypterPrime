from __future__ import annotations

from enum import Enum


class BenchmarkOrder(str, Enum):
    COL_THEN_SUB = "col_then_sub"
    SUB_THEN_COL = "sub_then_col"


class PipelineRunMode(str, Enum):
    FULL = "full"
    FOCUS_SUB_THEN_COL = "focus_sub_then_col"
    FOCUS_P5_P7 = "focus_p5_p7"
    FOCUS_P10_FAST = "focus_p10_fast"
    FOCUS_P10_FAST_RESUME = "focus_p10_fast_resume"
    SMOKE = "smoke"


class StageABScorerProfile(str, Enum):
    A_CHAR1 = "A_char1"
    A_CHAR34 = "A_char34"
    A_CHAR34_WLI34 = "A_char34_wli34"


class InstanceStatus(str, Enum):
    SOLVED = "solved"
    STALLED = "stalled"
    UNSOLVED = "unsolved"
    SKIPPED_PROVEN = "skipped_proven"
    ERROR = "error"


class InstanceStopReason(str, Enum):
    AUTOSKIP_PROVEN = "autoskip_proven"
    COMPLETED_PIPELINE = "completed_pipeline"
    SOLVED_STAGE_B = "solved_stageB"
    SOLVED_STAGE_C = "solved_stageC"
    STALLED_NO_IMPROVE = "stalled_no_improve"
    UNSOLVED = "unsolved"
