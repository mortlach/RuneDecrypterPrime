from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.catalogs import ObjectiveCatalog, OperatorCatalog
from tools.benchmarks.periodic_sub_trans.common.stage_spec import ObjectiveRef, StageSpec


pytestmark = pytest.mark.tier_a


def test_objective_catalog_register_build_and_ref_lookup() -> None:
    cat = ObjectiveCatalog()
    ref = ObjectiveRef(
        objective_id="A_char1",
        family="char_ngram",
        normalisation="avg",
        window_policy="full_text",
    )
    cat.register("A_char1", lambda: {"objective": "avg.logp.full_text"}, ref=ref)
    assert cat.has("A_char1")
    assert cat.build("A_char1")["objective"] == "avg.logp.full_text"
    assert cat.get_ref("A_char1").objective_id == "A_char1"
    assert cat.objective_ids() == ["A_char1"]


def test_objective_catalog_rejects_unknown_stage_spec_objective() -> None:
    cat = ObjectiveCatalog()
    cat.register("A_char1", lambda: {"objective": "avg.logp.full_text"})
    stage = StageSpec(
        stage_id="s1",
        search_objective=ObjectiveRef("A_char1", "char_ngram", "avg", "full_text"),
        decision_objective=ObjectiveRef("B_char34", "char_ngram", "avg", "full_text"),
    )
    with pytest.raises(KeyError):
        cat.ensure_stage_spec_supported(stage)


def test_operator_catalog_register_lookup_and_ids() -> None:
    ops = OperatorCatalog()
    ops.register("op_a", lambda x: x + 1)
    assert ops.has("op_a")
    assert ops.get("op_a")(1) == 2
    assert ops.operator_ids() == ["op_a"]
    with pytest.raises(KeyError):
        ops.get("missing")

