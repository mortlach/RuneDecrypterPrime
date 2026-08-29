from __future__ import annotations
from rdp import api

def test_v1_has_one_run_operation_and_no_class_or_solve_alias() -> None:
    assert callable(api.run)
    assert not hasattr(api, "RunAPI")
    assert not hasattr(api, "solve")
