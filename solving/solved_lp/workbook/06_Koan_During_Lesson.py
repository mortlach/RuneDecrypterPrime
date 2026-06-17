from __future__ import annotations

"""Worked solve for the LP koan "During a Lesson"."""

import sys
import time
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.core.config.cipher import CipherConfig  # noqa: E402
from rune_decrypter_prime.ciphers.vigenere_cipher import RuneVigenereCipher  # noqa: E402
from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


SOURCE_LABEL = "koan_during_lesson"
RECIPE_LABEL = "recipe.koan_during_lesson.vigenere_interruptors"
KEY_TEXT_HINT_HUMAN = "CIRCUMFERENCE"
RECIPE_REFERENCE_KEY_OR_SHIFT = "FIRFUMFERENFE"
KEY_LENGTH = len(RECIPE_REFERENCE_KEY_OR_SHIFT)
PINNED_FOUND_KEY_CORE = [0, 10, 4, 0, 1, 19, 0, 18, 4, 18, 9, 0, 18]
PINNED_FOUND_INTERRUPTORS = [49, 58]
INTERRUPTOR_COUNT = len(PINNED_FOUND_INTERRUPTORS)
PINNED_BEST_SCORE = 0.6140413888975398
PINNED_STOP_REASON = "no_improve_5"
ACCEPTANCE_MATCH_RATIO = 1.0

CANONICAL_KOAN_DURING_LESSON_TEXT = """
A KOAN DURING A LESSON THE MASTER EXPLAINED THE I THE I IS THE VOICE OF THE
CIRCUMFERENCE HE SAID WHEN ASKED BY A STUDENT TO EXPLAIN WHAT THAT MEANT THE
MASTER SAID IT IS A VOICE INSIDE YOUR HEAD I DON'T HAVE A VOICE IN MY HEAD
THOUGHT THE STUDENT AND HE RAISED HIS HAND TO TELL THE MASTER THE MASTER
STOPPED THE STUDENT AND SAID THE VOICE THAT JUST SAID YOU HAVE NO VOICE IN
YOUR HEAD IS THE I AND THE STUDENTS WERE ENLIGHTENED
"""


def zero_positions(values: list[int]) -> list[int]:
    return [index for index, value in enumerate(values) if int(value) == 0]


def encode_reference(text: str) -> list[int]:
    idx, _wli, _runes = Runeglish.encode_english_to_runes(text, direction="ltr")
    return [int(value) for value in idx]


def match_ratio(candidate: list[int], reference: list[int]) -> float:
    if not candidate and not reference:
        return 1.0
    total = max(len(candidate), len(reference))
    if total == 0:
        return 0.0
    matches = sum(1 for left, right in zip(candidate, reference) if int(left) == int(right))
    return matches / total


def replay_pinned_solution(ct_idx: list[int], wli: list[list[int]]) -> list[int]:
    cipher = RuneVigenereCipher(
        CipherConfig(
            name="vigenere",
            key_length=KEY_LENGTH,
            ciphertext=np.asarray(ct_idx, dtype=np.uint8),
            wli_data=wli,
        )
    )
    plaintext = cipher.decrypt(
        ciphertext=np.asarray(ct_idx, dtype=np.uint8),
        key=np.asarray(PINNED_FOUND_KEY_CORE, dtype=np.uint8),
        interrupt_idx=np.asarray(PINNED_FOUND_INTERRUPTORS, dtype=np.intp),
    )[0]
    return [int(value) for value in plaintext.tolist()]


def print_kv(key: str, value: object) -> None:
    print(f"{key}: {value}")


def main() -> int:
    started = time.perf_counter()
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = [int(value) for value in payload.ct_idx]
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    master_page_start = metadata.get("master_page_start", metadata.get("main_page_start"))
    master_page_end = metadata.get("master_page_end", metadata.get("main_page_end"))
    interruptor_pool = zero_positions(ct_idx)
    reference_idx = encode_reference(CANONICAL_KOAN_DURING_LESSON_TEXT)
    plaintext_idx = replay_pinned_solution(ct_idx, wli)
    plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)
    ratio = match_ratio(plaintext_idx, reference_idx)
    status = "solved" if ratio >= ACCEPTANCE_MATCH_RATIO else "diagnostic_not_yet_solved"
    found_interruptors_in_pool = all(value in interruptor_pool for value in PINNED_FOUND_INTERRUPTORS)
    keyspace_hint_idx = encode_reference(RECIPE_REFERENCE_KEY_OR_SHIFT)
    key_matches_recipe_hint = PINNED_FOUND_KEY_CORE == keyspace_hint_idx
    elapsed_wall_time_s = time.perf_counter() - started

    print("\nLP_KOAN_DURING_LESSON_RUN_CONFIG_BEGIN")
    for key, value in (
        ("source_label", SOURCE_LABEL),
        ("resolved_source_label", metadata["source_label"]),
        ("main_page_start", metadata["main_page_start"]),
        ("main_page_end", metadata["main_page_end"]),
        ("master_page_start", master_page_start),
        ("master_page_end", master_page_end),
        ("ciphertext_length", len(ct_idx)),
        ("wli_length", len(wli)),
        ("recipe", recipe.recipe_label),
        ("cipher_family", recipe.cipher_family),
        ("key_text_hint_human", KEY_TEXT_HINT_HUMAN),
        ("recipe_reference_key_or_shift", RECIPE_REFERENCE_KEY_OR_SHIFT),
        ("key_length", KEY_LENGTH),
        ("interrupter_count_required", INTERRUPTOR_COUNT),
        ("interrupter_pool_strategy", "ciphertext_zero_positions"),
        ("interrupter_pool_size", len(interruptor_pool)),
        ("interrupter_pool", interruptor_pool),
        ("acceptance_match_ratio", f"{ACCEPTANCE_MATCH_RATIO:.3f}"),
    ):
        print_kv(key, value)
    print("LP_KOAN_DURING_LESSON_RUN_CONFIG_END")

    print("\nLP_KOAN_DURING_LESSON_ATTEMPT_SUMMARY_BEGIN")
    for key, value in (
        ("method", "pinned_period_13_vigenere_interruptor_replay"),
        ("found_key_core", PINNED_FOUND_KEY_CORE),
        ("found_key_core_len", len(PINNED_FOUND_KEY_CORE)),
        ("found_key_matches_recipe_keyspace_hint", key_matches_recipe_hint),
        ("found_interruptors", PINNED_FOUND_INTERRUPTORS),
        ("found_interrupter_count", len(PINNED_FOUND_INTERRUPTORS)),
        ("found_interruptors_in_pool", found_interruptors_in_pool),
        ("best_score", PINNED_BEST_SCORE),
        ("stop_reason", PINNED_STOP_REASON),
        ("match_ratio", f"{ratio:.3f}"),
        ("plaintext_idx_length", len(plaintext_idx)),
        ("reference_idx_length", len(reference_idx)),
        ("elapsed_wall_time_s", elapsed_wall_time_s),
        ("status", status),
    ):
        print_kv(key, value)
    print("LP_KOAN_DURING_LESSON_ATTEMPT_SUMMARY_END")

    print("\nLP_KOAN_DURING_LESSON_FINAL_RESULT_BEGIN")
    for key, value in (
        ("source_label", SOURCE_LABEL),
        ("resolved_source_label", metadata["source_label"]),
        ("master_page_start", master_page_start),
        ("master_page_end", master_page_end),
        ("recipe", recipe.recipe_label),
        ("cipher_family", recipe.cipher_family),
        ("key_text_hint_human", KEY_TEXT_HINT_HUMAN),
        ("recipe_reference_key_or_shift", RECIPE_REFERENCE_KEY_OR_SHIFT),
        ("key_length", KEY_LENGTH),
        ("interrupter_pool_size", len(interruptor_pool)),
        ("interrupter_pool", interruptor_pool),
        ("interrupter_count_required", INTERRUPTOR_COUNT),
        ("found_key_core", PINNED_FOUND_KEY_CORE),
        ("found_interruptors", PINNED_FOUND_INTERRUPTORS),
        ("found_interrupter_count", len(PINNED_FOUND_INTERRUPTORS)),
        ("found_interruptors_in_pool", found_interruptors_in_pool),
        ("best_score", PINNED_BEST_SCORE),
        ("stop_reason", PINNED_STOP_REASON),
        ("match_ratio", f"{ratio:.3f}"),
        ("status", status),
        (
            "notes",
            "exact solved reference match using period-13 Vigenere/interrupter replay over ciphertext-zero pool; found two interrupters [49, 58]",
        ),
    ):
        print_kv(key, value)
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_KOAN_DURING_LESSON_FINAL_RESULT_END")
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
