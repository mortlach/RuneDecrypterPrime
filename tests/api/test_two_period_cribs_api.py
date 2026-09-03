from __future__ import annotations
import rdp.api.two_period_cribs
from rdp import api
import json
import pytest
import numpy as np
from rdp.core.config.solution import Solution
from rdp.data.runeglish import Runeglish

def test_builder_is_canonical_and_json_safe():
    spec = api.SolverSpec.two_period_cribs(fixed_cribs=(('Uncomfortable', 188),), candidate_words=('pilgrimage', 'Dormouse', 'dormouse'), candidate_positions={'dormouse': (206, 81, 206)}, starts=7, seed=2026)
    request = rdp.api.two_period_cribs.normalize_two_period_cribs_request(spec)
    assert spec.kind is api.advanced.SolverKind.TWO_PERIOD_CRIBS
    assert spec.seed == 2026
    assert spec.parameters['fixed_cribs'] == (('uncomfortable', 188),)
    assert spec.parameters['candidate_words'] == ('dormouse', 'pilgrimage')
    assert spec.parameters['candidate_positions'] == {'dormouse': (81, 206)}
    assert spec.to_dict()['parameters']['fixed_cribs'] == [['uncomfortable', 188]]
    assert request.effective_seed == 2026

@pytest.mark.parametrize('kwargs, error', [({'fixed_cribs': 'word'}, TypeError), ({'fixed_cribs': (('bad word', 0),)}, ValueError), ({'fixed_cribs': (('word', True),)}, TypeError), ({'candidate_words': 'word'}, TypeError), ({'candidate_words': ('word',), 'candidate_positions': {'other': (0,)}}, ValueError), ({'candidate_words': ('word',), 'candidate_positions': {'word': '0'}}, TypeError), ({'fixed_cribs': (('word', 0),), 'starts': 0}, ValueError), ({}, ValueError)])
def test_builder_rejects_invalid_contracts(kwargs, error):
    with pytest.raises(error):
        api.SolverSpec.two_period_cribs(**kwargs)

def test_special_route_passes_canonical_interruptor_config_to_staged_solver(monkeypatch):
    from rdp.solvers import two_period_cribs as staged
    captured = {}

    def fake_run_two_period_stages(**kwargs):
        captured.update(kwargs)
        return Solution(key=[0] * 12, plaintext=[0, 0, 0], score=0.0, meta={}, stop_reason='done')
    monkeypatch.setattr(staged, 'run_two_period_stages', fake_run_two_period_stages)
    cipher, key = (api.CipherSpec.two_period_vigenere(first_period=5, second_period=7, alphabet_size=29), api.KeySpec.repeating(length=5 + 7))
    solver = api.SolverSpec.two_period_cribs(fixed_cribs=(('a', 0),), starts=1)
    config = api.InterruptorConfig.exact([1])
    result = api.run(problem_input=api.RuneIndexInput(indices=(0, 1, 2), word_lengths=((0, 1), (0, 1), (0, 1))), cipher=cipher, key_space=key, solver=solver, text_direction=api.TextDirection.LEFT_TO_RIGHT, interruptors=config)
    assert isinstance(result, api.RunResult)
    assert captured['interruptors'] is config
    assert captured['interruptors_exact'] is None
    assert captured['interruptors_pool'] is None
    assert captured['interruptors_max'] is None

def test_special_route_passes_search_interruptor_config_without_legacy_projection(monkeypatch):
    from rdp.solvers import two_period_cribs as staged
    captured = {}

    def fake_run_two_period_stages(**kwargs):
        captured.update(kwargs)
        return Solution(key=[0] * 12, plaintext=[0, 0, 0], score=0.0, meta={}, stop_reason='done')
    monkeypatch.setattr(staged, 'run_two_period_stages', fake_run_two_period_stages)
    cipher, key = (api.CipherSpec.two_period_vigenere(first_period=5, second_period=7, alphabet_size=29), api.KeySpec.repeating(length=5 + 7))
    solver = api.SolverSpec.two_period_cribs(fixed_cribs=(('a', 0),), starts=1)
    config = api.InterruptorConfig.search([2, 1], maximum_count=1)
    api.run(problem_input=api.RuneIndexInput(indices=(0, 1, 2), word_lengths=((0, 1), (0, 1), (0, 1))), cipher=cipher, key_space=key, solver=solver, text_direction=api.TextDirection.LEFT_TO_RIGHT, interruptors=config)
    assert captured['interruptors'] is config
    assert captured['interruptors_exact'] is None
    assert captured['interruptors_pool'] is None
    assert captured['interruptors_max'] is None

@pytest.mark.full_assets
def test_real_route_returns_standard_exact_solution_with_installed_assets():
    from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
    word_starts = [index for index, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    word_ends = {index + 1 for index, pair in enumerate(word_breaks1) if int(pair[0]) == int(pair[1]) - 1}
    sample_start = next((index for index in word_starts if index + 308 in word_ends))
    plaintext = np.asarray(plaintext1[sample_start:sample_start + 308], dtype=np.uint8)
    wli = tuple((tuple((int(x) for x in pair)) for pair in word_breaks1[sample_start:sample_start + 308]))
    fixed_cribs = []
    for start, (offset, length) in enumerate(wli):
        if offset != 0:
            continue
        tokens = []
        for value in plaintext[start:start + length]:
            token = Runeglish.pos2latin[int(value)]
            tokens.append('ING' if token == '(I)NG' else token)
        word = ''.join(tokens).lower()
        encoded, _encoded_wli, _runes = Runeglish.encode_english_to_runes(word, direction='ltr')
        if encoded == plaintext[start:start + length].astype(int).tolist():
            fixed_cribs.append((word, start))
    cipher, key = (api.CipherSpec.two_period_vigenere(first_period=13, second_period=31, alphabet_size=29), api.KeySpec.repeating(length=13 + 31))
    known_key = np.asarray([*((5 * index + 3) % 29 for index in range(13)), 0, *((7 * index + 11) % 29 for index in range(1, 31))], dtype=np.uint8)
    ciphertext = api.encrypt(tuple((int(value) for value in plaintext)), cipher=cipher, key=tuple((int(value) for value in known_key)))
    solver = api.SolverSpec.two_period_cribs(fixed_cribs=tuple(fixed_cribs), starts=1, seed=2026)
    result = api.run(problem_input=api.RuneIndexInput(indices=ciphertext, word_lengths=wli), cipher=cipher, key_space=key, solver=solver, text_direction=api.TextDirection.LEFT_TO_RIGHT)
    assert isinstance(result, api.RunResult)
    assert result.key == tuple(int(value) for value in known_key)
    assert result.plaintext == tuple(int(value) for value in plaintext)
    assert result.status.stop_reason is api.advanced.StopReason.CONFIGURED_WORK_LIMIT_REACHED
    assert result.solver_report.details['run_status']['stop_reason'] == 'configured_work_limit_reached'
    assert result.solver_report.solver is api.advanced.SolverKind.TWO_PERIOD_CRIBS
    assert result.solver_report.details['execution_route'] == 'two_period_cribs'
    details = result.solver_report.details['two_period_solve']
    summaries = {row['stage_id']: row for row in details['stage_summaries']}
    assert tuple(summaries) == ('S2', 'B1', 'F1', 'final_union')
    assert summaries['F1']['sweeps'] == 3
    assert summaries['F1']['generated_terminals'] == summaries['F1']['inputs']
    assert summaries['final_union']['generated_terminals'] == 0
    assert summaries['final_union']['mode'] == 'static_rescore'
    assert summaries['final_union']['stop_reason'] == 'static_rescore_completed'
    assert summaries['final_union']['stop_category'] == 'budget'
    assert all((row['stop_reason'] != 'done' for row in summaries.values()))
    counts = details['candidate_counts']
    assert counts['judge_inputs'] >= counts['judge_unique_terminals']
    assert counts['final_union_inputs'] >= counts['final_union_unique_terminals']
    portable_details = result.solver_report.to_json_dict()['details']['two_period_solve']
    report_json = json.dumps(portable_details, sort_keys=True)
    assert 'reference' not in report_json.lower()
    assert 'truth' not in report_json.lower()
