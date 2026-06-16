from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from rune_decrypter_prime.data.liber_primus.lp_adapter import LPSolverPayload
    from rune_decrypter_prime.data.liber_primus.lp_data import LPSection
    from rune_decrypter_prime.data.liber_primus.lp_registry import LPFragmentLocator, LPPageRef, LPPartitionEntry
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


def load_lp_master_transcript(*, attach_catalogue: bool = True) -> "LPTranscript":
    """Return the parsed master LP transcript."""
    from rune_decrypter_prime.data.liber_primus.lp_master import load_master_transcript

    return load_master_transcript(attach_catalogue=attach_catalogue)


def load_lp_master_section(
    section_id: int,
    *,
    split: str = "page",
) -> tuple[list[int], list[list[int]]]:
    """Return (ct_idx, wli) extracted from the master transcript for a section."""
    from rune_decrypter_prime.data.liber_primus.lp_master import (
        extract_section_ct_wli_by_id,
        load_master_transcript,
    )

    doc = load_master_transcript(attach_catalogue=True)
    return extract_section_ct_wli_by_id(doc, section_id=section_id, split=split)


def load_lp_payload_from_label(label: str) -> "LPSolverPayload":
    """Return deterministic solver payload for a verified LP source label."""
    from rune_decrypter_prime.data.liber_primus.lp_source_catalogue import payload_from_label

    return payload_from_label(label)


def load_lp_payload_from_locator(
    locator: "LPFragmentLocator",
    *,
    line_mode: "LPLineReadMode | None" = None,
    selector: "LPLineRuneSelector | None" = None,
    spiral_route: "LPSpiralRoute | None" = None,
) -> "LPSolverPayload":
    """Return deterministic solver payload for a typed LP locator."""
    from rune_decrypter_prime.data.liber_primus.lp_adapter import payload_from_locator
    from rune_decrypter_prime.data.liber_primus.lp_master import load_master_transcript
    from rune_decrypter_prime.data.liber_primus.lp_routes import LPLineRuneSelector

    effective_selector = selector or LPLineRuneSelector.ALL
    doc = load_master_transcript(attach_catalogue=True)
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
    from rune_decrypter_prime.data.liber_primus.lp_adapter import payload_from_partition_entry
    from rune_decrypter_prime.data.liber_primus.lp_master import load_master_transcript

    doc = load_master_transcript(attach_catalogue=True)
    return payload_from_partition_entry(doc, entry, intersect_page_ref=intersect_page_ref)
