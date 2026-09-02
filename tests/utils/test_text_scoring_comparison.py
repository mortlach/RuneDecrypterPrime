from __future__ import annotations
import numpy as np
import pytest
from rdp.core.types import Direction
from rune_decrypter_prime.data.cipher_tests.plaintext import long_plaintext_string
from rune_decrypter_prime.utils.text_scoring_comparison import compare_two_texts, default_scoring_methods

def _randomize_letters_preserving_spaces(text: str, *, seed: int) -> str:
    rng = np.random.default_rng(int(seed))
    alphabet = np.asarray(list('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    out = []
    for ch in text:
        if ch.isalpha():
            out.append(str(rng.choice(alphabet)))
        else:
            out.append(ch)
    return ''.join(out)

def test_default_scoring_methods_cover_char_and_wli_n1_to_n4():
    methods = default_scoring_methods()
    names = {m.name for m in methods}
    for n in range(1, 5):
        assert f'raw_char_n{n}' in names
        assert f'raw_wli_n{n}_full' in names
        assert f'pct_char_n{n}' in names
        assert f'pct_wli_n{n}' in names
    assert 'raw_combo_char34_wli12_full' in names
    assert 'pct_combo_char34_wli12' in names

@pytest.mark.full_assets
@pytest.mark.tier_a
def test_compare_two_texts_scores_real_beats_random_on_core_methods():
    from tests.scoring._helpers.lm_test_guard import require_full_lm_assets
    lm_root, _ = require_full_lm_assets(models=('char', 'wli'), modes=('ltr',), poses=('nose',), ns=(1, 2, 3, 4), ecdf_stats=('logp',))
    text_a = long_plaintext_string[:700]
    text_b = _randomize_letters_preserving_spaces(text_a, seed=20260214)
    rows = compare_two_texts(text_a, text_b, direction=Direction.LTR, model_root=lm_root)
    assert rows
    by_name = {r.method: r for r in rows}
    for method_name in ('raw_char_n4', 'pct_char_n4', 'raw_wli_n2_full', 'pct_wli_n2'):
        assert method_name in by_name
        row = by_name[method_name]
        assert np.isfinite(row.score_a)
        assert np.isfinite(row.score_b)
        assert row.score_a > row.score_b
