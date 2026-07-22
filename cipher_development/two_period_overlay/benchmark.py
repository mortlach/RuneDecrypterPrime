from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np

from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    CRIB_RUNES,
    CRIB_START,
    CRIB_WORD,
    PERIOD_A,
    PERIOD_B,
    SCORING_CONTRACT,
    TEXT_LENGTH,
)
from cipher_development.two_period_overlay.keyspace import (
    crib_space,
    deterministic_key,
    expand,
)

ScoreVariables = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True, slots=True)
class SearchCase:
    sample_start: int
    ciphertext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    crib: np.ndarray
    particular: np.ndarray
    basis: np.ndarray
    free_columns: tuple[int, ...]
    evaluate_variables: ScoreVariables


@dataclass(frozen=True, slots=True)
class ReferenceCase:
    cipher: Any
    ciphertext: np.ndarray
    plaintext: np.ndarray
    wli: tuple[tuple[int, int], ...]
    true_key: np.ndarray


def build_rdp_case() -> tuple[SearchCase, ReferenceCase]:
    from rune_decrypter_prime.api import by_name, cipher_instance
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction
    from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1

    starts = [i for i, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    ends = {i + 1 for i, pair in enumerate(word_breaks1) if int(pair[0]) == int(pair[1]) - 1}
    sample_start = next((i for i in starts if i + TEXT_LENGTH in ends), None)
    if sample_start is None:
        raise ValueError("RDP plaintext1 has no exact whole-word 308-rune slice")
    plaintext = np.asarray(plaintext1[sample_start: sample_start + TEXT_LENGTH], dtype=np.uint8)
    wli = tuple((int(a), int(b)) for a, b in word_breaks1[sample_start: sample_start + TEXT_LENGTH])
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    if not np.array_equal(plaintext[CRIB_START: CRIB_START + len(crib)], crib):
        raise ValueError(f"RDP asset no longer matches crib {CRIB_WORD!r}")
    if wli[CRIB_START: CRIB_START + len(crib)] != tuple((i, len(crib)) for i in range(len(crib))):
        raise ValueError(f"RDP WLI no longer describes complete crib {CRIB_WORD!r}")

    spec, key_spec = by_name.cipher_with_key(
        "two_period_vigenere",
        period_a=PERIOD_A,
        period_b=PERIOD_B,
        schedule="overlay",
        alphabet_size=ALPHABET_SIZE,
        default_key=True,
    )
    cipher = cipher_instance(spec)
    true_key = deterministic_key()
    ciphertext = cipher.encrypt_single(plaintext=plaintext, key=true_key)
    if not np.array_equal(cipher.decrypt_single(ciphertext=ciphertext, key=true_key), plaintext):
        raise RuntimeError("known-key roundtrip failed")
    particular, basis, free = crib_space(ciphertext, crib)
    true_variables = np.asarray([true_key[index] for index in free], dtype=np.uint8)
    if len(free) != 16 or not np.array_equal(expand(true_variables, particular, basis), true_key):
        raise RuntimeError("crib parameterisation does not reproduce the gauge-fixed benchmark key")

    cipher_cfg = build_cipher_config(
        cipher=spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=[list(pair) for pair in wli],
        device=Device.CPU,
        encoding_dir=Direction.LTR,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    hard_crib = HardCribConfig(
        enabled=True,
        fixed_chars={CRIB_START + i: [int(x)] for i, x in enumerate(crib.tolist())},
    )
    scoring = ScoringConfig(
        objective=SCORING_CONTRACT["objective"],
        include_char=True,
        use_word_breaks=True,
        n_char=4,
        n_wli=4,
        char_weights={3: 0.5, 4: 0.5},
        wli_weights={3: 0.5, 4: 0.5},
        encoding_dir=Direction.LTR,
        hard_crib=hard_crib,
    )
    problem = DecryptionProblem(
        cipher=cipher,
        scorer=build_scorer(cipher_cfg, scoring),
        c_cfg=cipher_cfg,
        s_cfg=scoring,
        enable_telemetry=True,
    )

    def evaluate_variables(values: np.ndarray) -> np.ndarray:
        keys = expand(values, particular, basis)
        batch = keys[None, :] if keys.ndim == 1 else keys
        return np.asarray(problem.evaluate_keys(batch), dtype=np.float64)

    return (
        SearchCase(
            sample_start=sample_start,
            ciphertext=ciphertext,
            wli=wli,
            crib=crib,
            particular=particular,
            basis=basis,
            free_columns=free,
            evaluate_variables=evaluate_variables,
        ),
        ReferenceCase(
            cipher=cipher,
            ciphertext=ciphertext,
            plaintext=plaintext,
            wli=wli,
            true_key=true_key,
        ),
    )


def reference_metrics(reference: ReferenceCase, variables: np.ndarray, particular: np.ndarray, basis: np.ndarray) -> dict[str, Any]:
    key = expand(variables, particular, basis)
    decoded = reference.cipher.decrypt_single(ciphertext=reference.ciphertext, key=key)
    zeros = np.zeros(TEXT_LENGTH, dtype=np.uint8)
    word_starts = [(i, length) for i, (offset, length) in enumerate(reference.wli) if offset == 0]
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


def normalise_baseline_result(payload: Mapping[str, Any], source_sha256: str, source_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(char not in "0123456789abcdef" for char in source_sha256)):
        raise ValueError("source_sha256 must be a 64-character lowercase hexadecimal digest")
    if payload.get("schema") != "rdp.two_period_crib_solver.plateau_comparison.v1":
        raise ValueError("baseline result has an unsupported schema")
    config = payload.get("config")
    if not isinstance(config, Mapping):
        raise ValueError("baseline result has no config mapping")
    if tuple(config.get("periods", ())) != (PERIOD_A, PERIOD_B):
        raise ValueError("baseline result periods do not match P13/P17")
    if config.get("alphabet_size") != ALPHABET_SIZE:
        raise ValueError("baseline result alphabet size does not match")
    text = config.get("text", {})
    crib = config.get("crib", {})
    if text.get("length") != TEXT_LENGTH or crib.get("word") != CRIB_WORD or crib.get("compact_core_offset") != CRIB_START:
        raise ValueError("baseline result benchmark contract does not match")
    best = payload.get("best_result")
    if not isinstance(best, Mapping):
        raise ValueError("baseline result has no best_result mapping")
    reference_names = {
        "exact_plaintext", "rune_matches", "complete_word_matches", "complete_words_total",
        "canonical_key_equal", "combined_shift_equal",
    }
    reference = {name: best[name] for name in reference_names if name in best}
    summary = {
        "source_filename": Path(source_name).name,
        "source_sha256": source_sha256,
        "historical_schema": payload["schema"],
        "historical_status": payload.get("status"),
        "historical_decision": payload.get("decision"),
        "historical_stop_reason": payload.get("stop_reason"),
        "historical_evaluations": payload.get("evaluations"),
        "historical_elapsed_s": payload.get("elapsed_seconds"),
        "best_phase": best.get("phase"),
        "best_score": best.get("score"),
    }
    return summary, reference

