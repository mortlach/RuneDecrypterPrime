from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    export_scorer_component_inventory_v1 as inventory_mod,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.export_scorer_component_inventory_v1 import (
    ALLOWED_REUSE_RECOMMENDATIONS,
    REQUIRED_FIELDS,
    build_inventory_rows,
    summarize_inventory,
    write_inventory_outputs,
)


pytestmark = pytest.mark.tier_a


def _component(**overrides):
    row = {
        "component_id": "demo_component",
        "component_name": "Demo component",
        "source_project": "current_rdp",
        "source_path": "src/rune_decrypter_prime/scoring/rune_scorer.py",
        "component_type": "char_ngram",
        "input_type": "runes",
        "output_type": "score",
        "needs_plaintext": 1,
        "needs_runes": 1,
        "needs_spaces": 0,
        "needs_word_boundaries": 0,
        "uses_truth_or_oracle": 0,
        "runtime_safe": 1,
        "inner_loop_safe": 1,
        "reranker_safe": 1,
        "final_judge_safe": 1,
        "expected_text_length": "short",
        "known_failure_mode_addressed": "demo",
        "known_failure_mode_created": "none",
        "test_file_paths": "tests/scoring/test_scorer_report_builder.py",
        "has_tests": 1,
        "evidence_paths": "src/rune_decrypter_prime/scoring/rune_scorer.py",
        "reuse_recommendation": "reuse_directly",
        "notes": "demo",
        "deterministic_outputs": 1,
    }
    row.update(overrides)
    return row


def test_inventory_rows_contain_required_fields_and_allowed_reuse_values() -> None:
    rows = build_inventory_rows()

    assert rows
    for row in rows:
        assert set(REQUIRED_FIELDS).issubset(row)
        assert str(row["reuse_recommendation"]) in ALLOWED_REUSE_RECOMMENDATIONS


def test_runtime_safe_components_cannot_use_truth_or_oracle_fields() -> None:
    with pytest.raises(ValueError, match="runtime_safe component uses truth/oracle"):
        build_inventory_rows([_component(uses_truth_or_oracle=1, runtime_safe=1)])


def test_inner_loop_safe_components_must_have_deterministic_outputs() -> None:
    with pytest.raises(ValueError, match="inner_loop_safe component is not deterministic"):
        build_inventory_rows([_component(inner_loop_safe=1, deterministic_outputs=0)])


def test_summary_counts_match_rows() -> None:
    rows = build_inventory_rows(
        [
            _component(component_id="direct", reuse_recommendation="reuse_directly"),
            _component(
                component_id="report",
                runtime_safe=0,
                inner_loop_safe=0,
                reuse_recommendation="reuse_as_report_feature",
            ),
            _component(
                component_id="unknown",
                source_project="external_pending",
                test_file_paths="",
                has_tests=0,
                reuse_recommendation="unknown_pending_review",
            ),
        ]
    )

    summary = summarize_inventory(rows)

    assert int(summary["component_count"]) == len(rows)
    assert int(summary["reuse_directly_count"]) == 1
    assert int(summary["reuse_as_report_feature_count"]) == 1
    assert int(summary["unknown_pending_review_count"]) == 1
    assert int(summary["components_with_tests_count"]) == 2
    assert int(summary["components_missing_tests_count"]) == 1


def test_missing_test_paths_are_reported_clearly() -> None:
    rows = build_inventory_rows(
        [
            _component(
                test_file_paths="tests/does_not_exist_for_inventory_v1.py",
                has_tests=0,
            )
        ]
    )

    assert int(rows[0]["has_tests"]) == 0
    assert rows[0]["missing_test_file_paths"] == "tests/does_not_exist_for_inventory_v1.py"


def test_unknown_components_are_allowed_when_marked_pending() -> None:
    rows = build_inventory_rows(
        [
            _component(
                component_id="pending_external",
                source_project="external_pending",
                source_path="../missing_external_source",
                test_file_paths="",
                has_tests=0,
                reuse_recommendation="unknown_pending_review",
                runtime_safe=0,
                inner_loop_safe=0,
            )
        ]
    )

    assert rows[0]["reuse_recommendation"] == "unknown_pending_review"


def test_write_inventory_outputs_uses_expected_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inventory_mod, "REPO_ROOT", tmp_path)
    rows = build_inventory_rows([_component()])
    out_dir = tmp_path / "scorer_component_inventory_v1"

    summary = write_inventory_outputs(rows=rows, output_dir=out_dir)

    assert int(summary["component_count"]) == 1
    assert (out_dir / "scorer_component_inventory_rows.csv").exists()
    assert (out_dir / "scorer_component_inventory_rows.jsonl").exists()
    assert (out_dir / "scorer_component_inventory_summary.json").exists()
    assert (out_dir / "scorer_component_inventory_readout.md").exists()
