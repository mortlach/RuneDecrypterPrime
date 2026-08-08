from __future__ import annotations

"""Deterministic tutorial-only P13/P31 fixture.

This module constructs ciphertext for a reproducible demonstration. Reference
plaintext and key values are never passed to the production solver.
"""

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

from rdp import api
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext1, word_breaks1


TEXT_LENGTH = 308
PERIOD_A = 13
PERIOD_B = 31
ALPHABET_SIZE = 29


@dataclass(frozen=True, slots=True)
class TwoPeriodDemoFixture:
    ciphertext: tuple[int, ...]
    wli: tuple[tuple[int, int], ...]
    reference_plaintext: tuple[int, ...]
    reference_key: tuple[int, ...]
    reference_interruptors: tuple[int, ...] = ()


def build_demo_fixture(
    cipher_spec: Any,
    *,
    interruptors: Sequence[int] = (),
) -> TwoPeriodDemoFixture:
    starts = [index for index, pair in enumerate(word_breaks1) if int(pair[0]) == 0]
    ends = {
        index + 1
        for index, pair in enumerate(word_breaks1)
        if int(pair[0]) == int(pair[1]) - 1
    }
    sample_start = next(index for index in starts if index + TEXT_LENGTH in ends)
    plaintext = np.asarray(
        plaintext1[sample_start : sample_start + TEXT_LENGTH], dtype=np.uint8
    )
    wli = tuple(
        (int(offset), int(length))
        for offset, length in word_breaks1[
            sample_start : sample_start + TEXT_LENGTH
        ]
    )
    reference_key = np.asarray(
        [
            *((5 * index + 3) % ALPHABET_SIZE for index in range(PERIOD_A)),
            0,
            *((7 * index + 11) % ALPHABET_SIZE for index in range(1, PERIOD_B)),
        ],
        dtype=np.uint8,
    )
    ciphertext = api.cipher_instance(cipher_spec).encrypt_single(
        plaintext=plaintext,
        key=reference_key,
        interrupt_idx=(
            None
            if not interruptors
            else np.asarray(tuple(interruptors), dtype=np.intp)
        ),
    )
    return TwoPeriodDemoFixture(
        ciphertext=tuple(int(value) for value in ciphertext),
        wli=wli,
        reference_plaintext=tuple(int(value) for value in plaintext),
        reference_key=tuple(int(value) for value in reference_key),
        reference_interruptors=tuple(int(value) for value in interruptors),
    )


__all__ = [
    "ALPHABET_SIZE",
    "PERIOD_A",
    "PERIOD_B",
    "TEXT_LENGTH",
    "TwoPeriodDemoFixture",
    "build_demo_fixture",
]
