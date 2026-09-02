from __future__ import annotations
from pathlib import Path
import pytest
from rdp.scoring.hamming.loader import load_raw1grams_wordlists
from rdp.scoring.hamming.backend import HammingBackend
from rdp.data.runeglish import Runeglish
try:
    from rdp.scoring.hamming import _hamming as _hamming_extension

    _EXT_AVAILABLE = True
except Exception:
    _EXT_AVAILABLE = False
requires_ext = pytest.mark.skipif(not _EXT_AVAILABLE, reason='Hamming extension not built')

def _write_csv(path: Path, rows):
    lines = []
    for r in rows:
        lines.append(','.join(r))
    path.write_text('\n'.join(lines), encoding='utf-8')

@requires_ext
def test_loader_filters_selected_and_builds_rtl(tmp_path: Path):
    f_runes = Runeglish.pos_to_rune([0])
    fa_runes = Runeglish.pos_to_rune([0, 24])
    rows_01 = [['F', '10', '1', f_runes, '1'], ['SKIP', '2', '0', f_runes, '2']]
    rows_02 = [['FA', '5', '1', fa_runes, '3']]
    _write_csv(tmp_path / 'raw1grams_01.csv', rows_01)
    _write_csv(tmp_path / 'raw1grams_02.csv', rows_02)
    wl_ltr, wl_rtl = load_raw1grams_wordlists(tmp_path, build_rtl=True)
    assert 1 in wl_ltr and 2 in wl_ltr
    assert wl_rtl is not None and 1 in wl_rtl and (2 in wl_rtl)
    assert wl_ltr[1] == [[0]]
    assert wl_ltr[2] == [[0, 24]]
    rtl_fa, _, _ = Runeglish.encode_english_to_runes('FA', direction='rtl')
    assert wl_rtl[1] == [[0]]
    assert wl_rtl[2] == [list(rtl_fa)]

@requires_ext
def test_hamming_backend_total_hd_and_direction_modes():
    wl_ltr = {2: [[1, 3], [1, 2]], 1: [[0]]}
    wl_rtl = {1: [[5]]}
    backend = HammingBackend(wl_ltr, wl_rtl, max_hd=10, length_weights={1: 2.0})
    runes = [1, 3, 0]
    wli = [[0, 2], [1, 2], [0, 1]]
    assert backend.total_min_hd(runes, wli, direction='ltr') == 0.0
    runes_miss = [1, 3, 7]
    hd = backend.total_min_hd(runes_miss, wli, direction='ltr')
    assert hd == pytest.approx(2.0)
    runes_rtl = [5]
    wli_rtl = [[0, 1]]
    hd_both = backend.total_min_hd(runes_rtl, wli_rtl, direction='ltr', mode='both')
    assert hd_both == 0.0

@requires_ext
def test_hamming_backend_respects_max_hd_short_circuit():
    wl = {2: [[0, 0]]}
    backend = HammingBackend(wl, None, max_hd=1)
    runes = [1, 1]
    wli = [[0, 2], [1, 2]]
    assert backend.total_min_hd(runes, wli, direction='ltr') >= 1.0
