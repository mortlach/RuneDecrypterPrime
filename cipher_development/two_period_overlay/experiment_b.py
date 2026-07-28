from __future__ import annotations

"""WP6 Experiment B candidate-word branch scaling.

Each valid distinct eight-rune word defines its own d8 affine branch.  Every
branch receives the same S2 scout starts and budget.  A global score-based pool
then continues through B1 and F1 without one-candidate-per-branch quotas.
Search, persistence and replay finish before terminal branch identity is opened.
"""

import hashlib
import json
import math
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import (
    ArchivePolicy,
    CandidateArchive,
    CandidateRecord,
    archive_content_hash,
    write_candidate_archive,
)
from cipher_development.two_period_overlay.benchmark import build_rdp_case
from cipher_development.two_period_overlay.candidate_words import (
    CandidateWord,
    benchmark_for_candidate,
    build_nested_candidate_lists,
)
from cipher_development.two_period_overlay.config import DORMOUSE_RUNES, MASTER_SEED
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import B1, F1, S2
from cipher_development.two_period_overlay.staged_handoff import (
    _attempt_terminal_movement,
    _deduplicated_records,
    _first_stage_map,
    _rescore_final_union,
    _run_stage,
    _stage_terminal_summary,
    _write_final_union_and_replay,
    _write_stage_and_replay,
    latest_completed_experiment,
)

B10_EXPERIMENT_ID = "candidate_word_branches_b10_v1"
B100_EXPERIMENT_ID = "candidate_word_branches_b100_v1"
B1000_EXPERIMENT_ID = "candidate_word_branches_b1000_v1"
SUPPORTED_LIST_SIZES = (10, 100, 1000)

STARTS_PER_BRANCH = 160
B1000_STARTS_PER_BRANCH = 8
SCOUT_ARCHIVE_PER_BRANCH = 8
GLOBAL_SCOUT_CAPACITY_PER_BRANCH = 4
B1000_GLOBAL_SCOUT_CAPACITY = 400
SCOUT_SWEEPS = 5
BRIDGE_SWEEPS = 4
JUDGE_SWEEPS = 3
PROJECTION_SAFETY_FACTOR = 1.20
OVERNIGHT_SECONDS = 8.0 * 60.0 * 60.0
EXPERIMENT_CEILING_SECONDS = {
    10: 2.0 * 60.0 * 60.0,
    100: 8.0 * 60.0 * 60.0,
    1000: 8.0 * 60.0 * 60.0,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _experiment_id(list_size: int) -> str:
    if list_size == 10:
        return B10_EXPERIMENT_ID
    if list_size == 100:
        return B100_EXPERIMENT_ID
    if list_size == 1000:
        return B1000_EXPERIMENT_ID
    raise ValueError("list_size must be 10, 100 or 1000")


def _source_experiment_a(repo_root: Path) -> dict[str, Any]:
    run_dir = latest_completed_experiment(repo_root, "experiment_a_standard_panel_v1")
    result_path = run_dir / "artifacts/experiment_result.json"
    result = _read_json(result_path)
    summary = result.get("result_summary")
    summary = summary if isinstance(summary, Mapping) else {}
    if result.get("decision") != "promote" or summary.get("promotion_gate_passed") is not True:
        raise RuntimeError("Experiment A has not passed its promotion gate")
    return {
        "run_id": run_dir.name,
        "result_sha256": _sha256(result_path),
        "decision": str(result.get("decision")),
        "promotion_gate_passed": True,
    }


def _source_b1000_gate(repo_root: Path) -> dict[str, Any]:
    run_dir = latest_completed_experiment(repo_root, "b100_scout_budget_sensitivity_v1")
    result_path = run_dir / "artifacts/experiment_result.json"
    result = _read_json(result_path)
    summary = result.get("result_summary")
    summary = summary if isinstance(summary, Mapping) else {}
    if result.get("decision") != "promote" or summary.get("b1000_gate_passed") is not True:
        raise RuntimeError("B1000 has not passed the compressed-budget progression gate")
    return {
        "run_id": run_dir.name,
        "result_sha256": _sha256(result_path),
        "decision": str(result.get("decision")),
        "b1000_gate_passed": True,
    }


def build_branch_starts(count: int = STARTS_PER_BRANCH) -> tuple[dict[str, Any], ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    rows: list[dict[str, Any]] = []
    for restart_index in range(count):
        payload = f"{MASTER_SEED}:candidate-branches:{restart_index}".encode("ascii")
        seed = int.from_bytes(
            hashlib.blake2b(payload, digest_size=8, person=b"rdp-bstart-v1").digest(),
            "big",
        )
        rng = np.random.default_rng(seed)
        rows.append({
            "restart_index": restart_index,
            "seed": seed,
            "variables": rng.integers(0, 29, size=8, dtype=np.uint8).astype(int).tolist(),
        })
    return tuple(rows)


def _group(records: Sequence[CandidateRecord]) -> dict[str, tuple[CandidateRecord, ...]]:
    grouped: dict[str, list[CandidateRecord]] = defaultdict(list)
    for record in records:
        if record.family_id is None:
            raise RuntimeError("candidate branch family_id was not preserved")
        grouped[record.family_id].append(record)
    return {key: tuple(value) for key, value in grouped.items()}


def _branch_best(records: Sequence[CandidateRecord], score_name: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for record in records:
        if record.family_id is None:
            raise RuntimeError("candidate branch family_id was not preserved")
        score = float(record.scores[score_name])
        result[record.family_id] = max(score, result.get(record.family_id, -math.inf))
    return result


def _branch_ranking(best_scores: Mapping[str, float]) -> list[dict[str, Any]]:
    ordered = sorted(best_scores.items(), key=lambda item: (-float(item[1]), item[0]))
    return [
        {"rank": index + 1, "branch_id": branch_id, "best_score": float(score)}
        for index, (branch_id, score) in enumerate(ordered)
    ]


def _rank_for(ranking: Sequence[Mapping[str, Any]], branch_id: str) -> int | None:
    for row in ranking:
        if row.get("branch_id") == branch_id:
            return int(row["rank"])
    return None


def _selection_archive(records: Sequence[CandidateRecord], capacity: int) -> CandidateArchive:
    archive = CandidateArchive(ArchivePolicy(
        capacity=capacity,
        decision_score=S2.score_name,
        higher_is_better=True,
        family_limit=None,
    ))
    for record in records:
        archive.offer(record)
    return archive


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0.0:
        raise TimeoutError("candidate-branch experiment reached its wall-clock ceiling")
    return remaining


def _candidate_lookup(candidates: Sequence[CandidateWord]) -> dict[str, CandidateWord]:
    return {candidate.branch_id: candidate for candidate in candidates}


def _persist_global_selection(
    run_dir: Path,
    archive: CandidateArchive,
    full_records: Sequence[CandidateRecord],
) -> tuple[Path, Path]:
    archive_rel = Path("artifacts/experiment_b/shared/scout_selection_archive.json")
    summary_rel = Path("artifacts/experiment_b/shared/scout_selection_summary.json")
    write_candidate_archive(run_dir / archive_rel, archive)
    full_families = {record.family_id for record in full_records}
    selected_families = {record.family_id for record in archive.records}
    _write_json(run_dir / summary_rel, {
        "schema": "rdp.two_period_overlay.branch_scout_selection.v1",
        "input_candidate_count": len(full_records),
        "input_branch_count": len(full_families),
        "capacity": archive.policy.capacity,
        "selected_candidate_count": len(archive.records),
        "selected_branch_count": len(selected_families),
        "branch_survival_rate": len(selected_families) / len(full_families),
        "selection_policy": "global S2 score, deterministic candidate tie-break; no per-branch quota",
        "archive_hash": archive_content_hash(archive),
    })
    return archive_rel, summary_rel


def _runtime_projection(
    *,
    list_size: int,
    scientific_elapsed_s: float,
) -> dict[str, Any]:
    if list_size != 10:
        return {
            "schema": "rdp.two_period_overlay.branch_runtime_projection.v1",
            "source_list_size": list_size,
            "target_list_size": None,
            "central_elapsed_s": None,
            "safety_adjusted_elapsed_s": None,
            "safety_factor": PROJECTION_SAFETY_FACTOR,
        }
    central = scientific_elapsed_s * 10.0
    return {
        "schema": "rdp.two_period_overlay.branch_runtime_projection.v1",
        "basis": "linear B10 wall-clock scaling at identical per-branch budget",
        "source_list_size": 10,
        "target_list_size": 100,
        "central_elapsed_s": central,
        "safety_adjusted_elapsed_s": central * PROJECTION_SAFETY_FACTOR,
        "safety_factor": PROJECTION_SAFETY_FACTOR,
        "overnight_available_s": OVERNIGHT_SECONDS,
    }


def _progression_gate(
    *,
    list_size: int,
    survived: bool,
    exact: bool,
    final_rank: int | None,
    projection: Mapping[str, Any],
) -> bool:
    """Apply the predeclared terminal gate without changing search behaviour."""

    if list_size == 10:
        useful_enrichment = survived and (
            exact or (final_rank is not None and int(final_rank) <= 3)
        )
        projected = projection.get("safety_adjusted_elapsed_s")
        return bool(
            useful_enrichment
            and isinstance(projected, (int, float))
            and math.isfinite(float(projected))
            and float(projected) <= OVERNIGHT_SECONDS
        )
    if list_size == 100:
        return bool(survived and final_rank is not None and int(final_rank) <= 10)
    if list_size == 1000:
        return bool(survived and final_rank is not None and int(final_rank) <= 25)
    raise ValueError("list_size must be 10, 100 or 1000")


def run_candidate_word_branches(
    repo_root: Path,
    *,
    list_size: int,
    wordlist_dir: str | Path | None = None,
) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )
    from cipher_development.shared.replay_provenance import build_evaluator_provenance

    if list_size not in SUPPORTED_LIST_SIZES:
        raise ValueError("list_size must be 10, 100 or 1000")
    repo_root = repo_root.resolve()
    experiment_id = _experiment_id(list_size)
    source_a = _source_experiment_a(repo_root)
    source_b1000 = _source_b1000_gate(repo_root) if list_size == 1000 else None
    bundle = build_nested_candidate_lists(wordlist_dir)
    if list_size == 10:
        candidates = bundle.candidates_10
    elif list_size == 100:
        candidates = bundle.candidates_100
    else:
        candidates = bundle.candidates_1000
    lookup = _candidate_lookup(candidates)
    starts_per_branch = B1000_STARTS_PER_BRANCH if list_size == 1000 else STARTS_PER_BRANCH
    global_scout_capacity = (
        B1000_GLOBAL_SCOUT_CAPACITY
        if list_size == 1000
        else GLOBAL_SCOUT_CAPACITY_PER_BRANCH * list_size
    )
    starts = build_branch_starts(starts_per_branch)
    started_at = _utc_now_iso()
    scientific_started = time.perf_counter()
    ceiling = EXPERIMENT_CEILING_SECONDS[list_size]
    deadline = time.monotonic() + ceiling

    question = (
        f"Can the correct offset-206 eight-rune word branch be promoted from a deterministic "
        f"B{list_size} candidate list under equal per-branch S2 scouting and shared B1/F1 continuation?"
    )
    decision_rule = (
        "For B10, authorise B100 only when all branches and replays complete, the correct branch "
        "survives the global scout selection, its final rank is at most three or it solves exactly, "
        "and the safety-adjusted B100 projection fits eight hours. For B100, promote branch "
        "identification when the correct branch survives and finishes in the top ten. For B1000, "
        "promote the compressed-budget scaling result when the correct branch survives and finishes "
        "in the top twenty-five; report exact solve success separately. No branch survival or budget "
        "decision may use benchmark identity before all search and replay for that list have completed."
    )
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=experiment_id,
        benchmark_id=f"alice_308_p13_p17_candidate_words_b{list_size}_d08",
        question=question,
        hypothesis=(
            "Equal-budget S2 scouting will enrich the correct d8 branch sufficiently for shared "
            "B1/F1 continuation to preserve and highly rank it within home-computer resources."
        ),
        alternative=(
            "Plausible false-word branches score as well as or better than the correct branch, the "
            "correct branch is eliminated, or branch scaling exceeds the available runtime."
        ),
        decision_rule=decision_rule,
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.BUDGET,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_seconds=ceiling,
        budget_evaluations=(25_000_000 if list_size == 1000 else (35_000_000 if list_size == 100 else 4_000_000)),
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "list_id": f"b{list_size}",
        "candidate_count": list_size,
        "starts_per_branch": starts_per_branch,
        "scout_archive_per_branch": SCOUT_ARCHIVE_PER_BRANCH,
        "global_scout_capacity": global_scout_capacity,
        "stage_profiles": [S2.to_json_dict(), B1.to_json_dict(), F1.to_json_dict()],
        "stage_sweeps": {
            S2.profile_id: SCOUT_SWEEPS,
            B1.profile_id: BRIDGE_SWEEPS,
            F1.profile_id: JUDGE_SWEEPS,
        },
        "equal_branch_budget": True,
        "global_selection_has_no_per_branch_quota": True,
        "search_signal_only_stopping": True,
        "all_search_and_replay_before_terminal_branch_evaluation": True,
        "source_experiment_a": {
            "run_id": source_a["run_id"],
            "result_sha256": source_a["result_sha256"],
        },
        "source_b1000_gate": (
            None
            if source_b1000 is None
            else {
                "run_id": source_b1000["run_id"],
                "result_sha256": source_b1000["result_sha256"],
            }
        ),
    }

    run_dir: Path | None = None
    result_path: Path | None = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            required_paths: set[str] = {
                "artifacts/experiment_manifest.json",
                "artifacts/experiment_result.json",
            }
            provenance = build_evaluator_provenance(
                repo_root=repo_root,
                evaluator_source=Path(__file__).with_name("replay.py"),
                scoring_contracts=(
                    S2.scoring_contract(),
                    B1.scoring_contract(),
                    F1.scoring_contract(),
                ),
                require_assets=True,
            )
            source_rel = Path("artifacts/experiment_b/source_experiment_a_gate.json")
            _write_json(run_dir / source_rel, {
                "schema": "rdp.two_period_overlay.source_experiment_gate.v1",
                "experiment_id": "experiment_a_standard_panel_v1",
                "run_id": source_a["run_id"],
                "result_sha256": source_a["result_sha256"],
                "decision": source_a["decision"],
                "promotion_gate_passed": source_a["promotion_gate_passed"],
                "terminal_payload_copied": False,
            })
            required_paths.add(source_rel.as_posix())
            if source_b1000 is not None:
                b1000_gate_rel = Path("artifacts/experiment_b/source_b1000_gate.json")
                _write_json(run_dir / b1000_gate_rel, {
                    "schema": "rdp.two_period_overlay.source_b1000_gate.v1",
                    "experiment_id": "b100_scout_budget_sensitivity_v1",
                    "run_id": source_b1000["run_id"],
                    "result_sha256": source_b1000["result_sha256"],
                    "decision": source_b1000["decision"],
                    "b1000_gate_passed": source_b1000["b1000_gate_passed"],
                    "terminal_payload_copied": False,
                })
                required_paths.add(b1000_gate_rel.as_posix())

            list_rel = Path("artifacts/experiment_b/candidate_list.json")
            assets_rel = Path("artifacts/experiment_b/candidate_list_assets.json")
            starts_rel = Path("artifacts/experiment_b/shared_starts.json")
            _write_json(run_dir / list_rel, bundle.public_payload(list_size))
            _write_json(run_dir / assets_rel, {
                "schema": "rdp.two_period_overlay.candidate_word_assets.v1",
                "directory_label": bundle.source_dir.name,
                "files": list(bundle.source_files),
            })
            _write_json(run_dir / starts_rel, {
                "schema": "rdp.two_period_overlay.branch_starts.v1",
                "count": len(starts),
                "dimension": 8,
                "rows": list(starts),
            })
            required_paths.update(path.as_posix() for path in (list_rel, assets_rel, starts_rel))

            search_rows: list[dict[str, Any]] = []
            replay_rows: list[dict[str, Any]] = []
            attempt_rows: list[dict[str, Any]] = []
            all_scout_records: list[CandidateRecord] = []
            scout_outcomes: dict[str, Any] = {}

            # Search and replay every branch before opening terminal branch identity.
            for branch_index, candidate in enumerate(candidates):
                _remaining(deadline)
                benchmark = benchmark_for_candidate(candidate)
                scout_case, _unused_reference = build_rdp_case(
                    benchmark, scoring_contract=S2.scoring_contract()
                )
                outcome = _run_stage(
                    stage_id="scout",
                    profile=S2,
                    search_case=scout_case,
                    inputs=starts,
                    sweeps=SCOUT_SWEEPS,
                    benchmark=benchmark,
                    archive_capacity=SCOUT_ARCHIVE_PER_BRANCH,
                    stage_safety_seconds=_remaining(deadline),
                    provenance_source=experiment_id,
                    provenance_operation="candidate_branch_scout",
                    family_id=candidate.branch_id,
                )
                root = Path(f"artifacts/experiment_b/branches/{candidate.branch_id}")
                persisted = _write_stage_and_replay(
                    run_dir=run_dir,
                    run=run,
                    stage=outcome,
                    search_case=scout_case,
                    evaluator_provenance=provenance,
                    artifact_root=root,
                    experiment_id=experiment_id,
                    benchmark=benchmark,
                    selection_purpose="handoff",
                    selection_label=f"{candidate.branch_id}__scout_all",
                    evaluator_id=f"two_period_overlay_{experiment_id}_{candidate.branch_id}_scout_v1",
                )
                scout_outcomes[candidate.branch_id] = outcome
                all_scout_records.extend(outcome.archive.records)
                search_rows.append({
                    "branch_id": candidate.branch_id,
                    "branch_index": branch_index,
                    "stage": "scout",
                    **outcome.to_search_summary(),
                })
                replay_rows.append({
                    "branch_id": candidate.branch_id,
                    "stage": "scout",
                    "deterministic": persisted["replay_deterministic"],
                    "stored_scores_verified": persisted["replay_stored_scores_verified"],
                })
                attempt_rows.extend({"branch_id": candidate.branch_id, **dict(row)} for row in outcome.attempt_rows)
                required_paths.update(persisted["artifacts"].values())

            global_scout = _selection_archive(
                all_scout_records,
                global_scout_capacity,
            )
            selection_archive_rel, selection_summary_rel = _persist_global_selection(
                run_dir, global_scout, all_scout_records
            )
            required_paths.update((selection_archive_rel.as_posix(), selection_summary_rel.as_posix()))
            selected_by_branch = _group(global_scout.records)

            bridge_outcomes: dict[str, Any] = {}
            bridge_records: list[CandidateRecord] = []
            for branch_id in sorted(selected_by_branch):
                _remaining(deadline)
                candidate = lookup[branch_id]
                benchmark = benchmark_for_candidate(candidate)
                bridge_case, _unused_reference = build_rdp_case(
                    benchmark, scoring_contract=B1.scoring_contract()
                )
                outcome = _run_stage(
                    stage_id="bridge",
                    profile=B1,
                    search_case=bridge_case,
                    inputs=selected_by_branch[branch_id],
                    sweeps=BRIDGE_SWEEPS,
                    benchmark=benchmark,
                    archive_capacity=len(selected_by_branch[branch_id]),
                    stage_safety_seconds=_remaining(deadline),
                    provenance_source=experiment_id,
                    provenance_operation="candidate_branch_bridge",
                )
                root = Path(f"artifacts/experiment_b/branches/{branch_id}")
                persisted = _write_stage_and_replay(
                    run_dir=run_dir,
                    run=run,
                    stage=outcome,
                    search_case=bridge_case,
                    evaluator_provenance=provenance,
                    artifact_root=root,
                    experiment_id=experiment_id,
                    benchmark=benchmark,
                    selection_purpose="handoff",
                    selection_label=f"{branch_id}__bridge_all",
                    evaluator_id=f"two_period_overlay_{experiment_id}_{branch_id}_bridge_v1",
                )
                bridge_outcomes[branch_id] = outcome
                bridge_records.extend(outcome.archive.records)
                search_rows.append({"branch_id": branch_id, "stage": "bridge", **outcome.to_search_summary()})
                replay_rows.append({
                    "branch_id": branch_id,
                    "stage": "bridge",
                    "deterministic": persisted["replay_deterministic"],
                    "stored_scores_verified": persisted["replay_stored_scores_verified"],
                })
                attempt_rows.extend({"branch_id": branch_id, **dict(row)} for row in outcome.attempt_rows)
                required_paths.update(persisted["artifacts"].values())

            judge_inputs = _deduplicated_records(global_scout.records, bridge_records)
            judge_by_branch = _group(judge_inputs)
            judge_outcomes: dict[str, Any] = {}
            final_archives: dict[str, CandidateArchive] = {}
            final_records: list[CandidateRecord] = []
            for branch_id in sorted(judge_by_branch):
                _remaining(deadline)
                candidate = lookup[branch_id]
                benchmark = benchmark_for_candidate(candidate)
                judge_case, _unused_reference = build_rdp_case(
                    benchmark, scoring_contract=F1.scoring_contract()
                )
                outcome = _run_stage(
                    stage_id="judge",
                    profile=F1,
                    search_case=judge_case,
                    inputs=judge_by_branch[branch_id],
                    sweeps=JUDGE_SWEEPS,
                    benchmark=benchmark,
                    archive_capacity=len(judge_by_branch[branch_id]),
                    stage_safety_seconds=_remaining(deadline),
                    provenance_source=experiment_id,
                    provenance_operation="candidate_branch_judge",
                )
                root = Path(f"artifacts/experiment_b/branches/{branch_id}")
                persisted = _write_stage_and_replay(
                    run_dir=run_dir,
                    run=run,
                    stage=outcome,
                    search_case=judge_case,
                    evaluator_provenance=provenance,
                    artifact_root=root,
                    experiment_id=experiment_id,
                    benchmark=benchmark,
                    selection_purpose="replay",
                    selection_label=f"{branch_id}__judge_all",
                    evaluator_id=f"two_period_overlay_{experiment_id}_{branch_id}_judge_v1",
                )
                judge_outcomes[branch_id] = outcome
                search_rows.append({"branch_id": branch_id, "stage": "judge", **outcome.to_search_summary()})
                replay_rows.append({
                    "branch_id": branch_id,
                    "stage": "judge",
                    "deterministic": persisted["replay_deterministic"],
                    "stored_scores_verified": persisted["replay_stored_scores_verified"],
                })
                attempt_rows.extend({"branch_id": branch_id, **dict(row)} for row in outcome.attempt_rows)
                required_paths.update(persisted["artifacts"].values())

                scout_records = selected_by_branch[branch_id]
                branch_bridge = bridge_outcomes[branch_id].archive.records
                union = _deduplicated_records(scout_records, branch_bridge, outcome.archive.records)
                first_stage = _first_stage_map(scout_records, branch_bridge, outcome.archive.records)
                final_archive, rescore_elapsed, rescore_evaluations = _rescore_final_union(
                    union,
                    judge_case,
                    F1,
                    first_stage,
                    archive_capacity=len(union),
                    provenance_source=experiment_id,
                    provenance_operation="candidate_branch_final_rescore",
                )
                final_archives[branch_id] = final_archive
                final_records.extend(final_archive.records)
                final_persisted = _write_final_union_and_replay(
                    run_dir=run_dir,
                    run=run,
                    archive=final_archive,
                    search_case=judge_case,
                    profile=F1,
                    evaluator_provenance=provenance,
                    artifact_root=root,
                    experiment_id=experiment_id,
                    benchmark=benchmark,
                    selection_label=f"{branch_id}__final_union_all",
                    evaluator_id=f"two_period_overlay_{experiment_id}_{branch_id}_final_v1",
                )
                replay_rows.append({
                    "branch_id": branch_id,
                    "stage": "final_union",
                    "deterministic": final_persisted["replay_deterministic"],
                    "stored_scores_verified": final_persisted["replay_stored_scores_verified"],
                })
                required_paths.update(final_persisted["artifacts"].values())
                search_rows.append({
                    "branch_id": branch_id,
                    "stage": "final_union",
                    "candidate_count": len(final_archive.records),
                    "rescore_elapsed_s": rescore_elapsed,
                    "rescore_evaluations": rescore_evaluations,
                    "archive_hash": archive_content_hash(final_archive),
                })

            all_replays = all(
                bool(row["deterministic"]) and bool(row["stored_scores_verified"])
                for row in replay_rows
            )
            if not all_replays:
                raise RuntimeError("candidate branch replay gate failed")

            search_rel = Path("artifacts/experiment_b/search_summary.json")
            replay_rel = Path("artifacts/experiment_b/replay_summary.json")
            attempts_rel = Path("artifacts/experiment_b/attempt_timing.json")
            _write_json(run_dir / search_rel, {
                "schema": "rdp.two_period_overlay.candidate_branch_search.v1",
                "rows": search_rows,
            })
            _write_json(run_dir / replay_rel, {
                "schema": "rdp.two_period_overlay.candidate_branch_replay.v1",
                "all_deterministic": all_replays,
                "rows": replay_rows,
            })
            _write_json(run_dir / attempts_rel, {
                "schema": "rdp.two_period_overlay.candidate_branch_attempt_timing.v1",
                "rows": attempt_rows,
            })
            required_paths.update(path.as_posix() for path in (search_rel, replay_rel, attempts_rel))

            # Terminal-only branch identity and correctness evaluation starts here.
            required_runes = tuple(int(value) for value in DORMOUSE_RUNES)
            required_candidate = next(
                candidate for candidate in candidates if candidate.runes == required_runes
            )
            required_branch_id = required_candidate.branch_id
            scout_ranking = _branch_ranking(_branch_best(all_scout_records, S2.score_name))
            selected_ranking = _branch_ranking(_branch_best(global_scout.records, S2.score_name))
            bridge_ranking = _branch_ranking(_branch_best(bridge_records, B1.score_name))
            final_ranking = _branch_ranking(_branch_best(final_records, F1.score_name))
            survived = required_branch_id in selected_by_branch

            benchmark = benchmark_for_candidate(required_candidate)
            scout_case, reference = build_rdp_case(
                benchmark, scoring_contract=S2.scoring_contract()
            )
            bridge_case, _ = build_rdp_case(benchmark, scoring_contract=B1.scoring_contract())
            judge_case, _ = build_rdp_case(benchmark, scoring_contract=F1.scoring_contract())
            terminal: dict[str, Any] = {
                "schema": "rdp.two_period_overlay.candidate_branch_terminal.v1",
                "candidate_list_id": f"b{list_size}",
                "controlled_word": required_candidate.word,
                "controlled_branch_id": required_branch_id,
                "controlled_word_occurred_naturally": bundle.required_occurred_naturally,
                "controlled_word_source": (
                    "source_list" if bundle.required_occurred_naturally else "controlled_insertion"
                ),
                "branch_ranks": {
                    "scout_full": _rank_for(scout_ranking, required_branch_id),
                    "scout_selected": _rank_for(selected_ranking, required_branch_id),
                    "bridge": _rank_for(bridge_ranking, required_branch_id),
                    "final": _rank_for(final_ranking, required_branch_id),
                },
                "survived_global_scout_selection": survived,
                "branch_survival_rate": len(selected_by_branch) / list_size,
                "false_high_branches": [
                    {**row, "word": lookup[str(row["branch_id"])].word}
                    for row in final_ranking
                    if row["branch_id"] != required_branch_id
                ][:10],
            }
            if survived:
                terminal["scout"] = {
                    "archive": _stage_terminal_summary(
                        scout_outcomes[required_branch_id].archive.records,
                        S2,
                        scout_case,
                        reference,
                    ),
                    "movement": _attempt_terminal_movement(
                        scout_outcomes[required_branch_id], scout_case, reference
                    ),
                }
                terminal["bridge"] = {
                    "archive": _stage_terminal_summary(
                        bridge_outcomes[required_branch_id].archive.records,
                        B1,
                        bridge_case,
                        reference,
                    ),
                    "movement": _attempt_terminal_movement(
                        bridge_outcomes[required_branch_id], bridge_case, reference
                    ),
                }
                terminal["judge"] = {
                    "archive": _stage_terminal_summary(
                        judge_outcomes[required_branch_id].archive.records,
                        F1,
                        judge_case,
                        reference,
                    ),
                    "movement": _attempt_terminal_movement(
                        judge_outcomes[required_branch_id], judge_case, reference
                    ),
                }
                terminal["final_union"] = {
                    "archive": _stage_terminal_summary(
                        final_archives[required_branch_id].records,
                        F1,
                        judge_case,
                        reference,
                    )
                }
            else:
                terminal["scout"] = {
                    "archive": _stage_terminal_summary(
                        scout_outcomes[required_branch_id].archive.records,
                        S2,
                        scout_case,
                        reference,
                    )
                }

            exact = bool(
                terminal.get("final_union", {}).get("archive", {}).get("exact_plaintext_count", 0)
            ) if survived else bool(
                terminal["scout"]["archive"].get("exact_plaintext_count", 0)
            )
            terminal["exact_solution_persisted"] = exact

            scientific_elapsed = time.perf_counter() - scientific_started
            projection = _runtime_projection(
                list_size=list_size,
                scientific_elapsed_s=scientific_elapsed,
            )
            final_rank = terminal["branch_ranks"]["final"]
            progression_gate = _progression_gate(
                list_size=list_size,
                survived=survived,
                exact=exact,
                final_rank=(None if final_rank is None else int(final_rank)),
                projection=projection,
            )

            terminal["progression_gate_passed"] = progression_gate
            terminal["progression_gate_meaning"] = (
                "authorise_b100"
                if list_size == 10
                else (
                    "branch_identification_success_not_b1000_authorisation"
                    if list_size == 100
                    else "b1000_branch_identification_success_no_further_authorisation"
                )
            )
            terminal["runtime_projection"] = projection
            terminal_rel = Path("artifacts/experiment_b/terminal_branch_evaluation.json")
            timing_rel = Path("artifacts/execution_timing.json")
            summary_rel = Path("artifacts/candidate_branch_summary.json")
            _write_json(run_dir / terminal_rel, terminal)
            _write_json(run_dir / timing_rel, {
                "schema": "rdp.two_period_overlay.candidate_branch_timing.v1",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now_iso(),
                "scientific_work_elapsed_s": scientific_elapsed,
                "list_size": list_size,
                "branches": list_size,
                "starts_per_branch": starts_per_branch,
                "attempt_timing_artifact": attempts_rel.as_posix(),
                "runtime_projection": projection,
            })
            _write_json(run_dir / summary_rel, {
                "schema": "rdp.two_period_overlay.candidate_branch_summary.v1",
                "list_id": f"b{list_size}",
                "branch_count": list_size,
                "starts_per_branch": starts_per_branch,
                "global_scout_capacity": global_scout_capacity,
                "selected_branch_count": len(selected_by_branch),
                "branch_survival_rate": len(selected_by_branch) / list_size,
                "all_replays_deterministic": all_replays,
                "progression_gate_passed": progression_gate,
                "exact_solution_persisted": exact,
                "terminal_artifact": terminal_rel.as_posix(),
                "timing": _read_json(run_dir / timing_rel),
            })
            required_paths.update(path.as_posix() for path in (terminal_rel, timing_rel, summary_rel))

            inventory_rel = Path("artifacts/experiment_b/required_artifacts.json")
            required_paths.add(inventory_rel.as_posix())
            _write_json(run_dir / inventory_rel, {
                "schema": "rdp.two_period_overlay.dynamic_required_artifacts.v1",
                "paths": sorted(required_paths),
            })

            result_path = run.finish(
                decision=(
                    ExperimentDecision.PROMOTE if progression_gate else ExperimentDecision.REFINE
                ),
                stop_reason="done",
                result_summary={
                    "artifact": summary_rel.as_posix(),
                    "list_id": f"b{list_size}",
                    "branch_count": list_size,
                    "starts_per_branch": starts_per_branch,
                    "selected_branch_count": len(selected_by_branch),
                    "branch_survival_rate": len(selected_by_branch) / list_size,
                    "all_replays_deterministic": all_replays,
                    "progression_gate_passed": progression_gate,
                    "exact_solution_persisted": exact,
                    "timing": _read_json(run_dir / timing_rel),
                },
                reference_evaluation=terminal,
            )
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, original_error=exc)
        raise
    if run_dir is None or result_path is None:
        raise RuntimeError("candidate-word experiment did not create a result")
    write_review_pack_after_run(repo_root, run_dir)
    return result_path


__all__ = [
    "B10_EXPERIMENT_ID",
    "B100_EXPERIMENT_ID",
    "B1000_EXPERIMENT_ID",
    "STARTS_PER_BRANCH",
    "B1000_STARTS_PER_BRANCH",
    "B1000_GLOBAL_SCOUT_CAPACITY",
    "_progression_gate",
    "build_branch_starts",
    "run_candidate_word_branches",
]
