from __future__ import annotations
import json
import os
import datetime as dt
from pathlib import Path
import pytest
from rune_decrypter_prime.io import run_logger
from rune_decrypter_prime.io.run_logger import RunLogger

def _jsonl_events(run_dir: Path) -> list[dict[str, object]]:
    text = (run_dir / 'logs' / 'app.jsonl').read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()]

def test_log_trace_event_path_is_run_relative(tmp_path: Path) -> None:
    logger = RunLogger(out_dir=str(tmp_path))
    trace_path = logger.log_trace({'func': 'example', 'trace': 'trace body'})
    assert trace_path is not None
    events = _jsonl_events(tmp_path)
    trace_events = [event for event in events if event.get('type') == 'trace_written']
    assert len(trace_events) == 1
    event_path = trace_events[0]['path']
    assert isinstance(event_path, str)
    assert not os.path.isabs(event_path)
    assert event_path.startswith('trace/')
    assert (tmp_path / event_path).resolve() == trace_path.resolve()

def test_log_trace_repeated_same_func_writes_unique_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    logger = RunLogger(out_dir=str(tmp_path))

    class FixedDateTime(dt.datetime):

        @classmethod
        def now(cls, tz=None):
            return cls(2026, 5, 12, 10, 11, 12, tzinfo=tz)
    monkeypatch.setattr(run_logger._dt, 'datetime', FixedDateTime)
    first = logger.log_trace({'func': 'same_func', 'trace': 'first'})
    second = logger.log_trace({'func': 'same_func', 'trace': 'second'})
    assert first is not None
    assert second is not None
    assert first != second
    assert first.name == 'same_func__101112.txt'
    assert second.name == 'same_func__101112__001.txt'
    assert first.read_text(encoding='utf-8') == 'first'
    assert second.read_text(encoding='utf-8') == 'second'
    events = _jsonl_events(tmp_path)
    trace_paths = [event['path'] for event in events if event.get('type') == 'trace_written']
    assert len(trace_paths) == 2
    assert len(set(trace_paths)) == 2
    assert all((isinstance(path, str) and (not os.path.isabs(path)) for path in trace_paths))

def test_log_event_path_payloads_are_run_relative(tmp_path: Path) -> None:
    logger = RunLogger(out_dir=str(tmp_path))
    artifact = tmp_path / 'artifacts' / 'report.json'
    logger.log_event({'type': 'artifact', 'path': artifact, 'nested': {'paths': [artifact]}})
    event = _jsonl_events(tmp_path)[0]
    assert event['path'] == 'artifacts/report.json'
    nested = event['nested']
    assert isinstance(nested, dict)
    assert nested['paths'] == ['artifacts/report.json']

def test_log_event_relative_path_payloads_are_preserved(tmp_path: Path) -> None:
    logger = RunLogger(out_dir=str(tmp_path))
    logger.log_event({'type': 'artifact', 'path': Path('artifacts/report.json')})
    event = _jsonl_events(tmp_path)[0]
    assert event['path'] == 'artifacts/report.json'

def test_log_event_external_path_payloads_are_redacted(tmp_path: Path) -> None:
    logger = RunLogger(out_dir=str(tmp_path))
    external_path = tmp_path.parent / 'outside-run-dir.txt'
    logger.log_event({'type': 'external', 'path': external_path})
    event = _jsonl_events(tmp_path)[0]
    assert event['path'] == '<external>'

def test_log_trace_error_event_uses_portable_error_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    logger = RunLogger(out_dir=str(tmp_path))
    leaked_path = tmp_path / 'private' / 'secret.txt'

    def _raise_path_error(self: Path, *args, **kwargs) -> int:
        _ = (self, args, kwargs)
        raise RuntimeError(f'cannot write {leaked_path}')
    monkeypatch.setattr(Path, 'write_text', _raise_path_error)
    trace_path = logger.log_trace({'func': 'failing_trace', 'trace': 'body'})
    assert trace_path is None
    events = _jsonl_events(tmp_path)
    trace_errors = [event for event in events if event.get('type') == 'trace_error']
    assert len(trace_errors) == 1
    event = trace_errors[0]
    assert 'error' not in event
    assert event['error_type'] == 'RuntimeError'
    assert event['error_message'] == 'cannot write <path>'
    assert event['error_details_redacted'] is True
    assert str(leaked_path) not in json.dumps(event)
