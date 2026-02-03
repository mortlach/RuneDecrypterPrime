"""Single-source normalisation helpers for the public API boundary."""
from __future__ import annotations
from typing import List, Tuple, Sequence, Union, Optional, TypeVar, Dict, Any
import numpy as np

from rune_decrypter_prime.api._resolve import resolve_optimizer_aliases
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.core.types import (
    Direction,
    Device,
    SeMode,
    Channel,
    ObjectiveSpec,
    Stat,
    ObjectiveFamily,
    ensure_direction,
    ensure_float_dtype,
)
_T = TypeVar("_T")

def normalize_objective_family(value: Any) -> ObjectiveFamily:
    if isinstance(value, str):
        v = value.lower()
        if v in ("pct", "percentile"):
            return ObjectiveFamily.PCT
        if v in ("avg", "average"):
            return ObjectiveFamily.AVG
        if v == "energy":
            return ObjectiveFamily.PCT
        if v == "neglogp":
            return ObjectiveFamily.NEGLOGP
        raise ValueError(f"Unknown ObjectiveFamily string: {value}.")
    elif isinstance(value, ObjectiveFamily):
        return ObjectiveFamily.PCT if value is ObjectiveFamily.ENERGY else value
    else:
        raise ValueError(f"Unknown ObjectiveFamily parameter type: {type(value)}.")


def normalize_stat(value: Any) -> Stat:
    if isinstance(value, str):
        v = value.lower()
        if v == "logp":
            return Stat.LOGP
        if v == "zsum":
            return Stat.ZSUM
        if v == "madsum":
            return Stat.MADSUM
        raise ValueError(f"Unknown Stat string: {value}.")
    elif isinstance(value, Stat):
        return value
    else:
        raise ValueError(f"Unknown Stat parameter type: {type(value)}.")


def normalize_objective_spec(value: Any) -> ObjectiveSpec:
    if isinstance(value, ObjectiveSpec):
        if value.family is ObjectiveFamily.ENERGY:
            return ObjectiveSpec(family=ObjectiveFamily.PCT, stat=value.stat, win=value.win)
        return value
    if isinstance(value, str):
        # parse simple dotted strings like "pct.logp.win10" or "neglogp"
        parts = value.lower().split(".")
        if parts[0] in ("pct", "energy"):
            if len(parts) == 3 and parts[2].startswith("win"):
                win = int(parts[2][3:])
            else:
                raise ValueError(f"ObjectiveSpec '{value}' must include window (e.g. win10).")
            return ObjectiveSpec(
                family=ObjectiveFamily.PCT,
                stat=normalize_stat(parts[1]),
                win=win,
            )
        elif parts[0] in ("avg", "neglogp"):
            fam = normalize_objective_family(parts[0])
            stat = None
            win = None
            if fam is ObjectiveFamily.AVG:
                if len(parts) >= 2 and parts[1]:
                    stat = normalize_stat(parts[1])
                else:
                    stat = Stat.LOGP
                if len(parts) >= 3 and parts[2].startswith("win"):
                    win = int(parts[2][3:])
            return ObjectiveSpec(family=fam, stat=stat, win=win)
        else:
            raise ValueError(f"Cannot parse ObjectiveSpec string: {value}.")
    elif isinstance(value, dict):
        fam = normalize_objective_family(value.get("family"))
        stat = normalize_stat(value.get("stat")) if value.get("stat") else None
        win = value.get("win")
        return ObjectiveSpec(family=fam, stat=stat, win=win)
    else:
        raise ValueError(f"Unknown ObjectiveSpec parameter type: {type(value)}.")

def normalize_encoding_dir(direction: Union[str, Direction]) -> Direction:
    """Strict public API normaliser for text direction."""
    if direction is None:
        raise ValueError("encoding_dir must be 'ltr' or 'rtl', not None.")
    if isinstance(direction, str):
        key = direction.strip().lower()
        alias = {
            "fwd": "ltr",
            "forward": "ltr",
            "rev": "rtl",
            "reverse": "rtl",
        }
        key = alias.get(key, key)
        if key not in {"ltr", "rtl"}:
            raise ValueError(f"Unknown encoding_dir '{direction}'. Expected 'ltr' or 'rtl'.")
        direction = key
    try:
        return ensure_direction(direction)
    except (TypeError, ValueError) as exc:
        raise ValueError(str(exc)) from exc


def normalize_se_mode(value: Any) -> SeMode:
    if isinstance(value, SeMode):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "nose":
            return SeMode.NOSE
        if v == "wise":
            return SeMode.WISE
        raise ValueError(f"Unknown SeMode string: {value}.")
    raise ValueError(f"Unknown SeMode parameter(s): {type(value)}.")


def normalize_channel(value: Any) -> Channel:
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "char":
            return Channel.CHAR
        if v == "wli":
            return Channel.WLI
        raise ValueError(f"Unknown Channel string: {value}.")
    if isinstance(value, Channel):
        return value
    raise ValueError(f"Unknown Channel parameter(s): {type(value)}.")


def normalize_device(value: Any) -> Device:
    """
    Accept Device or strings ('cpu','cuda'), plus alias 'gpu'->CUDA.
    """
    if isinstance(value, Device):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v == "cpu":
            return Device.CPU
        if v in ("cuda", "gpu"):
            return Device.CUDA
    raise TypeError(f"Invalid device: {value!r} (expected Device or 'cpu'/'cuda'/'gpu').")


def normalize_scorer_params(params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not params:
        return {}
    if "channel" in params:
        raise ValueError("scorer_params.channel is not supported (use include_char/use_word_breaks/weights instead).")
    if "device" in params:
        raise ValueError("scorer_params.device is not supported (use RunAPI device=...).")
    if "se_mode" in params:
        params["se_mode"] = normalize_se_mode(params["se_mode"])
    if "encoding_dir" in params:
        params["encoding_dir"] = normalize_encoding_dir(params["encoding_dir"])
    if "objective" in params:
        params["objective"] = normalize_objective_spec(params["objective"])
    if "objective" not in params and "win" in params:
        params["objective"] = ObjectiveSpec(
            family=ObjectiveFamily.PCT,
            stat=Stat.LOGP,
            win=int(params["win"]),
        )
        params.pop("win", None)
    if "objective" in params and "win" in params:
        obj = params.get("objective")
        legacy_win = params.get("win")
        if isinstance(obj, ObjectiveSpec) and obj.family in (ObjectiveFamily.PCT, ObjectiveFamily.ENERGY, ObjectiveFamily.AVG):
            if obj.win is None and legacy_win is not None:
                stat = obj.stat if obj.stat is not None else (Stat.LOGP if obj.family is ObjectiveFamily.AVG else obj.stat)
                params["objective"] = ObjectiveSpec(family=obj.family, stat=stat, win=int(legacy_win))
        params.pop("win", None)
    if "compute_dtype" in params:
        params["compute_dtype"] = ensure_float_dtype(params["compute_dtype"]).value
    if "acc_dtype" in params:
        params["acc_dtype"] = ensure_float_dtype(params["acc_dtype"]).value
    if "dtype" in params and params["dtype"] is not None:
        params["dtype"] = ensure_float_dtype(params["dtype"]).value
    return params

# ----------------------------- public API ----------------------------- #

def _coerce_index_array(data: Any) -> np.ndarray:
    raw = np.asarray(data)
    if raw.dtype.kind == "f":
        if not np.all(np.isfinite(raw)):
            raise ValueError("ciphertext indices must be finite integers")
        if not np.all(raw == np.floor(raw)):
            raise TypeError("ciphertext indices must be integers")
    idx = raw.astype(np.int64, copy=False).reshape(-1)
    if idx.size and ((idx < 0).any() or (idx > 28).any()):
        raise ValueError("ciphertext indices must be in [0..28]")
    out = idx.astype(np.uint8, copy=False).reshape(-1)
    # Force C-contig; view if possible, else copy once.
    if not out.flags.c_contiguous:
        out = np.ascontiguousarray(out)
    return out

def to_indices(text: Union[str, np.ndarray, Sequence[int], Tuple[np.ndarray, Sequence[Sequence[int]]]]) -> np.ndarray:
    """Return `np.ndarray[np.uint8]` of rune indices (shape (L,), C-contiguous).

    Accepted `text` forms:
    1) Rune string (29 alphabet). Spaces allowed; ignored here (WLI is inferred elsewhere).
    2) English string (A–Z); transliterated word-by-word → runes → indices.
    3) Sequence of ints (already rune indices 0..28).
    4) Tuple `(indices, wli)` — **fast path**: if given, we return the indices part
       (the WLI remains the caller’s responsibility for this function).
    """
    # Fast-path: (indices, wli) tuple — accept indices directly
    if isinstance(text, tuple) and len(text) == 2:
        arr, _ = text
        return _coerce_index_array(arr)

    # Numpy array of ints
    if isinstance(text, np.ndarray):
        return _coerce_index_array(text)

    # List/tuple of ints
    if isinstance(text, (list, tuple)) and not isinstance(text, str):
        return _coerce_index_array(text)

    # String path: rune string or English words
    if isinstance(text, str):
        words = [w for w in text.split() if w]
        runeset = set(getattr(Runeglish, "runes", []))
        is_rune_string = any(ch in runeset for ch in text)

        all_idx: list[int] = []
        if is_rune_string:
            # Rune words → indices
            for w in words:
                try:
                    all_idx.extend(Runeglish.rune_to_pos(w))
                except KeyError as e:
                    raise ValueError(f"Unknown rune character: {e.args[0]}") from None
        else:
            # English → Runeglish (gematria) → indices, per word
            for w in words:
                rw = Runeglish.translate_to_gematria(w.upper())
                try:
                    all_idx.extend(Runeglish.rune_to_pos(rw))
                except KeyError as e:
                    raise ValueError(f"English→rune produced unknown rune: {e.args[0]}") from None
        return _coerce_index_array(all_idx)

    raise TypeError("Unsupported ciphertext type: expected str | array | sequence[int] | (indices, wli) tuple.")


def make_single_word_wli(L: int) -> list[list[int]] | None:
    """Return a single-word WLI using (pos_in_word, word_len). (L must be <= 63 for LMPrime WLI encoding.)"""
    if L >= 0:
        return [[i, L] for i in range(0, L)]
    return None


def wli_from_text(text: str) -> List[List[int]]:
    """Infer WLI from spaces in a *string* input after transliteration.
    WLI entries are (pos_in_word, word_len).
    """
    words = [w for w in text.split() if w]
    # Build lengths in rune-space (after transliteration) for correctness.
    rune_lengths: list[int] = []
    for w in words:
        rw = w if any(ch in getattr(Runeglish, "runes", []) for ch in w) else Runeglish.translate_to_gematria(w.upper())
        rune_lengths.append(len(Runeglish.rune_to_pos(rw)))

    wli: list[list[int]] = []
    for ln in rune_lengths:
        for i in range(ln):
            wli.append([i, ln])
    return wli

def runes_from_indices(idx: Sequence[int], wli: Optional[Sequence[Sequence[int]]] = None) -> str:
    """
    Render rune characters from indices (grouped by WLI).
    This is NOT the Latin-canon. For Latin-canon, use Runeglish.to_rune(indices, wli).
    """
    idx = list(map(int, idx))
    if Runeglish is None:
        return ""
    if not wli:
        # Single-word render
        return "".join(Runeglish.pos_to_rune(i) for i in idx)  # type: ignore[union-attr]

    out_words: List[str] = []
    cur: List[str] = []
    for i, sym in enumerate(idx):
        cur.append(Runeglish.pos_to_rune(sym))  # type: ignore[union-attr]
        if wli[i][0] == wli[i][1] - 1:
            out_words.append("".join(cur))
            cur = []
    if cur:
        out_words.append("".join(cur))
    return " ".join(out_words)

def normalize_ciphertext(
    text: Union[str, np.ndarray, Sequence[int], Tuple[np.ndarray, Sequence[Sequence[int]]]],
    wli_data: Optional[Sequence[Sequence[int]]] = None,
) -> Tuple[np.ndarray, List[List[int]]]:
    """Convert user ciphertext input into (indices, WLI), **once**.

    Accepted inputs:
      • Rune string (29 alphabet, spaces optional)
      • English string (A–Z; transliterated per word)
      • Sequence of ints (already rune indices 0..28)
      • Tuple `(indices, wli)` — **fast path** (both must be valid)

    WLI rules:
      • If input is indices and caller provides `wli_data`, we trust it.
      • If input is indices and no `wli_data`, default to a single-word WLI.
      • If input is string, WLI is inferred from spaces after transliteration.
      • If a `(indices, wli)` tuple is passed, it overrides `wli_data`.
    """
    # Fast path: pre-normalised tuple
    if isinstance(text, tuple) and len(text) == 2:
        arr, wli = text
        ct = to_indices(arr)
        wli_list = [[int(p[0]), int(p[1])] for p in wli]
        _assert_core_ready(ct, wli_list)
        return ct, wli_list

    # Normalise indices
    ct = to_indices(text)

    # Build/accept WLI
    if wli_data is not None:
        wli_list = [[int(p[0]), int(p[1])] for p in wli_data]
    elif isinstance(text, str):
        wli_list = wli_from_text(text)
    else:
        wli_list = make_single_word_wli(int(ct.size))
    _assert_core_ready(ct, wli_list)
    return ct, wli_list


# --------------------------- internal helpers --------------------------- #

def _assert_core_ready(ct: np.ndarray, wli_list: Sequence[Sequence[int]] = None) -> None:
    """Hard, cheap assertions for the UI→core boundary.
    Guarantees so the core never re-casts/validates again:
      • ct: dtype=uint8, shape (L,), C-contiguous
      • WLI: list of (pos_in_word, word_len) pairs with length == L
    """
    if not isinstance(ct, np.ndarray):
        raise TypeError("ct must be a numpy ndarray")
    if ct.dtype != np.uint8:
        raise TypeError("ct must be dtype uint8")
    if ct.ndim != 1:
        raise ValueError("ct must be 1-D")
    if not ct.flags.c_contiguous:
        raise ValueError("ct must be C-contiguous")

    if wli_list is not None:
        if not isinstance(wli_list, (list, tuple)):
            raise TypeError("wli must be a list of [pos_in_word, word_len] pairs")
        if len(wli_list) == 0:
            return
        _validate_wli_poslen(wli_list, int(ct.size))


def _as_int(value: Any, name: str) -> int:
    import numpy as _np
    if isinstance(value, (bool, str, bytes, bytearray)):
        raise TypeError(f"{name} must be an integer")
    if isinstance(value, (float, _np.floating)):
        raise TypeError(f"{name} must be an integer")
    try:
        return int(value)
    except Exception as exc:
        raise TypeError(f"{name} must be an integer") from exc


def _validate_wli_poslen(wli_list: Sequence[Sequence[int]], L: int) -> None:
    if len(wli_list) != int(L):
        raise ValueError("wli length must match ciphertext length")
    expected_pos = 0
    current_len = None
    for i, p in enumerate(wli_list):
        if not (isinstance(p, (list, tuple)) and len(p) == 2):
            raise TypeError("each wli entry must be a [pos_in_word, word_len] pair")
        pos = _as_int(p[0], f"wli[{i}][0]")
        ln = _as_int(p[1], f"wli[{i}][1]")
        if pos < 0 or ln <= 0:
            raise ValueError("wli entries must be non-negative; word_len must be > 0")
        if pos >= ln:
            raise ValueError("wli pos_in_word must be < word_len")
        if pos > 63 or ln > 63:
            raise ValueError("wli entries must be <= 63 to match LMPrime WLI encoding")
        if expected_pos == 0:
            current_len = ln
        if ln != current_len:
            raise ValueError("wli word_len must remain constant within a word")
        if pos != expected_pos:
            raise ValueError("wli pos_in_word sequence must be contiguous within each word")
        expected_pos += 1
        if expected_pos == current_len:
            expected_pos = 0
            current_len = None
    if expected_pos != 0:
        raise ValueError("wli word_len exceeds available positions")

# --- Enum normalisers (API boundary only) -------------------------------------
from typing import Any, Union
from rune_decrypter_prime.core.types import Direction, ScorerImpl, SolverName

# def normalize_direction(x: Union[str, Direction]) -> Direction:
#     if isinstance(x, Direction):
#         return x
#     v = str(x).strip().lower()
#     if v == "ltr":
#         return Direction.LTR
#     if v == "rtl":
#         return Direction.RTL
#     raise ValueError(f"Unknown direction: {x!r} (expected 'ltr' or 'rtl' or Direction)")

def normalize_scorer_impl(x: Union[str, ScorerImpl]) -> ScorerImpl:
    if isinstance(x, ScorerImpl):
        return x
    v = str(x).strip().lower()
    match v:
        case "numpy":   return ScorerImpl.NUMPY
        case "torch":   return ScorerImpl.TORCH
        case "unified": return ScorerImpl.UNIFIED
        case "auto":    return ScorerImpl.AUTO
    raise ValueError(f"Unknown scorer impl: {x!r} (expected 'numpy'|'torch'|'unified'|'auto' or ScorerImpl)")

def normalize_optimizer_name(x: Union[str, SolverName]) -> SolverName:
    if isinstance(x, SolverName):
        return x
    v = str(x).strip().lower()
    match v:
        case "beam":   return SolverName.BEAM
        case "ga":     return SolverName.GA
        case "sa":     return SolverName.SA
        case "hybrid": return SolverName.HYBRID
        case "kaeding": return SolverName.KAEDING
    raise ValueError(
        f"Unknown solver name: {x!r} (expected 'beam'|'ga'|'sa'|'hybrid'|'kaeding' or OptimizerName)"
    )




# --- TEXT_PERMUTATION helpers ---

def _perm_as_sequence(obj: Any) -> Sequence[Any]:
    # Accept list/tuple/range; accept numpy arrays if present (duck-typed via .tolist()).
    if isinstance(obj, (list, tuple, range)):
        return obj  # type: ignore[return-value]
    if hasattr(obj, "tolist") and callable(getattr(obj, "tolist")):
        return obj.tolist()  # numpy-like
    raise TypeError("Permutation must be a sequence of integers (list/tuple/range or numpy array).")

def _perm_to_int_list(seq: Sequence[Any]) -> list[int]:
    """
    Coerce to list[int] with strict type policy:
      - Accept: Python ints, numpy integer scalars (via int(x))
      - Reject: str/bytes/bytearray, bool, float (incl. numpy floats)
      - Rationale: TEXT_PERMUTATION must be a list of integers, not strings or floats.
    """
    out: list[int] = []
    for i, x in enumerate(seq):
        # hard rejects
        if isinstance(x, (str, bytes, bytearray)):
            raise TypeError(f"Permutation contains non-integer at index {i}: {x!r}")
        if isinstance(x, bool):
            raise TypeError(f"Permutation contains boolean at index {i}: {x!r}")
        if isinstance(x, float):
            raise TypeError(f"Permutation contains float at index {i}: {x!r}")
        try:
            xi = int(x)  # allows numpy integer scalars, IntEnum, etc.
        except Exception as e:
            raise TypeError(f"Permutation contains non-integer at index {i}: {x!r}") from e
        out.append(xi)
    return out

def normalize_text_permutation(p: Optional[Any], n_tokens: int) -> Optional[list[int]]:
    """
    Normalize TEXT_PERMUTATION at the UI boundary.
      - None -> None
      - Otherwise accepts list/tuple/range or numpy arrays; coerces to list[int]
      - Validates it's a *true permutation* of 0..n_tokens-1 with matching length.
    """
    if p is None:
        return None
    seq = _perm_as_sequence(p)
    ints = _perm_to_int_list(seq)

    if len(ints) != n_tokens:
        raise ValueError(f"TEXT_PERMUTATION must have length {n_tokens}, got {len(ints)}.")
    if len(set(ints)) != n_tokens:
        raise ValueError("TEXT_PERMUTATION must not contain duplicates.")
    if min(ints) != 0 or max(ints) != n_tokens - 1 or sorted(ints) != list(range(n_tokens)):
        raise ValueError("TEXT_PERMUTATION must be a permutation of 0..n_tokens-1.")
    return ints

def apply_permutation(tokens: Sequence[_T], perm: Optional[Sequence[int]]) -> list[_T]:
    """Apply permutation to tokens. If perm is None, returns list(tokens)."""
    if perm is None:
        return list(tokens)
    perm_list = _perm_to_int_list(_perm_as_sequence(perm))
    if len(perm_list) != len(tokens):
        raise ValueError(f"Permutation length {len(perm_list)} != token count {len(tokens)}.")
    return [tokens[i] for i in perm_list]

def invert_permutation(perm: Sequence[int]) -> list[int]:
    """Inverse permutation: perm ∘ inv == identity."""
    p = _perm_to_int_list(_perm_as_sequence(perm))
    n = len(p)
    inv = [0] * n
    for i, v in enumerate(p):
        if v < 0 or v >= n:
            raise ValueError(f"Permutation value out of range at index {i}: {v}")
        inv[v] = i
    return inv





def normalize_optimizer_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and flatten an optimiser spec into `{name, <canonical params...>}`.

    Accepts either `{name, params={...}}` or `{name, ...flat params...}`.
    """
    name = (spec.get("name") or "").lower()
    raw_params = spec.get("params") if isinstance(spec.get("params"), dict) else {
        k: v for k, v in spec.items() if k != "name"
    }
    flat = resolve_optimizer_aliases(name, dict(raw_params))
    return {"name": name, **flat}
