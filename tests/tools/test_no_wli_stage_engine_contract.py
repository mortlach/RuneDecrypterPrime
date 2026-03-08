from __future__ import annotations

from pathlib import Path

import pytest

from tools.benchmarks.periodic_sub_trans.no_wli import runner as no_wli_runner
from tools.benchmarks.periodic_sub_trans.no_wli.stage_engine_contract import (
    build_no_wli_policy_spec,
    build_no_wli_stage_specs,
    build_no_wli_stage_specs_from_profile,
    write_stage_engine_contract_artifacts,
)


pytestmark = pytest.mark.tier_a


def test_build_no_wli_stage_specs_uses_runner_labels() -> None:
    specs = build_no_wli_stage_specs(state=no_wli_runner.__dict__)
    assert [s.stage_id for s in specs] == [
        "stage_a_discovery",
        "stage_b_promotion",
        "stage_c_refine",
    ]
    assert specs[0].search_objective.objective_id == str(no_wli_runner.SCORER_STAGE1_LABEL)
    assert specs[1].search_objective.objective_id == str(no_wli_runner.SCORER_STAGE2_LABEL)
    assert specs[2].search_objective.objective_id == str(no_wli_runner.SCORER_STAGE3_LABEL)
    assert specs[0].params.get("dedupe_by_basin") is False
    assert specs[1].params.get("dedupe_by_basin") is True
    assert specs[2].params.get("dedupe_by_basin") is True


def test_build_no_wli_policy_spec_is_deterministic() -> None:
    policy = build_no_wli_policy_spec(state=no_wli_runner.__dict__)
    payload = policy.to_json_dict()
    assert payload["policy_id"] == "no_wli_adaptive_policy_v1"
    assert isinstance(payload["tie_band_eps"], float)
    assert isinstance(payload["ambiguity_expand_top_k"], int)


def test_build_no_wli_stage_specs_from_longrun_profile_pins_avg_fulltext_labels() -> None:
    specs = build_no_wli_stage_specs_from_profile(
        profile_id="no_wli_a1_m4_b4_stage3avg_fulltext_longrun3x_v1",
        state=no_wli_runner.__dict__,
    )
    assert specs[0].search_objective.objective_id == "A_char2_avg_fulltext"
    assert specs[1].search_objective.objective_id == "M_char4_avg_fulltext"
    assert specs[2].search_objective.objective_id == "B_char4_avg_fulltext"


def test_write_stage_engine_contract_artifacts(tmp_path: Path) -> None:
    written: dict[str, object] = {}

    def _write_json(path: Path, payload):
        written[str(path.name)] = payload

    out = write_stage_engine_contract_artifacts(
        run_dir=tmp_path,
        state=no_wli_runner.__dict__,
        write_json_fn=_write_json,
    )
    assert str(Path(out["stage_specs_path"]).name) == "stage_specs.json"
    assert str(Path(out["policy_spec_path"]).name) == "policy_spec.json"
    assert "stage_specs.json" in written
    assert "policy_spec.json" in written
    stage_specs = written["stage_specs.json"]
    assert isinstance(stage_specs, list)
    assert len(stage_specs) == 3
    assert stage_specs[0]["stage_id"] == "stage_a_discovery"
