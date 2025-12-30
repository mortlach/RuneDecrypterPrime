from __future__ import annotations

from importlib import util
from pathlib import Path

from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA
from rune_decrypter_prime.data.liber_primus.lp_master import (
    CANON_PAGE_COUNT,
    RuneGlyphIndex,
    extract_section_ct_wli,
    load_master_transcript,
    match_lp_section,
)


def _canon_num(value: object) -> int | None:
    if not value:
        return None
    stem = str(value).split(".", 1)[0]
    return int(stem) if stem.isdigit() else None


def _load_old_5455(path: Path) -> tuple[list[int], list[list[int]]]:
    spec = util.spec_from_file_location("old_5455", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load old data from {path}")
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return list(getattr(module, "CT_5455")), list(getattr(module, "WLI_5455"))


def test_master_transcript_canon_mapping():
    doc = load_master_transcript(attach_catalogue=True)
    offset = len(doc.pages) - CANON_PAGE_COUNT
    assert doc.page_id_by_canon("0.jpg") == offset
    assert doc.page_id_by_canon("57.jpg") == len(doc.pages) - 1
    assert doc.page(offset).canon_name == "0.jpg"


def test_lp_sections_match_transcript_pages_and_ct():
    doc = load_master_transcript(attach_catalogue=True)
    rune_index = RuneGlyphIndex.from_doc(doc)

    for section_id in LP_DATA.list_sections(split="page"):
        section = LP_DATA.get_section(section_id, split="page")
        match = match_lp_section(doc, section, rune_index=rune_index)

        start_meta = _canon_num(section.meta.get("page_number_start"))
        end_meta = _canon_num(section.meta.get("page_number_end"))

        assert match.canon_start == start_meta
        assert match.canon_end == end_meta

        ct_idx, wli = extract_section_ct_wli(doc, section, rune_index=rune_index)
        assert ct_idx == list(section.ct_idx)
        assert len(wli) == len(ct_idx)


def test_pages_54_55_match_old_5455():
    root = Path(__file__).resolve().parents[2]
    old_path = root / "src" / "rune_decrypter_prime" / "data" / "liber_primus" / "old" / "5455.py"
    old_ct, old_wli = _load_old_5455(old_path)

    doc = load_master_transcript(attach_catalogue=True)
    p54 = doc.page_by_canon("54.jpg")
    p55 = doc.page_by_canon("55.jpg")
    span = doc.glyph_span(p54.rec.g_start, p55.rec.g_end - p54.rec.g_start)
    ct_idx, wli = span.ct_wli()

    assert ct_idx == old_ct
    assert wli == old_wli
