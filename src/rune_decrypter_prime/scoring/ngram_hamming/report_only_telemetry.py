from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from rune_decrypter_prime.scoring.ngram_hamming.bridge import (
    NgramProfileSpec,
    best_hit_signature,
    bridge_profile_specs,
    cluster_hits_overlap_touch,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit


REPORT_PROFILE_ID = "BR_O3_conservative"
REPORT_CUT = "normal"
REPORT_ORDER = 3
REPORT_INTEGRATION_MODE = "report_only_no_rank_effect"
REPORT_DETAILS_KEY = "ngram_hamming_n3c_normal_report_only"
REPORT_AUTHORITY = "report_only_telemetry"


@dataclass(frozen=True)
class N3CNormalReportTelemetryConfig:
    enabled: bool = False
    asset_source_mode: str = "fast_runtime_index"
    runtime_index_asset_id: str = ""
    compact_asset_id: str = ""
    runtime_validation_status: str = ""
    old_phrase_index_v1_used: bool = False
    sample_asset_used: bool = False
    full_raw_shards_used_directly_as_runtime: bool = False


def n3c_normal_report_profile() -> NgramProfileSpec:
    matches = [
        spec for spec in bridge_profile_specs()
        if spec.profile_id == REPORT_PROFILE_ID
        and REPORT_ORDER in spec.orders
        and REPORT_CUT in spec.cuts
        and spec.canonical_profile_id == "N3C"
        and "canonical_equivalent_for_normal" in spec.parameter_status
    ]
    if len(matches) != 1:
        raise RuntimeError("N3C-normal report profile contract is not uniquely satisfied")
    return matches[0]


def validate_report_config(config: N3CNormalReportTelemetryConfig) -> None:
    if not config.enabled:
        return
    blocked: list[str] = []
    if config.asset_source_mode != "fast_runtime_index":
        blocked.append("asset_source_mode is not fast_runtime_index")
    if config.runtime_validation_status != "pass":
        blocked.append("runtime validation status is not pass")
    if not config.runtime_index_asset_id:
        blocked.append("runtime index asset id is missing")
    if not config.compact_asset_id:
        blocked.append("compact asset id is missing")
    if config.old_phrase_index_v1_used:
        blocked.append("old phrase_index_v1 is forbidden")
    if config.sample_asset_used:
        blocked.append("sample asset is forbidden")
    if config.full_raw_shards_used_directly_as_runtime:
        blocked.append("full raw shard runtime is forbidden")
    if blocked:
        raise RuntimeError("N3C-normal report telemetry blocked: " + "; ".join(blocked))


def build_n3c_normal_report_telemetry(
    *,
    candidate_id: str,
    hits: Iterable[PhraseHit],
    config: N3CNormalReportTelemetryConfig,
) -> dict[str, object]:
    validate_report_config(config)
    if not config.enabled:
        return {
            "enabled": False,
            "report_authority": REPORT_AUTHORITY,
            "report_integration_mode": REPORT_INTEGRATION_MODE,
            "production_rank_effect": "none",
        }

    spec = n3c_normal_report_profile()
    selected_hits = tuple(
        hit for hit in hits
        if hit.candidate_id == candidate_id
        and hit.profile_id == spec.profile_id
        and hit.dictionary_cut == REPORT_CUT
        and hit.ngram_order == REPORT_ORDER
    )
    clusters = cluster_hits_overlap_touch(
        selected_hits,
        cluster_scope="canonical_equivalent_report_only_telemetry",
        allowed_profile_ids={spec.profile_id},
    )
    phrase_counter = Counter(hit.phrase_id for hit in selected_hits)
    cluster_hit_counts = [cluster.raw_hit_count for cluster in clusters]
    warning_flags: list[str] = []
    if selected_hits and max(phrase_counter.values(), default=0) / len(selected_hits) >= 0.75:
        warning_flags.append("one_phrase_dominates")
    if selected_hits and max(cluster_hit_counts, default=0) / len(selected_hits) >= 0.75:
        warning_flags.append("one_cluster_dominates")

    return {
        "enabled": True,
        "asset_source_mode": config.asset_source_mode,
        "runtime_index_asset_id": config.runtime_index_asset_id,
        "compact_asset_id": config.compact_asset_id,
        "profile_id": spec.profile_id,
        "canonical_profile_id": spec.canonical_profile_id,
        "parameter_status": spec.parameter_status,
        "score_authority": spec.score_authority,
        "report_authority": REPORT_AUTHORITY,
        "report_integration_mode": REPORT_INTEGRATION_MODE,
        "production_rank_effect": "none",
        "cut": REPORT_CUT,
        "ngram_order": REPORT_ORDER,
        "cluster_count": len(clusters),
        "exact_cluster_count": sum(1 for cluster in clusters if cluster.exact_hit_present),
        "hit_count": len(selected_hits),
        "best_hit_signature": best_hit_signature(selected_hits),
        "dominant_cluster_hit_fraction": (
            max(cluster_hit_counts, default=0) / len(selected_hits) if selected_hits else 0.0
        ),
        "dominant_phrase_hit_fraction": (
            max(phrase_counter.values(), default=0) / len(selected_hits) if selected_hits else 0.0
        ),
        "warning_flags": sorted(warning_flags),
        "counts_are_diagnostic_only": True,
        "log_counts_are_diagnostic_only": True,
        "raw_hit_count_is_diagnostic_only": True,
    }


def merge_n3c_normal_report_details(
    *,
    extra_details: Mapping[str, Any] | None,
    candidate_id: str,
    hits: Iterable[PhraseHit],
    config: N3CNormalReportTelemetryConfig,
) -> dict[str, Any]:
    if config.enabled and (not isinstance(candidate_id, str) or not candidate_id):
        raise ValueError("candidate_id is required for N3C-normal report telemetry")
    details = dict(extra_details or {})
    if REPORT_DETAILS_KEY in details:
        raise ValueError(f"extra_details already contains reserved section {REPORT_DETAILS_KEY!r}")
    details[REPORT_DETAILS_KEY] = build_n3c_normal_report_telemetry(
        candidate_id=candidate_id,
        hits=hits,
        config=config,
    )
    return details
