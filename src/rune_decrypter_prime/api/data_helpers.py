from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from rune_decrypter_prime.data.liber_primus.lp_data import LPSection
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
    from rune_decrypter_prime.data.liber_primus.lp_data import LP_DATA

    section = LP_DATA.get_section(section_id, split=split)
    ct_idx = list(section.ct_idx)
    wli = [list(pair) for pair in section.wli]
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
