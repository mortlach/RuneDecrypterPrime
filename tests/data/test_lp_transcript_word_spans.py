from __future__ import annotations
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript
from rune_decrypter_prime.utils.runeglish import Runeglish

def test_word_spans_page_boundary_and_wli_is_slice_relative(tmp_path):
    r1, r2, r3 = Runeglish.runes[:3]
    raw = f'{r1}{r2}/\n%\n{r3}/\n%\n'
    path = tmp_path / 'span.txt'
    path.write_text(raw, encoding='utf-8')
    doc = LPTranscript.from_file(path)
    p0 = doc.page(0).glyph_span()
    p1 = doc.page(1).glyph_span()
    ct0, wli0 = p0.ct_wli()
    assert ct0 == [Runeglish.rune2pos[r1], Runeglish.rune2pos[r2]]
    assert wli0 == [[0, 2], [1, 2]]
    ct1, wli1 = p1.ct_wli()
    assert ct1 == [Runeglish.rune2pos[r3]]
    assert wli1 == [[0, 1]]
    span = doc.glyph_span(p0.g_start, p1.g_end - p0.g_start)
    ct2, wli2 = span.ct_wli()
    assert ct2 == [Runeglish.rune2pos[r1], Runeglish.rune2pos[r2], Runeglish.rune2pos[r3]]
    assert wli2 == [[0, 3], [1, 3], [2, 3]]
