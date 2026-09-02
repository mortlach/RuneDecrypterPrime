# ============================================================
# rdp/io/run_logger.py
# Minimal structured run logger for tests & dev runs.
# ============================================================
from __future__ import annotations

from dataclasses import is_dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any
import json
import datetime as _dt
import threading

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except Exception:  # pragma: no cover
    ZoneInfo = None  # type: ignore[assignment]
    ZoneInfoNotFoundError = Exception  # type: ignore[assignment]

# Importing here avoids circulars (core.logging_config does not import us)
from rdp.core.config.logging_config import (
    LoggingConfig,
    init_logging,
    get_run_dir,
)
from rdp.io.artifact_policy import (
    artifact_json_value,
    artifact_path,
    portable_exception_message,
)


def _load_log_timezone():
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo("America/Los_Angeles")
    except ZoneInfoNotFoundError:
        return _dt.timezone.utc


_TZ = _load_log_timezone()
_lock = threading.Lock()
_singleton: Optional["RunLogger"] = None


def _ts() -> str:
    if _TZ:
        return _dt.datetime.now(tz=_TZ).isoformat()
    return _dt.datetime.now().isoformat()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


class RunLogger:
    """
    Simple JSONL event logger + text trace writer.

    • If out_dir is provided, use it.
    • Else, try get_run_dir() from logging_config.
    • If not initialized yet, self-initialize with a sensible default
      (run_kind="test", label="autolog").
    """
    def __init__(self, *, out_dir: Optional[str] = None, echo: bool = False):
        # Resolve where to write
        if out_dir:
            rd = Path(out_dir).resolve()
            _ensure_dir(rd / "logs")
            _ensure_dir(rd / "trace")
        else:
            try:
                rd = get_run_dir()
            except Exception:
                # No prior init — do a minimal self-init for tests/dev
                cfg = LoggingConfig(verbose=echo, print_progress=echo, write_jsonl=True,
                                    run_kind="test", label="autolog")
                rd = init_logging(cfg)

        self._run_dir = rd
        self._echo = bool(echo)
        self._jsonl_path = (self._run_dir / "logs" / "app.jsonl").resolve()
        # touch file
        _ensure_dir(self._jsonl_path.parent)
        if not self._jsonl_path.exists():
            self._jsonl_path.write_text("", encoding="utf-8")

    # ------------ public helpers ------------
    @property
    def run_dir(self) -> Path:
        return self._run_dir

    def log_event(self, obj: Dict[str, Any]) -> None:
        """
        Append one JSON object as a line into logs/app.jsonl, with timestamp.
        """
        if is_dataclass(obj):
            obj = asdict(obj)  # type: ignore[assignment]
        rec = artifact_json_value(dict(obj), root=self._run_dir)
        rec.setdefault("ts", _ts())
        line = json.dumps(rec, ensure_ascii=False)
        with _lock:
            with self._jsonl_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        if self._echo:
            # Keep console readable, but don't spam on huge dicts
            typ = rec.get("type", "event")
            print(f"[log] {typ}: { {k: v for k, v in rec.items() if k != 'trace'} }", flush=True)

    def log_trace(self, obj: Dict[str, Any]) -> Optional[Path]:
        """
        Write a human-readable trace file under trace/, also record an event.
        Expected keys: {"func": "name", "trace": "<text>"}.
        """
        func = str(obj.get("func", "trace"))
        text = str(obj.get("trace", ""))
        safe = "".join(ch for ch in func if ch.isalnum() or ch in "-_")[:80] or "trace"
        stem = f"{safe}__{_dt.datetime.now().strftime('%H%M%S')}"
        path = (self._run_dir / "trace" / f"{stem}.txt").resolve()
        suffix = 1
        while path.exists():
            path = (self._run_dir / "trace" / f"{stem}__{suffix:03d}.txt").resolve()
            suffix += 1
        _ensure_dir(path.parent)
        try:
            path.write_text(text, encoding="utf-8")
            self.log_event(
                {
                    "type": "trace_written",
                    "func": func,
                    "path": artifact_path(path, root=self._run_dir),
                }
            )
            return path
        except Exception as e:
            error_message, error_details_redacted = portable_exception_message(e)
            self.log_event(
                {
                    "type": "trace_error",
                    "func": func,
                    "error_type": type(e).__name__,
                    "error_message": error_message,
                    "error_details_redacted": error_details_redacted,
                }
            )
            return None


# ------------- singleton -------------
def get_logger() -> RunLogger:
    global _singleton
    if _singleton is None:
        _singleton = RunLogger()
    return _singleton
