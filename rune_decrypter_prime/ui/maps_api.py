# ============================================================
# rune_decrypter_prime/ui/maps_api.py
#   High-level UX helpers for user-defined maps and lookup ciphers
# ============================================================
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple, Union
import numpy as np

from rune_decrypter_prime.core.config import CipherConfig, RunConfig, OptimizerConfig
from rune_decrypter_prime.core.factory import build_solver
from rune_decrypter_prime.ui.api import CipherSpec, KeySpec, SolveSpec  # reuse canonical classes
# Ensure generic cipher is registered
import rune_decrypter_prime.ciphers.generic_map_cipher  # noqa: F401


def define_map(*, N: int = 29,
               function: Optional[Callable[..., int]] = None,
               table: Optional[Any] = None,
               degeneracy: str = "forbid",
               resolver: str = "first",
               per_pos_limit: int = 1,
               name: Optional[str] = None) -> CipherSpec:
    """
    Define a user map or lookup table.
    Returns a CipherSpec consistent with ui.api contracts.
    """
    if function is not None and table is not None:
        raise ValueError("Provide either function or table, not both.")
    if function is not None:
        import inspect
        n = len(inspect.signature(function).parameters)
        if n == 2:
            return CipherSpec.user_map2(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit, name=name or "user_map2")
        elif n == 3:
            return CipherSpec.user_map3(function=function, N=N, degeneracy=degeneracy,
                                        resolver=resolver, per_pos_limit=per_pos_limit, name=name or "user_map3")
        else:
            raise ValueError("function must accept (pt,k) or (pt,k1,k2)")
    if table is not None:
        return CipherSpec.from_lookup(table=table, N=N, degeneracy=degeneracy,
                                      resolver=resolver, per_pos_limit=per_pos_limit, name=name or "lookup")
    raise ValueError("Either function or table must be provided.")


def define_cipher(*, spec: CipherSpec, key: Optional[KeySpec] = None, key_len: Optional[int] = None
                 ) -> Tuple[CipherSpec, KeySpec]:
    """
    Convenience: returns (CipherSpec, KeySpec).
    If key is omitted, build KeySpec.repeat(len=key_len) or default 1.
    """
    if key is not None:
        return spec, key
    L = int(key_len) if key_len is not None else 1
    return spec, KeySpec.repeat(len=L)


def _normalize_text(text: Union[str, np.ndarray, list, tuple]) -> np.ndarray:
    # Accept int indices array directly
    if isinstance(text, np.ndarray) and text.dtype == np.uint8:
        return text.reshape(-1)
    if isinstance(text, (list, tuple)):
        arr = np.asarray(text, dtype=np.uint8).reshape(-1)
        return arr
    # If string, naive mapping by digit groups (tests/examples use indices anyway)
    import re
    toks = re.findall(r"\d+", str(text))
    if not toks:
        return np.zeros((0,), dtype=np.uint8)
    vals = [int(t) for t in toks]
    return np.asarray(vals, dtype=np.uint8).reshape(-1)


def preview(text: Union[str, np.ndarray, list, tuple], *, cipher: CipherSpec, key: KeySpec,
            direction: str = "decrypt", device: str = "cpu") -> np.ndarray:
    """
    Preview with a fully specified key (OTP/const). Returns indices.
    """
    arr = _normalize_text(text)
    L = int(arr.size)

    # materialize key
    if key.plan == "otp":
        stream = key.params.get("stream", None)
        if stream is None:
            raise ValueError("OTP KeySpec requires 'stream' parameter.")
        k = np.asarray(stream, dtype=np.uint8).reshape(-1)
    elif key.plan == "const":
        val = int(key.params.get("value", 0))
        k = np.full(L, val, dtype=np.uint8)
    else:
        raise ValueError("preview requires KeySpec.otp(...) or KeySpec.const(...)")

    if k.size < L:
        k = np.resize(k, L)
    elif k.size > L:
        k = k[:L]

    cfg = CipherConfig(
        ciphertext=np.zeros(L, dtype=np.uint8),
        wli_data=[[0, L]],
        key_length=int(k.size if cipher.kind != "user_map3" else 1),
        text_transposition="fwd",
        device=device,
        name=(cipher.kind if cipher.kind in ("user_map2","user_map3","lookup") else "generic-map"),
    )
    setattr(cfg, "spec", cipher)

    # Optimizer fast-path: test_key returns single decrypt w/o search
    opt = OptimizerConfig(name="beam", params={"beam_width": 1, "test_key": k.tolist()})
    run_cfg = RunConfig(cipher=cfg, scorer_name="rune", scorer_params={"objective":"pct.logp.win10","n_char":2,"n_wli":2,"win":10},
                        optimizer=opt, logging={})
    engine = build_solver(run_cfg)
    sol = engine.solve()
    return np.asarray(sol.plaintext_idx, dtype=np.uint8)


class run_map:
    """
    High-level runner for user-defined maps.
    Usage:
        spec = define_map(function=my_f)  # or from_lookup(...)
        key  = KeySpec.repeat(len=5)
        sol  = run_map.solve(text=ct, cipher=spec, key=key, solve=SolveSpec.beam(8))
    """
    @classmethod
    def solve(cls,
              text: Union[str, np.ndarray, list, tuple],
              cipher: CipherSpec,
              key: Union[KeySpec, Tuple[KeySpec, KeySpec]],
              solve: SolveSpec,
              *,
              device: str = "cpu",
              scorer: str = "rune",
              scorer_params: Optional[Dict[str, Any]] = None,
              logging: Optional[Dict[str, Any]] = None):
        arr = _normalize_text(text)
        L = int(arr.size)

        if cipher.kind == "user_map3":
            if not isinstance(key, tuple) or len(key) != 2:
                raise ValueError("user_map3 expects a tuple of two KeySpec with equal lengths.")
            k1, k2 = key
            p1 = k1.period_hint(); p2 = k2.period_hint()
            if not p1 or not p2 or int(p1) <= 0 or int(p2) <= 0 or int(p1) != int(p2):
                raise ValueError("user_map3 requires KeySpec.repeat(len=K) for both keys (equal K).")
            K = int(p1)
        else:
            if isinstance(key, tuple):
                raise ValueError(f"{cipher.kind} expects a single KeySpec.")
            K = key.period_hint()
            if not K or int(K) <= 0:
                if key.plan in ("otp","const"):
                    K = None
                else:
                    raise ValueError(f"{cipher.kind} requires KeySpec.repeat(len=K) with K>0.")
            else:
                K = int(K)

        # Known-key fast path (otp/const)
        if not isinstance(key, tuple) and key.plan in ("otp","const"):
            if key.plan == "otp":
                stream = key.params.get("stream", None)
                if stream is None:
                    raise ValueError("OTP KeySpec requires 'stream' parameter.")
                k = np.asarray(stream, dtype=np.uint8).reshape(-1)
            else:
                val = int(key.params.get("value", 0))
                k = np.full(L, val, dtype=np.uint8)
            if k.size < L: k = np.resize(k, L)
            if k.size > L: k = k[:L]
            cfg = CipherConfig(ciphertext=arr, wli_data=[[0,L]], key_length=int(k.size),
                               text_transposition="fwd", device=device, name=cipher.kind)
            setattr(cfg, "spec", cipher)
            opt = OptimizerConfig(name="beam", params={"beam_width": 1, "test_key": k.tolist()})
            rcfg = RunConfig(cipher=cfg, scorer_name=scorer, scorer_params=(scorer_params or {
                "objective":"pct.logp.win10","n_char":2,"n_wli":2,"win":10}),
                optimizer=opt, logging=(logging or {}))
            return build_solver(rcfg).solve()

        # Search path
        cfg = CipherConfig(ciphertext=arr, wli_data=[[0,L]], key_length=int(K), text_transposition="fwd",
                           device=device, name=cipher.kind)
        setattr(cfg, "spec", cipher)
        opt = OptimizerConfig(name=solve.name, params=dict(solve.params))
        sc = dict(scorer_params or {})
        sc.setdefault("objective","pct.logp.win10"); sc.setdefault("n_char",2)
        sc.setdefault("n_wli",2); sc.setdefault("win",10)

        rcfg = RunConfig(cipher=cfg, scorer_name=scorer, scorer_params=sc, optimizer=opt, logging=(logging or {}))
        return build_solver(rcfg).solve()
