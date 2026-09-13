from __future__ import annotations

import importlib.util

from rdp import api


def test_v1_has_one_run_operation_and_no_class_or_solve_alias() -> None:
    assert callable(api.run)
    assert not hasattr(api, "RunAPI")
    assert not hasattr(api, "solve")
    assert importlib.util.find_spec("rdp.api.api") is None
    assert importlib.util.find_spec("rdp.api.wrappers") is None


def test_v1_specs_have_only_canonical_typed_constructors() -> None:
    for owner, obsolete in (
        (api.KeySpec, ("repeat", "repeat_range", "periodic_structured", "align")),
        (api.SolverSpec, ("beam", "ga", "sa")),
    ):
        for name in obsolete:
            assert not hasattr(owner, name)
