from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.benchmarks.community.config import (
    apply_profile_overrides_to_pipeline_module,
    load_profile_catalog_from_dict,
)

pytestmark = pytest.mark.tier_a


def test_profile_catalog_validation_accepts_known_profile_catalog():
    catalog_data = {
        "catalog_version": "v1.1",
        "profiles": [
            {
                "profile_id": "p_ok",
                "description": "valid profile",
                "scorer_schedule": {},
                "overrides": {
                    "stage3_gating": {"full_entry_score": None, "probe_entry_score": "PIPELINE_DEFAULT"},
                    "stage12_carry_through": {"promote_top": 16, "archive_keep": 48},
                    "stage1_breadth": {"sub_candidates_by_columns": {"3": 32, "7": 24}},
                    "stage3_basin_exploration": {"initial_keys_by_columns": {"3": 36, "7": 40}},
                    "solver_stage1": "PIPELINE_DEFAULT",
                    "solver_stage2": "PIPELINE_DEFAULT",
                    "solver_stage3": "PIPELINE_DEFAULT",
                },
            }
        ],
    }
    catalog = load_profile_catalog_from_dict(catalog_data)
    profile = catalog.get_profile("p_ok")
    assert profile.profile_id == "p_ok"


def test_profile_catalog_validation_rejects_out_of_range_values():
    catalog_data = {
        "catalog_version": "v1.1",
        "profiles": [
            {
                "profile_id": "p_bad",
                "description": "invalid profile",
                "scorer_schedule": {},
                "overrides": {
                    "stage12_carry_through": {"promote_top": 9999},
                },
            }
        ],
    }
    with pytest.raises(ValueError):
        load_profile_catalog_from_dict(catalog_data)


def test_apply_profile_overrides_keeps_defaults_and_applies_explicit_values():
    module = SimpleNamespace(
        STAGE3_FULL_ENTRY_SCORE=0.1,
        STAGE3_PROBE_ENTRY_SCORE=0.06,
        STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS={3: 0.1},
        STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS={3: 0.06},
        STAGE12_PROMOTE_TOP=8,
        STAGE12_ARCHIVE_KEEP=24,
        STAGE1_SUB_CANDIDATES_BY_COLUMNS={3: 10},
        STAGE3_INITIAL_KEYS_BY_COLUMNS={3: 12},
        SOLVER_STAGE1={"steps": 10},
        SOLVER_STAGE2={"rounds": 2},
        SOLVER_STAGE3={"steps": 20},
    )
    catalog_data = {
        "catalog_version": "v1.1",
        "profiles": [
            {
                "profile_id": "p_apply",
                "description": "apply profile",
                "scorer_schedule": {},
                "overrides": {
                    "stage3_gating": {"full_entry_score": None, "probe_entry_score": "PIPELINE_DEFAULT"},
                    "stage12_carry_through": {"promote_top": 16, "archive_keep": "PIPELINE_DEFAULT"},
                    "stage1_breadth": {"sub_candidates_by_columns": {"7": 24}},
                    "stage3_basin_exploration": {"initial_keys_by_columns": {"7": 40}},
                },
            }
        ],
    }
    catalog = load_profile_catalog_from_dict(catalog_data)
    profile = catalog.get_profile("p_apply")
    apply_profile_overrides_to_pipeline_module(module, profile)

    assert module.STAGE3_FULL_ENTRY_SCORE is None
    assert module.STAGE3_PROBE_ENTRY_SCORE == 0.06
    assert module.STAGE3_FULL_ENTRY_SCORE_BY_COLUMNS == {}
    assert module.STAGE3_PROBE_ENTRY_SCORE_BY_COLUMNS == {}
    assert module.STAGE12_PROMOTE_TOP == 16
    assert module.STAGE12_ARCHIVE_KEEP == 24
    assert module.STAGE1_SUB_CANDIDATES_BY_COLUMNS[7] == 24
    assert module.STAGE3_INITIAL_KEYS_BY_COLUMNS[7] == 40

