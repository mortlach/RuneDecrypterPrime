from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.scorer_schedule import (
    SCORER_SCHEDULE_ID_CATALOG,
    SCHEDULE_EARLY_A_CHAR1,
    SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
    SCHEDULE_LATE_B_CHAR34,
    SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    SCHEDULE_MIDDLE_M_CHAR12,
    SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
)
from tools.benchmarks.periodic_sub_trans.no_wli import run_fixture_matrix as fixture_matrix


pytestmark = pytest.mark.tier_a


def test_schedule_matrix_minimal_mode_covers_all_catalog_ids():
    rows = fixture_matrix.build_schedule_matrix(mode="minimal_all_ids")
    assert rows
    early = {str(r["early"]) for r in rows}
    middle = {str(r["middle"]) for r in rows}
    late = {str(r["late"]) for r in rows}
    assert set(SCORER_SCHEDULE_ID_CATALOG["early"]).issubset(early)
    assert set(SCORER_SCHEDULE_ID_CATALOG["middle"]).issubset(middle)
    assert set(SCORER_SCHEDULE_ID_CATALOG["late"]).issubset(late)


def test_schedule_matrix_cartesian_mode_size_matches_catalog_product():
    rows = fixture_matrix.build_schedule_matrix(mode="cartesian_all")
    expect = (
        len(SCORER_SCHEDULE_ID_CATALOG["early"])
        * len(SCORER_SCHEDULE_ID_CATALOG["middle"])
        * len(SCORER_SCHEDULE_ID_CATALOG["late"])
    )
    assert len(rows) == int(expect)


def test_build_fixture_jobs_dimensions():
    fixtures = [fixture_matrix.FixtureSpec(fixture_id="fixture_001", length=2376)]
    period_columns = {5: (1, 3)}
    schedules = [
        {
            "early": SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
            "middle": SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
            "late": SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
        }
    ]
    jobs = fixture_matrix.build_fixture_jobs(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=(111, 211),
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        heartbeat_seconds=3600,
        text_offsets=(0,),
        scorer_impl="numpy",
        scorer_stage3_impl_avg_fulltext="numpy",
        scoring_experiment_profiles=("off", "a_baseline"),
        schedules=schedules,
    )
    assert len(jobs) == 8
    first = jobs[0]
    assert first.fixture_id == "fixture_001"
    assert first.run_mode == "adaptive_fixture_v1"
    assert first.scorer_schedule() == {
        "early": SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
        "middle": SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
        "late": SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
    }
    assert first.span_ab_case_id == "none"
    assert first.span_decision_role_enabled is False


def test_build_fixture_jobs_span_ab_pair_mode_doubles_jobs():
    fixtures = [fixture_matrix.FixtureSpec(fixture_id="fixture_001", length=2376)]
    period_columns = {7: (3,)}
    schedules = [
        {
            "early": SCHEDULE_EARLY_A_CHAR1_AVG_FULLTEXT,
            "middle": SCHEDULE_MIDDLE_M_CHAR12_AVG_FULLTEXT,
            "late": SCHEDULE_LATE_B_CHAR4_AVG_FULLTEXT,
        }
    ]
    jobs = fixture_matrix.build_fixture_jobs(
        fixtures=fixtures,
        period_columns=period_columns,
        run_seeds=(111,),
        run_mode="adaptive_fixture_v1",
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        heartbeat_seconds=3600,
        text_offsets=(0,),
        scorer_impl="numpy",
        scorer_stage3_impl_avg_fulltext="numpy",
        scoring_experiment_profiles=("off",),
        schedules=schedules,
        enable_span_ab_pair=True,
        span_ab_decision_role="prune",
    )
    assert len(jobs) == 2
    case_ids = {str(job.span_ab_case_id) for job in jobs}
    assert case_ids == {"span_shadow", "span_prune"}


def test_resolve_period_columns_from_grid():
    cfg = {
        "grid": {
            "period_min": 5,
            "period_max": 6,
            "columns_min": 1,
            "columns_max": 3,
        }
    }
    period_columns = fixture_matrix.resolve_period_columns(
        campaign_config=cfg,
        use_campaign_grid=True,
        periods_override=None,
        columns_override_by_period=None,
    )
    assert period_columns == {5: (1, 2, 3), 6: (1, 2, 3)}


def test_load_fixture_specs_applies_length_override():
    cfg = {
        "fixtures": [
            {
                "text_fixture_id": "fixture_001",
                "length": 2376,
            }
        ]
    }
    specs = fixture_matrix.load_fixture_specs(
        campaign_config=cfg,
        repo_root=fixture_matrix._ROOT,
        fixture_ids=None,
        fixture_length_override=1000,
    )
    assert len(specs) == 1
    assert int(specs[0].length) == 1000


def test_build_schedule_matrix_minimal_avg_ids_excludes_known_win10_overrides():
    rows = fixture_matrix.build_schedule_matrix(mode="minimal_avg_ids")
    assert rows
    assert not any(r["middle"] == SCHEDULE_MIDDLE_M_CHAR12 for r in rows)
    assert not any(r["late"] == SCHEDULE_LATE_B_CHAR34 for r in rows)


def test_build_fixture_jobs_rejects_win10_schedule_when_guard_enabled():
    fixtures = [fixture_matrix.FixtureSpec(fixture_id="fixture_001", length=1000)]
    period_columns = {7: (1,)}
    with pytest.raises(ValueError, match="REQUIRE_NO_WIN10_OBJECTIVES violated"):
        fixture_matrix.build_fixture_jobs(
            fixtures=fixtures,
            period_columns=period_columns,
            run_seeds=(111,),
            run_mode="adaptive_fixture_v1",
            profile_id="no_wli_a1_m12_b34_stage3avg_fulltext_v1",
            heartbeat_seconds=3600,
            text_offsets=(0,),
            scorer_impl="numpy",
            scorer_stage3_impl_avg_fulltext="numpy",
            scoring_experiment_profiles=("off",),
            schedules=[
                {
                    "early": SCHEDULE_EARLY_A_CHAR1,
                    "middle": SCHEDULE_MIDDLE_M_CHAR12,
                    "late": SCHEDULE_LATE_B_CHAR34,
                }
            ],
        )


def test_validate_schedule_contract_for_best_avg_full_text_path():
    fixture_matrix.validate_schedule_contract(
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        schedule={
            "early": "a_char2_avg_fulltext",
            "middle": "m_char4_avg_fulltext",
            "late": "b_char4_avg_fulltext",
        },
    )


def test_validate_schedule_contract_rejects_non_full_text_when_guard_enabled():
    old_no_win10 = bool(fixture_matrix.REQUIRE_NO_WIN10_OBJECTIVES)
    old_full_text = bool(fixture_matrix.REQUIRE_FULL_TEXT_EFFECTIVE)
    try:
        fixture_matrix.REQUIRE_NO_WIN10_OBJECTIVES = False
        fixture_matrix.REQUIRE_FULL_TEXT_EFFECTIVE = True
        with pytest.raises(ValueError, match="REQUIRE_FULL_TEXT_EFFECTIVE violated"):
            fixture_matrix.validate_schedule_contract(
                profile_id="no_wli_a1_m12_b34_v1",
                schedule={
                    "early": "a_char1",
                    "middle": "m_char12",
                    "late": "b_char34",
                },
            )
    finally:
        fixture_matrix.REQUIRE_NO_WIN10_OBJECTIVES = old_no_win10
        fixture_matrix.REQUIRE_FULL_TEXT_EFFECTIVE = old_full_text
