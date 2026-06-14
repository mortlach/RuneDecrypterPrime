from __future__ import annotations

from typing import Optional, Sequence, Dict, Any
import numpy as np

from rune_decrypter_prime.core.types import Direction
from rune_decrypter_prime.utils.runeglish import Runeglish as _R
from rune_decrypter_prime.telemetry.events import attach_telemetry_to_meta
from rune_decrypter_prime.telemetry.pipeline import finalize_run_meta


_SCORER_LANES_ERROR_CODE = "scorer_lanes_unavailable"


def finalize_solution(
    problem,
    res,
    *,
    ciphertext: np.ndarray,
    wli: Optional[Sequence[Sequence[int]]],
    cipher,
    encoding_dir: Direction,
    cfg=None,
    telemetry_on: bool = True,
    pipeline_block: Optional[Dict[str, Any]] = None,
):
    """
    Attach telemetry (if enabled) and normalize plaintext/ciphertext views.
    """
    if telemetry_on:
        attach_telemetry_to_meta(res, problem)
    else:
        if not hasattr(res, "meta") or res.meta is None:
            res.meta = {}
        # Mark explicitly so lower layers (e.g., dump_telemetry) can hard-respect the toggle
        try:
            res.meta["telemetry_off"] = True
        except Exception:
            pass

    _attach_scorer_lanes_to_meta(res, problem)

    try:
        res.wli = wli
    except Exception:
        pass

    ensure_plaintext_rune(
        res,
        ciphertext=ciphertext,
        wli=wli,
        cipher=cipher,
        encoding_dir=encoding_dir,
    )

    if telemetry_on and cfg is not None:
        try:
            finalize_run_meta(res, cfg)
        except Exception:
            pass

    if pipeline_block is not None:
        try:
            res.pipeline = dict(pipeline_block)
        except Exception:
            pass

    return res


def _set_scorer_lanes_payload(res, payload: dict[str, Any]) -> None:
    if not hasattr(res, "meta") or not isinstance(getattr(res, "meta", None), dict):
        res.meta = {}
    res.meta["scorer_lanes"] = payload


def _scorer_lanes_error_payload(*, message: str, exc: BaseException | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {
        "code": _SCORER_LANES_ERROR_CODE,
        "message": str(message),
    }
    if exc is not None:
        error["exception_type"] = exc.__class__.__name__
    return {
        "lanes": [],
        "components": [],
        "error": error,
    }


def _attach_scorer_lanes_to_meta(res, problem) -> None:
    scorer = getattr(problem, "scorer", None)
    capability_report = getattr(scorer, "capability_report", None)
    if not callable(capability_report):
        return

    try:
        report = capability_report()
    except Exception as exc:
        _set_scorer_lanes_payload(
            res,
            _scorer_lanes_error_payload(
                message="scorer capability_report() failed",
                exc=exc,
            ),
        )
        return

    to_json_dict = getattr(report, "to_json_dict", None)
    try:
        payload = to_json_dict() if callable(to_json_dict) else report
    except Exception as exc:
        _set_scorer_lanes_payload(
            res,
            _scorer_lanes_error_payload(
                message="scorer capability report serialization failed",
                exc=exc,
            ),
        )
        return

    if not isinstance(payload, dict):
        _set_scorer_lanes_payload(
            res,
            _scorer_lanes_error_payload(
                message=f"scorer capability report payload must be dict, got {type(payload).__name__}",
            ),
        )
        return

    _set_scorer_lanes_payload(res, payload)


def ensure_plaintext_rune(res, *, ciphertext=None, wli=None, cipher=None, encoding_dir=Direction.RTL):
    """Populate canonical plaintext/ciphertext views on the Solution (idempotent)."""
    import numpy as _np

    # plaintext_idx
    try:
        pt = getattr(res, "plaintext", None)
        if pt is not None:
            arr = _np.asarray(pt, dtype=_np.uint8).reshape(-1)
            res.plaintext_idx = [int(x) for x in arr.tolist()]
    except Exception:
        pass

    # plaintext_rune / latin variants
    try:
        if getattr(res, "plaintext_idx", None):
            idx = list(res.plaintext_idx)
            w = wli if wli is not None else getattr(res, "wli", None)
            try:
                res.plaintext_rune = _R.to_rune(idx, w)
            except Exception:
                res.plaintext_rune = ""
            try:
                res.plaintext_latin = _R.to_latin(idx, w)
            except Exception:
                try:
                    res.plaintext_latin = _R.to_rune_latin(idx, w)
                except Exception:
                    res.plaintext_latin = ""
            res.plaintext_rune_nospace = str(getattr(res, "plaintext_rune", "")).replace(" ", "")
            res.plaintext_latin_nospace = str(getattr(res, "plaintext_latin", "")).replace(" ", "")
            if not getattr(res, "plaintext_str", ""):
                res.plaintext_str = res.plaintext_rune
    except Exception:
        pass

    # ciphertext canonical views
    try:
        ct = getattr(res, "ciphertext_idx", None)
        if not ct and ciphertext is not None:
            arr = _np.asarray(ciphertext, dtype=_np.uint8).reshape(-1)
            res.ciphertext_idx = [int(x) for x in arr.tolist()]
        if getattr(res, "ciphertext_idx", None):
            w = wli if wli is not None else getattr(res, "wli", None)
            res.ciphertext_rune = _R.to_rune(res.ciphertext_idx, w)
            try:
                res.ciphertext_latin = _R.to_latin(res.ciphertext_idx, w)
            except Exception:
                try:
                    res.ciphertext_latin = _R.to_rune_latin(res.ciphertext_idx, w)
                except Exception:
                    res.ciphertext_latin = ""
            res.ciphertext_rune_nospace = str(getattr(res, "ciphertext_rune", "")).replace(" ", "")
            res.ciphertext_latin_nospace = str(getattr(res, "ciphertext_latin", "")).replace(" ", "")
    except Exception:
        pass

    # Direction metadata
    try:
        if not hasattr(res, "pipeline") or res.pipeline is None:
            res.pipeline = {}
        if isinstance(res.pipeline, dict):
            res.pipeline.setdefault("text_encoding_direction", str(getattr(encoding_dir, "value", encoding_dir)))
    except Exception:
        pass

    return res
