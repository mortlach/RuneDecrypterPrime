from __future__ import annotations

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    sweep_span_hamming_500_robust_composite_space_v1 as mod,
)


def test_build_rules_includes_unpenalized_and_penalized_rules() -> None:
    rules = mod.build_rules()

    assert any(not rule.penalty_features and rule.lambda_value == 0 for rule in rules)
    assert any(rule.penalty_features and rule.lambda_value > 0 for rule in rules)


def test_score_rule_adds_positive_terms_and_subtracts_penalty() -> None:
    rule = mod.RuleSpec(
        rule_id="r",
        positive_features=("a", "b"),
        penalty_features=("n",),
        lambda_value=0.5,
    )
    rows = [{"token_hash": "h", "chunk_kind": "prefix", "a": "2", "b": "3", "n": "4"}]

    scores = mod._score_rule(rows, rule)

    assert scores["h"]["prefix"] == 3
