from rdp import api
import numpy as np
import pytest
from rune_decrypter_prime.ciphers.periodic_columnar_cipher import PeriodicColumnarCipher
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rdp.core.types import (
    Device,
    Direction,
)
from rune_decrypter_prime.keyops.periodic_structured_matrix_ops import (
    PeriodicStructuredMatrixKeyOps,
)
from rdp.data.runeglish import Runeglish
from rune_decrypter_prime.utils.seed_utils_periodic_columnar import SeedPlan, generate_seed_keys_periodic_columnar
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
ALPHABET_SIZE = 29

def _word_aligned_prefix_len(wli: list[list[int]], target: int) -> int:
    end = min(int(target), len(wli))
    while end > 0:
        pos, ln = wli[end - 1]
        if pos == ln - 1:
            return end
        end -= 1
    return 0

def _assert_perm(x: np.ndarray, size: int) -> None:
    arr = np.asarray(x, dtype=np.int64).reshape(-1)
    assert arr.size == size
    assert arr.min() >= 0 and arr.max() < size
    assert np.unique(arr).size == size

def test_seed_generator_wli_rerank_requires_wli_data_when_enabled():
    with pytest.raises(ValueError):
        generate_seed_keys_periodic_columnar(np.asarray([0, 1, 2, 3], dtype=np.uint8), period=2, columns=2, order='col_then_sub', direction=Direction.RTL, seed=0, scoring_cfg=None, pt_unigram_rank_override=list(range(29)), n_keys=4, refine=False, rerank_cfg=api.ScoringConfig(word_length_lane_enabled=True))

@pytest.mark.full_assets
def test_seed_generator_wli_rerank_runs_when_assets_present():
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
    lm_root, _ = require_full_lm_assets(models=('char', 'wli'), modes=('rtl',), poses=('nose',), ns=(3, 4), ecdf_stats=('logp',))
    period, columns = (5, 11)
    pt_idx, wli, _runes = Runeglish.encode_english_to_runes(long_plaintext_string, direction='rtl')
    L = _word_aligned_prefix_len(wli, 600)
    assert L >= 200
    pt = np.asarray(pt_idx[:L], dtype=np.uint8)
    wli_slice = wli[:L]
    key_len = period * ALPHABET_SIZE + columns
    rng = np.random.default_rng(123)
    keyops = PeriodicStructuredMatrixKeyOps(K=key_len, period=period, A=ALPHABET_SIZE, columns=columns)
    key_true = keyops.random(rng).astype(np.int16, copy=False)
    cipher_cfg = CipherConfig(name='periodic_columnar', ciphertext=[], period=period, columns=columns, alphabet_size=ALPHABET_SIZE, key_length=key_len, order='col_then_sub', encoding_dir=Direction.RTL, wli_data=[], device=Device.CPU)
    cipher = PeriodicColumnarCipher(cipher_cfg)
    ct = cipher.encrypt_single(plaintext=pt, key=key_true)
    scoring_cfg = api.ScoringConfig(
        language_model_root=lm_root,
        character_lane_enabled=True,
        word_length_lane_enabled=False,
        character_order_weights={3: 0.5, 4: 0.5},
        word_length_order_weights={},
        backend=api.advanced.ScorerBackend.NUMPY,
    )
    rerank_cfg = api.ScoringConfig(
        language_model_root=lm_root,
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={3: 0.25, 4: 0.25},
        word_length_order_weights={3: 0.25, 4: 0.25},
        backend=api.advanced.ScorerBackend.NUMPY,
    )
    keys = generate_seed_keys_periodic_columnar(
        ct,
        period=period,
        columns=columns,
        order="col_then_sub",
        direction=Direction.RTL,
        seed=2026,
        wli_data=wli_slice,
        scoring_cfg=scoring_cfg,
        n_keys=16,
        plan=SeedPlan(n_block_seeds=4, n_tail_seeds=4, n_starts=16, refine_steps=0),
        refine=False,
        rerank_cfg=rerank_cfg,
    )
    assert isinstance(keys, list)
    assert len(keys) == 16
    for k in keys:
        arr = np.asarray(k, dtype=np.int16).reshape(-1)
        assert arr.size == key_len
        for r in range(period):
            _assert_perm(arr[r * ALPHABET_SIZE:(r + 1) * ALPHABET_SIZE], ALPHABET_SIZE)
        _assert_perm(arr[period * ALPHABET_SIZE:], columns)
