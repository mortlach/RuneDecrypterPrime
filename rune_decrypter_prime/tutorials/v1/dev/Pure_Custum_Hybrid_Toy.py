# -*- coding: utf-8 -*-
# File: Tutorial_CustomHybrid_MapAndKeyops.py

from __future__ import annotations
from typing import List, Tuple, Any
import random

from rune_decrypter_prime.ui.api import define_map, KeySpec, SolveSpec, run
from rune_decrypter_prime.core.keyops import KeyOpsBase  # your abstract base
from rune_decrypter_prime.utils.runeglish import Runeglish

N = 29

# Cipher: PT first goes through a Caesar shift (k_shift), then a fixed 2x2 block swap
# (permutes indices in each block of 2 using a permutation key over {0,1}).
# Key = (k_shift in [0..28], swap_flag in {0,1} per 2-symbol block) → represent swap flags as a binary vector.

def hybrid_cell(pt: int, shift: int, flag: int) -> int:
    c = (int(pt) + int(shift)) % N
    # “flag” is 0 or 1; if 1 we flip c with a simple involution for demo (c ↔ (N-1-c))
    return (N-1-c) if (flag & 1) else c

def make_hybrid_stream_key(seed_shift: int, flags: List[int]) -> List[Tuple[int,int]]:
    # produce a per-char (shift, flag) sequence: shift is constant; flag repeats per char
    return [(seed_shift, flags[i % len(flags)]) for i in range(10_000_000)]  # oversized, engine will slice

class HybridKeyOps(KeyOpsBase):
    """
    Key structure:
      k = (shift:int in [0..28], flags: List[int] of length F with entries {0,1})
    """
    def __init__(self, flag_len: int, *, rng_seed: int | None = None):
        self.flag_len = int(flag_len)
        self.rng = random.Random(rng_seed)

    # GA/SA hooks your optimizers expect:
    def random(self, rng) -> Any:
        shift = self.rng.randrange(N)
        flags = [self.rng.randrange(2) for _ in range(self.flag_len)]
        return (shift, flags)

    def mutate(self, key, rng, prob: float = 0.2):
        shift, flags = key
        if rng.random() < prob:
            shift = (shift + rng.randrange(1, N)) % N
        flags = [f ^ 1 if rng.random() < prob else f for f in flags]
        return (shift, flags)

    def crossover(self, a, b, rng):
        sa, fa = a
        sb, fb = b
        cut = rng.randrange(self.flag_len)
        child_flags = fa[:cut] + fb[cut:]
        child_shift = sa if rng.random() < 0.5 else sb
        return (child_shift, child_flags)

    def normalize(self, key):
        shift, flags = key
        shift = int(shift) % N
        flags = [0 if (f & 1)==0 else 1 for f in flags]
        return (shift, flags)

    # For scoring batches: turn a key into flat ndarray/tuple the engine accepts
    # (your modern solver already supports non-np key payloads; otherwise provide pack/unpack)

def main() -> None:
    pt_en = "DOWN THE RABBIT HOLE WITH SOME STRANGE HYBRID MAP DEMO"
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(pt_en, direction="fwd")
    pt_runes = pt_runes.replace(" ", "")
    wli = None

    # Define the general map in “stream” fashion using adapter inside your API
    # We’ll supply per-char (shift, flag) via the key stream generator in the pipeline.
    def map_cell(pt_sym: int, key_tuple: Tuple[int,int]) -> int:
        shift, flag = key_tuple
        return hybrid_cell(pt_sym, shift, flag)

    spec = define_map(function=map_cell, N=N, name="hybrid-caesar-swap")

    # Encrypt with known key
    seed_shift = 6
    flags = [1,0,0,1, 1,0,1,0]  # len=8
    # pack key as required by your engine: (seed_shift, flags)
    known_key = (seed_shift, flags)
    ct = run.encrypt(text=pt_runes, cipher=spec, key=known_key, wli_data=None).ciphertext

    # Tell the optimizer how to explore that composite key
    keyops = HybridKeyOps(flag_len=len(flags), rng_seed=1337)
    key = KeySpec.custom(keyops=keyops)

    solve = SolveSpec.ga(population=200, generations=300, cx_frac=0.7, mut_prob=0.3, elite_frac=0.05)
    scorer_params = dict(objective="pct.logp.win10", n_char=2, n_wli=None, win=10, include_char=True, use_word_breaks=False, weights=(1.0,))

    sol = run.solve(
        text=ct, cipher=spec, key=key, solve=solve,
        device="cpu", scorer="rune", scorer_params=scorer_params,
        wli_data=None, force_no_wli=True
    )

    print("─"*60)
    print("Custom Hybrid (Map + KeyOps) Demo")
    print("PT:", pt_runes)
    print("CT:", ct[:160] if isinstance(ct, str) else "")
    print("REC:", getattr(sol, "plaintext", "")[:160])
    print("Key(found):", getattr(sol, "key", None))
    print("Score:", getattr(sol, "score", None))
    print("─"*60)

if __name__ == "__main__":
    main()
