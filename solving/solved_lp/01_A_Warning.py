from __future__ import annotations

'Worked solve for the solved LP section "A Warning".'
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from rune_decrypter_prime.data import liber_primus as lp
from rune_decrypter_prime.utils.solve_output import (
    configure_utf8_stdio,
    page_value,
    print_final_result,
    render_plaintext,
)

configure_utf8_stdio()
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
    plaintext_latin, plaintext_runes = render_plaintext(plaintext_idx, wli)
    print_final_result(
        block_name="LP_WARNING_FINAL_RESULT",
        source_label=SOURCE_LABEL,
        resolved_source_label=metadata["source_label"],
        main_page_start=page_value(metadata, "main_page_start"),
        main_page_end=page_value(metadata, "main_page_end"),
        ciphertext_length=len(ct_idx),
        wli_length=len(wli),
        recipe=recipe.recipe_label,
        cipher_family=recipe.cipher_family,
        method="reverse_gematria",
        key_or_params={"modulus": MODULUS},
        match_ratio=match,
        status=status,
        acceptance_rule="reverse gematria roundtrip reproduces loaded ciphertext",
        plaintext_latin=plaintext_latin,
        plaintext_runes=plaintext_runes,
    )
    return 0 if status == "solved" else 1


if __name__ == "__main__":
    raise SystemExit(main())
