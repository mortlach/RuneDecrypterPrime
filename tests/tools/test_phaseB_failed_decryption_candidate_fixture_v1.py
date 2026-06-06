from __future__ import annotations

import csv
import json

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_retained_candidate_fixture_v1 as fixture,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    validate_phaseB_failed_decryption_retained_candidate_fixture_v1 as validation,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_fixture_n3c_report_telemetry_v1 as telemetry,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    build_phaseB_failed_decryption_candidate_inventory_v1 as inventory,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    assess_phaseB_failed_decryption_full_runtime_n3c_query_readiness_v1 as readiness,
)


def test_completed_inventory_is_source_backed_and_rank_neutral() -> None:
    manifest = json.loads((inventory.OUTPUT_DIR / "inventory_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "pass"
    assert manifest["parse_failure_count"] == 0
    assert manifest["selected_artifact_count"] == 2
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False


def test_full_runtime_readiness_blocks_naive_scan() -> None:
    manifest = readiness.assess_readiness()

    assert manifest["status"] == "blocked_requires_candidate_keyed_query"
    assert manifest["runtime_validation_status"] == "pass"
    assert manifest["eligible_phrase_row_count"] > 500_000_000
    assert manifest["naive_raw_phrase_position_checks"] > 100_000_000_000_000
    assert manifest["naive_full_scan_approved"] is False
    assert manifest["broad_candidate_scan_started"] is False
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False


def test_fixture_is_source_backed_trial_specific_and_order4_ready() -> None:
    manifest = fixture.build_fixture()
    rows = list(csv.DictReader((fixture.OUTPUT_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")))

    assert manifest["status"] == "pass"
    assert manifest["candidate_count"] == len({(row["trial_id"], row["candidate_id"]) for row in rows})
    assert manifest["future_supported_phrase_orders"] == [4]
    assert manifest["production_ranking_change"] is False


def test_fixture_validation_passes_and_pair_refs_are_within_trial() -> None:
    fixture.build_fixture()
    manifest = validation.validate_fixture()

    assert manifest["status"] == "pass"
    assert manifest["failure_count"] == 0


def test_candidate_token_counts_match_payload() -> None:
    fixture.build_fixture()
    row = next(csv.DictReader((fixture.OUTPUT_DIR / "retained_candidate_rows.csv").open(encoding="utf-8", newline="")))

    assert len(json.loads(row["candidate_token_ids_json"])) == int(row["candidate_token_count"])


def test_completed_telemetry_run_preserves_score_and_rank_authority() -> None:
    manifest = json.loads((telemetry.OUTPUT_DIR / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "pass"
    assert manifest["candidate_count"] == 734
    assert manifest["baseline_scores_preserved"] is True
    assert manifest["baseline_order_preserved"] is True
    assert manifest["production_rank_effect"] == "none"
    assert manifest["report_authority"] == "report_only_telemetry"
    assert manifest["production_scoring_change"] is False
    assert manifest["production_ranking_change"] is False
    assert manifest["phrase_entry_scope"] == "lane2b_selected_bounded_subset"
    assert manifest["selected_phrase_entry_count"] == 48
    assert manifest["full_runtime_index_queried"] is False
    assert manifest["coverage_interpretation"] == "bounded_canary_only_not_full_runtime_coverage"
