from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import numpy as np

REVIEW_PACK_SCHEMA = "rdp.two_period_overlay.review_pack.v1"
LOCAL_VALIDATION_SCHEMA = "rdp.two_period_overlay.local_validation.v1"
REVIEW_PACK_ROOT = Path("output/cipher_development/two_period_overlay/review_packs")
VALIDATION_RECEIPT = Path(
    "output/cipher_development/two_period_overlay/local_validation.json"
)
VALIDATION_ARTIFACT_ROOT = Path(
    "output/cipher_development/two_period_overlay/validation"
)
_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_REFERENCE_KEYS = {
    "expected_key", "expected_plaintext", "ground_truth", "known_key", "known_plaintext",
    "match_ratio", "oracle", "oracle_key", "reference", "reference_evaluation",
    "reference_metrics", "test_key", "truth", "truth_key", "truth_metrics",
}
_REFERENCE_PREFIXES = ("oracle_", "reference_", "truth_")
_COORDINATE_SUPPLY_BENCHMARK_IDS = (
    "alice_308_p05_p13_d04",
    "alice_308_p09_p13_d08",
)

CAMPAIGN_SOURCE_PATHS = (
    Path("cipher_development/two_period_overlay/CAMPAIGN.md"),
    Path("cipher_development/two_period_overlay/config.py"),
    Path("cipher_development/two_period_overlay/benchmark.py"),
    Path("cipher_development/two_period_overlay/keyspace.py"),
    Path("cipher_development/two_period_overlay/search.py"),
    Path("cipher_development/two_period_overlay/coordinate_supply.py"),
    Path("cipher_development/two_period_overlay/diagnostics.py"),
    Path("cipher_development/two_period_overlay/replay.py"),
    Path("cipher_development/two_period_overlay/replay_suite.py"),
    Path("cipher_development/two_period_overlay/review_pack.py"),
    Path("cipher_development/two_period_overlay/run.py"),
)
OPTIONAL_CAMPAIGN_SOURCE_PATHS = (
    Path("cipher_development/two_period_overlay/selection.py"),
    Path("cipher_development/two_period_overlay/candidate_selection.py"),
    Path("cipher_development/two_period_overlay/exploitation.py"),
    Path("cipher_development/two_period_overlay/target_supply.py"),
    Path("cipher_development/two_period_overlay/target_ranking.py"),
    Path("cipher_development/two_period_overlay/scorer_profiles.py"),
    Path("cipher_development/two_period_overlay/multiscale.py"),
    Path("cipher_development/two_period_overlay/pack01.py"),
    Path("cipher_development/two_period_overlay/matched_pilot.py"),
    Path("cipher_development/two_period_overlay/pack02a.py"),
    Path("cipher_development/two_period_overlay/staged_handoff.py"),
    Path("cipher_development/two_period_overlay/pack02b.py"),
    Path("cipher_development/two_period_overlay/experiment_a.py"),
    Path("cipher_development/two_period_overlay/pack03a.py"),
    Path("cipher_development/two_period_overlay/candidate_words.py"),
    Path("cipher_development/two_period_overlay/experiment_b.py"),
    Path("cipher_development/two_period_overlay/pack04.py"),
    Path("cipher_development/two_period_overlay/b100_budget_sensitivity.py"),
    Path("cipher_development/two_period_overlay/pack05.py"),
)
SHARED_SOURCE_PATHS = (
    Path("cipher_development/shared/experiment.py"),
    Path("cipher_development/shared/ledger.py"),
    Path("cipher_development/shared/archive.py"),
    Path("cipher_development/shared/replay.py"),
    Path("cipher_development/shared/replay_binding.py"),
    Path("cipher_development/shared/replay_evidence.py"),
    Path("cipher_development/shared/replay_execution.py"),
    Path("cipher_development/shared/replay_provenance.py"),
)
TEST_SOURCE_PATHS = (
    Path("tests/cipher_development/test_two_period_overlay.py"),
    Path("tests/cipher_development/test_campaign_replay.py"),
    Path("tests/cipher_development/test_two_period_review_pack.py"),
    Path("tests/cipher_development/test_two_period_coordinate_supply.py"),
    Path("tests/cipher_development/test_two_period_selection.py"),
    Path("tests/cipher_development/test_two_period_exploitation.py"),
    Path("tests/cipher_development/test_two_period_target_supply.py"),
    Path("tests/cipher_development/test_two_period_target_ranking.py"),
    Path("tests/cipher_development/test_two_period_multiscale.py"),
    Path("tests/cipher_development/test_two_period_matched_pilot.py"),
    Path("tests/cipher_development/test_two_period_staged_handoff.py"),
    Path("tests/cipher_development/test_two_period_experiment_a.py"),
    Path("tests/cipher_development/test_two_period_experiment_b.py"),
    Path("tests/cipher_development/test_two_period_b100_budget_sensitivity.py"),
)


@dataclass(frozen=True, slots=True)
class ReviewPackResult:
    path: Path
    pack_complete: bool
    review_ready: bool
    missing_artifacts: tuple[str, ...]
    missing_sources: tuple[str, ...]


def _json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed JSON in {path.name}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_fingerprint(repo_root: Path) -> str:
    paths = sorted(set((
        *CAMPAIGN_SOURCE_PATHS,
        *OPTIONAL_CAMPAIGN_SOURCE_PATHS,
        *SHARED_SOURCE_PATHS,
        *TEST_SOURCE_PATHS,
    )), key=lambda item: item.as_posix())
    records = []
    for relative in paths:
        source = repo_root.resolve() / relative
        if source.is_file():
            records.append({
                "path": relative.as_posix(),
                "sha256": _sha256(source.read_bytes()),
            })
    encoded = json.dumps(
        records, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.blake2b(
        encoded, digest_size=20, person=b"rdp-wp6-src-v1"
    ).hexdigest()


def _record(path: str, data: bytes, purpose: str) -> dict[str, Any]:
    return {
        "path": path,
        "size_bytes": len(data),
        "sha256": _sha256(data),
        "purpose": purpose,
    }


def _safe_member(path: str) -> str:
    member = PurePosixPath(path.replace("\\", "/"))
    if member.is_absolute() or not member.parts or ".." in member.parts or "." in member.parts:
        raise ValueError(f"unsafe review-pack member path {path!r}")
    return member.as_posix()


def _contains_reference(value: Any) -> str | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token == "truth_policy":
                pass
            elif token in _REFERENCE_KEYS or token.startswith(_REFERENCE_PREFIXES):
                return str(key)
            found = _contains_reference(item)
            if found is not None:
                return found
    elif isinstance(value, (list, tuple)):
        for item in value:
            found = _contains_reference(item)
            if found is not None:
                return found
    return None


def _guard_run_json(relative: Path, data: bytes) -> None:
    if relative.as_posix() in {
        "artifacts/experiment_result.json",
        "artifacts/source_experiment_result.json",
        "artifacts/staged_d8_handoff/source_static_experiment_result.json",
        "artifacts/staged_d8_handoff/source_shell_experiment_result.json",
        "artifacts/staged_d8_handoff/source_pilot_experiment_result.json",
        "artifacts/experiment_a/source_pack02b_experiment_result.json",
        "artifacts/experiment_b/terminal_branch_evaluation.json",
    }:
        return
    if relative.suffix.lower() != ".json":
        return
    try:
        value = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    found = _contains_reference(value)
    if found is not None:
        raise ValueError(
            f"search-visible run artifact {relative.as_posix()} contains reference field {found!r}"
        )


def _guard_portable(data: bytes, repo_root: Path, member: str) -> None:
    if b"\x00" in data:
        return
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return
    candidates = {
        str(repo_root.resolve()),
        str(repo_root.resolve()).replace("\\", "/"),
        str(repo_root.resolve()).replace("/", "\\"),
    }
    for candidate in candidates:
        if candidate and candidate in text:
            raise ValueError(f"review-pack member {member} contains the absolute repository path")


def _git(repo_root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip()


def _git_state(repo_root: Path, meta: Mapping[str, Any]) -> dict[str, Any]:
    status = _git(repo_root, "status", "--porcelain")
    current_commit = _git(repo_root, "rev-parse", "HEAD")
    branch = _git(repo_root, "branch", "--show-current")
    recorded_git = meta.get("git") if isinstance(meta.get("git"), Mapping) else {}
    return {
        "recorded_run_commit": recorded_git.get("commit"),
        "recorded_run_dirty": recorded_git.get("dirty"),
        "current_commit": current_commit,
        "current_branch": branch,
        "working_tree_clean": None if status is None else status == "",
        "working_tree_entries": [] if not status else status.splitlines(),
    }


def _environment() -> dict[str, Any]:
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "numpy_version": np.__version__,
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "byteorder": sys.byteorder,
    }


def _required_artifacts(experiment_id: str, run_dir: Path | None = None) -> tuple[str, ...]:
    common = (
        "artifacts/experiment_manifest.json",
        "artifacts/experiment_result.json",
    )
    if experiment_id in {"technical_canary_v1", "archive_handoff_v1"}:
        return (*common,
            "artifacts/replay_context.json",
            "artifacts/coordinate_archive.json",
            "artifacts/archive_handoff_batch.json",
            "artifacts/archive_handoff_binding.json",
            "artifacts/control_start_batch.json",
            "artifacts/control_start_binding.json",
            "artifacts/final_archive.json",
            "artifacts/control_final_archive.json",
        )
    if experiment_id == "coordinate_supply_v1":
        benchmark_artifacts = tuple(
            f"artifacts/coordinate_supply/{benchmark_id}/{filename}"
            for benchmark_id in _COORDINATE_SUPPLY_BENCHMARK_IDS
            for filename in (
                "discovery_pool_archive.json",
                "coordinate_archive.json",
                "discovery_restarts.json",
                "discovery_diagnostics.json",
            )
        )
        replay_contexts = tuple(
            f"artifacts/replay_contexts/{benchmark_id}.json"
            for benchmark_id in _COORDINATE_SUPPLY_BENCHMARK_IDS
        )
        return (
            *common,
            "artifacts/coordinate_supply_summary.json",
            *replay_contexts,
            *benchmark_artifacts,
        )
    if experiment_id == "target_coordinate_supply_v1":
        block_artifacts = tuple(
            f"artifacts/target_coordinate_supply/seed_block_{seed_block}/{filename}"
            for seed_block in (0, 1)
            for filename in (
                "discovery_pool_archive.json",
                "coordinate_archive.json",
                "discovery_restarts.json",
                "discovery_diagnostics.json",
            )
        )
        return (
            *common,
            "artifacts/replay_context.json",
            "artifacts/target_coordinate_supply_summary.json",
            "artifacts/target_coordinate_supply/combined_pool_archive.json",
            "artifacts/target_coordinate_supply/combined_diagnostics.json",
            *block_artifacts,
        )
    if experiment_id == "target_ranking_diagnostic_v1":
        return (
            *common,
            "artifacts/replay_context.json",
            "artifacts/source_experiment_manifest.json",
            "artifacts/source_experiment_result.json",
            "artifacts/source_target_coordinate_supply_summary.json",
            "artifacts/source_combined_pool_archive.json",
            "artifacts/source_combined_diagnostics.json",
            "artifacts/source_replay_context.json",
            "artifacts/all_candidates_batch.json",
            "artifacts/all_candidates_binding.json",
            "artifacts/all_candidates_replay.json",
        )
    if experiment_id == "multiscale_scorer_contract_canary_v1":
        return (*common, "artifacts/scorer_contract_canary.json")
    if experiment_id == "multiscale_static_panel_v1":
        return (*common, "artifacts/static_panel_summary.json")
    if experiment_id == "exact_extra_crib_contract_canary_v1":
        return (*common, "artifacts/exact_extra_crib_contracts.json")
    if experiment_id == "multiscale_perturbation_shells_v1":
        return (
            *common,
            "artifacts/perturbation_shell_design.json",
            "artifacts/execution_timing.json",
        )
    if experiment_id == "matched_d8_profile_pilot_v1":
        return (
            *common,
            "artifacts/matched_d8_pilot_summary.json",
            "artifacts/matched_d8_pilot/starts.json",
            "artifacts/matched_d8_pilot/source_static_panel_summary.json",
            "artifacts/execution_timing.json",
            "artifacts/matched_d8_pilot/attempt_timing.json",
        )
    if experiment_id == "staged_d8_handoff_v1":
        stage_artifacts = tuple(
            f"artifacts/staged_d8_handoff/{stage_id}/{filename}"
            for stage_id in ("scout", "bridge", "judge")
            for filename in (
                "candidate_archive.json",
                "attempts.json",
                "handoff_batch.json",
                "replay_context.json",
                "replay_binding.json",
                "replay_evidence.json",
            )
        )
        final_artifacts = tuple(
            f"artifacts/staged_d8_handoff/final_union/{filename}"
            for filename in (
                "candidate_archive.json",
                "replay_batch.json",
                "replay_context.json",
                "replay_binding.json",
                "replay_evidence.json",
            )
        )
        return (
            *common,
            "artifacts/staged_d8_handoff_summary.json",
            "artifacts/execution_timing.json",
            "artifacts/staged_d8_handoff/ladder_freeze.json",
            "artifacts/staged_d8_handoff/scout_starts.json",
            "artifacts/staged_d8_handoff/attempt_timing.json",
            "artifacts/staged_d8_handoff/runtime_projection.json",
            "artifacts/staged_d8_handoff/source_static_experiment_result.json",
            "artifacts/staged_d8_handoff/source_shell_experiment_result.json",
            "artifacts/staged_d8_handoff/source_pilot_experiment_result.json",
            *stage_artifacts,
            *final_artifacts,
        )
    if experiment_id == "experiment_a_standard_panel_v1":
        block_artifacts: list[str] = []
        primary_benchmark = "alice_308_p13_p17_crib188x13_plus206x8_d08"
        positional_benchmark = "alice_308_p13_p17_crib188x13_plus081x8_d08"
        for benchmark_id, block_ids, include_baseline in (
            (primary_benchmark, range(31, 39), True),
            (positional_benchmark, range(41, 45), False),
        ):
            for block_id in block_ids:
                root = (
                    f"artifacts/experiment_a/{benchmark_id}/"
                    f"block_{block_id:02d}"
                )
                block_artifacts.append(f"{root}/starts.json")
                if include_baseline:
                    block_artifacts.extend(
                        f"{root}/baseline/search/{filename}"
                        for filename in (
                            "candidate_archive.json",
                            "attempts.json",
                            "handoff_batch.json",
                            "replay_context.json",
                            "replay_binding.json",
                            "replay_evidence.json",
                        )
                    )
                for stage_id in ("scout", "bridge", "judge"):
                    block_artifacts.extend(
                        f"{root}/staged/{stage_id}/{filename}"
                        for filename in (
                            "candidate_archive.json",
                            "attempts.json",
                            "handoff_batch.json",
                            "replay_context.json",
                            "replay_binding.json",
                            "replay_evidence.json",
                        )
                    )
                block_artifacts.extend(
                    f"{root}/staged/final_union/{filename}"
                    for filename in (
                        "candidate_archive.json",
                        "replay_batch.json",
                        "replay_context.json",
                        "replay_binding.json",
                        "replay_evidence.json",
                    )
                )
        return (
            *common,
            "artifacts/experiment_a_standard_panel_summary.json",
            "artifacts/execution_timing.json",
            "artifacts/experiment_a/runtime_plan.json",
            "artifacts/experiment_a/attempt_timing.json",
            "artifacts/experiment_a/search_summary.json",
            "artifacts/experiment_a/replay_summary.json",
            "artifacts/experiment_a/source_pack02b_experiment_result.json",
            *tuple(block_artifacts),
        )
    if experiment_id in {"candidate_word_branches_b10_v1", "candidate_word_branches_b100_v1", "candidate_word_branches_b1000_v1"}:
        base = (
            *common,
            "artifacts/candidate_branch_summary.json",
            "artifacts/execution_timing.json",
            "artifacts/experiment_b/candidate_list.json",
            "artifacts/experiment_b/candidate_list_assets.json",
            "artifacts/experiment_b/shared_starts.json",
            "artifacts/experiment_b/shared/scout_selection_archive.json",
            "artifacts/experiment_b/shared/scout_selection_summary.json",
            "artifacts/experiment_b/search_summary.json",
            "artifacts/experiment_b/replay_summary.json",
            "artifacts/experiment_b/attempt_timing.json",
            "artifacts/experiment_b/terminal_branch_evaluation.json",
            "artifacts/experiment_b/source_experiment_a_gate.json",
            "artifacts/experiment_b/required_artifacts.json",
        )
        if run_dir is None:
            return base
        inventory_path = run_dir / "artifacts/experiment_b/required_artifacts.json"
        if not inventory_path.is_file():
            return base
        inventory = _read_json(inventory_path)
        paths = inventory.get("paths")
        if not isinstance(paths, list) or any(not isinstance(item, str) for item in paths):
            raise ValueError("candidate branch required-artifact inventory is invalid")
        safe_paths: list[str] = []
        for item in paths:
            candidate = Path(item)
            if (
                not item
                or candidate.is_absolute()
                or ".." in candidate.parts
                or "\\" in item
                or candidate.as_posix() != item
            ):
                raise ValueError(
                    "candidate branch required-artifact inventory contains an unsafe path"
                )
            safe_paths.append(item)
        return tuple(dict.fromkeys((*base, *safe_paths)))
    if experiment_id == "b100_scout_budget_sensitivity_v1":
        return (
            *common,
            "artifacts/execution_timing.json",
            "artifacts/b100_budget_sensitivity/source_b100_gate.json",
            "artifacts/b100_budget_sensitivity/summary.json",
        )
    if experiment_id == "candidate_selection_v1":
        return (
            *common,
            "artifacts/replay_context.json",
            "artifacts/source_experiment_manifest.json",
            "artifacts/source_experiment_result.json",
            "artifacts/source_discovery_pool_archive.json",
            "artifacts/source_discovery_diagnostics.json",
            "artifacts/source_replay_context.json",
            "artifacts/top_wli_batch.json",
            "artifacts/top_wli_binding.json",
            "artifacts/top_wli_replay.json",
            "artifacts/diverse_high_wli_batch.json",
            "artifacts/diverse_high_wli_binding.json",
            "artifacts/diverse_high_wli_replay.json",
            "artifacts/selection_comparison.json",
        )
    if experiment_id == "matched_exploitation_v1":
        source_artifacts = (
            "artifacts/source_experiment_manifest.json",
            "artifacts/source_experiment_result.json",
            "artifacts/source_replay_context.json",
            "artifacts/source_selection_comparison.json",
            "artifacts/source_top_wli_batch.json",
            "artifacts/source_top_wli_binding.json",
            "artifacts/source_top_wli_replay.json",
            "artifacts/source_diverse_high_wli_batch.json",
            "artifacts/source_diverse_high_wli_binding.json",
            "artifacts/source_diverse_high_wli_replay.json",
            "artifacts/source_discovery_pool_archive.json",
            "artifacts/source_discovery_diagnostics.json",
        )
        final_artifacts = tuple(
            f"artifacts/{label}_final_{suffix}.json"
            for label in ("top_wli", "diverse_high_wli", "independent_control")
            for suffix in ("archive", "batch", "binding", "replay")
        )
        return (
            *common,
            "artifacts/replay_context.json",
            *source_artifacts,
            "artifacts/control_start_archive.json",
            "artifacts/control_start_batch.json",
            "artifacts/control_start_binding.json",
            "artifacts/matched_exploitation.json",
            *final_artifacts,
        )
    if experiment_id == "candidate_replay_v1":
        return (*common, "artifacts/candidate_replay.json")
    if experiment_id == "technical_canary_replay_suite_v1":
        return (
            *common,
            "artifacts/source_replay_context.json",
            "artifacts/archive_handoff_replay.json",
            "artifacts/control_start_replay.json",
        )
    if experiment_id == "benchmark_contract_canary_v1":
        return (*common, "artifacts/benchmark_contract.json")
    return common


def _validation_receipt(repo_root: Path) -> dict[str, Any]:
    path = repo_root / VALIDATION_RECEIPT
    if not path.is_file():
        return {
            "schema": LOCAL_VALIDATION_SCHEMA,
            "status": "not_recorded",
            "passed": None,
            "failed": None,
            "skipped": None,
            "note": "Run focused and real-asset tests locally before treating this pack as review-ready.",
            "source_fingerprint": None,
        }
    receipt = _read_json(path)
    if receipt.get("schema") != LOCAL_VALIDATION_SCHEMA:
        raise ValueError("local validation receipt has an unsupported schema")
    return receipt


def write_local_validation_receipt(
    repo_root: Path,
    *,
    selected: int,
    passed: int,
    failed: int,
    skipped: int,
    duration_s: float,
    note: str | None = None,
) -> Path:
    counts = {
        "selected": selected,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
    }
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if passed + failed + skipped != selected:
        raise ValueError("passed, failed and skipped must sum to selected")
    if isinstance(duration_s, bool):
        raise ValueError("duration_s must be a non-negative finite number")
    duration = float(duration_s)
    if not np.isfinite(duration) or duration < 0:
        raise ValueError("duration_s must be a non-negative finite number")
    if note is not None and (not isinstance(note, str) or not note.strip()):
        raise ValueError("note must be a non-empty string or None")
    payload = {
        "schema": LOCAL_VALIDATION_SCHEMA,
        "status": "passed" if failed == 0 else "failed",
        **counts,
        "duration_s": duration,
        "note": None if note is None else note.strip(),
        "source_fingerprint": _source_fingerprint(repo_root),
    }
    path = repo_root.resolve() / VALIDATION_RECEIPT
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    try:
        temporary.write_bytes(_json_bytes(payload))
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path


def _review_markdown(manifest: Mapping[str, Any], result: Mapping[str, Any]) -> str:
    experiment = manifest["experiment"]
    experiment_id = str(manifest.get("experiment_id") or "")
    quality = manifest["evidence_quality"]
    summary = result.get("result_summary", {})
    lines = [
        "# Two-period overlay run review",
        "",
        "## Identity",
        "",
        f"- campaign: `{manifest['campaign_id']}`",
        f"- experiment: `{manifest['experiment_id']}`",
        f"- benchmark: `{manifest['benchmark_id']}`",
        f"- run: `{manifest['run_id']}`",
        f"- status: `{manifest['run_status']}`",
        f"- decision: `{manifest.get('decision')}`",
        f"- stop reason: `{manifest.get('stop_reason')}`",
        f"- configuration hash: `{manifest.get('configuration_hash')}`",
        "",
        "## Scientific contract",
        "",
        f"**Question:** {experiment.get('question')}",
        "",
        f"**Hypothesis:** {experiment.get('hypothesis')}",
        "",
        f"**Strongest alternative:** {experiment.get('alternative')}",
        "",
        f"**Decision rule:** {experiment.get('decision_rule')}",
        "",
        f"- WLI mode: `{experiment.get('wli_mode')}`",
        f"- truth policy: `{experiment.get('truth_policy')}`",
        f"- budget seconds: `{experiment.get('budget_seconds')}`",
        f"- budget evaluations: `{experiment.get('budget_evaluations')}`",
        f"- lesson IDs: `{', '.join(experiment.get('lesson_ids', []))}`",
        "",
        "## Result summary",
        "",
    ]
    for key in (
        "comparison_count", "requested_comparisons", "minimum_comparisons",
        "underpowered", "archive_wins", "control_wins", "ties", "best_score",
        "best_candidate_id", "best_arm", "evaluations", "elapsed_s",
        "candidate_count", "deterministic", "stored_scores_verified",
        "benchmark_count", "repeat_count", "all_structural_repeats_equal",
        "artifact", "replay_context_artifacts", "source_run_id",
        "replay_count", "all_deterministic", "all_stored_scores_verified",
        "technical_replay_gate_passed", "replays",
        "benchmark_ids", "minimum_unique_candidates", "total_evaluations",
        "evaluation_budget_upper_bound", "total_generated_candidates",
        "total_unique_candidates", "all_unique_thresholds_met", "benchmarks",
        "selection_count", "shortlist_count", "overlap_count",
        "selection_sets_identical", "top_wli_batch_id",
        "diverse_high_wli_batch_id", "top_wli_binding_id",
        "diverse_high_wli_binding_id", "top_score_summary",
        "diverse_score_summary", "top_affine_hamming_summary",
        "diverse_affine_hamming_summary", "selection_gate_passed",
        "policy_signal", "preference_min_wins", "arm_summaries",
        "pairwise", "slot_winner_counts", "tied_slots",
        "control_start_evaluations", "exploitation_evaluations",
        "final_replay_evaluations", "evaluation_ceiling",
        "all_final_replays_verified", "matched_exploitation_gate_passed",
        "final_replays", "seed_blocks", "restarts_per_block", "sweeps",
        "minimum_unique_per_block", "minimum_combined_unique",
        "all_block_thresholds_met", "target_supply_gate_passed",
        "combined", "blocks", "replay_evaluations", "terminal_evaluations",
        "batch_id", "binding_id", "replay_id",
        "ranking_diagnostic_gate_passed", "profile_count", "profile_ids",
        "all_profiles_passed", "recorded_baseline_effective_weights",
        "intended_judge_effective_weights", "surface_count", "surface_ids",
        "all_deterministic", "static_panel_gate_passed", "all_contracts_passed",
        "primary_block_count", "positional_block_count", "starts_per_block",
        "promotion_gate_passed", "primary_baseline_exact_blocks",
        "primary_staged_exact_blocks", "positional_staged_exact_blocks",
        "experiment_a_overnight_recommended", "list_id", "branch_count",
        "selected_branch_count", "branch_survival_rate",
        "progression_gate_passed", "exact_solution_persisted",
    ):
        if key in summary:
            rendered = (
                json.dumps(summary[key], ensure_ascii=False, sort_keys=True)
                if isinstance(summary[key], (Mapping, list, tuple))
                else str(summary[key])
            )
            lines.append(f"- {key}: `{rendered}`")

    timing = summary.get("timing")
    if isinstance(timing, Mapping):
        lines.extend([
            "",
            "## Timing",
            "",
            f"- started at UTC: `{timing.get('started_at_utc')}`",
            f"- finished at UTC: `{timing.get('finished_at_utc')}`",
            (
                "- scientific-work elapsed seconds: "
                f"`{timing.get('scientific_work_elapsed_s', timing.get('elapsed_s'))}`"
            ),
            f"- scope: {timing.get('scope')}",
        ])
        phases = timing.get("phases")
        if isinstance(phases, Mapping):
            for phase_name, phase_elapsed in phases.items():
                lines.append(f"- {phase_name}: `{phase_elapsed}` seconds")
        profiles = timing.get("profiles")
        if isinstance(profiles, Mapping):
            lines.extend(["", "### Profile and arm timing", ""])
            for profile_id in sorted(profiles):
                profile_timing = profiles[profile_id]
                if not isinstance(profile_timing, Mapping):
                    continue
                if "elapsed_s" in profile_timing:
                    lines.append(
                        f"- `{profile_id}`: elapsed=`{profile_timing.get('elapsed_s')}` s; "
                        f"evaluations=`{profile_timing.get('evaluations')}`; "
                        f"evaluations/s=`{profile_timing.get('candidate_evaluations_per_s')}`"
                    )
                    continue
                for arm_id in sorted(profile_timing):
                    arm = profile_timing[arm_id]
                    if not isinstance(arm, Mapping):
                        continue
                    attempt_summary = arm.get("attempt_elapsed_s_summary")
                    attempt_summary = attempt_summary if isinstance(attempt_summary, Mapping) else {}
                    lines.append(
                        f"- `{profile_id}/{arm_id}`: elapsed=`{arm.get('elapsed_s')}` s; "
                        f"attempts=`{arm.get('attempt_count')}`; "
                        f"median attempt=`{attempt_summary.get('median')}` s; "
                        f"maximum attempt=`{attempt_summary.get('maximum')}` s; "
                        f"evaluations/s=`{arm.get('candidate_evaluations_per_s')}`"
                    )
        if timing.get("attempt_timing_artifact"):
            lines.append(
                f"- individual attempt log: `{timing.get('attempt_timing_artifact')}`"
            )

    if experiment_id in {"candidate_word_branches_b10_v1", "candidate_word_branches_b100_v1", "candidate_word_branches_b1000_v1"}:
        terminal = result.get("reference_evaluation")
        if isinstance(terminal, Mapping):
            ranks = terminal.get("branch_ranks")
            ranks = ranks if isinstance(ranks, Mapping) else {}
            lines.extend([
                "",
                "## Terminal branch result",
                "",
                f"- controlled word: `{terminal.get('controlled_word')}`",
                f"- occurred naturally in source list: `{terminal.get('controlled_word_occurred_naturally')}`",
                f"- survived global scout selection: `{terminal.get('survived_global_scout_selection')}`",
                f"- scout-full branch rank: `{ranks.get('scout_full')}`",
                f"- scout-selected branch rank: `{ranks.get('scout_selected')}`",
                f"- bridge branch rank: `{ranks.get('bridge')}`",
                f"- final branch rank: `{ranks.get('final')}`",
                f"- exact solution persisted: `{terminal.get('exact_solution_persisted')}`",
                f"- progression gate passed: `{terminal.get('progression_gate_passed')}`",
            ])

    if experiment_id == "b100_scout_budget_sensitivity_v1":
        terminal = result.get("reference_evaluation")
        if isinstance(terminal, Mapping):
            checks = terminal.get("gate_checks")
            checks = checks if isinstance(checks, Mapping) else {}
            lines.extend([
                "",
                "## B1000 progression result",
                "",
                f"- B1000 gate passed: `{terminal.get('b1000_gate_passed')}`",
                *[f"- {key}: `{value}`" for key, value in sorted(checks.items())],
            ])

    lines.extend([
        "",
        "## Evidence quality",
        "",
        f"- required run artifacts complete: `{quality['required_artifacts_complete']}`",
        f"- source snapshot complete: `{quality['source_snapshot_complete']}`",
        f"- local tests recorded as passed: `{quality['tests_passed']}`",
        f"- validation matches packed source: `{quality['validation_source_matches']}`",
        f"- working tree clean (informational): `{quality['working_tree_clean']}`",
        f"- pack complete: `{manifest['pack_complete']}`",
        f"- review ready: `{manifest['review_ready']}`",
    ])
    if manifest["missing_artifacts"]:
        lines.append(f"- missing artifacts: `{', '.join(manifest['missing_artifacts'])}`")
    if manifest["missing_sources"]:
        lines.append(f"- missing sources: `{', '.join(manifest['missing_sources'])}`")
    if manifest.get("missing_source_run_artifacts"):
        lines.append(
            "- missing source-run artifacts: `"
            + ", ".join(manifest["missing_source_run_artifacts"])
            + "`"
        )
    review_questions = {
        "benchmark_contract_canary_v1": (
            "Were all four expected affine dimensions derived as `0/4/8/16`?",
            "Did every known key round-trip with affine reconstruction and `B[0] = 0`?",
            "Were scores finite and exactly repeated?",
            "Were ciphertext, WLI, crib, affine structures and replay-context IDs identical?",
            "Was reference evaluation terminal-only and exact for plaintext, key and shifts?",
            "Are all search-visible artifacts free of plaintext and benchmark-key fields?",
        ),
        "coordinate_supply_v1": (
            "Did every declared restart complete within the frozen evaluation budget?",
            "Was every unique coordinate optimum retained with restart provenance?",
            "How many unique candidates were supplied on the dimension-4 and dimension-8 rungs?",
            "Did either rung collapse to duplicate or near-duplicate affine basins?",
            "When did the best score and bounded archive last change?",
            "Do the terminal reference results show an exact lower-rung solve without truth leakage?",
            "Is P13/P17 candidate-supply execution justified, or is another discovery mechanism needed first?",
        ),
        "target_coordinate_supply_v1": (
            "Did both independent P13/P17 seed blocks complete within their frozen budgets?",
            "Did each block supply at least sixteen unique coordinate optima?",
            "Did the combined pool contain at least thirty-two unique candidates?",
            "How much candidate-identity overlap occurred between the two seed blocks?",
            "Do the combined affine and expanded-key diagnostics show broad basin coverage?",
            "Did the best score continue improving late in either block?",
            "Was benchmark truth used only for terminal evaluation of the combined best candidate?",
            "Is the resulting target pool sufficient for deterministic selection, or is a new discovery operator required?",
        ),
        "target_ranking_diagnostic_v1": (
            "Did all sixty-four P13/P17 candidates replay twice with stored scores verified?",
            "Does the terminal output contain only aggregate ranking diagnostics, with no candidate-specific truth mapping?",
            "How strongly does WLI rank associate with terminal rune and complete-word matches?",
            "Are the score-ranked top 8, 16 and 32 enriched for the strongest terminal candidates?",
            "Where does the best terminal candidate fall in the WLI ordering?",
            "Does the evidence support score-only selection, diversity-aware selection, or scorer investigation before exploitation?",
        ),
        "multiscale_scorer_contract_canary_v1": (
            "Did every predeclared profile build and execute using the installed assets?",
            "Did repeated batch scoring and scalar scoring agree within the frozen tolerance?",
            "Does the evidence distinguish the exact recorded J0 weighting from intended J1 weighting?",
            "Were asset names and hashes recorded for all orders 1-4 used by the panel?",
        ),
        "multiscale_static_panel_v1": (
            "Did all d4, d8 and d16 candidates rerank twice under every profile?",
            "Which profiles improve rune, complete-word and affine enrichment over J0?",
            "How strongly do profile rankings disagree across the three saved surfaces?",
            "Are throughput and Python allocation costs acceptable for the matched d8 pilot?",
            "Does terminal output remain aggregate-only with no candidate-specific truth mapping?",
            "Which profiles should enter the matched pilot without freezing the ladder prematurely?",
        ),
        "exact_extra_crib_contract_canary_v1": (
            "Do offsets 206 and 81 each add rank eight to the original d16 space?",
            "Do both contracts preserve B[0] = 0 and reconstruct the exact gauge-fixed key?",
            "Are both complete dormouse spans recorded explicitly as declared oracle assistance?",
            "Was any normal search performed during this contract-only canary?",
        ),
        "multiscale_perturbation_shells_v1": (
            "Were all d16 shell distances 1, 2, 4, 6, 8, 12 and 16 sampled deterministically?",
            "Were variable indices and non-zero modulo-29 deltas balanced as declared?",
            "Which profiles show monotonic median movement and the least adjacent-shell overlap?",
            "Do shell scores associate with rune, complete-word and affine-variable correctness?",
            "Were shell candidates kept out of normal candidate archives and later search seeds?",
            "Are total and per-profile scoring times explicit and plausible?",
        ),
        "matched_d8_profile_pilot_v1": (
            "Did every profile use the same eight deterministic starting vectors?",
            "Did the fixed core use identical coordinate-sweep limits for every profile?",
            "Were the calibrated-time sweep caps derived only from the accepted Pack 01 static evidence?",
            "Did every retained candidate replay with its stored profile score verified?",
            "Which profiles improve rune, word and affine correctness from the matched starts?",
            "How do duplicate rate, basin diversity, throughput and terminal enrichment compare?",
            "Was all search-visible work completed before terminal metrics were opened?",
            "Does the evidence justify freezing one scout, one bridge and one judge for Pack 02B?",
            "Are total, per-profile/arm and individual restart timings explicit enough for home-PC scaling decisions?",
        ),
        "staged_d8_handoff_v1": (
            "Was the ladder frozen explicitly as S2 scout, B1 bridge and F1 judge from the accepted aggregate evidence?",
            "Did all ninety-six deterministic scout starts complete under the frozen budget?",
            "Did every unique scout candidate enter the bridge and every unique scout/bridge candidate enter the judge?",
            "Were scout, bridge, judge and final-union candidate surfaces all persisted and replayed deterministically?",
            "Did the final F1 union preserve earlier basins rather than silently retaining only the last stage?",
            "Which stage first generated the eventual best candidate, and did later stages promote, rescue or damage it?",
            "Did any exact candidate appear, or did the search repeatedly saturate at the 289-rune basin?",
            "Are per-stage, per-attempt and total timing data explicit, with 256/512/1024 and eight-hour projections?",
            "Does the evidence justify a substantially longer standard Experiment A panel before an overnight run?",
        ),
        "candidate_word_branches_b10_v1": (
            "Did all ten valid distinct branches receive identical starts and equal S2 budget?",
            "Did the correct branch survive global score-only selection without a per-branch quota?",
            "What was its rank after scout, bridge and final judgement?",
            "Did any false branches outrank it, and did the correct branch solve exactly?",
            "Does the measured safety-adjusted B100 projection fit eight hours?",
            "Was B100 authorised only by the predeclared terminal gate?",
        ),
        "candidate_word_branches_b100_v1": (
            "Did all one hundred branches receive identical starts and equal S2 budget?",
            "Did the correct branch survive and finish in the top ten?",
            "Did the correct branch produce an exact persisted and replayed solution?",
            "Which false branches produced the strongest final scores?",
            "Did actual runtime remain within the declared overnight budget?",
            "Is B1000 scientifically and computationally justified?",
        ),
        "b100_scout_budget_sensitivity_v1": (
            "Was the diagnostic derived only from the completed source-matched B100 attempt evidence?",
            "Did every disjoint eight-start block rank the controlled branch in the top three?",
            "Did the controlled branch survive the frozen top-200 candidate selection in every eight-start block?",
            "Was the minimum controlled-versus-false score margin at least 0.05?",
            "Does the conservative safety-adjusted B1000 projection fit eight hours?",
            "Was B1000 authorised only by the complete predeclared diagnostic gate?",
        ),
        "candidate_word_branches_b1000_v1": (
            "Did all one thousand distinct branches receive the same eight deterministic S2 starts?",
            "Was global scout retention capped at four hundred candidates with no per-branch quota?",
            "Did the controlled branch survive and finish in the top twenty-five?",
            "Did the exact solution persist and replay deterministically?",
            "How many branches survived and which false branches produced the strongest final scores?",
            "Did scientific runtime remain within the declared eight-hour ceiling?",
            "Does the result close the current B1000 scaling question without silently authorising further work?",
        ),
        "experiment_a_standard_panel_v1": (
            "Did all eight primary baseline/staged blocks and four positional staged blocks complete from independent deterministic starts?",
            "Did primary J0 and staged arms receive identical starting vectors, equal archive capacities and equal wall-clock ceilings?",
            "Were all current-run search surfaces persisted and replayed before any current-run terminal metrics were opened?",
            "How many independent primary blocks solved under J0 and under the staged ladder?",
            "How many S2 scout attempts converged to the exact candidate in each block, and did B1 or F1 add any exact candidates not already present in scout?",
            "Did the offset-81 positional confirmation produce at least one exact persisted and replayed solution?",
            "What were the exact-block rates, time-to-first-exact distributions and per-stage runtimes?",
            "Does J0 match or exceed the staged method, or does the staged/scout surface retain a clear advantage?",
            "Is another assisted-d8 overnight run scientifically justified, or should the overnight budget move to Experiment B scaling or later d16 work?",
        ),
        "candidate_selection_v1": (
            "Were both selections derived from the exact bound d8 coordinate-supply archive?",
            "Does the diverse-high-WLI policy preserve the best candidate and produce a different eight-candidate set?",
            "How much score is sacrificed, if any, to increase affine basin separation?",
            "Did both selected batches replay twice with stored scores and ranking verified?",
            "Are both batches and bindings suitable for the next matched exploitation experiment?",
        ),
        "matched_exploitation_v1": (
            "Were the top-WLI and diverse-high-WLI surfaces loaded from the exact verified selection run?",
            "Did all three arms use the same matched seed and identical exploitation budget at each slot?",
            "Did each selected policy outperform the common independent-control surface?",
            "Did top-WLI or diverse-high-WLI win at least six of eight matched policy comparisons?",
            "How strongly did starting WLI score predict final score and gain?",
            "Did all unique final candidates replay twice with stored scores verified?",
            "Do terminal reference results show exact solves or saturation without truth leakage?",
            "Does the d8 evidence justify one selection policy, a second seed block, or P13/P17 supply work?",
        ),
        "candidate_replay_v1": (
            "Does the binding identify the exact source run, context and candidate batch?",
            "Does every candidate reproduce its stored identity, affine key and gauge?",
            "Are repeated scores and ranking deterministic within the declared tolerances?",
            "Does evaluator and language-model provenance match the source context?",
        ),
        "technical_canary_replay_suite_v1": (
            "Are both required technical-canary bindings present and tied to one source run?",
            "Did every archive-handoff and independent-control candidate verify twice?",
            "Are both stored rankings deterministic within the declared tolerances?",
            "Does evaluator and language-model provenance match the source context?",
            "Is the complete source binding, context and batch evidence included in this pack?",
        ),
    }.get(
        manifest["experiment_id"],
        (
            "Did discovery supply enough unique candidates?",
            "Did discovery collapse into one basin?",
            "Did the selected policies produce genuinely different candidate sets?",
            "Did starting score predict final performance?",
            "Did archive-derived candidates beat independent starts?",
            "Did exploitation improve the supplied candidates?",
            "Are bindings, provenance and replay evidence sufficient?",
            "Is the experiment valid and sufficiently powered?",
            "Is scale-up justified?",
        ),
    )
    lines.extend([
        "",
        "## Review questions",
        "",
        *(f"- {question}" for question in review_questions),
        "",
        "Review `review_manifest.json` and `file_inventory.sha256` before relying on individual artifacts.",
        "",
    ])
    return "\n".join(lines)


def _add_source_entries(
    entries: dict[str, bytes],
    records: list[dict[str, Any]],
    missing: list[str],
    repo_root: Path,
    paths: Iterable[Path],
    prefix: str,
    purpose: str,
    *,
    required: bool,
) -> None:
    for relative in paths:
        source = repo_root / relative
        if not source.is_file():
            if required:
                missing.append(relative.as_posix())
            continue
        member = _safe_member(f"{prefix}/{relative.name}")
        data = source.read_bytes()
        _guard_portable(data, repo_root, member)
        entries[member] = data
        records.append(_record(member, data, purpose))


def _portable_validation_bytes(data: bytes, repo_root: Path) -> bytes:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = data.decode("utf-16")
    elif data.startswith(b"\xef\xbb\xbf"):
        text = data.decode("utf-8-sig")
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            return data
    root = str(repo_root.resolve())
    for candidate in {root, root.replace("\\", "/"), root.replace("/", "\\")}:
        if candidate:
            text = text.replace(candidate, "<repo_root>")
    return text.encode("utf-8")


def _add_local_validation_artifacts(
    entries: dict[str, bytes],
    records: list[dict[str, Any]],
    repo_root: Path,
) -> None:
    root = repo_root / VALIDATION_ARTIFACT_ROOT
    if not root.is_dir():
        return
    for source in sorted(path for path in root.rglob("*") if path.is_file()):
        relative = source.relative_to(root)
        member = _safe_member(f"validation/local/{relative.as_posix()}")
        data = source.read_bytes()
        if source.suffix.lower() in {".log", ".txt"}:
            data = _portable_validation_bytes(data, repo_root)
        _guard_portable(data, repo_root, member)
        entries[member] = data
        records.append(_record(member, data, "local validation output"))


def _asset_provenance(run_dir: Path) -> dict[str, Any]:
    direct = run_dir / "artifacts/replay_context.json"
    source_context = run_dir / "artifacts/source_replay_context.json"
    context_paths = [path for path in (direct, source_context) if path.is_file()]
    context_paths.extend(sorted(
        path for path in (run_dir / "artifacts").rglob("replay_context.json")
        if path not in context_paths
    ))
    nested = run_dir / "artifacts/replay_contexts"
    if nested.is_dir():
        context_paths.extend(sorted(
            path for path in nested.glob("*.json") if path not in context_paths
        ))
    contexts: list[dict[str, Any]] = []
    for path in context_paths:
        context = _read_json(path)
        payload = context.get("payload") if isinstance(context.get("payload"), Mapping) else {}
        provenance = payload.get("evaluator_provenance")
        if not isinstance(provenance, Mapping):
            continue
        contexts.append({
            "artifact": path.relative_to(run_dir).as_posix(),
            "context_id": context.get("context_id"),
            "evaluator_provenance": dict(provenance),
        })
    if not contexts:
        for relative in (
            "artifacts/scorer_contract_canary.json",
            "artifacts/perturbation_shell_design.json",
        ):
            source = run_dir / relative
            if not source.is_file():
                continue
            payload = _read_json(source)
            provenance = payload.get("asset_provenance")
            if isinstance(provenance, Mapping):
                return dict(provenance)
        return {}
    if len(contexts) == 1:
        return dict(contexts[0]["evaluator_provenance"])
    canonical = contexts[0]["evaluator_provenance"]
    return {
        "schema": "rdp.two_period_overlay.asset_provenance.v1",
        "context_count": len(contexts),
        "all_evaluator_provenance_equal": all(
            item["evaluator_provenance"] == canonical for item in contexts[1:]
        ),
        "evaluator_provenance": canonical,
        "contexts": contexts,
    }


_REPLAY_SOURCE_ARTIFACTS = (
    "META.json",
    "artifacts/experiment_manifest.json",
    "artifacts/experiment_result.json",
    "artifacts/replay_context.json",
    "artifacts/archive_handoff_batch.json",
    "artifacts/archive_handoff_binding.json",
    "artifacts/control_start_batch.json",
    "artifacts/control_start_binding.json",
)


def _add_replay_source_entries(
    entries: dict[str, bytes],
    records: list[dict[str, Any]],
    missing: list[str],
    repo_root: Path,
    source_run_id: str | None,
) -> None:
    if not source_run_id:
        missing.append("source_run_id")
        return
    if source_run_id in {".", ".."} or "/" in source_run_id or "\\" in source_run_id:
        raise ValueError("source_run_id must be one directory name")
    campaign_root = (repo_root / "output/cipher_development/two_period_overlay").resolve()
    source_run = (campaign_root / source_run_id).resolve()
    if campaign_root not in source_run.parents:
        raise ValueError("source replay run escaped the campaign output root")
    for relative in _REPLAY_SOURCE_ARTIFACTS:
        source = source_run / PurePosixPath(relative)
        if not source.is_file():
            missing.append(relative)
            continue
        member = _safe_member(f"source_run/{relative}")
        data = source.read_bytes()
        _guard_run_json(Path(relative), data)
        _guard_portable(data, repo_root, member)
        entries[member] = data
        records.append(_record(member, data, "bound replay source evidence"))


def write_review_pack(repo_root: Path, run_dir: Path) -> ReviewPackResult:
    repo_root = repo_root.resolve()
    run_dir = run_dir.resolve()
    campaign_root = (repo_root / "output/cipher_development/two_period_overlay").resolve()
    if campaign_root not in run_dir.parents:
        raise ValueError("run_dir must remain below the two-period campaign output root")
    run_id = run_dir.name
    manifest_path = run_dir / "artifacts/experiment_manifest.json"
    result_path = run_dir / "artifacts/experiment_result.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    result = _read_json(result_path) if result_path.is_file() else {}
    meta = _read_json(run_dir / "META.json") if (run_dir / "META.json").is_file() else {}
    experiment = manifest.get("experiment") if isinstance(manifest.get("experiment"), Mapping) else {}
    experiment_id = str(experiment.get("experiment_id") or result.get("experiment_id") or "unknown")
    benchmark_id = str(experiment.get("benchmark_id") or result.get("benchmark_id") or "unknown")
    required_artifacts = _required_artifacts(experiment_id, run_dir)
    missing_artifacts = [path for path in required_artifacts if not (run_dir / path).is_file()]

    entries: dict[str, bytes] = {}
    run_records: list[dict[str, Any]] = []
    for source in sorted(path for path in run_dir.rglob("*") if path.is_file()):
        relative = source.relative_to(run_dir)
        member = _safe_member(f"run/{relative.as_posix()}")
        data = source.read_bytes()
        _guard_run_json(relative, data)
        _guard_portable(data, repo_root, member)
        entries[member] = data
        run_records.append(_record(member, data, "run evidence"))

    source_records: list[dict[str, Any]] = []
    missing_sources: list[str] = []
    _add_source_entries(
        entries, source_records, missing_sources, repo_root,
        CAMPAIGN_SOURCE_PATHS, "source/campaign", "campaign source", required=True,
    )
    _add_source_entries(
        entries, source_records, missing_sources, repo_root,
        OPTIONAL_CAMPAIGN_SOURCE_PATHS, "source/campaign", "optional campaign source",
        required=False,
    )
    _add_source_entries(
        entries, source_records, missing_sources, repo_root,
        SHARED_SOURCE_PATHS, "source/shared_contracts", "shared evidence contract",
        required=True,
    )
    _add_source_entries(
        entries, source_records, missing_sources, repo_root,
        TEST_SOURCE_PATHS, "source/tests", "focused test source", required=True,
    )

    source_run_records: list[dict[str, Any]] = []
    missing_source_run_artifacts: list[str] = []
    if experiment_id == "technical_canary_replay_suite_v1":
        summary = result.get("result_summary")
        summary = summary if isinstance(summary, Mapping) else {}
        _add_replay_source_entries(
            entries, source_run_records, missing_source_run_artifacts, repo_root,
            str(summary.get("source_run_id") or "") or None,
        )

    git_state = _git_state(repo_root, meta)
    environment = _environment()
    validation = _validation_receipt(repo_root)
    asset_provenance = _asset_provenance(run_dir)

    generated_validation = {
        "validation/git_state.json": git_state,
        "validation/environment.json": environment,
        "validation/asset_provenance.json": dict(asset_provenance),
        "validation/test_results.json": validation,
    }
    validation_records: list[dict[str, Any]] = []
    for member, value in generated_validation.items():
        data = _json_bytes(value)
        entries[member] = data
        validation_records.append(_record(member, data, "generated validation evidence"))

    _add_local_validation_artifacts(entries, validation_records, repo_root)

    current_source_fingerprint = _source_fingerprint(repo_root)
    validation_source_matches = (
        validation.get("source_fingerprint") == current_source_fingerprint
    )
    tests_passed = (
        validation.get("status") == "passed"
        and int(validation.get("failed", 0)) == 0
        and validation_source_matches
    )
    required_complete = not missing_artifacts
    sources_complete = not missing_sources
    source_run_complete = not missing_source_run_artifacts
    pack_complete = required_complete and sources_complete and source_run_complete
    review_ready = pack_complete and tests_passed
    review_manifest = {
        "schema": REVIEW_PACK_SCHEMA,
        "campaign_id": "two_period_overlay",
        "experiment_id": experiment_id,
        "benchmark_id": benchmark_id,
        "run_id": run_id,
        "run_status": result.get("status", "unknown"),
        "decision": result.get("decision"),
        "stop_reason": result.get("stop_reason"),
        "configuration_hash": manifest.get("configuration_hash"),
        "experiment": dict(experiment),
        "starting_git_commit": (
            meta.get("git", {}).get("commit") if isinstance(meta.get("git"), Mapping) else None
        ),
        "ending_git_commit": git_state.get("current_commit"),
        "working_tree_clean": git_state.get("working_tree_clean"),
        "required_artifacts": list(required_artifacts),
        "missing_artifacts": sorted(missing_artifacts),
        "missing_sources": sorted(missing_sources),
        "missing_source_run_artifacts": sorted(missing_source_run_artifacts),
        "run_files": run_records,
        "source_files": source_records,
        "source_run_files": source_run_records,
        "validation_files": validation_records,
        "asset_provenance": dict(asset_provenance),
        "test_summary": validation,
        "evidence_quality": {
            "required_artifacts_complete": required_complete,
            "source_snapshot_complete": sources_complete,
            "tests_passed": tests_passed,
            "validation_source_matches": validation_source_matches,
            "validation_source_fingerprint": validation.get("source_fingerprint"),
            "packed_source_fingerprint": current_source_fingerprint,
            "working_tree_clean": git_state.get("working_tree_clean"),
        },
        "pack_complete": pack_complete,
        "review_ready": review_ready,
        "generated_members": [
            "REVIEW.md", "review_manifest.json", "file_inventory.sha256",
            *sorted(generated_validation),
        ],
    }
    entries["review_manifest.json"] = _json_bytes(review_manifest)
    entries["REVIEW.md"] = _review_markdown(review_manifest, result).encode("utf-8")
    inventory_lines = [
        f"{_sha256(data)}  {member}" for member, data in sorted(entries.items())
    ]
    entries["file_inventory.sha256"] = ("\n".join(inventory_lines) + "\n").encode("ascii")

    for member, data in entries.items():
        _guard_portable(data, repo_root, member)
    output_dir = repo_root / REVIEW_PACK_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)
    pack_path = output_dir / (
        f"two_period_overlay_{experiment_id}_{run_id}_review_pack.zip"
    )
    temporary = pack_path.with_name(f".{pack_path.name}.tmp")
    try:
        with ZipFile(temporary, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
            for member in sorted(entries):
                info = ZipInfo(member, date_time=_FIXED_ZIP_TIME)
                info.compress_type = ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                info.create_system = 3
                archive.writestr(info, entries[member], compress_type=ZIP_DEFLATED, compresslevel=9)
        temporary.replace(pack_path)
    finally:
        temporary.unlink(missing_ok=True)
    return ReviewPackResult(
        path=pack_path,
        pack_complete=pack_complete,
        review_ready=review_ready,
        missing_artifacts=tuple(sorted(missing_artifacts)),
        missing_sources=tuple(sorted(missing_sources)),
    )


def write_review_pack_after_run(
    repo_root: Path,
    run_dir: Path,
    *,
    original_error: BaseException | None = None,
) -> ReviewPackResult | None:
    try:
        return write_review_pack(repo_root, run_dir)
    except Exception as pack_error:
        if original_error is None:
            raise
        note = f"automatic two-period review-pack generation failed: {pack_error}"
        add_note = getattr(original_error, "add_note", None)
        if callable(add_note):
            add_note(note)
        return None


__all__ = [
    "REVIEW_PACK_SCHEMA",
    "LOCAL_VALIDATION_SCHEMA",
    "ReviewPackResult",
    "write_local_validation_receipt",
    "write_review_pack",
    "write_review_pack_after_run",
]
