from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli import (
    analyze_phasec_slice_signals as analyze_mod,
    artifact_resume as artifact_resume_mod,
    profile_word_ngram_tiebreak as profile_mod,
    replay_phasec_rescue_sweep as replay_mod,
    replay_stage35_substitution_solver as stage35_mod,
)


def test_offline_no_wli_output_roots_are_repo_anchored() -> None:
    cases = (
        (artifact_resume_mod, "artifact_resume"),
        (analyze_mod, "phasec_slice_signal_analysis"),
        (profile_mod, "word_ngram_tiebreak_profile"),
        (replay_mod, "phasec_rescue_replay"),
        (stage35_mod, "stage35_substitution_replay"),
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
