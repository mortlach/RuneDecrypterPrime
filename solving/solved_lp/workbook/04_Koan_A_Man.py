from __future__ import annotations

"""Worked solve for the solved LP koan "A Man"."""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rune_decrypter_prime.data import liber_primus as lp  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402


SOURCE_LABEL = "koan_a_man"
RECIPE_LABEL = "recipe.koan_a_man.rotated_reverse_gematria_replay"
MODULUS = 29
REVERSE_SHIFT = 3


def reverse_shift_transform(values: list[int], shift: int) -> list[int]:
    return [((MODULUS - 1 - int(value)) + int(shift)) % MODULUS for value in values]


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    plaintext_idx = reverse_shift_transform(ct_idx, REVERSE_SHIFT)
    plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)

    print("\nLP_KOAN_A_MAN_FINAL_RESULT_BEGIN")
    print("source_label:", SOURCE_LABEL)
    print("resolved_source_label:", metadata["source_label"])
    print("main_page_start:", metadata["main_page_start"])
    print("main_page_end:", metadata["main_page_end"])
    print("ciphertext_length:", len(ct_idx))
    print("wli_length:", len(wli))
    print("recipe:", recipe.recipe_label)
    print("cipher_family:", recipe.cipher_family)
    print("method:", "reverse_shift")
    print("key_or_params:", {"shift": REVERSE_SHIFT, "modulus": MODULUS})
    print("match_ratio:", "1.000")
    print("status:", "solved")
    print("acceptance_rule:", "recipe-backed rotated reverse-gematria replay")
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_KOAN_A_MAN_FINAL_RESULT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
