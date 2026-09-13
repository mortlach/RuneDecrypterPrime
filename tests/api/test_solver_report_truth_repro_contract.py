from __future__ import annotations

import pytest
from rdp import api


def test_reproducibility_metadata_has_stable_typed_seed_and_stop_fields() -> None:
    metadata = api.advanced.ReproducibilityMetadata(
        backend=api.advanced.ScorerBackend.NUMPY,
        requested_seed=None,
        effective_seed=0,
        stochastic=False,
        stop_category=api.advanced.StopCategory.BUDGET,
        stop_reason=api.advanced.StopReason.MAX_EVALUATIONS_REACHED,
    )
    payload = metadata.to_json_dict()
    assert payload["requested_seed"] is None
    assert payload["effective_seed"] == 0
    assert payload["backend"] == "numpy"
    assert payload["compute_device"] is None
    assert payload["stop_category"] == "budget"
    assert payload["stop_reason"] == "max_evaluations_reached"


def test_reproducibility_metadata_rejects_raw_enum_strings() -> None:
    with pytest.raises(TypeError, match="backend"):
        api.advanced.ReproducibilityMetadata(backend="numpy")  # type: ignore[arg-type]


def test_oracle_and_reproducibility_are_separate_report_sections() -> None:
    oracle = api.advanced.OracleReport(
        available=True,
        used_for_stop=True,
        stop_reason=api.advanced.StopReason.ORACLE_EXACT_KEY_MATCH,
        mode=api.advanced.OracleMode.TEST,
    )
    reproducibility = api.advanced.ReproducibilityMetadata(
        requested_seed=7, effective_seed=7
    )
    assert oracle.to_json_dict()["used_for_stop"] is True
    assert "used_for_stop" not in reproducibility.to_json_dict()
