from __future__ import annotations

import pytest
from rdp import api


def test_oracle_report_defaults_to_unavailable_and_unused() -> None:
    report = api.advanced.OracleReport()
    assert report.to_json_dict() == {
        "available": False,
        "used_for_scoring": False,
        "used_for_ranking": False,
        "used_for_stop": False,
        "stop_reason": None,
        "mode": "real_solve",
    }


def test_known_key_oracle_use_is_explicit_and_typed() -> None:
    report = api.advanced.OracleReport(
        available=True,
        used_for_stop=True,
        stop_reason=api.advanced.StopReason.KNOWN_KEY_EXECUTION_COMPLETED,
        mode=api.advanced.OracleMode.TEST,
    )
    assert report.to_json_dict()["stop_reason"] == "known_key_execution_completed"
    assert report.to_json_dict()["mode"] == "test"


def test_oracle_use_cannot_be_claimed_without_available_truth() -> None:
    with pytest.raises(ValueError, match="available"):
        api.advanced.OracleReport(used_for_ranking=True)


def test_oracle_stop_reason_and_use_are_bound_together() -> None:
    with pytest.raises(ValueError, match="recorded together"):
        api.advanced.OracleReport(
            available=True,
            stop_reason=api.advanced.StopReason.ORACLE_EXACT_KEY_MATCH,
        )
