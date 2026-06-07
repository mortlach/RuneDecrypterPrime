from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

O4_RUNTIME_ASSET_ID = "phaseB_ngram_hamming_order4_fwd_nose_fast_runtime_index_v1"
RUNTIME_FORMAT = "grouped_npz_by_length_and_word_shape"


def validate_o4_runtime_manifest(manifest: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    if manifest.get("asset_id") != O4_RUNTIME_ASSET_ID:
        failures.append("unexpected O4 asset_id")
    if manifest.get("runtime_format") != RUNTIME_FORMAT:
        failures.append("unexpected runtime_format")
    if list(manifest.get("orders", [])) != [4]:
        failures.append("orders must be [4]")
    if list(manifest.get("directions", [])) != ["fwd"]:
        failures.append("directions must be ['fwd']")
    if "strict" not in set(manifest.get("cuts", [])):
        failures.append("strict cut missing")
    if manifest.get("source_compact_validation_status") != "pass":
        failures.append("source compact validation must pass")
    for field in ("production_scorer_change", "sample_asset_used", "old_phrase_index_v1_used", "full_raw_shards_used_directly_as_runtime"):
        if manifest.get(field) is not False:
            failures.append(f"{field} must be false")
    return failures


def load_and_validate_o4_runtime_manifest(path: Path) -> Mapping[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    failures = validate_o4_runtime_manifest(manifest)
    if failures:
        raise ValueError("O4 runtime manifest failed authority checks: " + "; ".join(failures))
    return manifest


def selected_o4_strict_fwd_files(manifest: Mapping[str, Any], *, min_phrase_len: int = 10) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in manifest.get("files", []):
        if str(row.get("direction")) != "fwd":
            continue
        if int(row.get("ngram_order", -1)) != 4:
            continue
        if str(row.get("dictionary_cut")) != "strict":
            continue
        if int(row.get("phrase_token_length", -1)) < int(min_phrase_len):
            continue
        rows.append(dict(row))
    if not rows:
        raise ValueError("no strict FWD O4 runtime files selected")
    return rows
