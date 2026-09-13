from __future__ import annotations

from pathlib import Path

import pytest

from rdp.data.liber_primus.lp_main import load_main_transcript
from rdp.data.liber_primus.lp_source_catalogue import payload_from_label
from rdp.data.liber_primus.lp_transcript import Delimiters, LPTranscript
from rdp.data.runeglish import Runeglish

pytestmark = pytest.mark.tier_a


def parse(raw: str) -> LPTranscript:
    return LPTranscript(delimiters=Delimiters(), raw_text=raw)


def test_colour_crosses_physical_and_encoded_lines_without_breaking_word():
    raw = '[red]ᚠ/\r\nᚢ\r\nᚦ[/red]-ᚩ./'
    doc = parse(raw)
    assert doc.raw == raw
    assert [w.text for w in doc.words] == ['ᚠᚢᚦ', 'ᚩ']
    assert len(doc.lines) == 2  # '/' remains the authoritative line marker.
    assert doc.page(0).glyph_span().ct_wli()[1] == [[0, 3], [1, 3], [2, 3], [0, 1]]


def test_adjacent_marks_and_split_marks_create_one_word_gap():
    doc = parse('[dot_13]ᚠ[dot_3_L]/\n-[red][dot_10][/red].ᚢ[dot_23]/')
    assert [w.text for w in doc.words] == ['ᚠ', 'ᚢ']
    assert doc.page(0).text(line_sep=' ') == 'ᚠ ᚢ'
    assert doc.page(0).glyph_span().ct_wli()[1] == [[0, 1], [0, 1]]


def test_numeral_is_retained_but_not_a_rune_or_an_implicit_word_boundary():
    doc = parse('ᚠ[red]3[/red]ᚢ/')
    assert ''.join(doc.glyphs) == 'ᚠ3ᚢ'
    assert doc.page(0).glyph_span().ct_wli() == (
        [Runeglish.rune2pos['ᚠ'], Runeglish.rune2pos['ᚢ']], [[0, 2], [1, 2]],
    )


@pytest.mark.parametrize('tag', ['[dot_3_L]', '[dot_3_R]', '[dot_5]', '[dot_10]',
                                      '[dot_11]', '[dot_13]', '[dot_23]', '[dot_7_custom]'])
def test_dot_counts_and_shape_suffixes_are_extensible(tag):
    assert [w.text for w in parse(f'ᚠ{tag}ᚢ/').words] == ['ᚠ', 'ᚢ']


@pytest.mark.parametrize('raw', [
    'ᚠ[red', 'ᚠ[/red]/', '[red]ᚠ/', '[red]ᚠ[red]ᚢ[/red]/',
    'ᚠ[reed]ᚢ/', 'ᚠ[dot_0]ᚢ/', 'ᚠ[dot_3_]ᚢ/', 'ᚠ]ᚢ/',
])
def test_malformed_typography_fails_with_source_location(raw):
    with pytest.raises(ValueError, match=r'file line 1, column \d+'):
        parse(raw)


@pytest.fixture(scope='module')
def masters():
    root = Path(__file__).resolve().parents[2]
    old = LPTranscript.from_file(root / 'assets/liber_primus/liber-primus__transcription--master.txt')
    return old, load_main_transcript(attach_catalogue=True)


def test_master_migration_preserves_glyphs_pages_and_lines(masters):
    old, new = masters
    assert len(new.pages) == len(old.pages) == 73
    assert len(new.lines) == len(old.lines) == 797
    assert new.glyphs == old.glyphs
    assert len(new.glyphs) == 16757
    for old_line, new_line in zip(old.lines, new.lines):
        assert (old_line.g_start, old_line.g_end) == (new_line.g_start, new_line.g_end)
    for page in range(73):
        old_ct, old_wli = old.page(page).glyph_span().ct_wli()
        new_ct, new_wli = new.page(page).glyph_span().ct_wli()
        assert new_ct == old_ct
        assert '  ' not in new.page(page).text(line_sep=' ')
        if page != 52:  # Canonical LP37: deliberately removed dot beside numeral 3.
            assert new_wli == old_wli
        else:
            assert old_wli[89:94] == [[0, 2], [1, 2], [0, 3], [1, 3], [2, 3]]
            assert new_wli == old_wli[:89] + [[i, 5] for i in range(5)] + old_wli[94:]


@pytest.mark.parametrize('label', [
    'warning', 'welcome_pilgrim', 'some_wisdom', 'koan_a_man',
    'loss_of_divinity', 'koan_during_lesson', 'instruction', 'an_end', 'parable',
])
def test_all_solved_sources_keep_their_ciphertext_and_wli(masters, label):
    old, new = masters
    before = payload_from_label(label, doc=old)
    after = payload_from_label(label, doc=new)
    assert after.ct_idx == before.ct_idx
    assert after.wli == before.wli
