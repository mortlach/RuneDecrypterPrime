import numpy as np
import pytest

from rune_decrypter_prime.ciphers.periodic_substitution_cipher import PeriodicSubstitutionCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.transpositions import assert_is_permutation
from rune_decrypter_prime.core.types import Device, Direction
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.utils.runeglish import Runeglish

from tools.benchmarks.seed_utils_periodic_columnar_col_then_sub import (
    make_periodic_seed_pool_col_then_sub,
    make_tail_seed_pool,
    combine_periodic_sub_key_with_tail,
)

pytestmark = pytest.mark.tier_a

ALPHABET_SIZE = 29


def _validate_periodic_key_layout(key: list[int], *, period: int, A: int = ALPHABET_SIZE) -> None:
    k = np.asarray(key, dtype=np.int64).reshape(-1)
    assert k.size == int(period) * int(A)
    for r in range(int(period)):
        block = k[r * A : (r + 1) * A].astype(int).tolist()
        assert_is_permutation(block, A)


def test_seed_pool_deterministic_and_layout_ok():
    A = ALPHABET_SIZE
    period = 5
    # A mildly non-uniform ciphertext so rank alignment is meaningful.
    ct = np.asarray(([0] * 50) + ([1] * 40) + ([2] * 30) + ([3] * 20) + ([4] * 10) + list(range(A)) * 3, dtype=np.uint8)
    pt_order = list(range(A))  # deterministic override (no LM dependency)

    keys1 = make_periodic_seed_pool_col_then_sub(
        ct,
        period=period,
        direction="ltr",
        seed=2026,
        n_block_seeds=6,
        total_seeds=24,
        swaps_per_block=2,
        alphabet_size=A,
        pt_unigram_rank_override=pt_order,
        global_shrink=0.25,
        phase_len_target=160,
    )
    keys2 = make_periodic_seed_pool_col_then_sub(
        ct,
        period=period,
        direction="ltr",
        seed=2026,
        n_block_seeds=6,
        total_seeds=24,
        swaps_per_block=2,
        alphabet_size=A,
        pt_unigram_rank_override=pt_order,
        global_shrink=0.25,
        phase_len_target=160,
    )

    assert keys1 == keys2
    assert len(keys1) == 24
    for k in keys1:
        _validate_periodic_key_layout(k, period=period, A=A)


def test_combine_periodic_sub_key_with_tail_validates_and_concatenates():
    A = ALPHABET_SIZE
    period = 3
    columns = 7
    rng = np.random.default_rng(77)
    sub_blocks = [rng.permutation(A).astype(np.int16) for _ in range(period)]
    sub_key = np.concatenate(sub_blocks, axis=0).astype(np.int16).tolist()
    tail = rng.permutation(columns).astype(np.int16).tolist()

    full = combine_periodic_sub_key_with_tail(
        sub_key,
        tail_perm=tail,
        period=period,
        alphabet_size=A,
        columns=columns,
    )
    assert len(full) == period * A + columns

    # Validate blocks remain permutations and tail is a permutation.
    for r in range(period):
        assert_is_permutation(full[r * A : (r + 1) * A], A)
    assert_is_permutation(full[period * A :], columns)


def test_seed_pool_quality_beats_random_baseline_fraction_of_gap_on_periodic_substitution():
    # This is a coverage / initialisation sanity check (not a full solver test).
    A = ALPHABET_SIZE
    period = 5
    direction = Direction.LTR

    rg = Runeglish()
    pt_idx, _wli, _runes = rg.encode_english_to_runes(long_plaintext_string.strip(), direction=direction.value)
    pt = np.asarray(pt_idx[:4000], dtype=np.uint8)  # keep test fast and deterministic

    # A corpus-derived pt unigram rank (no LM assets required).
    counts_pt = np.bincount(pt.astype(np.int64), minlength=A).astype(np.int64)
    pt_order = np.argsort(-counts_pt, kind="stable").astype(np.int64).tolist()

    keyops = PeriodicStructuredMatrixKeyOps(K=period * A, period=period, A=A)
    rng = np.random.default_rng(1234)
    key_true = keyops.random(rng).astype(np.int16)

    cfg = CipherConfig(
        name="periodic_substitution",
        ciphertext=[],
        wli_data=[],
        key_length=period * A,
        period=period,
        alphabet_size=A,
        encoding_dir=direction,
        device=Device.CPU,
    )
    cipher = PeriodicSubstitutionCipher(cfg)
    ct = np.asarray(cipher.encrypt_single(plaintext=pt, key=key_true), dtype=np.uint8)

    def match_count_for_key(key: np.ndarray) -> int:
        rec = np.asarray(cipher.decrypt_single(ciphertext=ct, key=key), dtype=np.uint8).reshape(-1)
        return int(np.count_nonzero(rec == pt))

    oracle = match_count_for_key(key_true)
    random_scores = [match_count_for_key(keyops.random(rng).astype(np.int16)) for _ in range(48)]
    best_random = max(random_scores)

    seed_keys = make_periodic_seed_pool_col_then_sub(
        ct,
        period=period,
        direction=direction.value,
        seed=2026,
        n_block_seeds=8,
        total_seeds=48,
        swaps_per_block=2,
        alphabet_size=A,
        pt_unigram_rank_override=pt_order,
        global_shrink=0.25,
        phase_len_target=160,
    )
    seed_scores = [match_count_for_key(np.asarray(k, dtype=np.int16)) for k in seed_keys]
    best_seed = max(seed_scores)

    gap = oracle - best_random
    improvement = best_seed - best_random
    assert gap > 0, f"Expected oracle to beat random baseline. oracle={oracle} best_random={best_random}"
    assert improvement / gap >= 0.10


def test_make_tail_seed_pool_is_deterministic_and_valid():
    cols = 13
    a = make_tail_seed_pool(columns=cols, seed=123, total_seeds=128, structured_swaps=32, random_seeds=64)
    b = make_tail_seed_pool(columns=cols, seed=123, total_seeds=128, structured_swaps=32, random_seeds=64)
    assert a == b
    assert len(a) == 128
    for perm in a[:20]:
        assert sorted(perm) == list(range(cols))

