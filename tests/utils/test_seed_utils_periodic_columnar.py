import numpy as np
import pytest

from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.transpositions import assert_is_permutation
from rune_decrypter_prime.core.types import Direction, Device, ScorerImpl, ObjectiveFamily, ObjectiveSpec, SeMode, Stat
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import PeriodicStructuredMatrixKeyOps
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.scoring.language_model.language_model_prime import LanguageModelPrime
from rune_decrypter_prime.utils.runeglish import Runeglish
from tests.scoring._helpers.lm_test_guard import require_full_lm_assets

from rune_decrypter_prime.utils.seed_utils_periodic_columnar import (
    SeedPlan,
    generate_seed_keys_periodic_columnar,
)

pytestmark = pytest.mark.tier_a

ALPHABET_SIZE = 29


def _validate_key_layout(key: np.ndarray, *, period: int, columns: int) -> None:
    k = np.asarray(key, dtype=np.int64).reshape(-1)
    assert k.size == period * ALPHABET_SIZE + columns
    for r in range(period):
        block = k[r * ALPHABET_SIZE : (r + 1) * ALPHABET_SIZE]
        assert_is_permutation(block.tolist(), ALPHABET_SIZE)
    tail = k[period * ALPHABET_SIZE :]
    assert_is_permutation(tail.tolist(), columns)


def _make_instance(
    *,
    order: str,
    direction: Direction = Direction.RTL,
    period: int = 5,
    columns: int = 11,
    key_seed: int = 1234,
) -> tuple[np.ndarray, np.ndarray, PeriodicColumnarCipher]:
    txt = long_plaintext_string.strip()
    ##txt = (txt * 3).strip()

    rg = Runeglish()
    pt_idx, _wli, _runes = rg.encode_english_to_runes(txt, direction=direction.value)
    pt_idx = np.asarray(pt_idx, dtype=np.uint8)

    key_len = period * ALPHABET_SIZE + columns

    rng = np.random.default_rng(key_seed)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=ALPHABET_SIZE, columns=columns)
    key_true = keyops.random(rng)

    cfg = CipherConfig(
        name="periodic_columnar",
        ciphertext=[],
        period=period,
        columns=columns,
        alphabet_size=ALPHABET_SIZE,
        order=order,
        encoding_dir=direction,
        key_length=key_len,
        wli_data=[],
        device=Device.CPU,
    )
    cipher = PeriodicColumnarCipher(cfg)
    ct_idx = cipher.encrypt_single(plaintext=pt_idx, key=key_true)
    return ct_idx, key_true, cipher


def _char_only_scoring_cfg(direction: Direction, *, model_root=None) -> ScoringConfig:
    return ScoringConfig(
        model_root=model_root,
        objective=ObjectiveSpec(family=ObjectiveFamily.PCT, stat=Stat.LOGP, win=10),
        se_mode=SeMode.NOSE,
        encoding_dir=direction,
        include_char=True,
        use_word_breaks=False,
        char_weights={3: 0.5, 4: 0.5},
        wli_weights={},
        impl=ScorerImpl.NUMPY,
    )


def _raw_char_score(pt: np.ndarray, *, lm: LanguageModelPrime, weights: dict[int, float], direction: Direction) -> float:
    total_w = float(sum(weights.values()))
    if total_w <= 0:
        raise ValueError("char_weights must include at least one positive weight")
    acc = 0.0
    L = int(pt.size)
    for n, w in weights.items():
        n = int(n)
        total_eval = L - n + 1
        if total_eval <= 0:
            return float("-inf")
        res = lm.score([pt.tolist()], None, direction=direction.value, se="nose", n=n, model="char")[0]
        avg = float(res.logprob_sum) / float(total_eval)
        acc += float(w) * avg
    return acc / total_w


def test_seed_generator_rejects_missing_or_unknown_order():
    ct_idx = np.arange(ALPHABET_SIZE, dtype=np.uint8)

    with pytest.raises(ValueError):
        generate_seed_keys_periodic_columnar(
            ct_idx,
            period=5,
            columns=11,
            order="",
            direction=Direction.RTL,
            seed=1,
            scoring_cfg=None,
            pt_unigram_rank_override=list(range(ALPHABET_SIZE)),
        )

    with pytest.raises(ValueError):
        generate_seed_keys_periodic_columnar(
            ct_idx,
            period=5,
            columns=11,
            order="col_then_sub_then_something",
            direction=Direction.RTL,
            seed=1,
            scoring_cfg=None,
            pt_unigram_rank_override=list(range(ALPHABET_SIZE)),
        )


def test_seed_generator_deterministic_and_layout_ok():
    ct_idx, _, _ = _make_instance(order="col_then_sub")

    keys1 = generate_seed_keys_periodic_columnar(
        ct_idx,
        period=5,
        columns=11,
        order="col_then_sub",
        direction=Direction.RTL,
        seed=2026,
        scoring_cfg=None,
        pt_unigram_rank_override=list(range(ALPHABET_SIZE)),
        n_keys=24,
        plan=SeedPlan(n_block_seeds=6, n_tail_seeds=6, n_starts=24, refine_steps=120),
    )
    keys2 = generate_seed_keys_periodic_columnar(
        ct_idx,
        period=5,
        columns=11,
        order="col_then_sub",
        direction=Direction.RTL,
        seed=2026,
        scoring_cfg=None,
        pt_unigram_rank_override=list(range(ALPHABET_SIZE)),
        n_keys=24,
        plan=SeedPlan(n_block_seeds=6, n_tail_seeds=6, n_starts=24, refine_steps=120),
    )

    assert keys1 == keys2
    assert len(keys1) == 24

    for k in keys1:
        _validate_key_layout(np.asarray(k), period=5, columns=11)


def test_seed_generator_columns_one_tail_identity():
    ct_idx = np.arange(ALPHABET_SIZE, dtype=np.uint8)
    keys = generate_seed_keys_periodic_columnar(
        ct_idx,
        period=3,
        columns=1,
        order="col_then_sub",
        direction=Direction.RTL,
        seed=7,
        scoring_cfg=None,
        pt_unigram_rank_override=list(range(ALPHABET_SIZE)),
        n_keys=6,
        plan=SeedPlan(n_block_seeds=3, n_tail_seeds=3, n_starts=6, refine_steps=0),
    )
    for k in keys:
        assert k[-1] == 0
        _validate_key_layout(np.asarray(k), period=3, columns=1)


def test_seed_generator_quality_beats_random_baseline_fraction_of_gap():
    lm_root, _ = require_full_lm_assets(models=("char",), modes=("ltr",), poses=("nose",), ns=(3, 4), ecdf_stats=("logp",))

    period, columns = 5, 11
    direction = Direction.LTR
    ct_idx, key_true, cipher = _make_instance(order="col_then_sub", direction=direction, period=period, columns=columns)
    cfg = _char_only_scoring_cfg(direction, model_root=lm_root)
    key_length = period * ALPHABET_SIZE + columns

    lm = LanguageModelPrime(
        lm_root=cfg.model_root,
        smoothing=cfg.smoothing,
        alpha=cfg.alpha,
        oov_policy=cfg.oov_policy,
        include_char=True,
    )
    weights = dict(cfg.char_weights) if cfg.char_weights else {3: 0.5, 4: 0.5}

    def score_key(key: np.ndarray) -> float:
        pt = cipher.decrypt_single(ciphertext=ct_idx, key=key)
        return _raw_char_score(pt, lm=lm, weights=weights, direction=direction)

    oracle = score_key(key_true)

    rng = np.random.default_rng(999)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_length, period=period, A=ALPHABET_SIZE, columns=columns)
    random_scores = [score_key(keyops.random(rng)) for _ in range(48)]
    best_random = max(random_scores)

    seed_keys = generate_seed_keys_periodic_columnar(
        ct_idx,
        period=period,
        columns=columns,
        order="col_then_sub",
        direction=direction,
        seed=2026,
        scoring_cfg=cfg,
        n_keys=24,
        plan=SeedPlan(n_block_seeds=6, n_tail_seeds=6, n_starts=28, refine_steps=220),
        refine=True,
    )
    seed_scores = [score_key(np.asarray(k, dtype=np.int16)) for k in seed_keys]
    best_seed = max(seed_scores)

    gap = oracle - best_random
    improvement = best_seed - best_random

    assert gap > 1e-6, (
        "Oracle score should exceed random baseline; check LM root/direction and scoring path. "
        f"oracle={oracle:.6f} best_random={best_random:.6f}"
    )
    assert improvement / gap >= 0.10
