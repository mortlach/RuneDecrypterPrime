from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tools.benchmarks.community import generate_manifest as gm
from tools.benchmarks.community._campaign_common import resolve_orders, sha256_hex_from_obj

pytestmark = pytest.mark.tier_a


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_build_manifest_rows_is_deterministic_and_schema_valid():
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/canary_campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    schema = _load_json(Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"))
    validator = Draft202012Validator(schema)

    rows_1 = gm.build_manifest_rows(campaign_config, profile_catalog)
    rows_2 = gm.build_manifest_rows(campaign_config, profile_catalog)
    assert rows_1 == rows_2

    selected_profiles = gm.resolve_profile_ids(campaign_config, profile_catalog)
    grid = campaign_config["grid"]
    expected_rows = (
        len(campaign_config["fixtures"])
        * (grid["period_max"] - grid["period_min"] + 1)
        * (grid["columns_max"] - grid["columns_min"] + 1)
        * len(resolve_orders(grid["orders"]))
        * len(selected_profiles)
        * campaign_config["replicates_per_cell"]
    )
    assert len(rows_1) == expected_rows

    seen_job_ids: set[str] = set()
    for row in rows_1:
        validator.validate(row)
        assert row["job_id"] not in seen_job_ids
        seen_job_ids.add(row["job_id"])
        row_without_job_id = dict(row)
        row_job_id = row_without_job_id.pop("job_id")
        assert row_job_id == sha256_hex_from_obj(row_without_job_id)

    assert {row["profile_id"] for row in rows_1} == {"baseline_resume_v1_1"}


def test_resolve_profile_ids_rejects_unknown_profile_id():
    campaign_config = _load_json(Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"))
    profile_catalog = _load_json(Path("tools/benchmarks/community/profile_catalog_v1_1.json"))
    campaign_config_bad = copy.deepcopy(campaign_config)
    campaign_config_bad["profile_ids"] = ["does_not_exist"]
    with pytest.raises(ValueError, match="unknown profile"):
        gm.resolve_profile_ids(campaign_config_bad, profile_catalog)


def test_generate_manifest_writes_jsonl_and_summary(tmp_path: Path):
    summary = gm.generate_manifest(
        campaign_config_path=Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"),
        profile_catalog_path=Path("tools/benchmarks/community/profile_catalog_v1_1.json"),
        manifest_schema_path=Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        output_path=tmp_path / "manifest.jsonl",
        summary_output_path=tmp_path / "manifest_summary.json",
    )
    assert summary["rows"] > 0
    assert (tmp_path / "manifest.jsonl").exists()
    assert (tmp_path / "manifest_summary.json").exists()
