from __future__ import annotations

import json

from rune_decrypter_prime.scoring.ngram_hamming.fast_backend import fast_ngram_hamming_available
from tools.benchmarks.periodic_sub_trans.no_wli.analysis import (
    run_phaseB_ngram_hamming_fast_real_index_smoke_v1 as smoke,
)


def test_fast_real_index_smoke_requires_cpp_backend() -> None:
    assert fast_ngram_hamming_available()


def test_fast_real_index_smoke_matches_python_reference() -> None:
    manifest = smoke.run_smoke()

    assert manifest["status"] == "pass"
    assert manifest["backend_impl"] == "cpp_fast"
    assert manifest["reference_backend_impl"] == "python_reference"
    assert manifest["python_fallback_allowed"] is False
    assert manifest["broad_pilot"] is False
    assert manifest["entry_limit"] == smoke.ENTRY_LIMIT
    assert manifest["loaded_entry_count"] <= smoke.ENTRY_LIMIT
    assert manifest["parity_match"] is True
    assert manifest["selected_phrase_control"]["exact_hit_found"] is True
    assert manifest["selected_phrase_control"]["expected_hit_start"] == 1
    assert manifest["selected_phrase_control"]["expected_total_phrase_hd"] == 0
    assert all(value == 0 for value in manifest["selected_phrase_control"]["expected_word_hds"])
    assert len(manifest["positive_control"]["fast"]["phrase_hits"]) > 0
    assert manifest["elapsed_seconds"] <= smoke.MAX_WALLCLOCK_SECONDS


def test_fast_real_index_smoke_manifest_is_json_serialisable() -> None:
    manifest = smoke.run_smoke()

    json.dumps(manifest, sort_keys=True)
