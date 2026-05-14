from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_runeberg_nose_damage_ladder_v1 as runner,
)


RUN_LABEL = "stage2_fwd_full_len2_14_pc_a"
RUN_MODE = "stage2_fwd_full_len2_14"
CHUNK_START_INDEX = 1000
NUM_CLEAN_CHUNKS_THIS_RUN = 4200
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "stage2_fwd_full_len2_14_pc_a"
)
LOG_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/logs/"
    "stage2_fwd_full_len2_14_pc_a.log"
)
LADDER_PROFILE = "v0_3_plus_long_relaxed_v2_len2_14"
ACTIVE_SPAN_LENGTHS = tuple(range(2, 15))


class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, text: str) -> int:
        for stream in self.streams:
            stream.write(text)
            stream.flush()
        return len(text)

    def flush(self) -> None:
        for stream in self.streams:
            stream.flush()


def configure() -> None:
    runner.RUN_LABEL = RUN_LABEL
    runner.RUN_MODE = RUN_MODE
    runner.CHUNK_START_INDEX = CHUNK_START_INDEX
    runner.OUTPUT_DIR_REL = OUTPUT_DIR_REL
    runner.LADDER_PROFILE = LADDER_PROFILE
    runner.SPAN_LENGTHS = ACTIVE_SPAN_LENGTHS
    runner.BASELINE_V0_3_RUNG_COUNT = sum(
        runner.BASELINE_V0_3_MAX_HD_BY_LENGTH[length] + 1 for length in runner.SPAN_LENGTHS
    )
    runner.TOTAL_LADDER_RUNG_COUNT = sum(
        runner.MAX_HD_BY_LENGTH[length] + 1 for length in runner.SPAN_LENGTHS
    )
    runner.EXTRA_EXPERIMENTAL_RUNG_COUNT = (
        runner.TOTAL_LADDER_RUNG_COUNT - runner.BASELINE_V0_3_RUNG_COUNT
    )
    runner.DIRECTIONS_BY_MODE[RUN_MODE] = ("fwd",)
    runner.SCORE_REGIONS_BY_MODE[RUN_MODE] = ("full",)
    runner.START_VIEW_SHIFTS_BY_MODE[RUN_MODE] = (0,)
    if RUN_MODE not in runner.WRITE_FEATURE_HISTOGRAMS_MODES:
        runner.WRITE_FEATURE_HISTOGRAMS_MODES = (*runner.WRITE_FEATURE_HISTOGRAMS_MODES, RUN_MODE)
    if RUN_MODE not in runner.WRITE_FEATURE_QUANTILES_MODES:
        runner.WRITE_FEATURE_QUANTILES_MODES = (*runner.WRITE_FEATURE_QUANTILES_MODES, RUN_MODE)
    runner.MODE_LIMITS[RUN_MODE] = {
        **runner.MODE_LIMITS["stage1_fwd_full_1k"],
        "num_clean_chunks": NUM_CLEAN_CHUNKS_THIS_RUN,
        "max_books": 510,
        "checkpoint_every_samples": 500,
        "checkpoint_every_seconds": 300.0,
    }


def main() -> None:
    configure()
    log_path = runner._resolve_from_repo_root(LOG_REL)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log_fh:

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = Tee(sys.__stdout__, log_fh)
            sys.stderr = Tee(sys.__stderr__, log_fh)
            print(
                f"[{RUN_LABEL}] configured CHUNK_START_INDEX={CHUNK_START_INDEX} "
                f"NUM_CLEAN_CHUNKS_THIS_RUN={NUM_CLEAN_CHUNKS_THIS_RUN} "
                f"LADDER_PROFILE={LADDER_PROFILE} active_lengths={ACTIVE_SPAN_LENGTHS}",
                flush=True,
            )
            runner.run_once()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr



if __name__ == "__main__":
    main()
