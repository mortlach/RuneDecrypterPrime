from __future__ import annotations

"""WP6 Pack 07R controlled P13/P31 d22 staged science panel.

This module is a campaign-specific orchestration layer over the already accepted
S2 -> B1 -> F1 coordinate-search, archive, replay and terminal-evaluation
contracts.  It deliberately does not add another solver framework.

The recovery panel is frozen at three independent 512-start blocks. A four-start
integration canary and the first two scientific blocks form operational gates
only. No terminal benchmark metrics are opened until the canary and all three
scientific blocks have completed search, persistence and deterministic replay.
"""

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

from cipher_development.shared.archive import CandidateArchive, CandidateRecord
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import (
    BenchmarkSpec,
    MASTER_SEED,
    P13_P31_DORMOUSE_206_BENCHMARK,
    P13_P31_PRIMARY_BENCHMARK,
)
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import B1, F1, S2, ScorerProfile
from cipher_development.two_period_overlay.staged_handoff import (
    STAGE_SWEEPS,
    StageOutcome,
    _attempt_terminal_movement,
    _deduplicated_records,
    _first_stage_map,
    _rescore_final_union,
    _run_stage,
    _stage_terminal_summary,
    _write_final_union_and_replay,
    _write_stage_and_replay,
)

EXPERIMENT_ID = "p13_p31_two_word_d22_staged_panel_v2"
BENCHMARK = P13_P31_DORMOUSE_206_BENCHMARK
CONTRACT_BENCHMARKS = (P13_P31_PRIMARY_BENCHMARK, P13_P31_DORMOUSE_206_BENCHMARK)

SCOUT_PROFILE = S2
BRIDGE_PROFILE = B1
JUDGE_PROFILE = F1
FROZEN_LADDER = (SCOUT_PROFILE, BRIDGE_PROFILE, JUDGE_PROFILE)

CANARY_BLOCK_ID = 70
CANARY_STARTS = 4
PHASE_A_BLOCK_IDS = (71, 72)
PHASE_B_BLOCK_IDS = (73,)
SCIENCE_BLOCK_IDS = (*PHASE_A_BLOCK_IDS, *PHASE_B_BLOCK_IDS)
STARTS_PER_BLOCK = 512
ARCHIVE_CAPACITY = STARTS_PER_BLOCK * 4
REPLAY_REPEAT_COUNT = 2

STAGE_WALLCLOCK_CEILING_S = 180.0 * 60.0
BLOCK_WALLCLOCK_CEILING_S = 225.0 * 60.0
SCIENTIFIC_WALLCLOCK_CEILING_S = 12.0 * 60.0 * 60.0
TERMINAL_RUNTIME_RESERVE_S = 20.0 * 60.0
RUNTIME_PROJECTION_SAFETY_FACTOR = 1.10

# The first real Pack 07 d22 canary completed four starts, all three stages and
# replay in 98.1855874999892 seconds. That direct d22 timing supersedes the
# invalid d14 dimension-scaling projection that caused science block 71 to hit
# its 9,000-second block ceiling. Phase A remains the authoritative truth-blind
# continuation signal during the recovery run.
PACK07_CANARY_ELAPSED_S = 98.1855874999892
PACK07_CANARY_STARTS = 4

NEAR_SOLVE_RUNES = 289
NEAR_SOLVE_COMPLETE_WORDS = 63


@dataclass(frozen=True, slots=True)
class StagedBlock:
    benchmark: BenchmarkSpec
    block_id: int
    phase: str
    starts: tuple[dict[str, Any], ...]
    scout: StageOutcome
    bridge: StageOutcome
    judge: StageOutcome
    final_archive: CandidateArchive
    final_rescore_elapsed_s: float
    final_rescore_evaluations: int
    search_elapsed_s: float
    total_elapsed_s: float = 0.0


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


def _status(run_dir: Path | None, state: str, **details: Any) -> None:
    payload = {
        "schema": "rdp.two_period_overlay.p13_p31_d22_visible_status.v1",
        "updated_at_utc": _utc_now_iso(),
        "state": state,
        **details,
    }
    print(
        f"[{payload['updated_at_utc']}] {state}: "
        + json.dumps(details, sort_keys=True, allow_nan=False),
        flush=True,
    )
    if run_dir is not None:
        _write_json(run_dir / "artifacts/experiment_d/visible_status.json", payload)


def panel_seed(benchmark_id: str, block_id: int, stage_id: str, token: str) -> int:
    if not benchmark_id or not stage_id or not token:
        raise ValueError("benchmark_id, stage_id and token must be non-empty")
    if isinstance(block_id, bool) or not isinstance(block_id, int) or block_id < 0:
        raise ValueError("block_id must be a non-negative integer")
    payload = (
        f"{MASTER_SEED}:wp6-pack07:{benchmark_id}:{block_id}:{stage_id}:{token}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp6-07").digest(),
        "big",
    )


def build_block_starts(
    benchmark: BenchmarkSpec,
    block_id: int,
    *,
    count: int = STARTS_PER_BLOCK,
) -> tuple[dict[str, Any], ...]:
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError("count must be a positive integer")
    rows: list[dict[str, Any]] = []
    for restart_index in range(count):
        token = f"restart-{restart_index}"
        seed = panel_seed(benchmark.benchmark_id, block_id, "start", token)
        rng = np.random.default_rng(seed)
        variables = rng.integers(
            0,
            benchmark.alphabet_size,
            size=benchmark.expected_free_dimension,
            dtype=np.uint8,
        )
        rows.append({
            "block_id": block_id,
            "restart_index": restart_index,
            "seed": seed,
            "variables": variables.astype(int).tolist(),
        })
    return tuple(rows)


def evaluation_budget_upper(
    *,
    starts_per_block: int = STARTS_PER_BLOCK,
    block_count: int = len(SCIENCE_BLOCK_IDS),
    dimension: int = BENCHMARK.expected_free_dimension,
    alphabet_size: int = BENCHMARK.alphabet_size,
) -> dict[str, int]:
    for name, value in (
        ("starts_per_block", starts_per_block),
        ("block_count", block_count),
        ("dimension", dimension),
        ("alphabet_size", alphabet_size),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    scout = starts_per_block * (
        2 + STAGE_SWEEPS[SCOUT_PROFILE.profile_id] * dimension * alphabet_size
    )
    bridge = starts_per_block * (
        2 + STAGE_SWEEPS[BRIDGE_PROFILE.profile_id] * dimension * alphabet_size
    )
    judge_input_upper = starts_per_block * 2
    judge = judge_input_upper * (
        2 + STAGE_SWEEPS[JUDGE_PROFILE.profile_id] * dimension * alphabet_size
    )
    final_union_upper = starts_per_block * 4
    final_rescore = final_union_upper

    # Two replays of scout, bridge, judge and final-union surfaces, followed by
    # terminal metrics over the three stage surfaces and final union.  These are
    # deliberately conservative maxima; deduplication and early convergence may
    # reduce actual work.
    replay = REPLAY_REPEAT_COUNT * (
        starts_per_block
        + starts_per_block
        + judge_input_upper
        + final_union_upper
    )
    terminal = (
        starts_per_block
        + starts_per_block
        + judge_input_upper
        + final_union_upper
    )
    per_block = scout + bridge + judge + final_rescore + replay + terminal
    return {
        "scout": scout,
        "bridge": bridge,
        "judge": judge,
        "final_rescore": final_rescore,
        "replay": replay,
        "terminal": terminal,
        "per_block": per_block,
        "science_panel": per_block * block_count,
        "canary": per_block * CANARY_STARTS // starts_per_block,
        "complete_pack07": per_block * block_count + per_block * CANARY_STARTS // starts_per_block,
    }


def planned_runtime() -> dict[str, Any]:
    seconds_per_start_d22 = PACK07_CANARY_ELAPSED_S / PACK07_CANARY_STARTS
    science_starts = len(SCIENCE_BLOCK_IDS) * STARTS_PER_BLOCK
    central = science_starts * seconds_per_start_d22
    safety_adjusted = central * RUNTIME_PROJECTION_SAFETY_FACTOR
    return {
        "schema": "rdp.two_period_overlay.p13_p31_d22_runtime_plan.v1",
        "source_timing": {
            "experiment": "p13_p31_two_word_d22_staged_panel_v1",
            "run_id": (
                "20260726_081457__two_period_overlay__"
                "p13_p31_two_word_d22_staged_panel_v1__4e06b05"
            ),
            "phase": "canary",
            "block_id": 70,
            "elapsed_s": PACK07_CANARY_ELAPSED_S,
            "starts": PACK07_CANARY_STARTS,
            "dimension": 22,
        },
        "target_dimension": BENCHMARK.expected_free_dimension,
        "canary_starts": CANARY_STARTS,
        "science_blocks": len(SCIENCE_BLOCK_IDS),
        "starts_per_block": STARTS_PER_BLOCK,
        "science_starts": science_starts,
        "central_elapsed_s": central,
        "central_elapsed_hours": central / 3600.0,
        "safety_factor": RUNTIME_PROJECTION_SAFETY_FACTOR,
        "safety_adjusted_elapsed_s": safety_adjusted,
        "safety_adjusted_elapsed_hours": safety_adjusted / 3600.0,
        "hard_scientific_ceiling_s": SCIENTIFIC_WALLCLOCK_CEILING_S,
        "hard_scientific_ceiling_hours": SCIENTIFIC_WALLCLOCK_CEILING_S / 3600.0,
        "terminal_runtime_reserve_s": TERMINAL_RUNTIME_RESERVE_S,
        "evaluation_budget_upper": evaluation_budget_upper(),
        "planning_statement": (
            "approximately 10.5 hours centrally and 11.5 hours with the frozen "
            "1.10 safety factor, under a twelve-hour hard scientific ceiling"
        ),
    }


def contract_preflight(repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for benchmark in CONTRACT_BENCHMARKS:
        search_case, _ = build_rdp_case(
            benchmark,
            scoring_contract=SCOUT_PROFILE.scoring_contract(),
        )
        rows.append({
            "benchmark_id": benchmark.benchmark_id,
            "period_a": benchmark.period_a,
            "period_b": benchmark.period_b,
            "declared_dimension": benchmark.expected_free_dimension,
            "derived_dimension": len(search_case.free_columns),
            "free_columns": list(search_case.free_columns),
            "all_free_columns_in_stream_b": all(
                index >= benchmark.period_a for index in search_case.free_columns
            ),
            "known_key_affine_roundtrip_verified": True,
            "complete_crib_and_wli_spans_verified": True,
        })
    expected = [30, 22]
    actual = [int(row["derived_dimension"]) for row in rows]
    if actual != expected:
        raise RuntimeError(f"P13/P31 dimension ladder mismatch: {actual!r}")
    if not rows[-1]["all_free_columns_in_stream_b"]:
        raise RuntimeError("P13/P31 d22 free-column contract changed unexpectedly")
    return {
        "schema": "rdp.two_period_overlay.p13_p31_d22_contract_preflight.v1",
        "repo_root_name": repo_root.resolve().name,
        "passed": True,
        "rows": rows,
        "target_benchmark_id": BENCHMARK.benchmark_id,
        "target_dimension": BENCHMARK.expected_free_dimension,
        "target_free_columns": rows[-1]["free_columns"],
    }


def _stage_seed_factory(benchmark: BenchmarkSpec, block_id: int):
    def seed_factory(stage_id: str, token: str) -> int:
        return panel_seed(benchmark.benchmark_id, block_id, stage_id, token)

    return seed_factory


def _remaining_seconds(deadline: float, ceiling: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0.0:
        raise TimeoutError("Pack 07 wall-clock ceiling reached")
    return min(remaining, ceiling)


def _run_staged_block(
    benchmark: BenchmarkSpec,
    block_id: int,
    phase: str,
    starts: tuple[dict[str, Any], ...],
    cases: Mapping[str, Any],
    *,
    global_deadline: float,
) -> StagedBlock:
    block_started = time.perf_counter()
    block_deadline = min(
        global_deadline,
        time.monotonic() + BLOCK_WALLCLOCK_CEILING_S,
    )
    seed_factory = _stage_seed_factory(benchmark, block_id)

    scout = _run_stage(
        stage_id="scout",
        profile=SCOUT_PROFILE,
        search_case=cases["scout"],
        inputs=starts,
        sweeps=STAGE_SWEEPS[SCOUT_PROFILE.profile_id],
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=_remaining_seconds(
            block_deadline, STAGE_WALLCLOCK_CEILING_S
        ),
        provenance_source="p13_p31_two_word_d22_staged_panel",
    )
    bridge = _run_stage(
        stage_id="bridge",
        profile=BRIDGE_PROFILE,
        search_case=cases["bridge"],
        inputs=scout.archive.records,
        sweeps=STAGE_SWEEPS[BRIDGE_PROFILE.profile_id],
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=_remaining_seconds(
            block_deadline, STAGE_WALLCLOCK_CEILING_S
        ),
        provenance_source="p13_p31_two_word_d22_staged_panel",
    )
    judge_inputs = _deduplicated_records(
        scout.archive.records,
        bridge.archive.records,
    )
    judge = _run_stage(
        stage_id="judge",
        profile=JUDGE_PROFILE,
        search_case=cases["judge"],
        inputs=judge_inputs,
        sweeps=STAGE_SWEEPS[JUDGE_PROFILE.profile_id],
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=_remaining_seconds(
            block_deadline, STAGE_WALLCLOCK_CEILING_S
        ),
        provenance_source="p13_p31_two_word_d22_staged_panel",
    )
    first_stage = _first_stage_map(
        scout.archive.records,
        bridge.archive.records,
        judge.archive.records,
    )
    all_records = _deduplicated_records(
        scout.archive.records,
        bridge.archive.records,
        judge.archive.records,
    )
    if len(all_records) > ARCHIVE_CAPACITY:
        raise RuntimeError("complete staged union exceeds the frozen archive capacity")
    final_archive, rescore_elapsed, rescore_evaluations = _rescore_final_union(
        all_records,
        cases["judge"],
        JUDGE_PROFILE,
        first_stage,
        archive_capacity=ARCHIVE_CAPACITY,
        provenance_source="p13_p31_two_word_d22_staged_panel",
    )
    elapsed = time.perf_counter() - block_started
    if time.monotonic() > block_deadline:
        raise TimeoutError(f"P13/P31 block {block_id} exceeded its wall-clock ceiling")
    return StagedBlock(
        benchmark=benchmark,
        block_id=block_id,
        phase=phase,
        starts=starts,
        scout=scout,
        bridge=bridge,
        judge=judge,
        final_archive=final_archive,
        final_rescore_elapsed_s=rescore_elapsed,
        final_rescore_evaluations=rescore_evaluations,
        search_elapsed_s=elapsed,
    )


def _block_root(phase: str, block_id: int) -> Path:
    return Path("artifacts/experiment_d") / phase / f"block_{block_id:02d}"


def _stage_artifact_paths(root: Path, stage_id: str) -> tuple[str, ...]:
    return tuple(
        (root / stage_id / filename).as_posix()
        for filename in (
            "candidate_archive.json",
            "attempts.json",
            "handoff_batch.json",
            "replay_context.json",
            "replay_binding.json",
            "replay_evidence.json",
        )
    )


def _block_artifact_paths(phase: str, block_id: int) -> tuple[str, ...]:
    root = _block_root(phase, block_id)
    final = tuple(
        (root / "final_union" / filename).as_posix()
        for filename in (
            "candidate_archive.json",
            "replay_batch.json",
            "replay_context.json",
            "replay_binding.json",
            "replay_evidence.json",
        )
    )
    return (
        (root / "starts.json").as_posix(),
        *_stage_artifact_paths(root, "scout"),
        *_stage_artifact_paths(root, "bridge"),
        *_stage_artifact_paths(root, "judge"),
        *final,
        (root / "block_completed.json").as_posix(),
    )


def required_artifact_paths() -> tuple[str, ...]:
    static = (
        "artifacts/experiment_d/required_artifacts.json",
        "artifacts/experiment_d/visible_status.json",
        "artifacts/experiment_d/runtime_plan.json",
        "artifacts/experiment_d/contract_preflight.json",
        "artifacts/experiment_d/operational_gate.json",
        "artifacts/experiment_d/attempt_timing.json",
        "artifacts/experiment_d/search_summary.json",
        "artifacts/experiment_d/replay_summary.json",
        "artifacts/experiment_d/terminal_evaluation.json",
        "artifacts/p13_p31_two_word_d22_staged_panel_summary.json",
        "artifacts/execution_timing.json",
    )
    paths: list[str] = list(static)
    paths.extend(_block_artifact_paths("canary", CANARY_BLOCK_ID))
    for block_id in SCIENCE_BLOCK_IDS:
        paths.extend(_block_artifact_paths("science", block_id))
    return tuple(dict.fromkeys(paths))


def _persist_staged(
    *,
    run_dir: Path,
    run: Any,
    block: StagedBlock,
    cases: Mapping[str, Any],
    evaluator_provenance: Mapping[str, Any],
) -> tuple[StagedBlock, dict[str, Any]]:
    persist_started = time.perf_counter()
    root = _block_root(block.phase, block.block_id)
    _write_json(run_dir / root / "starts.json", {
        "schema": "rdp.two_period_overlay.p13_p31_d22_starts.v1",
        "benchmark_id": block.benchmark.benchmark_id,
        "phase": block.phase,
        "block_id": block.block_id,
        "rows": list(block.starts),
    })
    scout = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.scout,
        search_case=cases["scout"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root,
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"p13_p31_block_{block.block_id:02d}_scout__all",
        evaluator_id=f"two_period_overlay_p13_p31_scout_{block.block_id:02d}",
    )
    bridge = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.bridge,
        search_case=cases["bridge"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root,
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"p13_p31_block_{block.block_id:02d}_bridge__all",
        evaluator_id=f"two_period_overlay_p13_p31_bridge_{block.block_id:02d}",
    )
    judge = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.judge,
        search_case=cases["judge"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root,
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"p13_p31_block_{block.block_id:02d}_judge__all",
        evaluator_id=f"two_period_overlay_p13_p31_judge_{block.block_id:02d}",
    )
    final = _write_final_union_and_replay(
        run_dir=run_dir,
        run=run,
        archive=block.final_archive,
        search_case=cases["judge"],
        profile=JUDGE_PROFILE,
        evaluator_provenance=evaluator_provenance,
        artifact_root=root,
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"p13_p31_block_{block.block_id:02d}_final_union__all",
        evaluator_id=f"two_period_overlay_p13_p31_final_{block.block_id:02d}",
    )
    replay_ok = all(
        row.get("replay_deterministic") is True
        and row.get("replay_stored_scores_verified") is True
        for row in (scout, bridge, judge, final)
    )
    if not replay_ok:
        raise RuntimeError(f"P13/P31 block {block.block_id} replay verification failed")
    total_elapsed = block.search_elapsed_s + (time.perf_counter() - persist_started)
    completed = {
        "schema": "rdp.two_period_overlay.p13_p31_d22_block_completed.v1",
        "benchmark_id": block.benchmark.benchmark_id,
        "phase": block.phase,
        "block_id": block.block_id,
        "starts": len(block.starts),
        "search_elapsed_s": block.search_elapsed_s,
        "total_elapsed_s": total_elapsed,
        "replay_deterministic": True,
        "replay_stored_scores_verified": True,
        "surfaces": {
            "scout": scout,
            "bridge": bridge,
            "judge": judge,
            "final_union": {
                **final,
                "rescore_elapsed_s": block.final_rescore_elapsed_s,
                "rescore_evaluations": block.final_rescore_evaluations,
            },
        },
    }
    _write_json(run_dir / root / "block_completed.json", completed)
    return (
        StagedBlock(
            benchmark=block.benchmark,
            block_id=block.block_id,
            phase=block.phase,
            starts=block.starts,
            scout=block.scout,
            bridge=block.bridge,
            judge=block.judge,
            final_archive=block.final_archive,
            final_rescore_elapsed_s=block.final_rescore_elapsed_s,
            final_rescore_evaluations=block.final_rescore_evaluations,
            search_elapsed_s=block.search_elapsed_s,
            total_elapsed_s=total_elapsed,
        ),
        completed,
    )


def _search_summary(block: StagedBlock) -> dict[str, Any]:
    return {
        "benchmark_id": block.benchmark.benchmark_id,
        "phase": block.phase,
        "block_id": block.block_id,
        "starts": len(block.starts),
        "search_elapsed_s": block.search_elapsed_s,
        "total_elapsed_s": block.total_elapsed_s,
        "stages": {
            "scout": block.scout.to_search_summary(),
            "bridge": block.bridge.to_search_summary(),
            "judge": block.judge.to_search_summary(),
            "final_union": {
                "candidate_count": len(block.final_archive.records),
                "rescore_elapsed_s": block.final_rescore_elapsed_s,
                "rescore_evaluations": block.final_rescore_evaluations,
            },
        },
    }


def _attempt_rows(block: StagedBlock) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stage in (block.scout, block.bridge, block.judge):
        for row in stage.attempt_rows:
            rows.append({
                "benchmark_id": block.benchmark.benchmark_id,
                "phase": block.phase,
                "block_id": block.block_id,
                **dict(row),
            })
    return rows


def _operational_gate(
    *,
    phase_a_elapsed_s: float,
    elapsed_before_phase_a_s: float,
    phase_a_replays_verified: bool,
    completed_blocks: int,
) -> dict[str, Any]:
    if completed_blocks != len(PHASE_A_BLOCK_IDS):
        raise ValueError("operational gate requires the complete frozen Phase A")
    if phase_a_elapsed_s <= 0.0:
        raise ValueError("phase_a_elapsed_s must be positive")
    if elapsed_before_phase_a_s < 0.0:
        raise ValueError("elapsed_before_phase_a_s must be non-negative")
    projected_science = (
        phase_a_elapsed_s / completed_blocks * len(SCIENCE_BLOCK_IDS)
    )
    projected = elapsed_before_phase_a_s + projected_science
    safety_adjusted = (
        elapsed_before_phase_a_s
        + projected_science * RUNTIME_PROJECTION_SAFETY_FACTOR
    )
    continuation_ceiling = (
        SCIENTIFIC_WALLCLOCK_CEILING_S - TERMINAL_RUNTIME_RESERVE_S
    )
    passed = (
        phase_a_replays_verified
        and safety_adjusted <= continuation_ceiling
    )
    return {
        "schema": "rdp.two_period_overlay.p13_p31_d22_operational_gate.v1",
        "terminal_metrics_opened": False,
        "completed_phase_a_blocks": completed_blocks,
        "phase_a_elapsed_s": phase_a_elapsed_s,
        "elapsed_before_phase_a_s": elapsed_before_phase_a_s,
        "phase_a_replays_verified": phase_a_replays_verified,
        "projected_science_panel_elapsed_s": projected_science,
        "projected_complete_panel_elapsed_s": projected,
        "safety_factor": RUNTIME_PROJECTION_SAFETY_FACTOR,
        "safety_adjusted_projection_s": safety_adjusted,
        "hard_scientific_ceiling_s": SCIENTIFIC_WALLCLOCK_CEILING_S,
        "terminal_runtime_reserve_s": TERMINAL_RUNTIME_RESERVE_S,
        "continuation_projection_ceiling_s": continuation_ceiling,
        "gate_passed": passed,
        "failure_meaning": (
            "incomplete runtime evidence only; the d22 method is not scientifically closed"
            if not passed
            else "not applicable"
        ),
    }


def _exact_candidate_ids(
    records: Sequence[CandidateRecord],
    search_case: Any,
    reference: Any,
) -> set[str]:
    exact: set[str] = set()
    for record in records:
        variables = np.asarray(record.payload["variables"], dtype=np.uint8)
        metrics = reference_metrics(
            reference,
            variables,
            search_case.particular,
            search_case.basis,
        )
        if metrics["exact_plaintext"]:
            exact.add(record.candidate_id)
    return exact


def _exact_attempt_summary(stage: StageOutcome, exact_ids: set[str]) -> dict[str, Any]:
    cumulative = 0.0
    first_elapsed: float | None = None
    first_input: int | None = None
    exact_count = 0
    for row in stage.attempt_rows:
        cumulative += float(row["elapsed_s"])
        if row["candidate_id"] in exact_ids:
            exact_count += 1
            if first_elapsed is None:
                first_elapsed = cumulative
                first_input = int(row["input_index"])
    return {
        "exact_attempt_count": exact_count,
        "first_exact_input_index": first_input,
        "post_hoc_cumulative_attempt_elapsed_s_to_first_exact": first_elapsed,
    }


def _near_solve_count(
    records: Sequence[CandidateRecord],
    search_case: Any,
    reference: Any,
) -> int:
    count = 0
    for record in records:
        variables = np.asarray(record.payload["variables"], dtype=np.uint8)
        metrics = reference_metrics(
            reference,
            variables,
            search_case.particular,
            search_case.basis,
        )
        if (
            int(metrics["rune_matches"]) >= NEAR_SOLVE_RUNES
            and int(metrics["complete_word_matches"]) >= NEAR_SOLVE_COMPLETE_WORDS
        ):
            count += 1
    return count


def _terminal_block(
    block: StagedBlock,
    cases: Mapping[str, Any],
    reference: Any,
) -> dict[str, Any]:
    stage_records = {
        "scout": block.scout.archive.records,
        "bridge": block.bridge.archive.records,
        "judge": block.judge.archive.records,
        "final_union": block.final_archive.records,
    }
    exact_ids = {
        stage_id: _exact_candidate_ids(
            records,
            cases["judge"] if stage_id == "final_union" else cases[stage_id],
            reference,
        )
        for stage_id, records in stage_records.items()
    }
    first_exact_stage = next(
        (stage_id for stage_id in ("scout", "bridge", "judge") if exact_ids[stage_id]),
        None,
    )
    scout_summary = _stage_terminal_summary(
        block.scout.archive.records,
        SCOUT_PROFILE,
        cases["scout"],
        reference,
    )
    bridge_summary = _stage_terminal_summary(
        block.bridge.archive.records,
        BRIDGE_PROFILE,
        cases["bridge"],
        reference,
    )
    judge_summary = _stage_terminal_summary(
        block.judge.archive.records,
        JUDGE_PROFILE,
        cases["judge"],
        reference,
    )
    final_summary = _stage_terminal_summary(
        block.final_archive.records,
        JUDGE_PROFILE,
        cases["judge"],
        reference,
    )
    near_count = _near_solve_count(
        block.final_archive.records,
        cases["judge"],
        reference,
    )
    return {
        "block_id": block.block_id,
        "phase": block.phase,
        "scout": {
            "archive": scout_summary,
            "movement": _attempt_terminal_movement(block.scout, cases["scout"], reference),
            "exact_attempts": _exact_attempt_summary(block.scout, exact_ids["scout"]),
        },
        "bridge": {
            "archive": bridge_summary,
            "movement": _attempt_terminal_movement(block.bridge, cases["bridge"], reference),
            "exact_attempts": _exact_attempt_summary(block.bridge, exact_ids["bridge"]),
        },
        "judge": {
            "archive": judge_summary,
            "movement": _attempt_terminal_movement(block.judge, cases["judge"], reference),
            "exact_attempts": _exact_attempt_summary(block.judge, exact_ids["judge"]),
        },
        "final_union": {
            "archive": final_summary,
            "near_solve_candidate_count": near_count,
            "near_solve_threshold": {
                "rune_matches": NEAR_SOLVE_RUNES,
                "complete_word_matches": NEAR_SOLVE_COMPLETE_WORDS,
            },
        },
        "first_exact_stage": first_exact_stage,
    }


def _classify_panel(blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(blocks) != len(SCIENCE_BLOCK_IDS):
        raise ValueError("panel classification requires all frozen scientific blocks")
    exact_blocks = 0
    exact_rank_one_blocks = 0
    exact_unique_key_blocks = 0
    near_solve_blocks = 0
    first_stage_counts = {"scout": 0, "bridge": 0, "judge": 0, "none": 0}

    for row in blocks:
        final = row["final_union"]
        archive = final["archive"]
        exact = int(archive["exact_plaintext_count"]) > 0
        exact_blocks += int(exact)
        top_exact = bool(archive["top_scored_candidate_terminal"]["exact_plaintext"])
        exact_rank_one_blocks += int(exact and top_exact)
        unique_key = (
            int(archive["canonical_key_count"]) == 1
            and int(archive["combined_shift_count"]) == 1
        )
        exact_unique_key_blocks += int(exact and unique_key)
        near_solve_blocks += int(int(final["near_solve_candidate_count"]) > 0)
        stage = row.get("first_exact_stage")
        first_stage_counts[str(stage) if stage is not None else "none"] += 1

    promote = (
        exact_blocks >= 2
        and exact_rank_one_blocks == exact_blocks
        and exact_unique_key_blocks == exact_blocks
    )
    if promote:
        decision = "promote"
        rationale = (
            "At least two independent blocks solved exactly; every exact solution was "
            "final-union rank one with one canonical key and one combined shift."
        )
    elif exact_blocks >= 1 or near_solve_blocks >= 2:
        decision = "refine"
        rationale = (
            "The frozen d22 panel produced one exact block, a ranking/uniqueness issue, "
            "or repeated near-solve enrichment requiring unchanged replication or review."
        )
    else:
        decision = "close"
        rationale = (
            "All three frozen d22 blocks completed with zero exact solutions and fewer "
            "than two near-solve blocks. This closes only the frozen Pack 07R budget."
        )
    return {
        "schema": "rdp.two_period_overlay.p13_p31_d22_panel_classification.v1",
        "decision": decision,
        "rationale": rationale,
        "science_block_count": len(blocks),
        "exact_blocks": exact_blocks,
        "exact_rank_one_blocks": exact_rank_one_blocks,
        "exact_unique_key_blocks": exact_unique_key_blocks,
        "near_solve_blocks": near_solve_blocks,
        "first_exact_stage_counts": first_stage_counts,
        "promotion_gate_passed": promote,
        "closure_scope": (
            "only the frozen 1,536-start P13/P31 d22 S2-B1-F1 Pack 07R budget"
        ),
        "fallback_automatically_authorised": False,
    }


def _write_incremental_summaries(
    run_dir: Path,
    *,
    blocks: Sequence[StagedBlock],
    replay_rows: Sequence[Mapping[str, Any]],
) -> None:
    attempts: list[dict[str, Any]] = []
    for block in blocks:
        attempts.extend(_attempt_rows(block))
    _write_json(run_dir / "artifacts/experiment_d/attempt_timing.json", {
        "schema": "rdp.two_period_overlay.p13_p31_d22_attempt_timing.v1",
        "rows": attempts,
    })
    _write_json(run_dir / "artifacts/experiment_d/search_summary.json", {
        "schema": "rdp.two_period_overlay.p13_p31_search_summary.v1",
        "rows": [_search_summary(block) for block in blocks],
    })
    _write_json(run_dir / "artifacts/experiment_d/replay_summary.json", {
        "schema": "rdp.two_period_overlay.p13_p31_replay_summary.v1",
        "all_completed_replays_deterministic": all(
            row.get("replay_deterministic") is True
            and row.get("replay_stored_scores_verified") is True
            for row in replay_rows
        ),
        "rows": list(replay_rows),
    })


def run_p13_p31_two_word_d22_panel(repo_root: Path) -> Path:
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )
    from cipher_development.shared.replay_provenance import build_evaluator_provenance

    repo_root = repo_root.resolve()
    started_at = _utc_now_iso()
    experiment_started = time.perf_counter()
    global_deadline = time.monotonic() + SCIENTIFIC_WALLCLOCK_CEILING_S
    runtime_plan = planned_runtime()
    eval_budget = evaluation_budget_upper()["complete_pack07"]

    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=EXPERIMENT_ID,
        benchmark_id=BENCHMARK.benchmark_id,
        question=(
            "Can the frozen S2-B1-F1 staged solver exactly recover the controlled "
            "308-rune P13/P31 d22 benchmark from three independent 512-start blocks?"
        ),
        hypothesis=(
            "The validated staged method will retain at least two independent exact "
            "P13/P31 solutions at final-union score rank one within the frozen budget."
        ),
        alternative=(
            "The longer second period weakens coordinate signal enough that the frozen "
            "1,536-start d22 panel produces fewer than two valid rank-one exact blocks."
        ),
        decision_rule=(
            "Promote only when all three blocks and all replay surfaces complete and at "
            "least two independent blocks contain one canonical exact solution at "
            "final-union rank one. Refine for one exact block, a ranking/uniqueness issue, "
            "or at least two near-solve blocks. Close only the frozen Pack 07R budget when "
            "all blocks complete with zero exact and fewer than two near-solve blocks. "
            "No terminal metrics may control the Phase A to Phase B continuation."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CONTRACT,
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.HANDOFF,
            FailureMechanism.BUDGET,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_seconds=SCIENTIFIC_WALLCLOCK_CEILING_S,
        budget_evaluations=eval_budget,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "contract_revision": "pack07r_three_block_recovery_v1",
        "supersedes_failed_run_id": (
            "20260726_081457__two_period_overlay__"
            "p13_p31_two_word_d22_staged_panel_v1__4e06b05"
        ),
        "revision_basis": (
            "real d22 canary timing invalidated the original d14-scaled "
            "ten-block runtime projection"
        ),
        "benchmark": BENCHMARK.to_json_dict(),
        "contract_benchmark_ids": [item.benchmark_id for item in CONTRACT_BENCHMARKS],
        "canary": {"block_id": CANARY_BLOCK_ID, "starts": CANARY_STARTS},
        "phase_a_block_ids": list(PHASE_A_BLOCK_IDS),
        "phase_b_block_ids": list(PHASE_B_BLOCK_IDS),
        "starts_per_science_block": STARTS_PER_BLOCK,
        "archive_capacity": ARCHIVE_CAPACITY,
        "staged_ladder": [profile.to_json_dict() for profile in FROZEN_LADDER],
        "stage_sweeps": dict(STAGE_SWEEPS),
        "replay_repeat_count": REPLAY_REPEAT_COUNT,
        "stage_wallclock_ceiling_s": STAGE_WALLCLOCK_CEILING_S,
        "block_wallclock_ceiling_s": BLOCK_WALLCLOCK_CEILING_S,
        "scientific_wallclock_ceiling_s": SCIENTIFIC_WALLCLOCK_CEILING_S,
        "terminal_runtime_reserve_s": TERMINAL_RUNTIME_RESERVE_S,
        "phase_a_continuation_is_operational_only": True,
        "all_search_and_replay_before_terminal_metrics": True,
        "complete_stage_union_retained": True,
        "automatic_fallback_disabled": True,
        "runtime_plan": runtime_plan,
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
            _status(run_dir, "pack07_started", experiment_id=EXPERIMENT_ID)
            _write_json(run_dir / "artifacts/experiment_d/runtime_plan.json", runtime_plan)
            _status(run_dir, "contract_preflight_started")
            preflight = contract_preflight(repo_root)
            _write_json(
                run_dir / "artifacts/experiment_d/contract_preflight.json",
                preflight,
            )
            _status(
                run_dir,
                "contract_preflight_passed",
                target_dimension=BENCHMARK.expected_free_dimension,
            )
            expected_paths = required_artifact_paths()
            _write_json(run_dir / "artifacts/experiment_d/required_artifacts.json", {
                "schema": "rdp.two_period_overlay.p13_p31_required_artifacts.v1",
                "paths": list(expected_paths),
            })

            scout_case, reference = build_rdp_case(
                BENCHMARK,
                scoring_contract=SCOUT_PROFILE.scoring_contract(),
            )
            bridge_case, _ = build_rdp_case(
                BENCHMARK,
                scoring_contract=BRIDGE_PROFILE.scoring_contract(),
            )
            judge_case, _ = build_rdp_case(
                BENCHMARK,
                scoring_contract=JUDGE_PROFILE.scoring_contract(),
            )
            cases = {
                "scout": scout_case,
                "bridge": bridge_case,
                "judge": judge_case,
            }

            completed_blocks: list[StagedBlock] = []
            replay_rows: list[dict[str, Any]] = []

            def execute_block(block_id: int, phase: str, count: int) -> StagedBlock:
                if time.monotonic() >= global_deadline:
                    raise TimeoutError("Pack 07 global scientific ceiling reached")
                _status(
                    run_dir,
                    "block_started",
                    phase=phase,
                    block_id=block_id,
                    starts=count,
                    completed_science_blocks=sum(
                        item.phase == "science" for item in completed_blocks
                    ),
                )
                starts = build_block_starts(BENCHMARK, block_id, count=count)
                block = _run_staged_block(
                    BENCHMARK,
                    block_id,
                    phase,
                    starts,
                    cases,
                    global_deadline=global_deadline,
                )
                persisted, completed = _persist_staged(
                    run_dir=run_dir,
                    run=run,
                    block=block,
                    cases=cases,
                    evaluator_provenance=provenance,
                )
                completed_blocks.append(persisted)
                replay_rows.append({
                    "phase": phase,
                    "block_id": block_id,
                    "replay_deterministic": True,
                    "replay_stored_scores_verified": True,
                    "block_completed_artifact": (
                        _block_root(phase, block_id) / "block_completed.json"
                    ).as_posix(),
                    "total_elapsed_s": completed["total_elapsed_s"],
                })
                _write_incremental_summaries(
                    run_dir,
                    blocks=completed_blocks,
                    replay_rows=replay_rows,
                )
                if time.monotonic() >= global_deadline:
                    raise TimeoutError(
                        "Pack 07 global scientific ceiling reached after persisting block "
                        f"{block_id}"
                    )
                _status(
                    run_dir,
                    "block_completed",
                    phase=phase,
                    block_id=block_id,
                    total_elapsed_s=persisted.total_elapsed_s,
                    scout_candidates=len(persisted.scout.archive.records),
                    bridge_candidates=len(persisted.bridge.archive.records),
                    judge_candidates=len(persisted.judge.archive.records),
                    final_union_candidates=len(persisted.final_archive.records),
                )
                return persisted

            # Real integration canary: same d22 contract and frozen ladder, but no
            # terminal metrics are opened and it is excluded from solve-rate claims.
            execute_block(CANARY_BLOCK_ID, "canary", CANARY_STARTS)

            elapsed_before_phase_a = time.perf_counter() - experiment_started
            phase_a_started = time.perf_counter()
            for block_id in PHASE_A_BLOCK_IDS:
                execute_block(block_id, "science", STARTS_PER_BLOCK)
            phase_a_elapsed = time.perf_counter() - phase_a_started
            gate = _operational_gate(
                phase_a_elapsed_s=phase_a_elapsed,
                elapsed_before_phase_a_s=elapsed_before_phase_a,
                phase_a_replays_verified=True,
                completed_blocks=len(PHASE_A_BLOCK_IDS),
            )
            _write_json(
                run_dir / "artifacts/experiment_d/operational_gate.json",
                gate,
            )
            _status(
                run_dir,
                "phase_a_operational_gate",
                gate_passed=gate["gate_passed"],
                safety_adjusted_projection_s=gate["safety_adjusted_projection_s"],
                hard_scientific_ceiling_s=SCIENTIFIC_WALLCLOCK_CEILING_S,
            )
            if not gate["gate_passed"]:
                raise TimeoutError(
                    "Pack 07R Phase A safety-adjusted runtime projection exceeds the "
                    "frozen twelve-hour scientific ceiling"
                )

            for block_id in PHASE_B_BLOCK_IDS:
                execute_block(block_id, "science", STARTS_PER_BLOCK)

            if time.monotonic() >= global_deadline:
                raise TimeoutError("Pack 07 global scientific ceiling reached before terminal evaluation")

            science_blocks = [
                block for block in completed_blocks if block.phase == "science"
            ]
            if tuple(block.block_id for block in science_blocks) != SCIENCE_BLOCK_IDS:
                raise RuntimeError("Pack 07 did not complete the frozen scientific block set")
            if not all(
                row["replay_deterministic"] is True
                and row["replay_stored_scores_verified"] is True
                for row in replay_rows
            ):
                raise RuntimeError("Pack 07 replay verification failed")

            # Terminal-only block begins after canary plus all three science blocks have
            # completed search, persistence and replay.
            _status(run_dir, "terminal_evaluation_started")
            terminal_started = time.perf_counter()
            science_terminal = [
                _terminal_block(block, cases, reference) for block in science_blocks
            ]
            canary_block = next(
                block for block in completed_blocks if block.phase == "canary"
            )
            canary_terminal = _terminal_block(canary_block, cases, reference)
            classification = _classify_panel(science_terminal)
            terminal_elapsed = time.perf_counter() - terminal_started
            if time.monotonic() > global_deadline:
                raise TimeoutError(
                    "Pack 07 terminal diagnostics exceeded the frozen twelve-hour "
                    "scientific ceiling"
                )
            terminal_artifact = {
                "schema": "rdp.two_period_overlay.p13_p31_d22_terminal_evaluation.v1",
                "terminal_metrics_opened_after_all_search_and_replay": True,
                "canary_excluded_from_scientific_classification": True,
                "canary": canary_terminal,
                "science_blocks": science_terminal,
                "classification": classification,
            }
            _write_json(
                run_dir / "artifacts/experiment_d/terminal_evaluation.json",
                terminal_artifact,
            )

            timing = {
                "schema": "rdp.two_period_overlay.p13_p31_d22_execution_timing.v1",
                "started_at_utc": started_at,
                "finished_at_utc": _utc_now_iso(),
                "scientific_work_elapsed_s": time.perf_counter() - experiment_started,
                "hard_scientific_ceiling_s": SCIENTIFIC_WALLCLOCK_CEILING_S,
                "phase_a_elapsed_s": phase_a_elapsed,
                "phase_a_gate": gate,
                "terminal_diagnostics_elapsed_s": terminal_elapsed,
                "blocks": [
                    {
                        "phase": block.phase,
                        "block_id": block.block_id,
                        "starts": len(block.starts),
                        "search_elapsed_s": block.search_elapsed_s,
                        "total_elapsed_s": block.total_elapsed_s,
                    }
                    for block in completed_blocks
                ],
                "attempt_timing_artifact": "artifacts/experiment_d/attempt_timing.json",
            }
            _write_json(run_dir / "artifacts/execution_timing.json", timing)

            summary = {
                "schema": "rdp.two_period_overlay.p13_p31_d22_panel_summary.v1",
                "benchmark_id": BENCHMARK.benchmark_id,
                "canary_starts": CANARY_STARTS,
                "science_blocks": len(science_blocks),
                "starts_per_block": STARTS_PER_BLOCK,
                "total_science_starts": len(science_blocks) * STARTS_PER_BLOCK,
                "all_replays_deterministic": True,
                "all_stored_scores_verified": True,
                "all_search_and_replay_before_terminal_metrics": True,
                "complete_stage_union_retained": True,
                "runtime_plan": runtime_plan,
                "operational_gate": gate,
                "classification": classification,
                "timing": timing,
                "artifacts": {
                    "contract_preflight": "artifacts/experiment_d/contract_preflight.json",
                    "operational_gate": "artifacts/experiment_d/operational_gate.json",
                    "search_summary": "artifacts/experiment_d/search_summary.json",
                    "replay_summary": "artifacts/experiment_d/replay_summary.json",
                    "attempt_timing": "artifacts/experiment_d/attempt_timing.json",
                    "terminal_evaluation": "artifacts/experiment_d/terminal_evaluation.json",
                    "required_artifacts": "artifacts/experiment_d/required_artifacts.json",
                },
            }
            _write_json(
                run_dir / "artifacts/p13_p31_two_word_d22_staged_panel_summary.json",
                summary,
            )

            decision = ExperimentDecision(classification["decision"])
            _status(
                run_dir,
                "scientific_classification_complete",
                decision=classification["decision"],
                exact_blocks=classification["exact_blocks"],
                near_solve_blocks=classification["near_solve_blocks"],
            )
            result_path = run.finish(
                decision=decision,
                stop_reason="done",
                result_summary={
                    "artifact": "artifacts/p13_p31_two_word_d22_staged_panel_summary.json",
                    "benchmark_id": BENCHMARK.benchmark_id,
                    "science_block_count": len(science_blocks),
                    "starts_per_block": STARTS_PER_BLOCK,
                    "total_science_starts": len(science_blocks) * STARTS_PER_BLOCK,
                    "all_replays_deterministic": True,
                    "all_stored_scores_verified": True,
                    "promotion_gate_passed": classification["promotion_gate_passed"],
                    "exact_blocks": classification["exact_blocks"],
                    "near_solve_blocks": classification["near_solve_blocks"],
                    "first_exact_stage_counts": classification["first_exact_stage_counts"],
                    "timing": timing,
                },
                reference_evaluation={
                    "candidate_specific_truth_emitted": False,
                    "terminal_artifact": "artifacts/experiment_d/terminal_evaluation.json",
                    "classification": classification,
                    "science_blocks": science_terminal,
                    "canary": canary_terminal,
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
    "ARCHIVE_CAPACITY",
    "BENCHMARK",
    "CANARY_BLOCK_ID",
    "CANARY_STARTS",
    "CONTRACT_BENCHMARKS",
    "EXPERIMENT_ID",
    "FROZEN_LADDER",
    "NEAR_SOLVE_COMPLETE_WORDS",
    "NEAR_SOLVE_RUNES",
    "PHASE_A_BLOCK_IDS",
    "PHASE_B_BLOCK_IDS",
    "SCIENCE_BLOCK_IDS",
    "SCIENTIFIC_WALLCLOCK_CEILING_S",
    "STARTS_PER_BLOCK",
    "TERMINAL_RUNTIME_RESERVE_S",
    "_classify_panel",
    "_operational_gate",
    "build_block_starts",
    "contract_preflight",
    "evaluation_budget_upper",
    "panel_seed",
    "planned_runtime",
    "required_artifact_paths",
    "run_p13_p31_two_word_d22_panel",
]
