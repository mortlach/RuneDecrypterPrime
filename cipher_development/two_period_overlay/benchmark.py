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


def _scoring_kwargs(direction_type: Any, hard_crib: Any) -> dict[str, Any]:
    return {
        "objective": SCORING_CONTRACT["objective"],
        "include_char": bool(SCORING_CONTRACT["include_char"]),
        "use_word_breaks": bool(SCORING_CONTRACT["use_word_breaks"]),
        "n_char": int(SCORING_CONTRACT["n_char"]),
        "n_wli": int(SCORING_CONTRACT["n_wli"]),
        "char_weights": dict(SCORING_CONTRACT["char_weights"]),
        "wli_weights": dict(SCORING_CONTRACT["wli_weights"]),
        "encoding_dir": direction_type(str(SCORING_CONTRACT["encoding_direction"])),
        "hard_crib": hard_crib,
    }


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
    wli = tuple(
        (int(a), int(b))
        for a, b in word_breaks1[sample_start: sample_start + TEXT_LENGTH]
    )
    crib = np.asarray(CRIB_RUNES, dtype=np.uint8)
    if not np.array_equal(plaintext[CRIB_START: CRIB_START + len(crib)], crib):
        raise ValueError(f"RDP asset no longer matches crib {CRIB_WORD!r}")
    if wli[CRIB_START: CRIB_START + len(crib)] != tuple(
        (i, len(crib)) for i in range(len(crib))
    ):
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

    direction = Direction(str(SCORING_CONTRACT["encoding_direction"]))
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
    hard_crib = HardCribConfig(
        enabled=bool(SCORING_CONTRACT["hard_crib"]),
        fixed_chars={CRIB_START + i: [int(x)] for i, x in enumerate(crib.tolist())},
    )
    scoring = ScoringConfig(**_scoring_kwargs(Direction, hard_crib))
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


def reference_metrics(
    reference: ReferenceCase,
    variables: np.ndarray,
    particular: np.ndarray,
    basis: np.ndarray,
) -> dict[str, Any]:
    key = expand(variables, particular, basis)
    decoded = reference.cipher.decrypt_single(ciphertext=reference.ciphertext, key=key)
    zeros = np.zeros(TEXT_LENGTH, dtype=np.uint8)
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


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"baseline result has no {name} mapping")
    return value


def _validate_gauge(value: Any) -> None:
    if isinstance(value, str):
        token = value.replace(" ", "").lower()
        if token in {"b[0]=0", "b0=0"}:
            return
    if isinstance(value, Mapping):
        if value.get("stream") == "B" and value.get("index") == 0 and value.get("value") == 0:
            return
        if value.get("b0") == 0:
            return
    raise ValueError("baseline result gauge does not establish B[0] = 0")


def _validate_historical_scoring(scoring: Mapping[str, Any]) -> None:
    required = {
        "objective": SCORING_CONTRACT["objective"],
        "include_char": SCORING_CONTRACT["include_char"],
        "use_word_breaks": SCORING_CONTRACT["use_word_breaks"],
        "n_char": SCORING_CONTRACT["n_char"],
        "n_wli": SCORING_CONTRACT["n_wli"],
        "encoding_direction": SCORING_CONTRACT["encoding_direction"],
        "hard_crib": SCORING_CONTRACT["hard_crib"],
    }
    for name, expected in required.items():
        if scoring.get(name) != expected:
            raise ValueError(f"baseline scoring field {name!r} does not match")
    for name in ("char_weights", "wli_weights"):
        actual = {int(k): float(v) for k, v in _mapping(scoring.get(name), name).items()}
        expected = {int(k): float(v) for k, v in SCORING_CONTRACT[name].items()}
        if actual != expected:
            raise ValueError(f"baseline scoring field {name!r} does not match")


def normalise_baseline_result(
    payload: Mapping[str, Any],
    source_sha256: str,
    source_name: str,
    runner_sha256: str,
    runner_name: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    for value, name in ((source_sha256, "source_sha256"), (runner_sha256, "runner_sha256")):
        if (not isinstance(value, str) or len(value) != 64
                or any(char not in "0123456789abcdef" for char in value)):
            raise ValueError(f"{name} must be a 64-character lowercase hexadecimal digest")
    if payload.get("schema") != "rdp.two_period_crib_solver.plateau_comparison.v1":
        raise ValueError("baseline result has an unsupported schema")
    if payload.get("status") != "completed":
        raise ValueError("baseline result must have completed status")
    config = _mapping(payload.get("config"), "config")
    if tuple(config.get("periods", ())) != (PERIOD_A, PERIOD_B):
        raise ValueError("baseline result periods do not match P13/P17")
    if config.get("alphabet_size") != ALPHABET_SIZE:
        raise ValueError("baseline result alphabet size does not match")
    if config.get("schedule") != "overlay":
        raise ValueError("baseline result schedule does not match overlay")
    _validate_gauge(config.get("gauge"))
    text = _mapping(config.get("text"), "config.text")
    crib = _mapping(config.get("crib"), "config.crib")
    if (text.get("length") != TEXT_LENGTH
            or crib.get("word") != CRIB_WORD
            or crib.get("compact_core_offset") != CRIB_START):
        raise ValueError("baseline result benchmark contract does not match")
    _validate_historical_scoring(_mapping(config.get("scoring"), "config.scoring"))

    phases = payload.get("phases")
    if isinstance(phases, Mapping):
        phase_names = set(str(name) for name in phases)
    elif isinstance(phases, (list, tuple)):
        phase_names = {
            str(item.get("phase"))
            for item in phases
            if isinstance(item, Mapping) and item.get("phase")
        }
    else:
        raise ValueError("baseline result has no phase evidence")
    required_phases = {"coordinate", "short_sa", "coordinate_beam"}
    if not required_phases.issubset(phase_names):
        raise ValueError("baseline result does not contain the expected three historical phases")

    best = _mapping(payload.get("best_result"), "best_result")
    reference_names = {
        "exact_plaintext",
        "rune_matches",
        "complete_word_matches",
        "complete_words_total",
        "canonical_key_equal",
        "combined_shift_equal",
    }
    missing_reference = sorted(reference_names - set(best))
    if missing_reference:
        raise ValueError(f"baseline best_result is missing reference fields: {missing_reference}")
    reference = {name: best[name] for name in sorted(reference_names)}
    summary = {
        "source_filename": Path(source_name).name,
        "source_sha256": source_sha256,
        "runner_filename": Path(runner_name).name,
        "runner_sha256": runner_sha256,
        "historical_schema": payload["schema"],
        "historical_status": payload["status"],
        "historical_decision": payload.get("decision"),
        "historical_stop_reason": payload.get("stop_reason"),
        "historical_evaluations": payload.get("evaluations"),
        "historical_elapsed_s": payload.get("elapsed_seconds"),
        "best_phase": best.get("phase"),
        "best_score": best.get("score"),
    }
    return summary, reference
