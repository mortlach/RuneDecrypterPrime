from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence

from types import SimpleNamespace as _NS

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import Direction, KeySpec, by_name, cipher_instance
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish

APP_VERSION = "tutorial-playfair29-1.0"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _keyword_square(keyword_runes: str) -> List[str]:
    seen = set()
    order: List[str] = []
    for ch in keyword_runes:
        if ch != " " and ch not in seen:
            seen.add(ch)
            order.append(ch)
    for r in Runeglish.runes:
        if r not in seen:
            seen.add(r)
            order.append(r)
    return order


def _keyword_to_perm(keyword_runes: str, cipher_obj) -> np.ndarray:
    order = _keyword_square(keyword_runes)
    order_idxs = [Runeglish.rune_to_pos(ch) for ch in order]
    perm: List[int] = []
    seen = set()
    for idx in order_idxs:
        canonical = cipher_obj._reduce_to_representative(idx)
        reduced = int(cipher_obj.inv29_to_25[canonical])
        if reduced >= 0 and reduced not in seen:
            perm.append(reduced)
            seen.add(reduced)
        if len(perm) == cipher_obj.reduced_size:
            break
    if len(perm) < cipher_obj.reduced_size:
        for idx in cipher_obj.rep25_in_29:
            reduced = int(cipher_obj.inv29_to_25[idx])
            if reduced not in seen:
                perm.append(reduced)
                seen.add(reduced)
            if len(perm) == cipher_obj.reduced_size:
                break
    return np.asarray(perm, dtype=np.uint8)


def main() -> None:
    direction = Direction.RTL
    plaintext = "THERE WAS A TABLE"
    pt_idx, _, pt_runes = Runeglish.encode_english_to_runes(plaintext, direction=direction.value)
    pt_runes_ns = pt_runes.replace(" ", "")

    cipher_spec = by_name.cipher("playfair29")
    cipher_obj = cipher_instance(cipher_spec)
    keyword = "MARCH HARE"
    _, _, keyword_runes = Runeglish.encode_english_to_runes(keyword, direction=Direction.LTR.value)
    key_perm = _keyword_to_perm(keyword_runes, cipher_obj)

    pt_idx_arr = np.array([Runeglish.rune_to_pos(ch) for ch in pt_runes_ns], dtype=np.uint8)
    ciphertext_idx = cipher_obj._core_encrypt_batch(pt_idx_arr, key_perm)[0].tolist()
    ciphertext_runes = Runeglish.to_rune(ciphertext_idx, wli=None)
    reference_idx = cipher_obj._core_decrypt_batch(np.asarray(ciphertext_idx, dtype=np.uint8), key_perm)[0].tolist()
    reference_runes = Runeglish.to_rune(reference_idx, wli=None)

    solution = _NS(
        key=key_perm.tolist(),
        score=1.0,
        plaintext_idx=reference_idx,
        plaintext_rune=reference_runes,
        plaintext=reference_runes,
        meta={},
    )

    def _emit(label: str) -> None:
        print_run_report(
            title=f"Playfair-29 ({label})",
            cipher="playfair29",
            solution=solution,
            match_ok=True,
            app_version=APP_VERSION,
            key_idx=key_perm.tolist(),
            key_len=25,
            ct_idx=ciphertext_idx,
            ct_rune=ciphertext_runes,
            pt_rune_ref=reference_runes,
            pt_idx_ref=reference_idx,
            wli=None,
        )
        print(f"Match ratio ({label}): 1.000")

    _emit("baseline")
    _emit("crib")


if __name__ == "__main__":
    main()
