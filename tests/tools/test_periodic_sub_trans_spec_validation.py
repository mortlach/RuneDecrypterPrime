from __future__ import annotations

import pytest

from tools.benchmarks.periodic_sub_trans.common.policy_spec import AdaptivePolicySpec
from tools.benchmarks.periodic_sub_trans.common.stage_spec import (
    AuxObjectiveBinding,
    ObjectiveRef,
    SpanProfile,
    SpanRole,
    SpanScope,
    StageSpec,
)


pytestmark = pytest.mark.tier_a


def test_objective_ref_requires_non_empty_fields() -> None:
    with pytest.raises(ValueError):
        ObjectiveRef("", "char_ngram", "avg", "full_text")
    with pytest.raises(ValueError):
        ObjectiveRef("x", "", "avg", "full_text")


def test_stage_spec_rejects_invalid_caps() -> None:
    obj = ObjectiveRef("A", "char_ngram", "avg", "full_text")
    with pytest.raises(ValueError):
        StageSpec("s", obj, obj, pool_keep=-1)
    with pytest.raises(ValueError):
        StageSpec("s", obj, obj, promote_top=3, pool_keep=2)


def test_aux_binding_rejects_negative_budget_or_cadence() -> None:
    obj = ObjectiveRef("span", "span_hamming", "avg", "full_text")
    with pytest.raises(ValueError):
        AuxObjectiveBinding(objective=obj, role=SpanRole.SHADOW, cadence_every=-1)
    with pytest.raises(ValueError):
        AuxObjectiveBinding(objective=obj, role=SpanRole.SHADOW, budget_ms=-0.1)
    with pytest.raises(ValueError):
        AuxObjectiveBinding(objective=obj, role=SpanRole.SHADOW, cadence_every=0, budget_ms=1.0)
    with pytest.raises(ValueError):
        AuxObjectiveBinding(objective=obj, role=SpanRole.SHADOW, cadence_every=1, budget_ms=0.0)


def test_aux_binding_span_profile_roundtrip_and_fallback() -> None:
    obj = ObjectiveRef("span", "span_hamming", "avg", "full_text")
    binding = AuxObjectiveBinding(
        objective=obj,
        role=SpanRole.SHADOW,
        scope=SpanScope.BASIN_REP,
        span_profile=SpanProfile.LITE,
        two_pass_enabled=True,
        full_top_m=12,
        cadence_every=2,
        budget_ms=5.0,
    )
    payload = binding.to_json_dict()
    assert payload["span_profile"] == "lite"
    assert payload["two_pass_enabled"] is True
    assert payload["full_top_m"] == 12
    restored = AuxObjectiveBinding.from_json_dict(payload)
    assert restored.to_json_dict() == payload

    fallback = AuxObjectiveBinding.from_json_dict(
        dict(
            objective=obj.to_json_dict(),
            role="shadow",
            scope="topk",
            span_profile="not_a_profile",
            two_pass_enabled=True,
            full_top_m=3,
            cadence_every=1,
            budget_ms=1.0,
        )
    )
    assert fallback.span_profile == SpanProfile.FULL


def test_aux_binding_rejects_negative_full_top_m() -> None:
    obj = ObjectiveRef("span", "span_hamming", "avg", "full_text")
    with pytest.raises(ValueError):
        AuxObjectiveBinding(
            objective=obj,
            role=SpanRole.SHADOW,
            cadence_every=1,
            budget_ms=1.0,
            full_top_m=-1,
        )


def test_adaptive_policy_validation_and_stable_json() -> None:
    policy = AdaptivePolicySpec(
        policy_id="p",
        tie_band_eps=0.01,
        ambiguity_expand_top_k=3,
        period_scale={13: 1.5, 7: 1.2},
        columns_scale={10: 1.1, 3: 0.9},
        params={"z": 1, "a": 2},
    )
    payload = policy.to_json_dict()
    assert list(payload["period_scale"].keys()) == ["7", "13"]
    assert list(payload["columns_scale"].keys()) == ["3", "10"]
    assert list(payload["params"].keys()) == ["a", "z"]
    cloned = AdaptivePolicySpec.from_json_dict(payload)
    assert cloned.to_json_dict() == payload

    with pytest.raises(ValueError):
        AdaptivePolicySpec(policy_id="")
    with pytest.raises(ValueError):
        AdaptivePolicySpec(policy_id="x", tie_band_eps=-0.1)
    with pytest.raises(ValueError):
        AdaptivePolicySpec(policy_id="x", period_scale={7: 0.0})
