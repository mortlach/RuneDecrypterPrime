from __future__ import annotations
from rdp import api
import rdp.api.data_helpers
from importlib import util
from pathlib import Path
from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA
from rune_decrypter_prime.data.liber_primus.lp_registry import LPFragmentLocator, LPPageRef, build_red_rune_17_partition
from rune_decrypter_prime.data.liber_primus.lp_routes import LPLineReadMode, LPLineRuneSelector, read_lines
from rune_decrypter_prime.data.liber_primus.lp_main import CANON_PAGE_COUNT, RuneGlyphIndex, extract_locator_ct_wli, extract_partition_entry_ct_wli, extract_section_ct_wli, extract_section_ct_wli_by_id, glyph_span_from_partition_entry, load_main_transcript, match_lp_section, page_view_from_ref, resolve_typed_page_ref, route_locator_lines_text

def _canon_num(value: object) -> int | None:
    if not value:
        return None
    stem = str(value).split('.', 1)[0]
    return int(stem) if stem.isdigit() else None

def _load_old_5455(path: Path) -> tuple[list[int], list[list[int]]]:
    spec = util.spec_from_file_location('old_5455', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Unable to load old data from {path}')
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return (list(getattr(module, 'CT_5455')), list(getattr(module, 'WLI_5455')))

def test_main_transcript_canon_mapping():
    doc = load_main_transcript(attach_catalogue=True)
    offset = len(doc.pages) - CANON_PAGE_COUNT
    assert doc.page_id_by_canon('0.jpg') == offset
    assert doc.page_id_by_canon('57.jpg') == len(doc.pages) - 1
    assert doc.page(offset).canon_name == '0.jpg'

def test_lp_sections_match_transcript_pages_and_ct():
    doc = load_main_transcript(attach_catalogue=True)
    rune_index = RuneGlyphIndex.from_doc(doc)
    for section_id in LP_DATA.list_sections(split='page'):
        section = LP_DATA.get_section(section_id, split='page')
        match = match_lp_section(doc, section, rune_index=rune_index)
        start_meta = _canon_num(section.meta.get('page_number_start'))
        end_meta = _canon_num(section.meta.get('page_number_end'))
        assert match.canon_start == start_meta
        assert match.canon_end == end_meta
        ct_idx, wli = extract_section_ct_wli(doc, section, rune_index=rune_index)
        assert ct_idx == list(section.ct_idx)
        assert len(wli) == len(ct_idx)

def test_pages_54_55_match_old_5455():
    root = Path(__file__).resolve().parents[2]
    old_path = root / 'src' / 'rune_decrypter_prime' / 'data' / 'liber_primus' / 'old' / '5455.py'
    old_ct, old_wli = _load_old_5455(old_path)
    doc = load_main_transcript(attach_catalogue=True)
    p54 = doc.page_by_canon('54.jpg')
    p55 = doc.page_by_canon('55.jpg')
    span = doc.glyph_span(p54.rec.g_start, p55.rec.g_end - p54.rec.g_start)
    ct_idx, wli = span.ct_wli()
    assert ct_idx == old_ct
    assert wli == old_wli

def test_pages_54_55_span_matches_master_section_and_crosses_boundary():
    doc = load_main_transcript(attach_catalogue=True)
    p54 = doc.page_by_canon('54.jpg')
    p55 = doc.page_by_canon('55.jpg')
    boundary = p55.rec.g_start
    assert doc._glyph_to_word[boundary - 1] == doc._glyph_to_word[boundary]
    span = doc.glyph_span(p54.rec.g_start, p55.rec.g_end - p54.rec.g_start)
    ct_span, wli_span = span.ct_wli()
    ct_api, wli_api = rdp.api.data_helpers.load_lp_main_section(13, split='page')
    assert len(ct_api) == 308
    assert ct_api == ct_span
    assert wli_api == wli_span

def test_load_lp_main_section_api_matches_direct_extract():
    doc = load_main_transcript(attach_catalogue=True)
    ct_direct, wli_direct = extract_section_ct_wli_by_id(doc, section_id=13, split='page')
    ct_api, wli_api = rdp.api.data_helpers.load_lp_main_section(13, split='page')
    ct_data, wli_data = rdp.api.data_helpers.load_lp_section(13, split='page')
    assert ct_api == ct_direct
    assert wli_api == wli_direct
    assert ct_api == ct_data
    assert wli_api == wli_data

def test_typed_page_ref_parity_matches_canon_lookup():
    doc = load_main_transcript(attach_catalogue=True)
    page_id_typed = resolve_typed_page_ref(doc, LPPageRef.canon_page(54))
    page_id_legacy = doc.page_id_by_canon('54.jpg')
    assert page_id_typed == page_id_legacy
    assert page_view_from_ref(doc, LPPageRef.canon_page(54)).page_id == page_id_legacy

def test_typed_locator_line_slice_matches_direct_span_ct_wli():
    doc = load_main_transcript(attach_catalogue=True)
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54), line=0, line_end=1)
    ct_typed, wli_typed = extract_locator_ct_wli(doc, locator)
    page = doc.page_by_canon('54.jpg')
    lines = page.lines()
    span = doc.glyph_span(lines[0].rec.g_start, lines[1].rec.g_end - lines[0].rec.g_start)
    ct_legacy, wli_legacy = span.ct_wli()
    assert ct_typed == ct_legacy
    assert wli_typed == wli_legacy

def test_partition_entry_span_matches_direct_page_range():
    doc = load_main_transcript(attach_catalogue=True)
    entry = build_red_rune_17_partition()[0]
    ct_typed, wli_typed = extract_partition_entry_ct_wli(doc, entry)
    p0 = doc.page_by_canon('0.jpg')
    p2 = doc.page_by_canon('2.jpg')
    direct = doc.glyph_span(p0.rec.g_start, p2.rec.g_end - p0.rec.g_start)
    ct_direct, wli_direct = direct.ct_wli()
    assert ct_typed == ct_direct
    assert wli_typed == wli_direct
    assert glyph_span_from_partition_entry(doc, entry).text() == direct.text()

def test_typed_routed_line_extraction_matches_direct_route():
    doc = load_main_transcript(attach_catalogue=True)
    locator = LPFragmentLocator(page_ref=LPPageRef.canon_page(54), line=0, line_end=2)
    routed_typed = route_locator_lines_text(doc, locator, mode=LPLineReadMode.BOUSTROPHEDON, selector=LPLineRuneSelector.FIRST_ONLY)
    page = doc.page_by_canon('54.jpg')
    lines = [line.text(sep='') for line in page.lines()[0:3]]
    routed_direct = read_lines(lines, mode=LPLineReadMode.BOUSTROPHEDON, selector=LPLineRuneSelector.FIRST_ONLY)
    assert routed_typed == routed_direct
