# ============================================================
# rune_decrypter_prime/api/maps_api.py
#   Consolidated UX helpers for user-defined maps and lookup ciphers
# ============================================================
from __future__ import annotations
from typing import Any, Callable, Dict, Optional, Tuple, Union, Sequence
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig, RunConfig, SolverConfig
from rune_decrypter_prime.core.types import KEY_DTYPE
from rune_decrypter_prime.api.specs import CipherSpec, KeySpec, SolverSpec  # reuse canonical classes
from rune_decrypter_prime.api.normalize import to_indices, make_single_word_wli
from rune_decrypter_prime.api.wrappers import by_name
# Ensure generic cipher is registered
import rune_decrypter_prime.ciphers.generic_map_cipher  # noqa: F401


# ----------------------------- builders ----------------------------- #

def define_map(*, N: int = 29,
               function: Optional[Callable[..., int]] = None,
               table: Optional[Any] = None,
               degeneracy: str = "forbid",
               resolver: str = "expand_beam",
               per_pos_limit: int = 29,
               resolver_limit: int = 8193,
               name: Optional[str] = None) -> CipherSpec:
    """Define a user map or lookup table → `CipherSpec`.
    Exactly one of `function` or `table` must be provided.
    """
    if (function is None) == (table is None):
        raise ValueError("Provide exactly one of function or table.")

    if function is not None:
        import inspect
        n = len(inspect.signature(function).parameters)
        if n == 2:
            return CipherSpec.user_map2(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit,
                                        resolver_limit=resolver_limit, name=name or "user_map2")
        if n == 3:
            return CipherSpec.user_map3(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit,
                                        resolver_limit=resolver_limit, name=name or "user_map3")
        raise ValueError("function must accept (pt,k) or (pt,k1,k2)")

    # table path
    return CipherSpec.from_lookup(table=table, N=N, degeneracy=degeneracy,
                                  resolver=resolver, per_pos_limit=per_pos_limit,
                                  resolver_limit=resolver_limit, name=name or "lookup")


def define_cipher(
    *,
    spec: CipherSpec | None = None,
    name: str | None = None,
    key: Optional[KeySpec] = None,
    key_len: Optional[int] = None,
    **kwargs: Any,
) -> Tuple[CipherSpec, KeySpec]:
    """
    Convenience: return `(CipherSpec, KeySpec)`.

    Usage patterns:
        define_cipher(spec=my_spec, key=KeySpec.repeat(...))
        define_cipher(spec=my_spec, key_len=3)
        define_cipher(name="columnar", default_key=True, key_len=6)

    When `name` is provided, the handler looks up the registered UX wrapper
    (via `by_name`) so callers get the same spec/key defaults as the tutorials.
    """
    if (spec is None) == (name is None) is False:
        raise ValueError("Provide exactly one of 'spec' or 'name'.")

    if name is not None:
        spec_obj, default_key = by_name.cipher_with_key(name, **kwargs)
        if key is not None:
            return spec_obj, key
        if default_key is not None:
            return spec_obj, default_key
        L = int(key_len) if key_len is not None else 1
        return spec_obj, KeySpec.repeat(len=L)

    if spec is None:
        raise ValueError("define_cipher requires either 'spec' or 'name'.")

    if key is not None:
        return spec, key
    L = int(key_len) if key_len is not None else 1
    return spec, KeySpec.repeat(len=L)


# ------------------------------ preview ------------------------------ #

def preview(
    text: Union[str, np.ndarray, Sequence[int]],
    *,
    cipher: CipherSpec,
    key: KeySpec,
    direction: str = "decrypt",  # or "encrypt"
    text_encoding_direction: str = "ltr",  # pipeline knob (no hidden default)
    device: str = "cpu",
) -> np.ndarray:
    """Preview a user map cipher with a fully specified key (OTP/const).

    Returns: plaintext/ciphertext indices (np.uint8, shape (L,)).
    - For `otp`: uses provided `stream` (resized to L if needed).
    - For `const`: broadcasts a constant of length L.
    """
    arr = to_indices(text)
    L = int(arr.size)

    # materialise key
    if key.plan == "otp":
        stream = key.params.get("stream", None)
        if stream is None:
            raise ValueError("OTP KeySpec requires 'stream' parameter.")
        k = np.asarray(stream, dtype=KEY_DTYPE).reshape(-1)
    elif key.plan == "const":
        val = int(key.params.get("value", 0))
        k = np.full(L, val, dtype=KEY_DTYPE)
    else:
        raise ValueError("preview requires KeySpec.otp(.) or KeySpec.const(.)")

    if k.size < L:
        k = np.resize(k, L)
    elif k.size > L:
        k = k[:L]

    from rune_decrypter_prime.core.factory import build_solver  # lazy import to avoid circulars
    cfg = CipherConfig(
        ciphertext=np.zeros(L, dtype=np.uint8),
        wli_data=[],
        key_length=int(k.size if cipher.kind != "user_map3" else 1),
        text_transposition=text_encoding_direction,
        device=device,
        name=(cipher.kind if cipher.kind in ("user_map2", "user_map3", "lookup") else "generic-map"),
    )
    setattr(cfg, "spec", cipher)

    # Optimiser fast-path: test_key returns single decrypt w/o search
    opt = SolverConfig(name="beam", params={"beam_width": 1, "test_key": k.tolist()})
    run_cfg = RunConfig(cipher=cfg, scorer_name="rune",
                        scorer_params={"objective": "pct.logp.win10", "n_char": 2, "n_wli": 2, "win": 10,
                                       "use_word_breaks": False, "wli_weights": {}},
                        solver=opt, logging={})
    engine = build_solver(run_cfg)

    # Directly use the instantiated cipher for transform
    cipher_impl = getattr(engine, "cipher", engine)
    if direction.lower() == "decrypt":
        out = cipher_impl.decrypt(ciphertext=arr, key=k)
    elif direction.lower() == "encrypt":
        out = cipher_impl.encrypt(plaintext=arr, key=k)
    else:
        raise ValueError("direction must be 'decrypt' or 'encrypt'.")

    result_idx = out[0] if isinstance(out, tuple) else out
    return np.asarray(result_idx, dtype=np.uint8).reshape(-1)
