from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import List, Sequence

import numpy as np

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, run
from rune_decrypter_prime.core.types import ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.utils.bigram_seed_generator import BigramSeedGenerator, build_wli_bigram_prior
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish


TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE MARCH HARE AND THE HATTER "
    "WERE HAVING TEA AT IT A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP AND THE OTHER TWO WERE "
    "USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT"
)


def _match_ratio(found: Sequence[int], reference: Sequence[int]) -> float:
    n = min(len(found), len(reference))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if found[i] == reference[i])
    return matches / float(n)


def _build_crib_codes(
    ciphertext_idx: Sequence[int],
    plaintext_idx: Sequence[int],
    start: int,
    span_len: int,
    *,
    alphabet: int,
) -> List[tuple[int, int]]:
    codes: List[tuple[int, int]] = []
    for offset in range(0, span_len, 2):
        ct_a = ciphertext_idx[start + offset]
        ct_b = ciphertext_idx[start + offset + 1]
        pt_a = plaintext_idx[start + offset]
        pt_b = plaintext_idx[start + offset + 1]
        ct_code = ct_a * alphabet + ct_b
        pt_code = pt_a * alphabet + pt_b
        codes.append((ct_code, pt_code))
    return codes


def _select_crib(pt_idx: Sequence[int], wli, text: str) -> tuple[list[str], int, list[int]]:
    import re

    def _build_word_spans():
        words = re.findall(r"[A-Za-z]+", text.upper())
        spans: List[tuple[str, int, int]] = []
        i = 0
        for word in words:
            while i < len(wli) and wli[i][0] != 0:
                i += 1
            if i >= len(wli):
                break
            length = int(wli[i][1])
            spans.append((word, i, length))
            i += length
        return spans

    spans = _build_word_spans()
    for window in range(10, 3, -1):
        for idx in range(len(spans) - window + 1):
            start = spans[idx][1]
            total_len = sum(spans[idx + j][2] for j in range(window))
            if start % 2 != 0 or total_len % 2 != 0 or total_len < 10:
                continue
            phrase = [spans[idx + j][0] for j in range(window)]
            crib_idx = list(pt_idx[start : start + total_len])
            return phrase, start, crib_idx
    raise RuntimeError("Unable to select crib phrase")


@dataclass
class RunStats:
    label: str
    score: float
    match_ratio: float
    meta: dict


def run_once(
    *,
    ciphertext_runes: str,
    ciphertext_idx: list[int],
    cipher_spec,
    key_spec,
    solver_spec,
    wli,
    direction: Direction,
    pt_idx_reference: list[int],
    pt_runes_reference: str,
    initial_keys,
) -> RunStats:
    solution = run(
        text=ciphertext_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            objective="pct.logp.win8",
            n_char=2,
            n_wli=2,
            include_char=True,
            use_word_breaks=True,
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        initial_keys=initial_keys,
    )
    ratio = _match_ratio(solution.plaintext_idx, pt_idx_reference)
    return RunStats(
        label="seeded" if initial_keys else "unseeded",
        score=float(solution.score),
        match_ratio=ratio,
        meta=getattr(solution, "meta", {}) or {},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare seeded vs unseeded hybrid runs for the bigram cipher.")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per scenario.")
    parser.add_argument("--seed-count", type=int, default=64, help="Number of LM seeds to inject when seeding.")
    parser.add_argument("--lm-seed", type=int, default=2027, help="RNG seed for LM seed generation.")
    parser.add_argument("--solver-seed", type=int, default=4040, help="Base solver seed.")
    args = parser.parse_args()

    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(TEXT, direction=direction.value)
    pt_idx_list = list(pt_idx)

    cipher_spec = by_name.cipher("bigram_sub")
    cipher = cipher_instance(cipher_spec)
    rng = np.random.default_rng(12345)
    alphabet = 29
    key_len = alphabet * alphabet
    true_key = np.arange(key_len, dtype=np.int16)
    for offset in range(0, key_len, alphabet):
        rng.shuffle(true_key[offset : offset + alphabet])

    ciphertext_idx = cipher.encrypt_single(
        plaintext=np.asarray(pt_idx, dtype=np.uint8),
        key=true_key,
    ).tolist()
    ciphertext_runes = Runeglish.to_rune(ciphertext_idx, wli)

    crib_phrase, crib_start, crib_idx = _select_crib(pt_idx_list, wli, TEXT)
    crib_codes = _build_crib_codes(ciphertext_idx, pt_idx_list, crib_start, len(crib_idx), alphabet=alphabet)
    print(f"Crib phrase: {' '.join(crib_phrase)} (start {crib_start}, runes {len(crib_idx)})")

    cipher_spec = by_name.cipher("bigram_sub", crib=crib_codes)
    key_spec = KeySpec.permutation(len=key_len)

    prior = build_wli_bigram_prior()
    seed_gen = BigramSeedGenerator(
        alphabet_size=alphabet,
        plaintext_prior=prior,
        crib_ct_codes=[ct for ct, _ in crib_codes],
        crib_pt_codes=[pt for _, pt in crib_codes],
    )
    lm_seeds = seed_gen.generate_seeds(ciphertext_idx, n_seeds=args.seed_count, seed=args.lm_seed)

    solver_params = dict(
        beam_width=48,
        rounds=2,
        use_beam=True,
        ga=dict(pop_size=96, generations=140, mut_prob=0.35),
        sa=dict(sa_iters=800),
    )

    results: list[RunStats] = []
    for i in range(args.runs):
        solver_seed = args.solver_seed + i
        solver_spec = SolverSpec.hybrid(seed=solver_seed, **solver_params)
        res = run_once(
            ciphertext_runes=ciphertext_runes,
            ciphertext_idx=ciphertext_idx,
            cipher_spec=cipher_spec,
            key_spec=key_spec,
            solver_spec=solver_spec,
            wli=wli,
            direction=direction,
            pt_idx_reference=pt_idx_list,
            pt_runes_reference=pt_runes,
            initial_keys=None,
        )
        results.append(res)

    for i in range(args.runs):
        solver_seed = args.solver_seed + 1000 + i
        solver_spec = SolverSpec.hybrid(seed=solver_seed, **solver_params)
        res = run_once(
            ciphertext_runes=ciphertext_runes,
            ciphertext_idx=ciphertext_idx,
            cipher_spec=cipher_spec,
            key_spec=key_spec,
            solver_spec=solver_spec,
            wli=wli,
            direction=direction,
            pt_idx_reference=pt_idx_list,
            pt_runes_reference=pt_runes,
            initial_keys=lm_seeds,
        )
        results.append(res)

    print()
    print("--- Hybrid diagnostics ---")
    for res in results:
        print(f"{res.label:8s} | score={res.score:.6f}  match={res.match_ratio:.3f}")
        diag = (res.meta or {}).get("seed_diag")
        if diag:
            print(f"            seed_diag={diag}")

    def _summary(label: str):
        group = [r for r in results if r.label == label]
        if not group:
            return
        mean_score = float(np.mean([r.score for r in group]))
        mean_match = float(np.mean([r.match_ratio for r in group]))
        print(f"{label:8s} mean score={mean_score:.6f}  mean match={mean_match:.3f}")

    print()
    _summary("unseeded")
    _summary("seeded")


if __name__ == "__main__":
    main()
