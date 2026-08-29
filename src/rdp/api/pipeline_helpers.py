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

    # ---- Key normalisation -------------------------------------------------
    key_val = getattr(res, "key", None)
    if isinstance(key_val, _np.ndarray):
        try:
            res.key = key_val.astype(int).tolist()
        except Exception:
            pass
    elif hasattr(key_val, "tolist") and not isinstance(key_val, list):
        try:
            res.key = key_val.tolist()
        except Exception:
            pass
    elif isinstance(key_val, tuple):
        res.key = list(key_val)

    # ---- Plaintext indices --------------------------------------------------
    idx_source = getattr(res, "plaintext_idx", None)
    arr = None
    if idx_source is not None:
        arr = _np.asarray(idx_source, dtype=_np.uint8).reshape(-1)
        if arr.size == 0:
            arr = None

    if arr is None:
        pt = getattr(res, "plaintext", None)
        if isinstance(pt, (list, tuple, _np.ndarray)):
            arr = _np.asarray(pt, dtype=_np.uint8).reshape(-1)
        elif isinstance(pt, str) and pt:
            try:
                arr = _np.asarray(_R.rune_to_pos(pt.replace(' ', '')), dtype=_np.uint8).reshape(-1)
            except Exception:
                arr = _np.asarray([], dtype=_np.uint8)
        else:
            arr = _np.asarray([], dtype=_np.uint8)

    pt_idx_list = arr.tolist()
    res.plaintext_idx = pt_idx_list

    # ---- WLI reconciliation -------------------------------------------------
    wli_from_res = getattr(res, "wli", None)
    effective_wli = wli_from_res if wli_from_res is not None else wli
    if effective_wli is not None and len(effective_wli) != len(pt_idx_list):
        effective_wli_valid = None
    else:
        effective_wli_valid = effective_wli

    if effective_wli_valid is not None and wli_from_res is None:
        try:
            res.wli = effective_wli_valid
        except Exception:
            pass

    has_wli = effective_wli_valid is not None
    res.has_wli = bool(has_wli)

    # ---- Plaintext renderings ----------------------------------------------
    def _latin_nospace(seq):
        try:
            return ''.join(_R.pos_to_latin(int(p)) for p in seq)
        except Exception:
            return ''

    try:
        pt_rune_nospace = _R.pos_to_rune(pt_idx_list)
    except Exception:
        pt_rune_nospace = ''

    if has_wli:
        try:
            pt_rune = _R.to_rune(pt_idx_list, effective_wli_valid)
        except Exception:
            pt_rune = pt_rune_nospace
        try:
            pt_latin = _R.to_rune_latin(pt_idx_list, effective_wli_valid, direction=encoding_dir)
        except Exception:
            pt_latin = _latin_nospace(pt_idx_list)
    else:
        pt_rune = pt_rune_nospace
        pt_latin = _latin_nospace(pt_idx_list)

    pt_latin_nospace = _latin_nospace(pt_idx_list)

    res.plaintext_rune_nospace = pt_rune_nospace
    res.plaintext_rune = pt_rune
    res.plaintext_str = pt_rune
    res.plaintext_latin = pt_latin
    res.plaintext_latin_nospace = pt_latin_nospace

    # ---- Ciphertext renderings ---------------------------------------------
    if ciphertext is not None:
        ct_arr = _np.asarray(ciphertext, dtype=_np.uint8).reshape(-1)
        ct_idx_list = ct_arr.tolist()
        res.ciphertext_idx = ct_idx_list

        ct_wli = wli if wli is not None else effective_wli_valid
        if ct_wli is not None and len(ct_wli) != len(ct_idx_list):
            ct_wli = None

        def _latin_from_idx(seq):
            try:
                return ''.join(_R.pos_to_latin(int(p)) for p in seq)
            except Exception:
                return ''

        try:
            ct_rune_nospace = _R.pos_to_rune(ct_idx_list)
        except Exception:
            ct_rune_nospace = ''

        if ct_wli is not None:
            try:
                ct_rune = _R.to_rune(ct_idx_list, ct_wli)
            except Exception:
                ct_rune = ct_rune_nospace
            try:
                ct_latin = _R.to_rune_latin(ct_idx_list, ct_wli, direction=encoding_dir)
            except Exception:
                ct_latin = _latin_from_idx(ct_idx_list)
        else:
            ct_rune = ct_rune_nospace
            ct_latin = _latin_from_idx(ct_idx_list)

        ct_latin_nospace = _latin_from_idx(ct_idx_list)

        res.ciphertext_idx = ct_idx_list
        res.ciphertext_rune = ct_rune
        res.ciphertext_rune_nospace = ct_rune_nospace
        res.ciphertext_latin = ct_latin
        res.ciphertext_latin_nospace = ct_latin_nospace
    else:
        res.ciphertext_idx = list(getattr(res, "ciphertext_idx", []))
        res.ciphertext_rune = getattr(res, "ciphertext_rune", '')
        res.ciphertext_rune_nospace = getattr(
            res,
            "ciphertext_rune_nospace",
            res.ciphertext_rune.replace(' ', ''),
        )
        res.ciphertext_latin = getattr(res, "ciphertext_latin", '')
        res.ciphertext_latin_nospace = getattr(
            res,
            "ciphertext_latin_nospace",
            res.ciphertext_latin.replace(' ', ''),
        )

    # ---- Metadata ----------------------------------------------------------
    try:
        res.alphabet_size = int(getattr(res, "alphabet_size", _R.size()))
    except Exception:
        res.alphabet_size = _R.size()
    res.alphabet = getattr(res, "alphabet", "runic-29")

    if encoding_dir is not None:
        dir_value = encoding_dir.value if isinstance(encoding_dir, Direction) else str(encoding_dir)
        res.direction = dir_value.lower()

    if cipher is not None:
        res.cipher_name = getattr(cipher, "name", '') or getattr(
            cipher,
            "kind",
            getattr(res, "cipher_name", ''),
        )

    return res


def coerce_wli_for_config(wli):
    if wli is None:
        return None
    converted = []
    for pair in wli:
        if pair is None:
            continue
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("wli entries must be (pos_in_word, word_len) pairs")
        pos = int(pair[0])
        ln = int(pair[1])
        converted.append([pos, ln])
    return converted
