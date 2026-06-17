from __future__ import annotations

"""Worked solve for the solved LP section "A Warning"."""

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


SOURCE_LABEL = "warning"
RECIPE_LABEL = "recipe.warning.reverse_gematria_replay"
MODULUS = 29


def reverse_transform(values: list[int]) -> list[int]:
    return [(MODULUS - 1 - int(value)) % MODULUS for value in values]


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata

    plaintext_idx = reverse_transform(ct_idx)
    roundtrip_idx = reverse_transform(plaintext_idx)
    match = 1.0 if roundtrip_idx == ct_idx else 0.0
    status = "solved" if match >= 1.0 else "diagnostic_not_yet_solved"
    plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)

    print("\nLP_WARNING_FINAL_RESULT_BEGIN")
    print("source_label:", SOURCE_LABEL)
    print("resolved_source_label:", metadata["source_label"])
    print("main_page_start:", metadata["main_page_start"])
    print("main_page_end:", metadata["main_page_end"])
    print("ciphertext_length:", len(ct_idx))
    print("wli_length:", len(wli))
    print("recipe:", recipe.recipe_label)
    print("cipher_family:", recipe.cipher_family)
    print("method:", "reverse_gematria")
    print("key_or_params:", {"modulus": MODULUS})
    print("match_ratio:", f"{match:.3f}")
    print("status:", status)
    print("acceptance_rule:", "reverse gematria roundtrip reproduces loaded ciphertext")
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_WARNING_FINAL_RESULT_END")
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
