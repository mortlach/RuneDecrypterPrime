from __future__ import annotations

from dataclasses import replace

from rune_decrypter_prime.scoring.ngram_hamming.bridge import (
    CANDIDATE_SUMMARY_REQUIRED_FIELDS,
    CLUSTER_ROW_REQUIRED_FIELDS,
    PAIR_LEDGER_REQUIRED_FIELDS,
    PROFILE_MANIFEST_REQUIRED_FIELDS,
    ZERO_HIT_AUDIT_REQUIRED_FIELDS,
    bridge_profile_specs,
    canonical_profile_specs,
    candidate_summary_rows,
    cluster_hits_overlap_touch,
    cluster_rows,
    pair_ledger_row,
    profile_manifest_hash,
    profile_manifest_rows,
    score_candidate_profile_ids,
    validate_pair_ledger_row,
    validate_zero_hit_audit_row,
    zero_hit_audit_row,
)
from rune_decrypter_prime.scoring.ngram_hamming.reference import PhraseHit


def make_hit(
    *,
    profile_id: str,
    start: int,
    end: int,
    phrase_id: str = "phrase",
    cut: str = "normal",
    order: int = 2,
    total_hd: int = 1,
) -> PhraseHit:
    return PhraseHit(
        candidate_id="candidate",
        chunk_id="chunk",
        damage_level="",
        profile_id=profile_id,
        ngram_order=order,
        dictionary_cut=cut,
        phrase_id=phrase_id,
        phrase_count=1,
        phrase_log_count=0.0,
        phrase_token_length=end - start,
        word_lengths=(end - start,),
        word_hds=(total_hd,),
        total_phrase_hd=total_hd,
        max_word_hd=total_hd,
        mean_word_hd=float(total_hd),
        normalised_phrase_hd=total_hd / (end - start),
        hit_start=start,
        hit_end=end,
    )


def specs_by_id(specs):
    return {spec.profile_id: spec for spec in specs}


def test_profile_manifest_requires_authority_fields() -> None:
    rows = profile_manifest_rows((*canonical_profile_specs(), *bridge_profile_specs()))
    assert rows
    for row in rows:
        assert PROFILE_MANIFEST_REQUIRED_FIELDS <= set(row)


def test_bridge_profile_does_not_equal_s3w_when_thresholds_differ() -> None:
    canonical = specs_by_id(canonical_profile_specs())
    bridge = specs_by_id(bridge_profile_specs())
    s3w = canonical["S3W"]
    strict_bridge = bridge["BR_O3_conservative"]
    assert strict_bridge.cuts == ("normal", "strict")
    assert strict_bridge.min_phrase_token_length != s3w.min_phrase_token_length
    assert strict_bridge.max_word_hd != s3w.max_word_hd
    assert strict_bridge.narrower_than_profile == "S3W for strict cut"


def test_s34c_main_min_length_is_10() -> None:
    canonical = specs_by_id(canonical_profile_specs())
    assert canonical["S34C_main"].min_phrase_token_length == 10
    assert canonical["S34C_main"].canonical_profile_id == "S34C"


def test_overlap_and_touch_clusters_merge_and_gap_splits() -> None:
    hits = (
        make_hit(profile_id="BR_O2_soft", start=0, end=5, phrase_id="a"),
        make_hit(profile_id="BR_O2_soft", start=3, end=8, phrase_id="b"),
        make_hit(profile_id="BR_O2_soft", start=8, end=10, phrase_id="c"),
        make_hit(profile_id="BR_O2_soft", start=12, end=14, phrase_id="d"),
    )
    clusters = cluster_hits_overlap_touch(hits, cluster_scope="all_profile_overlap_touch_cluster")
    assert len(clusters) == 2
    assert clusters[0].start_offset == 0
    assert clusters[0].end_offset == 10
    assert clusters[0].raw_hit_count == 3
    assert clusters[1].start_offset == 12


def test_diagnostic_profiles_do_not_shape_score_candidate_clusters() -> None:
    hits = (
        make_hit(profile_id="BR_O3_conservative", start=0, end=3, phrase_id="score_a", order=3),
        make_hit(profile_id="BR_O2_soft", start=3, end=6, phrase_id="diag_bridge", order=2),
        make_hit(profile_id="BR_O3_conservative", start=6, end=9, phrase_id="score_b", order=3),
    )
    all_clusters = cluster_hits_overlap_touch(hits, cluster_scope="all_profile_overlap_touch_cluster")
    score_clusters = cluster_hits_overlap_touch(
        hits,
        cluster_scope="score_candidate_overlap_touch_cluster",
        allowed_profile_ids={"BR_O3_conservative"},
    )
    assert len(all_clusters) == 1
    assert len(score_clusters) == 2
    assert [cluster.raw_hit_count for cluster in score_clusters] == [1, 1]


def test_raw_hit_count_can_exceed_cluster_count() -> None:
    hits = (
        make_hit(profile_id="BR_O2_soft", start=0, end=5, phrase_id="a"),
        make_hit(profile_id="BR_O2_soft", start=1, end=6, phrase_id="b"),
        make_hit(profile_id="BR_O2_soft", start=2, end=7, phrase_id="c"),
    )
    clusters = cluster_hits_overlap_touch(hits, cluster_scope="all_profile_overlap_touch_cluster")
    assert len(hits) == 3
    assert len(clusters) == 1
    assert clusters[0].raw_hit_count == 3
    assert clusters[0].unique_phrase_id_count == 3


def test_exact_hits_are_fields_not_profiles() -> None:
    hit = make_hit(profile_id="BR_O2_soft", start=0, end=5, total_hd=0)
    clusters = cluster_hits_overlap_touch((hit,), cluster_scope="all_profile_overlap_touch_cluster")
    assert clusters[0].exact_hit_present is True
    assert clusters[0].exact_hit_count == 1
    assert "exact" not in clusters[0].profiles_present


def test_normal_and_strict_remain_separate_in_specs() -> None:
    bridge = specs_by_id(bridge_profile_specs())
    assert bridge["BR_O2_soft"].cuts == ("normal", "strict")
    assert bridge["BR_O2_soft"].score_authority == "diagnostic_only"


def test_profile_manifest_hash_changes_when_thresholds_change() -> None:
    specs = bridge_profile_specs()
    changed = tuple(
        replace(spec, min_phrase_token_length=spec.min_phrase_token_length + 1)
        if spec.profile_id == "BR_O2_soft"
        else spec
        for spec in specs
    )
    assert profile_manifest_hash(specs) != profile_manifest_hash(changed)


def test_cluster_rows_emit_required_schema_fields() -> None:
    hits = (
        make_hit(profile_id="BR_O3_conservative", start=0, end=8, phrase_id="a", order=3, total_hd=0),
        make_hit(profile_id="BR_O3_conservative", start=8, end=16, phrase_id="b", order=3, total_hd=1),
    )
    clusters = cluster_hits_overlap_touch(hits, cluster_scope="score_candidate_overlap_touch_cluster")
    rows = cluster_rows(clusters, run_id="synthetic")

    assert len(rows) == 1
    assert CLUSTER_ROW_REQUIRED_FIELDS <= set(rows[0])
    assert rows[0]["run_id"] == "synthetic"
    assert rows[0]["raw_hit_count"] == 2
    assert rows[0]["exact_hit_present"] is True
    assert rows[0]["best_hit_signature"].startswith("BR_O3_conservative|normal|3|a|")


def test_candidate_summary_rows_carry_authority_and_cluster_counts() -> None:
    hits = (
        make_hit(profile_id="BR_O3_conservative", start=0, end=8, phrase_id="a", order=3, total_hd=0),
        make_hit(profile_id="BR_O3_conservative", start=8, end=16, phrase_id="a", order=3, total_hd=1),
        make_hit(profile_id="BR_O2_soft", start=20, end=28, phrase_id="diag", order=2, total_hd=1),
    )
    clusters = cluster_hits_overlap_touch(hits, cluster_scope="all_profile_overlap_touch_cluster")
    rows = candidate_summary_rows(
        hits,
        clusters,
        bridge_profile_specs(),
        expected_cluster_scope="all_profile_overlap_touch_cluster",
    )
    by_profile = {row["profile_id"]: row for row in rows}

    assert CANDIDATE_SUMMARY_REQUIRED_FIELDS <= set(by_profile["BR_O3_conservative"])
    assert by_profile["BR_O3_conservative"]["score_authority"] == "blocked_bridge_candidate"
    assert by_profile["BR_O3_conservative"]["raw_hit_count"] == 2
    assert by_profile["BR_O3_conservative"]["cluster_count"] == 1
    assert by_profile["BR_O3_conservative"]["exact_hit_count"] == 1
    assert by_profile["BR_O3_conservative"]["exact_cluster_count"] == 1
    assert by_profile["BR_O3_conservative"]["top_phrase_share"] == 1.0
    assert by_profile["BR_O2_soft"]["score_authority"] == "diagnostic_only"


def test_candidate_summary_rejects_unknown_profile_reference() -> None:
    hit = make_hit(profile_id="unknown", start=0, end=8, phrase_id="x")
    clusters = cluster_hits_overlap_touch((hit,), cluster_scope="all_profile_overlap_touch_cluster")

    try:
        candidate_summary_rows(
            (hit,),
            clusters,
            bridge_profile_specs(),
            expected_cluster_scope="all_profile_overlap_touch_cluster",
        )
    except ValueError as exc:
        assert "unknown profile" in str(exc)
    else:
        raise AssertionError("expected unknown profile reference to fail")


def test_candidate_summary_rejects_wrong_cluster_scope() -> None:
    hit = make_hit(profile_id="BR_O3_conservative", start=0, end=8, phrase_id="x", order=3)
    clusters = cluster_hits_overlap_touch((hit,), cluster_scope="all_profile_overlap_touch_cluster")

    try:
        candidate_summary_rows(
            (hit,),
            clusters,
            bridge_profile_specs(),
            expected_cluster_scope="score_candidate_overlap_touch_cluster",
        )
    except ValueError as exc:
        assert "cluster scope mismatch" in str(exc)
    else:
        raise AssertionError("expected wrong candidate summary cluster scope to fail")


def test_score_candidate_profile_ids_exclude_diagnostic_only_profiles() -> None:
    ids = score_candidate_profile_ids((*canonical_profile_specs(), *bridge_profile_specs()))

    assert "N3C" in ids
    assert "S3W" in ids
    assert "BR_O3_conservative" in ids
    assert "BR_O2_soft" not in ids
    assert "B2R" not in ids


def test_pair_ledger_and_zero_hit_audit_schema_validators() -> None:
    pair_row = {field: "" for field in PAIR_LEDGER_REQUIRED_FIELDS}
    zero_row = {field: "" for field in ZERO_HIT_AUDIT_REQUIRED_FIELDS}

    validate_pair_ledger_row(pair_row)
    validate_zero_hit_audit_row(zero_row)

    bad_pair = dict(pair_row)
    bad_pair.pop("pair_id")
    bad_zero = dict(zero_row)
    bad_zero.pop("likely_no_hit_reason")

    for validator, row, expected in (
        (validate_pair_ledger_row, bad_pair, "pair_id"),
        (validate_zero_hit_audit_row, bad_zero, "likely_no_hit_reason"),
    ):
        try:
            validator(row)
        except ValueError as exc:
            assert expected in str(exc)
        else:
            raise AssertionError("expected schema validator to reject missing field")


def test_pair_ledger_row_builder_serialises_nested_tuple_fields() -> None:
    row = pair_ledger_row(
        pair_id="pair-1",
        expected_better_id="better",
        expected_worse_id="worse",
        order2_tuple_better={"raw_hit_count": 3},
        order2_tuple_worse={"raw_hit_count": 1},
        normal_support_delta=2.0,
        concentration_flags=("top_phrase_share_high",),
        unsafe_interpretation_flags=("partial_provenance",),
    )

    assert PAIR_LEDGER_REQUIRED_FIELDS <= set(row)
    assert row["order2_tuple_better"] == '{"raw_hit_count":3}'
    assert row["normal_support_delta"] == 2.0
    assert row["concentration_flags"] == '["top_phrase_share_high"]'
    assert row["unsafe_interpretation_flags"] == '["partial_provenance"]'


def test_zero_hit_audit_row_builder_serialises_order_counts() -> None:
    row = zero_hit_audit_row(
        pair_id="pair-1",
        candidate_id="candidate",
        role="expected_better",
        chunk_id="chunk-1",
        ngram_hit_count_by_order={2: 0, 3: 0},
        phrase_opportunity_count_by_order={2: 12, 3: 7},
        likely_no_hit_reason="synthetic zero-hit",
    )

    assert ZERO_HIT_AUDIT_REQUIRED_FIELDS <= set(row)
    assert row["ngram_hit_count_by_order"] == '{"2":0,"3":0}'
    assert row["phrase_opportunity_count_by_order"] == '{"2":12,"3":7}'
    assert row["likely_no_hit_reason"] == "synthetic zero-hit"
