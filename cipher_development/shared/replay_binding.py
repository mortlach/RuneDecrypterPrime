from __future__ import annotations
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from cipher_development.shared.archive import _atomic_write_json, _canonical_json
from cipher_development.shared.replay import (
    CandidateReplayBatch,
    CandidateReplayContext,
    _hash40,
    _identifier,
    _strict_keys,
    _text,
    read_candidate_batch,
    read_replay_context,
)

BINDING_SCHEMA = "rdp_cipher_development_replay_binding.v1"
_MANIFEST_SCHEMA = "rdp_cipher_development_experiment_manifest.v1"
_RESULT_SCHEMA = "rdp_cipher_development_experiment_result.v1"
_BINDING_KEYS = frozenset(
    {
        "schema",
        "binding_id",
        "campaign_id",
        "source_run_id",
        "configuration_hash",
        "benchmark_id",
        "context_id",
        "batch_id",
        "source_archive_hash",
        "source_decision_score",
        "context_artifact",
        "batch_artifact",
    }
)


def _artifact(value: Any, name: str) -> str:
    text = _text(value, name).replace("\\", "/")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or not path.parts
        or ".." in path.parts
        or ("." in path.parts)
    ):
        raise ValueError(f"{name} must be a relative artifact path without traversal")
    if path.parts[0] != "artifacts":
        raise ValueError(f"{name} must stay below the run's artifacts directory")
    return path.as_posix()


def _binding_content(
    *,
    campaign_id: str,
    source_run_id: str,
    configuration_hash: str,
    benchmark_id: str,
    context_id: str,
    batch_id: str,
    source_archive_hash: str,
    source_decision_score: str,
    context_artifact: str,
    batch_artifact: str,
) -> dict[str, Any]:
    return {
        "schema": BINDING_SCHEMA,
        "campaign_id": campaign_id,
        "source_run_id": source_run_id,
        "configuration_hash": configuration_hash,
        "benchmark_id": benchmark_id,
        "context_id": context_id,
        "batch_id": batch_id,
        "source_archive_hash": source_archive_hash,
        "source_decision_score": source_decision_score,
        "context_artifact": context_artifact,
        "batch_artifact": batch_artifact,
    }


def _binding_id(content: Mapping[str, Any]) -> str:
    return hashlib.blake2b(
        _canonical_json(content, "replay_binding").encode("utf-8"),
        digest_size=20,
        person=b"rdp-binding-v1",
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class CandidateReplayBinding:
    schema: str
    binding_id: str
    campaign_id: str
    source_run_id: str
    configuration_hash: str
    benchmark_id: str
    context_id: str
    batch_id: str
    source_archive_hash: str
    source_decision_score: str
    context_artifact: str
    batch_artifact: str

    def __post_init__(self) -> None:
        if self.schema != BINDING_SCHEMA:
            raise ValueError(f"schema must be {BINDING_SCHEMA!r}")
        campaign_id = _identifier(self.campaign_id, "campaign_id")
        source_run_id = _text(self.source_run_id, "source_run_id")
        configuration_hash = _hash40(self.configuration_hash, "configuration_hash")
        benchmark_id = _identifier(self.benchmark_id, "benchmark_id")
        context_id = _hash40(self.context_id, "context_id")
        batch_id = _hash40(self.batch_id, "batch_id")
        source_archive_hash = _hash40(self.source_archive_hash, "source_archive_hash")
        source_decision_score = _text(
            self.source_decision_score, "source_decision_score"
        )
        context_artifact = _artifact(self.context_artifact, "context_artifact")
        batch_artifact = _artifact(self.batch_artifact, "batch_artifact")
        content = _binding_content(
            campaign_id=campaign_id,
            source_run_id=source_run_id,
            configuration_hash=configuration_hash,
            benchmark_id=benchmark_id,
            context_id=context_id,
            batch_id=batch_id,
            source_archive_hash=source_archive_hash,
            source_decision_score=source_decision_score,
            context_artifact=context_artifact,
            batch_artifact=batch_artifact,
        )
        expected = _binding_id(content)
        if str(self.binding_id) != expected:
            raise ValueError("binding_id does not match replay binding content")
        for name, value in content.items():
            if name != "schema":
                object.__setattr__(self, name, value)
        object.__setattr__(self, "binding_id", expected)

    @classmethod
    def create(
        cls,
        *,
        campaign_id: str,
        source_run_id: str,
        configuration_hash: str,
        benchmark_id: str,
        context: CandidateReplayContext,
        batch: CandidateReplayBatch,
        context_artifact: str,
        batch_artifact: str,
    ) -> "CandidateReplayBinding":
        if context.campaign_id != campaign_id:
            raise ValueError("replay context belongs to a different campaign")
        if context.run_id != source_run_id:
            raise ValueError("replay context belongs to a different source run")
        if context.configuration_hash != configuration_hash:
            raise ValueError("replay context configuration hash does not match")
        content = _binding_content(
            campaign_id=_identifier(campaign_id, "campaign_id"),
            source_run_id=_text(source_run_id, "source_run_id"),
            configuration_hash=_hash40(configuration_hash, "configuration_hash"),
            benchmark_id=_identifier(benchmark_id, "benchmark_id"),
            context_id=context.context_id,
            batch_id=batch.batch_id,
            source_archive_hash=batch.source_archive_hash,
            source_decision_score=batch.source_decision_score,
            context_artifact=_artifact(context_artifact, "context_artifact"),
            batch_artifact=_artifact(batch_artifact, "batch_artifact"),
        )
        return cls(binding_id=_binding_id(content), **content)

    def validate(
        self, batch: CandidateReplayBatch, context: CandidateReplayContext
    ) -> None:
        mismatches = []
        expected = {
            "campaign_id": context.campaign_id,
            "source_run_id": context.run_id,
            "configuration_hash": context.configuration_hash,
            "context_id": context.context_id,
            "batch_id": batch.batch_id,
            "source_archive_hash": batch.source_archive_hash,
            "source_decision_score": batch.source_decision_score,
        }
        for name, value in expected.items():
            if getattr(self, name) != value:
                mismatches.append(name)
        if mismatches:
            raise ValueError(
                f"replay binding does not match batch/context fields: {mismatches}"
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            **_binding_content(
                campaign_id=self.campaign_id,
                source_run_id=self.source_run_id,
                configuration_hash=self.configuration_hash,
                benchmark_id=self.benchmark_id,
                context_id=self.context_id,
                batch_id=self.batch_id,
                source_archive_hash=self.source_archive_hash,
                source_decision_score=self.source_decision_score,
                context_artifact=self.context_artifact,
                batch_artifact=self.batch_artifact,
            ),
        }

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "CandidateReplayBinding":
        if not isinstance(payload, Mapping):
            raise TypeError("replay binding must be a mapping")
        _strict_keys(payload, _BINDING_KEYS, "replay binding")
        return cls(**dict(payload))


def write_replay_binding(path: Path, binding: CandidateReplayBinding) -> None:
    if not isinstance(binding, CandidateReplayBinding):
        raise TypeError("binding must be a CandidateReplayBinding")
    _atomic_write_json(path, binding.to_json_dict())


def read_replay_binding(path: Path) -> CandidateReplayBinding:
    if not isinstance(path, Path):
        raise TypeError("path must be a Path")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed replay binding JSON: {exc.msg}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != BINDING_SCHEMA:
        raise ValueError(f"replay binding schema must be {BINDING_SCHEMA!r}")
    return CandidateReplayBinding.from_json_dict(payload)


def resolve_run_artifact(run_dir: Path, relative: str | Path) -> Path:
    rel = _artifact(str(relative), "artifact path")
    root = run_dir.resolve()
    resolved = (root / PurePosixPath(rel)).resolve()
    if root not in resolved.parents:
        raise ValueError("artifact path escaped the source run")
    return resolved


def _binding_summary_entries(
    result_summary: Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    raw = result_summary.get("replay_bindings", {})
    if isinstance(raw, Mapping):
        return [item for item in raw.values() if isinstance(item, Mapping)]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, Mapping)]
    return []


def load_bound_replay_source(
    run_dir: Path,
    binding_artifact: str | Path,
    *,
    expected_campaign_id: str,
    expected_run_id: str | None = None,
):
    run_dir = run_dir.resolve()
    manifest_path = run_dir / "artifacts/experiment_manifest.json"
    result_path = run_dir / "artifacts/experiment_result.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed source experiment JSON: {exc.msg}") from exc
    if manifest.get("schema") != _MANIFEST_SCHEMA:
        raise ValueError("source manifest has an unsupported schema")
    if result.get("schema") != _RESULT_SCHEMA:
        raise ValueError("source result has an unsupported schema")
    run_id = _text(expected_run_id or run_dir.name, "source_run_id")
    for payload_name, payload in (("manifest", manifest), ("result", result)):
        if payload.get("campaign_id") != expected_campaign_id:
            raise ValueError(f"source {payload_name} belongs to a different campaign")
        if payload.get("run_id") != run_id:
            raise ValueError(f"source {payload_name} run ID does not match")
    if result.get("status") != "completed":
        raise ValueError("source experiment result must be completed")
    configuration_hash = manifest.get("configuration_hash")
    binding_path = resolve_run_artifact(run_dir, binding_artifact)
    binding = read_replay_binding(binding_path)
    context = read_replay_context(
        resolve_run_artifact(run_dir, binding.context_artifact)
    )
    batch = read_candidate_batch(resolve_run_artifact(run_dir, binding.batch_artifact))
    binding.validate(batch, context)
    if binding.campaign_id != expected_campaign_id or binding.source_run_id != run_id:
        raise ValueError("replay binding does not identify the selected source run")
    if binding.configuration_hash != configuration_hash:
        raise ValueError(
            "replay binding configuration hash does not match the manifest"
        )
    entries = _binding_summary_entries(result.get("result_summary", {}))
    if not any(
        (
            item.get("binding_id") == binding.binding_id
            and item.get("artifact")
            == _artifact(str(binding_artifact), "binding_artifact")
            for item in entries
        )
    ):
        raise ValueError("source result does not record the configured replay binding")
    return (manifest, result, binding, context, batch)


__all__ = [
    "BINDING_SCHEMA",
    "CandidateReplayBinding",
    "load_bound_replay_source",
    "read_replay_binding",
    "resolve_run_artifact",
    "write_replay_binding",
]
