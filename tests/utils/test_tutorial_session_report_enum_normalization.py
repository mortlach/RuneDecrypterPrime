from __future__ import annotations

from types import SimpleNamespace

from rune_decrypter_prime.utils.tutorial_benchmark import TutorialStopPolicy
from rune_decrypter_prime.utils.tutorial_reference import TutorialReference
from rune_decrypter_prime.utils.tutorial_session_report import build_tutorial_session_report


def test_session_report_accepts_string_run_kind_and_reference_policy() -> None:
    solution = SimpleNamespace(key=[3, 1, 4], plaintext_idx=[1, 2, 3], meta={})
    reference = TutorialReference(truth_policy="known_key_and_plaintext", key_idx=[3, 1, 4], plaintext_idx=[1, 2, 3])

    report = build_tutorial_session_report(
        title="demo",
        cipher="scheduled_stream_lookup",
        solution=solution,
        reference=reference,
        run_kind="real_key_recovery_benchmark",
        stop_policy=TutorialStopPolicy(),
    )

    assert report["benchmark"]["run_kind"] == "real_key_recovery_benchmark"
    assert report["benchmark"]["truth_policy"] == "known_key_and_plaintext"
    assert report["match_ratio"] == 1.0
    assert report["key"]["exact"] is True
