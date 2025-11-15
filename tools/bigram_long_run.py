from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Sequence, Tuple

import numpy as np

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, run
from rune_decrypter_prime.core.types import KEY_DTYPE
from rune_decrypter_prime.utils.bigram_seed_generator import (
    BigramSeedGenerator,
    build_wli_bigram_prior,
)
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish

APP_VERSION = "bigram-long-run-1.0"

BASE_TEXT = (
    "THERE WAS A TABLE SET OUT UNDER A TREE IN FRONT OF THE HOUSE AND THE MARCH HARE AND THE "
    "HATTER WERE HAVING TEA AT IT. A DORMOUSE WAS SITTING BETWEEN THEM FAST ASLEEP AND THE OTHER "
    "TWO WERE USING IT AS A CUSHION RESTING THEIR ELBOWS ON IT. THE HATTER OPENED HIS EYES VERY "
    "WIDE ON HEARING THIS BUT ALL HE SAID WAS WHATS THE ANSWER. I GIVE IT UP ALICE REPLIED. THATS "
    "JUST WHAT I WAS GOING TO ASK THE DORMOUSE SAID. AND THEY ALL SAT SILENTLY FOR A MINUTE, "
    "CONSIDERING. THERE WAS NOTHING SO VERY REMARKABLE IN THAT NOR DID ALICE THINK IT SO VERY "
    "MUCH OUT OF THE WAY TO HEAR THE RABBIT SAY TO ITSELF OH DEAR OH DEAR I SHALL BE LATE."
)
LONG_TEXT = " ".join(BASE_TEXT for _ in range(4))


def _match_ratio(found: Sequence[int], reference: Sequence[int]) -> float:
    n = min(len(found), len(reference))
    if n == 0:
        return 0.0
    matches = sum(1 for i in range(n) if found[i] == reference[i])
    return matches / float(n)


def _active_bigram_codes(tokens: Sequence[int], alphabet: int) -> np.ndarray:
    arr = np.asarray(tokens, dtype=np.uint8).reshape(-1)
    limit = (arr.size // 2) * 2
    if limit == 0:
        return np.empty(0, dtype=np.int64)
    pairs = arr[:limit].reshape(-1, 2).astype(np.int64, copy=False)
    codes = pairs[:, 0] * alphabet + pairs[:, 1]
    return np.unique(codes)


def _build_crib_codes(
    ciphertext_idx: Sequence[int],
    plaintext_idx: Sequence[int],
    start: int,
    span_len: int,
    *,
    alphabet: int,
) -> List[Tuple[int, int]]:
    codes: List[Tuple[int, int]] = []
    for offset in range(0, span_len, 2):
        ct_a = ciphertext_idx[start + offset]
        ct_b = ciphertext_idx[start + offset + 1]
        pt_a = plaintext_idx[start + offset]
        pt_b = plaintext_idx[start + offset + 1]
        ct_code = ct_a * alphabet + ct_b
        pt_code = pt_a * alphabet + pt_b
        codes.append((ct_code, pt_code))
    return codes


def _build_word_spans(wli: Sequence[Sequence[int]], source_text: str) -> List[tuple[str, int, int]]:
    import re

    words = re.findall(r"[A-Za-z]+", source_text.upper())
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


def _select_crib(
    pt_idx: Sequence[int],
    wli: Sequence[Sequence[int]],
    source_text: str,
) -> tuple[list[str], int, list[int]]:
    spans = _build_word_spans(wli, source_text)
    for window in range(12, 4, -1):
        for idx in range(len(spans) - window + 1):
            phrase = [spans[idx + j][0] for j in range(window)]
            start = spans[idx][1]
            total_len = sum(spans[idx + j][2] for j in range(window))
            if start % 2 != 0 or total_len % 2 != 0 or total_len < 40:
                continue
            crib_idx = list(pt_idx[start : start + total_len])
            return phrase, start, crib_idx
    raise RuntimeError("Unable to find an even-length crib phrase in the sample text.")


def _jitter_key(key: np.ndarray, *, swaps: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.array(key, copy=True)
    K = out.size
    for _ in range(max(1, swaps)):
        i, j = rng.integers(0, K, size=2)
        if i != j:
            out[i], out[j] = out[j], out[i]
    return out


def main() -> None:
    direction = Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(LONG_TEXT, direction=direction.value)
    pt_idx_arr = np.array(pt_idx, dtype=np.uint8)

    cipher_spec = by_name.cipher("bigram_sub")
    cipher_obj = cipher_instance(cipher_spec)

    rng = np.random.default_rng(4242)
    alphabet = 29
    key_len = alphabet * alphabet
    true_key = np.arange(key_len, dtype=KEY_DTYPE)
    plaintext_codes = _active_bigram_codes(pt_idx_arr, alphabet)
    if plaintext_codes.size > 128:
        plaintext_codes = np.asarray(
            rng.choice(plaintext_codes, size=128, replace=False), dtype=np.int64
        )
    shuffled_codes = plaintext_codes.copy()
    rng.shuffle(shuffled_codes)
    true_key[plaintext_codes] = shuffled_codes.astype(KEY_DTYPE, copy=False)

    ct_arr = cipher_obj.encrypt_single(
        plaintext=np.asarray(pt_idx_arr, dtype=np.uint8),
        key=true_key,
    )
    ciphertext_idx = ct_arr.tolist()
    ciphertext_runes = Runeglish.to_rune(ciphertext_idx, wli)

    crib_phrase, crib_start, crib_idx = _select_crib(pt_idx, wli, LONG_TEXT)
    crib_codes = _build_crib_codes(
        ciphertext_idx,
        pt_idx,
        crib_start,
        len(crib_idx),
        alphabet=alphabet,
    )
    print(f"Crib phrase: {' '.join(crib_phrase)} (start rune {crib_start}, length {len(crib_idx)})")

    cipher_spec = by_name.cipher("bigram_sub", crib=crib_codes)
    key_spec = KeySpec.permutation(len=key_len)

    recovered_solution = SimpleNamespace(
        plaintext_idx=pt_idx_arr.tolist(),
        plaintext=pt_runes,
        score=1.0,
        key=true_key.tolist(),
        solver={},
        meta={},
    )
    print_run_report(
        title="Bigram Substitution (known key)",
        cipher="bigram_sub",
        solution=recovered_solution,
        match_ok=True,
        app_version=APP_VERSION,
        key_idx=true_key.tolist(),
        key_len=key_len,
        ct_idx=ciphertext_idx,
        ct_rune=ciphertext_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )

    print("\nBuilding LM seed pool (this can take ~1 minute)...")
    prior = build_wli_bigram_prior()
    seed_gen = BigramSeedGenerator(
        alphabet_size=alphabet,
        plaintext_prior=prior,
        crib_ct_codes=[ct for ct, _ in crib_codes],
        crib_pt_codes=[pt for _, pt in crib_codes],
    )
    LM_SEED_COUNT = 1536
    RANDOM_SEED_COUNT = 256
    lm_seeds = seed_gen.generate_seeds(
        ciphertext_idx,
        n_seeds=LM_SEED_COUNT,
        n_random=RANDOM_SEED_COUNT,
        seed=9090,
    )
    alignment_seed = cipher_obj.seed_key_from_crib(
        ciphertext_idx,
        crib_idx,
        offset=crib_start // 2,
        alphabet=cipher_obj.alphabet,
        rng_seed=2025,
    ).astype(KEY_DTYPE, copy=False)
    combined_seeds: list[list[int]] = [alignment_seed.tolist()]
    for swaps in (32, 64, 96, 128):
        combined_seeds.append(
            _jitter_key(alignment_seed, swaps=swaps, seed=7000 + swaps).astype(KEY_DTYPE, copy=False).tolist()
        )
    combined_seeds.extend(lm_seeds)
    print(
        f"Seed pool ready: {len(combined_seeds)} keys "
        f"(LM={LM_SEED_COUNT}, random={RANDOM_SEED_COUNT}, crib variants=5)."
    )
    print(
        "Starting long hybrid optimisation — expect 5–15 minutes depending on CPU.\n"
        "Progress lines appear every ~2% of each phase with plaintext previews."
    )

    logging_cfg = dict(progress_pct=2, print_progress=True, verbose=True)
    solver_spec = SolverSpec.hybrid(
        beam_width=160,
        rounds=6,
        use_beam=True,
        ga=dict(pop_size=512, generations=1200, mut_prob=0.35, elite_frac=0.08, plateau_gens=180),
        sa=dict(sa_iters=6000, local_improve_on_accept=True),
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=64,
        verbose_console=True,
        seed=9901,
    )

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
        logging=logging_cfg,
        initial_keys=combined_seeds,
    )

    ratio = _match_ratio(solution.plaintext_idx, pt_idx_arr.tolist())
    print_run_report(
        title="Bigram Substitution (hybrid long run)",
        cipher="bigram_sub",
        solution=solution,
        match_ok=ratio >= 0.5,
        app_version=APP_VERSION,
        key_idx=getattr(solution, "key", None),
        key_len=key_len,
        ct_idx=ciphertext_idx,
        ct_rune=ciphertext_runes,
        pt_rune_ref=pt_runes,
        pt_idx_ref=pt_idx,
        wli=wli,
    )
    print(f"Match ratio (hybrid long run): {ratio:.3f}")


if __name__ == "__main__":
    main()
