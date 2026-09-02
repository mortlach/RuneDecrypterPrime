from __future__ import annotations
from rdp import api
from dataclasses import dataclass
from typing import Any, Callable, Mapping
import numpy as np
from cipher_development.two_period_overlay.config import CRIB_RUNES, SCORING_CONTRACT, TARGET_BENCHMARK, BenchmarkSpec
from cipher_development.two_period_overlay.keyspace import crib_space, deterministic_key, expand
ScoreVariables = Callable[[np.ndarray], np.ndarray]

@dataclass(frozen=True, slots=True)
class SearchCase:
    benchmark: BenchmarkSpec
    sample_start: int
    ciphertext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    crib: np.ndarray
    particular: np.ndarray
    basis: np.ndarray
    free_columns: tuple[int, ...]
    evaluate_variables: ScoreVariables
    scoring_contract: Mapping[str, Any]

@dataclass(frozen=True, slots=True)
class ReferenceCase:
    benchmark: BenchmarkSpec
    cipher: api.CipherSpec
    ciphertext: np.ndarray
    plaintext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    true_key: np.ndarray

def _scoring_kwargs(direction_type: Any, hard_crib: Any, scoring_contract: Mapping[str, Any]=SCORING_CONTRACT) -> api.ScoringConfig:
    contract = dict(scoring_contract)
    return api.ScoringConfig(character_lane_enabled=bool(contract['include_char']), word_length_lane_enabled=bool(contract['use_word_breaks']), character_order_weights=dict(contract['char_weights']), word_length_order_weights=dict(contract['wli_weights']), objective=api.advanced.ScoringObjective.percentile_log_probability(window_size=10))


def build_rdp_case(
    benchmark: BenchmarkSpec = TARGET_BENCHMARK,
    *,
    scoring_contract: Mapping[str, Any] | None = None,
) -> tuple[SearchCase, ReferenceCase]:
    from rdp.core.config.hard_crib import HardCribConfig
    from rdp.core.config.cipher import materialize_cipher_config
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.engine.builders import build_cipher
    from rdp.core.problem.runtime import DecryptionProblem
    from rdp.core.types import Direction
    from rune_decrypter_prime.data.cipher_tests.plaintext import (
        plaintext1,
        word_breaks1,
    )

    contract = dict(SCORING_CONTRACT if scoring_contract is None else scoring_contract)
    starts = [i for i, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    ends = {i + 1 for i, pair in enumerate(word_breaks1) if int(pair[0]) == int(pair[1]) - 1}
    sample_start = next((i for i in starts if i + benchmark.text_length in ends), None)
    if sample_start is None:
        raise ValueError(f'RDP plaintext1 has no exact whole-word {benchmark.text_length}-rune slice')
    plaintext = np.asarray(plaintext1[sample_start:sample_start + benchmark.text_length], dtype=np.uint8)
    wli = tuple(((int(a), int(b)) for a, b in word_breaks1[sample_start:sample_start + benchmark.text_length]))
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    start = benchmark.crib_start
    if not np.array_equal(plaintext[start:start + len(crib)], crib):
        raise ValueError(f'RDP asset no longer matches crib {benchmark.crib_word!r}')
    if wli[start:start + len(crib)] != tuple(((i, len(crib)) for i in range(len(crib)))):
        raise ValueError(f'RDP WLI no longer describes complete crib {benchmark.crib_word!r}')
    for extra in benchmark.additional_cribs:
        expected = np.asarray(extra.runes, dtype=np.uint8)
        if benchmark.additional_cribs_are_exact and (not np.array_equal(plaintext[extra.start:extra.stop], expected)):
            raise ValueError(f'RDP asset no longer matches extra crib {extra.word!r}')
        if wli[extra.start:extra.stop] != tuple(((i, len(extra.runes)) for i in range(len(extra.runes)))):
            raise ValueError(f'RDP WLI no longer describes extra crib {extra.word!r}')
    spec, key_spec = (api.CipherSpec.two_period_vigenere(first_period=benchmark.period_a, second_period=benchmark.period_b, schedule=api.advanced.ScheduledStreamSchedule(str(benchmark.schedule)), alphabet_size=benchmark.alphabet_size), api.KeySpec.repeating(length=benchmark.period_a + benchmark.period_b))
    cipher = spec
    true_key = deterministic_key(benchmark)
    ciphertext = np.asarray(api.encrypt(tuple(int(value) for value in plaintext), cipher=cipher, key=tuple(int(value) for value in true_key)), dtype=np.uint8)
    if not np.array_equal(api.decrypt(tuple(int(value) for value in ciphertext), cipher=cipher, key=tuple(int(value) for value in true_key)), plaintext):
        raise RuntimeError('known-key roundtrip failed')
    particular, basis, free = crib_space(ciphertext, crib, benchmark)
    true_variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    if len(free) != benchmark.expected_free_dimension:
        raise RuntimeError(f'{benchmark.benchmark_id} produced free dimension {len(free)}, expected {benchmark.expected_free_dimension}')
    if benchmark.additional_cribs_are_exact and (not np.array_equal(expand(true_variables, particular, basis, benchmark), true_key)):
        raise RuntimeError('crib parameterisation does not reproduce the gauge-fixed benchmark key')
    direction = Direction(str(contract['encoding_direction']))
    cipher_cfg = materialize_cipher_config(
        cipher=spec,
        key_space=key_spec,
        ciphertext=ciphertext,
        word_lengths=wli,
        compute_device=api.ComputeDevice.CPU,
        text_direction=api.TextDirection(str(direction.value)),
    )
    fixed_characters = {start + i: [int(x)] for i, x in enumerate(crib.tolist())}
    for extra in benchmark.additional_cribs:
        fixed_characters.update(
            {extra.start + i: [int(x)] for i, x in enumerate(extra.runes)}
        )
    hard_crib = HardCribConfig(
        enabled=bool(contract["hard_crib"]), fixed_characters=fixed_characters
    )
    scoring = api.ScoringConfig(hard_crib=hard_crib)
    problem = DecryptionProblem(
        cipher=build_cipher(cipher_cfg),
        scorer=build_scorer(cipher_cfg, scoring),
        c_cfg=cipher_cfg,
        s_cfg=scoring,
        enable_telemetry=True,
    )

    def evaluate_variables(values: np.ndarray) -> np.ndarray:
        keys = expand(values, particular, basis, benchmark)
        batch = keys[None, :] if keys.ndim == 1 else keys
        return np.asarray(problem.evaluate_keys(batch), dtype=np.float64)
    return (SearchCase(benchmark=benchmark, sample_start=sample_start, ciphertext=ciphertext, wli=wli, crib=crib, particular=particular, basis=basis, free_columns=free, evaluate_variables=evaluate_variables, scoring_contract=contract), ReferenceCase(benchmark=benchmark, cipher=cipher, ciphertext=ciphertext, plaintext=plaintext, wli=wli, true_key=true_key))

def reference_metrics(reference: ReferenceCase, variables: np.ndarray, particular: np.ndarray, basis: np.ndarray) -> dict[str, Any]:
    benchmark = reference.benchmark
    key = expand(variables, particular, basis, benchmark)
    decoded = np.asarray(api.decrypt(tuple(int(value) for value in reference.ciphertext), cipher=reference.cipher, key=tuple(int(value) for value in key)), dtype=np.uint8)
    zeros = np.zeros(benchmark.text_length, dtype=np.uint8)
    word_starts = [(i, length) for i, (offset, length) in enumerate(reference.wli) if offset == 0]
    zero_input = tuple(int(value) for value in zeros)
    return {'exact_plaintext': bool(np.array_equal(decoded, reference.plaintext)), 'rune_matches': int(np.count_nonzero(decoded == reference.plaintext)), 'complete_word_matches': int(sum((np.array_equal(decoded[i:i + length], reference.plaintext[i:i + length]) for i, length in word_starts))), 'complete_words_total': len(word_starts), 'canonical_key_equal': bool(np.array_equal(key, reference.true_key)), 'combined_shift_equal': bool(np.array_equal(api.encrypt(zero_input, cipher=reference.cipher, key=tuple(int(value) for value in key)), api.encrypt(zero_input, cipher=reference.cipher, key=tuple(int(value) for value in reference.true_key))))}
