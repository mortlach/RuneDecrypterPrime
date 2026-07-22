from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

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
from cipher_development.two_period_overlay.config import (
    ALPHABET_SIZE,
    CRIB_START,
    DECISION_SCORE,
    PERIOD_A,
    PERIOD_B,
    SCORING_CONTRACT,
)
from cipher_development.two_period_overlay.keyspace import expand

SOURCE_RUN_ID = ""
SOURCE_BATCH_RELPATH = Path("artifacts/archive_handoff_batch.json")
SOURCE_CONTEXT_RELPATH = Path("artifacts/replay_context.json")
REPLAY_MODE = ReplayMode.VERIFY
DECISION_SCORE_NAME = DECISION_SCORE
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
    search_case: Any, *, run_id: str, configuration_hash: str
) -> CandidateReplayContext:
    return CandidateReplayContext.create(
        campaign_id="two_period_overlay",
        run_id=run_id,
        configuration_hash=configuration_hash,
        evaluator_id="two_period_overlay_wli_v1",
        payload={
            "benchmark_id": "alice_308_p13_p17",
            "alphabet_size": ALPHABET_SIZE,
            "period_a": PERIOD_A,
            "period_b": PERIOD_B,
            "schedule": "overlay",
            "ciphertext": np.asarray(search_case.ciphertext, dtype=np.uint8).tolist(),
            "wli": [list(pair) for pair in search_case.wli],
            "crib": np.asarray(search_case.crib, dtype=np.uint8).tolist(),
            "crib_start": CRIB_START,
            "gauge": "B[0]=0",
            "particular": np.asarray(search_case.particular, dtype=np.uint8).tolist(),
            "basis": np.asarray(search_case.basis, dtype=np.uint8).tolist(),
            "free_columns": list(search_case.free_columns),
            "decision_score": DECISION_SCORE,
            "scoring": _portable_json(SCORING_CONTRACT),
        },
    )


def build_replay_evaluator(context: CandidateReplayContext):
    if context.campaign_id != "two_period_overlay":
        raise ValueError("replay context belongs to a different campaign")
    payload = context.payload
    from rune_decrypter_prime.api import by_name, cipher_instance
    from rune_decrypter_prime.api.wrappers.registry import build_cipher_config
    from rune_decrypter_prime.core.config import HardCribConfig, ScoringConfig
    from rune_decrypter_prime.core.engine.builders import build_scorer
    from rune_decrypter_prime.core.problem.runtime import DecryptionProblem
    from rune_decrypter_prime.core.types import Device, Direction

    ciphertext = np.asarray(payload["ciphertext"], dtype=np.uint8)
    wli = tuple((int(a), int(b)) for a, b in payload["wli"])
    crib = np.asarray(payload["crib"], dtype=np.uint8)
    particular = np.asarray(payload["particular"], dtype=np.uint8)
    basis = np.asarray(payload["basis"], dtype=np.uint8)
    scoring_contract = dict(payload["scoring"])
    spec, key_spec = by_name.cipher_with_key(
        "two_period_vigenere",
        period_a=int(payload["period_a"]),
        period_b=int(payload["period_b"]),
        schedule=str(payload["schedule"]),
        alphabet_size=int(payload["alphabet_size"]),
        default_key=True,
    )
    cipher = cipher_instance(spec)
    direction = Direction(str(scoring_contract["encoding_direction"]))
    cipher_cfg = build_cipher_config(
        cipher=spec,
        key=key_spec,
        ciphertext=ciphertext,
        wli=[list(pair) for pair in wli],
        device=Device.CPU,
        encoding_dir=direction,
        initial_text_permutation_indices=None,
        initial_keys=None,
        interruptors=None,
        interruptors_exact=None,
        interruptors_pool=None,
        interruptors_max=None,
    )
    hard_crib = HardCribConfig(
        enabled=bool(scoring_contract["hard_crib"]),
        fixed_chars={int(payload["crib_start"]) + i: [int(value)] for i, value in enumerate(crib)},
    )
    scoring = ScoringConfig(
        objective=str(scoring_contract["objective"]),
        include_char=bool(scoring_contract["include_char"]),
        use_word_breaks=bool(scoring_contract["use_word_breaks"]),
        n_char=int(scoring_contract["n_char"]),
        n_wli=int(scoring_contract["n_wli"]),
        char_weights={int(k): float(v) for k, v in scoring_contract["char_weights"].items()},
        wli_weights={int(k): float(v) for k, v in scoring_contract["wli_weights"].items()},
        encoding_dir=direction,
        hard_crib=hard_crib,
    )
    problem = DecryptionProblem(
        cipher=cipher,
        scorer=build_scorer(cipher_cfg, scoring),
        c_cfg=cipher_cfg,
        s_cfg=scoring,
        enable_telemetry=False,
    )

    def evaluator(candidate, _context):
        variables = np.asarray(candidate.payload["variables"], dtype=np.uint8)
        stored_key = np.asarray(candidate.payload["expanded_key"], dtype=np.uint8)
        rebuilt = expand(variables, particular, basis)
        if not np.array_equal(rebuilt, stored_key):
            raise ValueError("candidate variables do not reproduce the stored expanded key")
        score = float(np.asarray(problem.evaluate_keys(stored_key[None, :]))[0])
        return ReplayEvaluation(
            scores={DECISION_SCORE: score},
            stable_metrics={
                "candidate_id": candidate.candidate_id,
                "payload_valid": True,
                "gauge_valid": bool(int(stored_key[PERIOD_A]) == 0),
            },
        )

    return evaluator


def _resolve_source_run(repo_root: Path, run_id: str) -> Path:
    if not run_id or run_id in {".", ".."} or "/" in run_id or "\\" in run_id:
        raise ValueError("source run ID must be one directory name")
    campaign_root = (
        repo_root / "output/cipher_development/two_period_overlay"
    ).resolve()
    run_dir = (campaign_root / run_id).resolve()
    if campaign_root not in run_dir.parents:
        raise ValueError("source run ID escaped the campaign output root")
    return run_dir


def _safe_source_path(run_dir: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("source artifact path must be relative and remain within the run")
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
    manifest_path = source_run / "artifacts/experiment_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("campaign_id") != "two_period_overlay":
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
            "campaign": "two_period_overlay",
            "context_id": context.context_id,
            "decision_score": DECISION_SCORE_NAME,
        },
        repeat_count=REPEAT_COUNT,
        absolute_tolerance=ABSOLUTE_TOLERANCE,
        relative_tolerance=RELATIVE_TOLERANCE,
    )
    spec = ExperimentSpec(
        campaign_id="two_period_overlay",
        experiment_id="wp5_candidate_replay",
        benchmark_id="alice_308_p13_p17",
        question="Can a saved WP3 candidate batch be rescored deterministically without discovery?",
        hypothesis=(
            "The saved candidate surface and truth-free context reproduce "
            "its scores and order."
        ),
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
