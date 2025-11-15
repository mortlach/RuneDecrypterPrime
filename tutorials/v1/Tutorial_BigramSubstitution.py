from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Sequence, Tuple
from types import SimpleNamespace

import numpy as np
import re

_ROOT = Path(__file__).resolve().parents[3]
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
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

APP_VERSION = "tutorial-bigram-sub-2.0"
TEXT = plaintext_english_string

PHRASE_CANDIDATES = [
    ["FAST", "ASLEEP", "AND", "THE"],
    ["THERE", "WAS", "A", "TABLE", "SET", "OUT"],
    ["MARCH", "HARE"],
    ["FAST", "ASLEEP", "AND"],
    ["FAST", "ASLEEP"],
    ["OTHER", "TWO"],
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


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


def _report_solution(
    label: str,
    *,
    solution,
    ratio: float,
    ciphertext_runes: str,
    ciphertext_idx: List[int],
    pt_idx_reference: Sequence[int],
    pt_runes_reference: str,
    wli,
    direction,
) -> None:
    print_run_report(
        title=f"Bigram Substitution ({label})",
        cipher="bigram_sub",
        solution=solution,
        match_ok=ratio >= 0.9,
        app_version=APP_VERSION,
        key_idx=getattr(solution, "key", None),
        key_len=29 * 29,
        ct_idx=ciphertext_idx,
        ct_rune=ciphertext_runes,
        pt_rune_ref=pt_runes_reference,
        pt_idx_ref=pt_idx_reference,
        wli=wli,
    )
    print(f"Match ratio ({label}): {ratio:.3f}")


def _run_scenario(
    label: str,
    *,
    ciphertext_runes: str,
    ciphertext_idx: List[int],
    cipher_spec,
    key_spec,
    solver_spec,
    wli,
    direction,
    pt_idx_reference: Sequence[int],
    pt_runes_reference: str,
    initial_keys: List[List[int]],
    emit_report: bool = True,
):
    logging_cfg = dict(progress_pct=1, print_progress=True)
    solution = run(
        text=ciphertext_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        device="cpu",
        scorer="rune",
        scorer_params=dict(
            char_weights={2: 0.3},
            wli_weights={2: 0.7},
            include_char=True,
            use_word_breaks=True,
            encoding_dir=direction,
        ),
        wli_data=wli,
        encoding_dir=direction,
        telemetry_on=True,
        logging=logging_cfg,
        initial_keys=initial_keys,
    )

    ratio = _match_ratio(solution.plaintext_idx, pt_idx_reference)
    if emit_report:
        _report_solution(
            label,
            solution=solution,
            ratio=ratio,
            ciphertext_runes=ciphertext_runes,
            ciphertext_idx=ciphertext_idx,
            pt_idx_reference=pt_idx_reference,
            pt_runes_reference=pt_runes_reference,
            wli=wli,
            direction=direction,
        )
    return solution, ratio


def _build_word_spans(wli: Sequence[Sequence[int]], source_text: str) -> List[tuple[str, int, int]]:
    """Return [(WORD, start_rune_idx, rune_len), ...] in reading order."""
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
    for window in range(10, 3, -1):
        for idx in range(len(spans) - window + 1):
            phrase = [spans[idx + j][0] for j in range(window)]
            start = spans[idx][1]
            total_len = sum(spans[idx + j][2] for j in range(window))
            if start % 2 != 0 or total_len % 2 != 0 or total_len < 30:
                continue
            crib_idx = list(pt_idx[start : start + total_len])
            return phrase, start, crib_idx

    for phrase in PHRASE_CANDIDATES:
        for idx in range(len(spans) - len(phrase) + 1):
            if all(spans[idx + j][0] == phrase[j] for j in range(len(phrase))):
                start = spans[idx][1]
                total_len = sum(spans[idx + j][2] for j in range(len(phrase)))
                if start % 2 != 0 or total_len % 2 != 0:
                    continue
                crib_idx = list(pt_idx[start : start + total_len])
                return phrase, start, crib_idx
    raise RuntimeError("Could not locate an even-length crib phrase in the sample text.")


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


def _jitter_key(key: np.ndarray, *, swaps: int = 6, seed: int = 0) -> np.ndarray:
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
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(TEXT, direction=direction.value)
    pt_idx_arr = np.array(pt_idx, dtype=np.uint8)

    cipher_spec = by_name.cipher("bigram_sub")
    cipher_obj = cipher_instance(cipher_spec)
    rng = np.random.default_rng(424242)
    alphabet = 29
    key_len = alphabet * alphabet
    true_key = np.arange(key_len, dtype=KEY_DTYPE)
    plaintext_codes = _active_bigram_codes(pt_idx_arr, alphabet)
    if plaintext_codes.size > 64:
        plaintext_codes = np.asarray(
            rng.choice(plaintext_codes, size=64, replace=False), dtype=np.int64
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

    crib_phrase, crib_start, crib_idx = _select_crib(pt_idx, wli, TEXT)
    crib_codes = _build_crib_codes(
        ciphertext_idx,
        pt_idx,
        crib_start,
        len(crib_idx),
        alphabet=29,
    )
    print(f"Crib phrase: {' '.join(crib_phrase)} (start rune {crib_start}, length {len(crib_idx)})")

    cipher_spec = by_name.cipher("bigram_sub", crib=crib_codes)
    key_spec = KeySpec.permutation(len=29 * 29)

    # Stage 1: known key (fast-path sanity)
    recovered_idx = cipher_obj.decrypt_single(
        ciphertext=np.asarray(ciphertext_idx, dtype=np.uint8),
        key=true_key,
    )
    recovered_ratio = _match_ratio(recovered_idx, pt_idx_arr)
    recovered_solution = SimpleNamespace(
        plaintext_idx=recovered_idx.tolist(),
        plaintext=Runeglish.to_rune(recovered_idx.tolist(), wli),
        score=1.0,
        key=true_key.tolist(),
        solver={"name": "known_key_demo"},
        meta={
            "telemetry": {
                "solver": {"name": "known_key_demo"},
                "note": "synthetic-known-key",
            },
            "solver": {"name": "known_key_demo"},
            "timings": {"solve": 0.0},
            "work": {"tokens": int(len(pt_idx_arr))},
        },
    )
    _report_solution(
        "known key",
        solution=recovered_solution,
        ratio=recovered_ratio,
        ciphertext_runes=ciphertext_runes,
        ciphertext_idx=ciphertext_idx,
        pt_idx_reference=pt_idx,
        pt_runes_reference=pt_runes,
        wli=wli,
        direction=direction,
    )

    # Stage 2: LM + crib seeded hybrid search (long run)
    print("Building seed pool (this may take a moment)...")
    prior = build_wli_bigram_prior()
    seed_gen = BigramSeedGenerator(
        alphabet_size=29,
        plaintext_prior=prior,
        crib_ct_codes=[ct for ct, _ in crib_codes],
        crib_pt_codes=[pt for _, pt in crib_codes],
    )
    LM_SEED_COUNT = 896
    RANDOM_SEED_COUNT = 128
    lm_seeds = seed_gen.generate_seeds(
        ciphertext_idx,
        n_seeds=LM_SEED_COUNT,
        n_random=RANDOM_SEED_COUNT,
        seed=2027,
    )
    alignment_seed = cipher_obj.seed_key_from_crib(
        ciphertext_idx,
        crib_idx,
        offset=crib_start // 2,
        alphabet=cipher_obj.alphabet,
        rng_seed=2020,
    ).astype(KEY_DTYPE, copy=False)
    combined_seeds: list[list[int]] = [alignment_seed.tolist()]
    for swaps in (24, 48, 72):
        combined_seeds.append(_jitter_key(alignment_seed, swaps=swaps, seed=8080 + swaps).astype(KEY_DTYPE, copy=False).tolist())
    combined_seeds.extend(lm_seeds)
    print(f"Seed pool contains {len(combined_seeds)} keys "
          f"(LM-derived={LM_SEED_COUNT}, random={RANDOM_SEED_COUNT}, alignment+variants=4).")
    print("Starting hybrid optimisation — expect several minutes on a desktop CPU.")

    _run_scenario(
        "hybrid LM seed",
        ciphertext_runes=ciphertext_runes,
        ciphertext_idx=ciphertext_idx,
        cipher_spec=cipher_spec,
        key_spec=key_spec,
        solver_spec=SolverSpec.hybrid(
            beam_width=96,
            rounds=4,
            use_beam=True,
            ga=dict(pop_size=256, generations=400, mut_prob=0.4, elite_frac=0.1, plateau_gens=50),
            sa=dict(sa_iters=2000),
             progress_pct=5,
             print_progress=True,
             progress_preview_chars=48,
            seed=2027,
        ),
        wli=wli,
        direction=direction,
        pt_idx_reference=pt_idx,
        pt_runes_reference=pt_runes,
        initial_keys=combined_seeds,
    )


if __name__ == "__main__":
    main()
