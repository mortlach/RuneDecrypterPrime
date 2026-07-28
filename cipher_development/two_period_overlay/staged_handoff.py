from __future__ import annotations

"""WP6 Pack 02B frozen-ladder staged handoff on the exact-extra-crib d8 surface.

This is deliberately a thin campaign runner over the existing affine search,
candidate archive, handoff, replay and review-pack contracts. It is not a new
solver framework.

The ladder is frozen from accepted Pack 01/02A aggregate evidence:

* scout: S2 WLI12;
* bridge: B1 char23 + WLI23;
* judge: F1 char1234 + WLI1234.

All search-visible stages and deterministic replay finish before terminal
benchmark metrics are opened. Earlier stage surfaces are persisted and the
final judge surface is the deduplicated union of all stage candidates, rescored
under F1, so later refinement cannot silently erase an earlier basin from the
evidence.
"""

import hashlib
import json
import math
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateProvenance,
    CandidateRecord,
    archive_content_hash,
    candidate_id_for,
    write_candidate_archive,
)
from cipher_development.shared.replay import (
    CandidateReplayContext,
    select_candidate_batch,
    write_candidate_batch,
    write_replay_context,
)
from cipher_development.shared.replay_binding import (
    CandidateReplayBinding,
    write_replay_binding,
)
from cipher_development.shared.replay_evidence import ReplayMode, write_candidate_replay
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import (
    BenchmarkSpec,
    EXACT_EXTRA_CRIB_BENCHMARKS,
    MASTER_SEED,
)
from cipher_development.two_period_overlay.keyspace import coordinate_search, expand
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import B1, F1, S2, ScorerProfile

STAGED_BENCHMARK = EXACT_EXTRA_CRIB_BENCHMARKS[0]
SCOUT_PROFILE = S2
BRIDGE_PROFILE = B1
JUDGE_PROFILE = F1
FROZEN_LADDER = (SCOUT_PROFILE, BRIDGE_PROFILE, JUDGE_PROFILE)

STAGED_RESTARTS = 96
STAGED_SEED_BLOCK = 21
STAGE_SWEEPS = {
    SCOUT_PROFILE.profile_id: 5,
    BRIDGE_PROFILE.profile_id: 4,
    JUDGE_PROFILE.profile_id: 3,
}
STAGE_SAFETY_SECONDS = 4.0 * 60.0 * 60.0
PROJECTION_START_COUNTS = (256, 512, 1024)
PROJECTION_SAFETY_FACTOR = 1.25
OVERNIGHT_SECONDS = 8.0 * 60.0 * 60.0

REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _numeric_summary(values: Sequence[int | float]) -> dict[str, float]:
    array = np.asarray(tuple(float(value) for value in values), dtype=np.float64)
    if array.size == 0:
        return {
            "minimum": 0.0,
            "q25": 0.0,
            "median": 0.0,
            "q75": 0.0,
            "maximum": 0.0,
            "mean": 0.0,
        }
    return {
        "minimum": float(np.min(array)),
        "q25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "q75": float(np.quantile(array, 0.75)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }

PACK01_STATIC_EXPERIMENT_ID = "multiscale_static_panel_v1"
PACK02A_SHELL_EXPERIMENT_ID = "multiscale_perturbation_shells_v1"
PACK02A_PILOT_EXPERIMENT_ID = "matched_d8_profile_pilot_v1"


@dataclass(frozen=True, slots=True)
class StageOutcome:
    stage_id: str
    profile: ScorerProfile
    sweeps_requested: int
    input_count: int
    archive: CandidateArchive
    attempt_rows: tuple[Mapping[str, Any], ...]
    generated_candidates: int
    unique_candidates: int
    duplicate_candidates: int
    evaluations: int
    elapsed_s: float

    def to_search_summary(self) -> dict[str, Any]:
        attempt_elapsed = [float(row["elapsed_s"]) for row in self.attempt_rows]
        attempt_rates = [
            float(row["candidate_evaluations_per_s"]) for row in self.attempt_rows
        ]
        score_gains = [float(row["score_gain"]) for row in self.attempt_rows]
        changed = sum(bool(row["candidate_changed"]) for row in self.attempt_rows)
        return {
            "stage_id": self.stage_id,
            "profile_id": self.profile.profile_id,
            "sweeps_requested": self.sweeps_requested,
            "input_count": self.input_count,
            "attempt_count": len(self.attempt_rows),
            "generated_candidates": self.generated_candidates,
            "unique_candidates": self.unique_candidates,
            "duplicate_candidates": self.duplicate_candidates,
            "duplicate_rate": (
                self.duplicate_candidates / self.generated_candidates
                if self.generated_candidates
                else 0.0
            ),
            "changed_candidate_count": changed,
            "unchanged_candidate_count": len(self.attempt_rows) - changed,
            "evaluations": self.evaluations,
            "elapsed_s": self.elapsed_s,
            "candidate_evaluations_per_s": self.evaluations / self.elapsed_s,
            "attempt_elapsed_s_summary": _numeric_summary(attempt_elapsed),
            "attempt_candidate_evaluations_per_s_summary": _numeric_summary(
                attempt_rates
            ),
            "score_gain_summary": _numeric_summary(score_gains),
            "archive_hash": archive_content_hash(self.archive),
        }


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            dict(payload),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _campaign_root(repo_root: Path) -> Path:
    return (repo_root.resolve() / "output/cipher_development/two_period_overlay").resolve()


def _safe_run_dir(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("run ID must be one directory name")
    root = _campaign_root(repo_root)
    path = (root / run_id).resolve()
    if root not in path.parents:
        raise ValueError("run ID escaped the campaign output root")
    return path


def latest_completed_experiment(repo_root: Path, experiment_id: str) -> Path:
    root = _campaign_root(repo_root)
    matches: list[Path] = []
    if not root.is_dir():
        raise FileNotFoundError("the two-period campaign output directory does not exist")
    for run_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        manifest_path = run_dir / "artifacts/experiment_manifest.json"
        result_path = run_dir / "artifacts/experiment_result.json"
        if not manifest_path.is_file() or not result_path.is_file():
            continue
        manifest = _read_json(manifest_path)
        result = _read_json(result_path)
        experiment = manifest.get("experiment")
        if not isinstance(experiment, Mapping):
            continue
        if (
            experiment.get("experiment_id") == experiment_id
            and result.get("experiment_id") == experiment_id
            and result.get("status") == "completed"
            and result.get("run_id") == run_dir.name
        ):
            matches.append(run_dir)
    if not matches:
        raise FileNotFoundError(f"no completed {experiment_id} run was found")
    return max(matches, key=lambda path: path.name)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be numeric")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name} must be finite")
    return out


def _freeze_ladder_evidence(repo_root: Path) -> dict[str, Any]:
    static_run = latest_completed_experiment(repo_root, PACK01_STATIC_EXPERIMENT_ID)
    shell_run = latest_completed_experiment(repo_root, PACK02A_SHELL_EXPERIMENT_ID)
    pilot_run = latest_completed_experiment(repo_root, PACK02A_PILOT_EXPERIMENT_ID)

    static_result_path = static_run / "artifacts/experiment_result.json"
    shell_result_path = shell_run / "artifacts/experiment_result.json"
    pilot_result_path = pilot_run / "artifacts/experiment_result.json"
    static_result = _read_json(static_result_path)
    shell_result = _read_json(shell_result_path)
    pilot_result = _read_json(pilot_result_path)

    shell_reference = shell_result.get("reference_evaluation")
    pilot_reference = pilot_result.get("reference_evaluation")
    if not isinstance(shell_reference, Mapping) or not isinstance(pilot_reference, Mapping):
        raise ValueError("Pack 02A evidence is missing terminal diagnostics")
    shell_profiles = shell_reference.get("profile_shell_diagnostics")
    pilot_profiles = pilot_reference.get("aggregate_dynamic_profile_diagnostics")
    if not isinstance(shell_profiles, Mapping) or not isinstance(pilot_profiles, Mapping):
        raise ValueError("Pack 02A evidence is missing profile diagnostics")

    def shell_metric(profile_id: str, metric: str) -> float:
        row = shell_profiles.get(profile_id)
        if not isinstance(row, Mapping):
            raise ValueError(f"shell evidence is missing {profile_id}")
        return _require_number(row.get(metric), f"{profile_id}.{metric}")

    def pilot_arm(profile_id: str) -> Mapping[str, Any]:
        profile_row = pilot_profiles.get(profile_id)
        if not isinstance(profile_row, Mapping):
            raise ValueError(f"pilot evidence is missing {profile_id}")
        arm = profile_row.get("calibrated_time")
        if not isinstance(arm, Mapping):
            raise ValueError(f"pilot evidence is missing {profile_id}/calibrated_time")
        return arm

    def pilot_summary(profile_id: str) -> Mapping[str, Any]:
        arm = pilot_arm(profile_id)
        summary = arm.get("archive_profile_diagnostic")
        if not isinstance(summary, Mapping):
            raise ValueError(f"pilot evidence is missing {profile_id} archive diagnostics")
        return summary

    def movement(profile_id: str) -> Mapping[str, Any]:
        arm = pilot_arm(profile_id)
        row = arm.get("matched_start_to_final")
        if not isinstance(row, Mapping):
            raise ValueError(f"pilot evidence is missing {profile_id} movement")
        return row

    s2_summary = pilot_summary(SCOUT_PROFILE.profile_id)
    b1_summary = pilot_summary(BRIDGE_PROFILE.profile_id)
    f1_summary = pilot_summary(JUDGE_PROFILE.profile_id)
    b1_move = movement(BRIDGE_PROFILE.profile_id)
    f1_move = movement(JUDGE_PROFILE.profile_id)

    checks = {
        "s2_shell_rune_spearman_at_least_0_95": (
            shell_metric(SCOUT_PROFILE.profile_id, "score_vs_rune_matches_spearman")
            >= 0.95
        ),
        "s2_shell_fully_monotonic": (
            int(shell_profiles[SCOUT_PROFILE.profile_id]["median_score_monotonic_steps_towards_truth"])
            == int(shell_profiles[SCOUT_PROFILE.profile_id]["median_score_monotonic_steps_total"])
        ),
        "s2_dynamic_median_at_least_289": (
            _require_number(s2_summary["rune_match_summary"]["median"], "s2 median")
            >= 289.0
        ),
        "s2_dynamic_best_ranked_first": int(s2_summary["best_rune_candidate_score_rank"]) == 1,
        "b1_shell_rune_spearman_at_least_0_95": (
            shell_metric(BRIDGE_PROFILE.profile_id, "score_vs_rune_matches_spearman")
            >= 0.95
        ),
        "b1_dynamic_improves_at_least_six_starts": int(b1_move["rune_improved_count"]) >= 6,
        "b1_dynamic_reaches_289": int(b1_summary["best_rune_matches"]) >= 289,
        "f1_shell_fully_monotonic": (
            int(shell_profiles[JUDGE_PROFILE.profile_id]["median_score_monotonic_steps_towards_truth"])
            == int(shell_profiles[JUDGE_PROFILE.profile_id]["median_score_monotonic_steps_total"])
        ),
        "f1_dynamic_median_at_least_289": (
            _require_number(f1_summary["rune_match_summary"]["median"], "f1 median")
            >= 289.0
        ),
        "f1_dynamic_best_ranked_first": int(f1_summary["best_rune_candidate_score_rank"]) == 1,
        "f1_dynamic_improves_at_least_six_starts": int(f1_move["rune_improved_count"]) >= 6,
    }
    if not all(checks.values()):
        failed = sorted(name for name, passed in checks.items() if not passed)
        raise RuntimeError(f"Pack 02A evidence does not satisfy ladder freeze: {failed}")

    return {
        "schema": "rdp.two_period_overlay.ladder_freeze.v1",
        "frozen": True,
        "scout": SCOUT_PROFILE.to_json_dict(),
        "bridge": BRIDGE_PROFILE.to_json_dict(),
        "judge": JUDGE_PROFILE.to_json_dict(),
        "checks": checks,
        "selection_rationale": {
            "scout": (
                "S2 had the strongest d16 shell rune correlation, full shell monotonicity, "
                "a 289-rune calibrated median, first-place ranking of the best dynamic "
                "candidate and no duplicates in the eight-start pilot."
            ),
            "bridge": (
                "B1 retained strong shell/ranking association and reached the 289-rune "
                "basin while improving seven of eight calibrated starts, but its poor "
                "median makes it a refinement bridge rather than a broad scout."
            ),
            "judge": (
                "F1 was fully monotonic on shells, reached a 289-rune median in both pilot "
                "arms and ranked its strongest retained candidate first. It is slower but "
                "is the best demonstrated final multiscale judge; J0/J1 are not selected."
            ),
        },
        "source_runs": {
            "static": {
                "run_id": static_run.name,
                "result_sha256": _sha256(static_result_path),
            },
            "shell": {
                "run_id": shell_run.name,
                "result_sha256": _sha256(shell_result_path),
            },
            "pilot": {
                "run_id": pilot_run.name,
                "result_sha256": _sha256(pilot_result_path),
            },
        },
    }


def stage_seed(stage_id: str, candidate_token: str) -> int:
    if not stage_id or not candidate_token:
        raise ValueError("stage_id and candidate_token must be non-empty")
    payload = f"{MASTER_SEED}:wp6-pack02b:{stage_id}:{candidate_token}".encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp6-02b").digest(),
        "big",
    )


def build_scout_starts(
    benchmark: BenchmarkSpec = STAGED_BENCHMARK,
    *,
    restarts: int = STAGED_RESTARTS,
    seed_block: int = STAGED_SEED_BLOCK,
    seed_factory: Callable[[str, str], int] = stage_seed,
) -> tuple[dict[str, Any], ...]:
    if restarts <= 0:
        raise ValueError("restarts must be positive")
    rows: list[dict[str, Any]] = []
    for restart_index in range(restarts):
        token = f"block-{seed_block}-restart-{restart_index}"
        seed = seed_factory("scout_start", token)
        rng = np.random.default_rng(seed)
        variables = rng.integers(
            0,
            benchmark.alphabet_size,
            size=benchmark.expected_free_dimension,
            dtype=np.uint8,
        )
        rows.append({
            "restart_index": restart_index,
            "seed": seed,
            "variables": variables.astype(int).tolist(),
        })
    return tuple(rows)


def _archive_policy(profile: ScorerProfile, capacity: int) -> ArchivePolicy:
    return ArchivePolicy(
        capacity=capacity,
        decision_score=profile.score_name,
        higher_is_better=True,
        family_limit=None,
    )


def _candidate_record(
    variables: np.ndarray,
    score: float,
    search_case: Any,
    profile: ScorerProfile,
    *,
    stage_id: str,
    evaluation_index: int,
    parent: CandidateRecord | None,
    details: Mapping[str, Any],
    benchmark: BenchmarkSpec = STAGED_BENCHMARK,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "coordinate_descent",
    family_id: str | None = None,
) -> CandidateRecord:
    values = np.asarray(variables, dtype=np.uint8)
    expanded = expand(
        values,
        search_case.particular,
        search_case.basis,
        benchmark,
    )
    identity = {"expanded_key": expanded.astype(int).tolist()}
    candidate_id = candidate_id_for(identity)
    inherited_scores = {} if parent is None else dict(parent.scores)
    inherited_scores[profile.score_name] = float(score)
    parent_id = None if parent is None else parent.candidate_id
    parent_ids = (
        (parent_id,)
        if parent_id is not None and parent_id != candidate_id
        else ()
    )
    provenance_details = {
        "stage_id": stage_id,
        "profile_id": profile.profile_id,
        "parent_candidate_id": parent_id,
        **dict(details),
    }
    return CandidateRecord(
        candidate_id=candidate_id,
        identity=identity,
        payload={
            "variables": values.astype(int).tolist(),
            "expanded_key": expanded.astype(int).tolist(),
            "benchmark_id": benchmark.benchmark_id,
        },
        scores=inherited_scores,
        provenance=CandidateProvenance(
            source=provenance_source,
            operation=provenance_operation,
            parent_ids=parent_ids,
            evaluation_index=evaluation_index,
            details=provenance_details,
        ),
        family_id=(parent.family_id if parent is not None else family_id),
    )


def _run_stage(
    *,
    stage_id: str,
    profile: ScorerProfile,
    search_case: Any,
    inputs: Sequence[CandidateRecord | Mapping[str, Any]],
    sweeps: int,
    benchmark: BenchmarkSpec = STAGED_BENCHMARK,
    seed_factory: Callable[[str, str], int] = stage_seed,
    archive_capacity: int | None = None,
    stage_safety_seconds: float = STAGE_SAFETY_SECONDS,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "coordinate_descent",
    family_id: str | None = None,
) -> StageOutcome:
    if not inputs:
        raise ValueError(f"{stage_id} inputs must not be empty")
    if sweeps <= 0:
        raise ValueError("sweeps must be positive")
    capacity = len(inputs) if archive_capacity is None else int(archive_capacity)
    if capacity <= 0:
        raise ValueError("archive_capacity must be positive")
    if stage_safety_seconds <= 0.0:
        raise ValueError("stage_safety_seconds must be positive")
    archive = CandidateArchive(_archive_policy(profile, capacity))
    attempt_rows: list[dict[str, Any]] = []
    generated_ids: set[str] = set()
    evaluations = 0
    stage_started = time.perf_counter()
    deadline = time.monotonic() + stage_safety_seconds

    for input_index, source in enumerate(inputs):
        if isinstance(source, CandidateRecord):
            parent = source
            start_variables = np.asarray(source.payload["variables"], dtype=np.uint8)
            token = source.candidate_id
            source_candidate_id = source.candidate_id
            source_label = "candidate"
        else:
            parent = None
            start_variables = np.asarray(source["variables"], dtype=np.uint8)
            token = f"restart-{int(source['restart_index'])}-seed-{int(source['seed'])}"
            source_candidate_id = None
            source_label = "deterministic_restart"

        seed = seed_factory(stage_id, token)
        rng = np.random.default_rng(seed)
        start_score = float(search_case.evaluate_variables(start_variables)[0])
        attempt_started = time.perf_counter()
        ending, final_score, used = coordinate_search(
            search_case.evaluate_variables,
            rng,
            start_variables,
            sweeps,
            deadline=deadline,
        )
        attempt_elapsed = time.perf_counter() - attempt_started
        attempt_evaluations = 1 + used  # separate start-score evidence + search calls
        evaluations += attempt_evaluations
        changed = not np.array_equal(start_variables, ending)
        record = _candidate_record(
            ending,
            final_score,
            search_case,
            profile,
            stage_id=stage_id,
            evaluation_index=evaluations,
            parent=parent,
            benchmark=benchmark,
            provenance_source=provenance_source,
            provenance_operation=provenance_operation,
            family_id=family_id,
            details={
                "input_index": input_index,
                "input_kind": source_label,
                "seed": seed,
                "starting_variables": start_variables.astype(int).tolist(),
                "ending_variables": ending.astype(int).tolist(),
                "start_score": start_score,
                "final_score": float(final_score),
                "score_gain": float(final_score - start_score),
                "sweeps_requested": sweeps,
                "evaluations_used": attempt_evaluations,
                "elapsed_s": attempt_elapsed,
                "candidate_evaluations_per_s": attempt_evaluations / attempt_elapsed,
                "candidate_changed": changed,
            },
        )
        generated_ids.add(record.candidate_id)
        offer = archive.offer(record)
        attempt_rows.append({
            "stage_id": stage_id,
            "profile_id": profile.profile_id,
            "input_index": input_index,
            "input_kind": source_label,
            "source_candidate_id": source_candidate_id,
            "seed": seed,
            "starting_variables": start_variables.astype(int).tolist(),
            "ending_variables": ending.astype(int).tolist(),
            "start_score": start_score,
            "final_score": float(final_score),
            "score_gain": float(final_score - start_score),
            "sweeps_requested": sweeps,
            "evaluations_used": attempt_evaluations,
            "elapsed_s": attempt_elapsed,
            "candidate_evaluations_per_s": attempt_evaluations / attempt_elapsed,
            "candidate_changed": changed,
            "candidate_id": record.candidate_id,
            "archive_offer_action": offer.action.value,
            "archive_retained": offer.retained,
        })

    elapsed = time.perf_counter() - stage_started
    return StageOutcome(
        stage_id=stage_id,
        profile=profile,
        sweeps_requested=sweeps,
        input_count=len(inputs),
        archive=archive,
        attempt_rows=tuple(attempt_rows),
        generated_candidates=len(attempt_rows),
        unique_candidates=len(generated_ids),
        duplicate_candidates=len(attempt_rows) - len(generated_ids),
        evaluations=evaluations,
        elapsed_s=elapsed,
    )


def _deduplicated_records(*surfaces: Sequence[CandidateRecord]) -> tuple[CandidateRecord, ...]:
    selected: dict[str, CandidateRecord] = {}
    for surface in surfaces:
        for record in surface:
            selected.setdefault(record.candidate_id, record)
    return tuple(selected[key] for key in sorted(selected))


def _first_stage_map(
    scout: Sequence[CandidateRecord],
    bridge: Sequence[CandidateRecord],
    judge: Sequence[CandidateRecord],
) -> dict[str, str]:
    result: dict[str, str] = {}
    for stage_id, records in (
        ("scout", scout),
        ("bridge", bridge),
        ("judge", judge),
    ):
        for record in records:
            result.setdefault(record.candidate_id, stage_id)
    return result


def _rescore_final_union(
    records: Sequence[CandidateRecord],
    search_case: Any,
    profile: ScorerProfile,
    first_stage: Mapping[str, str],
    *,
    archive_capacity: int | None = None,
    provenance_source: str = "staged_d8_handoff",
    provenance_operation: str = "final_judge_rescore",
) -> tuple[CandidateArchive, float, int]:
    capacity = len(records) if archive_capacity is None else int(archive_capacity)
    if capacity <= 0:
        raise ValueError("archive_capacity must be positive")
    archive = CandidateArchive(_archive_policy(profile, capacity))
    started = time.perf_counter()
    evaluations = 0
    for index, source in enumerate(records):
        variables = np.asarray(source.payload["variables"], dtype=np.uint8)
        score = float(search_case.evaluate_variables(variables)[0])
        evaluations += 1
        merged_scores = dict(source.scores)
        merged_scores[profile.score_name] = score
        archive.offer(CandidateRecord(
            candidate_id=source.candidate_id,
            identity=source.identity,
            payload=source.payload,
            scores=merged_scores,
            provenance=CandidateProvenance(
                source=provenance_source,
                operation=provenance_operation,
                parent_ids=(),
                evaluation_index=index + 1,
                details={
                    "profile_id": profile.profile_id,
                    "first_stage": first_stage[source.candidate_id],
                    "source_candidate_id": source.candidate_id,
                },
            ),
            family_id=source.family_id,
        ))
    return archive, time.perf_counter() - started, evaluations


def _write_stage_and_replay(
    *,
    run_dir: Path,
    run: Any,
    stage: StageOutcome,
    search_case: Any,
    evaluator_provenance: Mapping[str, Any],
    artifact_root: Path = Path("artifacts/staged_d8_handoff"),
    experiment_id: str = "staged_d8_handoff_v1",
    benchmark: BenchmarkSpec = STAGED_BENCHMARK,
    selection_purpose: str = "handoff",
    selection_label: str | None = None,
    evaluator_id: str | None = None,
) -> dict[str, Any]:
    from cipher_development.two_period_overlay.replay import (
        build_replay_evaluator,
        make_replay_context,
    )

    root = artifact_root / stage.stage_id
    archive_rel = root / "candidate_archive.json"
    attempts_rel = root / "attempts.json"
    batch_rel = root / "handoff_batch.json"
    context_rel = root / "replay_context.json"
    binding_rel = root / "replay_binding.json"
    replay_rel = root / "replay_evidence.json"

    write_candidate_archive(run_dir / archive_rel, stage.archive)
    _write_json(run_dir / attempts_rel, {
        "schema": "rdp.two_period_overlay.staged_attempts.v1",
        "stage_id": stage.stage_id,
        "profile_id": stage.profile.profile_id,
        "rows": list(stage.attempt_rows),
    })
    batch = select_candidate_batch(
        stage.archive,
        purpose=selection_purpose,
        selection_label=selection_label or f"{stage.stage_id}__all",
        candidate_ids=tuple(record.candidate_id for record in stage.archive.records),
    )
    write_candidate_batch(run_dir / batch_rel, batch)
    context: CandidateReplayContext = make_replay_context(
        search_case,
        run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        evaluator_provenance=evaluator_provenance,
        scoring_contract=stage.profile.scoring_contract(),
        decision_score=stage.profile.score_name,
        evaluator_id=(
            evaluator_id
            or f"two_period_overlay_{stage.stage_id}_{stage.profile.profile_id}_v1"
        ),
    )
    write_replay_context(run_dir / context_rel, context)
    binding = CandidateReplayBinding.create(
        campaign_id="two_period_overlay",
        source_run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        benchmark_id=benchmark.benchmark_id,
        context=context,
        batch=batch,
        context_artifact=context_rel.as_posix(),
        batch_artifact=batch_rel.as_posix(),
    )
    write_replay_binding(run_dir / binding_rel, binding)
    replay = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=build_replay_evaluator(context),
        mode=ReplayMode.VERIFY,
        decision_score=stage.profile.score_name,
        higher_is_better=True,
        evaluator_configuration={
            "experiment": experiment_id,
            "stage_id": stage.stage_id,
            "profile": stage.profile.to_json_dict(),
            "evaluator_provenance": dict(evaluator_provenance),
        },
        repeat_count=REPLAY_REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    write_candidate_replay(run_dir / replay_rel, replay)
    return {
        **stage.to_search_summary(),
        "replay_deterministic": replay.deterministic,
        "replay_stored_scores_verified": replay.stored_scores_verified,
        "artifacts": {
            "archive": archive_rel.as_posix(),
            "attempts": attempts_rel.as_posix(),
            "batch": batch_rel.as_posix(),
            "context": context_rel.as_posix(),
            "binding": binding_rel.as_posix(),
            "replay": replay_rel.as_posix(),
        },
    }


def _write_final_union_and_replay(
    *,
    run_dir: Path,
    run: Any,
    archive: CandidateArchive,
    search_case: Any,
    profile: ScorerProfile,
    evaluator_provenance: Mapping[str, Any],
    artifact_root: Path = Path("artifacts/staged_d8_handoff"),
    experiment_id: str = "staged_d8_handoff_v1",
    benchmark: BenchmarkSpec = STAGED_BENCHMARK,
    selection_label: str = "final_union__all",
    evaluator_id: str = "two_period_overlay_final_union_f1_v1",
) -> dict[str, Any]:
    from cipher_development.two_period_overlay.replay import (
        build_replay_evaluator,
        make_replay_context,
    )

    root = artifact_root / "final_union"
    archive_rel = root / "candidate_archive.json"
    batch_rel = root / "replay_batch.json"
    context_rel = root / "replay_context.json"
    binding_rel = root / "replay_binding.json"
    replay_rel = root / "replay_evidence.json"
    write_candidate_archive(run_dir / archive_rel, archive)
    batch = select_candidate_batch(
        archive,
        purpose="replay",
        selection_label=selection_label,
        candidate_ids=tuple(record.candidate_id for record in archive.records),
    )
    write_candidate_batch(run_dir / batch_rel, batch)
    context = make_replay_context(
        search_case,
        run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        evaluator_provenance=evaluator_provenance,
        scoring_contract=profile.scoring_contract(),
        decision_score=profile.score_name,
        evaluator_id=evaluator_id,
    )
    write_replay_context(run_dir / context_rel, context)
    binding = CandidateReplayBinding.create(
        campaign_id="two_period_overlay",
        source_run_id=run_dir.name,
        configuration_hash=run.configuration_hash,
        benchmark_id=benchmark.benchmark_id,
        context=context,
        batch=batch,
        context_artifact=context_rel.as_posix(),
        batch_artifact=batch_rel.as_posix(),
    )
    write_replay_binding(run_dir / binding_rel, binding)
    replay = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=build_replay_evaluator(context),
        mode=ReplayMode.VERIFY,
        decision_score=profile.score_name,
        higher_is_better=True,
        evaluator_configuration={
            "experiment": experiment_id,
            "stage_id": "final_union",
            "profile": profile.to_json_dict(),
            "evaluator_provenance": dict(evaluator_provenance),
        },
        repeat_count=REPLAY_REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    write_candidate_replay(run_dir / replay_rel, replay)
    return {
        "candidate_count": len(archive.records),
        "archive_hash": archive_content_hash(archive),
        "replay_deterministic": replay.deterministic,
        "replay_stored_scores_verified": replay.stored_scores_verified,
        "artifacts": {
            "archive": archive_rel.as_posix(),
            "batch": batch_rel.as_posix(),
            "context": context_rel.as_posix(),
            "binding": binding_rel.as_posix(),
            "replay": replay_rel.as_posix(),
        },
    }


def _stage_terminal_summary(
    records: Sequence[CandidateRecord],
    profile: ScorerProfile,
    search_case: Any,
    reference: Any,
) -> dict[str, Any]:
    from cipher_development.two_period_overlay.multiscale import aggregate_profile_diagnostic

    candidate_ids = [record.candidate_id for record in records]
    scores = [float(record.scores[profile.score_name]) for record in records]
    true_variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns],
        dtype=np.uint8,
    )
    terminal_rows: list[dict[str, Any]] = []
    for record in records:
        variables = np.asarray(record.payload["variables"], dtype=np.uint8)
        row = reference_metrics(
            reference,
            variables,
            search_case.particular,
            search_case.basis,
        )
        row["affine_variable_matches"] = int(np.count_nonzero(variables == true_variables))
        terminal_rows.append(row)
    return aggregate_profile_diagnostic(candidate_ids, scores, terminal_rows)


def _attempt_terminal_movement(
    stage: StageOutcome,
    search_case: Any,
    reference: Any,
) -> dict[str, Any]:
    true_variables = np.asarray(
        [reference.true_key[index] for index in search_case.free_columns],
        dtype=np.uint8,
    )
    rows: list[dict[str, int]] = []
    for attempt in stage.attempt_rows:
        start = np.asarray(attempt["starting_variables"], dtype=np.uint8)
        final = np.asarray(attempt["ending_variables"], dtype=np.uint8)
        start_metrics = reference_metrics(
            reference, start, search_case.particular, search_case.basis
        )
        final_metrics = reference_metrics(
            reference, final, search_case.particular, search_case.basis
        )
        rows.append({
            "rune_improvement": int(final_metrics["rune_matches"]) - int(start_metrics["rune_matches"]),
            "complete_word_improvement": (
                int(final_metrics["complete_word_matches"])
                - int(start_metrics["complete_word_matches"])
            ),
            "affine_variable_improvement": (
                int(np.count_nonzero(final == true_variables))
                - int(np.count_nonzero(start == true_variables))
            ),
        })
    return {
        "attempt_count": len(rows),
        "rune_improved_count": sum(row["rune_improvement"] > 0 for row in rows),
        "rune_worsened_count": sum(row["rune_improvement"] < 0 for row in rows),
        "rune_improvement_summary": _numeric_summary(
            [row["rune_improvement"] for row in rows]
        ),
        "complete_word_improved_count": sum(
            row["complete_word_improvement"] > 0 for row in rows
        ),
        "complete_word_worsened_count": sum(
            row["complete_word_improvement"] < 0 for row in rows
        ),
        "complete_word_improvement_summary": _numeric_summary(
            [row["complete_word_improvement"] for row in rows]
        ),
        "affine_variable_improved_count": sum(
            row["affine_variable_improvement"] > 0 for row in rows
        ),
        "affine_variable_worsened_count": sum(
            row["affine_variable_improvement"] < 0 for row in rows
        ),
        "affine_variable_improvement_summary": _numeric_summary(
            [row["affine_variable_improvement"] for row in rows]
        ),
    }


def _runtime_projection(
    *,
    scout: StageOutcome,
    bridge: StageOutcome,
    judge: StageOutcome,
    final_union_count: int,
    final_rescore_elapsed_s: float,
) -> dict[str, Any]:
    scout_per_start = scout.elapsed_s / scout.input_count
    bridge_per_input = bridge.elapsed_s / bridge.input_count
    judge_per_input = judge.elapsed_s / judge.input_count
    bridge_ratio = bridge.input_count / scout.input_count
    judge_ratio = judge.input_count / scout.input_count
    final_ratio = final_union_count / scout.input_count
    final_rescore_per_candidate = (
        final_rescore_elapsed_s / final_union_count if final_union_count else 0.0
    )
    seconds_per_start = (
        scout_per_start
        + bridge_ratio * bridge_per_input
        + judge_ratio * judge_per_input
        + final_ratio * final_rescore_per_candidate
    )
    if seconds_per_start <= 0.0:
        raise RuntimeError("runtime projection received non-positive measured cost")

    projections: dict[str, Any] = {}
    for starts in PROJECTION_START_COUNTS:
        central = seconds_per_start * starts
        projections[str(starts)] = {
            "scout_starts": starts,
            "central_elapsed_s": central,
            "safety_adjusted_elapsed_s": central * PROJECTION_SAFETY_FACTOR,
        }
    overnight_starts = max(
        1,
        int(math.floor(OVERNIGHT_SECONDS / (seconds_per_start * PROJECTION_SAFETY_FACTOR))),
    )
    return {
        "schema": "rdp.two_period_overlay.runtime_projection.v1",
        "basis": "linear empirical projection from the completed Pack 02B staged run",
        "warning": (
            "This is a planning estimate, not a timing guarantee. Candidate deduplication, "
            "cache state and later archive selection can change scaling."
        ),
        "measured": {
            "scout_starts": scout.input_count,
            "scout_seconds_per_start": scout_per_start,
            "bridge_input_ratio_per_scout_start": bridge_ratio,
            "bridge_seconds_per_input": bridge_per_input,
            "judge_input_ratio_per_scout_start": judge_ratio,
            "judge_seconds_per_input": judge_per_input,
            "final_union_ratio_per_scout_start": final_ratio,
            "final_rescore_seconds_per_candidate": final_rescore_per_candidate,
            "central_seconds_per_scout_start": seconds_per_start,
        },
        "safety_factor": PROJECTION_SAFETY_FACTOR,
        "projected_panels": projections,
        "overnight_8h": {
            "available_seconds": OVERNIGHT_SECONDS,
            "projected_scout_starts_with_safety_factor": overnight_starts,
            "projected_elapsed_s": (
                overnight_starts * seconds_per_start * PROJECTION_SAFETY_FACTOR
            ),
            "authorised_by_this_experiment": False,
        },
    }


def run_staged_d8_handoff(repo_root: Path) -> Path:
    from cipher_development.shared.replay_provenance import build_evaluator_provenance
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    repo_root = repo_root.resolve()
    experiment_started_at_utc = _utc_now_iso()
    experiment_started = time.perf_counter()
    ladder_freeze = _freeze_ladder_evidence(repo_root)

    max_scout_evals = STAGED_RESTARTS * (
        2
        + STAGE_SWEEPS[SCOUT_PROFILE.profile_id]
        * STAGED_BENCHMARK.expected_free_dimension
        * STAGED_BENCHMARK.alphabet_size
    )
    max_bridge_evals = STAGED_RESTARTS * (
        2
        + STAGE_SWEEPS[BRIDGE_PROFILE.profile_id]
        * STAGED_BENCHMARK.expected_free_dimension
        * STAGED_BENCHMARK.alphabet_size
    )
    max_judge_inputs = STAGED_RESTARTS * 2
    max_judge_evals = max_judge_inputs * (
        2
        + STAGE_SWEEPS[JUDGE_PROFILE.profile_id]
        * STAGED_BENCHMARK.expected_free_dimension
        * STAGED_BENCHMARK.alphabet_size
    )
    max_final_union = STAGED_RESTARTS * 4
    max_replay = (
        STAGED_RESTARTS + STAGED_RESTARTS + max_judge_inputs + max_final_union
    ) * REPLAY_REPEAT_COUNT
    max_terminal = STAGED_RESTARTS + STAGED_RESTARTS + max_judge_inputs + max_final_union
    evaluation_budget_upper = (
        max_scout_evals
        + max_bridge_evals
        + max_judge_evals
        + max_final_union
        + max_replay
        + max_terminal
    )

    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="staged_d8_handoff_v1",
        benchmark_id=STAGED_BENCHMARK.benchmark_id,
        question=(
            "Does the frozen S2 to B1 to F1 ladder preserve and promote useful "
            "candidate basins on the exact-extra-crib P13/P17 d8 surface?"
        ),
        hypothesis=(
            "S2 supplies a broad near-truth pool, B1 supplies a distinct medium-order "
            "refinement surface, and F1 can judge the union without silently losing the "
            "best earlier-stage candidate."
        ),
        alternative=(
            "The bridge or judge destroys useful earlier candidates, the final union does "
            "not improve over the scout, or measured scaling makes a longer panel unjustified."
        ),
        decision_rule=(
            "This handoff validation always refines. Proceed to the standard Experiment A "
            "panel only when every stage and final union replay deterministically, all prior "
            "candidate surfaces remain persisted, and timing evidence supports a declared "
            "longer budget. This run does not authorise an overnight panel."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_evaluations=evaluation_budget_upper,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "benchmark": STAGED_BENCHMARK.to_json_dict(),
        "ladder": [profile.to_json_dict() for profile in FROZEN_LADDER],
        "ladder_freeze": ladder_freeze,
        "scout_restarts": STAGED_RESTARTS,
        "seed_block": STAGED_SEED_BLOCK,
        "stage_sweeps": dict(STAGE_SWEEPS),
        "handoff_policy": {
            "scout_to_bridge": "all unique scout candidates",
            "judge_inputs": "deduplicated union of scout and bridge candidates",
            "final_union": "deduplicated scout, bridge and judge surfaces rescored by F1",
            "single_candidate_collapse_allowed": False,
        },
        "terminal_metrics_opened_only_after_all_search_and_replay": True,
        "overnight_authorised": False,
        "evaluation_budget_upper_bound": evaluation_budget_upper,
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=tuple(
                    profile.scoring_contract() for profile in FROZEN_LADDER
                ),
                require_assets=True,
            )
            _write_json(run_dir / "artifacts/staged_d8_handoff/ladder_freeze.json", ladder_freeze)
            for label, experiment_id in (
                ("source_static", PACK01_STATIC_EXPERIMENT_ID),
                ("source_shell", PACK02A_SHELL_EXPERIMENT_ID),
                ("source_pilot", PACK02A_PILOT_EXPERIMENT_ID),
            ):
                source_run = latest_completed_experiment(repo_root, experiment_id)
                shutil.copyfile(
                    source_run / "artifacts/experiment_result.json",
                    run_dir / f"artifacts/staged_d8_handoff/{label}_experiment_result.json",
                )

            starts = build_scout_starts()
            _write_json(run_dir / "artifacts/staged_d8_handoff/scout_starts.json", {
                "schema": "rdp.two_period_overlay.staged_scout_starts.v1",
                "benchmark_id": STAGED_BENCHMARK.benchmark_id,
                "seed_block": STAGED_SEED_BLOCK,
                "rows": list(starts),
            })

            # Build all scorer surfaces before terminal metrics are opened.
            scout_case, reference = build_rdp_case(
                STAGED_BENCHMARK,
                scoring_contract=SCOUT_PROFILE.scoring_contract(),
            )
            bridge_case, _ = build_rdp_case(
                STAGED_BENCHMARK,
                scoring_contract=BRIDGE_PROFILE.scoring_contract(),
            )
            judge_case, _ = build_rdp_case(
                STAGED_BENCHMARK,
                scoring_contract=JUDGE_PROFILE.scoring_contract(),
            )

            search_started = time.perf_counter()
            scout = _run_stage(
                stage_id="scout",
                profile=SCOUT_PROFILE,
                search_case=scout_case,
                inputs=starts,
                sweeps=STAGE_SWEEPS[SCOUT_PROFILE.profile_id],
            )
            bridge = _run_stage(
                stage_id="bridge",
                profile=BRIDGE_PROFILE,
                search_case=bridge_case,
                inputs=scout.archive.records,
                sweeps=STAGE_SWEEPS[BRIDGE_PROFILE.profile_id],
            )
            judge_inputs = _deduplicated_records(
                scout.archive.records,
                bridge.archive.records,
            )
            judge = _run_stage(
                stage_id="judge",
                profile=JUDGE_PROFILE,
                search_case=judge_case,
                inputs=judge_inputs,
                sweeps=STAGE_SWEEPS[JUDGE_PROFILE.profile_id],
            )
            search_elapsed = time.perf_counter() - search_started

            first_stage = _first_stage_map(
                scout.archive.records,
                bridge.archive.records,
                judge.archive.records,
            )
            all_stage_records = _deduplicated_records(
                scout.archive.records,
                bridge.archive.records,
                judge.archive.records,
            )
            final_archive, final_rescore_elapsed, final_rescore_evals = _rescore_final_union(
                all_stage_records,
                judge_case,
                JUDGE_PROFILE,
                first_stage,
            )

            # Persist and replay every stage before terminal benchmark metrics.
            replay_started = time.perf_counter()
            scout_summary = _write_stage_and_replay(
                run_dir=run_dir,
                run=run,
                stage=scout,
                search_case=scout_case,
                evaluator_provenance=provenance,
            )
            bridge_summary = _write_stage_and_replay(
                run_dir=run_dir,
                run=run,
                stage=bridge,
                search_case=bridge_case,
                evaluator_provenance=provenance,
            )
            judge_summary = _write_stage_and_replay(
                run_dir=run_dir,
                run=run,
                stage=judge,
                search_case=judge_case,
                evaluator_provenance=provenance,
            )
            final_summary = _write_final_union_and_replay(
                run_dir=run_dir,
                run=run,
                archive=final_archive,
                search_case=judge_case,
                profile=JUDGE_PROFILE,
                evaluator_provenance=provenance,
            )
            replay_elapsed = time.perf_counter() - replay_started
            all_replays_deterministic = all(
                bool(row["replay_deterministic"])
                and bool(row["replay_stored_scores_verified"])
                for row in (scout_summary, bridge_summary, judge_summary, final_summary)
            )
            if not all_replays_deterministic:
                raise RuntimeError("staged handoff replay verification failed")

            attempt_rows = [
                *scout.attempt_rows,
                *bridge.attempt_rows,
                *judge.attempt_rows,
            ]
            _write_json(run_dir / "artifacts/staged_d8_handoff/attempt_timing.json", {
                "schema": "rdp.two_period_overlay.staged_attempt_timing.v1",
                "rows": attempt_rows,
            })
            runtime_projection = _runtime_projection(
                scout=scout,
                bridge=bridge,
                judge=judge,
                final_union_count=len(final_archive.records),
                final_rescore_elapsed_s=final_rescore_elapsed,
            )
            _write_json(
                run_dir / "artifacts/staged_d8_handoff/runtime_projection.json",
                runtime_projection,
            )

            # Terminal-only block begins here, after all search, persistence and replay.
            terminal_started = time.perf_counter()
            stage_terminal = {
                "scout": {
                    "archive": _stage_terminal_summary(
                        scout.archive.records, SCOUT_PROFILE, scout_case, reference
                    ),
                    "movement": _attempt_terminal_movement(scout, scout_case, reference),
                },
                "bridge": {
                    "archive": _stage_terminal_summary(
                        bridge.archive.records, BRIDGE_PROFILE, bridge_case, reference
                    ),
                    "movement": _attempt_terminal_movement(bridge, bridge_case, reference),
                },
                "judge": {
                    "archive": _stage_terminal_summary(
                        judge.archive.records, JUDGE_PROFILE, judge_case, reference
                    ),
                    "movement": _attempt_terminal_movement(judge, judge_case, reference),
                },
                "final_union": {
                    "archive": _stage_terminal_summary(
                        final_archive.records, JUDGE_PROFILE, judge_case, reference
                    ),
                },
            }
            best_final = final_archive.records[0]
            best_variables = np.asarray(best_final.payload["variables"], dtype=np.uint8)
            best_terminal = reference_metrics(
                reference,
                best_variables,
                judge_case.particular,
                judge_case.basis,
            )
            best_terminal.update({
                "candidate_id": best_final.candidate_id,
                "first_stage": first_stage[best_final.candidate_id],
                "final_score_rank": 1,
            })
            stage_presence = {
                stage_id: (
                    next(
                        (
                            index + 1
                            for index, record in enumerate(records)
                            if record.candidate_id == best_final.candidate_id
                        ),
                        None,
                    )
                )
                for stage_id, records in (
                    ("scout", scout.archive.records),
                    ("bridge", bridge.archive.records),
                    ("judge", judge.archive.records),
                    ("final_union", final_archive.records),
                )
            }
            terminal_elapsed = time.perf_counter() - terminal_started

            finished_at_utc = _utc_now_iso()
            timing = {
                "schema": "rdp.two_period_overlay.staged_execution_timing.v1",
                "started_at_utc": experiment_started_at_utc,
                "finished_at_utc": finished_at_utc,
                "scientific_work_elapsed_s": time.perf_counter() - experiment_started,
                "scope": "Frozen-ladder search, persistence, replay and terminal diagnostics.",
                "phases": {
                    "search_elapsed_s": search_elapsed,
                    "final_union_rescore_elapsed_s": final_rescore_elapsed,
                    "replay_elapsed_s": replay_elapsed,
                    "terminal_diagnostics_elapsed_s": terminal_elapsed,
                },
                "profiles": {
                    "scout": scout_summary,
                    "bridge": bridge_summary,
                    "judge": judge_summary,
                },
                "attempt_timing_artifact": "artifacts/staged_d8_handoff/attempt_timing.json",
            }
            _write_json(run_dir / "artifacts/execution_timing.json", timing)
            summary_artifact = {
                "schema": "rdp.two_period_overlay.staged_d8_handoff_summary.v1",
                "benchmark_id": STAGED_BENCHMARK.benchmark_id,
                "ladder_freeze": ladder_freeze,
                "stages": {
                    "scout": scout_summary,
                    "bridge": bridge_summary,
                    "judge": judge_summary,
                },
                "final_union": {
                    **final_summary,
                    "rescore_elapsed_s": final_rescore_elapsed,
                    "rescore_evaluations": final_rescore_evals,
                },
                "all_replays_deterministic": all_replays_deterministic,
                "all_prior_surfaces_persisted": True,
                "terminal_metrics_opened_only_after_all_search_and_replay": True,
                "runtime_projection": runtime_projection,
                "timing": timing,
            }
            _write_json(
                run_dir / "artifacts/staged_d8_handoff_summary.json",
                summary_artifact,
            )
            result_path = run.finish(
                decision=ExperimentDecision.REFINE,
                stop_reason="done",
                result_summary={
                    "artifact": "artifacts/staged_d8_handoff_summary.json",
                    "ladder_frozen": True,
                    "ladder_profile_ids": [
                        profile.profile_id for profile in FROZEN_LADDER
                    ],
                    "scout_restarts": STAGED_RESTARTS,
                    "stage_input_counts": {
                        "scout": scout.input_count,
                        "bridge": bridge.input_count,
                        "judge": judge.input_count,
                    },
                    "stage_unique_candidate_counts": {
                        "scout": scout.unique_candidates,
                        "bridge": bridge.unique_candidates,
                        "judge": judge.unique_candidates,
                        "final_union": len(final_archive.records),
                    },
                    "all_replays_deterministic": all_replays_deterministic,
                    "all_prior_surfaces_persisted": True,
                    "overnight_authorised": False,
                    "runtime_projection_artifact": (
                        "artifacts/staged_d8_handoff/runtime_projection.json"
                    ),
                    "timing": timing,
                },
                reference_evaluation={
                    "candidate_specific_truth_emitted": True,
                    "stage_terminal_diagnostics": stage_terminal,
                    "best_final_candidate_terminal": best_terminal,
                    "best_final_candidate_stage_score_ranks": stage_presence,
                },
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


__all__ = [
    "BRIDGE_PROFILE",
    "FROZEN_LADDER",
    "JUDGE_PROFILE",
    "PROJECTION_SAFETY_FACTOR",
    "SCOUT_PROFILE",
    "STAGED_BENCHMARK",
    "STAGED_RESTARTS",
    "STAGE_SWEEPS",
    "StageOutcome",
    "build_scout_starts",
    "latest_completed_experiment",
    "run_staged_d8_handoff",
    "stage_seed",
]
