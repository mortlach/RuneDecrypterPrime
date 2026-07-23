from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from cipher_development.shared.ledger import ExperimentLedgerRow, read_ledger
from cipher_development.shared.replay_evidence import read_candidate_replay

SCHEMA = "rdp_cipher_development_milestone_summary.v1"
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_RESULT_SCHEMA = "rdp_cipher_development_experiment_result.v1"
_OUTPUT_BASE = Path("output/cipher_development")
_PROPOSAL_KEYS = frozenset({
    "proposal_id", "title", "suggested_status", "scope",
    "evidence_run_ids", "reason", "known_limits",
})
_LESSON_STATUSES = frozenset({
    "candidate", "supported", "general", "limited", "superseded", "rejected",
})


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} must use lowercase letters, numbers, '_' or '-'")
    return value


def _json_value(value: Any, name: str) -> Any:
    if isinstance(value, Path):
        raise TypeError(f"{name} must not contain Path values")
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} contains a non-finite float")
        return float(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(f"{name} mapping keys must be non-empty strings")
            out[key] = _json_value(item, f"{name}.{key}")
        return out
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f"{name}[]") for item in value]
    if isinstance(value, (set, frozenset)):
        raise TypeError(f"{name} must not contain sets")
    if callable(value):
        raise TypeError(f"{name} must not contain callables")
    raise TypeError(f"{name} contains unsupported type {type(value).__name__}")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def _lesson_proposal(value: Any, selected_run_ids: tuple[str, ...]) -> Mapping[str, Any]:
    proposal = _json_value(value, "candidate_lesson_proposals[]")
    if not isinstance(proposal, dict):
        raise TypeError("candidate lesson proposals must be mappings")
    keys = frozenset(proposal)
    unknown = keys - _PROPOSAL_KEYS
    missing = _PROPOSAL_KEYS - keys
    if unknown:
        raise ValueError(f"candidate lesson proposal has unknown fields: {sorted(unknown)}")
    if missing:
        raise ValueError(f"candidate lesson proposal is missing fields: {sorted(missing)}")
    proposal["proposal_id"] = _identifier(proposal["proposal_id"], "proposal_id")
    for name in ("title", "scope", "reason", "known_limits"):
        proposal[name] = _text(proposal[name], name)
    status = _text(proposal["suggested_status"], "suggested_status")
    if status not in _LESSON_STATUSES:
        raise ValueError(f"suggested_status must be one of {sorted(_LESSON_STATUSES)}")
    proposal["suggested_status"] = status
    evidence = proposal["evidence_run_ids"]
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("evidence_run_ids must be a non-empty list")
    evidence_ids = [_text(item, "evidence_run_ids[]") for item in evidence]
    if len(set(evidence_ids)) != len(evidence_ids):
        raise ValueError("evidence_run_ids must be unique")
    missing_runs = sorted(set(evidence_ids) - set(selected_run_ids))
    if missing_runs:
        raise ValueError(
            f"candidate lesson evidence is not selected in this milestone: {missing_runs}"
        )
    proposal["evidence_run_ids"] = evidence_ids
    return MappingProxyType(proposal)


@dataclass(frozen=True, slots=True)
class MilestoneSpec:
    milestone_id: str
    campaign_id: str
    title: str
    as_of: str
    selected_run_ids: tuple[str, ...]
    include_reference_evaluation: bool = False
    candidate_lesson_proposals: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        milestone_id = _identifier(self.milestone_id, "milestone_id")
        campaign_id = _identifier(self.campaign_id, "campaign_id")
        title = _text(self.title, "title")
        as_of = _text(self.as_of, "as_of")
        run_ids = tuple(_text(item, "selected_run_ids[]") for item in self.selected_run_ids)
        if not run_ids:
            raise ValueError("selected_run_ids must not be empty")
        if len(set(run_ids)) != len(run_ids):
            raise ValueError("selected_run_ids must be unique")
        if type(self.include_reference_evaluation) is not bool:
            raise TypeError("include_reference_evaluation must be a bool")
        proposals = tuple(
            _lesson_proposal(item, run_ids)
            for item in self.candidate_lesson_proposals
        )
        object.__setattr__(self, "milestone_id", milestone_id)
        object.__setattr__(self, "campaign_id", campaign_id)
        object.__setattr__(self, "title", title)
        object.__setattr__(self, "as_of", as_of)
        object.__setattr__(self, "selected_run_ids", run_ids)
        object.__setattr__(self, "candidate_lesson_proposals", proposals)


@dataclass(frozen=True, slots=True)
class MilestoneSummary:
    schema: str
    milestone_id: str
    campaign_id: str
    title: str
    as_of: str
    source_hashes: Mapping[str, str]
    selected_runs: tuple[Mapping[str, Any], ...]
    decision_counts: Mapping[str, int]
    status_counts: Mapping[str, int]
    mechanisms_seen: tuple[str, ...]
    configuration_hashes: tuple[str, ...]
    latest_completed_run_id: str | None
    candidate_lesson_proposals: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        if self.schema != SCHEMA:
            raise ValueError(f"schema must be {SCHEMA!r}")
        object.__setattr__(self, "milestone_id", _identifier(self.milestone_id, "milestone_id"))
        object.__setattr__(self, "campaign_id", _identifier(self.campaign_id, "campaign_id"))
        object.__setattr__(self, "title", _text(self.title, "title"))
        object.__setattr__(self, "as_of", _text(self.as_of, "as_of"))
        object.__setattr__(
            self,
            "source_hashes",
            MappingProxyType(_json_value(self.source_hashes, "source_hashes")),
        )
        object.__setattr__(self, "selected_runs", tuple(
            MappingProxyType(_json_value(item, "selected_runs[]")) for item in self.selected_runs
        ))
        object.__setattr__(
            self,
            "decision_counts",
            MappingProxyType(_json_value(self.decision_counts, "decision_counts")),
        )
        object.__setattr__(
            self,
            "status_counts",
            MappingProxyType(_json_value(self.status_counts, "status_counts")),
        )
        object.__setattr__(
            self,
            "mechanisms_seen",
            tuple(sorted({
                _text(item, "mechanisms_seen[]")
                for item in self.mechanisms_seen
            })),
        )
        object.__setattr__(
            self,
            "configuration_hashes",
            tuple(sorted({
                _text(item, "configuration_hashes[]")
                for item in self.configuration_hashes
            })),
        )
        if self.latest_completed_run_id is not None:
            object.__setattr__(
                self,
                "latest_completed_run_id",
                _text(self.latest_completed_run_id, "latest_completed_run_id"),
            )
        object.__setattr__(self, "candidate_lesson_proposals", tuple(
            MappingProxyType(_json_value(item, "candidate_lesson_proposals[]"))
            for item in self.candidate_lesson_proposals
        ))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "milestone_id": self.milestone_id,
            "campaign_id": self.campaign_id,
            "title": self.title,
            "as_of": self.as_of,
            "source_hashes": dict(self.source_hashes),
            "selected_runs": [dict(item) for item in self.selected_runs],
            "decision_counts": dict(self.decision_counts),
            "status_counts": dict(self.status_counts),
            "mechanisms_seen": list(self.mechanisms_seen),
            "configuration_hashes": list(self.configuration_hashes),
            "latest_completed_run_id": self.latest_completed_run_id,
            "candidate_lesson_proposals": [dict(item) for item in self.candidate_lesson_proposals],
        }


def _safe_run_artifact(run_dir: Path, relpath: str) -> Path:
    relative = Path(_text(relpath, "artifact"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("artifact path must remain below the selected run")
    resolved = (run_dir / relative).resolve()
    if run_dir.resolve() not in resolved.parents:
        raise ValueError("artifact path escaped the selected run")
    return resolved


def _load_result(path: Path, row: ExperimentLedgerRow, include_reference: bool,
                 source_hashes: dict[str, str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed result JSON for run {row.run_id}: {exc.msg}") from exc
    if not isinstance(payload, Mapping) or payload.get("schema") != _RESULT_SCHEMA:
        raise ValueError(f"run {row.run_id} has an unsupported experiment result schema")
    for name, expected in (
        ("run_id", row.run_id),
        ("campaign_id", row.campaign_id),
        ("status", row.status),
        ("decision", row.decision),
    ):
        if payload.get(name) != expected:
            raise ValueError(f"ledger/result {name} mismatch for run {row.run_id}")
    reference = payload.get("reference_evaluation")
    if include_reference and row.truth_policy == "none":
        raise ValueError("blind runs cannot opt in to reference evaluation")
    summary = payload.get("result_summary", {})
    if not isinstance(summary, Mapping):
        raise TypeError(f"run {row.run_id} result_summary must be a mapping")
    replay_summary = None
    if "replay_id" in summary:
        artifact_path = _safe_run_artifact(path.parent.parent, summary.get("artifact", ""))
        if not artifact_path.is_file():
            raise FileNotFoundError(artifact_path)
        evidence = read_candidate_replay(artifact_path)
        checks = {
            "replay_id": evidence.replay_id,
            "source_binding_id": evidence.source_binding_id,
            "source_batch_id": evidence.source_batch_id,
            "source_context_id": evidence.source_context_id,
            "deterministic": evidence.deterministic,
            "stored_scores_verified": evidence.stored_scores_verified,
            "ranking": list(evidence.ranking),
        }
        for name, expected in checks.items():
            if summary.get(name) != expected:
                raise ValueError(f"replay result summary {name} mismatch for run {row.run_id}")
        source_hashes[f"replay:{row.run_id}"] = _sha256(artifact_path)
        replay_summary = {
            **checks,
            "mode": evidence.mode.value,
            "candidate_count": len(evidence.candidate_ids),
            "artifact": str(summary["artifact"]),
        }
    result = {
        "run_id": row.run_id,
        "experiment_id": row.experiment_id,
        "benchmark_id": row.benchmark_id,
        "hypothesis": row.hypothesis,
        "alternative": row.alternative,
        "status": row.status,
        "decision": row.decision,
        "stop_category": row.stop_category,
        "stop_reason": row.stop_reason,
        "elapsed_s": row.elapsed_s,
        "configuration_hash": row.configuration_hash,
        "wli_mode": row.wli_mode,
        "truth_policy": row.truth_policy,
        "mechanisms": list(row.mechanisms),
        "budget_seconds": row.budget_seconds,
        "budget_evaluations": row.budget_evaluations,
        "lesson_ids": list(row.lesson_ids),
        "result_summary": dict(summary),
        "reference_evaluation_present": reference is not None,
        **({"reference_evaluation": reference} if include_reference else {}),
    }
    if replay_summary is not None:
        result["replay_evidence"] = replay_summary
    return result


def build_milestone_summary(repo_root: Path, spec: MilestoneSpec) -> MilestoneSummary:
    if not isinstance(repo_root, Path):
        raise TypeError("repo_root must be a Path")
    if not isinstance(spec, MilestoneSpec):
        raise TypeError("spec must be a MilestoneSpec")
    root = repo_root.resolve()
    campaign_root = (root / _OUTPUT_BASE / spec.campaign_id).resolve()
    output_base = (root / _OUTPUT_BASE).resolve()
    if output_base != campaign_root and output_base not in campaign_root.parents:
        raise ValueError("campaign output root escaped output/cipher_development")
    ledger_path = campaign_root / "experiment_ledger.jsonl"
    rows = read_ledger(ledger_path)
    ids = [row.run_id for row in rows]
    duplicates = sorted({run_id for run_id in ids if ids.count(run_id) > 1})
    if duplicates:
        raise ValueError(f"source ledger contains duplicate run IDs: {duplicates}")
    by_id = {row.run_id: row for row in rows}
    ledger_order = {row.run_id: index for index, row in enumerate(rows)}
    missing = [run_id for run_id in spec.selected_run_ids if run_id not in by_id]
    if missing:
        raise ValueError(f"selected run IDs are absent from the ledger: {missing}")
    campaign_doc = root / "cipher_development" / spec.campaign_id / "CAMPAIGN.md"
    lessons_doc = root / "cipher_development" / "LESSONS.md"
    for path in (ledger_path, campaign_doc, lessons_doc):
        if not path.is_file():
            raise FileNotFoundError(path)
    selected: list[dict[str, Any]] = []
    source_hashes: dict[str, str] = {
        "ledger": _sha256(ledger_path),
        "campaign_brief": _sha256(campaign_doc),
        "lesson_registry": _sha256(lessons_doc),
    }
    for run_id in spec.selected_run_ids:
        row = by_id[run_id]
        if row.campaign_id != spec.campaign_id:
            raise ValueError(f"run {run_id} belongs to a different campaign")
        result_path = (ledger_path.parent / row.result_relpath).resolve()
        if campaign_root != result_path and campaign_root not in result_path.parents:
            raise ValueError(f"result path escaped campaign output root for run {run_id}")
        if not result_path.is_file():
            raise FileNotFoundError(result_path)
        source_hashes[f"result:{run_id}"] = _sha256(result_path)
        selected.append(_load_result(
            result_path, row, spec.include_reference_evaluation, source_hashes
        ))
    decisions = Counter(str(item["decision"]) for item in selected if item["decision"] is not None)
    statuses = Counter(str(item["status"]) for item in selected)
    completed_ids = [item["run_id"] for item in selected if item["status"] == "completed"]
    latest_completed = max(completed_ids, key=ledger_order.__getitem__) if completed_ids else None
    mechanisms = tuple(sorted({
        mechanism for item in selected for mechanism in item.get("mechanisms", [])
    }))
    config_hashes = tuple(sorted({str(item["configuration_hash"]) for item in selected}))
    return MilestoneSummary(
        schema=SCHEMA,
        milestone_id=spec.milestone_id,
        campaign_id=spec.campaign_id,
        title=spec.title,
        as_of=spec.as_of,
        source_hashes=source_hashes,
        selected_runs=tuple(selected),
        decision_counts=dict(sorted(decisions.items())),
        status_counts=dict(sorted(statuses.items())),
        mechanisms_seen=mechanisms,
        configuration_hashes=config_hashes,
        latest_completed_run_id=latest_completed,
        candidate_lesson_proposals=spec.candidate_lesson_proposals,
    )


def render_milestone_markdown(summary: MilestoneSummary) -> str:
    lines = [
        f"# {summary.title}", "",
        f"- Milestone: `{summary.milestone_id}`",
        f"- Campaign: `{summary.campaign_id}`",
        f"- As of: `{summary.as_of}`", "", "## Source evidence", "",
    ]
    for name, digest in sorted(summary.source_hashes.items()):
        lines.append(f"- `{name}`: `{digest}`")
    lines.extend([
        "", "## Runs", "",
        "| Run | Experiment | Status | Decision | Stop reason | Configuration |",
        "|---|---|---|---|---|---|",
    ])
    for row in summary.selected_runs:
        lines.append(
            "| `{run_id}` | `{experiment_id}` | {status} | {decision} | `{stop_reason}` | "
            "`{configuration_hash}` |".format(**row)
        )
    lines.extend([
        "", "## Decisions", "",
        f"- Decision counts: `{json.dumps(dict(summary.decision_counts), sort_keys=True)}`",
        f"- Status counts: `{json.dumps(dict(summary.status_counts), sort_keys=True)}`",
        f"- Latest completed run: `{summary.latest_completed_run_id}`",
        "", "## Failure mechanisms", "",
        ", ".join(f"`{item}`" for item in summary.mechanisms_seen) or "None recorded.",
        "", "## Configuration changes", "",
    ])
    lines.extend(f"- `{item}`" for item in summary.configuration_hashes)
    lines.extend(["", "## Replay evidence", ""])
    replay_rows = [row for row in summary.selected_runs if "replay_evidence" in row]
    if replay_rows:
        for row in replay_rows:
            rendered = json.dumps(row["replay_evidence"], sort_keys=True)
            lines.append(f"- `{row['run_id']}`: `{rendered}`")
    else:
        lines.append("No selected replay runs.")
    if any("reference_evaluation" in row for row in summary.selected_runs):
        lines.extend(["", "## Reference evidence", ""])
        for row in summary.selected_runs:
            if "reference_evaluation" in row:
                lines.append(f"- `{row['run_id']}`: present in JSON summary.")
    lines.extend(["", "## Candidate lesson proposals", ""])
    if summary.candidate_lesson_proposals:
        for proposal in summary.candidate_lesson_proposals:
            lines.append(f"- `{json.dumps(dict(proposal), sort_keys=True)}`")
    else:
        lines.append("None supplied.")
    lines.extend([
        "", "## Required human decisions", "",
        "- Confirm that the selected runs are the correct evidence set.",
        "- Review candidate lessons manually; this synthesis does not edit `LESSONS.md`.",
        "- Update the campaign brief only after reviewing the raw artifacts.", "",
    ])
    return "\n".join(lines)


def write_milestone(repo_root: Path, spec: MilestoneSpec) -> tuple[Path, Path]:
    summary = build_milestone_summary(repo_root, spec)
    output_dir = (
        repo_root.resolve() / _OUTPUT_BASE / spec.campaign_id / "milestones" / spec.milestone_id
    )
    json_path = output_dir / "milestone_summary.json"
    md_path = output_dir / "milestone_summary.md"
    json_text = json.dumps(
        summary.to_json_dict(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
    ) + "\n"
    _atomic_text(json_path, json_text)
    _atomic_text(md_path, render_milestone_markdown(summary))
    return json_path, md_path


__all__ = [
    "MilestoneSpec", "MilestoneSummary", "build_milestone_summary",
    "render_milestone_markdown", "write_milestone",
]
