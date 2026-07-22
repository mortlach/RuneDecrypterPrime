from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from cipher_development.periodic_sub_trans_wli.benchmark import (
    scoring_kwargs,
    validate_structured_key,
)
from cipher_development.periodic_sub_trans_wli.config import (
    ALPHABET_SIZE,
    ORDER,
    RAW_SCORE,
    WLI_SCORE,
)
from cipher_development.shared.replay import (
    CandidateReplayContext,
    read_candidate_batch,
    read_replay_context,
)
from cipher_development.shared.replay_evidence import (
    ReplayEvaluation,
    ReplayMode,
    write_candidate_replay,
)
from cipher_development.shared.replay_execution import replay_candidate_batch

SOURCE_RUN_ID = ""
SOURCE_BATCH_RELPATH = Path("artifacts/<benchmark_id>/wli_handoff_batch.json")
SOURCE_CONTEXT_RELPATH = Path("artifacts/<benchmark_id>/replay_context.json")
REPLAY_MODE = ReplayMode.VERIFY
DECISION_SCORE_NAME = WLI_SCORE
REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _portable_json(value):
    if isinstance(value, dict):
        return {str(key): _portable_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_portable_json(item) for item in value]
    return value


def make_replay_context(
    search_case,
    *,
    run_id: str,
    configuration_hash: str,
    raw_scoring: dict,
    wli_scoring: dict,
) -> CandidateReplayContext:
    return CandidateReplayContext.create(
        campaign_id="periodic_sub_trans_wli",
        run_id=run_id,
        configuration_hash=configuration_hash,
        evaluator_id="periodic_columnar_dual_score_v1",
        payload={
            "benchmark_id": search_case.benchmark_id,
            "family": search_case.family,
            "period": search_case.period,
            "columns": search_case.columns,
            "length": search_case.length,
            "order": search_case.order,
            "alphabet_size": ALPHABET_SIZE,
            "ciphertext": list(search_case.ciphertext),
            "wli": [list(pair) for pair in search_case.wli],
            "raw_score": RAW_SCORE,
            "wli_score": WLI_SCORE,
            "raw_scoring": _portable_json(raw_scoring),
            "wli_scoring": _portable_json(wli_scoring),
            "key_contract": {
                "structure": "periodic_structured",
                "key_length": search_case.period * ALPHABET_SIZE + search_case.columns,
            },
        },
    )


def build_replay_evaluator(context: CandidateReplayContext):
    if context.campaign_id != "periodic_sub_trans_wli":
        raise ValueError("replay context belongs to a different campaign")
    payload = context.payload
    from rune_decrypter_prime.api import by_name, cipher_instance
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction

    period = int(payload["period"])
    columns = int(payload["columns"])
    ciphertext = np.asarray(payload["ciphertext"], dtype=np.uint8)
    wli = tuple((int(a), int(b)) for a, b in payload["wli"])
    spec, key_spec = by_name.cipher_with_key(
        "periodic_columnar",
        period=period,
        columns=columns,
        order=str(payload["order"]),
        alphabet_size=int(payload["alphabet_size"]),
        default_key=True,
    )
    cipher = cipher_instance(spec)
    direction = Direction(str(payload["wli_scoring"]["encoding_direction"]))

    def make_problem(contract, with_wli: bool):
        cipher_cfg = build_cipher_config(
            cipher=spec,
            key=key_spec,
            ciphertext=ciphertext,
            wli=[list(pair) for pair in wli] if with_wli else None,
            device=Device.CPU,
            encoding_dir=direction,
            initial_text_permutation_indices=None,
            initial_keys=None,
            interruptors=None,
            interruptors_exact=None,
            interruptors_pool=None,
            interruptors_max=None,
        )
        scoring = ScoringConfig(**scoring_kwargs(contract, Direction))
        return DecryptionProblem(
            cipher=cipher,
            scorer=build_scorer(cipher_cfg, scoring),
            c_cfg=cipher_cfg,
            s_cfg=scoring,
            enable_telemetry=False,
        )

    raw_problem = make_problem(payload["raw_scoring"], False)
    wli_problem = make_problem(payload["wli_scoring"], True)

    def evaluator(candidate, _context):
        key = validate_structured_key(
            candidate.payload["expanded_key"], period=period, columns=columns
        )
        raw_score = float(np.asarray(raw_problem.evaluate_keys(key[None, :]))[0])
        wli_score = float(np.asarray(wli_problem.evaluate_keys(key[None, :]))[0])
        return ReplayEvaluation(
            scores={RAW_SCORE: raw_score, WLI_SCORE: wli_score},
            stable_metrics={
                "candidate_id": candidate.candidate_id,
                "payload_valid": True,
                "key_length": int(key.size),
            },
        )

    return evaluator


def _resolve_source_run(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("source run ID must be one directory name")
    campaign_root = (
        repo_root / "output/cipher_development/periodic_sub_trans_wli"
    ).resolve()
    run_dir = (campaign_root / run_id).resolve()
    if campaign_root not in run_dir.parents:
        raise ValueError("source run ID escaped the campaign output root")
    return run_dir


def _safe_source_path(run_dir: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("source artifact path must be relative and remain within the run")
    if "<benchmark_id>" in relative.as_posix():
        raise ValueError("replace <benchmark_id> in the configured source artifact paths")
    resolved = (run_dir / relative).resolve()
    if run_dir.resolve() not in resolved.parents:
        raise ValueError("source artifact path escaped the run directory")
    return resolved


def run_saved_replay(repo_root: Path) -> Path:
    if not SOURCE_RUN_ID:
        raise ValueError("configure SOURCE_RUN_ID before running replay")
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    source_run = _resolve_source_run(repo_root, SOURCE_RUN_ID)
    manifest = json.loads(
        (source_run / "artifacts/experiment_manifest.json").read_text(encoding="utf-8")
    )
    if manifest.get("campaign_id") != "periodic_sub_trans_wli":
        raise ValueError("source manifest belongs to a different campaign")
    if manifest.get("run_id") != SOURCE_RUN_ID:
        raise ValueError("source manifest run ID does not match the selected run")
    context = read_replay_context(_safe_source_path(source_run, SOURCE_CONTEXT_RELPATH))
    batch = read_candidate_batch(_safe_source_path(source_run, SOURCE_BATCH_RELPATH))
    if context.run_id != SOURCE_RUN_ID:
        raise ValueError("replay context run ID does not match the selected source run")
    if context.configuration_hash != manifest.get("configuration_hash"):
        raise ValueError("replay context configuration hash does not match the manifest")
    evaluator = build_replay_evaluator(context)
    evidence = replay_candidate_batch(
        batch,
        context,
        evaluator=evaluator,
        mode=REPLAY_MODE,
        decision_score=DECISION_SCORE_NAME,
        higher_is_better=True,
        evaluator_configuration={
            "campaign": "periodic_sub_trans_wli",
            "context_id": context.context_id,
            "decision_score": DECISION_SCORE_NAME,
        },
        repeat_count=REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    spec = ExperimentSpec(
        campaign_id="periodic_sub_trans_wli",
        experiment_id="wp5_candidate_replay",
        benchmark_id=str(context.payload["benchmark_id"]),
        question=(
            "Can a saved WP4 candidate batch be rescored deterministically "
            "without generation or Kaeding?"
        ),
        hypothesis="The saved periodic-columnar surface reproduces both raw and WLI scores.",
        decision_rule="Replay studies always refine; report reproducibility evidence only.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.EVIDENCE_REPRODUCIBILITY,),
    )
    with ExperimentRun(
        spec=spec,
        configuration={
            "source_run_id": SOURCE_RUN_ID,
            "source_batch_id": batch.batch_id,
            "source_context_id": context.context_id,
            "mode": str(REPLAY_MODE),
            "decision_score": DECISION_SCORE_NAME,
            "repeat_count": REPEAT_COUNT,
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "relative_tolerance": RELATIVE_TOLERANCE,
        },
        repo_root=repo_root,
    ) as run:
        assert run.run_dir is not None
        artifact = run.run_dir / "artifacts/candidate_replay.json"
        write_candidate_replay(artifact, evidence)
        return run.finish(
            decision=ExperimentDecision.REFINE,
            stop_reason="max_rounds",
            result_summary={
                "source_run_id": SOURCE_RUN_ID,
                "source_batch_id": batch.batch_id,
                "source_context_id": context.context_id,
                "replay_id": evidence.replay_id,
                "mode": evidence.mode.value,
                "candidate_count": len(evidence.candidate_ids),
                "decision_score": evidence.decision_score,
                "deterministic": evidence.deterministic,
                "stored_scores_verified": evidence.stored_scores_verified,
                "ranking": list(evidence.ranking),
                "artifact": "artifacts/candidate_replay.json",
            },
        )


def main() -> int:
    run_saved_replay(Path(__file__).resolve().parents[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
