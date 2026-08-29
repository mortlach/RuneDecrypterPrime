"""First-class display/share contract for RDP runs.

This module is intentionally API-level, not tutorial-specific. It builds a
small, JSON-safe view of the main objects users need to inspect, debug, review,
and share: problem/input summary, cipher/key/solver/scoring configuration,
solver result, solver report, scorer report, telemetry, stop reason, oracle use,
tutorial metadata, LP evidence metadata, and artifact/report paths.

Scope in v1:
- consume the existing public API objects where available: RunSpec, CipherSpec,
  KeySpec, SolverSpec, RunResult, Solution, SolverReport, and ScorerReport;
- avoid changing solver/scorer behaviour;
- provide deterministic, compact console text plus a stable JSON payload;
- make missing context visible through warnings rather than guessing;
- use one standard summary schema for tutorials, examples, LP evidence, user
  scripts, and future GUI/report consumers;
- never expose absolute local filesystem paths in display output.

Known gaps / TODOs:
- RDP does not yet attach the originating RunSpec to RunResult, so callers should
  pass ``spec=...`` when they want complete problem/cipher/key/scoring display;
- ScoringConfig has many fields; v1 displays API scorer params and a compact
  scope note rather than mirroring every normalised ScoringConfig attribute;
- ScorerReport is not always returned by normal solves yet, so it is optional;
- artifact path discovery is caller-supplied unless a logging/run-dir layer adds
  a display-summary artifact in a later patch;
- this module is a display/share view, not a persistence format for resuming
searches or reproducing full solver state.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from pathlib import Path, PurePosixPath
from typing import Any, TextIO

from rdp.api.artifact_agreement import KnownArtifactRelpath
from rdp.api.run_result import RunResult
from rdp.api.run_spec import RawTextInput, RuneIndexInput, RunSpec, SourceReferenceInput
from rdp.api.solver_report import SolverReport
from rdp.api.specs import KeySpec
from rdp.api.stop_reason_contract import (
    StopReasonDetailKey,
    stop_category_for_reason,
    stop_reason_details_from_solution,
)

SUMMARY_SCHEMA = "api_display_summary.v1"
SUMMARY_RELATIVE_PATH = KnownArtifactRelpath.RDP_DISPLAY_SUMMARY.value
_PARTIAL_RECOVERY_ACCEPTANCE = "partial_recovery"
_OPSEC_PATH_PARENT_NAMES = frozenset({"artifacts", "config", "logs", "trace", "traces", "output"})
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class SummaryOptions:
    """Controls how much of the standard RDP run summary is shown."""

    mode: str = "standard"
    include_plaintext: bool = True
    include_ciphertext: bool = True
    include_key: bool = True
    include_solver_report: bool = True
    include_scorer_report: bool = True
    include_telemetry_summary: bool = True
    plaintext_preview_chars: int = 500
    ciphertext_preview_chars: int = 240
    max_sequence_preview: int = 40
    include_scope_notes: bool = True

    def __post_init__(self) -> None:
        _require_text(self.mode, "mode")
        _require_bool(self.include_plaintext, "include_plaintext")
        _require_bool(self.include_ciphertext, "include_ciphertext")
        _require_bool(self.include_key, "include_key")
        _require_bool(self.include_solver_report, "include_solver_report")
        _require_bool(self.include_scorer_report, "include_scorer_report")
        _require_bool(self.include_telemetry_summary, "include_telemetry_summary")
        _require_bool(self.include_scope_notes, "include_scope_notes")
        _require_nonnegative_int(self.plaintext_preview_chars, "plaintext_preview_chars")
        _require_nonnegative_int(self.ciphertext_preview_chars, "ciphertext_preview_chars")
        _require_nonnegative_int(self.max_sequence_preview, "max_sequence_preview")

    @classmethod
    def standard(cls) -> "SummaryOptions":
        return cls(mode="standard")

    @classmethod
    def for_console(cls) -> "SummaryOptions":
        return cls(mode="console", plaintext_preview_chars=500, ciphertext_preview_chars=180)

    @classmethod
    def for_tutorial(cls) -> "SummaryOptions":
        return cls(mode="tutorial", plaintext_preview_chars=700, ciphertext_preview_chars=200)

    @classmethod
    def for_lp_evidence(cls) -> "SummaryOptions":
        return cls(mode="lp_evidence", plaintext_preview_chars=2000, ciphertext_preview_chars=320)

    @classmethod
    def for_debug(cls) -> "SummaryOptions":
        return cls(mode="debug", plaintext_preview_chars=2000, ciphertext_preview_chars=800, max_sequence_preview=120)


@dataclass(frozen=True, slots=True)
class DisplaySummary:
    """JSON-safe, shareable standard display view of an RDP run."""

    schema: str = SUMMARY_SCHEMA
    problem: Mapping[str, Any] = field(default_factory=dict)
    cipher: Mapping[str, Any] = field(default_factory=dict)
    key: Mapping[str, Any] = field(default_factory=dict)
    solver: Mapping[str, Any] = field(default_factory=dict)
    scoring: Mapping[str, Any] = field(default_factory=dict)
    result: Mapping[str, Any] = field(default_factory=dict)
    solver_report: Mapping[str, Any] | None = None
    scorer_report: Mapping[str, Any] | None = None
    telemetry: Mapping[str, Any] = field(default_factory=dict)
    stop: Mapping[str, Any] = field(default_factory=dict)
    oracle: Mapping[str, Any] = field(default_factory=dict)
    tutorial: Mapping[str, Any] | None = None
    lp_evidence: Mapping[str, Any] | None = None
    artifacts: Mapping[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema", _require_text(self.schema, "schema"))
        for field_name in (
            "problem",
            "cipher",
            "key",
            "solver",
            "scoring",
            "result",
            "telemetry",
            "stop",
            "oracle",
            "artifacts",
        ):
            object.__setattr__(self, field_name, _copy_json_mapping(getattr(self, field_name), field_name))
        for field_name in ("solver_report", "scorer_report", "tutorial", "lp_evidence"):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(self, field_name, _copy_json_mapping(value, field_name))
        object.__setattr__(self, "warnings", tuple(_require_text(item, "warnings[]") for item in self.warnings))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "problem": _to_json_value(self.problem),
            "cipher": _to_json_value(self.cipher),
            "key": _to_json_value(self.key),
            "solver": _to_json_value(self.solver),
            "scoring": _to_json_value(self.scoring),
            "result": _to_json_value(self.result),
            "solver_report": _to_json_value(self.solver_report),
            "scorer_report": _to_json_value(self.scorer_report),
            "telemetry": _to_json_value(self.telemetry),
            "stop": _to_json_value(self.stop),
            "oracle": _to_json_value(self.oracle),
            "tutorial": _to_json_value(self.tutorial),
            "lp_evidence": _to_json_value(self.lp_evidence),
            "artifacts": _to_json_value(self.artifacts),
            "warnings": list(self.warnings),
        }


def build_summary(
    value: object,
    *,
    spec: RunSpec | None = None,
    scorer_report: object | None = None,
    reference_plaintext: str | None = None,
    reference_idx: Sequence[int] | None = None,
    tutorial_entry: Mapping[str, Any] | None = None,
    lp_evidence: Mapping[str, Any] | None = None,
    artifacts: Mapping[str, Any] | None = None,
    artifact_manifest_path: str | Path | None = None,
    options: SummaryOptions | None = None,
) -> DisplaySummary:
    """Build the standard display/share summary from an RDP result or solution."""

    options = options or SummaryOptions.standard()
    if not isinstance(options, SummaryOptions):
        raise TypeError("options must be SummaryOptions or None")
    if spec is not None and not isinstance(spec, RunSpec):
        raise TypeError("spec must be RunSpec or None")

    warnings: list[str] = []
    solution = _solution_from(value)
    solver_report = _solver_report_from(value)

    if spec is None:
        warnings.append(
            "RunSpec was not supplied; problem/cipher/key/scoring display is reconstructed only from result/report fields."
        )
    if solution is None:
        warnings.append("No solution object was available in the supplied value.")
    if solver_report is None:
        warnings.append("No SolverReport was available; call run(..., return_solver_report=True) for full display/share data.")

    problem = _problem_summary(spec, solution, options=options)
    cipher = _cipher_summary(spec, solution, options=options)
    key = _key_summary(spec, solution, solver_report, options=options)
    solver = _solver_summary(spec, solver_report, options=options)
    scoring = _scoring_summary(spec, options=options)
    result = _result_summary(
        solution,
        reference_plaintext=reference_plaintext,
        reference_idx=reference_idx,
        options=options,
    )
    solver_report_json = _solver_report_summary(solver_report, options=options)
    scorer_report_json = _scorer_report_summary(scorer_report, options=options)
    telemetry = _telemetry_summary(solution, options=options)
    stop = _stop_summary(solution, solver_report)
    oracle = _oracle_summary(solution, solver_report)
    tutorial = _tutorial_summary(tutorial_entry, options=options)
    lp = _optional_mapping(lp_evidence, "lp_evidence", options=options)
    artifact_summary = _artifact_summary(
        artifacts,
        artifact_manifest_path=artifact_manifest_path,
        options=options,
    )

    warnings.extend(_policy_warnings(stop=stop, oracle=oracle, tutorial=tutorial, telemetry=telemetry))

    return DisplaySummary(
        problem=problem,
        cipher=cipher,
        key=key,
        solver=solver,
        scoring=scoring,
        result=result,
        solver_report=solver_report_json,
        scorer_report=scorer_report_json,
        telemetry=telemetry,
        stop=stop,
        oracle=oracle,
        tutorial=tutorial,
        lp_evidence=lp,
        artifacts=artifact_summary,
        warnings=tuple(_dedupe(warnings)),
    )


def format_summary(summary: DisplaySummary | object, **build_kwargs: Any) -> str:
    """Return a compact human-readable rendering of the standard summary."""

    if not isinstance(summary, DisplaySummary):
        summary = build_summary(summary, **build_kwargs)

    data = summary.to_json_dict()
    lines: list[str] = ["RDP standard summary", "===================="]

    result = data.get("result") or {}
    solver = data.get("solver") or {}
    cipher = data.get("cipher") or {}
    stop = data.get("stop") or {}
    oracle = data.get("oracle") or {}
    artifacts = data.get("artifacts") or {}
    problem = data.get("problem") or {}

    _append_kv(lines, "schema", data.get("schema"))
    _append_kv(lines, "encoding_dir", problem.get("encoding_dir"))
    _append_kv(lines, "cipher", cipher.get("name") or cipher.get("cipher_name"))
    _append_kv(lines, "solver", solver.get("name") or solver.get("solver_name"))
    _append_kv(lines, "score", result.get("score"))
    _append_kv(lines, "match_ratio", result.get("match_ratio"))
    _append_kv(lines, "stop_reason", stop.get("stop_reason"))
    _append_kv(lines, "stop_category", stop.get("stop_category"))
    _append_kv(lines, "oracle_use", oracle.get("oracle_use"))
    _append_kv(lines, "truth_data_policy", oracle.get("truth_data_policy"))

    plaintext = result.get("plaintext")
    if isinstance(plaintext, Mapping):
        preview = plaintext.get("latin_preview") or plaintext.get("rune_preview")
        if preview:
            lines.extend(["", "Plaintext", "---------", str(preview)])

    key = data.get("key") or {}
    recovered = key.get("recovered_key") if isinstance(key, Mapping) else None
    if isinstance(recovered, Mapping) and recovered.get("preview") is not None:
        lines.extend(["", "Recovered key", "-------------", json.dumps(recovered, ensure_ascii=False)])

    if artifacts:
        lines.extend(["", "Artifacts", "---------"])
        for k, v in artifacts.items():
            _append_kv(lines, str(k), v)

    if data.get("warnings"):
        lines.extend(["", "Warnings", "--------"])
        for warning in data["warnings"]:
            lines.append(f"- {warning}")

    return "\n".join(lines) + "\n"


def print_summary(
    summary: DisplaySummary | object,
    *,
    file: TextIO | None = None,
    **build_kwargs: Any,
) -> None:
    import sys

    target = sys.stdout if file is None else file
    target.write(format_summary(summary, **build_kwargs))


def write_summary_json(summary: DisplaySummary, path: Path | str = SUMMARY_RELATIVE_PATH) -> str:
    """Write a display summary JSON file and return a display-safe POSIX path."""

    if not isinstance(summary, DisplaySummary):
        raise TypeError("summary must be DisplaySummary")
    if isinstance(path, str):
        path = Path(path)
    if not isinstance(path, Path):
        raise TypeError("path must be a Path or string")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(summary.to_json_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return _safe_display_path(path)


def _solution_from(value: object) -> object | None:
    if isinstance(value, RunResult):
        return value
    if isinstance(value, SolverReport):
        return None
    return value


def _solver_report_from(value: object) -> SolverReport | None:
    report = getattr(value, "solver_report", None)
    if isinstance(report, SolverReport):
        return report
    if isinstance(value, SolverReport):
        return value
    return None


def _problem_summary(spec: RunSpec | None, solution: object | None, *, options: SummaryOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if spec is not None:
        inp = spec.problem_input
        if isinstance(inp, RawTextInput):
            out.update({"input_kind": "raw_text", "text_length": len(inp.text), "text_preview": _preview_text(inp.text, 160)})
        elif isinstance(inp, RuneIndexInput):
            out.update(
                {
                    "input_kind": "normalized",
                    "ciphertext_length": len(inp.ct_idx),
                    "has_wli": inp.wli is not None,
                    "wli_length": len(inp.wli) if inp.wli is not None else None,
                }
            )
        elif isinstance(inp, SourceReferenceInput):
            out.update(
                {
                    "input_kind": "source_ref",
                    "source_kind": inp.source_kind,
                    "asset_id": inp.asset_id,
                    "asset_version": inp.asset_version,
                    "ref": _json_value(inp.ref, options=options),
                }
            )
        out["encoding_dir"] = _enum_value(spec.text_direction)
        out["device"] = _enum_value(spec.compute_device)
        out["telemetry_on"] = bool(spec.telemetry_enabled)
    if solution is not None:
        ct_idx = _as_sequence(getattr(solution, "ciphertext_idx", None))
        plaintext_value = getattr(solution, "plaintext", None)
        pt_idx = _as_sequence(
            plaintext_value if isinstance(solution, RunResult) else getattr(solution, "plaintext_idx", None)
        )
        if ct_idx is not None:
            out.setdefault("ciphertext_length", len(ct_idx))
        if pt_idx is not None:
            out.setdefault("plaintext_length", len(pt_idx))
        out.setdefault("has_wli", getattr(solution, "has_wli", None))
        out.setdefault("alphabet", getattr(solution, "alphabet", None))
        out.setdefault("alphabet_size", getattr(solution, "alphabet_size", None))
    if options.include_scope_notes:
        out.setdefault("scope_note", "Problem display is complete only when RunSpec is supplied.")
    return _json_value(out, options=options)


def _cipher_summary(spec: RunSpec | None, solution: object | None, *, options: SummaryOptions) -> dict[str, Any]:
    cipher = getattr(spec, "cipher", None) if spec is not None else None
    out: dict[str, Any] = {}
    if cipher is not None:
        out.update(
            {
                "name": cipher.kind.value,
                "kind": cipher.kind.value,
                "alphabet_size": cipher.parameters.get("alphabet_size"),
                "parameters": _json_value(cipher.parameters, options=options),
            }
        )
    if solution is not None:
        out.setdefault("cipher_name", getattr(solution, "cipher_name", None))
    return _json_value(out, options=options)


def _key_summary(
    spec: RunSpec | None,
    solution: object | None,
    solver_report: SolverReport | None,
    *,
    options: SummaryOptions,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    key = getattr(spec, "key_space", None) if spec is not None else None
    if key is not None:
        if isinstance(key, tuple):
            out["requested_key_specs"] = [_key_spec_summary(item, options=options) for item in key]
        else:
            out["requested_key_spec"] = _key_spec_summary(key, options=options)
    if options.include_key:
        recovered = None
        if solver_report is not None and solver_report.best_key is not None:
            recovered = solver_report.best_key
        elif solution is not None:
            recovered = getattr(solution, "key", None)
        if recovered is not None:
            out["recovered_key"] = _preview_sequence(recovered, options.max_sequence_preview)
    return _json_value(out, options=options)


def _key_spec_summary(key_spec: object, *, options: SummaryOptions) -> dict[str, Any]:
    if isinstance(key_spec, KeySpec):
        return _json_value(key_spec.to_dict(), options=options)
    to_telemetry = getattr(key_spec, "to_telemetry", None)
    if callable(to_telemetry):
        try:
            return _json_value(to_telemetry(), options=options)
        except Exception as exc:
            return {"error": f"key spec telemetry failed: {exc.__class__.__name__}"}
    return _json_value({"plan": getattr(key_spec, "plan", None)}, options=options)


def _solver_summary(spec: RunSpec | None, solver_report: SolverReport | None, *, options: SummaryOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    solver = getattr(spec, "solver", None) if spec is not None else None
    if solver is not None:
        out.update({"name": solver.kind.value, "params": solver.parameters, "seed": solver.seed})
    if solver_report is not None:
        out.update(
            {
                "solver_name": solver_report.solver.value,
                "requested_seed": solver_report.requested_seed,
                "effective_seed": solver_report.effective_seed,
                "normalized_params": solver_report.parameters.effective,
            }
        )
    return _json_value(out, options=options)


def _scoring_summary(spec: RunSpec | None, *, options: SummaryOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if spec is not None:
        out["scorer"] = spec.scoring.backend.value
        out["scorer_params"] = _json_value(spec.scoring.to_dict(), options=options)
    if options.include_scope_notes:
        out["scope_note"] = (
            "v1 display shows API scorer params and ScorerReport when supplied; "
            "it does not exhaustively serialise every ScoringConfig field yet."
        )
    return _json_value(out, options=options)


def _result_summary(
    solution: object | None,
    *,
    reference_plaintext: str | None,
    reference_idx: Sequence[int] | None,
    options: SummaryOptions,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if solution is None:
        return out
    out.update(
        {
            "score": _finite_or_none(getattr(solution, "score", None)),
            "maximize": getattr(solution, "maximize", None),
            "step": getattr(getattr(solution, "solver_report", None), "steps", getattr(solution, "step", None)),
            "evals": getattr(getattr(solution, "solver_report", None), "evaluations", getattr(solution, "evals", None)),
            "tokens_processed": getattr(getattr(solution, "solver_report", None), "tokens_processed", getattr(solution, "tokens_processed", None)),
            "wall_time_s": _finite_or_none(getattr(getattr(solution, "solver_report", None), "wall_time_seconds", getattr(solution, "wall_time_s", None))),
            "decrypt_time_s": _finite_or_none(getattr(getattr(solution, "solver_report", None), "decrypt_time_seconds", getattr(solution, "decrypt_time_s", None))),
            "score_time_s": _finite_or_none(getattr(getattr(solution, "solver_report", None), "score_time_seconds", getattr(solution, "score_time_s", None))),
        }
    )
    if options.include_plaintext:
        out["plaintext"] = {
            "latin_preview": _preview_text(getattr(solution, "plaintext_latin", "") or "", options.plaintext_preview_chars),
            "rune_preview": _preview_text(getattr(solution, "plaintext_rune", "") or getattr(solution, "plaintext_text", None) or getattr(solution, "plaintext_str", "") or "", options.plaintext_preview_chars),
            "length": _safe_len(getattr(solution, "plaintext", None) if isinstance(solution, RunResult) else getattr(solution, "plaintext_idx", None)),
        }
    if options.include_ciphertext:
        out["ciphertext"] = {
            "latin_preview": _preview_text(getattr(solution, "ciphertext_latin", "") or "", options.ciphertext_preview_chars),
            "rune_preview": _preview_text(getattr(solution, "ciphertext_rune", "") or "", options.ciphertext_preview_chars),
            "length": _safe_len(getattr(solution, "ciphertext_idx", None)),
        }
    match = _reference_match(solution, reference_plaintext=reference_plaintext, reference_idx=reference_idx)
    if match:
        out.update(match)
    return _json_value(out, options=options)


def _solver_report_summary(solver_report: SolverReport | None, *, options: SummaryOptions) -> dict[str, Any] | None:
    if solver_report is None or not options.include_solver_report:
        return None
    return _json_value(solver_report.to_json_dict(), options=options)


def _scorer_report_summary(scorer_report: object | None, *, options: SummaryOptions) -> dict[str, Any] | None:
    if scorer_report is None or not options.include_scorer_report:
        return None
    to_json_dict = getattr(scorer_report, "to_json_dict", None)
    if callable(to_json_dict):
        return _json_value(to_json_dict(), options=options)
    if isinstance(scorer_report, Mapping):
        return _json_value(scorer_report, options=options)
    return {"unserialised_type": type(scorer_report).__name__}


def _telemetry_summary(solution: object | None, *, options: SummaryOptions) -> dict[str, Any]:
    if solution is None:
        return {}
    if isinstance(solution, RunResult):
        if not options.include_telemetry_summary:
            return {"available": bool(solution.telemetry)}
        return _json_value(solution.telemetry, options=options)
    meta = getattr(solution, "meta", None)
    if not isinstance(meta, Mapping):
        return {}
    if bool(meta.get("telemetry_off")):
        return {"telemetry_off": True}
    tel = meta.get("telemetry")
    if not isinstance(tel, Mapping) or not options.include_telemetry_summary:
        return {"available": isinstance(tel, Mapping)}
    out: dict[str, Any] = {"available": True, "keys": sorted(str(key) for key in tel.keys())}
    for key in ("run", "solver", "scorer", "pipeline", "encoding_dir", "seed", "wall_time_s"):
        if key in tel:
            out[key] = tel[key]
    return _json_value(out, options=options)


def _stop_summary(solution: object | None, solver_report: SolverReport | None) -> dict[str, Any]:
    # Prefer the canonical A4/June status when a SolverReport is available. The
    # Solution field remains a low-level compatibility reason and can differ for
    # routes such as explicit known-key execution.
    if solver_report is not None:
        return _json_value(solver_report.status.to_json_dict(), options=SummaryOptions.standard())
    if solution is not None:
        try:
            return _json_value(stop_reason_details_from_solution(solution), options=SummaryOptions.standard())
        except Exception:
            pass
    reason = None
    category = stop_category_for_reason(reason)
    return {
        StopReasonDetailKey.STOP_CATEGORY.value: category.value,
        StopReasonDetailKey.STOP_REASON.value: reason,
        StopReasonDetailKey.STOP_DETAIL.value: reason,
        StopReasonDetailKey.BLOCKED_BEFORE_RUN.value: category.value == "blocked_before_run",
        StopReasonDetailKey.ERROR_TYPE.value: None,
    }


def _oracle_summary(
    solution: object | None, solver_report: SolverReport | None
) -> dict[str, Any]:
    if isinstance(solution, RunResult):
        return solution.oracle.to_json_dict()
    if solver_report is None:
        return {}
    details = solver_report.details
    oracle = details.get("oracle") if isinstance(details, Mapping) else None
    return dict(oracle) if isinstance(oracle, Mapping) else {}


def _tutorial_summary(entry: Mapping[str, Any] | None, *, options: SummaryOptions) -> dict[str, Any] | None:
    if entry is None:
        return None
    keep = (
        "path",
        "title",
        "cipher_family",
        "tutorial_kind",
        "gate",
        "required_asset_profile",
        "acceptance_kind",
        "min_match_ratio",
        "uses_oracle_stop_score",
        "supplies_true_key_to_solver",
        "current_status",
    )
    return _json_value({key: entry.get(key) for key in keep if key in entry}, options=options)


def _artifact_summary(
    artifacts: Mapping[str, Any] | None,
    *,
    artifact_manifest_path: str | Path | None,
    options: SummaryOptions,
) -> dict[str, Any]:
    out = dict(artifacts or {})
    out.setdefault("display_summary_relpath", SUMMARY_RELATIVE_PATH)
    if artifact_manifest_path is not None:
        out["artifact_manifest_path"] = artifact_manifest_path
    return _json_value(_redact_artifact_paths(out), options=options)


def _redact_artifact_paths(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _redact_artifact_paths(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_artifact_paths(item) for item in value]
    if isinstance(value, Path):
        return _safe_display_path(value)
    if isinstance(value, str) and _looks_like_path(value):
        return _safe_display_path(value)
    return value


def _safe_display_path(value: Path | str) -> str:
    raw = value.as_posix() if isinstance(value, Path) else str(value).replace("\\", "/")
    if not _looks_like_absolute_path(raw):
        return raw
    parts = tuple(part for part in PurePosixPath(raw).parts if part not in ("/", ""))
    if not parts:
        return "."
    for index, part in enumerate(parts):
        if part in _OPSEC_PATH_PARENT_NAMES and index + 1 < len(parts):
            return PurePosixPath(*parts[index:]).as_posix()
    return parts[-1]


def _looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value or bool(_WINDOWS_ABSOLUTE_RE.match(value))


def _looks_like_absolute_path(value: str) -> bool:
    return value.startswith("/") or bool(_WINDOWS_ABSOLUTE_RE.match(value))


def _optional_mapping(value: Mapping[str, Any] | None, field_name: str, *, options: SummaryOptions) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping or None")
    return _json_value(value, options=options)


def _policy_warnings(
    *,
    stop: Mapping[str, Any],
    oracle: Mapping[str, Any],
    tutorial: Mapping[str, Any] | None,
    telemetry: Mapping[str, Any],
) -> list[str]:
    warnings: list[str] = []
    category = stop.get(StopReasonDetailKey.STOP_CATEGORY.value)
    if category in {"budget", "blocked_before_run", "error", "manual", "not_started"}:
        warnings.append(f"stop category is {category}")
    oracle_use = oracle.get("oracle_use")
    if oracle_use and oracle_use != "none":
        warnings.append(f"truth/oracle data use is reported as {oracle_use}")
    if tutorial is not None and tutorial.get("acceptance_kind") == _PARTIAL_RECOVERY_ACCEPTANCE:
        warnings.append("tutorial accepts a partial-recovery threshold; exact recovery is not required")
    if telemetry.get("telemetry_off") is True:
        warnings.append("telemetry was explicitly disabled")
    return warnings


def _reference_match(
    solution: object,
    *,
    reference_plaintext: str | None,
    reference_idx: Sequence[int] | None,
) -> dict[str, Any]:
    if reference_idx is not None:
        candidate = _as_int_list(
            getattr(solution, "plaintext", None)
            if isinstance(solution, RunResult)
            else getattr(solution, "plaintext_idx", None)
        )
        reference = _as_int_list(reference_idx)
        if candidate is not None and reference is not None:
            return {"match_ratio": _match_ratio(candidate, reference), "reference_kind": "plaintext_idx"}
    if reference_plaintext is not None:
        candidate_text = str(
            getattr(solution, "plaintext_latin", "")
            or getattr(solution, "plaintext_text", "")
            or getattr(solution, "plaintext_str", "")
            or ""
        )
        candidate_norm = _normalise_plaintext_for_match(candidate_text)
        reference_norm = _normalise_plaintext_for_match(reference_plaintext)
        if candidate_norm or reference_norm:
            return {"match_ratio": _text_match_ratio(candidate_norm, reference_norm), "reference_kind": "plaintext_text"}
    return {}


def _match_ratio(candidate: Sequence[int], reference: Sequence[int]) -> float:
    total = max(len(candidate), len(reference))
    if total <= 0:
        return 1.0
    matches = sum(1 for left, right in zip(candidate, reference) if int(left) == int(right))
    return float(matches / total)


def _text_match_ratio(candidate: str, reference: str) -> float:
    total = max(len(candidate), len(reference))
    if total <= 0:
        return 1.0
    matches = sum(1 for left, right in zip(candidate, reference) if left == right)
    return float(matches / total)


def _normalise_plaintext_for_match(value: str) -> str:
    return re.sub(r"[^A-Za-z]", "", value).upper()


def _preview_text(value: object, limit: int) -> str:
    text = str(value or "")
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + "..."


def _preview_sequence(values: object, limit: int) -> dict[str, Any]:
    seq = _as_sequence(values)
    if seq is None:
        return {"length": None, "preview": None, "truncated": False}
    preview = [_json_value(item, options=SummaryOptions.standard()) for item in seq[:limit]]
    return {"length": len(seq), "preview": preview, "truncated": len(seq) > limit}


def _as_sequence(values: object) -> list[Any] | None:
    if values is None or isinstance(values, (str, bytes, Path, Mapping)):
        return None
    if hasattr(values, "tolist"):
        try:
            values = values.tolist()
        except Exception:
            return None
    if not isinstance(values, Sequence):
        return None
    return list(values)


def _as_int_list(values: object) -> list[int] | None:
    seq = _as_sequence(values)
    if seq is None:
        return None
    try:
        return [int(item) for item in seq]
    except Exception:
        return None


def _safe_len(values: object) -> int | None:
    seq = _as_sequence(values)
    return len(seq) if seq is not None else None


def _finite_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except Exception:
        return None
    if not math.isfinite(out):
        return None
    return out


def _json_value(value: object, *, options: SummaryOptions) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return _safe_display_path(value)
    if hasattr(value, "item"):
        try:
            return _json_value(value.item(), options=options)
        except Exception:
            pass
    if isinstance(value, Mapping):
        return {str(k): _json_value(v, options=options) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item, options=options) for item in value]
    if hasattr(value, "to_json_dict"):
        return _json_value(value.to_json_dict(), options=options)
    return str(value)


def _copy_json_mapping(value: object, field_name: str) -> dict[str, Any]:
    if isinstance(value, Path) or not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    return {str(key): _copy_json_value(item, f"{field_name}.{key}") for key, item in value.items()}


def _copy_json_value(value: object, field_name: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{field_name} float values must be finite")
        return float(value)
    if isinstance(value, Mapping):
        return _copy_json_mapping(value, field_name)
    if isinstance(value, (list, tuple)):
        return tuple(_copy_json_value(item, f"{field_name}[]") for item in value)
    raise TypeError(f"{field_name} must be JSON-compatible")


def _to_json_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _to_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_to_json_value(item) for item in value]
    if isinstance(value, list):
        return [_to_json_value(item) for item in value]
    return value


def _require_text(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _require_bool(value: object, field_name: str) -> None:
    if type(value) is not bool:
        raise TypeError(f"{field_name} must be a bool")


def _require_nonnegative_int(value: object, field_name: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{field_name} must be an int")
    if value < 0:
        raise ValueError(f"{field_name} must be >= 0")


def _enum_value(value: object) -> object:
    return value.value if isinstance(value, Enum) else value


def _append_kv(lines: list[str], key: str, value: object) -> None:
    if value is not None and value != {} and value != []:
        lines.append(f"{key}: {value}")


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


class PrintFormat(StrEnum):
    TEXT = "text"
    JSON = "json"


class PrintDetail(StrEnum):
    COMPACT = "compact"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


class BannerStyle(StrEnum):
    PLAIN = "plain"
    BOX = "box"


@dataclass(frozen=True, slots=True)
class PrintOptions:
    """Controls shared human console presentation."""

    detail: PrintDetail | str = PrintDetail.DETAILED
    width: int = 72
    output_root: str = "output/"
    banner_style: BannerStyle | str = BannerStyle.PLAIN

    def __post_init__(self) -> None:
        object.__setattr__(self, "detail", _print_ensure_detail(self.detail))
        object.__setattr__(self, "banner_style", _print_ensure_banner_style(self.banner_style))
        _print_require_positive_int(self.width, "width")
        object.__setattr__(self, "output_root", _print_safe_display_path(self.output_root, field_name="output_root"))

    @classmethod
    def compact(cls) -> "PrintOptions":
        return cls(detail=PrintDetail.COMPACT)

    @classmethod
    def standard(cls) -> "PrintOptions":
        return cls(detail=PrintDetail.STANDARD)

    @classmethod
    def detailed(cls) -> "PrintOptions":
        return cls(detail=PrintDetail.DETAILED)

    @classmethod
    def debug(cls) -> "PrintOptions":
        return cls(detail=PrintDetail.DEBUG, width=88)


def render_summary(
    summary: DisplaySummary | object,
    *,
    output_format: PrintFormat | str = PrintFormat.TEXT,
    **build_kwargs: Any,
) -> str:
    """Render a standard RDP summary as text or JSON.

    ``summary`` may already be an ``DisplaySummary`` or may be any value
    accepted by ``build_summary``. Build keyword arguments are forwarded only
    when a summary must be built.
    """

    fmt = _print_ensure_format(output_format)
    if not isinstance(summary, DisplaySummary):
        summary = build_summary(summary, **build_kwargs)

    if fmt is PrintFormat.TEXT:
        return format_summary(summary)
    if fmt is PrintFormat.JSON:
        return json.dumps(summary.to_json_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    raise AssertionError(f"unhandled print format: {fmt}")


def print_result(
    value: object,
    *,
    file: TextIO | None = None,
    output_format: PrintFormat | str = PrintFormat.TEXT,
    options: SummaryOptions | None = None,
    **build_kwargs: Any,
) -> DisplaySummary:
    """Build, print, and return the standard RDP display summary."""

    summary = build_summary(value, options=options, **build_kwargs)
    rendered = render_summary(summary, output_format=output_format)
    if file is None:
        import sys

        file = sys.stdout
    file.write(rendered)
    return summary


def write_summary_artifact(
    summary: DisplaySummary | object,
    *,
    run_dir: Path,
    options: SummaryOptions | None = None,
    **build_kwargs: Any,
) -> str:
    """Write ``artifacts/rdp_display_summary.json`` under ``run_dir``.

    The returned value is always the standard run-relative sidecar path, never an
    absolute local path.
    """

    if not isinstance(run_dir, Path):
        raise TypeError("run_dir must be a Path")
    if isinstance(summary, DisplaySummary):
        built = summary
    else:
        built = build_summary(summary, options=options, **build_kwargs)
    relpath = write_summary_json(built, run_dir / SUMMARY_RELATIVE_PATH)
    if relpath != SUMMARY_RELATIVE_PATH:
        # Keep the public contract fixed even if the internal path was absolute.
        return SUMMARY_RELATIVE_PATH
    return relpath


def format_banner(
    *,
    title: str = "Rune Decrypter Prime",
    version_label: str = "RDP V1 pre-release",
    output_root: str | Path | None = None,
    options: PrintOptions | None = None,
) -> str:
    """Return the standard restrained RDP console banner."""
    opts = _print_ensure_options(options)
    root = opts.output_root if output_root is None else _print_safe_display_path(output_root, field_name="output_root")
    lines = [
        _print_require_text(title, "title"),
        "=" * len(title),
        _print_require_text(version_label, "version_label"),
        f"output root : {root}",
    ]
    if opts.banner_style is BannerStyle.PLAIN:
        return "\n".join(lines) + "\n"

    inner_width = max(max(len(line) for line in lines), 42)
    out = ["+" + "-" * (inner_width + 2) + "+"]
    out.extend(f"| {line.ljust(inner_width)} |" for line in lines)
    out.append("+" + "-" * (inner_width + 2) + "+")
    return "\n".join(out) + "\n"


def format_section(title: str, *, underline: str = "-") -> str:
    """Return a simple deterministic section heading."""
    title_text = _print_require_text(title, "title")
    underline_text = _print_require_text(underline, "underline")
    marker = underline_text[0]
    return f"{title_text}\n{marker * len(title_text)}\n"


def format_key_value_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> str:
    """Return a deterministic key/value section for human console output."""
    _print_ensure_options(options)
    items = _print_normalise_rows(rows)
    key_width = max((len(key) for key, _ in items), default=0)
    lines = [format_section(title).rstrip()]
    for key, value in items:
        rendered = _print_display_value(value)
        value_lines = rendered.splitlines() or [""]
        lines.append(f"{key.ljust(key_width)} : {value_lines[0]}")
        indent = " " * (key_width + 3)
        lines.extend(f"{indent}{line}" for line in value_lines[1:])
    return "\n".join(lines) + "\n"


def format_preview_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> str:
    """Return a preview section using the standard key/value style."""
    return format_key_value_block(title, rows, options=options)


def format_status_block(
    title: str,
    rows: Mapping[str, Any] | Sequence[tuple[str, Any]],
    *,
    options: PrintOptions | None = None,
) -> str:
    """Return a status section using the standard key/value style."""
    return format_key_value_block(title, rows, options=options)


def print_text(text: str, *, file: TextIO | None = None) -> None:
    """Write human console text to ``file`` or stdout."""
    if file is None:
        import sys

        file = sys.stdout
    file.write(str(text))
    if text and not str(text).endswith("\n"):
        file.write("\n")


def print_block(text: str, *, file: TextIO | None = None) -> None:
    """Write a complete console block followed by one blank line."""
    if file is None:
        import sys

        file = sys.stdout
    file.write(str(text).rstrip() + "\n\n")


def _print_normalise_rows(rows: Mapping[str, Any] | Sequence[tuple[str, Any]]) -> list[tuple[str, Any]]:
    if isinstance(rows, Mapping):
        iterable = list(rows.items())
    elif isinstance(rows, Sequence) and not isinstance(rows, (str, bytes)):
        iterable = list(rows)
    else:
        raise TypeError("rows must be a mapping or sequence of key/value pairs")

    out: list[tuple[str, Any]] = []
    for index, item in enumerate(iterable):
        if not isinstance(item, tuple) or len(item) != 2:
            raise TypeError(f"rows[{index}] must be a two-item tuple")
        key, value = item
        out.append((_print_require_text(str(key), f"rows[{index}].key"), value))
    return out


def _print_display_value(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, Path):
        return _print_safe_display_path(value, field_name="value")
    if isinstance(value, float):
        return f"{value:.6f}" if value == value and abs(value) < 1e9 else str(value)
    return str(value)


def _print_safe_display_path(value: str | Path, *, field_name: str) -> str:
    if isinstance(value, Path):
        if value.is_absolute():
            raise ValueError(f"{field_name} must be display-safe and repo-relative")
        text = value.as_posix()
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field_name} must not be empty")
        path = Path(text)
        if path.is_absolute() or _print_looks_windows_absolute(text):
            raise ValueError(f"{field_name} must be display-safe and repo-relative")
        text = text.replace("\\", "/")
    else:
        raise TypeError(f"{field_name} must be a string or Path")
    return text


def _print_looks_windows_absolute(value: str) -> bool:
    return len(value) >= 3 and value[1] == ":" and value[2] in {"/", "\\"} and value[0].isalpha()


def _print_ensure_format(value: PrintFormat | str) -> PrintFormat:
    if isinstance(value, PrintFormat):
        return value
    try:
        return PrintFormat(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in PrintFormat)
        raise ValueError(f"output_format must be one of {allowed}") from exc


def _print_ensure_detail(value: PrintDetail | str) -> PrintDetail:
    if isinstance(value, PrintDetail):
        return value
    try:
        return PrintDetail(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in PrintDetail)
        raise ValueError(f"detail must be one of {allowed}") from exc


def _print_ensure_banner_style(value: BannerStyle | str) -> BannerStyle:
    if isinstance(value, BannerStyle):
        return value
    try:
        return BannerStyle(str(value))
    except ValueError as exc:
        allowed = sorted(item.value for item in BannerStyle)
        raise ValueError(f"banner_style must be one of {allowed}") from exc


def _print_ensure_options(value: PrintOptions | None) -> PrintOptions:
    if value is None:
        return PrintOptions.detailed()
    if not isinstance(value, PrintOptions):
        raise TypeError("options must be PrintOptions or None")
    return value


def _print_require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value:
        raise ValueError(f"{field_name} must not be empty")
    return value


def _print_require_positive_int(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field_name} must be an integer")
    if value <= 0:
        raise ValueError(f"{field_name} must be > 0")


__all__ = [
    "SUMMARY_RELATIVE_PATH",
    "SUMMARY_SCHEMA",
    "SummaryOptions",
    "DisplaySummary",
    "BannerStyle",
    "PrintDetail",
    "PrintFormat",
    "PrintOptions",
    "build_summary",
    "format_summary",
    "print_summary",
    "render_summary",
    "print_result",
    "write_summary_json",
    "write_summary_artifact",
    "format_banner",
    "format_key_value_block",
    "format_preview_block",
    "format_section",
    "format_status_block",
    "print_block",
    "print_text",
]
