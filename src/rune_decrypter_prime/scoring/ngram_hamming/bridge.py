from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from itertools import groupby
from typing import Iterable

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit


@dataclass(frozen=True)
class NgramProfileSpec:
    profile_id: str
    profile_origin: str
    canonical_profile_id: str
    parameter_status: str
    score_authority: str
    direction: str
    orders: tuple[int, ...]
    cuts: tuple[str, ...]
    min_phrase_token_length: int
    max_total_phrase_hd: int
    max_word_hd: int
    role: str
    scope_reason: str
    equivalent_research_profile: str
    promotion_status: str
    normalised_hd_ceiling: float | None = None
    broader_than_profile: str = ""
    narrower_than_profile: str = ""
    threshold_diff_summary: str = ""

    def manifest_row(self) -> dict[str, object]:
        row = asdict(self)
        row["orders"] = list(self.orders)
        row["cuts"] = list(self.cuts)
        return row


@dataclass(frozen=True)
class PhraseCluster:
    cluster_scope: str
    cluster_id: int
    candidate_id: str
    chunk_id: str
    start_offset: int
    end_offset: int
    hits: tuple[PhraseHit, ...]

    @property
    def raw_hit_count(self) -> int:
        return len(self.hits)

    @property
    def profiles_present(self) -> tuple[str, ...]:
        return tuple(sorted({hit.profile_id for hit in self.hits}))

    @property
    def cuts_present(self) -> tuple[str, ...]:
        return tuple(sorted({hit.dictionary_cut for hit in self.hits}))

    @property
    def orders_present(self) -> tuple[int, ...]:
        return tuple(sorted({hit.ngram_order for hit in self.hits}))

    @property
    def unique_phrase_id_count(self) -> int:
        return len({hit.phrase_id for hit in self.hits})

    @property
    def unique_start_count(self) -> int:
        return len({hit.hit_start for hit in self.hits})

    @property
    def exact_hit_count(self) -> int:
        return sum(1 for hit in self.hits if hit.total_phrase_hd == 0)

    @property
    def exact_hit_present(self) -> bool:
        return self.exact_hit_count > 0


def canonical_profile_specs(*, direction: str = "fwd") -> tuple[NgramProfileSpec, ...]:
    return (
        NgramProfileSpec(
            profile_id="B2R",
            profile_origin="deep_research_canon",
            canonical_profile_id="B2R",
            parameter_status="canonical",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(2,),
            cuts=("normal", "strict"),
            min_phrase_token_length=7,
            max_total_phrase_hd=2,
            max_word_hd=2,
            role="weak order-2 telemetry",
            scope_reason="canonical diagnostic family",
            equivalent_research_profile="B2R",
            promotion_status="diagnostic_only",
        ),
        NgramProfileSpec(
            profile_id="N3S_diag",
            profile_origin="deep_research_canon",
            canonical_profile_id="N3S_diag",
            parameter_status="canonical",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(3,),
            cuts=("normal",),
            min_phrase_token_length=7,
            max_total_phrase_hd=2,
            max_word_hd=2,
            role="soft normal trigram diagnostic",
            scope_reason="canonical diagnostic family",
            equivalent_research_profile="N3S_diag",
            promotion_status="diagnostic_only",
        ),
        NgramProfileSpec(
            profile_id="N3C",
            profile_origin="deep_research_canon",
            canonical_profile_id="N3C",
            parameter_status="canonical",
            score_authority="score_bearing_candidate",
            direction=direction,
            orders=(3,),
            cuts=("normal",),
            min_phrase_token_length=8,
            max_total_phrase_hd=2,
            max_word_hd=1,
            role="main normal 3-gram coverage",
            scope_reason="canonical score-candidate family",
            equivalent_research_profile="N3C",
            promotion_status="score_candidate_pending_review",
        ),
        NgramProfileSpec(
            profile_id="S3W",
            profile_origin="deep_research_canon",
            canonical_profile_id="S3W",
            parameter_status="canonical",
            score_authority="score_bearing_candidate",
            direction=direction,
            orders=(3,),
            cuts=("strict",),
            min_phrase_token_length=7,
            max_total_phrase_hd=2,
            max_word_hd=2,
            role="strict trigram confirmation with moderate reach",
            scope_reason="canonical score-candidate family",
            equivalent_research_profile="S3W",
            promotion_status="score_candidate_pending_review",
        ),
        NgramProfileSpec(
            profile_id="N4L",
            profile_origin="deep_research_canon",
            canonical_profile_id="N4L",
            parameter_status="canonical",
            score_authority="score_bearing_candidate",
            direction=direction,
            orders=(4,),
            cuts=("normal",),
            min_phrase_token_length=10,
            max_total_phrase_hd=3,
            max_word_hd=2,
            role="longer normal 4-gram confirmation",
            scope_reason="canonical score-candidate family",
            equivalent_research_profile="N4L",
            promotion_status="score_candidate_pending_review",
        ),
        NgramProfileSpec(
            profile_id="S34C_main",
            profile_origin="deep_research_canon",
            canonical_profile_id="S34C",
            parameter_status="canonical",
            score_authority="score_bearing_candidate",
            direction=direction,
            orders=(3, 4),
            cuts=("strict",),
            min_phrase_token_length=10,
            max_total_phrase_hd=2,
            max_word_hd=1,
            role="highest-precision strict confirmation",
            scope_reason="canonical score-candidate family",
            equivalent_research_profile="S34C",
            promotion_status="score_candidate_pending_review",
        ),
        NgramProfileSpec(
            profile_id="F5D",
            profile_origin="deep_research_canon",
            canonical_profile_id="F5D",
            parameter_status="canonical",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(5,),
            cuts=("normal", "strict"),
            min_phrase_token_length=12,
            max_total_phrase_hd=3,
            max_word_hd=2,
            role="sparse high-confidence 5-gram diagnostic",
            scope_reason="canonical diagnostic family",
            equivalent_research_profile="F5D",
            promotion_status="diagnostic_only",
        ),
    )


def bridge_profile_specs(*, direction: str = "fwd") -> tuple[NgramProfileSpec, ...]:
    return (
        NgramProfileSpec(
            profile_id="BR_O2_soft",
            profile_origin="bridge_derived",
            canonical_profile_id="B2R",
            parameter_status="canonical_equivalent",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(2,),
            cuts=("normal", "strict"),
            min_phrase_token_length=7,
            max_total_phrase_hd=2,
            max_word_hd=2,
            role="inspect currently active order-2 shape",
            scope_reason="temporary order-2/order-3 bridge diagnostic",
            equivalent_research_profile="B2R",
            promotion_status="blocked",
        ),
        NgramProfileSpec(
            profile_id="BR_O2_len8_conservative",
            profile_origin="bridge_derived",
            canonical_profile_id="",
            parameter_status="new_noncanonical",
            score_authority="blocked_bridge_candidate",
            direction=direction,
            orders=(2,),
            cuts=("normal", "strict"),
            min_phrase_token_length=8,
            max_total_phrase_hd=2,
            max_word_hd=1,
            role="test whether conservative order-2 evidence survives anti-inflation checks",
            scope_reason="temporary order-2/order-3 bridge diagnostic",
            equivalent_research_profile="P2 order-2 slice",
            promotion_status="blocked_pending_null_concentration_pair_ledger_damage_tier_review",
        ),
        NgramProfileSpec(
            profile_id="BR_O2_len10_long",
            profile_origin="bridge_derived",
            canonical_profile_id="",
            parameter_status="new_noncanonical",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(2,),
            cuts=("normal", "strict"),
            min_phrase_token_length=10,
            max_total_phrase_hd=2,
            max_word_hd=1,
            role="test whether long two-word phrases behave differently",
            scope_reason="temporary order-2/order-3 bridge diagnostic",
            equivalent_research_profile="none",
            promotion_status="blocked",
        ),
        NgramProfileSpec(
            profile_id="BR_O3_soft",
            profile_origin="bridge_derived",
            canonical_profile_id="N3S_diag",
            parameter_status="canonical_equivalent_for_normal_new_noncanonical_for_strict",
            score_authority="diagnostic_only",
            direction=direction,
            orders=(3,),
            cuts=("normal", "strict"),
            min_phrase_token_length=7,
            max_total_phrase_hd=2,
            max_word_hd=2,
            role="inspect soft P1-style trigram behaviour",
            scope_reason="temporary order-2/order-3 bridge diagnostic",
            equivalent_research_profile="N3S_diag normal cut only",
            promotion_status="blocked",
        ),
        NgramProfileSpec(
            profile_id="BR_O3_conservative",
            profile_origin="bridge_derived",
            canonical_profile_id="N3C",
            parameter_status="canonical_equivalent_for_normal_narrower_than_S3W_for_strict",
            score_authority="blocked_bridge_candidate",
            direction=direction,
            orders=(3,),
            cuts=("normal", "strict"),
            min_phrase_token_length=8,
            max_total_phrase_hd=2,
            max_word_hd=1,
            role="first serious order-3 bridge candidate",
            scope_reason="temporary order-2/order-3 bridge diagnostic",
            equivalent_research_profile="N3C normal cut only",
            promotion_status="can_inform_N3C_strict_view_requires_separate_review",
            narrower_than_profile="S3W for strict cut",
            threshold_diff_summary="S3W min_len=7 max_word_hd=2; this profile min_len=8 max_word_hd=1",
        ),
    )


def profile_manifest_rows(specs: Iterable[NgramProfileSpec]) -> list[dict[str, object]]:
    return [spec.manifest_row() for spec in specs]


def profile_manifest_hash(specs: Iterable[NgramProfileSpec]) -> str:
    payload = json.dumps(profile_manifest_rows(specs), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cluster_hits_overlap_touch(
    hits: Iterable[PhraseHit],
    *,
    cluster_scope: str,
    allowed_profile_ids: set[str] | None = None,
) -> tuple[PhraseCluster, ...]:
    filtered_hits = [
        hit for hit in hits
        if allowed_profile_ids is None or hit.profile_id in allowed_profile_ids
    ]
    filtered_hits.sort(key=lambda hit: (hit.candidate_id, hit.chunk_id, hit.hit_start, hit.hit_end, hit.profile_id))
    clusters: list[PhraseCluster] = []
    next_cluster_id = 1
    for (candidate_id, chunk_id), group_iter in groupby(filtered_hits, key=lambda hit: (hit.candidate_id, hit.chunk_id)):
        current_hits: list[PhraseHit] = []
        current_start = 0
        current_end = 0
        for hit in group_iter:
            if not current_hits:
                current_hits = [hit]
                current_start = hit.hit_start
                current_end = hit.hit_end
                continue
            if hit.hit_start <= current_end:
                current_hits.append(hit)
                current_end = max(current_end, hit.hit_end)
                continue
            clusters.append(
                PhraseCluster(
                    cluster_scope=cluster_scope,
                    cluster_id=next_cluster_id,
                    candidate_id=candidate_id,
                    chunk_id=chunk_id,
                    start_offset=current_start,
                    end_offset=current_end,
                    hits=tuple(current_hits),
                )
            )
            next_cluster_id += 1
            current_hits = [hit]
            current_start = hit.hit_start
            current_end = hit.hit_end
        if current_hits:
            clusters.append(
                PhraseCluster(
                    cluster_scope=cluster_scope,
                    cluster_id=next_cluster_id,
                    candidate_id=candidate_id,
                    chunk_id=chunk_id,
                    start_offset=current_start,
                    end_offset=current_end,
                    hits=tuple(current_hits),
                )
            )
            next_cluster_id += 1
    return tuple(clusters)

