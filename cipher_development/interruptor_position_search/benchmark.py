from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Sequence

import numpy as np

from rune_decrypter_prime.api import Direction, cipher_instance
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1
from rune_decrypter_prime.utils.runeglish import Runeglish

from .config import (
    DIRECTION,
    INTERRUPTOR_LATIN_SYMBOL,
    KEY_VALUES,
    TRUE_INTERRUPT_COUNT,
)


@dataclass(frozen=True, slots=True)
class InterruptorBenchmark:
    plaintext: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]
    ciphertext: tuple[int, ...]
    key: tuple[int, ...]
    symbol_index: int
    true_positions: tuple[int, ...]
    pool: tuple[int, ...]

    @property
    def text_length(self) -> int:
        return len(self.plaintext)

    def public_context(self) -> dict:
        return {
            "text_length": self.text_length,
            "wli_length": len(self.wli),
            "key_length": len(self.key),
            "interruptor_symbol_latin": INTERRUPTOR_LATIN_SYMBOL,
            "interruptor_symbol_index": self.symbol_index,
            "pool_size": len(self.pool),
            "ciphertext_sha256": _hash_ints(self.ciphertext),
            "wli_sha256": hashlib.sha256(repr(self.wli).encode("utf-8")).hexdigest(),
        }


def _hash_ints(values: Sequence[int]) -> str:
    return hashlib.sha256(bytes(int(v) for v in values)).hexdigest()


def _symbol_index() -> int:
    idx, _wli, _runes = Runeglish.encode_english_to_runes(
        INTERRUPTOR_LATIN_SYMBOL,
        direction=DIRECTION,
    )
    if len(idx) != 1:
        raise RuntimeError(
            f"{INTERRUPTOR_LATIN_SYMBOL!r} did not encode to exactly one rune"
        )
    return int(idx[0])


def _spread_positions(occurrences: Sequence[int], count: int) -> tuple[int, ...]:
    if len(occurrences) < count:
        raise RuntimeError(
            f"need at least {count} plaintext occurrences, found {len(occurrences)}"
        )
    # Deterministic interior quantiles avoid selecting only clustered early symbols.
    numerators = tuple(1 + 2 * i for i in range(count))
    denominator = 2 * count
    selected = []
    for numerator in numerators:
        index = min(
            len(occurrences) - 1,
            (numerator * len(occurrences)) // denominator,
        )
        selected.append(int(occurrences[index]))
    result = tuple(sorted(set(selected)))
    if len(result) != count:
        raise RuntimeError("deterministic position selection collapsed duplicates")
    return result


def build_benchmark() -> InterruptorBenchmark:
    plaintext = tuple(int(v) for v in plaintext1)
    wli = tuple((int(a), int(b)) for a, b in word_breaks1)
    if len(plaintext) != len(wli):
        raise RuntimeError("plaintext and WLI lengths differ")

    symbol = _symbol_index()
    occurrences = tuple(i for i, value in enumerate(plaintext) if value == symbol)
    true_positions = _spread_positions(occurrences, TRUE_INTERRUPT_COUNT)

    key = tuple(int(v) for v in KEY_VALUES)
    cipher = cipher_instance(
        "vigenere",
        key_length=len(key),
        text_transposition=Direction(DIRECTION).value,
    )
    ciphertext_arr = cipher.encrypt_single(
        plaintext=np.asarray(plaintext, dtype=np.uint8),
        key=np.asarray(key, dtype=np.uint8),
        interrupt_idx=list(true_positions),
    )
    ciphertext = tuple(int(v) for v in ciphertext_arr.tolist())
    pool = tuple(i for i, value in enumerate(ciphertext) if value == symbol)

    if not set(true_positions).issubset(set(pool)):
        raise RuntimeError("true interruptor positions are absent from the symbol pool")
    if len(pool) <= len(true_positions):
        raise RuntimeError("benchmark has no false-positive symbol positions")
    if any(ciphertext[i] != plaintext[i] for i in true_positions):
        raise RuntimeError("interruptor symbols were not preserved")

    return InterruptorBenchmark(
        plaintext=plaintext,
        wli=wli,
        ciphertext=ciphertext,
        key=key,
        symbol_index=symbol,
        true_positions=true_positions,
        pool=pool,
    )
