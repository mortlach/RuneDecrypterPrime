from __future__ import annotations
import rdp.api.stop_reason_contract
from rdp import api
import hashlib
import json
import math
import os
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any
from rune_decrypter_prime.core.config.logging_config import init_logging
from rune_decrypter_prime.io.artifact_policy import portable_exception_message
from cipher_development.shared.ledger import SCHEMA as LEDGER_SCHEMA
from cipher_development.shared.ledger import ExperimentLedgerRow, append_ledger_row
MANIFEST_SCHEMA = 'rdp_cipher_development_experiment_manifest.v1'
SNAPSHOT_SCHEMA = 'rdp_cipher_development_progress_snapshot.v1'
RESULT_SCHEMA = 'rdp_cipher_development_experiment_result.v1'
_ID_RE = re.compile('^[a-z0-9][a-z0-9_-]*$')
_LESSON_ID_RE = re.compile('^CSL-[0-9]{3}$')
_REFERENCE_KEYS = {'expected_key', 'expected_plaintext', 'ground_truth', 'known_key', 'known_plaintext', 'match_ratio', 'oracle', 'oracle_key', 'reference', 'reference_evaluation', 'reference_metrics', 'test_key', 'truth', 'truth_key', 'truth_metrics'}
_REFERENCE_PREFIXES = ('oracle_', 'reference_', 'truth_')
_COUNTERS = ('eval_keys', 'eval_batches', 'candidates_evaluated', 'tokens_processed', 'decrypt_time_s', 'score_time_s')
_ACTIVE_RUN: ExperimentRun | None = None

class WliMode(StrEnum):
    WITH_WLI = 'with_wli'
    WITHOUT_WLI = 'without_wli'

class TruthPolicy(StrEnum):
    BENCHMARK_ONLY = 'benchmark_only'
    NONE = 'none'

class FailureMechanism(StrEnum):
    CONTRACT = 'contract'
    OBJECTIVE = 'objective'
    CANDIDATE_SUPPLY = 'candidate_supply'
    DIVERSITY_COLLAPSE = 'diversity_collapse'
    RANKING = 'ranking'
    HANDOFF = 'handoff'
    EXPLOITATION = 'exploitation'
    ACCEPTANCE = 'acceptance'
    BUDGET = 'budget'
    EVIDENCE_REPRODUCIBILITY = 'evidence_reproducibility'

class ExperimentDecision(StrEnum):
    PROMOTE = 'promote'
    REFINE = 'refine'
    CLOSE = 'close'

def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be a non-empty string')
    return value.strip()

def _identifier(value: Any, name: str) -> str:
    value = _text(value, name)
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} must use lowercase letters, numbers, '_' or '-'")
    return value

def _enum(value: Any, enum_type: type[StrEnum], name: str) -> StrEnum:
    if isinstance(value, enum_type):
        return value
    try:
        return enum_type(str(value))
    except ValueError as exc:
        raise ValueError(f"{name} must be one of: {', '.join((x.value for x in enum_type))}") from exc

def _json_value(value: Any, name: str) -> Any:
    if isinstance(value, Path):
        raise TypeError(f'{name} must not contain Path values')
    if isinstance(value, Enum):
        return _json_value(value.value, name)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f'{name} contains a non-finite float')
        return float(value)
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise TypeError(f'{name} mapping keys must be non-empty strings')
            out[key] = _json_value(item, f'{name}.{key}')
        return out
    if isinstance(value, (list, tuple)):
        return [_json_value(item, f'{name}[]') for item in value]
    if isinstance(value, set):
        raise TypeError(f'{name} must not contain sets')
    if callable(value):
        raise TypeError(f'{name} must not contain callables')
    raise TypeError(f'{name} contains unsupported value type {type(value).__name__}')

def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f'{name} must be a mapping')
    return _json_value(value, name)

def _optional_mapping(value: Any, name: str) -> dict[str, Any]:
    return {} if value is None else _mapping(value, name)

def _reject_reference_fields(value: Any, name: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            token = str(key).strip().lower()
            if token in _REFERENCE_KEYS or token.startswith(_REFERENCE_PREFIXES):
                raise ValueError(f'{name} must not contain reference or truth field {key!r}')
            _reject_reference_fields(item, name)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_reference_fields(item, name)

def _canonical_json(configuration: Mapping[str, Any]) -> str:
    payload = _mapping(configuration, 'configuration')
    _reject_reference_fields(payload, 'configuration')
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    campaign_id: str
    experiment_id: str
    benchmark_id: str
    question: str
    hypothesis: str
    alternative: str
    decision_rule: str
    wli_mode: WliMode = WliMode.WITH_WLI
    truth_policy: TruthPolicy = TruthPolicy.BENCHMARK_ONLY
    mechanisms: tuple[FailureMechanism, ...] = ()
    budget_seconds: float | None = None
    budget_evaluations: int | None = None
    lesson_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ('campaign_id', 'experiment_id', 'benchmark_id'):
            object.__setattr__(self, name, _identifier(getattr(self, name), name))
        for name in ('question', 'hypothesis', 'alternative', 'decision_rule'):
            object.__setattr__(self, name, _text(getattr(self, name), name))
        object.__setattr__(self, 'wli_mode', _enum(self.wli_mode, WliMode, 'wli_mode'))
        object.__setattr__(self, 'truth_policy', _enum(self.truth_policy, TruthPolicy, 'truth_policy'))
        mechanisms = tuple((_enum(x, FailureMechanism, 'mechanisms[]') for x in self.mechanisms))
        if len(set(mechanisms)) != len(mechanisms):
            raise ValueError('mechanisms must be unique')
        object.__setattr__(self, 'mechanisms', mechanisms)
        if self.budget_seconds is not None:
            if isinstance(self.budget_seconds, bool):
                raise TypeError('budget_seconds must be a positive finite float or None')
            value = float(self.budget_seconds)
            if not math.isfinite(value) or value <= 0:
                raise ValueError('budget_seconds must be a positive finite float or None')
            object.__setattr__(self, 'budget_seconds', value)
        if self.budget_evaluations is not None:
            value = self.budget_evaluations
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError('budget_evaluations must be a positive integer or None')
            if value <= 0:
                raise ValueError('budget_evaluations must be a positive integer or None')
        lesson_ids = tuple((_text(item, 'lesson_ids[]') for item in self.lesson_ids))
        invalid_lessons = [item for item in lesson_ids if not _LESSON_ID_RE.fullmatch(item)]
        if invalid_lessons:
            raise ValueError('lesson_ids must use the CSL-NNN format')
        if len(set(lesson_ids)) != len(lesson_ids):
            raise ValueError('lesson_ids must be unique')
        object.__setattr__(self, 'lesson_ids', lesson_ids)

    def to_json_dict(self) -> dict[str, Any]:
        return {'campaign_id': self.campaign_id, 'experiment_id': self.experiment_id, 'benchmark_id': self.benchmark_id, 'question': self.question, 'hypothesis': self.hypothesis, 'alternative': self.alternative, 'decision_rule': self.decision_rule, 'wli_mode': self.wli_mode.value, 'truth_policy': self.truth_policy.value, 'mechanisms': [x.value for x in self.mechanisms], 'budget_seconds': self.budget_seconds, 'budget_evaluations': self.budget_evaluations, 'lesson_ids': list(self.lesson_ids)}

def canonical_config_hash(configuration: Mapping[str, Any]) -> str:
    return hashlib.blake2b(_canonical_json(configuration).encode('utf-8'), digest_size=20, person=b'rdp-cipher-v1').hexdigest()

def telemetry_summary(telemetry: Any) -> dict[str, int | float | None]:
    if telemetry is None:
        return {}
    mapping = isinstance(telemetry, Mapping)
    out: dict[str, int | float | None] = {}
    for name in _COUNTERS:
        if mapping:
            if name not in telemetry:
                continue
            value = telemetry[name]
        else:
            if not hasattr(telemetry, name):
                continue
            value = getattr(telemetry, name)
        if value is None:
            out[name] = None
        elif name.endswith('_time_s'):
            if isinstance(value, bool):
                raise TypeError(f'telemetry.{name} must be a non-negative finite number')
            value = float(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'telemetry.{name} must be a non-negative finite number')
            out[name] = value
        else:
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f'telemetry.{name} must be a non-negative integer')
            if value < 0:
                raise ValueError(f'telemetry.{name} must be a non-negative integer')
            out[name] = value
    return out

def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    text = json.dumps(_mapping(payload, 'payload'), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f'.{path.name}.{os.getpid()}.{time.time_ns()}.tmp')
    try:
        with temporary.open('w', encoding='utf-8', newline='\n') as handle:
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

class ExperimentRun:

    def __init__(self, *, spec: ExperimentSpec, configuration: Mapping[str, Any], repo_root: Path, output_root: Path) -> None:
        if not isinstance(spec, ExperimentSpec):
            raise TypeError('spec must be an ExperimentSpec')
        if not isinstance(repo_root, Path) or not isinstance(output_root, Path):
            raise TypeError('repo_root and output_root must be Path values')
        resolved_repo = repo_root.resolve()
        if not output_root.is_absolute():
            raise ValueError('output_root must be an absolute external path')
        resolved_output = output_root.resolve()
        if resolved_output == resolved_repo or resolved_output.is_relative_to(resolved_repo):
            raise ValueError('output_root must stay outside the repository')
        configuration_json = _canonical_json(configuration)
        self.spec = spec
        self.configuration_hash = hashlib.blake2b(configuration_json.encode('utf-8'), digest_size=20, person=b'rdp-cipher-v1').hexdigest()
        self.repo_root = repo_root.resolve()
        self.output_root = resolved_output
        self._configuration_json = configuration_json
        self.run_dir: Path | None = None
        self.ledger_path: Path | None = None
        self._start: float | None = None
        self._entered = False
        self._finished = False
        self._meta: dict[str, Any] = {}

    def __enter__(self) -> 'ExperimentRun':
        global _ACTIVE_RUN
        if self._entered:
            raise RuntimeError('ExperimentRun cannot be entered more than once')
        if _ACTIVE_RUN is not None:
            raise RuntimeError('only one ExperimentRun may be active in a process')
        self._entered, self._start, _ACTIVE_RUN = (True, time.perf_counter(), self)
        try:
            out_root = self.output_root.resolve()
            if out_root == self.repo_root or out_root.is_relative_to(self.repo_root):
                raise ValueError("output_root must stay outside the repository")
            cfg = api.LoggingConfig(
                verbose=False,
                show_progress=False,
                write_event_log=True,
                output_root=out_root,
                run_category=self.spec.campaign_id,
                label=self.spec.experiment_id,
                portable_output=True,
                write_artifact_manifest=False,
            )
            self.run_dir = init_logging(cfg)
            self.ledger_path = out_root / self.spec.campaign_id / 'experiment_ledger.jsonl'
            self._meta = json.loads((self.run_dir / 'META.json').read_text(encoding='utf-8'))
            _write_json(self.run_dir / 'artifacts/experiment_manifest.json', {'schema': MANIFEST_SCHEMA, 'run_id': self.run_dir.name, 'campaign_id': self.spec.campaign_id, 'experiment': self.spec.to_json_dict(), 'configuration': json.loads(self._configuration_json), 'configuration_hash': self.configuration_hash, 'standard_artifacts': {'run_meta': 'META.json', 'logging_config': 'config/logging.json'}, 'experiment_artifacts': {'progress_snapshot': 'artifacts/progress_snapshot.json', 'result': 'artifacts/experiment_result.json'}})
            return self
        except BaseException:
            _ACTIVE_RUN, self._entered, self._start = (None, False, None)
            raise

    def _active(self) -> None:
        if not self._entered or self.run_dir is None or self._start is None:
            raise RuntimeError('ExperimentRun has not been entered')
        if self._finished:
            raise RuntimeError('ExperimentRun has already finished')

    def _elapsed(self) -> float:
        assert self._start is not None
        return max(0.0, time.perf_counter() - self._start)

    def snapshot(self, *, label: str, metrics: Mapping[str, Any] | None=None, telemetry: Any=None) -> Path:
        self._active()
        metrics = _optional_mapping(metrics, 'metrics')
        _reject_reference_fields(metrics, 'metrics')
        assert self.run_dir is not None
        path = self.run_dir / 'artifacts/progress_snapshot.json'
        _write_json(path, {'schema': SNAPSHOT_SCHEMA, 'recorded_at': _now(), 'run_id': self.run_dir.name, 'campaign_id': self.spec.campaign_id, 'experiment_id': self.spec.experiment_id, 'label': _text(label, 'label'), 'elapsed_s': self._elapsed(), 'metrics': metrics, 'telemetry': telemetry_summary(telemetry)})
        return path

    def finish(self, *, decision: ExperimentDecision | str, stop_reason: str, result_summary: Mapping[str, Any] | None=None, telemetry: Any=None, reference_evaluation: Mapping[str, Any] | None=None) -> Path:
        self._active()
        decision = _enum(decision, ExperimentDecision, 'decision')
        stop_reason = _text(stop_reason, 'stop_reason')
        summary = _optional_mapping(result_summary, 'result_summary')
        _reject_reference_fields(summary, 'result_summary')
        reference = None
        if reference_evaluation is not None:
            if self.spec.truth_policy is TruthPolicy.NONE:
                raise ValueError('reference_evaluation is forbidden when truth_policy is none')
            reference = _mapping(reference_evaluation, 'reference_evaluation')
        category = rdp.api.stop_reason_contract.stop_category_for_reason(stop_reason)
        category = getattr(category, 'value', str(category))
        elapsed, counters = (self._elapsed(), telemetry_summary(telemetry))
        assert self.run_dir is not None
        path = self.run_dir / 'artifacts/experiment_result.json'
        _write_json(path, {'schema': RESULT_SCHEMA, 'recorded_at': _now(), 'run_id': self.run_dir.name, 'campaign_id': self.spec.campaign_id, 'experiment_id': self.spec.experiment_id, 'status': 'completed', 'decision': decision.value, 'stop_category': category, 'stop_reason': stop_reason, 'elapsed_s': elapsed, 'telemetry': counters, 'result_summary': summary, 'reference_evaluation': reference})
        self._finished = True
        self._append_row('completed', decision.value, category, stop_reason, elapsed, counters, summary, path)
        return path

    def _append_row(self, status: str, decision: str | None, category: str, reason: str, elapsed: float, telemetry: Mapping[str, Any], summary: Mapping[str, Any], result_path: Path) -> None:
        assert self.run_dir is not None and self.ledger_path is not None
        git = self._meta.get('git', {})
        git = git if isinstance(git, Mapping) else {}
        append_ledger_row(self.ledger_path, ExperimentLedgerRow(schema=LEDGER_SCHEMA, recorded_at=_now(), run_id=self.run_dir.name, campaign_id=self.spec.campaign_id, experiment_id=self.spec.experiment_id, benchmark_id=self.spec.benchmark_id, question=self.spec.question, hypothesis=self.spec.hypothesis, alternative=self.spec.alternative, configuration_hash=self.configuration_hash, wli_mode=self.spec.wli_mode.value, truth_policy=self.spec.truth_policy.value, mechanisms=tuple((x.value for x in self.spec.mechanisms)), budget_seconds=self.spec.budget_seconds, budget_evaluations=self.spec.budget_evaluations, lesson_ids=self.spec.lesson_ids, status=status, decision=decision, stop_category=category, stop_reason=reason, elapsed_s=elapsed, telemetry=telemetry, result_summary=summary, result_relpath=result_path.relative_to(self.ledger_path.parent).as_posix(), git_commit=git.get('commit'), git_dirty=git.get('dirty')))

    def _fail(self, exc: BaseException) -> None:
        if self.run_dir is None or self._start is None or self._finished:
            return
        if isinstance(exc, Exception):
            message, redacted = portable_exception_message(exc)
        else:
            message, redacted = (str(exc), False)
        summary = {'error_type': type(exc).__name__, 'error_message': message, 'error_details_redacted': bool(redacted)}
        elapsed = self._elapsed()
        path = self.run_dir / 'artifacts/experiment_result.json'
        try:
            _write_json(path, {'schema': RESULT_SCHEMA, 'recorded_at': _now(), 'run_id': self.run_dir.name, 'campaign_id': self.spec.campaign_id, 'experiment_id': self.spec.experiment_id, 'status': 'failed', 'decision': None, 'stop_category': 'error', 'stop_reason': 'exception', 'elapsed_s': elapsed, 'telemetry': {}, 'result_summary': summary, 'reference_evaluation': None})
            self._finished = True
            self._append_row('failed', None, 'error', 'exception', elapsed, {}, summary, path)
        except Exception:
            pass

    def __exit__(self, exc_type, exc, tb) -> bool:
        global _ACTIVE_RUN
        try:
            if exc is not None:
                self._fail(exc)
                return False
            if not self._finished:
                error = RuntimeError('ExperimentRun exited normally without finish()')
                self._fail(error)
                raise error
            return False
        finally:
            if _ACTIVE_RUN is self:
                _ACTIVE_RUN = None
__all__ = ['ExperimentDecision', 'ExperimentRun', 'ExperimentSpec', 'FailureMechanism', 'TruthPolicy', 'WliMode', 'canonical_config_hash', 'telemetry_summary']
