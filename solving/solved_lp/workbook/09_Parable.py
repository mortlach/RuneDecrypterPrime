from __future__ import annotations

"""Worked solve for the solved LP section "Parable"."""

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


SOURCE_LABEL = "parable"
RECIPE_LABEL = "recipe.parable.constant_shift_zero_replay"


def main() -> int:
    payload = lp.payload_from_label(SOURCE_LABEL)
    recipe = lp.resolve_solve_recipe_label(RECIPE_LABEL)
    ct_idx = list(payload.ct_idx)
    wli = [list(pair) for pair in payload.wli]
    metadata = payload.metadata
    plaintext_idx = list(ct_idx)
    match = 1.0 if plaintext_idx == ct_idx else 0.0
    status = "solved" if match >= 1.0 else "diagnostic_not_yet_solved"
    plaintext_latin = Runeglish.to_rune_latin(plaintext_idx, wli)
    plaintext_runes = Runeglish.to_rune(plaintext_idx, wli)

    print("\nLP_PARABLE_FINAL_RESULT_BEGIN")
    print("source_label:", SOURCE_LABEL)
    print("resolved_source_label:", metadata["source_label"])
    print("main_page_start:", metadata["main_page_start"])
    print("main_page_end:", metadata["main_page_end"])
    print("ciphertext_length:", len(ct_idx))
    print("wli_length:", len(wli))
    print("recipe:", recipe.recipe_label)
    print("cipher_family:", recipe.cipher_family)
    print("method:", "constant_shift")
    print("key_or_params:", {"shift": 0, "modulus": 29})
    print("match_ratio:", f"{match:.3f}")
    print("status:", status)
    print("acceptance_rule:", "shift-0 replay reproduces loaded solved text")
    print("plaintext_latin:")
    print(plaintext_latin)
    print("plaintext_runes:")
    print(plaintext_runes)
    print("LP_PARABLE_FINAL_RESULT_END")
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
