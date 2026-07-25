from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np

from cipher_development.two_period_overlay.config import (
    CRIB_RUNES,
    SCORING_CONTRACT,
    TARGET_BENCHMARK,
    BenchmarkSpec,
)
from cipher_development.two_period_overlay.keyspace import (
    crib_space,
    deterministic_key,
    expand,
)

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
    cipher: Any
    ciphertext: np.ndarray
    plaintext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    true_key: np.ndarray


def _scoring_kwargs(
    direction_type: Any,
    hard_crib: Any,
    scoring_contract: Mapping[str, Any] = SCORING_CONTRACT,
) -> dict[str, Any]:
    contract = dict(scoring_contract)
    return {
        "objective": contract["objective"],
        "include_char": bool(contract["include_char"]),
        "use_word_breaks": bool(contract["use_word_breaks"]),
        "n_char": int(contract["n_char"]),
        "n_wli": int(contract["n_wli"]),
        "char_weights": dict(contract["char_weights"]),
        "wli_weights": dict(contract["wli_weights"]),
        "encoding_dir": direction_type(str(contract["encoding_direction"])),
        "hard_crib": hard_crib,
    }


def build_rdp_case(
    benchmark: BenchmarkSpec = TARGET_BENCHMARK,
    *,
    scoring_contract: Mapping[str, Any] | None = None,
) -> tuple[SearchCase, ReferenceCase]:
    from rune_decrypter_prime.api import by_name, cipher_instance
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction
    from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1

    contract = dict(SCORING_CONTRACT if scoring_contract is None else scoring_contract)

    starts = [i for i, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    ends = {i + 1 for i, pair in enumerate(word_breaks1) if int(pair[0]) == int(pair[1]) - 1}
    sample_start = next(
        (i for i in starts if i + benchmark.text_length in ends), None
    )
    if sample_start is None:
        raise ValueError(
            f"RDP plaintext1 has no exact whole-word {benchmark.text_length}-rune slice"
        )
    plaintext = np.asarray(
        plaintext1[sample_start: sample_start + benchmark.text_length], dtype=np.uint8
    )
    wli = tuple(
        (int(a), int(b))
        for a, b in word_breaks1[sample_start: sample_start + benchmark.text_length]
    )
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    start = benchmark.crib_start
    if not np.array_equal(plaintext[start: start + len(crib)], crib):
        raise ValueError(f"RDP asset no longer matches crib {benchmark.crib_word!r}")
    if wli[start: start + len(crib)] != tuple((i, len(crib)) for i in range(len(crib))):
        raise ValueError(
            f"RDP WLI no longer describes complete crib {benchmark.crib_word!r}"
        )
    for extra in benchmark.additional_cribs:
        expected = np.asarray(extra.runes, dtype=np.uint8)
        if (
            benchmark.additional_cribs_are_exact
            and not np.array_equal(plaintext[extra.start:extra.stop], expected)
        ):
            raise ValueError(f"RDP asset no longer matches extra crib {extra.word!r}")
        if wli[extra.start:extra.stop] != tuple(
            (i, len(extra.runes)) for i in range(len(extra.runes))
        ):
            raise ValueError(f"RDP WLI no longer describes extra crib {extra.word!r}")

    spec, key_spec = by_name.cipher_with_key(
        "two_period_vigenere",
        period_a=benchmark.period_a,
        period_b=benchmark.period_b,
        schedule=benchmark.schedule,
        alphabet_size=benchmark.alphabet_size,
        default_key=True,
    )
    cipher = cipher_instance(spec)
    true_key = deterministic_key(benchmark)
    ciphertext = cipher.encrypt_single(plaintext=plaintext, key=true_key)
    if not np.array_equal(cipher.decrypt_single(ciphertext=ciphertext, key=true_key), plaintext):
        raise RuntimeError("known-key roundtrip failed")
    particular, basis, free = crib_space(ciphertext, crib, benchmark)
    true_variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    if len(free) != benchmark.expected_free_dimension:
        raise RuntimeError(
            f"{benchmark.benchmark_id} produced free dimension {len(free)}, expected "
            f"{benchmark.expected_free_dimension}"
        )
    if benchmark.additional_cribs_are_exact and not np.array_equal(
        expand(true_variables, particular, basis, benchmark), true_key
    ):
        raise RuntimeError("crib parameterisation does not reproduce the gauge-fixed benchmark key")

    direction = Direction(str(contract["encoding_direction"]))
    cipher_cfg = build_cipher_config(
        cipher=spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=[list(pair) for pair in wli],
        device=Device.CPU,
        encoding_dir=direction,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    fixed_chars = {start + i: [int(x)] for i, x in enumerate(crib.tolist())}
    for extra in benchmark.additional_cribs:
        fixed_chars.update({extra.start + i: [int(x)] for i, x in enumerate(extra.runes)})
    hard_crib = HardCribConfig(
        enabled=bool(contract["hard_crib"]),
        fixed_chars=fixed_chars,
    )
    scoring = ScoringConfig(**_scoring_kwargs(Direction, hard_crib, contract))
    problem = DecryptionProblem(
        cipher=cipher,
        scorer=build_scorer(cipher_cfg, scoring),
        c_cfg=cipher_cfg,
        s_cfg=scoring,
        enable_telemetry=True,
    )

    def evaluate_variables(values: np.ndarray) -> np.ndarray:
        keys = expand(values, particular, basis, benchmark)
        batch = keys[None, :] if keys.ndim == 1 else keys
        return np.asarray(problem.evaluate_keys(batch), dtype=np.float64)

    return (
        SearchCase(
            benchmark=benchmark,
            sample_start=sample_start,
            ciphertext=ciphertext,
            wli=wli,
            crib=crib,
            particular=particular,
            basis=basis,
            free_columns=free,
            evaluate_variables=evaluate_variables,
            scoring_contract=contract,
        ),
        ReferenceCase(
            benchmark=benchmark,
            cipher=cipher,
            ciphertext=ciphertext,
            plaintext=plaintext,
            wli=wli,
            true_key=true_key,
        ),
    )


def reference_metrics(
    reference: ReferenceCase,
    variables: np.ndarray,
    particular: np.ndarray,
    basis: np.ndarray,
) -> dict[str, Any]:
    benchmark = reference.benchmark
    key = expand(variables, particular, basis, benchmark)
    decoded = reference.cipher.decrypt_single(ciphertext=reference.ciphertext, key=key)
    zeros = np.zeros(benchmark.text_length, dtype=np.uint8)
    word_starts = [
        (i, length) for i, (offset, length) in enumerate(reference.wli) if offset == 0
    ]
    return {
        "exact_plaintext": bool(np.array_equal(decoded, reference.plaintext)),
        "rune_matches": int(np.count_nonzero(decoded == reference.plaintext)),
        "complete_word_matches": int(sum(
            np.array_equal(decoded[i:i + length], reference.plaintext[i:i + length])
            for i, length in word_starts
        )),
        "complete_words_total": len(word_starts),
        "canonical_key_equal": bool(np.array_equal(key, reference.true_key)),
        "combined_shift_equal": bool(np.array_equal(
            reference.cipher.encrypt_single(plaintext=zeros, key=key),
            reference.cipher.encrypt_single(plaintext=zeros, key=reference.true_key),
        )),
    }
