from __future__ import annotations

import pytest

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit
from rune_decrypter_prime.scoring.ngram_hamming.report_only_telemetry import (
    N3CNormalReportTelemetryConfig,
    REPORT_DETAILS_KEY,
    build_n3c_normal_report_telemetry,
    merge_n3c_normal_report_details,
    n3c_normal_report_profile,
)


def hit(*, profile_id: str = "BR_O3_conservative", cut: str = "normal", order: int = 3) -> PhraseHit:
    return PhraseHit(
        candidate_id="candidate-a",
        chunk_id="chunk-a",
        damage_level="none",
        profile_id=profile_id,
        ngram_order=order,
        dictionary_cut=cut,
        phrase_id="phrase-a",
        phrase_count=1,
        phrase_log_count=0.0,
        phrase_token_length=8,
        word_lengths=(1, 3, 4),
        word_hds=(0, 0, 0),
        total_phrase_hd=0,
        max_word_hd=0,
        mean_word_hd=0.0,
        normalised_phrase_hd=0.0,
        hit_start=2,
        hit_end=10,
    )


def enabled_config() -> N3CNormalReportTelemetryConfig:
    return N3CNormalReportTelemetryConfig(
        enabled=True,
        runtime_index_asset_id="runtime-v1",
        compact_asset_id="compact-v1",
        runtime_validation_status="pass",
    )


def test_report_profile_is_manifest_derived_n3c_normal_equivalent() -> None:
    spec = n3c_normal_report_profile()

    assert spec.profile_id == "BR_O3_conservative"
    assert spec.canonical_profile_id == "N3C"
    assert "canonical_equivalent_for_normal" in spec.parameter_status


def test_report_telemetry_defaults_off_and_has_no_rank_effect() -> None:
    row = build_n3c_normal_report_telemetry(
        candidate_id="candidate-a",
        hits=(hit(),),
        config=N3CNormalReportTelemetryConfig(),
    )

    assert row == {
        "enabled": False,
        "report_authority": "report_only_telemetry",
        "report_integration_mode": "report_only_no_rank_effect",
        "production_rank_effect": "none",
    }


def test_report_telemetry_filters_to_n3c_normal_equivalent_only() -> None:
    row = build_n3c_normal_report_telemetry(
        candidate_id="candidate-a",
        hits=(hit(), hit(cut="strict"), hit(profile_id="BR_O3_soft")),
        config=enabled_config(),
    )

    assert row["enabled"] is True
    assert row["production_rank_effect"] == "none"
    assert row["report_authority"] == "report_only_telemetry"
    assert row["report_integration_mode"] == "report_only_no_rank_effect"
    assert row["profile_id"] == "BR_O3_conservative"
    assert row["canonical_profile_id"] == "N3C"
    assert row["cut"] == "normal"
    assert row["ngram_order"] == 3
    assert row["hit_count"] == 1
    assert row["cluster_count"] == 1
    assert row["exact_cluster_count"] == 1


@pytest.mark.parametrize(
    "config",
    (
        N3CNormalReportTelemetryConfig(enabled=True, runtime_validation_status="pass"),
        N3CNormalReportTelemetryConfig(
            enabled=True,
            runtime_index_asset_id="runtime-v1",
            compact_asset_id="compact-v1",
            runtime_validation_status="blocked",
        ),
        N3CNormalReportTelemetryConfig(
            enabled=True,
            runtime_index_asset_id="runtime-v1",
            compact_asset_id="compact-v1",
            runtime_validation_status="pass",
            sample_asset_used=True,
        ),
    ),
)
def test_report_telemetry_fails_closed_for_invalid_runtime_source(config: N3CNormalReportTelemetryConfig) -> None:
    with pytest.raises(RuntimeError, match="report telemetry blocked"):
        build_n3c_normal_report_telemetry(candidate_id="candidate-a", hits=(hit(),), config=config)


def test_report_detail_merge_uses_reserved_report_only_section() -> None:
    details = merge_n3c_normal_report_details(
        extra_details={"existing": {"kept": True}},
        candidate_id="candidate-a",
        hits=(hit(),),
        config=enabled_config(),
    )

    assert details["existing"] == {"kept": True}
    assert details[REPORT_DETAILS_KEY]["hit_count"] == 1
    assert details[REPORT_DETAILS_KEY]["production_rank_effect"] == "none"


def test_report_detail_merge_rejects_reserved_section_collision() -> None:
    with pytest.raises(ValueError, match="reserved section"):
        merge_n3c_normal_report_details(
            extra_details={REPORT_DETAILS_KEY: {}},
            candidate_id="candidate-a",
            hits=(),
            config=enabled_config(),
        )
