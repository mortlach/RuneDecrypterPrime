# -*- coding: utf-8 -*-
# File: Tutorial_AutokeyVigenere.py

from __future__ import annotations
from typing import List, Sequence
from rune_decrypter_prime.ui.api import define_map, KeySpec, SolveSpec, run
from rune_decrypter_prime.utils.runeglish import Runeglish

N = 29

def autokey_map_factory(pt_context: Sequence[int]):
    """
    We return a cell f(pt_i, k_i) = (pt_i + k_i) % 29.
    The *pipeline* (CipherPipelineMixin) ensures the key stream is [seed, pt_prefix].
    You already have this pattern in your generalized map adaptor.
    """
    def cell(pt: int, k: int) -> int:
        return (int(pt) + int(k)) % N
    return cell

def main() -> None:
    pt_en = (
        "WHEN THE WHITE RABBIT READ THESE WORDS HE LOOKED SUDDENLY ALARMED "
        "FOR A SHOWER OF LITTLE GLASS BOXES CAME TUMBLING UPON HIM"
    )
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="fwd")

    # Define the autokey map (device-agnostic)
    cell = autokey_map_factory(pt_idx)
    spec = define_map(function=cell, N=N, name="autokey-vigenere")

    # Encrypt with a short seed key
    seed = [6, 1, 4]  # m = 3
    ct = run.encrypt(text=pt_runes, cipher=spec, key=seed, wli_data=wli).ciphertext

    # Now we *only* tell the solver the period (repeat length) and let it infer the seed
    key = KeySpec.repeat(len=len(seed))
    solve = SolveSpec.beam(beam_width=48)

    scorer_params = dict(objective="pct.logp.win10", n_char=2, n_wli=2, win=10, include_char=True, use_word_breaks=True, weights=(0.5,0.5))

    sol = run.solve(
        text=ct, cipher=spec, key=key, solve=solve,
        device="cpu", scorer="rune", scorer_params=scorer_params,
        wli_data=wli
    )

    print("─"*60)
    print("Autokey Vigenère Demo")
    print("PT runes:", pt_runes[:200])
    print("CT runes:", ct[:200] if isinstance(ct, str) else "")
    print("Recovered:", getattr(sol, "plaintext", "")[:200])
    print("Key(found):", getattr(sol, "key", None))
    print("Score:", getattr(sol, "score", None))
    print("─"*60)

if __name__ == "__main__":
    main()
