from __future__ import annotations
from rdp import api
from typing import Any, Mapping
import numpy as np
from cipher_development.shared.replay import CandidateReplayContext
from cipher_development.shared.replay_evidence import ReplayEvaluation
from cipher_development.two_period_overlay.config import BenchmarkSpec, CribSpec, DECISION_SCORE, SCORING_CONTRACT, TARGET_BENCHMARK, benchmark_for
from cipher_development.two_period_overlay.keyspace import expand

def _portable_json(value):
    if isinstance(value, Mapping):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value

def make_replay_context(search_case: Any, *, run_id: str, configuration_hash: str, evaluator_provenance: Mapping[str, Any], scoring_contract: Mapping[str, Any] | None=None, decision_score: str=DECISION_SCORE, evaluator_id: str='two_period_overlay_wli_v3') -> CandidateReplayContext:
    benchmark = getattr(search_case, 'benchmark', TARGET_BENCHMARK)
    contract = dict(getattr(search_case, 'scoring_contract', SCORING_CONTRACT) if scoring_contract is None else scoring_contract)
    return CandidateReplayContext.create(campaign_id='two_period_overlay', run_id=run_id, configuration_hash=configuration_hash, evaluator_id=evaluator_id, payload={'benchmark_id': benchmark.benchmark_id, 'benchmark': benchmark.to_json_dict(), 'ciphertext': np.asarray(search_case.ciphertext, dtype=np.uint8).tolist(), 'wli': [list(pair) for pair in search_case.wli], 'crib': np.asarray(search_case.crib, dtype=np.uint8).tolist(), 'particular': np.asarray(search_case.particular, dtype=np.uint8).tolist(), 'basis': np.asarray(search_case.basis, dtype=np.uint8).tolist(), 'free_columns': list(search_case.free_columns), 'decision_score': str(decision_score), 'scoring': _portable_json(contract), 'evaluator_provenance': _portable_json(evaluator_provenance)})

def _benchmark_from_payload(value: Any) -> BenchmarkSpec:
    if not isinstance(value, Mapping):
        raise ValueError('replay benchmark contract must be a mapping')
    gauge = str(value.get('gauge'))
    if gauge != 'B[0]=0':
        raise ValueError('replay benchmark contract does not establish B[0] = 0')
    additional_payload = value.get('additional_cribs', ())
    if not isinstance(additional_payload, (list, tuple)):
        raise ValueError('replay benchmark additional cribs must be a sequence')
    additional_cribs: list[CribSpec] = []
    for row in additional_payload:
        if not isinstance(row, Mapping):
            raise ValueError('replay benchmark crib contract must be a mapping')
        runes = row.get('runes')
        if not isinstance(runes, (list, tuple)):
            raise ValueError('replay benchmark crib runes must be a sequence')
        additional_cribs.append(CribSpec(label=str(row.get('label')), word=str(row.get('word')), start=int(row.get('start')), runes=tuple((int(item) for item in runes))))
    benchmark = BenchmarkSpec(benchmark_id=str(value.get('benchmark_id')), period_a=int(value.get('period_a')), period_b=int(value.get('period_b')), expected_free_dimension=int(value.get('expected_free_dimension')), alphabet_size=int(value.get('alphabet_size')), schedule=str(value.get('schedule')), text_length=int(value.get('text_length')), crib_word=str(value.get('crib_word')), crib_start=int(value.get('crib_start')), additional_cribs=tuple(additional_cribs), additional_cribs_are_exact=bool(value.get('additional_cribs_are_exact', True)))
    if _portable_json(value) != benchmark.to_json_dict():
        raise ValueError('replay benchmark contract is not canonical')
    return benchmark

def _context_benchmark(context: CandidateReplayContext):
    payload = context.payload
    benchmark_id = str(payload.get('benchmark_id'))
    if 'benchmark' not in payload:
        if benchmark_id != 'alice_308_p13_p17':
            raise ValueError('legacy replay context does not identify the P13/P17 target')
        if payload.get('gauge') != 'B[0]=0':
            raise ValueError('legacy replay context does not establish B[0] = 0')
        if (int(payload.get('period_a', -1)), int(payload.get('period_b', -1))) != (TARGET_BENCHMARK.period_a, TARGET_BENCHMARK.period_b):
            raise ValueError('legacy replay periods do not match the P13/P17 target')
        return TARGET_BENCHMARK
    serialized = payload.get('benchmark')
    try:
        benchmark = benchmark_for(benchmark_id)
    except ValueError:
        benchmark = _benchmark_from_payload(serialized)
        if benchmark.benchmark_id != benchmark_id:
            raise ValueError('replay benchmark ID does not match its bound contract')
        return benchmark
    if _portable_json(serialized) != benchmark.to_json_dict():
        raise ValueError('replay benchmark contract does not match the registered ladder')
    return benchmark

def validate_candidate_payload(candidate, context: CandidateReplayContext) -> np.ndarray:
    payload = context.payload
    benchmark = _context_benchmark(context)
    particular = np.asarray(payload['particular'], dtype=np.uint8)
    basis = np.asarray(payload['basis'], dtype=np.uint8)
    variables = np.asarray(candidate.payload['variables'], dtype=np.uint8)
    stored_key = np.asarray(candidate.payload['expanded_key'], dtype=np.uint8)
    strict_ladder_context = 'benchmark' in payload
    candidate_benchmark_id = candidate.payload.get('benchmark_id')
    if strict_ladder_context and candidate_benchmark_id != benchmark.benchmark_id:
        raise ValueError('candidate payload belongs to a different benchmark')
    if particular.shape != (benchmark.key_length,):
        raise ValueError('replay particular solution has the wrong length')
    expected_free_dimension = benchmark.expected_free_dimension if strict_ladder_context else basis.shape[1]
    if basis.shape != (benchmark.key_length, expected_free_dimension):
        raise ValueError('replay basis has the wrong shape')
    if variables.shape != (expected_free_dimension,):
        raise ValueError('stored affine variables have the wrong length')
    if stored_key.shape != (benchmark.key_length,):
        raise ValueError('stored expanded key has the wrong length')
    identity = _portable_json(candidate.identity)
    if identity != {'expanded_key': stored_key.astype(int).tolist()}:
        raise ValueError('candidate identity and payload expanded key disagree')
    rebuilt = expand(variables, particular, basis, benchmark)
    if not np.array_equal(rebuilt, stored_key):
        raise ValueError('candidate variables do not reproduce the stored expanded key')
    if int(stored_key[benchmark.gauge_key_index]) != benchmark.gauge_value:
        raise ValueError('candidate violates the B[0] = 0 gauge')
    return stored_key

def build_replay_evaluator(context: CandidateReplayContext):
    if context.campaign_id != 'two_period_overlay':
        raise ValueError('replay context belongs to a different campaign')
    payload = context.payload
    benchmark = _context_benchmark(context)
    from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig
    from rune_decrypter_prime.core.config.cipher import materialize_cipher_config
    from rune_decrypter_prime.core.engine.builders import build_cipher
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction
    ciphertext = np.asarray(payload['ciphertext'], dtype=np.uint8)
    wli = tuple(((int(a), int(b)) for a, b in payload['wli']))
    crib = np.asarray(payload['crib'], dtype=np.uint8)
    if len(ciphertext) != benchmark.text_length or len(wli) != benchmark.text_length:
        raise ValueError('replay ciphertext, WLI and benchmark lengths differ')
    if len(crib) != len(benchmark.crib_word):
        raise ValueError('replay crib length does not match the benchmark')
    scoring_contract = dict(payload['scoring'])
    spec, key_spec = (api.CipherSpec.from_name('two_period_vigenere', parameters={'period_a': benchmark.period_a, 'period_b': benchmark.period_b, 'schedule': benchmark.schedule, 'alphabet_size': benchmark.alphabet_size}), api.KeySpec.repeating(length=benchmark.period_a + benchmark.period_b))
    cipher = spec
    direction = Direction(str(scoring_contract['encoding_direction']))
    cipher_cfg = materialize_cipher_config(
        cipher=spec,
        key_space=key_spec,
        ciphertext=ciphertext,
        word_lengths=wli,
        compute_device=api.ComputeDevice.CPU,
        text_direction=api.TextDirection(str(direction.value)),
    )
    fixed_chars = {benchmark.crib_start + index: [int(value)] for index, value in enumerate(crib)}
    for extra in benchmark.additional_cribs:
        fixed_chars.update({extra.start + index: [int(value)] for index, value in enumerate(extra.runes)})
    hard_crib = HardCribConfig(enabled=bool(scoring_contract['hard_crib']), fixed_chars=fixed_chars)
    scoring_values = _portable_json(scoring_contract)
    if scoring_values.get('char_weights') or scoring_values.get('wli_weights'):
        scoring_values.pop('weights', None)
    scoring_values['encoding_dir'] = direction
    scoring_values['hard_crib'] = hard_crib
    scoring_values.pop('encoding_direction', None)
    scoring = api.ScoringConfig.from_dict({**scoring_values})
    problem = DecryptionProblem(cipher=build_cipher(cipher_cfg), scorer=build_scorer(cipher_cfg, scoring), c_cfg=cipher_cfg, s_cfg=scoring, enable_telemetry=False)
    decision_score = str(payload.get('decision_score', DECISION_SCORE))

    def evaluator(candidate, replay_context):
        stored_key = validate_candidate_payload(candidate, replay_context)
        score = float(np.asarray(problem.evaluate_keys(stored_key[None, :]))[0])
        return ReplayEvaluation(scores={decision_score: score}, stable_metrics={'candidate_id': candidate.candidate_id, 'benchmark_id': benchmark.benchmark_id, 'payload_valid': True, 'gauge_valid': True})
    return evaluator
