from __future__ import annotations
from rdp import api
import os
from rune_decrypter_prime.scoring.scorer_lane_report import build_scorer_lane_report


def test_scorer_lane_report_sections_are_stable_public_labels() -> None:
    report = build_scorer_lane_report(api.ScoringConfig())
    assert [lane.report_section for lane in report.lanes] == [
        "language_model_character_and_word_length",
        "hamming_dictionary",
        "span_hamming_raw",
        "span_hamming_calibrated",
        "word_ngram_judge",
        "ngram_hamming_experimental",
    ]


def test_scorer_lane_report_json_contains_no_absolute_paths() -> None:
    payload = build_scorer_lane_report(api.ScoringConfig()).to_json_dict()
    for lane in payload["lanes"]:
        section = lane.get("report_section")
        if section is not None:
            assert not os.path.isabs(section)
            assert "/" not in section
            assert "\\" not in section
        for issue in lane.get("issues", []):
            source = issue.get("source")
            if source is not None:
                assert not os.path.isabs(source)
