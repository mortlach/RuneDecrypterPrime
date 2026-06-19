from __future__ import annotations

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

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, TextIO

from rune_decrypter_prime.api.artifact_agreement import KnownArtifactRelpath
from rune_decrypter_prime.api.run_result import RunResult
from rune_decrypter_prime.api.run_spec import NormalizedInput, RawTextInput, RunSpec, SourceInputRef
from rune_decrypter_prime.api.solver_report import SolverReport, SolverReportDetailKey
from rune_decrypter_prime.api.stop_reason_contract import (
    StopReasonDetailKey,
    stop_category_for_reason,
    stop_reason_details_from_solution,
)

DISPLAY_SUMMARY_SCHEMA = "api_display_summary.v1"
DISPLAY_SUMMARY_RELPATH = KnownArtifactRelpath.RDP_DISPLAY_SUMMARY.value
_OPSEC_PATH_PARENT_NAMES = frozenset({"artifacts", "config", "logs", "trace", "traces", "output"})
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True, slots=True)
class RdpDisplayOptions:
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
    allow_absolute_paths: bool = False

    def __post_init__(self) -> None:
        _require_text(self.mode, "mode")
        _require_bool(self.include_plaintext, "include_plaintext")
        _require_bool(self.include_ciphertext, "include_ciphertext")
        _require_bool(self.include_key, "include_key")
        _require_bool(self.include_solver_report, "include_solver_report")
        _require_bool(self.include_scorer_report, "include_scorer_report")
        _require_bool(self.include_telemetry_summary, "include_telemetry_summary")
        _require_bool(self.include_scope_notes, "include_scope_notes")
        _require_bool(self.allow_absolute_paths, "allow_absolute_paths")
        _require_nonnegative_int(self.plaintext_preview_chars, "plaintext_preview_chars")
        _require_nonnegative_int(self.ciphertext_preview_chars, "ciphertext_preview_chars")
        _require_nonnegative_int(self.max_sequence_preview, "max_sequence_preview")

    @classmethod
    def standard(cls) -> "RdpDisplayOptions":
        return cls(mode="standard")

    @classmethod
    def for_console(cls) -> "RdpDisplayOptions":
        return cls(mode="console", plaintext_preview_chars=500, ciphertext_preview_chars=180)

    @classmethod
    def for_tutorial(cls) -> "RdpDisplayOptions":
        return cls(mode="tutorial", plaintext_preview_chars=700, ciphertext_preview_chars=200)

    @classmethod
    def for_lp_evidence(cls) -> "RdpDisplayOptions":
        return cls(mode="lp_evidence", plaintext_preview_chars=2000, ciphertext_preview_chars=320)

    @classmethod
    def for_debug(cls) -> "RdpDisplayOptions":
        return cls(mode="debug", plaintext_preview_chars=2000, ciphertext_preview_chars=800, max_sequence_preview=120)


@dataclass(frozen=True, slots=True)
class RdpDisplaySummary:
    """JSON-safe, shareable standard display view of an RDP run."""

    schema: str = DISPLAY_SUMMARY_SCHEMA
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


def build_rdp_summary(
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
    options: RdpDisplayOptions | None = None,
) -> RdpDisplaySummary:
    """Build the standard display/share summary from an RDP result or solution.

    ``value`` may be an API ``RunResult`` or a solution-like object. Pass
    ``spec`` when available; without it, the summary deliberately reports a
    warning because the result object does not contain all original config.
    """

    options = options or RdpDisplayOptions.standard()
    if not isinstance(options, RdpDisplayOptions):
        raise TypeError("options must be RdpDisplayOptions or None")
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
    oracle = _oracle_summary(solver_report)
    tutorial = _tutorial_summary(tutorial_entry, options=options)
    lp = _optional_mapping(lp_evidence, "lp_evidence", options=options)
    artifact_summary = _artifact_summary(
        artifacts,
        artifact_manifest_path=artifact_manifest_path,
        options=options,
    )

    warnings.extend(_policy_warnings(stop=stop, oracle=oracle, tutorial=tutorial, telemetry=telemetry))

    return RdpDisplaySummary(
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


def format_rdp_summary(summary: RdpDisplaySummary | object, **build_kwargs: Any) -> str:
    """Return a compact human-readable rendering of the standard summary."""

    if not isinstance(summary, RdpDisplaySummary):
        summary = build_rdp_summary(summary, **build_kwargs)

    data = summary.to_json_dict()
    lines: list[str] = ["RDP standard summary", "===================="]

    result = data.get("result") or {}
    solver = data.get("solver") or {}
    cipher = data.get("cipher") or {}
    stop = data.get("stop") or {}
    oracle = data.get("oracle") or {}
    artifacts = data.get("artifacts") or {}

    _append_kv(lines, "schema", data.get("schema"))
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


def print_rdp_summary(
    summary: RdpDisplaySummary | object,
    *,
    file: TextIO | None = None,
    **build_kwargs: Any,
) -> None:
    """Print a compact RDP display summary to stdout or a supplied file."""

    import sys

    target = sys.stdout if file is None else file
    target.write(format_rdp_summary(summary, **build_kwargs))


def write_rdp_summary_json(summary: RdpDisplaySummary, path: Path | str = DISPLAY_SUMMARY_RELPATH) -> str:
    """Write a display summary JSON file and return a display-safe POSIX path."""

    if not isinstance(summary, RdpDisplaySummary):
        raise TypeError("summary must be RdpDisplaySummary")
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
        return value.solution
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


def _problem_summary(spec: RunSpec | None, solution: object | None, *, options: RdpDisplayOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if spec is not None:
        inp = spec.problem_input
        if isinstance(inp, RawTextInput):
            out.update({"input_kind": "raw_text", "text_length": len(inp.text), "text_preview": _preview_text(inp.text, 160)})
        elif isinstance(inp, NormalizedInput):
            out.update(
                {
                    "input_kind": "normalized",
                    "ciphertext_length": len(inp.ct_idx),
                    "has_wli": inp.wli is not None,
                    "wli_length": len(inp.wli) if inp.wli is not None else None,
                }
            )
        elif isinstance(inp, SourceInputRef):
            out.update(
                {
                    "input_kind": "source_ref",
                    "source_kind": inp.source_kind,
                    "asset_id": inp.asset_id,
                    "asset_version": inp.asset_version,
                    "ref": _json_value(inp.ref, options=options),
                }
            )
        out["encoding_dir"] = _enum_value(spec.encoding_dir)
        out["device"] = _enum_value(spec.device)
        out["telemetry_on"] = bool(spec.telemetry_on)
    if solution is not None:
        ct_idx = _as_sequence(getattr(solution, "ciphertext_idx", None))
        pt_idx = _as_sequence(getattr(solution, "plaintext_idx", None))
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


def _cipher_summary(spec: RunSpec | None, solution: object | None, *, options: RdpDisplayOptions) -> dict[str, Any]:
    cipher = getattr(spec, "cipher", None) if spec is not None else None
    out: dict[str, Any] = {}
    if cipher is not None:
        out.update(
            {
                "name": getattr(cipher, "name", None),
                "kind": getattr(cipher, "kind", None),
                "alphabet_size": getattr(cipher, "N", None),
                "wrapper_core": getattr(cipher, "wrapper_core", None),
                "degeneracy": getattr(cipher, "degeneracy", None),
                "resolver": getattr(cipher, "resolver", None),
                "per_pos_limit": getattr(cipher, "per_pos_limit", None),
                "resolver_limit": getattr(cipher, "resolver_limit", None),
                "has_function": getattr(cipher, "function", None) is not None,
                "has_table": getattr(cipher, "table", None) is not None,
                "extra": _json_value(getattr(cipher, "extra", {}) or {}, options=options),
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
    options: RdpDisplayOptions,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    key = getattr(spec, "key", None) if spec is not None else None
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


def _key_spec_summary(key_spec: object, *, options: RdpDisplayOptions) -> dict[str, Any]:
    to_telemetry = getattr(key_spec, "to_telemetry", None)
    if callable(to_telemetry):
        try:
            return _json_value(to_telemetry(), options=options)
        except Exception as exc:
            return {"error": f"key spec telemetry failed: {exc.__class__.__name__}"}
    return _json_value({"plan": getattr(key_spec, "plan", None)}, options=options)


def _solver_summary(spec: RunSpec | None, solver_report: SolverReport | None, *, options: RdpDisplayOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    solver = getattr(spec, "solver", None) if spec is not None else None
    if solver is not None:
        out.update({"name": getattr(solver, "name", None), "params": getattr(solver, "params", None), "seed": getattr(solver, "seed", None)})
    if solver_report is not None:
        out.update(
            {
                "solver_name": solver_report.solver_name,
                "requested_seed": solver_report.requested_seed,
                "effective_seed": solver_report.effective_seed,
                "normalized_params": solver_report.normalized_params,
            }
        )
    return _json_value(out, options=options)


def _scoring_summary(spec: RunSpec | None, *, options: RdpDisplayOptions) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if spec is not None:
        out["scorer"] = spec.scorer
        out["scorer_params"] = _json_value(spec.scorer_params, options=options)
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
    options: RdpDisplayOptions,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if solution is None:
        return out
    out.update(
        {
            "score": _finite_or_none(getattr(solution, "score", None)),
            "maximize": getattr(solution, "maximize", None),
            "step": getattr(solution, "step", None),
            "evals": getattr(solution, "evals", None),
            "tokens_processed": getattr(solution, "tokens_processed", None),
            "wall_time_s": _finite_or_none(getattr(solution, "wall_time_s", None)),
            "decrypt_time_s": _finite_or_none(getattr(solution, "decrypt_time_s", None)),
            "score_time_s": _finite_or_none(getattr(solution, "score_time_s", None)),
        }
    )
    if options.include_plaintext:
        out["plaintext"] = {
            "latin_preview": _preview_text(getattr(solution, "plaintext_latin", "") or "", options.plaintext_preview_chars),
            "rune_preview": _preview_text(getattr(solution, "plaintext_rune", "") or getattr(solution, "plaintext_str", "") or "", options.plaintext_preview_chars),
            "length": _safe_len(getattr(solution, "plaintext_idx", None)),
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


def _solver_report_summary(solver_report: SolverReport | None, *, options: RdpDisplayOptions) -> dict[str, Any] | None:
    if solver_report is None or not options.include_solver_report:
        return None
    return _json_value(solver_report.to_json_dict(), options=options)


def _scorer_report_summary(scorer_report: object | None, *, options: RdpDisplayOptions) -> dict[str, Any] | None:
    if scorer_report is None or not options.include_scorer_report:
        return None
    to_json_dict = getattr(scorer_report, "to_json_dict", None)
    if callable(to_json_dict):
        return _json_value(to_json_dict(), options=options)
    if isinstance(scorer_report, Mapping):
        return _json_value(scorer_report, options=options)
    return {"unserialised_type": type(scorer_report).__name__}


def _telemetry_summary(solution: object | None, *, options: RdpDisplayOptions) -> dict[str, Any]:
    if solution is None:
        return {}
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
    if solution is not None:
        try:
            return _json_value(stop_reason_details_from_solution(solution), options=RdpDisplayOptions.standard())
        except Exception:
            pass
    reason = solver_report.stop_reason if solver_report is not None else None
    category = stop_category_for_reason(reason)
    return {
        StopReasonDetailKey.STOP_CATEGORY.value: category.value,
        StopReasonDetailKey.STOP_REASON.value: reason,
        StopReasonDetailKey.STOP_DETAIL.value: reason,
        StopReasonDetailKey.BLOCKED_BEFORE_RUN.value: category.value == "blocked_before_run",
        StopReasonDetailKey.ERROR_TYPE.value: None,
    }


def _oracle_summary(solver_report: SolverReport | None) -> dict[str, Any]:
    details = solver_report.details if solver_report is not None else {}
    if not isinstance(details, Mapping):
        details = {}
    return {
        "oracle_use": details.get(SolverReportDetailKey.ORACLE_USE.value),
        "truth_data_policy": details.get(SolverReportDetailKey.TRUTH_DATA_POLICY.value),
        "execution_route": details.get(SolverReportDetailKey.EXECUTION_ROUTE.value),
    }


def _tutorial_summary(entry: Mapping[str, Any] | None, *, options: RdpDisplayOptions) -> dict[str, Any] | None:
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
    options: RdpDisplayOptions,
) -> dict[str, Any]:
    out = dict(artifacts or {})
    out.setdefault("display_summary_relpath", DISPLAY_SUMMARY_RELPATH)
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


def _optional_mapping(value: Mapping[str, Any] | None, field_name: str, *, options: RdpDisplayOptions) -> dict[str, Any] | None:
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
    if tutorial is not None and tutorial.get("acceptance_kind") == "near_solve_min_match":
        warnings.append("tutorial accepts a near-solve threshold; exact recovery is not required")
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
        candidate = _as_int_list(getattr(solution, "plaintext_idx", None))
        reference = _as_int_list(reference_idx)
        if candidate is not None and reference is not None:
            return {"match_ratio": _match_ratio(candidate, reference), "reference_kind": "plaintext_idx"}
    if reference_plaintext is not None:
        candidate_text = str(getattr(solution, "plaintext_latin", "") or getattr(solution, "plaintext_str", "") or "")
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
    preview = [_json_value(item, options=RdpDisplayOptions.standard()) for item in seq[:limit]]
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


def _json_value(value: object, *, options: RdpDisplayOptions) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return float(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        if value.is_absolute() and not options.allow_absolute_paths:
            return _safe_display_path(value)
        return value.as_posix()
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


__all__ = [
    "DISPLAY_SUMMARY_RELPATH",
    "DISPLAY_SUMMARY_SCHEMA",
    "RdpDisplayOptions",
    "RdpDisplaySummary",
    "build_rdp_summary",
    "format_rdp_summary",
    "print_rdp_summary",
    "write_rdp_summary_json",
]
