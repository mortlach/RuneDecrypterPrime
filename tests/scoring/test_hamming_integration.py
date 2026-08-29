from __future__ import annotations
from rdp import api
import csv
import numpy as np
import pytest
from pathlib import Path
from rune_decrypter_prime.core.config.cipher import CipherConfig
from rune_decrypter_prime.core.config.scoring import ScoringConfig
from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.scoring import rune_scorer
from rune_decrypter_prime.scoring.hamming.loader import default_hamming_dir, load_raw1grams_wordlists
from rune_decrypter_prime.scoring.hamming.backend import HammingBackend
from rune_decrypter_prime.utils.runeglish import Runeglish
try:
    import rune_decrypter_prime.scoring.hamming._hamming as _h
    _EXT_AVAILABLE = True
except Exception:
    _EXT_AVAILABLE = False
requires_ext = pytest.mark.skipif(not _EXT_AVAILABLE, reason='Hamming extension not built')

class _StubECDF:

    def validate_clamp_range(self, **_kwargs):
        return None

    def load(self, **_kwargs):
        grid = np.array([0.0, 1.0], dtype=np.float64)
        q = np.array([0.0, 1.0], dtype=np.float64)
        return (grid, q)

    def interp_percentile(self, grid, q, x):
        return np.zeros_like(np.asarray(x, dtype=np.float32))

    @staticmethod
    def energy(p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=np.float32)
        return (-np.log1p(-np.clip(p, 0.0, 1.0))).astype(np.float32, copy=False)

    def asset_id(self, **_kwargs):
        return 'stub'

    def meta_hash(self, **_kwargs):
        return 'stub'

    def interp_dtype(self, **_kwargs):
        return 'float64'

    def meta(self, **_kwargs):
        return {}

class _StubRt:
    """Minimal LM runtime stub that returns zero logp stats."""

    def __init__(self, *_, **__):
        self.ecdf = _StubECDF()

    def _score_batch_char(self, _dir, _se, _n, pt_windows):
        nwin = pt_windows.shape[0] if hasattr(pt_windows, 'shape') else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float32)
        return (zeros, zeros, zeros)

    def _score_batch_wli(self, _dir, _se, _n, pt_windows, _wli_windows):
        nwin = pt_windows.shape[0] if hasattr(pt_windows, 'shape') else len(pt_windows or [])
        zeros = np.zeros((nwin,), dtype=np.float32)
        return (zeros, zeros, zeros)

def _cipher_config() -> CipherConfig:
    return CipherConfig(ciphertext=[], wli_data=[], key_length=None, encoding_dir=Direction.LTR)

@requires_ext
def test_hamming_affects_rune_scorer(monkeypatch):
    wl_ltr, _ = load_raw1grams_wordlists()
    assert wl_ltr and 1 in wl_ltr, 'Default hamming wordlists should include length-1 entries'
    word = wl_ltr[1][0]
    pt = [word[0]] * 10
    wli = [[0, 1] for _ in range(len(pt))]
    monkeypatch.setattr(rune_scorer, 'LmPrimeRuntime', _StubRt)
    cfg = api.ScoringConfig(hamming_enabled=True, hamming_weight=1.0, hamming_wordlist_directory=None)
    scorer = rune_scorer.RuneScorer(_cipher_config(), cfg)
    assert scorer._hamming_backend is not None, 'Hamming backend should be initialised'
    pct_match, raw_match = scorer.score_with_raw(pt, wli)
    assert pct_match == pytest.approx(1e-06, rel=0, abs=1e-08)
    backend = scorer._hamming_backend
    mutated = list(pt)
    mutated[0] = (mutated[0] + 1) % 29
    stats = backend.total_min_hd_stats(mutated, wli, direction=Direction.LTR)
    hd_mut = stats['total_hd']
    hd_avg = stats['avg_hd_word']
    assert hd_mut == 1
    pct_miss, raw_miss = scorer.score_with_raw(mutated, wli)
    assert pct_miss == pytest.approx(pct_match, rel=0, abs=1e-12)
    assert raw_miss == pytest.approx(raw_match - hd_avg, rel=1e-06, abs=1e-06)

@requires_ext
def test_selected_vs_unselected_words_have_correct_hd(monkeypatch):
    base: Path = default_hamming_dir()
    assert base.exists(), 'Default hamming_raw_1g assets must exist'
    wl_ltr, _ = load_raw1grams_wordlists()
    backend = HammingBackend(wl_ltr, None, max_hd=10)
    samples: list[tuple[int, list[str], list[str]]] = []
    for length in range(1, 6):
        fname = base / f'raw1grams_{length:02d}.csv'
        if not fname.exists():
            continue
        selected: list[str] = []
        unselected: list[str] = []
        with fname.open('r', encoding='utf-8', newline='') as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 4:
                    continue
                rune_str = row[3]
                flag = row[2].strip()
                if flag == '1' and len(selected) < 5:
                    selected.append(rune_str)
                if flag != '1' and len(unselected) < 5:
                    unselected.append(rune_str)
                if len(selected) >= 5 and len(unselected) >= 5:
                    break
        samples.append((length, selected, unselected))
    for length, selected, unselected in samples:
        for rune_str in selected:
            idx = Runeglish.rune_to_pos(rune_str)
            wli = [[i, length] for i in range(length)]
            hd = backend.total_min_hd(idx, wli, direction=Direction.LTR)
            assert hd == 0, f'Selected word {rune_str} (len {length}) should match exactly'
        hd_positive = 0
        for rune_str in unselected:
            idx = Runeglish.rune_to_pos(rune_str)
            wli = [[i, length] for i in range(length)]
            if idx in wl_ltr.get(length, []):
                continue
            hd = backend.total_min_hd(idx, wli, direction=Direction.LTR)
            assert hd > 0, f'Unselected word {rune_str} (len {length}) should incur HD > 0'
            hd_positive += 1
        if unselected:
            assert hd_positive >= 1, f'Expected at least one unique unselected word with HD>0 for len {length}'
    pair = next(((l, s[0], u[0]) for l, s, u in samples if s and u), None)
    if pair is None:
        pytest.skip('No length found with both selected and unselected samples')
    length, sel_rune, unsel_rune = pair
    sel_idx = Runeglish.rune_to_pos(sel_rune)
    unsel_idx = Runeglish.rune_to_pos(unsel_rune)
    copies = (10 + length - 1) // length
    sel_pt = list(sel_idx) * copies
    unsel_pt = list(unsel_idx) * copies
    wli = [[i, length] for _ in range(copies) for i in range(length)]
    monkeypatch.setattr(rune_scorer, 'LmPrimeRuntime', _StubRt)
    cfg = api.ScoringConfig(hamming_enabled=True, hamming_weight=1.0)
    scorer = rune_scorer.RuneScorer(_cipher_config(), cfg)
    assert scorer._hamming_backend is not None
    pct_sel, raw_sel = scorer.score_with_raw(sel_pt, wli)
    pct_unsel, raw_unsel = scorer.score_with_raw(unsel_pt, wli)
    assert pct_unsel == pytest.approx(pct_sel, rel=0, abs=1e-12)
    assert raw_unsel < raw_sel, 'Unselected word should score worse due to HD penalty'
