from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import List, Sequence, Tuple

import numpy as np

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, cipher_instance, run
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
from rune_decrypter_prime.core.config import ScoringConfig
from rune_decrypter_prime.core.engine.builders import build_scorer
from rune_decrypter_prime.core.types import KEY_DTYPE, Device
from rune_decrypter_prime.utils.bigram_seed_generator import BigramSeedGenerator, build_wli_bigram_prior
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string

APP_VERSION = "tutorial-bigram-sub-3.0"
ALPHABET_SIZE = 29
BIGRAM_KEY_LEN = ALPHABET_SIZE * ALPHABET_SIZE
CIPHERTEXT_SEED = 424242
HYBRID_SEED = 2027
LM_SEED_COUNT = 1250
RANDOM_SEED_COUNT = 250

PHRASE_CANDIDATES: List[List[str]] = [
    ["FAST", "ASLEEP", "AND", "THE"],
    ["THERE", "WAS", "A", "TABLE", "SET", "OUT"],
    ["MARCH", "HARE"],
    ["FAST", "ASLEEP", "AND"],
    ["FAST", "ASLEEP"],
    ["OTHER", "TWO"],
]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def preview(s: str, n: int = 120) -> str:
    return s if len(s) <= n else s[:n] + "..."


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


def _build_word_spans(
    wli: Sequence[Sequence[int]],
    source_text: str,
) -> List[Tuple[str, int, int]]:
    words = re.findall(r"[A-Za-z]+", source_text.upper())
    spans: List[Tuple[str, int, int]] = []
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
) -> Tuple[List[str], int, List[int]]:
    spans = _build_word_spans(wli, source_text)
    for window in range(10, 3, -1):
        for idx in range(len(spans) - window + 1):
            phrase = [spans[idx + j][0] for j in range(window)]
            start = spans[idx][1]
            total_len = sum(spans[idx + j][2] for j in range(window))
            if start % 2 != 0 or total_len % 2 != 0 or total_len < 30:
                continue
            crib_idx = list(pt_idx[start:start + total_len])
            return phrase, start, crib_idx
    for phrase in PHRASE_CANDIDATES:
        for idx in range(len(spans) - len(phrase) + 1):
            if all(spans[idx + j][0] == phrase[j] for j in range(len(phrase))):
                start = spans[idx][1]
                total_len = sum(spans[idx + j][2] for j in range(len(phrase)))
                if start % 2 != 0 or total_len % 2 != 0:
                    continue
                crib_idx = list(pt_idx[start:start + total_len])
                return phrase, start, crib_idx
    raise RuntimeError("Could not locate an even-length crib phrase in the sample text.")


def _build_crib_codes(
    ciphertext_idx: Sequence[int],
    plaintext_idx: Sequence[int],
    start: int,
    span_len: int,
    *,
    alphabet: int,
) -> List[dict]:
    entries: List[dict] = []
    for offset in range(0, span_len, 2):
        ct_a = ciphertext_idx[start + offset]
        ct_b = ciphertext_idx[start + offset + 1]
        pt_a = plaintext_idx[start + offset]
        pt_b = plaintext_idx[start + offset + 1]
        ct_code = ct_a * alphabet + ct_b
        pt_code = pt_a * alphabet + pt_b
        entries.append({"cipher": ct_code, "plaintext": pt_code})
    return entries


def _jitter_key(key: np.ndarray, *, swaps: int = 6, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    out = np.array(key, copy=True)
    K = out.size
    for _ in range(max(1, swaps)):
        i, j = rng.integers(0, K, size=2)
        if i != j:
            out[i], out[j] = out[j], out[i]
    return out


def _build_ciphertext(pt_en: str, *, encoding_dir: Direction):
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        pt_en, direction=encoding_dir.value
    )
    pt_idx_arr = np.asarray(pt_idx, dtype=np.uint8)
    cipher_spec = by_name.cipher("bigram_sub")
    cipher_obj = cipher_instance(cipher_spec)
    rng = np.random.default_rng(CIPHERTEXT_SEED)
    key_len = BIGRAM_KEY_LEN
    true_key = np.arange(key_len, dtype=KEY_DTYPE)
    shuffled = np.arange(key_len, dtype=KEY_DTYPE)
    rng.shuffle(shuffled)
    true_key = shuffled.astype(KEY_DTYPE, copy=False)
    ct_arr = cipher_obj.encrypt_single(
        plaintext=pt_idx_arr,
        key=true_key,
    )
    ciphertext_idx = ct_arr.astype(np.uint8, copy=False).tolist()
    ciphertext_runes = Runeglish.to_rune(ciphertext_idx, wli)
    return cipher_obj, ciphertext_idx, ciphertext_runes, pt_idx, pt_runes, wli, true_key


def _build_seed_pool(
    cipher_obj,
    ciphertext_idx: Sequence[int],
    crib_idx: Sequence[int],
    crib_start: int,
    crib_codes: Sequence[dict],
) -> List[List[int]]:
    prior = build_wli_bigram_prior()
    ct_codes = [entry["cipher"] for entry in crib_codes]
    pt_codes = [entry["plaintext"] for entry in crib_codes]
    seed_gen = BigramSeedGenerator(
        alphabet_size=ALPHABET_SIZE,
        plaintext_prior=prior,
        crib_ct_codes=ct_codes,
        crib_pt_codes=pt_codes,
    )
    lm_seeds = seed_gen.generate_seeds(
        ciphertext_idx,
        n_seeds=LM_SEED_COUNT,
        n_random=RANDOM_SEED_COUNT,
        seed=HYBRID_SEED,
    )
    alignment_seed = cipher_obj.seed_key_from_crib(
        ciphertext_idx,
        crib_idx,
        offset=crib_start // 2,
        alphabet=cipher_obj.alphabet,
        rng_seed=2020,
    ).astype(KEY_DTYPE, copy=False)
    seeds: List[List[int]] = [alignment_seed.tolist()]
    for swaps in (24, 48, 72, 96):
        seeds.append(
            _jitter_key(alignment_seed, swaps=swaps, seed=8080 + swaps)
            .astype(KEY_DTYPE, copy=False)
            .tolist()
        )
    seeds.extend(lm_seeds)
    return seeds


def _build_hybrid_spec() -> SolverSpec:
    return SolverSpec.hybrid(
        use_beam=True,
        beam_width=128,
        rounds=6,
        expand_mode="sample",
        sample_per_parent=24,
        top_parents_factor=0.65,
        progress_pct=2,
        print_progress=True,
        progress_preview_chars=80,
        ga=dict(
            pop_size=512,
            generations=900,
            elite_frac=0.10,
            cx_frac=0.8,
            mut_prob=0.35,
            tournament_k=4,
            plateau_gens=120,
            print_progress=True,
        ),
        sa=dict(
            sa_iters=6000,
            sa_init_temp=1.0,
            sa_min_temp=1e-4,
            sa_auto_cooling=True,
            sa_cooling=0.997,
            sa_elitism=True,
            sa_rescue_drop_abs=0.05,
            sa_rescue_drop_ratio=0.5,
            sa_reseed_interval=2000,
            local_improve_on_accept=False,
            print_progress=True,
        ),
        seed=HYBRID_SEED,
        verbose=True,
        log_interval=10,
    )

# NOTE: legacy tutorials still use the older `n_char` / `n_wli` knobs.
#       This example uses the modern explicit weight dictionaries.
def _build_scorer_params(direction: Direction) -> dict:
    return dict(
        objective="pct.logp.win8",
        include_char=True,
        use_word_breaks=True,
        encoding_dir=direction,
        char_weights={2: 0.3, 3: 0.3, 4: 0.3},
        wli_weights={2: 0.7, 3: 0.7, 4: 0.7},
    )


def _score_plaintext_pct(
    plaintext_idx: Sequence[int],
    *,
    ciphertext_idx: Sequence[int],
    wli,
    encoding_dir: Direction,
    scorer_params: dict,
) -> float:
    scoring_cfg = ScoringConfig(**scorer_params)
    scoring_cfg.encoding_dir = encoding_dir
    cipher_spec = by_name.cipher("bigram_sub")
    cipher_cfg = build_cipher_config(
        cipher=cipher_spec,
        key=KeySpec.permutation(len=BIGRAM_KEY_LEN),
        ciphertext=np.asarray(ciphertext_idx, dtype=np.uint8),
        wli=wli,
        device=Device.CPU,
        encoding_dir=encoding_dir,
        initial_text_permutation_indices=None,
        initial_keys=None,
    )
    scorer = build_scorer(cipher_cfg, scoring_cfg)
    return float(scorer.score(plaintext_idx, wli))


def _report_solution(
    label: str,
    *,
    solution,
    match_ratio: float,
    ciphertext_runes: str,
    ciphertext_idx: Sequence[int],
    pt_idx_reference: Sequence[int],
    pt_runes_reference: str,
    wli,
    direction: Direction,
) -> None:
    print_run_report(
        title=f"Bigram Substitution ({label})",
        cipher="bigram_sub",
        solution=solution,
        match_ok=(match_ratio >= 0.9) if label == "known key" else None,
        app_version=APP_VERSION,
        key_idx=getattr(solution, "key", None),
        key_len=BIGRAM_KEY_LEN,
        ct_idx=ciphertext_idx,
        ct_rune=ciphertext_runes,
        pt_rune_ref=pt_runes_reference,
        pt_idx_ref=pt_idx_reference,
        wli=wli,
    )
    print(f"Match ratio ({label}): {match_ratio:.3f}")


def main() -> None:
    encoding_dir = Direction.LTR
    scorer_params = _build_scorer_params(encoding_dir)
    pt_en = plaintext_english_string
    (
        cipher_obj,
        ciphertext_idx,
        ciphertext_runes,
        pt_idx,
        pt_runes,
        wli,
        true_key,
    ) = _build_ciphertext(pt_en, encoding_dir=encoding_dir)
    crib_phrase, crib_start, crib_idx = _select_crib(pt_idx, wli, pt_en)
    crib_codes = _build_crib_codes(
        ciphertext_idx,
        pt_idx,
        crib_start,
        len(crib_idx),
        alphabet=ALPHABET_SIZE,
    )
    print(
        f"Crib phrase: {' '.join(crib_phrase)} "
        f"(start rune {crib_start}, length {len(crib_idx)})"
    )
    recovered_idx = cipher_obj.decrypt_single(
        ciphertext=np.asarray(ciphertext_idx, dtype=np.uint8),
        key=true_key,
    )
    recovered_list = recovered_idx.tolist()
    recovered_ratio = _match_ratio(recovered_idx, pt_idx)
    known_score = _score_plaintext_pct(
        recovered_list,
        ciphertext_idx=ciphertext_idx,
        wli=wli,
        encoding_dir=encoding_dir,
        scorer_params=scorer_params,
    )
    print(f"[KnownKey] pct.win8 score: {known_score:.6f}")
    recovered_solution = SimpleNamespace(
        plaintext_idx=recovered_list,
        plaintext=Runeglish.to_rune(recovered_list, wli),
        score=known_score,
        key=true_key.tolist(),
        solver={"name": "known_key_demo"},
        meta={
            "telemetry": {
                "solver": {"name": "known_key_demo"},
                "note": "synthetic-known-key",
            },
            "solver": {"name": "known_key_demo"},
            "timings": {"solve": 0.0},
            "work": {"tokens": int(len(pt_idx))},
        },
    )
    print("-" * 72)
    _report_solution(
        "known key",
        solution=recovered_solution,
        match_ratio=recovered_ratio,
        ciphertext_runes=ciphertext_runes,
        ciphertext_idx=ciphertext_idx,
        pt_idx_reference=pt_idx,
        pt_runes_reference=pt_runes,
        wli=wli,
        direction=encoding_dir,
    )
    print("Building seed pool (LM + crib)...")
    seed_pool = _build_seed_pool(
        cipher_obj,
        ciphertext_idx,
        crib_idx,
        crib_start,
        crib_codes,
    )
    print(
        f"Seed pool contains {len(seed_pool)} keys "
        f"(LM-derived={LM_SEED_COUNT}, random={RANDOM_SEED_COUNT}, alignment+variants=4)."
    )
    print("Starting hybrid optimisation -- long run (~15+ minutes on desktop CPU).")
    legacy_crib = [(entry["cipher"], entry["plaintext"]) for entry in crib_codes]
    cipher_spec_with_crib = by_name.cipher("bigram_sub", crib=legacy_crib)
    logging_cfg = dict(progress_pct=2, print_progress=True)

    solution = run(
        text=ciphertext_runes,
        cipher=cipher_spec_with_crib,
        key=KeySpec.permutation(len=BIGRAM_KEY_LEN),
        solver=_build_hybrid_spec(),
        device="cpu",
        scorer_params=dict(scorer_params),
        wli_data=wli,
        encoding_dir=encoding_dir,
        telemetry_on=True,
        logging=logging_cfg,
        initial_keys=seed_pool,
    )
    match_ratio = _match_ratio(solution.plaintext_idx, pt_idx)
    _report_solution(
        "hybrid LM seed",
        solution=solution,
        match_ratio=match_ratio,
        ciphertext_runes=ciphertext_runes,
        ciphertext_idx=ciphertext_idx,
        pt_idx_reference=pt_idx,
        pt_runes_reference=pt_runes,
        wli=wli,
        direction=encoding_dir,
    )


if __name__ == "__main__":
    main()
