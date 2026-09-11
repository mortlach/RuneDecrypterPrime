import rdp.api._resolve
import json

import numpy as np
import pytest

from rdp import api
from rdp.core.component_contracts import UnsupportedConfigurationError


pytestmark = pytest.mark.tier_a

def test_kaeding_alias_resolver_accepts_seed_selection_params():
    out = rdp.api._resolve.resolve_optimizer_aliases('kaeding', {'steps': 10, 'seed_selection_metric': 'pct', 'seed_restarts': 3})
    assert out['steps'] == 10
    assert out['seed_selection_metric'] == 'pct'
    assert out['seed_restarts'] == 3


def test_typed_kaeding_raw_ordering_defaults_to_false():
    spec = api.SolverSpec.kaeding(steps=1, restarts=1, inner_batch_size=1)
    assert spec.parameters['use_raw_score'] is False
    assert spec.to_dict()['parameters']['use_raw_score'] is False
    restored = api.SolverSpec.from_name('kaeding', parameters={
        'steps': 1, 'restarts': 1, 'inner_batch_size': 1,
    })
    assert restored == spec


@pytest.mark.parametrize('use_raw_score', [False, True])
def test_kaeding_raw_ordering_json_round_trip_and_replay(use_raw_score):
    spec = api.SolverSpec.kaeding(steps=2, restarts=1, inner_batch_size=4,
        use_raw_score=use_raw_score, seed=12446)
    payload = json.loads(json.dumps(spec.to_dict()))
    restored = api.SolverSpec.from_name(payload['kind'], parameters={
        **payload['parameters'], 'seed': payload['seed'],
    })
    assert restored == spec
    assert restored.replay_key == spec.replay_key
    assert restored.parameters['use_raw_score'] is use_raw_score
    other = api.SolverSpec.kaeding(steps=2, restarts=1, inner_batch_size=4,
        use_raw_score=not use_raw_score, seed=12446)
    assert other.replay_key != spec.replay_key


@pytest.mark.parametrize('value', [None, 0, 1, 0.0, 1.0, 'true', 'False', [], {}, np.bool_(True)])
def test_kaeding_raw_ordering_rejects_non_bool(value):
    parameters = dict(steps=1, restarts=1, inner_batch_size=1, use_raw_score=value)
    with pytest.raises(TypeError, match='use_raw_score.*bool'):
        api.SolverSpec.kaeding(**parameters)
    with pytest.raises(UnsupportedConfigurationError, match='use_raw_score.*bool'):
        api.SolverSpec.from_name('kaeding', parameters=parameters)


@pytest.mark.parametrize('telemetry_enabled', [False, True])
def test_raw_ordering_reports_public_score_and_effective_request(telemetry_enabled):
    from rdp.data.runeglish import Runeglish

    plaintext, wli, _ = Runeglish.encode_english_to_runes(
        'THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE',
        direction=api.TextDirection.RTL,
    )
    cipher = api.CipherSpec.periodic_substitution(period=1)
    key = tuple(range(29))
    scoring = api.ScoringConfig(character_lane_enabled=True, wli_lane_enabled=False,
        character_order_weights={3: 0.5, 4: 0.5}, wli_order_weights={},
        objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))
    result = api.run(api.RunSpec(
        problem_input=api.RuneInput(api.encrypt(plaintext, cipher=cipher, key=key),
            word_length_information=wli),
        cipher=cipher, key_space=api.KeySpec.periodic_substitution(period=1),
        solver=api.SolverSpec.kaeding(steps=1, restarts=1, inner_batch_size=1,
            use_raw_score=True, seed=12446),
        scoring=scoring, initial_keys=(key,), text_direction=api.TextDirection.RTL,
        telemetry_enabled=telemetry_enabled,
    ))
    rescored = api.score(api.RuneInput(result.plaintext_indices,
        word_length_information=result.word_length_information), scoring=scoring,
        text_direction=api.TextDirection.RTL)
    assert result.score == pytest.approx(rescored)
    assert result.solver_report.best_score == pytest.approx(rescored)
    assert result.scorer_report.score == pytest.approx(rescored)
    assert result.configuration.solver.requested['parameters']['use_raw_score'] is True
    assert result.configuration.solver.effective['parameters']['use_raw_score'] is True
    assert result.configuration.scoring.requested['objective'] == scoring.objective.to_dict()
    assert result.configuration.scoring.effective['objective'] == scoring.objective.to_dict()
    assert result.reproducibility.solver_config['parameters']['use_raw_score'] is True
    assert result.oracle.used_for_stop is False
