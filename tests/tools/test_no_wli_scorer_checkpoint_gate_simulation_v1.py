from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    simulate_scorer_checkpoint_gates_v1 as mod,
)


def _pair(current_margin: str = "-0.01", current_correct: str = "0") -> dict[str, str]:
    return {
        "pair_id": "p1",
        "artifact_path": "artifact.json",
        "fixture_id": "",
        "fixture_seed": "411",
        "search_seed": "0",
        "token_length": "1000",
        "winner_token_hash": "truth_better",
        "challenger_token_hash": "truth_worse",
        "winner_candidate_hash": "cand_truth_better",
        "challenger_candidate_hash": "cand_truth_worse",
        "truth_gap": "0.1",
        "current_score_margin": current_margin,
        "current_score_correct": current_correct,
    }


def test_feature_side_direction_and_tie_threshold() -> None:
    assert mod._feature_side(1.0, 0.5, "higher", 0.1) == mod.SIDE_WINNER
    assert mod._feature_side(0.5, 1.0, "higher", 0.1) == mod.SIDE_CHALLENGER
    assert mod._feature_side(0.5, 0.55, "higher", 0.1) == mod.SIDE_NONE
    assert mod._feature_side(0.1, 0.2, "lower", 0.05) == mod.SIDE_WINNER
    assert mod._feature_side(0.2, 0.1, "lower", 0.05) == mod.SIDE_CHALLENGER


def test_current_margin_guard_makes_no_override() -> None:
    rule = mod.GateRule(
        rule_id="r",
        family="test",
        current_margin_max_abs=0.005,
        specs=(mod.FeatureSpec(source="s1b", feature_name="x", direction="higher"),),
    )
    result = mod.simulate_rule(rule, _pair(current_margin="-0.02"), {}, {})
    assert result["gate_fired"] == 0
    assert result["shadow_selected_side"] == mod.SIDE_CHALLENGER
    assert result["no_decision_reason"] == "current_margin_too_large"


def test_span_cap_pressure_guardrail_blocks_feature() -> None:
    rule = mod.GateRule(
        rule_id="r",
        family="span",
        current_margin_max_abs=0.02,
        specs=(
            mod.FeatureSpec(
                source="span",
                config_id="cfg",
                feature_name="span_score",
                direction="higher",
                threshold=0.01,
                max_cap_pruned_rate=0.05,
            ),
        ),
    )
    span = {
        ("cfg", "truth_better"): {"span_score": "0.9", "candidate_cap_pruned_rate": "0.2"},
        ("cfg", "truth_worse"): {"span_score": "0.1", "candidate_cap_pruned_rate": "0.0"},
    }
    result = mod.simulate_rule(rule, _pair(), {}, span)
    assert result["gate_fired"] == 0
    assert result["no_decision_reason"] == "cap_pressure_guardrail"


def test_word_trust_inactive_selected_side_is_no_decision() -> None:
    rule = mod.GateRule(
        rule_id="r",
        family="word",
        current_margin_max_abs=0.02,
        specs=(
            mod.FeatureSpec(
                source="s1b",
                feature_name="word_ngram_trust_score",
                direction="higher",
                threshold=0.05,
                require_selected_word_active=True,
            ),
        ),
    )
    s1b = {
        "truth_better": {"word_ngram_trust_score": "0.9", "word_ngram_active": "0"},
        "truth_worse": {"word_ngram_trust_score": "0.1", "word_ngram_active": "1"},
    }
    result = mod.simulate_rule(rule, _pair(), s1b, {})
    assert result["gate_fired"] == 0
    assert result["no_decision_reason"] == "selected_word_ngram_inactive"


def test_rescue_and_break_outcomes() -> None:
    assert mod._decision_outcome(_pair(current_correct="0"), mod.SIDE_WINNER) == "rescue"
    assert mod._decision_outcome(_pair(current_correct="1"), mod.SIDE_CHALLENGER) == "break"
    assert mod._decision_outcome(_pair(current_correct="1"), mod.SIDE_WINNER) == "same_correct"
    assert mod._decision_outcome(_pair(current_correct="0"), mod.SIDE_CHALLENGER) == "same_wrong"


def test_conjunction_requires_same_side() -> None:
    rule = mod.GateRule(
        rule_id="r",
        family="conjunction",
        current_margin_max_abs=0.02,
        combine="all_same",
        specs=(
            mod.FeatureSpec(source="s1b", feature_name="a", direction="higher", threshold=0.01),
            mod.FeatureSpec(source="s1b", feature_name="b", direction="lower", threshold=0.01),
        ),
    )
    s1b = {
        "truth_better": {"a": "0.9", "b": "0.9"},
        "truth_worse": {"a": "0.1", "b": "0.1"},
    }
    result = mod.simulate_rule(rule, _pair(), s1b, {})
    assert result["gate_fired"] == 0
    assert result["no_decision_reason"] == "feature_disagreement_or_tie"
