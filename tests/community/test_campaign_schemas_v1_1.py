from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

pytestmark = pytest.mark.tier_a

_ROOT = Path(__file__).resolve().parents[2]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_phase1_required_files_exist():
    required = [
        Path("tools/benchmarks/community/README.md"),
        Path("tools/benchmarks/community/README_runner.md"),
        Path("tools/benchmarks/community/README_canary.md"),
        Path("tools/benchmarks/community/README_organiser.md"),
        Path("tools/benchmarks/community/profile_catalog_v1_1.json"),
        Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"),
        Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"),
        Path("tools/benchmarks/community/examples/campaign_config_v1_1.json"),
        Path("tools/benchmarks/community/examples/canary_campaign_config_v1_1.json"),
        Path("tools/benchmarks/community/examples/runner_config_local.template.json"),
        Path("tools/benchmarks/community/fixtures/README.md"),
        Path("tools/benchmarks/community/fixtures/fixture_001.json"),
        Path("docs/setup/setup_and_preflight_v1_1.md"),
        Path("assets_packed/README.md"),
        Path("assets_manifest_v1.json"),
    ]
    missing = [str(path) for path in required if not path.exists()]
    assert not missing, f"missing phase-1 files: {missing}"


def test_manifest_schema_loads_and_validates():
    schema = _load_json(Path("tools/benchmarks/community/schemas/manifest_schema_v1_1.json"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    row = {
        "campaign_id": "community-v1-1",
        "job_id": "job_00000001",
        "git_sha": "7c346c2",
        "text_fixture_id": "fixture_001",
        "period": 10,
        "columns": 7,
        "order": "col_then_sub",
        "profile_id": "baseline",
        "run_seed": 111,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
    }
    validator.validate(row)

    invalid = dict(row)
    invalid["unexpected"] = True
    with pytest.raises(ValidationError):
        validator.validate(invalid)


def test_result_schema_loads_and_validates():
    schema = _load_json(Path("tools/benchmarks/community/schemas/result_schema_v1_1.json"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    row = {
        "campaign_id": "community-v1-1",
        "job_id": "job_00000001",
        "git_sha": "7c346c2",
        "text_fixture_id": "fixture_001",
        "period": 10,
        "columns": 7,
        "order": "col_then_sub",
        "profile_id": "baseline",
        "run_seed": 111,
        "replicate_idx": 0,
        "config_fingerprint": "abcdef12",
        "status": "unsolved",
        "stop_reason": "plateau_detected",
        "best_match_ratio": 0.5,
        "best_stage": 3,
        "total_seconds": 1.23,
        "total_evals": 456,
        "stage1_best_score": 0.1,
        "stage2_best_score": 0.2,
        "stage3_best_score": 0.3,
        "device": "cpu",
        "scoring_backend": "numpy",
        "fastlm_present": True,
    }
    validator.validate(row)

    invalid = dict(row)
    invalid["stop_reason"] = "not_in_enum"
    with pytest.raises(ValidationError):
        validator.validate(invalid)


@pytest.mark.parametrize(
    "path",
    sorted((_ROOT / "tools" / "benchmarks" / "community" / "examples").glob("*.json")),
)
def test_example_json_files_parse(path: Path):
    _load_json(path)
