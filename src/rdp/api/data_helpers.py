from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from rune_decrypter_prime.data.liber_primus.lp_adapter import LPSolverPayload
    from rune_decrypter_prime.data.liber_primus.lp_data import LPSection
    from rune_decrypter_prime.data.liber_primus.lp_registry import (
        LPFragmentLocator,
        LPPageRef,
        LPPartitionEntry,
    )
    from rune_decrypter_prime.data.liber_primus.lp_routes import (
        LPLineReadMode,
        LPLineRuneSelector,
        LPSpiralRoute,
    )
    from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript


def load_lp_section(
    section_id: int,
    *,
    split: str = "page",
) -> tuple[list[int], list[list[int]]]:
    """Return (ct_idx, wli) for a Liber Primus section."""
    from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA

    section = LP_DATA.get_section(section_id, split=split)
    ct_idx = list(section.ct_idx)
    wli = [list(pair) for pair in section.wli]
    return ct_idx, wli


def get_lp_section(section_id: int, *, split: str = "page") -> "LPSection":
    """Return the full LPSection record (words, meta, ct, wli)."""
    from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA

    return LP_DATA.get_section(section_id, split=split)


def load_lp_section_inputs(
    section_id: int,
    *,
    split: str = "page",
) -> dict[str, Sequence[Sequence[int]] | Sequence[int]]:
    """Return kwargs payload for run(): {'text': ct_idx, 'wli_data': wli}."""
    ct_idx, wli = load_lp_section(section_id, split=split)
    return {"text": ct_idx, "wli_data": wli}


def load_lp_main_transcript(*, attach_catalogue: bool = True) -> "LPTranscript":
    """Return the parsed main LP transcript."""
    from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript

    return load_main_transcript(attach_catalogue=attach_catalogue)


def load_lp_main_section(
    section_id: int,
    *,
    split: str = "page",
) -> tuple[list[int], list[list[int]]]:
    """Return (ct_idx, wli) extracted from the main transcript for a section."""
    from rune_decrypter_prime.data.liber_primus.lp_main import (
        extract_section_ct_wli_by_id,
        load_main_transcript,
    )

    doc = load_main_transcript(attach_catalogue=True)
    return extract_section_ct_wli_by_id(doc, section_id=section_id, split=split)


def load_lp_payload_from_label(label: str) -> "LPSolverPayload":
    """Return deterministic solver payload for a verified LP source label."""
    from rune_decrypter_prime.data.liber_primus.lp_source_catalogue import (
        payload_from_label,
    )

    return payload_from_label(label)


def load_lp_payload_from_main_pages(
    start_page: int,
    end_page: int | None = None,
) -> "LPSolverPayload":
    """Return deterministic solver payload for complete main transcript pages.

    Page numbers are zero-based main transcript page ids. This is the direct
    helper behind solved-source page-span retrieval.
    """
    from rune_decrypter_prime.data.liber_primus.lp_adapter import LPSolverPayload
    from rune_decrypter_prime.data.liber_primus.lp_main import (
        load_main_transcript,
        page_view_from_ref,
    )
    from rune_decrypter_prime.data.liber_primus.lp_registry import LPPageRef

    if not isinstance(start_page, int) or isinstance(start_page, bool):
        raise TypeError("start_page must be an integer")
    if end_page is None:
        end_page = start_page
    elif not isinstance(end_page, int) or isinstance(end_page, bool):
        raise TypeError("end_page must be an integer or None")
    if start_page < 0:
        raise ValueError("start_page must be >= 0")
    if end_page < start_page:
        raise ValueError("end_page must be >= start_page")

    doc = load_main_transcript(attach_catalogue=True)
    start = page_view_from_ref(doc, LPPageRef.transcript_page(start_page))
    end = page_view_from_ref(doc, LPPageRef.transcript_page(end_page))
    span = doc.glyph_span(start.rec.g_start, end.rec.g_end - start.rec.g_start)
    ct_idx, wli = span.ct_wli()
    metadata = {
        "source_kind": "liber_primus.main_pages",
        "main_page_start": start_page,
        "main_page_end": end_page,
        "bound_book_start": start_page + 1,
        "bound_book_end": end_page + 1,
        "boundary_granularity": "full_main_pages",
    }
    return LPSolverPayload(ct_idx=ct_idx, wli=wli, metadata=metadata)


def load_lp_payload_from_locator(
    locator: "LPFragmentLocator",
    *,
    line_mode: "LPLineReadMode | None" = None,
    selector: "LPLineRuneSelector | None" = None,
    spiral_route: "LPSpiralRoute | None" = None,
) -> "LPSolverPayload":
    """Return deterministic solver payload for a typed LP locator."""
    from rune_decrypter_prime.data.liber_primus.lp_adapter import payload_from_locator
    from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript
    from rune_decrypter_prime.data.liber_primus.lp_routes import LPLineRuneSelector

    effective_selector = selector or LPLineRuneSelector.ALL
    doc = load_main_transcript(attach_catalogue=True)
    return payload_from_locator(
        doc,
        locator,
        line_mode=line_mode,
        selector=effective_selector,
        spiral_route=spiral_route,
    )


def load_lp_payload_from_partition_entry(
    entry: "LPPartitionEntry",
    *,
    intersect_page_ref: "LPPageRef | None" = None,
) -> "LPSolverPayload":
    """Return deterministic solver payload for a typed LP partition entry."""
    from rune_decrypter_prime.data.liber_primus.lp_adapter import (
        payload_from_partition_entry,
    )
    from rune_decrypter_prime.data.liber_primus.lp_main import load_main_transcript

    doc = load_main_transcript(attach_catalogue=True)
    return payload_from_partition_entry(
        doc, entry, intersect_page_ref=intersect_page_ref
    )
