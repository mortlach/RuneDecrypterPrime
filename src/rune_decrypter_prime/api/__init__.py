# rune_decrypter_prime/api/__init__.py

from .run import RunAPI, run
from .run_result import RunResult
from .specs import CipherSpec, SolverSpec, KeySpec
from .run_spec import RawTextInput, NormalizedInput, SourceInputRef, RunSpec
from .solver_report import SolverReport
from .display import (
    DISPLAY_SUMMARY_RELPATH,
    DISPLAY_SUMMARY_SCHEMA,
    RdpDisplayOptions,
    RdpDisplaySummary,
    build_rdp_summary,
    format_rdp_summary,
    print_rdp_summary,
    write_rdp_summary_json,
)
from .printer import (
    RdpPrintFormat,
    print_rdp_result,
    render_rdp_summary,
    write_rdp_summary_artifact,
)
from .wrappers.by_name import by_name, cipher_instance
from .normalize import (
    Direction,
    normalize_ciphertext,
    normalize_encoding_dir,
    apply_permutation,
    invert_permutation,
)
from .maps_api import define_map, define_cipher, preview
from rune_decrypter_prime.core.config import InterruptorConfig
from .data_helpers import (
    get_lp_section,
    load_lp_payload_from_label,
    load_lp_payload_from_locator,
    load_lp_payload_from_main_pages,
    load_lp_payload_from_partition_entry,
    load_lp_main_section,
    load_lp_main_transcript,
    load_lp_section,
    load_lp_section_inputs,
)


__all__ = [
    "RunAPI",
    "run",
    "RunResult",
    "CipherSpec",
    "SolverSpec",
    "KeySpec",
    "RawTextInput",
    "NormalizedInput",
    "SourceInputRef",
    "RunSpec",
    "SolverReport",
    "DISPLAY_SUMMARY_RELPATH",
    "DISPLAY_SUMMARY_SCHEMA",
    "RdpDisplayOptions",
    "RdpDisplaySummary",
    "build_rdp_summary",
    "format_rdp_summary",
    "print_rdp_summary",
    "write_rdp_summary_json",
    "RdpPrintFormat",
    "print_rdp_result",
    "render_rdp_summary",
    "write_rdp_summary_artifact",
    "Direction",
    "normalize_ciphertext",
    "normalize_encoding_dir",
    "apply_permutation",
    "invert_permutation",
    "define_map",
    "define_cipher",
    "preview",
    "InterruptorConfig",
    "get_lp_section",
    "load_lp_payload_from_label",
    "load_lp_payload_from_locator",
    "load_lp_payload_from_main_pages",
    "load_lp_payload_from_partition_entry",
    "load_lp_main_section",
    "load_lp_main_transcript",
    "load_lp_section",
    "load_lp_section_inputs",
    "by_name",
    "cipher_instance",
]
