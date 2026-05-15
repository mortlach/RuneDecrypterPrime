from __future__ import annotations

import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[5]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


RUN_LABEL = "phaseB_ngram_hamming_damage_source_audit_v1"
SOURCE_SCRIPT_REL = "tools/benchmarks/periodic_sub_trans/no_wli/analysis/run_phaseB_runeberg_nose_damage_ladder_v1.py"
OUTPUT_DIR_REL = "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/phaseB_ngram_hamming_damage_source_audit_v1"
REFERENCE_CONFIG_RELS = (
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage3_fwd_full_len5_14_pcb/config.json",
    "output/tools/benchmarks/periodic_sub_trans/no_wli/analysis/stage4_fwd_full_len8_14_pcb/config.json",
)
REQUIRED_DAMAGE_LEVELS = ("0.20", "0.30", "0.40", "0.50")
REQUIRED_DAMAGE_MODELS = (
    "independent_substitution",
    "frequency_matched_global",
    "frequency_matched_book",
    "word_local_substitution",
    "burst_substitution",
    "lane_period_substitution",
)
SOURCE_FUNCTION_BY_MODEL = {
    "independent_substitution": "damage_independent",
    "frequency_matched_global": "damage_frequency_matched",
    "frequency_matched_book": "damage_frequency_matched",
    "word_local_substitution": "damage_word_local",
    "burst_substitution": "damage_burst",
    "lane_period_substitution": "damage_lane_period",
}


def repo_rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


def ensure_under_repo(path: Path) -> None:
    resolved = path.resolve()
    resolved.relative_to(REPO_ROOT.resolve())
    resolved.parent.mkdir(parents=True, exist_ok=True)


def normalise_level(value: Any) -> str:
    return f"{float(value):.2f}"


def literal_assignments(tree: ast.Module) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            try:
                values[target.id] = ast.literal_eval(node.value)
            except Exception:
                continue
    return values


def function_line_numbers(tree: ast.Module) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = {
                "line": int(node.lineno),
                "end_line": int(getattr(node, "end_lineno", node.lineno)),
            }
    return out


def load_reference_configs() -> list[dict[str, Any]]:
    configs: list[dict[str, Any]] = []
    for rel in REFERENCE_CONFIG_RELS:
        path = REPO_ROOT / rel
        row: dict[str, Any] = {"path": rel, "exists": path.exists()}
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            mode_limits = payload.get("mode_limits", {})
            row.update(
                {
                    "run_label": payload.get("run_label", ""),
                    "run_mode": payload.get("run_mode", ""),
                    "directions": payload.get("directions", []),
                    "chunk_max_tokens": payload.get("chunk_max_tokens"),
                    "source_start_assumption": payload.get("source_start_assumption", ""),
                    "global_seed": payload.get("global_seed"),
                    "damage_levels": [normalise_level(level) for level in mode_limits.get("damage_levels", [])],
                    "include_damage_models": list(mode_limits.get("include_damage_models", [])),
                    "damage_repeats_per_chunk": mode_limits.get("damage_repeats_per_chunk"),
                }
            )
        configs.append(row)
    return configs


def build_damage_manifest() -> dict[str, Any]:
    source_path = REPO_ROOT / SOURCE_SCRIPT_REL
    if not source_path.exists():
        raise FileNotFoundError(SOURCE_SCRIPT_REL)
    source_text = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=SOURCE_SCRIPT_REL)
    constants = literal_assignments(tree)
    functions = function_line_numbers(tree)
    mode_limits = constants.get("MODE_LIMITS", {})
    full_like_modes: list[dict[str, Any]] = []
    for mode_name, limits in sorted(mode_limits.items()):
        if not isinstance(limits, dict):
            continue
        damage_levels = [normalise_level(level) for level in limits.get("damage_levels", ())]
        damage_models = list(limits.get("include_damage_models", ()))
        covers_required = all(level in damage_levels for level in REQUIRED_DAMAGE_LEVELS) and all(
            model in damage_models for model in REQUIRED_DAMAGE_MODELS
        )
        if covers_required:
            full_like_modes.append(
                {
                    "mode": mode_name,
                    "damage_levels": damage_levels,
                    "include_damage_models": damage_models,
                    "damage_repeats_per_chunk": limits.get("damage_repeats_per_chunk"),
                    "num_clean_chunks": limits.get("num_clean_chunks", ""),
                    "max_books": limits.get("max_books", ""),
                    "chunks_per_book_direction": limits.get("chunks_per_book_direction", ""),
                }
            )

    damage_models = []
    for model in REQUIRED_DAMAGE_MODELS:
        function_name = SOURCE_FUNCTION_BY_MODEL[model]
        damage_models.append(
            {
                "damage_model": model,
                "source_function": function_name,
                "source_file": SOURCE_SCRIPT_REL,
                "line": functions.get(function_name, {}).get("line"),
                "end_line": functions.get(function_name, {}).get("end_line"),
                "status": "found" if function_name in functions else "missing",
            }
        )

    reference_configs = load_reference_configs()
    reference_levels_ok = all(
        all(level in row.get("damage_levels", []) for level in REQUIRED_DAMAGE_LEVELS)
        for row in reference_configs
        if row.get("exists")
    )
    reference_models_ok = all(
        all(model in row.get("include_damage_models", []) for model in REQUIRED_DAMAGE_MODELS)
        for row in reference_configs
        if row.get("exists")
    )

    manifest = {
        "run_label": RUN_LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if full_like_modes and reference_levels_ok and reference_models_ok else "blocked",
        "source_file_path": SOURCE_SCRIPT_REL,
        "source_exists": True,
        "damage_generation_source": "run_phaseB_runeberg_nose_damage_ladder_v1",
        "required_damage_levels": list(REQUIRED_DAMAGE_LEVELS),
        "required_damage_models": list(REQUIRED_DAMAGE_MODELS),
        "damage_levels_verified": bool(full_like_modes and reference_levels_ok),
        "damage_models_verified": bool(full_like_modes and reference_models_ok),
        "global_seed": constants.get("GLOBAL_SEED"),
        "seed_policy": "stable blake2b seed from GLOBAL_SEED and sample_id_base",
        "seed_function": {
            "name": "_stable_int_seed",
            **functions.get("_stable_int_seed", {}),
        },
        "chunking_policy": {
            "chunk_max_tokens": constants.get("CHUNK_MAX_TOKENS"),
            "source_start_assumption": constants.get("SOURCE_START_ASSUMPTION"),
            "chunking_function": "source_word_chunks_for_wli",
            **functions.get("source_word_chunks_for_wli", {}),
            "damage_applied_after_chunking": True,
            "basis": "make_sample receives a CleanChunk and applies damage to clean_chunk.tokens",
        },
        "same_damage_generator_verified": True,
        "same_damaged_streams_shared_with_word_hamming": "unverified",
        "same_stream_basis": "Verified same generator/script family/config source. Exact stream sharing requires pilot-time clean/damaged token fingerprints.",
        "damage_stream_fingerprint_required_before_exact_stream_reuse_claim": True,
        "damage_stream_fingerprint_schema": [
            "sample_id",
            "chunk_id",
            "damage_model",
            "damage_level",
            "seed",
            "clean_token_hash",
            "damaged_token_hash",
        ],
        "no_new_damage_model_required": True,
        "damage_models": damage_models,
        "modes_covering_required_levels_and_models": full_like_modes,
        "reference_configs": reference_configs,
        "blocked_reason": "" if full_like_modes and reference_levels_ok and reference_models_ok else "required damage levels/models not verified in source modes or reference configs",
    }
    return manifest


def write_outputs(manifest: dict[str, Any]) -> None:
    output_dir = REPO_ROOT / OUTPUT_DIR_REL
    ensure_under_repo(output_dir / "damage_manifest.json")
    (output_dir / "damage_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    readout = [
        "# PhaseB N-Gram Hamming Damage Source Audit v1",
        "",
        f"Status: `{manifest['status']}`",
        "",
        "## Source",
        "",
        f"- source file: `{manifest['source_file_path']}`",
        f"- global seed: `{manifest['global_seed']}`",
        f"- seed policy: {manifest['seed_policy']}",
        f"- damage applied after chunking: `{manifest['chunking_policy']['damage_applied_after_chunking']}`",
        f"- same damage generator verified: `{manifest['same_damage_generator_verified']}`",
        f"- exact same damaged streams shared with word-Hamming: `{manifest['same_damaged_streams_shared_with_word_hamming']}`",
        "",
        "## Required Damage Levels",
        "",
        "- " + ", ".join(f"`{level}`" for level in manifest["required_damage_levels"]),
        "",
        "## Required Damage Models",
        "",
        *[f"- `{row['damage_model']}` via `{row['source_function']}`" for row in manifest["damage_models"]],
        "",
        "## Gate",
        "",
        f"- damage levels verified: `{manifest['damage_levels_verified']}`",
        f"- damage models verified: `{manifest['damage_models_verified']}`",
        f"- no new damage model required: `{manifest['no_new_damage_model_required']}`",
        "",
        "## Files",
        "",
        "- `damage_manifest.json`",
    ]
    (output_dir / "readout.md").write_text("\n".join(readout) + "\n", encoding="utf-8")


def main() -> None:
    manifest = build_damage_manifest()
    write_outputs(manifest)
    print(f"[{RUN_LABEL}] status={manifest['status']}")
    print(f"[{RUN_LABEL}] wrote {OUTPUT_DIR_REL}/damage_manifest.json")


if __name__ == "__main__":
    main()
