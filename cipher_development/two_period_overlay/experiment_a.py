from __future__ import annotations

"""WP6 Experiment A standard panel and positional confirmation.

This is a campaign-specific orchestration layer over the existing coordinate
search, candidate archive, replay and review-pack contracts. It does not add a
new solver framework.

The panel deliberately performs all search, persistence and replay for both
benchmarks before opening current-run terminal truth metrics.
"""

import hashlib
import json
import shutil
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
    EXACT_EXTRA_CRIB_BENCHMARKS,
    MASTER_SEED,
)
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import (
    B1,
    F1,
    RECORDED_J0,
    S2,
    ScorerProfile,
)
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
    latest_completed_experiment,
)

EXPERIMENT_ID = "experiment_a_standard_panel_v1"
SOURCE_HANDOFF_EXPERIMENT_ID = "staged_d8_handoff_v1"

PRIMARY_BENCHMARK = EXACT_EXTRA_CRIB_BENCHMARKS[0]
POSITIONAL_BENCHMARK = EXACT_EXTRA_CRIB_BENCHMARKS[1]

BASELINE_PROFILE = RECORDED_J0
SCOUT_PROFILE = S2
BRIDGE_PROFILE = B1
JUDGE_PROFILE = F1
FROZEN_LADDER = (SCOUT_PROFILE, BRIDGE_PROFILE, JUDGE_PROFILE)

PRIMARY_BLOCK_IDS = tuple(range(31, 39))
POSITIONAL_BLOCK_IDS = tuple(range(41, 45))
STARTS_PER_BLOCK = 128
ARCHIVE_CAPACITY = 512
BASELINE_SWEEPS = 4
ARM_WALLCLOCK_CEILING_S = 30.0 * 60.0
EXPERIMENT_WALLCLOCK_CEILING_S = 3.0 * 60.0 * 60.0
REPLAY_REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12

# Planning evidence returned by Pack 02A/02B. These numbers are recorded only
# to make the expected one-to-two-hour scale explicit; they do not control
# search, stopping or truth handling.
PLANNED_SECONDS_PER_J0_START = 2.02522533750016
PLANNED_SECONDS_PER_STAGED_START = 218.17845449998276 / 96.0
PLANNED_RUNTIME_SAFETY_FACTOR = 1.25
OVERNIGHT_RATE_THRESHOLD = 0.50


@dataclass(frozen=True, slots=True)
class BaselineBlock:
    benchmark: BenchmarkSpec
    block_id: int
    starts: tuple[dict[str, Any], ...]
    search: StageOutcome
    elapsed_s: float


@dataclass(frozen=True, slots=True)
class StagedBlock:
    benchmark: BenchmarkSpec
    block_id: int
    starts: tuple[dict[str, Any], ...]
    scout: StageOutcome
    bridge: StageOutcome
    judge: StageOutcome
    final_archive: CandidateArchive
    final_rescore_elapsed_s: float
    final_rescore_evaluations: int
    elapsed_s: float


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def panel_seed(
    benchmark_id: str,
    block_id: int,
    stage_id: str,
    token: str,
) -> int:
    if not benchmark_id or not stage_id or not token:
        raise ValueError("benchmark_id, stage_id and token must be non-empty")
    if block_id < 0:
        raise ValueError("block_id must be non-negative")
    payload = (
        f"{MASTER_SEED}:wp6-pack03a:{benchmark_id}:{block_id}:{stage_id}:{token}"
    ).encode("utf-8")
    return int.from_bytes(
        hashlib.blake2b(payload, digest_size=8, person=b"rdp-wp6-03a").digest(),
        "big",
    )


def build_block_starts(
    benchmark: BenchmarkSpec,
    block_id: int,
    *,
    count: int = STARTS_PER_BLOCK,
) -> tuple[dict[str, Any], ...]:
    if count <= 0:
        raise ValueError("count must be positive")
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


def planned_runtime() -> dict[str, Any]:
    primary_starts = len(PRIMARY_BLOCK_IDS) * STARTS_PER_BLOCK
    positional_starts = len(POSITIONAL_BLOCK_IDS) * STARTS_PER_BLOCK
    central = (
        primary_starts * PLANNED_SECONDS_PER_J0_START
        + (primary_starts + positional_starts) * PLANNED_SECONDS_PER_STAGED_START
    )
    return {
        "schema": "rdp.two_period_overlay.experiment_a_runtime_plan.v1",
        "basis": {
            "j0_seconds_per_start": PLANNED_SECONDS_PER_J0_START,
            "staged_seconds_per_start": PLANNED_SECONDS_PER_STAGED_START,
            "source": "accepted Pack 02A J0 timing and Pack 02B staged timing",
        },
        "primary_blocks": len(PRIMARY_BLOCK_IDS),
        "positional_blocks": len(POSITIONAL_BLOCK_IDS),
        "starts_per_block": STARTS_PER_BLOCK,
        "primary_starts_per_arm": primary_starts,
        "positional_staged_starts": positional_starts,
        "central_elapsed_s": central,
        "safety_factor": PLANNED_RUNTIME_SAFETY_FACTOR,
        "safety_adjusted_elapsed_s": central * PLANNED_RUNTIME_SAFETY_FACTOR,
        "target_description": "approximately one to two hours on the measured home-PC surface",
    }


def _require_source_handoff(repo_root: Path) -> dict[str, Any]:
    source_run = latest_completed_experiment(repo_root, SOURCE_HANDOFF_EXPERIMENT_ID)
    result_path = source_run / "artifacts/experiment_result.json"
    result = _read_json(result_path)
    summary = result.get("result_summary")
    terminal = result.get("reference_evaluation")
    if not isinstance(summary, Mapping) or not isinstance(terminal, Mapping):
        raise RuntimeError("Pack 02B source result is incomplete")
    best = terminal.get("best_final_candidate_terminal")
    if (
        summary.get("all_replays_deterministic") is not True
        or summary.get("all_prior_surfaces_persisted") is not True
        or not isinstance(best, Mapping)
        or best.get("exact_plaintext") is not True
        or best.get("canonical_key_equal") is not True
        or best.get("combined_shift_equal") is not True
    ):
        raise RuntimeError("Pack 02B did not satisfy the Experiment A progression gate")
    return {
        "run_dir": source_run,
        "run_id": source_run.name,
        "result_path": result_path,
        "result_sha256": _sha256(result_path),
    }


def _stage_seed_factory(benchmark: BenchmarkSpec, block_id: int, arm_id: str):
    def seed_factory(stage_id: str, token: str) -> int:
        return panel_seed(
            benchmark.benchmark_id,
            block_id,
            f"{arm_id}:{stage_id}",
            token,
        )
    return seed_factory


def _run_baseline_block(
    benchmark: BenchmarkSpec,
    block_id: int,
    starts: tuple[dict[str, Any], ...],
    search_case: Any,
) -> BaselineBlock:
    started = time.perf_counter()
    search = _run_stage(
        stage_id="search",
        profile=BASELINE_PROFILE,
        search_case=search_case,
        inputs=starts,
        sweeps=BASELINE_SWEEPS,
        benchmark=benchmark,
        seed_factory=_stage_seed_factory(benchmark, block_id, "baseline"),
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=ARM_WALLCLOCK_CEILING_S,
        provenance_source="experiment_a_standard_panel",
    )
    return BaselineBlock(
        benchmark=benchmark,
        block_id=block_id,
        starts=starts,
        search=search,
        elapsed_s=time.perf_counter() - started,
    )


def _run_staged_block(
    benchmark: BenchmarkSpec,
    block_id: int,
    starts: tuple[dict[str, Any], ...],
    scout_case: Any,
    bridge_case: Any,
    judge_case: Any,
) -> StagedBlock:
    started = time.perf_counter()
    seed_factory = _stage_seed_factory(benchmark, block_id, "staged")
    scout = _run_stage(
        stage_id="scout",
        profile=SCOUT_PROFILE,
        search_case=scout_case,
        inputs=starts,
        sweeps=STAGE_SWEEPS[SCOUT_PROFILE.profile_id],
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=ARM_WALLCLOCK_CEILING_S,
        provenance_source="experiment_a_standard_panel",
    )
    bridge = _run_stage(
        stage_id="bridge",
        profile=BRIDGE_PROFILE,
        search_case=bridge_case,
        inputs=scout.archive.records,
        sweeps=STAGE_SWEEPS[BRIDGE_PROFILE.profile_id],
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=ARM_WALLCLOCK_CEILING_S,
        provenance_source="experiment_a_standard_panel",
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
        benchmark=benchmark,
        seed_factory=seed_factory,
        archive_capacity=ARCHIVE_CAPACITY,
        stage_safety_seconds=ARM_WALLCLOCK_CEILING_S,
        provenance_source="experiment_a_standard_panel",
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
    final_archive, rescore_elapsed, rescore_evaluations = _rescore_final_union(
        all_records,
        judge_case,
        JUDGE_PROFILE,
        first_stage,
        archive_capacity=ARCHIVE_CAPACITY,
        provenance_source="experiment_a_standard_panel",
    )
    return StagedBlock(
        benchmark=benchmark,
        block_id=block_id,
        starts=starts,
        scout=scout,
        bridge=bridge,
        judge=judge,
        final_archive=final_archive,
        final_rescore_elapsed_s=rescore_elapsed,
        final_rescore_evaluations=rescore_evaluations,
        elapsed_s=time.perf_counter() - started,
    )


def _block_root(benchmark: BenchmarkSpec, block_id: int) -> Path:
    return (
        Path("artifacts/experiment_a")
        / benchmark.benchmark_id
        / f"block_{block_id:02d}"
    )


def _persist_baseline(
    *,
    run_dir: Path,
    run: Any,
    block: BaselineBlock,
    search_case: Any,
    evaluator_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    root = _block_root(block.benchmark, block.block_id)
    _write_json(run_dir / root / "starts.json", {
        "schema": "rdp.two_period_overlay.experiment_a_starts.v1",
        "benchmark_id": block.benchmark.benchmark_id,
        "block_id": block.block_id,
        "rows": list(block.starts),
    })
    summary = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.search,
        search_case=search_case,
        evaluator_provenance=evaluator_provenance,
        artifact_root=root / "baseline",
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_purpose="replay",
        selection_label=f"baseline_block_{block.block_id:02d}__all",
        evaluator_id=(
            f"two_period_overlay_experiment_a_baseline_"
            f"{block.benchmark.benchmark_id}_{block.block_id:02d}"
        ),
    )
    summary["block_elapsed_s"] = block.elapsed_s
    return summary


def _persist_staged(
    *,
    run_dir: Path,
    run: Any,
    block: StagedBlock,
    cases: Mapping[str, Any],
    evaluator_provenance: Mapping[str, Any],
) -> dict[str, Any]:
    root = _block_root(block.benchmark, block.block_id)
    _write_json(run_dir / root / "starts.json", {
        "schema": "rdp.two_period_overlay.experiment_a_starts.v1",
        "benchmark_id": block.benchmark.benchmark_id,
        "block_id": block.block_id,
        "rows": list(block.starts),
    })
    scout = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.scout,
        search_case=cases["scout"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root / "staged",
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"staged_block_{block.block_id:02d}_scout__all",
        evaluator_id=(
            f"two_period_overlay_experiment_a_scout_"
            f"{block.benchmark.benchmark_id}_{block.block_id:02d}"
        ),
    )
    bridge = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.bridge,
        search_case=cases["bridge"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root / "staged",
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"staged_block_{block.block_id:02d}_bridge__all",
        evaluator_id=(
            f"two_period_overlay_experiment_a_bridge_"
            f"{block.benchmark.benchmark_id}_{block.block_id:02d}"
        ),
    )
    judge = _write_stage_and_replay(
        run_dir=run_dir,
        run=run,
        stage=block.judge,
        search_case=cases["judge"],
        evaluator_provenance=evaluator_provenance,
        artifact_root=root / "staged",
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"staged_block_{block.block_id:02d}_judge__all",
        evaluator_id=(
            f"two_period_overlay_experiment_a_judge_"
            f"{block.benchmark.benchmark_id}_{block.block_id:02d}"
        ),
    )
    final = _write_final_union_and_replay(
        run_dir=run_dir,
        run=run,
        archive=block.final_archive,
        search_case=cases["judge"],
        profile=JUDGE_PROFILE,
        evaluator_provenance=evaluator_provenance,
        artifact_root=root / "staged",
        experiment_id=EXPERIMENT_ID,
        benchmark=block.benchmark,
        selection_label=f"staged_block_{block.block_id:02d}_final_union__all",
        evaluator_id=(
            f"two_period_overlay_experiment_a_final_"
            f"{block.benchmark.benchmark_id}_{block.block_id:02d}"
        ),
    )
    return {
        "block_elapsed_s": block.elapsed_s,
        "scout": scout,
        "bridge": bridge,
        "judge": judge,
        "final_union": {
            **final,
            "rescore_elapsed_s": block.final_rescore_elapsed_s,
            "rescore_evaluations": block.final_rescore_evaluations,
        },
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


def _exact_attempt_summary(
    stage: StageOutcome,
    exact_ids: set[str],
) -> dict[str, Any]:
    exact_rows = [
        row for row in stage.attempt_rows if row["candidate_id"] in exact_ids
    ]
    cumulative = 0.0
    first_elapsed: float | None = None
    first_input: int | None = None
    for row in stage.attempt_rows:
        cumulative += float(row["elapsed_s"])
        if row["candidate_id"] in exact_ids:
            first_elapsed = cumulative
            first_input = int(row["input_index"])
            break
    return {
        "exact_attempt_count": len(exact_rows),
        "first_exact_input_index": first_input,
        "post_hoc_cumulative_attempt_elapsed_s_to_first_exact": first_elapsed,
    }


def _baseline_terminal(
    block: BaselineBlock,
    search_case: Any,
    reference: Any,
) -> dict[str, Any]:
    exact_ids = _exact_candidate_ids(block.search.archive.records, search_case, reference)
    return {
        "archive": _stage_terminal_summary(
            block.search.archive.records,
            BASELINE_PROFILE,
            search_case,
            reference,
        ),
        "movement": _attempt_terminal_movement(block.search, search_case, reference),
        "exact_attempts": _exact_attempt_summary(block.search, exact_ids),
    }


def _staged_terminal(
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
    return {
        "scout": {
            "archive": _stage_terminal_summary(
                block.scout.archive.records, SCOUT_PROFILE, cases["scout"], reference
            ),
            "movement": _attempt_terminal_movement(
                block.scout, cases["scout"], reference
            ),
            "exact_attempts": _exact_attempt_summary(block.scout, exact_ids["scout"]),
        },
        "bridge": {
            "archive": _stage_terminal_summary(
                block.bridge.archive.records, BRIDGE_PROFILE, cases["bridge"], reference
            ),
            "movement": _attempt_terminal_movement(
                block.bridge, cases["bridge"], reference
            ),
            "exact_attempts": _exact_attempt_summary(block.bridge, exact_ids["bridge"]),
        },
        "judge": {
            "archive": _stage_terminal_summary(
                block.judge.archive.records, JUDGE_PROFILE, cases["judge"], reference
            ),
            "movement": _attempt_terminal_movement(
                block.judge, cases["judge"], reference
            ),
            "exact_attempts": _exact_attempt_summary(block.judge, exact_ids["judge"]),
        },
        "final_union": {
            "archive": _stage_terminal_summary(
                block.final_archive.records, JUDGE_PROFILE, cases["judge"], reference
            ),
        },
        "first_exact_stage": first_exact_stage,
    }


def _block_exact(terminal: Mapping[str, Any], arm_id: str) -> bool:
    if arm_id == "baseline":
        archive = terminal["archive"]
    else:
        archive = terminal["final_union"]["archive"]
    return int(archive["exact_plaintext_count"]) > 0


def _aggregate_panel(
    *,
    primary_baseline: Sequence[Mapping[str, Any]],
    primary_staged: Sequence[Mapping[str, Any]],
    positional_staged: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    primary_baseline_exact = sum(_block_exact(row, "baseline") for row in primary_baseline)
    primary_staged_exact = sum(_block_exact(row, "staged") for row in primary_staged)
    positional_exact = sum(_block_exact(row, "staged") for row in positional_staged)

    primary_staged_rate = primary_staged_exact / len(primary_staged)
    positional_rate = positional_exact / len(positional_staged)
    source_replicated = primary_staged_exact > 0
    position_confirmed = positional_exact > 0
    promote = source_replicated and position_confirmed

    if min(primary_staged_rate, positional_rate) < OVERNIGHT_RATE_THRESHOLD:
        overnight = {
            "experiment_a_overnight_recommended": True,
            "reason": (
                "At least one staged exact-block rate is below the predeclared "
                f"{OVERNIGHT_RATE_THRESHOLD:.0%} replication threshold."
            ),
            "recommended_target": "Experiment A replication and solve-rate estimation",
        }
    else:
        overnight = {
            "experiment_a_overnight_recommended": False,
            "reason": (
                "Both staged exact-block rates meet the replication threshold; repeating "
                "the same assisted d8 search overnight would add less information than "
                "candidate-branch scaling or a later full-d16 strategy."
            ),
            "recommended_target": "Experiment B scaling, then full d16 if B evidence allows",
        }

    return {
        "schema": "rdp.two_period_overlay.experiment_a_aggregate.v1",
        "primary": {
            "block_count": len(primary_staged),
            "baseline_exact_blocks": primary_baseline_exact,
            "baseline_exact_block_rate": primary_baseline_exact / len(primary_baseline),
            "staged_exact_blocks": primary_staged_exact,
            "staged_exact_block_rate": primary_staged_rate,
        },
        "positional_confirmation": {
            "block_count": len(positional_staged),
            "staged_exact_blocks": positional_exact,
            "staged_exact_block_rate": positional_rate,
        },
        "source_exact_solve_replicated": source_replicated,
        "offset_81_position_confirmed": position_confirmed,
        "promotion_gate_passed": promote,
        "overnight_strategy": overnight,
    }


def _search_summary(outcome: BaselineBlock | StagedBlock) -> dict[str, Any]:
    if isinstance(outcome, BaselineBlock):
        return {
            "benchmark_id": outcome.benchmark.benchmark_id,
            "block_id": outcome.block_id,
            "arm_id": "baseline",
            "elapsed_s": outcome.elapsed_s,
            "stages": {"search": outcome.search.to_search_summary()},
        }
    return {
        "benchmark_id": outcome.benchmark.benchmark_id,
        "block_id": outcome.block_id,
        "arm_id": "staged",
        "elapsed_s": outcome.elapsed_s,
        "stages": {
            "scout": outcome.scout.to_search_summary(),
            "bridge": outcome.bridge.to_search_summary(),
            "judge": outcome.judge.to_search_summary(),
            "final_union": {
                "candidate_count": len(outcome.final_archive.records),
                "rescore_elapsed_s": outcome.final_rescore_elapsed_s,
                "rescore_evaluations": outcome.final_rescore_evaluations,
            },
        },
    }


def run_experiment_a_standard_panel(repo_root: Path) -> Path:
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
    source = _require_source_handoff(repo_root)
    planned = planned_runtime()
    experiment_started_at = _utc_now_iso()
    experiment_started = time.perf_counter()
    global_deadline = time.monotonic() + EXPERIMENT_WALLCLOCK_CEILING_S

    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id=EXPERIMENT_ID,
        benchmark_id=PRIMARY_BENCHMARK.benchmark_id,
        question=(
            "Across independent deterministic blocks, how reliably does the frozen "
            "S2-B1-F1 ladder solve the offset-206 d8 benchmark relative to the exact "
            "recorded J0 high-order baseline, and does the result generalise to the "
            "equally ranked offset-81 d8 crib?"
        ),
        hypothesis=(
            "The staged arm will independently reproduce the exact offset-206 solve, "
            "retain a stronger exact/near-truth rate than J0, and produce at least one "
            "exact solve at offset 81."
        ),
        alternative=(
            "The Pack 02B exact solve was seed-specific, J0 is equally or more effective, "
            "or the method does not generalise to offset 81."
        ),
        decision_rule=(
            "Promote Experiment A when all blocks and replays complete, at least one new "
            "primary staged block solves exactly, and at least one positional staged block "
            "solves exactly. Report J0 versus staged solve rates without using truth to "
            "alter budgets. Recommend an Experiment A overnight only when either staged "
            "exact-block rate is below 50 percent; otherwise reserve overnight work for "
            "Experiment B scaling or a later full-d16 strategy."
        ),
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.BENCHMARK_ONLY,
        mechanisms=(
            FailureMechanism.CANDIDATE_SUPPLY,
            FailureMechanism.RANKING,
            FailureMechanism.EVIDENCE_REPRODUCIBILITY,
        ),
        budget_seconds=EXPERIMENT_WALLCLOCK_CEILING_S,
        budget_evaluations=8_000_000,
        lesson_ids=("CSL-004", "CSL-005", "CSL-007"),
    )
    configuration = {
        "primary_benchmark": PRIMARY_BENCHMARK.to_json_dict(),
        "positional_benchmark": POSITIONAL_BENCHMARK.to_json_dict(),
        "primary_block_ids": list(PRIMARY_BLOCK_IDS),
        "positional_block_ids": list(POSITIONAL_BLOCK_IDS),
        "starts_per_block": STARTS_PER_BLOCK,
        "baseline": {
            "profile": BASELINE_PROFILE.to_json_dict(),
            "sweeps": BASELINE_SWEEPS,
        },
        "staged_ladder": [profile.to_json_dict() for profile in FROZEN_LADDER],
        "stage_sweeps": dict(STAGE_SWEEPS),
        "equal_arm_archive_capacity": ARCHIVE_CAPACITY,
        "equal_arm_wallclock_ceiling_s": ARM_WALLCLOCK_CEILING_S,
        "primary_arms_share_identical_start_vectors": True,
        "search_signal_only_stopping": True,
        "all_current_run_search_and_replay_before_terminal_metrics": True,
        "planned_runtime": planned,
        "overnight_rate_threshold": OVERNIGHT_RATE_THRESHOLD,
        "source_pack02b": {
            "run_id": source["run_id"],
            "result_sha256": source["result_sha256"],
        },
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
                    profile.scoring_contract()
                    for profile in (
                        BASELINE_PROFILE,
                        SCOUT_PROFILE,
                        BRIDGE_PROFILE,
                        JUDGE_PROFILE,
                    )
                ),
                require_assets=True,
            )
            source_copy = run_dir / "artifacts/experiment_a/source_pack02b_experiment_result.json"
            source_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source["result_path"], source_copy)
            _write_json(run_dir / "artifacts/experiment_a/runtime_plan.json", planned)

            cases: dict[str, dict[str, Any]] = {}
            references: dict[str, Any] = {}
            for benchmark in (PRIMARY_BENCHMARK, POSITIONAL_BENCHMARK):
                baseline_case, reference = build_rdp_case(
                    benchmark,
                    scoring_contract=BASELINE_PROFILE.scoring_contract(),
                )
                scout_case, _ = build_rdp_case(
                    benchmark,
                    scoring_contract=SCOUT_PROFILE.scoring_contract(),
                )
                bridge_case, _ = build_rdp_case(
                    benchmark,
                    scoring_contract=BRIDGE_PROFILE.scoring_contract(),
                )
                judge_case, _ = build_rdp_case(
                    benchmark,
                    scoring_contract=JUDGE_PROFILE.scoring_contract(),
                )
                cases[benchmark.benchmark_id] = {
                    "baseline": baseline_case,
                    "scout": scout_case,
                    "bridge": bridge_case,
                    "judge": judge_case,
                }
                references[benchmark.benchmark_id] = reference

            primary_baseline_blocks: list[BaselineBlock] = []
            primary_staged_blocks: list[StagedBlock] = []
            positional_staged_blocks: list[StagedBlock] = []
            search_summaries: list[dict[str, Any]] = []
            replay_summaries: list[dict[str, Any]] = []
            attempt_rows: list[dict[str, Any]] = []

            search_started = time.perf_counter()
            for block_id in PRIMARY_BLOCK_IDS:
                if time.monotonic() >= global_deadline:
                    raise TimeoutError("Experiment A global wall-clock ceiling reached")
                starts = build_block_starts(PRIMARY_BENCHMARK, block_id)
                primary_cases = cases[PRIMARY_BENCHMARK.benchmark_id]
                baseline = _run_baseline_block(
                    PRIMARY_BENCHMARK,
                    block_id,
                    starts,
                    primary_cases["baseline"],
                )
                staged = _run_staged_block(
                    PRIMARY_BENCHMARK,
                    block_id,
                    starts,
                    primary_cases["scout"],
                    primary_cases["bridge"],
                    primary_cases["judge"],
                )
                primary_baseline_blocks.append(baseline)
                primary_staged_blocks.append(staged)
                search_summaries.extend((_search_summary(baseline), _search_summary(staged)))

            for block_id in POSITIONAL_BLOCK_IDS:
                if time.monotonic() >= global_deadline:
                    raise TimeoutError("Experiment A global wall-clock ceiling reached")
                starts = build_block_starts(POSITIONAL_BENCHMARK, block_id)
                positional_cases = cases[POSITIONAL_BENCHMARK.benchmark_id]
                staged = _run_staged_block(
                    POSITIONAL_BENCHMARK,
                    block_id,
                    starts,
                    positional_cases["scout"],
                    positional_cases["bridge"],
                    positional_cases["judge"],
                )
                positional_staged_blocks.append(staged)
                search_summaries.append(_search_summary(staged))
            search_elapsed = time.perf_counter() - search_started

            # Persist and replay every current-run surface before opening terminal truth.
            replay_started = time.perf_counter()
            for baseline, staged in zip(primary_baseline_blocks, primary_staged_blocks):
                primary_cases = cases[PRIMARY_BENCHMARK.benchmark_id]
                baseline_replay = _persist_baseline(
                    run_dir=run_dir,
                    run=run,
                    block=baseline,
                    search_case=primary_cases["baseline"],
                    evaluator_provenance=provenance,
                )
                staged_replay = _persist_staged(
                    run_dir=run_dir,
                    run=run,
                    block=staged,
                    cases=primary_cases,
                    evaluator_provenance=provenance,
                )
                replay_summaries.extend((
                    {
                        "benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
                        "block_id": baseline.block_id,
                        "arm_id": "baseline",
                        **baseline_replay,
                    },
                    {
                        "benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
                        "block_id": staged.block_id,
                        "arm_id": "staged",
                        **staged_replay,
                    },
                ))
                for row in baseline.search.attempt_rows:
                    attempt_rows.append({
                        "benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
                        "block_id": baseline.block_id,
                        "arm_id": "baseline",
                        **dict(row),
                    })
                for stage in (staged.scout, staged.bridge, staged.judge):
                    for row in stage.attempt_rows:
                        attempt_rows.append({
                            "benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
                            "block_id": staged.block_id,
                            "arm_id": "staged",
                            **dict(row),
                        })

            for staged in positional_staged_blocks:
                positional_cases = cases[POSITIONAL_BENCHMARK.benchmark_id]
                staged_replay = _persist_staged(
                    run_dir=run_dir,
                    run=run,
                    block=staged,
                    cases=positional_cases,
                    evaluator_provenance=provenance,
                )
                replay_summaries.append({
                    "benchmark_id": POSITIONAL_BENCHMARK.benchmark_id,
                    "block_id": staged.block_id,
                    "arm_id": "staged",
                    **staged_replay,
                })
                for stage in (staged.scout, staged.bridge, staged.judge):
                    for row in stage.attempt_rows:
                        attempt_rows.append({
                            "benchmark_id": POSITIONAL_BENCHMARK.benchmark_id,
                            "block_id": staged.block_id,
                            "arm_id": "staged",
                            **dict(row),
                        })

            replay_elapsed = time.perf_counter() - replay_started
            all_replays = all(
                (
                    row.get("replay_deterministic") is True
                    and row.get("replay_stored_scores_verified") is True
                )
                if row["arm_id"] == "baseline"
                else all(
                    row[stage_id].get("replay_deterministic") is True
                    and row[stage_id].get("replay_stored_scores_verified") is True
                    for stage_id in ("scout", "bridge", "judge", "final_union")
                )
                for row in replay_summaries
            )
            if not all_replays:
                raise RuntimeError("Experiment A replay verification failed")

            _write_json(run_dir / "artifacts/experiment_a/attempt_timing.json", {
                "schema": "rdp.two_period_overlay.experiment_a_attempt_timing.v1",
                "rows": attempt_rows,
            })
            _write_json(run_dir / "artifacts/experiment_a/search_summary.json", {
                "schema": "rdp.two_period_overlay.experiment_a_search_summary.v1",
                "rows": search_summaries,
            })
            _write_json(run_dir / "artifacts/experiment_a/replay_summary.json", {
                "schema": "rdp.two_period_overlay.experiment_a_replay_summary.v1",
                "all_replays_deterministic": all_replays,
                "rows": replay_summaries,
            })

            # Terminal-only block begins after every current-run search and replay.
            terminal_started = time.perf_counter()
            primary_reference = references[PRIMARY_BENCHMARK.benchmark_id]
            primary_cases = cases[PRIMARY_BENCHMARK.benchmark_id]
            positional_reference = references[POSITIONAL_BENCHMARK.benchmark_id]
            positional_cases = cases[POSITIONAL_BENCHMARK.benchmark_id]

            primary_baseline_terminal = [
                {
                    "block_id": block.block_id,
                    **_baseline_terminal(
                        block,
                        primary_cases["baseline"],
                        primary_reference,
                    ),
                }
                for block in primary_baseline_blocks
            ]
            primary_staged_terminal = [
                {
                    "block_id": block.block_id,
                    **_staged_terminal(block, primary_cases, primary_reference),
                }
                for block in primary_staged_blocks
            ]
            positional_staged_terminal = [
                {
                    "block_id": block.block_id,
                    **_staged_terminal(block, positional_cases, positional_reference),
                }
                for block in positional_staged_blocks
            ]
            aggregate = _aggregate_panel(
                primary_baseline=primary_baseline_terminal,
                primary_staged=primary_staged_terminal,
                positional_staged=positional_staged_terminal,
            )
            terminal_elapsed = time.perf_counter() - terminal_started

            timing = {
                "schema": "rdp.two_period_overlay.experiment_a_execution_timing.v1",
                "started_at_utc": experiment_started_at,
                "finished_at_utc": _utc_now_iso(),
                "scientific_work_elapsed_s": time.perf_counter() - experiment_started,
                "scope": (
                    "Eight matched primary baseline/staged blocks and four positional "
                    "staged blocks, including persistence, replay and terminal diagnostics."
                ),
                "phases": {
                    "search_elapsed_s": search_elapsed,
                    "replay_elapsed_s": replay_elapsed,
                    "terminal_diagnostics_elapsed_s": terminal_elapsed,
                },
                "blocks": [
                    {
                        "benchmark_id": row["benchmark_id"],
                        "block_id": row["block_id"],
                        "arm_id": row["arm_id"],
                        "elapsed_s": row["elapsed_s"],
                    }
                    for row in search_summaries
                ],
                "attempt_timing_artifact": "artifacts/experiment_a/attempt_timing.json",
            }
            _write_json(run_dir / "artifacts/execution_timing.json", timing)

            summary_artifact = {
                "schema": "rdp.two_period_overlay.experiment_a_standard_panel_summary.v1",
                "primary_benchmark_id": PRIMARY_BENCHMARK.benchmark_id,
                "positional_benchmark_id": POSITIONAL_BENCHMARK.benchmark_id,
                "planned_runtime": planned,
                "all_replays_deterministic": all_replays,
                "all_prior_surfaces_persisted": True,
                "all_current_run_search_and_replay_before_terminal_metrics": True,
                "aggregate": aggregate,
                "timing": timing,
                "artifacts": {
                    "search_summary": "artifacts/experiment_a/search_summary.json",
                    "replay_summary": "artifacts/experiment_a/replay_summary.json",
                    "attempt_timing": "artifacts/experiment_a/attempt_timing.json",
                    "source_pack02b_result": (
                        "artifacts/experiment_a/source_pack02b_experiment_result.json"
                    ),
                    "runtime_plan": "artifacts/experiment_a/runtime_plan.json",
                },
            }
            _write_json(
                run_dir / "artifacts/experiment_a_standard_panel_summary.json",
                summary_artifact,
            )

            decision = (
                ExperimentDecision.PROMOTE
                if aggregate["promotion_gate_passed"]
                else ExperimentDecision.REFINE
            )
            result_path = run.finish(
                decision=decision,
                stop_reason="done",
                result_summary={
                    "artifact": "artifacts/experiment_a_standard_panel_summary.json",
                    "primary_block_count": len(PRIMARY_BLOCK_IDS),
                    "positional_block_count": len(POSITIONAL_BLOCK_IDS),
                    "starts_per_block": STARTS_PER_BLOCK,
                    "all_replays_deterministic": all_replays,
                    "all_prior_surfaces_persisted": True,
                    "promotion_gate_passed": aggregate["promotion_gate_passed"],
                    "primary_baseline_exact_blocks": (
                        aggregate["primary"]["baseline_exact_blocks"]
                    ),
                    "primary_staged_exact_blocks": (
                        aggregate["primary"]["staged_exact_blocks"]
                    ),
                    "positional_staged_exact_blocks": (
                        aggregate["positional_confirmation"]["staged_exact_blocks"]
                    ),
                    "experiment_a_overnight_recommended": (
                        aggregate["overnight_strategy"][
                            "experiment_a_overnight_recommended"
                        ]
                    ),
                    "timing": timing,
                },
                reference_evaluation={
                    "candidate_specific_truth_emitted": False,
                    "primary_baseline_blocks": primary_baseline_terminal,
                    "primary_staged_blocks": primary_staged_terminal,
                    "positional_staged_blocks": positional_staged_terminal,
                    "aggregate": aggregate,
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
    "BASELINE_PROFILE",
    "BASELINE_SWEEPS",
    "EXPERIMENT_ID",
    "FROZEN_LADDER",
    "OVERNIGHT_RATE_THRESHOLD",
    "POSITIONAL_BLOCK_IDS",
    "POSITIONAL_BENCHMARK",
    "PRIMARY_BLOCK_IDS",
    "PRIMARY_BENCHMARK",
    "STARTS_PER_BLOCK",
    "build_block_starts",
    "panel_seed",
    "planned_runtime",
    "run_experiment_a_standard_panel",
]
