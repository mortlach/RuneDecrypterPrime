from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.col_then_sub import runner as col_runner
from tools.benchmarks.periodic_sub_trans.col_then_sub.stage_engine_contract import (
    build_col_then_sub_policy_spec,
    build_col_then_sub_stage_specs,
    write_stage_engine_contract_artifacts,
)


pytestmark = pytest.mark.tier_a


def test_build_col_then_sub_stage_specs() -> None:
    specs = build_col_then_sub_stage_specs(state=col_runner.__dict__)
    assert [s.stage_id for s in specs] == [
        "stage_a_sub_discovery",
        "stage_b_col_search",
        "stage_c_full_refine",
    ]
    assert specs[0].search_objective.objective_id == str(col_runner.SCORER_STAGE1["objective"])
    assert specs[2].search_objective.objective_id == str(col_runner.SCORER_FULL["objective"])
    assert specs[0].params.get("dedupe_by_basin") is False
    assert specs[1].params.get("dedupe_by_basin") is True
    assert specs[2].params.get("dedupe_by_basin") is True


def test_build_col_then_sub_policy_spec() -> None:
    policy = build_col_then_sub_policy_spec(state=col_runner.__dict__)
    payload = policy.to_json_dict()
    assert payload["policy_id"] == "col_then_sub_adaptive_policy_v1"
    assert isinstance(payload["params"], dict)


def test_write_col_then_sub_contract_artifacts(tmp_path: Path) -> None:
    written: dict[str, object] = {}

    def _write_json(path: Path, payload):
        written[str(path.name)] = payload

    out = write_stage_engine_contract_artifacts(
        run_dir=tmp_path,
        state=col_runner.__dict__,
        write_json_fn=_write_json,
    )
    assert str(Path(out["stage_specs_path"]).name) == "stage_specs.json"
    assert str(Path(out["policy_spec_path"]).name) == "policy_spec.json"
    assert "stage_specs.json" in written
    assert "policy_spec.json" in written
