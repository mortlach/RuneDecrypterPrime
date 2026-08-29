from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from collections import Counter
from itertools import groupby
from typing import Iterable, Mapping

from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit


PROFILE_MANIFEST_REQUIRED_FIELDS = frozenset(
    {
        "profile_id",
        "profile_origin",
        "canonical_profile_id",
        "parameter_status",
        "score_authority",
        "direction",
        "orders",
        "cuts",
        "min_phrase_token_length",
        "max_total_phrase_hd",
        "max_word_hd",
        "normalised_hd_ceiling",
        "role",
        "scope_reason",
        "equivalent_research_profile",
        "promotion_status",
        "threshold_diff_summary",
    }
)

CLUSTER_ROW_REQUIRED_FIELDS = frozenset(
    {
        "run_id",
        "cluster_scope",
        "candidate_id",
        "chunk_id",
        "cluster_id",
        "start_offset",
        "end_offset",
        "profiles_present",
        "cuts_present",
        "orders_present",
        "raw_hit_count",
        "unique_phrase_id_count",
        "unique_start_count",
        "exact_hit_present",
        "exact_hit_count",
        "best_hit_signature",
    }
)

CANDIDATE_SUMMARY_REQUIRED_FIELDS = frozenset(
    {
        "candidate_id",
        "profile_id",
        "profile_origin",
        "canonical_profile_id",
        "parameter_status",
        "score_authority",
        "direction",
        "cut",
        "order",
        "raw_hit_count",
        "cluster_count",
        "exact_hit_count",
        "exact_cluster_count",
        "unique_phrase_id_count",
        "unique_start_count",
        "hit_to_cluster_ratio",
        "top_phrase_share",
        "best_hit_signature",
    }
)

PAIR_LEDGER_REQUIRED_FIELDS = frozenset(
    {
        "pair_id",
        "expected_better_id",
        "expected_worse_id",
        "baseline_winner",
        "phrase_tuple_winner",
        "order2_tuple_better",
        "order2_tuple_worse",
        "order3_tuple_better",
        "order3_tuple_worse",
        "normal_support_delta",
        "strict_support_delta",
        "first_diff_component",
        "outcome_label",
        "panel_rescue_flag",
        "concentration_flags",
        "null_lift_summary",
        "unsafe_interpretation_flags",
    }
)

ZERO_HIT_AUDIT_REQUIRED_FIELDS = frozenset(
    {
        "pair_id",
        "candidate_id",
        "role",
        "chunk_id",
        "panel_rescue_flag",
        "span_hamming_best_support",
        "ngram_hit_count_by_order",
        "phrase_opportunity_count_by_order",
        "best_failed_or_near_phrase_note",
        "likely_no_hit_reason",
    }
)


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

    @property
    def best_hit_signature(self) -> str:
        return best_hit_signature(self.hits)


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
    payload = json.dumps(
        profile_manifest_rows(specs), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score_candidate_profile_ids(specs: Iterable[NgramProfileSpec]) -> set[str]:
    return {
        spec.profile_id
        for spec in specs
        if spec.score_authority
        in {"score_bearing_candidate", "blocked_bridge_candidate"}
    }


def missing_required_fields(
    row: Mapping[str, object], required_fields: frozenset[str]
) -> tuple[str, ...]:
    return tuple(sorted(required_fields - set(row)))


def validate_required_fields(
    row: Mapping[str, object], required_fields: frozenset[str]
) -> None:
    missing = missing_required_fields(row, required_fields)
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")


def best_hit_signature(hits: Iterable[PhraseHit]) -> str:
    hit_list = list(hits)
    if not hit_list:
        return ""
    best = min(
        hit_list,
        key=lambda hit: (
            hit.total_phrase_hd,
            hit.max_word_hd,
            -hit.phrase_log_count,
            -hit.phrase_token_length,
            hit.profile_id,
            hit.phrase_id,
            hit.hit_start,
        ),
    )
    return "|".join(
        (
            best.profile_id,
            best.dictionary_cut,
            str(best.ngram_order),
            best.phrase_id,
            str(best.hit_start),
            str(best.hit_end),
            str(best.total_phrase_hd),
            str(best.max_word_hd),
        )
    )


def cluster_row(cluster: PhraseCluster, *, run_id: str) -> dict[str, object]:
    row: dict[str, object] = {
        "run_id": run_id,
        "cluster_scope": cluster.cluster_scope,
        "candidate_id": cluster.candidate_id,
        "chunk_id": cluster.chunk_id,
        "cluster_id": cluster.cluster_id,
        "start_offset": cluster.start_offset,
        "end_offset": cluster.end_offset,
        "profiles_present": json.dumps(
            list(cluster.profiles_present), separators=(",", ":")
        ),
        "cuts_present": json.dumps(list(cluster.cuts_present), separators=(",", ":")),
        "orders_present": json.dumps(
            list(cluster.orders_present), separators=(",", ":")
        ),
        "raw_hit_count": cluster.raw_hit_count,
        "unique_phrase_id_count": cluster.unique_phrase_id_count,
        "unique_start_count": cluster.unique_start_count,
        "exact_hit_present": cluster.exact_hit_present,
        "exact_hit_count": cluster.exact_hit_count,
        "best_hit_signature": cluster.best_hit_signature,
    }
    validate_required_fields(row, CLUSTER_ROW_REQUIRED_FIELDS)
    return row


def cluster_rows(
    clusters: Iterable[PhraseCluster], *, run_id: str
) -> list[dict[str, object]]:
    return [cluster_row(cluster, run_id=run_id) for cluster in clusters]


def candidate_summary_rows(
    hits: Iterable[PhraseHit],
    clusters: Iterable[PhraseCluster],
    specs: Iterable[NgramProfileSpec],
    *,
    expected_cluster_scope: str,
) -> list[dict[str, object]]:
    cluster_list = list(clusters)
    wrong_scopes = sorted(
        {
            cluster.cluster_scope
            for cluster in cluster_list
            if cluster.cluster_scope != expected_cluster_scope
        }
    )
    if wrong_scopes:
        raise ValueError(
            "candidate summary cluster scope mismatch: "
            f"expected {expected_cluster_scope}, got {', '.join(wrong_scopes)}"
        )
    specs_by_key = {
        (spec.profile_id, cut, order): spec
        for spec in specs
        for cut in spec.cuts
        for order in spec.orders
    }
    hit_groups: dict[tuple[str, str, str, int], list[PhraseHit]] = {}
    for hit in hits:
        key = (hit.candidate_id, hit.profile_id, hit.dictionary_cut, hit.ngram_order)
        hit_groups.setdefault(key, []).append(hit)
    cluster_counts: Counter[tuple[str, str, str, int]] = Counter()
    exact_cluster_counts: Counter[tuple[str, str, str, int]] = Counter()
    for cluster in cluster_list:
        keys = {
            (hit.candidate_id, hit.profile_id, hit.dictionary_cut, hit.ngram_order)
            for hit in cluster.hits
        }
        for key in keys:
            cluster_counts[key] += 1
            if any(
                hit.total_phrase_hd == 0
                and (
                    hit.candidate_id,
                    hit.profile_id,
                    hit.dictionary_cut,
                    hit.ngram_order,
                )
                == key
                for hit in cluster.hits
            ):
                exact_cluster_counts[key] += 1

    rows: list[dict[str, object]] = []
    for key, group_hits in sorted(hit_groups.items()):
        candidate_id, profile_id, cut, order = key
        spec = specs_by_key.get((profile_id, cut, order))
        if spec is None:
            raise ValueError(
                f"hit references unknown profile/cut/order: {profile_id}/{cut}/{order}"
            )
        raw_hit_count = len(group_hits)
        cluster_count = int(cluster_counts[key])
        phrase_counter = Counter(hit.phrase_id for hit in group_hits)
        top_phrase_share = (
            max(phrase_counter.values(), default=0) / raw_hit_count
            if raw_hit_count
            else 0.0
        )
        row: dict[str, object] = {
            "candidate_id": candidate_id,
            "profile_id": profile_id,
            "profile_origin": spec.profile_origin,
            "canonical_profile_id": spec.canonical_profile_id,
            "parameter_status": spec.parameter_status,
            "score_authority": spec.score_authority,
            "direction": spec.direction,
            "cut": cut,
            "order": order,
            "raw_hit_count": raw_hit_count,
            "cluster_count": cluster_count,
            "exact_hit_count": sum(1 for hit in group_hits if hit.total_phrase_hd == 0),
            "exact_cluster_count": int(exact_cluster_counts[key]),
            "unique_phrase_id_count": len(phrase_counter),
            "unique_start_count": len({hit.hit_start for hit in group_hits}),
            "hit_to_cluster_ratio": raw_hit_count / cluster_count
            if cluster_count
            else 0.0,
            "top_phrase_share": top_phrase_share,
            "best_hit_signature": best_hit_signature(group_hits),
        }
        validate_required_fields(row, CANDIDATE_SUMMARY_REQUIRED_FIELDS)
        rows.append(row)
    return rows


def validate_pair_ledger_row(row: Mapping[str, object]) -> None:
    validate_required_fields(row, PAIR_LEDGER_REQUIRED_FIELDS)


def validate_zero_hit_audit_row(row: Mapping[str, object]) -> None:
    validate_required_fields(row, ZERO_HIT_AUDIT_REQUIRED_FIELDS)


def pair_ledger_row(
    *,
    pair_id: str,
    expected_better_id: str,
    expected_worse_id: str,
    baseline_winner: str = "",
    phrase_tuple_winner: str = "",
    order2_tuple_better: Mapping[str, object] | None = None,
    order2_tuple_worse: Mapping[str, object] | None = None,
    order3_tuple_better: Mapping[str, object] | None = None,
    order3_tuple_worse: Mapping[str, object] | None = None,
    normal_support_delta: float = 0.0,
    strict_support_delta: float = 0.0,
    first_diff_component: str = "",
    outcome_label: str = "uninterpreted",
    panel_rescue_flag: bool = False,
    concentration_flags: Iterable[str] = (),
    null_lift_summary: str = "",
    unsafe_interpretation_flags: Iterable[str] = (),
) -> dict[str, object]:
    row: dict[str, object] = {
        "pair_id": pair_id,
        "expected_better_id": expected_better_id,
        "expected_worse_id": expected_worse_id,
        "baseline_winner": baseline_winner,
        "phrase_tuple_winner": phrase_tuple_winner,
        "order2_tuple_better": json.dumps(
            dict(order2_tuple_better or {}), sort_keys=True, separators=(",", ":")
        ),
        "order2_tuple_worse": json.dumps(
            dict(order2_tuple_worse or {}), sort_keys=True, separators=(",", ":")
        ),
        "order3_tuple_better": json.dumps(
            dict(order3_tuple_better or {}), sort_keys=True, separators=(",", ":")
        ),
        "order3_tuple_worse": json.dumps(
            dict(order3_tuple_worse or {}), sort_keys=True, separators=(",", ":")
        ),
        "normal_support_delta": float(normal_support_delta),
        "strict_support_delta": float(strict_support_delta),
        "first_diff_component": first_diff_component,
        "outcome_label": outcome_label,
        "panel_rescue_flag": bool(panel_rescue_flag),
        "concentration_flags": json.dumps(
            sorted(concentration_flags), separators=(",", ":")
        ),
        "null_lift_summary": null_lift_summary,
        "unsafe_interpretation_flags": json.dumps(
            sorted(unsafe_interpretation_flags), separators=(",", ":")
        ),
    }
    validate_pair_ledger_row(row)
    return row


def zero_hit_audit_row(
    *,
    pair_id: str,
    candidate_id: str,
    role: str,
    chunk_id: str,
    panel_rescue_flag: bool = False,
    span_hamming_best_support: str = "",
    ngram_hit_count_by_order: Mapping[int | str, int] | None = None,
    phrase_opportunity_count_by_order: Mapping[int | str, int] | None = None,
    best_failed_or_near_phrase_note: str = "",
    likely_no_hit_reason: str = "",
) -> dict[str, object]:
    row: dict[str, object] = {
        "pair_id": pair_id,
        "candidate_id": candidate_id,
        "role": role,
        "chunk_id": chunk_id,
        "panel_rescue_flag": bool(panel_rescue_flag),
        "span_hamming_best_support": span_hamming_best_support,
        "ngram_hit_count_by_order": json.dumps(
            {
                str(key): value
                for key, value in (ngram_hit_count_by_order or {}).items()
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        "phrase_opportunity_count_by_order": json.dumps(
            {
                str(key): value
                for key, value in (phrase_opportunity_count_by_order or {}).items()
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        "best_failed_or_near_phrase_note": best_failed_or_near_phrase_note,
        "likely_no_hit_reason": likely_no_hit_reason,
    }
    validate_zero_hit_audit_row(row)
    return row


def cluster_hits_overlap_touch(
    hits: Iterable[PhraseHit],
    *,
    cluster_scope: str,
    allowed_profile_ids: set[str] | None = None,
) -> tuple[PhraseCluster, ...]:
    filtered_hits = [
        hit
        for hit in hits
        if allowed_profile_ids is None or hit.profile_id in allowed_profile_ids
    ]
    filtered_hits.sort(
        key=lambda hit: (
            hit.candidate_id,
            hit.chunk_id,
            hit.hit_start,
            hit.hit_end,
            hit.profile_id,
        )
    )
    clusters: list[PhraseCluster] = []
    next_cluster_id = 1
    for (candidate_id, chunk_id), group_iter in groupby(
        filtered_hits, key=lambda hit: (hit.candidate_id, hit.chunk_id)
    ):
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
