from __future__ import annotations

import argparse
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Iterable, Sequence

import numpy as np

from rune_decrypter_prime.api import Direction, by_name, cipher_instance
from rune_decrypter_prime.core.types import (
    ObjectiveFamily,
    ObjectiveSpec,
    KEY_DTYPE,
    SeMode,
    Stat,
)
from rune_decrypter_prime.keyops.permutation_ops import PermutationKeyConfig, PermutationKeyOps
from rune_decrypter_prime.scoring.rune_scorer import RuneScorer
from rune_decrypter_prime.utils.bigram_seed_generator import (
    BigramSeedGenerator,
    build_wli_bigram_prior,
)
from rune_decrypter_prime.utils.runeglish import Runeglish


DEFAULT_TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE MARCH HARE AND THE HATTER "
    "WERE HAVING TEA AT IT A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP AND THE OTHER TWO WERE "
    "USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
)


@dataclass
class SeedDiagnostics:
    score: float
    match_ratio: float
    key_distance: int


def _match_ratio(a: Sequence[int], b: Sequence[int]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    matches = sum(1 for idx in range(n) if a[idx] == b[idx])
    return matches / float(n)


def _hamming_distance(a: Sequence[int], b: Sequence[int]) -> int:
    if len(a) != len(b):
        raise ValueError("Keys must have equal length for Hamming distance")
    return int(np.count_nonzero(np.asarray(a) != np.asarray(b)))


def _build_true_key(length: int, *, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    key = np.arange(length, dtype=KEY_DTYPE)
    block = 29
    for offset in range(0, length, block):
        rng.shuffle(key[offset : offset + block])
    return key


def _decrypt_score(
    cipher,
    ciphertext: np.ndarray,
    key: Iterable[int],
    scorer: RuneScorer,
    wli_windows,
    ground_truth: Sequence[int],
    true_key: Sequence[int],
) -> SeedDiagnostics:
    key_arr = np.asarray(key, dtype=KEY_DTYPE)
    plaintext = cipher.decrypt_single(ciphertext=ciphertext, key=key_arr)
    score = float(scorer.score(plaintext, wli_windows))
    match = _match_ratio(plaintext, ground_truth)
    distance = _hamming_distance(key_arr, true_key)
    return SeedDiagnostics(score=score, match_ratio=match, key_distance=distance)


def run_diagnostics(
    text: str,
    *,
    direction: Direction = Direction.RTL,
    n_seeds: int = 32,
    lm_seed: int = 2027,
    random_seed: int = 4242,
    scorer_objective: ObjectiveSpec | None = None,
) -> None:
    pt_idx, wli, _ = Runeglish.encode_english_to_runes(text, direction=direction.value)
    cipher_spec = by_name.cipher("bigram_sub")
    cipher = cipher_instance(cipher_spec)

    alphabet = 29
    key_len = alphabet * alphabet
    true_key = _build_true_key(key_len, seed=random_seed)
    ciphertext = cipher.encrypt_single(
        plaintext=np.asarray(pt_idx, dtype=np.uint8),
        key=true_key,
    )

    prior = build_wli_bigram_prior()
    seed_gen = BigramSeedGenerator(alphabet_size=alphabet, plaintext_prior=prior)
    lm_seeds = seed_gen.generate_seeds(ciphertext.tolist(), n_seeds=n_seeds, seed=lm_seed)

    keyops = PermutationKeyOps(PermutationKeyConfig(K=key_len))
    rng = np.random.default_rng(random_seed + 1337)
    random_seeds = [keyops.random(rng).astype(int).tolist() for _ in range(n_seeds)]

    objective = scorer_objective or ObjectiveSpec(
        family=ObjectiveFamily.PCT,
        stat=Stat.LOGP,
        win=10,
    )
    scorer_cfg = SimpleNamespace(
        encoding_dir=direction,
        se_mode=SeMode.NOSE,
        objective=objective,
        include_char=True,
        use_word_breaks=True,
        n_char=2,
        n_wli=2,
    )
    scorer = RuneScorer(SimpleNamespace(), scorer_cfg)

    ciphertext_arr = np.asarray(ciphertext, dtype=np.uint8)
    ground_truth = np.asarray(pt_idx, dtype=np.uint8)

    lm_stats = [
        _decrypt_score(cipher, ciphertext_arr, key, scorer, wli, ground_truth, true_key)
        for key in lm_seeds
    ]
    rand_stats = [
        _decrypt_score(cipher, ciphertext_arr, key, scorer, wli, ground_truth, true_key)
        for key in random_seeds
    ]

    def _print_block(label: str, stats: list[SeedDiagnostics]) -> None:
        print(f"{label}:")
        for idx, stat in enumerate(stats):
            print(
                f"  seed {idx:02d}: score={stat.score:.6f}  match={stat.match_ratio:.3f}  "
                f"key_distance={stat.key_distance}"
            )
        print(
            f"  mean score={np.mean([s.score for s in stats]):.6f}, "
            f"mean match={np.mean([s.match_ratio for s in stats]):.3f}, "
            f"mean key_distance={np.mean([s.key_distance for s in stats]):.1f}"
        )
        print()

    print("--- Bigram Seed Diagnostics ---")
    print(f"Ciphertext length: {len(ciphertext_arr)} runes")
    print(f"# of seeds per group: {n_seeds}")
    print()
    _print_block("LM seeds", lm_stats)
    _print_block("Random seeds", rand_stats)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare LM bigram seeds against random permutations.")
    parser.add_argument(
        "--text",
        type=str,
        default=DEFAULT_TEXT,
        help="Plaintext used to generate ciphertext (default: tutorial excerpt).",
    )
    parser.add_argument(
        "--n-seeds",
        type=int,
        default=32,
        help="Number of seeds to sample from each distribution.",
    )
    parser.add_argument(
        "--lm-seed",
        type=int,
        default=2027,
        help="RNG seed for LM/cribbed seed generation.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=4242,
        help="RNG seed used for true key construction and random permutations.",
    )
    args = parser.parse_args()
    run_diagnostics(
        args.text,
        direction=Direction.RTL,
        n_seeds=int(args.n_seeds),
        lm_seed=int(args.lm_seed),
        random_seed=int(args.random_seed),
    )


if __name__ == "__main__":
    main()
