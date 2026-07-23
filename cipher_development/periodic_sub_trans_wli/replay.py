from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

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
from cipher_development.shared.replay import CandidateReplayContext
from cipher_development.shared.replay_binding import load_bound_replay_source
from cipher_development.shared.replay_evidence import (
    ReplayEvaluation,
    ReplayMode,
    write_candidate_replay,
)
from cipher_development.shared.replay_execution import replay_candidate_batch
from cipher_development.shared.replay_provenance import (
    build_evaluator_provenance,
    validate_evaluator_provenance,
)

SOURCE_RUN_ID = ""
SOURCE_BINDING_RELPATH = Path(
    "artifacts/<benchmark_id>/wli_handoff_binding.json"
)
REPLAY_MODE = ReplayMode.VERIFY
DECISION_SCORE_NAME = WLI_SCORE
REPEAT_COUNT = 2
ABSOLUTE_TOLERANCE = 1e-12
RELATIVE_TOLERANCE = 1e-12


def _portable_json(value):
    if isinstance(value, Mapping):
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
    evaluator_provenance: Mapping[str, Any],
) -> CandidateReplayContext:
    return CandidateReplayContext.create(
        campaign_id="periodic_sub_trans_wli",
        run_id=run_id,
        configuration_hash=configuration_hash,
        evaluator_id="periodic_columnar_dual_score_v2",
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
            "evaluator_provenance": _portable_json(evaluator_provenance),
        },
    )


def validate_candidate_payload(candidate, context: CandidateReplayContext) -> np.ndarray:
    payload = context.payload
    period = int(payload["period"])
    columns = int(payload["columns"])
    if payload["order"] != ORDER:
        raise ValueError("replay context order does not match the campaign")
    expected_length = period * int(payload["alphabet_size"]) + columns
    if int(payload["key_contract"]["key_length"]) != expected_length:
        raise ValueError("replay key contract length is inconsistent")
    if payload["raw_score"] != RAW_SCORE or payload["wli_score"] != WLI_SCORE:
        raise ValueError("replay context score names do not match the campaign")
    key = validate_structured_key(
        candidate.payload["expanded_key"], period=period, columns=columns
    )
    key_list = key.astype(int).tolist()
    expected_identity = {
        "cipher": "periodic_columnar",
        "order": payload["order"],
        "period": period,
        "columns": columns,
        "expanded_key": key_list,
    }
    if _portable_json(candidate.identity) != expected_identity:
        raise ValueError("candidate identity and payload structured key disagree")
    expected_payload = {
        "expanded_key": key_list,
        "period": period,
        "columns": columns,
        "order": payload["order"],
    }
    actual_payload = {
        "expanded_key": _portable_json(candidate.payload["expanded_key"]),
        "period": int(candidate.payload["period"]),
        "columns": int(candidate.payload["columns"]),
        "order": str(candidate.payload["order"]),
    }
    if actual_payload != expected_payload:
        raise ValueError("candidate payload structure disagrees with the replay context")
    return key


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
    if len(ciphertext) != int(payload["length"]) or len(wli) != len(ciphertext):
        raise ValueError("replay context length, ciphertext and WLI disagree")
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

    def evaluator(candidate, replay_context):
        key = validate_candidate_payload(candidate, replay_context)
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


def run_saved_replay(repo_root: Path) -> Path:
    if not SOURCE_RUN_ID:
        raise ValueError("configure SOURCE_RUN_ID before running replay")
    if "<benchmark_id>" in SOURCE_BINDING_RELPATH.as_posix():
        raise ValueError("replace <benchmark_id> in SOURCE_BINDING_RELPATH")
    from cipher_development.shared.experiment import (
        ExperimentDecision,
        ExperimentRun,
        ExperimentSpec,
        FailureMechanism,
        TruthPolicy,
        WliMode,
    )

    source_run = _resolve_source_run(repo_root, SOURCE_RUN_ID)
    _, _, binding, context, batch = load_bound_replay_source(
        source_run,
        SOURCE_BINDING_RELPATH,
        expected_campaign_id="periodic_sub_trans_wli",
        expected_run_id=SOURCE_RUN_ID,
    )
    actual_provenance = build_evaluator_provenance(
        repo_root=repo_root,
        evaluator_source=Path(__file__),
        scoring_contracts=(
            dict(context.payload["raw_scoring"]),
            dict(context.payload["wli_scoring"]),
        ),
        require_assets=True,
    )
    validate_evaluator_provenance(
        context.payload["evaluator_provenance"], actual_provenance
    )
    evaluator = build_replay_evaluator(context)
    evidence = replay_candidate_batch(
        batch,
        context,
        binding,
        evaluator=evaluator,
        mode=REPLAY_MODE,
        decision_score=DECISION_SCORE_NAME,
        higher_is_better=True,
        evaluator_configuration={
            "campaign": "periodic_sub_trans_wli",
            "binding_id": binding.binding_id,
            "context_id": context.context_id,
            "decision_score": DECISION_SCORE_NAME,
            "evaluator_provenance": actual_provenance,
        },
        repeat_count=REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    spec = ExperimentSpec(
        campaign_id="periodic_sub_trans_wli",
        experiment_id="wp5_candidate_replay",
        benchmark_id=binding.benchmark_id,
        question=(
            "Can a bound WP4 candidate batch be rescored deterministically "
            "without generation or Kaeding?"
        ),
        hypothesis="The bound periodic-columnar surface reproduces both scores.",
        alternative=(
            "The saved surface or evaluator provenance is insufficient to reproduce both "
            "recorded scores."
        ),
        decision_rule="Replay studies always refine; report reproducibility evidence only.",
        wli_mode=WliMode.WITH_WLI,
        truth_policy=TruthPolicy.NONE,
        mechanisms=(FailureMechanism.EVIDENCE_REPRODUCIBILITY,),
        lesson_ids=(
            "CSL-001", "CSL-002", "CSL-003", "CSL-004",
            "CSL-005", "CSL-006", "CSL-007",
        ),
    )
    with ExperimentRun(
        spec=spec,
        configuration={
            "source_run_id": SOURCE_RUN_ID,
            "source_binding_id": binding.binding_id,
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
            stop_reason="done",
            result_summary={
                "source_run_id": SOURCE_RUN_ID,
                "source_binding_id": binding.binding_id,
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
