from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli import (
    artifact_resume as artifact_resume_mod,
    replay_phasec_rescue_sweep as replay_mod,
    replay_stage35_substitution_solver as stage35_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    analyze_phasec_slice_signals as analyze_mod,
    profile_word_ngram_tiebreak as profile_mod,
    profile_stage35_replay_hotspots as stage35_profile_mod,
    sweep_stage35_replay_configs as stage35_sweep_mod,
)


def test_offline_no_wli_output_roots_are_repo_anchored() -> None:
    cases = (
        (artifact_resume_mod, "artifact_resume"),
        (analyze_mod, "phasec_slice_signal_analysis"),
        (profile_mod, "word_ngram_tiebreak_profile"),
        (stage35_profile_mod, "stage35_replay_profile"),
        (replay_mod, "phasec_rescue_replay"),
        (stage35_mod, "stage35_substitution_replay"),
        (stage35_sweep_mod, "stage35_replay_sweep"),
    )
    for module, leaf in cases:
        expected = (
            module.REPO_ROOT
            / "output"
            / "tools"
            / "benchmarks"
            / "periodic_sub_trans"
            / "no_wli"
            / leaf
        )
        assert module.OUTPUT_ROOT == expected
        assert module.OUTPUT_ROOT.is_absolute()
