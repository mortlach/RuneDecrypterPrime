from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (  # noqa: E402
    validate_phaseB_ngram_hamming_fast_runtime_lookup_index_v1 as validator,
)


RUN_LABEL = "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_validation_v1"
RUNTIME_INDEX_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_v1"
)
RUNTIME_MANIFEST_REL = f"{RUNTIME_INDEX_DIR_REL}/runtime_index_manifest.json"
COMPACT_VALIDATION_MANIFEST_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_fwd_nose_compact_phrase_lookup_asset_validation_v1/validation_manifest.json"
)
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_lookup_index_validation_v1"
)
EXPECTED_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_index_v1"
EXPECTED_COMPACT_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_compact_lookup_v1"
EXPECTED_ORDERS = [4]
EXPECTED_CUTS = ["normal", "strict"]
EXPECTED_DIRECTIONS = ["fwd"]
EXPECTED_MAX_RUNTIME_ROWS_PER_FILE = 1_000_000


def configure_validator() -> None:
    validator.RUN_LABEL = RUN_LABEL
    validator.RUNTIME_INDEX_DIR_REL = RUNTIME_INDEX_DIR_REL
    validator.RUNTIME_MANIFEST_REL = RUNTIME_MANIFEST_REL
    validator.COMPACT_VALIDATION_MANIFEST_REL = COMPACT_VALIDATION_MANIFEST_REL
    validator.OUTPUT_DIR_REL = OUTPUT_DIR_REL
    validator.EXPECTED_ASSET_ID = EXPECTED_ASSET_ID
    validator.EXPECTED_COMPACT_ASSET_ID = EXPECTED_COMPACT_ASSET_ID
    validator.EXPECTED_ORDERS = EXPECTED_ORDERS
    validator.EXPECTED_CUTS = EXPECTED_CUTS
    validator.EXPECTED_DIRECTIONS = EXPECTED_DIRECTIONS
    validator.EXPECTED_MAX_RUNTIME_ROWS_PER_FILE = EXPECTED_MAX_RUNTIME_ROWS_PER_FILE


def main() -> None:
    configure_validator()
    validator.main()


if __name__ == "__main__":
    main()
