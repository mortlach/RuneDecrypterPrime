from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
SRC_DIR = REPO_ROOT / "src"
for path in (REPO_ROOT, SRC_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


RUN_LABEL = "phaseB_ngram_hamming_bridge_lane2_input_contract_v1"
OUTPUT_DIR_REL = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/"
    "phaseB_ngram_hamming_bridge_lane2_input_contract_v1"
)
NO_REAL_CANDIDATE_SCAN = True
NO_PRODUCTION_SCORER_CHANGES = True
ALLOWED_CANDIDATE_ROLES = frozenset({"known_better", "known_worse", "baseline", "challenger", "null"})
RUNE_TOKEN_MIN = 0
RUNE_TOKEN_MAX = 28
SHA256_HEX_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
CANDIDATE_CHUNK_REQUIRED_FIELDS = frozenset(
    {
        "candidate_id",
        "chunk_id",
        "candidate_role",
        "damage_level",
        "rune_token_ids",
        "token_count",
        "source_candidate_path",
        "source_candidate_sha256",
        "chunk_start_offset",
        "chunk_end_offset",
    }
)
PAIR_INPUT_REQUIRED_FIELDS = frozenset(
    {
        "pair_id",
        "expected_better_id",
        "expected_worse_id",
        "pair_source",
        "baseline_winner",
        "comparison_scope",
    }
)
RUN_CONFIG_REQUIRED_FIELDS = frozenset(
    {
        "run_id",
        "profile_manifest_path",
        "profile_manifest_hash",
        "phrase_index_path",
        "candidate_chunk_path",
        "pair_input_path",
        "cluster_scopes",
        "no_production_scorer_changes",
        "readiness_manifest_path",
    }
)


def repo_rel(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()


def ensure_under_repo(path: Path) -> None:
    path.resolve().relative_to(REPO_ROOT.resolve())
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    ensure_under_repo(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def missing_fields(row: dict[str, Any], required_fields: frozenset[str]) -> tuple[str, ...]:
    return tuple(sorted(required_fields - set(row)))


def validate_candidate_chunk_row(row: dict[str, Any]) -> list[str]:
    errors = [f"missing field {field}" for field in missing_fields(row, CANDIDATE_CHUNK_REQUIRED_FIELDS)]
    if errors:
        return errors
    if row["candidate_role"] not in ALLOWED_CANDIDATE_ROLES:
        errors.append("candidate_role must be one of known_better, known_worse, baseline, challenger, or null")
    if not isinstance(row["rune_token_ids"], list) or not row["rune_token_ids"]:
        errors.append("rune_token_ids must be a non-empty list")
    elif any(isinstance(token, bool) or not isinstance(token, int) for token in row["rune_token_ids"]):
        errors.append("rune_token_ids must contain only integers")
    elif any(token < RUNE_TOKEN_MIN or token > RUNE_TOKEN_MAX for token in row["rune_token_ids"]):
        errors.append("rune_token_ids must be rune token ids in range 0..28")
    if row.get("token_count") != len(row.get("rune_token_ids", [])):
        errors.append("token_count must equal len(rune_token_ids)")
    chunk_start = row.get("chunk_start_offset")
    chunk_end = row.get("chunk_end_offset")
    if (
        isinstance(chunk_start, bool)
        or isinstance(chunk_end, bool)
        or not isinstance(chunk_start, int)
        or not isinstance(chunk_end, int)
    ):
        errors.append("chunk_start_offset and chunk_end_offset must be integers")
    else:
        if chunk_end < chunk_start:
            errors.append("chunk_end_offset must be >= chunk_start_offset")
        if chunk_end - chunk_start != row.get("token_count"):
            errors.append("chunk_end_offset - chunk_start_offset must equal token_count")
    if row["source_candidate_path"] != "synthetic" and not SHA256_HEX_PATTERN.fullmatch(
        str(row["source_candidate_sha256"])
    ):
        errors.append("source_candidate_sha256 must be a 64-character hex digest for real candidate rows")
    return errors


def validate_pair_input_row(row: dict[str, Any]) -> list[str]:
    errors = [f"missing field {field}" for field in missing_fields(row, PAIR_INPUT_REQUIRED_FIELDS)]
    if errors:
        return errors
    if row["expected_better_id"] == row["expected_worse_id"]:
        errors.append("expected_better_id and expected_worse_id must differ")
    return errors


def schema_manifest() -> dict[str, Any]:
    return {
        "candidate_chunk_required_fields": sorted(CANDIDATE_CHUNK_REQUIRED_FIELDS),
        "pair_input_required_fields": sorted(PAIR_INPUT_REQUIRED_FIELDS),
        "run_config_required_fields": sorted(RUN_CONFIG_REQUIRED_FIELDS),
        "candidate_chunk_notes": [
            "rune_token_ids must be integer token ids, not rune_key_hex",
            "rune_token_ids must be in the closed rune token range 0..28",
            "token_count must equal len(rune_token_ids)",
            "chunk_end_offset - chunk_start_offset must equal token_count",
            "candidate_role must be known_better, known_worse, baseline, challenger, or null",
            "source_candidate_sha256 must be a 64-character hex digest for real candidate rows",
        ],
        "pair_input_notes": [
            "pair rows define expected comparison direction only",
            "pair rows must not imply score authority before readiness passes",
        ],
    }


def build_input_contract(output_dir: Path | None = None) -> dict[str, Any]:
    selected_output_dir = output_dir or (REPO_ROOT / OUTPUT_DIR_REL)
    schema = schema_manifest()
    valid_candidate = {
        "candidate_id": "synthetic-better",
        "chunk_id": "chunk-0",
        "candidate_role": "known_better",
        "damage_level": "synthetic",
        "rune_token_ids": [1, 2, 3, 4],
        "token_count": 4,
        "source_candidate_path": "synthetic",
        "source_candidate_sha256": "",
        "chunk_start_offset": 0,
        "chunk_end_offset": 4,
    }
    valid_pair = {
        "pair_id": "synthetic-pair",
        "expected_better_id": "synthetic-better",
        "expected_worse_id": "synthetic-worse",
        "pair_source": "synthetic",
        "baseline_winner": "",
        "comparison_scope": "synthetic_contract_only",
    }
    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass",
        "no_real_candidate_scan": NO_REAL_CANDIDATE_SCAN,
        "no_production_scorer_changes": NO_PRODUCTION_SCORER_CHANGES,
        "candidate_chunk_required_field_count": len(CANDIDATE_CHUNK_REQUIRED_FIELDS),
        "pair_input_required_field_count": len(PAIR_INPUT_REQUIRED_FIELDS),
        "run_config_required_field_count": len(RUN_CONFIG_REQUIRED_FIELDS),
        "synthetic_candidate_validation_errors": validate_candidate_chunk_row(valid_candidate),
        "synthetic_pair_validation_errors": validate_pair_input_row(valid_pair),
    }
    write_json(selected_output_dir / "input_contract_manifest.json", manifest)
    write_json(selected_output_dir / "input_schema_manifest.json", schema)
    write_json(selected_output_dir / "synthetic_candidate_chunk_row.json", valid_candidate)
    write_json(selected_output_dir / "synthetic_pair_input_row.json", valid_pair)
    write_readout(selected_output_dir / "readout.md", manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] no_real_candidate_scan={manifest['no_real_candidate_scan']}")
    return manifest


def write_readout(path: Path, manifest: dict[str, Any]) -> None:
    ensure_under_repo(path)
    lines = [
        "# PhaseB N-Gram Hamming Bridge Lane 2 Input Contract v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        f"- no real candidate scan: `{manifest['no_real_candidate_scan']}`",
        f"- production scorer changes: `{not manifest['no_production_scorer_changes']}`",
        f"- candidate chunk required fields: `{manifest['candidate_chunk_required_field_count']}`",
        f"- pair input required fields: `{manifest['pair_input_required_field_count']}`",
        f"- run config required fields: `{manifest['run_config_required_field_count']}`",
        "",
        "This contract prepares future runner inputs only. It does not read real",
        "candidate data or start a bridge diagnostic scan.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    build_input_contract()


if __name__ == "__main__":
    main()
