from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
for path in (REPO_ROOT, REPO_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 as full80,
)
from tools.benchmarks.periodic_sub_trans.no_wli.analysis.run_phaseB_failed_decryption_n3c_full80_query_evidence_v1 import (
    N3CRunSpec,
)


def run_strict_bucket(
    length_bucket: str,
    phase: str,
    max_runtime_seconds: float,
    *,
    candidate_scope: str = "selected_80_retained_candidates_v1",
    candidate_selection_mode: str = "initial_diverse_80",
    candidate_remaining_offset: int = 0,
) -> dict[str, object]:
    full80.RUN_SPEC = N3CRunSpec(
        run_family="n3c_strict_full80",
        schema_version="n3c_run_spec_v1",
        direction="fwd",
        ngram_order=3,
        dictionary_cut="strict",
        minimum_phrase_length=8,
        length_bucket=length_bucket,
        candidate_scope=candidate_scope,
        query_contract="total_hd_le_2_max_word_hd_le_1_word_structured",
    )
    full80.PHASE = phase
    full80.OUTPUT_DIR = (
        full80.REPO_ROOT / "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis" / full80.PHASE
    )
    full80.MAX_TOTAL_RUNTIME_SECONDS = max_runtime_seconds
    full80.CANDIDATE_SELECTION_MODE = candidate_selection_mode
    full80.CANDIDATE_REMAINING_OFFSET = candidate_remaining_offset
    full80.CANDIDATE_SELECTION_LABEL = candidate_scope
    full80.QUERY_SCOPE_LABEL = f"n3c_strict_full80_complete_{length_bucket}_bucket_for_selected_80_candidates"
    full80.QUERY_IS_FULL_N3C_FOR_SELECTED_80 = False
    return full80.run_full80()
