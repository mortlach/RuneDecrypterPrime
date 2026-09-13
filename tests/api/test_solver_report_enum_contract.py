from __future__ import annotations

import pytest

from rdp import api


def test_solver_report_contract_labels_are_enum_backed() -> None:
    assert api.advanced.StopReason.TARGET_SCORE_REACHED.value == "target_score_reached"
    assert api.advanced.StopCategory.SUCCESS.value == "success"
    assert api.advanced.ExecutionStatus.COMPLETED.value == "completed"
    assert api.advanced.RecoveryStatus.EXACT.value == "exact"
    assert api.advanced.OracleMode.REAL_SOLVE.value == "real_solve"


def test_oracle_report_rejects_unavailable_oracle_use() -> None:
    with pytest.raises(ValueError, match="available"):
        api.advanced.OracleReport(available=False, used_for_ranking=True)


def test_reproducibility_metadata_serializes_enum_values() -> None:
    metadata = api.advanced.ReproducibilityMetadata(
        compute_device=api.ComputeDevice.CPU,
        stop_category=api.advanced.StopCategory.SUCCESS,
        stop_reason=api.advanced.StopReason.TARGET_SCORE_REACHED,
    )

    payload = metadata.to_json_dict()
    assert payload["compute_device"] == "cpu"
    assert payload["stop_category"] == "success"
    assert payload["stop_reason"] == "target_score_reached"
