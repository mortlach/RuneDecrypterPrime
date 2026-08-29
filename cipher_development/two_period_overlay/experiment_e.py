from __future__ import annotations
'WP6 Pack 09 P13/P31 one-word d30 S2 discovery panel.'
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
if __package__ in {None, ''}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import numpy as np
from cipher_development.shared.archive import CandidateArchive, CandidateRecord
from cipher_development.two_period_overlay.benchmark import build_rdp_case, reference_metrics
from cipher_development.two_period_overlay.config import BenchmarkSpec, MASTER_SEED, P13_P31_PRIMARY_BENCHMARK
from cipher_development.two_period_overlay.review_pack import write_review_pack_after_run
from cipher_development.two_period_overlay.scorer_profiles import F1, S2
from cipher_development.two_period_overlay.pack09_support import STAGE_SWEEPS, StageOutcome, _attempt_terminal_movement, _rescore_final_union, _run_stage, _stage_terminal_summary, _write_final_union_and_replay, _write_stage_and_replay
EXPERIMENT_ID = 'p13_p31_one_word_d30_s2_discovery_panel_v1'
BENCHMARK = P13_P31_PRIMARY_BENCHMARK
SCOUT_PROFILE = S2
RANK_PROFILE = F1
CANARY_BLOCK_ID = 90
CANARY_STARTS = 8
PHASE_A_BLOCK_IDS = (91, 92)
PHASE_B_BLOCK_IDS = (93, 94, 95, 96)
SCIENCE_BLOCK_IDS = (*PHASE_A_BLOCK_IDS, *PHASE_B_BLOCK_IDS)
STARTS_PER_BLOCK = 512
ARCHIVE_CAPACITY = STARTS_PER_BLOCK
REPLAY_REPEAT_COUNT = 2
PLANNING_WINDOW_S = 8.0 * 60.0 * 60.0
TERMINAL_RESERVE_S = 45.0 * 60.0
RUNTIME_SAFETY_FACTOR = 1.2
STAGE_SAFETY_S = 90.0 * 60.0
BLOCK_SAFETY_S = 110.0 * 60.0
PACK07R_D22_SCOUT_MEAN_S = 2170.7778128333334
PACK07R_D22_DIMENSION = 22
NEAR_SOLVE_RUNES = 289
NEAR_SOLVE_COMPLETE_WORDS = 63

@dataclass(frozen=True, slots=True)
class DiscoveryBlock:
    benchmark: BenchmarkSpec
    block_id: int
    phase: str
    starts: tuple[dict[str, Any], ...]
    scout: StageOutcome
    final_archive: CandidateArchive
    final_rescore_elapsed_s: float
    final_rescore_evaluations: int
    search_elapsed_s: float
    total_elapsed_s: float = 0.0

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n', encoding='utf-8', newline='\n')

def _status(run_dir: Path | None, state: str, **details: Any) -> None:
    payload = {'schema': 'rdp.two_period_overlay.p13_p31_d30_visible_status.v1', 'updated_at_utc': _utc_now_iso(), 'state': state, **details}
    print(f"[{payload['updated_at_utc']}] {state}: " + json.dumps(details, sort_keys=True, allow_nan=False), flush=True)
    if run_dir is not None:
        _write_json(run_dir / 'artifacts/experiment_e/visible_status.json', payload)

def panel_seed(benchmark_id: str, block_id: int, stage_id: str, token: str) -> int:
    payload = f'{MASTER_SEED}:wp6-pack09:{benchmark_id}:{block_id}:{stage_id}:{token}'.encode('utf-8')
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8, person=b'rdp-wp6-09').digest(), 'big')

def build_block_starts(benchmark: BenchmarkSpec, block_id: int, *, count: int=STARTS_PER_BLOCK) -> tuple[dict[str, Any], ...]:
    if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
        raise ValueError('count must be a positive integer')
    rows = []
    for restart_index in range(count):
        seed = panel_seed(benchmark.benchmark_id, block_id, 'start', f'restart-{restart_index}')
        rng = np.random.default_rng(seed)
        variables = rng.integers(0, benchmark.alphabet_size, size=benchmark.expected_free_dimension, dtype=np.uint8)
        rows.append({'block_id': block_id, 'restart_index': restart_index, 'seed': seed, 'variables': variables.astype(int).tolist()})
    return tuple(rows)

def planned_runtime() -> dict[str, Any]:
    scaled_block = PACK07R_D22_SCOUT_MEAN_S * BENCHMARK.expected_free_dimension / PACK07R_D22_DIMENSION
    science_central = scaled_block * len(SCIENCE_BLOCK_IDS)
    return {'schema': 'rdp.two_period_overlay.p13_p31_d30_runtime_plan.v1', 'source': {'pack': 'Pack 07R', 'dimension': PACK07R_D22_DIMENSION, 'mean_scout_elapsed_s_per_512_starts': PACK07R_D22_SCOUT_MEAN_S}, 'target_dimension': BENCHMARK.expected_free_dimension, 'central_scout_elapsed_s_per_block': scaled_block, 'science_blocks': len(SCIENCE_BLOCK_IDS), 'starts_per_block': STARTS_PER_BLOCK, 'total_science_starts': len(SCIENCE_BLOCK_IDS) * STARTS_PER_BLOCK, 'central_science_scout_elapsed_s': science_central, 'central_science_scout_elapsed_hours': science_central / 3600.0, 'safety_factor': RUNTIME_SAFETY_FACTOR, 'safety_adjusted_science_scout_elapsed_s': science_central * RUNTIME_SAFETY_FACTOR, 'planning_window_s': PLANNING_WINDOW_S, 'terminal_reserve_s': TERMINAL_RESERVE_S}

def contract_preflight(repo_root: Path) -> dict[str, Any]:
    search_case, _ = build_rdp_case(BENCHMARK, scoring_contract=SCOUT_PROFILE.scoring_contract())
    if BENCHMARK.expected_free_dimension != 30:
        raise RuntimeError('Pack 09 benchmark is not d30')
    if len(search_case.free_columns) != 30:
        raise RuntimeError('Pack 09 derived dimension is not d30')
    if BENCHMARK.additional_cribs:
        raise RuntimeError('Pack 09 must not expose an additional crib')
    return {'schema': 'rdp.two_period_overlay.p13_p31_d30_contract_preflight.v1', 'passed': True, 'repo_root_name': repo_root.resolve().name, 'benchmark': BENCHMARK.to_json_dict(), 'active_crib_count': 1, 'active_crib_words': [BENCHMARK.crib_word], 'additional_cribs_present': False, 'derived_dimension': len(search_case.free_columns), 'free_columns': list(search_case.free_columns), 'known_key_affine_roundtrip_verified': True, 'complete_primary_crib_wli_span_verified': True}

def _stage_seed_factory(benchmark: BenchmarkSpec, block_id: int):

    def seed_factory(stage_id: str, token: str) -> int:
        return panel_seed(benchmark.benchmark_id, block_id, stage_id, token)
    return seed_factory

def _run_discovery_block(benchmark: BenchmarkSpec, block_id: int, phase: str, starts: tuple[dict[str, Any], ...], scout_case: Any, rank_case: Any) -> DiscoveryBlock:
    started = time.perf_counter()
    scout = _run_stage(stage_id='scout', profile=SCOUT_PROFILE, search_case=scout_case, inputs=starts, sweeps=STAGE_SWEEPS[SCOUT_PROFILE.profile_id], benchmark=benchmark, seed_factory=_stage_seed_factory(benchmark, block_id), archive_capacity=ARCHIVE_CAPACITY, stage_safety_seconds=STAGE_SAFETY_S, provenance_source='p13_p31_one_word_d30_discovery')
    first_stage = {record.candidate_id: 'scout' for record in scout.archive.records}
    final_archive, rescore_elapsed, rescore_evaluations = _rescore_final_union(scout.archive.records, rank_case, RANK_PROFILE, first_stage, archive_capacity=ARCHIVE_CAPACITY, provenance_source='p13_p31_one_word_d30_discovery', provenance_operation='static_f1_rescore')
    elapsed = time.perf_counter() - started
    if elapsed > BLOCK_SAFETY_S:
        raise TimeoutError(f'Pack 09 block {block_id} exceeded the block safety allowance')
    return DiscoveryBlock(benchmark=benchmark, block_id=block_id, phase=phase, starts=starts, scout=scout, final_archive=final_archive, final_rescore_elapsed_s=rescore_elapsed, final_rescore_evaluations=rescore_evaluations, search_elapsed_s=elapsed)

def _block_root(phase: str, block_id: int) -> Path:
    return Path('artifacts/experiment_e') / phase / f'block_{block_id:02d}'

def _required_artifact_paths(completed: Sequence[DiscoveryBlock]=()) -> tuple[str, ...]:
    paths = ['artifacts/p13_p31_one_word_d30_summary.json', 'artifacts/execution_timing.json', 'artifacts/experiment_e/visible_status.json', 'artifacts/experiment_e/runtime_plan.json', 'artifacts/experiment_e/contract_preflight.json', 'artifacts/experiment_e/operational_gate.json', 'artifacts/experiment_e/attempt_timing.json', 'artifacts/experiment_e/search_summary.json', 'artifacts/experiment_e/replay_summary.json', 'artifacts/experiment_e/terminal_evaluation.json', 'artifacts/experiment_e/required_artifacts.json']
    for block in completed:
        root = _block_root(block.phase, block.block_id)
        paths.extend((str(root / relative).replace('\\', '/') for relative in ('starts.json', 'block_completed.json', 'scout/candidate_archive.json', 'scout/attempts.json', 'scout/handoff_batch.json', 'scout/replay_context.json', 'scout/replay_binding.json', 'scout/replay_evidence.json', 'final_union/candidate_archive.json', 'final_union/replay_batch.json', 'final_union/replay_context.json', 'final_union/replay_binding.json', 'final_union/replay_evidence.json')))
    return tuple(dict.fromkeys(paths))

def _write_required_artifacts(run_dir: Path, completed: Sequence[DiscoveryBlock]) -> None:
    _write_json(run_dir / 'artifacts/experiment_e/required_artifacts.json', {'schema': 'rdp.two_period_overlay.p13_p31_d30_required_artifacts.v1', 'paths': list(_required_artifact_paths(completed))})

def _write_attempt_timing(run_dir: Path, completed: Sequence[DiscoveryBlock]) -> None:
    _write_json(run_dir / 'artifacts/experiment_e/attempt_timing.json', {'schema': 'rdp.two_period_overlay.p13_p31_d30_attempt_timing.v1', 'rows': [{'phase': block.phase, 'block_id': block.block_id, **dict(row)} for block in completed for row in block.scout.attempt_rows]})

def _persist_block(*, run_dir: Path, run: Any, block: DiscoveryBlock, scout_case: Any, rank_case: Any, evaluator_provenance: Mapping[str, Any]) -> tuple[DiscoveryBlock, dict[str, Any]]:
    persist_started = time.perf_counter()
    root = _block_root(block.phase, block.block_id)
    _write_json(run_dir / root / 'starts.json', {'schema': 'rdp.two_period_overlay.p13_p31_d30_starts.v1', 'benchmark_id': block.benchmark.benchmark_id, 'phase': block.phase, 'block_id': block.block_id, 'rows': list(block.starts)})
    scout = _write_stage_and_replay(run_dir=run_dir, run=run, stage=block.scout, search_case=scout_case, evaluator_provenance=evaluator_provenance, artifact_root=root, experiment_id=EXPERIMENT_ID, benchmark=block.benchmark, selection_label=f'p13_p31_d30_block_{block.block_id:02d}_scout__all', evaluator_id=f'two_period_overlay_p13_p31_d30_scout_{block.block_id:02d}')
    final = _write_final_union_and_replay(run_dir=run_dir, run=run, archive=block.final_archive, search_case=rank_case, profile=RANK_PROFILE, evaluator_provenance=evaluator_provenance, artifact_root=root, experiment_id=EXPERIMENT_ID, benchmark=block.benchmark, selection_label=f'p13_p31_d30_block_{block.block_id:02d}_static_f1__all', evaluator_id=f'two_period_overlay_p13_p31_d30_final_{block.block_id:02d}')
    for row in (scout, final):
        if row.get('replay_deterministic') is not True or row.get('replay_stored_scores_verified') is not True:
            raise RuntimeError(f'Pack 09 block {block.block_id} replay verification failed')
    total_elapsed = block.search_elapsed_s + (time.perf_counter() - persist_started)
    completed = {'schema': 'rdp.two_period_overlay.p13_p31_d30_block_completed.v1', 'benchmark_id': block.benchmark.benchmark_id, 'phase': block.phase, 'block_id': block.block_id, 'starts': len(block.starts), 'search_elapsed_s': block.search_elapsed_s, 'total_elapsed_s': total_elapsed, 'replay_deterministic': True, 'replay_stored_scores_verified': True, 'scout': scout, 'static_f1': {**final, 'rescore_elapsed_s': block.final_rescore_elapsed_s, 'rescore_evaluations': block.final_rescore_evaluations}}
    _write_json(run_dir / root / 'block_completed.json', completed)
    return (DiscoveryBlock(benchmark=block.benchmark, block_id=block.block_id, phase=block.phase, starts=block.starts, scout=block.scout, final_archive=block.final_archive, final_rescore_elapsed_s=block.final_rescore_elapsed_s, final_rescore_evaluations=block.final_rescore_evaluations, search_elapsed_s=block.search_elapsed_s, total_elapsed_s=total_elapsed), completed)

def _exact_ids(records: Sequence[CandidateRecord], search_case: Any, reference: Any):
    result = set()
    for record in records:
        variables = np.asarray(record.payload['variables'], dtype=np.uint8)
        metrics = reference_metrics(reference, variables, search_case.particular, search_case.basis)
        if metrics['exact_plaintext']:
            result.add(record.candidate_id)
    return result

def _exact_attempt_summary(stage: StageOutcome, exact_ids: set[str]) -> dict[str, Any]:
    cumulative = 0.0
    first_elapsed = None
    first_input = None
    count = 0
    for row in stage.attempt_rows:
        cumulative += float(row['elapsed_s'])
        if row['candidate_id'] in exact_ids:
            count += 1
            if first_elapsed is None:
                first_elapsed = cumulative
                first_input = int(row['input_index'])
    return {'exact_attempt_count': count, 'first_exact_input_index': first_input, 'post_hoc_cumulative_attempt_elapsed_s_to_first_exact': first_elapsed}

def _near_solve_count(records: Sequence[CandidateRecord], search_case: Any, reference: Any) -> int:
    count = 0
    for record in records:
        variables = np.asarray(record.payload['variables'], dtype=np.uint8)
        metrics = reference_metrics(reference, variables, search_case.particular, search_case.basis)
        if int(metrics['rune_matches']) >= NEAR_SOLVE_RUNES and int(metrics['complete_word_matches']) >= NEAR_SOLVE_COMPLETE_WORDS:
            count += 1
    return count

def _terminal_block(block: DiscoveryBlock, scout_case: Any, rank_case: Any, reference: Any) -> dict[str, Any]:
    scout_exact = _exact_ids(block.scout.archive.records, scout_case, reference)
    final_exact = _exact_ids(block.final_archive.records, rank_case, reference)
    return {'block_id': block.block_id, 'phase': block.phase, 'scout': {'archive': _stage_terminal_summary(block.scout.archive.records, SCOUT_PROFILE, scout_case, reference), 'movement': _attempt_terminal_movement(block.scout, scout_case, reference), 'exact_attempts': _exact_attempt_summary(block.scout, scout_exact)}, 'static_f1': {'archive': _stage_terminal_summary(block.final_archive.records, RANK_PROFILE, rank_case, reference), 'near_solve_candidate_count': _near_solve_count(block.final_archive.records, rank_case, reference)}, 'exact_scout_candidate_count': len(scout_exact), 'exact_static_f1_candidate_count': len(final_exact), 'exact_candidate_preserved': bool(scout_exact and final_exact)}

def _classify(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    exact_blocks = 0
    rank_one_blocks = 0
    unique_blocks = 0
    near_blocks = 0
    for row in rows:
        scout_exact = int(row['exact_scout_candidate_count']) > 0
        exact_blocks += int(scout_exact)
        final = row['static_f1']['archive']
        rank_one = bool(final['top_scored_candidate_terminal']['exact_plaintext'])
        rank_one_blocks += int(scout_exact and rank_one)
        unique = int(final['canonical_key_count']) == 1 and int(final['combined_shift_count']) == 1
        unique_blocks += int(scout_exact and unique)
        near_blocks += int(int(row['static_f1']['near_solve_candidate_count']) > 0)
    promote = len(rows) >= 4 and exact_blocks >= 2 and (rank_one_blocks == exact_blocks) and (unique_blocks == exact_blocks)
    if promote:
        decision = 'promote'
        rationale = 'At least two independent d30 blocks generated an exact S2 candidate; static F1 ranked every exact solution first with one canonical key.'
    elif exact_blocks == 1 or near_blocks >= 2 or rank_one_blocks < exact_blocks:
        decision = 'refine'
        rationale = 'The frozen discovery panel produced one exact block, repeated near-solves, or a static-F1 ranking issue.'
    elif len(rows) >= 4:
        decision = 'close'
        rationale = 'At least four frozen d30 blocks completed with zero exact S2 candidates and fewer than two near-solve blocks.'
    else:
        decision = 'incomplete'
        rationale = 'Fewer than four scientific blocks completed.'
    return {'schema': 'rdp.two_period_overlay.p13_p31_d30_classification.v1', 'decision': decision, 'rationale': rationale, 'science_blocks_completed': len(rows), 'exact_scout_blocks': exact_blocks, 'static_f1_rank_one_exact_blocks': rank_one_blocks, 'unique_exact_key_blocks': unique_blocks, 'near_solve_blocks': near_blocks, 'promotion_gate_passed': promote, 'closure_scope': 'only the frozen Pack 09 3,072-start S2 d30 discovery budget', 'automatic_fallback_authorised': False}

def _runtime_gate(*, phase_a_elapsed_s: float, completed_blocks: int, elapsed_before_phase_a_s: float) -> dict[str, Any]:
    per_block = phase_a_elapsed_s / completed_blocks
    projected_remaining = per_block * len(PHASE_B_BLOCK_IDS)
    safety_adjusted_total = elapsed_before_phase_a_s + phase_a_elapsed_s + projected_remaining * RUNTIME_SAFETY_FACTOR
    launch_all = safety_adjusted_total <= PLANNING_WINDOW_S - TERMINAL_RESERVE_S
    return {'schema': 'rdp.two_period_overlay.p13_p31_d30_operational_gate.v1', 'terminal_metrics_opened': False, 'completed_phase_a_blocks': completed_blocks, 'phase_a_elapsed_s': phase_a_elapsed_s, 'elapsed_before_phase_a_s': elapsed_before_phase_a_s, 'measured_elapsed_s_per_block': per_block, 'projected_remaining_s': projected_remaining, 'safety_factor': RUNTIME_SAFETY_FACTOR, 'safety_adjusted_complete_elapsed_s': safety_adjusted_total, 'planning_window_s': PLANNING_WINDOW_S, 'terminal_reserve_s': TERMINAL_RESERVE_S, 'all_phase_b_blocks_authorised': launch_all, 'terminal_metrics_used': []}

def run_p13_p31_one_word_d30_panel(repo_root: Path, *, output_root: Path) -> Path:
    from cipher_development.shared.experiment import ExperimentDecision, ExperimentRun, ExperimentSpec, FailureMechanism, TruthPolicy, WliMode
    from cipher_development.shared.replay_provenance import build_evaluator_provenance
    repo_root = repo_root.resolve()
    if not output_root.is_absolute():
        raise ValueError('Pack 09 requires an absolute external output root')
    output_root = output_root.resolve()
    if output_root == repo_root or output_root.is_relative_to(repo_root):
        raise ValueError('Pack 09 output must stay outside the repository')
    started_at = _utc_now_iso()
    experiment_started = time.perf_counter()
    spec = ExperimentSpec(campaign_id='two_period_overlay', experiment_id=EXPERIMENT_ID, benchmark_id=BENCHMARK.benchmark_id, question='Can truth-blind S2 search recover the controlled 308-rune P13/P31 d30 benchmark using only the complete word uncomfortable?', hypothesis='At least two independent 512-start blocks will generate an exact S2 candidate and static F1 will rank it first.', alternative='The one-word d30 space weakens the S2 coordinate signal enough that the frozen 3,072-start panel generates fewer than two exact blocks.', decision_rule='Promote for at least two exact S2 blocks among at least four completed blocks, with static-F1 rank one and unique key in every exact block. Refine for one exact block, repeated near-solves or a ranking issue. Close only this frozen budget after at least four complete weak blocks.', wli_mode=WliMode.WITH_WLI, truth_policy=TruthPolicy.BENCHMARK_ONLY, mechanisms=(FailureMechanism.CONTRACT, FailureMechanism.CANDIDATE_SUPPLY, FailureMechanism.RANKING, FailureMechanism.BUDGET, FailureMechanism.EVIDENCE_REPRODUCIBILITY), budget_seconds=PLANNING_WINDOW_S, budget_evaluations=None, lesson_ids=('CSL-004', 'CSL-005', 'CSL-007'))
    configuration = {'contract_revision': 'pack09_one_word_d30_discovery_v1', 'benchmark': BENCHMARK.to_json_dict(), 'active_crib_count': 1, 'additional_cribs_present': False, 'canary': {'block_id': CANARY_BLOCK_ID, 'starts': CANARY_STARTS}, 'phase_a_block_ids': list(PHASE_A_BLOCK_IDS), 'phase_b_block_ids': list(PHASE_B_BLOCK_IDS), 'starts_per_block': STARTS_PER_BLOCK, 'scout_profile': SCOUT_PROFILE.to_json_dict(), 'static_rank_profile': RANK_PROFILE.to_json_dict(), 'scout_sweeps': STAGE_SWEEPS[SCOUT_PROFILE.profile_id], 'bridge_coordinate_search_used': False, 'judge_coordinate_search_used': False, 'static_f1_rescore_used': True, 'archive_capacity': ARCHIVE_CAPACITY, 'replay_repeat_count': REPLAY_REPEAT_COUNT, 'planning_window_s': PLANNING_WINDOW_S, 'terminal_reserve_s': TERMINAL_RESERVE_S, 'automatic_fallback_disabled': True, 'runtime_plan': planned_runtime()}
    run_dir = None
    result_path = None
    try:
        with ExperimentRun(spec=spec, configuration=configuration, repo_root=repo_root, output_root=output_root) as run:
            assert run.run_dir is not None
            run_dir = run.run_dir
            provenance = build_evaluator_provenance(repo_root=repo_root, evaluator_source=Path(__file__).with_name('replay.py'), scoring_contracts=(SCOUT_PROFILE.scoring_contract(), RANK_PROFILE.scoring_contract()), require_assets=True)
            _status(run_dir, 'pack09_started')
            _write_json(run_dir / 'artifacts/experiment_e/runtime_plan.json', planned_runtime())
            _write_json(run_dir / 'artifacts/experiment_e/contract_preflight.json', contract_preflight(repo_root))
            scout_case, reference = build_rdp_case(BENCHMARK, scoring_contract=SCOUT_PROFILE.scoring_contract())
            rank_case, _ = build_rdp_case(BENCHMARK, scoring_contract=RANK_PROFILE.scoring_contract())
            completed: list[DiscoveryBlock] = []
            replay_rows: list[dict[str, Any]] = []
            _write_required_artifacts(run_dir, completed)

            def execute(block_id: int, phase: str, count: int):
                _status(run_dir, 'block_started', block_id=block_id, phase=phase, starts=count)
                block = _run_discovery_block(BENCHMARK, block_id, phase, build_block_starts(BENCHMARK, block_id, count=count), scout_case, rank_case)
                block, evidence = _persist_block(run_dir=run_dir, run=run, block=block, scout_case=scout_case, rank_case=rank_case, evaluator_provenance=provenance)
                completed.append(block)
                _write_attempt_timing(run_dir, completed)
                _write_required_artifacts(run_dir, completed)
                replay_rows.append({'phase': phase, 'block_id': block_id, 'replay_deterministic': True, 'replay_stored_scores_verified': True, 'total_elapsed_s': evidence['total_elapsed_s']})
                _write_json(run_dir / 'artifacts/experiment_e/search_summary.json', {'schema': 'rdp.two_period_overlay.p13_p31_d30_search_summary.v1', 'rows': [{'phase': item.phase, 'block_id': item.block_id, 'starts': len(item.starts), 'search_elapsed_s': item.search_elapsed_s, 'total_elapsed_s': item.total_elapsed_s, 'scout': item.scout.to_search_summary(), 'static_f1': {'candidate_count': len(item.final_archive.records), 'rescore_elapsed_s': item.final_rescore_elapsed_s, 'rescore_evaluations': item.final_rescore_evaluations}} for item in completed]})
                _write_json(run_dir / 'artifacts/experiment_e/replay_summary.json', {'schema': 'rdp.two_period_overlay.p13_p31_d30_replay_summary.v1', 'rows': replay_rows, 'all_completed_replays_verified': True})
                return block
            execute(CANARY_BLOCK_ID, 'canary', CANARY_STARTS)
            before_phase_a = time.perf_counter() - experiment_started
            phase_a_started = time.perf_counter()
            for block_id in PHASE_A_BLOCK_IDS:
                execute(block_id, 'science', STARTS_PER_BLOCK)
            phase_a_elapsed = time.perf_counter() - phase_a_started
            gate = _runtime_gate(phase_a_elapsed_s=phase_a_elapsed, completed_blocks=len(PHASE_A_BLOCK_IDS), elapsed_before_phase_a_s=before_phase_a)
            _write_json(run_dir / 'artifacts/experiment_e/operational_gate.json', gate)
            elapsed_now = time.perf_counter() - experiment_started
            per_block_safe = gate['measured_elapsed_s_per_block'] * RUNTIME_SAFETY_FACTOR
            available = PLANNING_WINDOW_S - TERMINAL_RESERVE_S - elapsed_now
            authorised = min(len(PHASE_B_BLOCK_IDS), max(0, int(available // per_block_safe)) if per_block_safe > 0 else 0)
            for block_id in PHASE_B_BLOCK_IDS[:authorised]:
                execute(block_id, 'science', STARTS_PER_BLOCK)
            science_blocks = [item for item in completed if item.phase == 'science']
            _status(run_dir, 'terminal_evaluation_started', science_blocks=len(science_blocks))
            terminal_rows = [_terminal_block(item, scout_case, rank_case, reference) for item in science_blocks]
            canary = next((item for item in completed if item.phase == 'canary'))
            canary_terminal = _terminal_block(canary, scout_case, rank_case, reference)
            classification = _classify(terminal_rows)
            terminal = {'schema': 'rdp.two_period_overlay.p13_p31_d30_terminal.v1', 'terminal_truth_opened_after_all_search_and_replay': True, 'canary_excluded_from_classification': True, 'canary': canary_terminal, 'science_blocks': terminal_rows, 'classification': classification}
            _write_json(run_dir / 'artifacts/experiment_e/terminal_evaluation.json', terminal)
            timing = {'schema': 'rdp.two_period_overlay.p13_p31_d30_timing.v1', 'started_at_utc': started_at, 'finished_at_utc': _utc_now_iso(), 'process_elapsed_s': time.perf_counter() - experiment_started, 'blocks': [{'phase': item.phase, 'block_id': item.block_id, 'starts': len(item.starts), 'search_elapsed_s': item.search_elapsed_s, 'total_elapsed_s': item.total_elapsed_s} for item in completed]}
            _write_json(run_dir / 'artifacts/execution_timing.json', timing)
            summary = {'schema': 'rdp.two_period_overlay.p13_p31_d30_panel_summary.v1', 'benchmark_id': BENCHMARK.benchmark_id, 'active_crib_count': 1, 'science_blocks_completed': len(science_blocks), 'starts_per_block': STARTS_PER_BLOCK, 'total_science_starts': len(science_blocks) * STARTS_PER_BLOCK, 'bridge_coordinate_search_used': False, 'judge_coordinate_search_used': False, 'static_f1_rescore_used': True, 'classification': classification, 'runtime_gate': gate, 'timing': timing}
            _write_json(run_dir / 'artifacts/p13_p31_one_word_d30_summary.json', summary)
            decision = ExperimentDecision(classification['decision'])
            result_path = run.finish(decision=decision, stop_reason='done', result_summary={'artifact': 'artifacts/p13_p31_one_word_d30_summary.json', **summary}, reference_evaluation={'candidate_specific_truth_emitted': False, 'terminal_artifact': 'artifacts/experiment_e/terminal_evaluation.json', 'classification': classification})
    except BaseException as exc:
        if run_dir is not None:
            write_review_pack_after_run(repo_root, run_dir, output_root=output_root / 'review_packs', original_error=exc)
        raise
    assert run_dir is not None and result_path is not None
    write_review_pack_after_run(repo_root, run_dir, output_root=output_root / 'review_packs')
    return result_path
__all__ = ['ARCHIVE_CAPACITY', 'BENCHMARK', 'CANARY_BLOCK_ID', 'CANARY_STARTS', 'EXPERIMENT_ID', 'PHASE_A_BLOCK_IDS', 'PHASE_B_BLOCK_IDS', 'SCIENCE_BLOCK_IDS', 'STARTS_PER_BLOCK', '_classify', '_runtime_gate', 'build_block_starts', 'contract_preflight', 'panel_seed', 'planned_runtime', 'run_p13_p31_one_word_d30_panel']
