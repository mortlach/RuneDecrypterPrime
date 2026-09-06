"""Typed Liber Primus data-access namespace."""

from rdp.api.run_spec import SourceReferenceInput as _SourceReferenceInput

from rdp.api.data_helpers import (
    get_lp_section as get_section,
    load_lp_main_section as load_main_section_indices,
    load_lp_main_transcript as load_main_transcript,
    load_lp_payload_from_label as payload_from_label,
    load_lp_payload_from_locator as payload_from_locator,
    load_lp_payload_from_main_pages as payload_from_main_pages,
    load_lp_payload_from_partition_entry as payload_from_partition_entry,
    load_lp_section as load_section_indices,
    load_lp_section_inputs as load_section_inputs,
)
from rdp.data.liber_primus.lp_adapter import LPSolverPayload as SolverPayload
from rdp.data.liber_primus.lp_data import LPSection as Section
from rdp.data.liber_primus.lp_registry import (
    LPFragmentLocator as FragmentLocator,
    LPPageRef as PageReference,
    LPPartitionEntry as PartitionEntry,
)
from rdp.data.liber_primus.lp_routes import (
    LPLineReadMode as LineReadMode,
    LPLineRuneSelector as LineRuneSelector,
    LPSpiralRoute as SpiralRoute,
)
from rdp.data.liber_primus.lp_transcript import LPTranscript as Transcript


def source(label: str) -> _SourceReferenceInput:
    """Describe a named LP source for a run, preserving its label and asset version.

    Labels and aliases use the existing catalogue. Rune data is resolved by the
    normal run-input path, which rejects a mismatched transcript version.
    """
    from rdp.data.liber_primus.lp_main import main_transcript_asset_identity
    from rdp.data.liber_primus.lp_source_catalogue import resolve_source_label

    entry = resolve_source_label(label)
    identity = main_transcript_asset_identity()
    return _SourceReferenceInput(
        source_kind="liber_primus.label",
        asset_id=identity["asset_id"],
        asset_version=identity["asset_version"],
        reference={"label": entry.source_label},
    )


__all__ = [
    "source",
    "Section",
    "SolverPayload",
    "FragmentLocator",
    "LineReadMode",
    "LineRuneSelector",
    "SpiralRoute",
    "PartitionEntry",
    "PageReference",
    "Transcript",
    "get_section",
    "payload_from_label",
    "payload_from_locator",
    "payload_from_main_pages",
    "payload_from_partition_entry",
    "load_main_section_indices",
    "load_main_transcript",
    "load_section_indices",
    "load_section_inputs",
]
