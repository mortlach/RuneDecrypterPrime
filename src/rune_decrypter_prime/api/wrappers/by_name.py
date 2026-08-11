from __future__ import annotations
from typing import Tuple, Dict, Callable, Any
from numbers import Integral

# Only import for type hints to avoid circular import at runtime
def _wrapper_int(value: Any, field: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{field} must be an integer, not bool")
    if isinstance(value, Integral):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            return int(text)
    raise TypeError(f"{field} must be an integer")


def _pull_N(kwargs: dict, default: int = 29) -> int:
    """Resolve the canonical alphabet-size aliases after conflict validation."""
    alphabet = kwargs.get("alphabet_size")
    legacy = kwargs.get("N")
    if alphabet is not None and legacy is not None:
        if _wrapper_int(alphabet, "alphabet_size") != _wrapper_int(legacy, "N"):
            raise ValueError("conflicting wrapper aliases: alphabet_size and N")
    value = alphabet if alphabet is not None else legacy
    return default if value is None else _wrapper_int(value, "alphabet_size")


_SCHEDULED_EXTRA_FIELDS = {
    "degeneracy", "per_pos_limit", "resolver_limit", "lookup",
    "alternating_start", "a_start", "b_start", "a_end", "b_end",
}

_WRAPPER_ALLOWED_FIELDS = {
    "vigenere": {"key_len", "default_key", "N", "alphabet_size", "resolver_limit"},
    "caesar": {"key_len", "default_key", "N", "alphabet_size", "resolver_limit"},
    "affine": {"key_len", "default_key", "degeneracy", "resolver", "per_pos_limit", "resolver_limit", "N", "alphabet_size"},
    "xor-mod": {"key_len", "default_key", "degeneracy", "resolver", "per_pos_limit", "resolver_limit", "N", "alphabet_size"},
    "beaufort": {"key_len", "default_key", "degeneracy", "resolver", "per_pos_limit", "resolver_limit", "N", "alphabet_size"},
    "variant-vigenere": {"key_len", "default_key", "degeneracy", "resolver", "per_pos_limit", "resolver_limit", "N", "alphabet_size"},
    "columnar": {"key_len", "key_length", "cols", "default_key"},
    "railfence": {"rails", "min_rails", "max_rails", "default_key"},
    "autokey": {"seed_len", "alphabet_size", "N", "default_key"},
    "route": {"cols", "default_key", "N", "alphabet_size", "resolver_limit"},
    "double_transposition": {"key_len1", "key_len2", "default_key", "N", "alphabet_size", "resolver_limit"},
    "blockperm": {"block_size", "default_key", "N", "alphabet_size", "resolver_limit"},
    "foursquare": {"default_key", "N", "alphabet_size", "resolver_limit"},
    "mono": {"key_len", "default_key", "N", "alphabet_size"},
    "substitution": {"key_len", "default_key", "N", "alphabet_size"},
    "periodic_substitution": {"period", "alphabet_size", "N", "default_key"},
    "periodic_columnar": {"period", "columns", "cols", "order", "alphabet_size", "N", "default_key"},
    "scheduled_stream_lookup": {"streams", "schedule", "operation", "mask", "alphabet_size", "N", "default_key", *_SCHEDULED_EXTRA_FIELDS},
    "periodic_plus_sequence": {"period", "sequence", "alphabet_size", "N", "default_key", *_SCHEDULED_EXTRA_FIELDS},
    "periodic_plus_primes": {"period", "prime_offset", "alphabet_size", "N", "default_key", *_SCHEDULED_EXTRA_FIELDS},
    "two_period_vigenere": {"period_a", "period_b", "alphabet_size", "N", "schedule", "mask", "default_key", *_SCHEDULED_EXTRA_FIELDS},
    "two_period_arithmetic": {"period_a", "period_b", "alphabet_size", "N", "operation", "schedule", "mask", "default_key", *_SCHEDULED_EXTRA_FIELDS},
}

_UNSUPPORTED_V1_WRAPPERS = {
    "hill": "Hill is not a supported RDP V1 production wrapper",
}


_WRAPPER_INTEGER_FIELDS = {
    "N", "alphabet_size", "key_len", "key_length", "cols",
    "rails", "min_rails", "max_rails", "seed_len",
    "key_len1", "key_len2", "block_size", "period", "columns",
    "per_pos_limit", "resolver_limit", "prime_offset", "period_a", "period_b",
    "a_start", "b_start", "a_end", "b_end",
}

_WRAPPER_POSITIVE_FIELDS = {
    "key_len", "key_length", "cols", "rails", "min_rails", "max_rails",
    "seed_len", "key_len1", "key_len2", "block_size", "period", "columns",
    "per_pos_limit", "resolver_limit", "period_a", "period_b",
}


def _normalise_wrapper_kwargs(name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    out = dict(kwargs)
    allowed = _WRAPPER_ALLOWED_FIELDS.get(name)
    if allowed is None:
        return out
    unknown = sorted(set(out) - allowed)
    if unknown:
        raise TypeError(f"{name} wrapper does not accept option(s): {unknown}")

    for field in sorted(set(out) & _WRAPPER_INTEGER_FIELDS):
        if out[field] is not None:
            out[field] = _wrapper_int(out[field], f"{name}.{field}")
    for field in sorted(set(out) & _WRAPPER_POSITIVE_FIELDS):
        if out[field] is not None and out[field] <= 0:
            raise ValueError(f"{name}.{field} must be > 0")
    if "default_key" in out and not isinstance(out["default_key"], bool):
        raise TypeError(f"{name}.default_key must be bool")

    if "N" in out and "alphabet_size" in out:
        if out["N"] is not None and out["alphabet_size"] is not None and out["N"] != out["alphabet_size"]:
            raise ValueError("conflicting wrapper aliases: N and alphabet_size")
        if out.get("alphabet_size") is None:
            out["alphabet_size"] = out.get("N")
        out.pop("N", None)
    elif "N" in out:
        out["alphabet_size"] = out.pop("N")

    if name == "caesar" and out.get("key_len") not in (None, 1):
        raise ValueError("caesar.key_len must be 1 when provided")
    if name == "railfence":
        rails = out.get("rails")
        min_rails = out.get("min_rails")
        max_rails = out.get("max_rails")
        if any(value is not None and value < 2 for value in (rails, min_rails, max_rails)):
            raise ValueError("railfence rails/min_rails/max_rails must be >= 2")
        if rails is not None:
            conflicts = [
                (field, value)
                for field, value in (("min_rails", min_rails), ("max_rails", max_rails))
                if value is not None and value != rails
            ]
            if conflicts:
                raise ValueError("conflicting railfence fixed rails and min/max bounds")
        elif min_rails is not None and max_rails is not None and min_rails > max_rails:
            raise ValueError("railfence min_rails cannot exceed max_rails")

    if name == "columnar":
        supplied = [(field, out[field]) for field in ("key_len", "key_length", "cols") if out.get(field) is not None]
        if supplied:
            values = {value for _field, value in supplied}
            if len(values) > 1:
                raise ValueError("conflicting columnar aliases: key_len/key_length/cols")
            value = supplied[0][1]
            out.pop("key_len", None); out.pop("cols", None)
            out["key_length"] = value
    if name == "periodic_columnar" and out.get("columns") is not None and out.get("cols") is not None:
        if out["columns"] != out["cols"]:
            raise ValueError("conflicting periodic_columnar aliases: columns and cols")
        out.pop("cols", None)
    return out


def _make_vigenere_like_spec(**kwargs):
    """
    Best-effort creation of a Vigenère *wrapper*. If the runtime doesn't expose
    CipherSpec.wrapper(core="vigenere"), gracefully fall back to a generic user_map2
    that implements ct = (pt + k) mod N.
    """
    from rune_decrypter_prime.api.specs import CipherSpec  # lazy import
    # Try the official wrapper constructor if present
    wrapper_ctor = getattr(CipherSpec, "wrapper", None)
    if callable(wrapper_ctor):
        return wrapper_ctor(core="vigenere")

    # Fallback to a user_map2 that behaves like Vigenère.
    N = _pull_N(kwargs)
    def f(pt: int, k: int) -> int:
        return (pt + k) % N
    resolver_limit_raw = kwargs.get("resolver_limit", 8193)
    resolver_limit = 8193 if resolver_limit_raw is None else int(resolver_limit_raw)
    return CipherSpec.user_map2(
        function=f,
        N=N,
        degeneracy="forbid",
        resolver="first",
        per_pos_limit=29,
        resolver_limit=resolver_limit,
    )


# API wrapper compatibility surface.
from types import SimpleNamespace as _NS
from typing import Union as _Union

from rune_decrypter_prime.ciphers import registry as _cipher_registry

def cipher_instance(spec_or_name: _Union[str, object], **overrides):
    """
    Materialise a concrete cipher instance from a name or CipherSpec.
    - If a name is given, build a minimal spec with that name, apply overrides, then construct.
    - If a CipherSpec is given, apply overrides to a shallow copy and construct.

    Returns: live cipher object implementing encrypt(...)/decrypt(...).
    """
    if isinstance(spec_or_name, str):
        name = spec_or_name
        spec = _NS(name=name)
    else:
        spec = spec_or_name
        name = getattr(spec, "name", None)
        if not name:
            raise ValueError("CipherSpec must have a 'name' attribute")

    if overrides:
        base = _NS(**getattr(spec, "__dict__", {}))
        for k, v in overrides.items():
            setattr(base, k, v)
        spec = base

    ctor = _cipher_registry.get(name)  # uses  cipher registry
    return ctor(spec)


class by_name:
    """
    UX registry for cipher wrappers. Every handler accepts **kwargs so callers
    can pass extra params without signature explosions (e.g., key_len, default_key, N).
    """

    @staticmethod
    def cipher_instance(name: str, **overrides):
        return cipher_instance(name, **overrides)

    @classmethod
    def cipher(cls, name: str, **kwargs) -> "CipherSpec":
        spec, _ = cls._get(name, **kwargs)
        return spec

    @classmethod
    def cipher_with_key(
        cls, name: str, **kwargs
    ) -> Tuple["CipherSpec", "KeySpec | tuple[KeySpec, KeySpec] | None"]:
        return cls._get(name, **kwargs)

    # ---------------- registry core ---------------- #

    @classmethod
    def _get(cls, name: str, **kwargs) -> Tuple["CipherSpec", "KeySpec | tuple[KeySpec, KeySpec] | None"]:
        key = name.lower().strip()
        if key in _UNSUPPORTED_V1_WRAPPERS:
            raise NotImplementedError(_UNSUPPORTED_V1_WRAPPERS[key])
        if key not in cls._REG:
            raise KeyError(f"Unknown cipher '{name}'. Available: {sorted(cls._REG)}")
        return cls._REG[key](**_normalise_wrapper_kwargs(key, kwargs))

    # ---------------- handlers ---------------- #
    # IMPORTANT: Lazy-import API spec types inside handlers to avoid circular imports.

    @staticmethod
    def _vigenere(*, key_len: int | None = None, default_key: bool = False, **kwargs: Any):
        """Vigenère wrapper → core 'vigenere' (or generic-map fallback)."""
        from rune_decrypter_prime.api.specs import KeySpec  # lazy
        spec = _make_vigenere_like_spec(**kwargs)
        key = KeySpec.repeat(len=key_len) if (default_key and key_len and key_len > 0) else None
        return spec, key

    @staticmethod
    def _caesar(*, key_len: int | None = None, default_key: bool = False, **kwargs: Any):
        """Caesar as period-1 Vigenère on the UX surface (uses same wrapper/fallback)."""
        from rune_decrypter_prime.api.specs import KeySpec  # lazy
        spec = _make_vigenere_like_spec(**kwargs)
        # ignore key_len; caesar is period 1
        key = KeySpec.repeat(len=1) if default_key else None
        return spec, key

    @staticmethod
    def _affine(
        *, key_len: int | None = None, default_key: bool = False,
        degeneracy: str = "forbid", resolver: str = "first", per_pos_limit: int = 29,
        resolver_limit: int = 8193, **kwargs: Any
    ):
        """
        Affine cipher: ct = (a * pt + b) mod N
        Implemented using generic user_map3 (pt, a, b) → ct.
        """
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy
        N = _pull_N(kwargs)
        def f(pt: int, a: int, b: int) -> int:
            return (a * pt + b) % N

        spec = CipherSpec.user_map3(
            function=f, N=N, degeneracy=degeneracy, resolver=resolver,
            per_pos_limit=per_pos_limit, resolver_limit=resolver_limit,
        )
        if default_key:
            L = key_len if (key_len and key_len > 0) else 1
            return spec, (KeySpec.repeat(len=L), KeySpec.repeat(len=L))
        return spec, None

    @staticmethod
    def _xor_mod(
        *, key_len: int | None = None, default_key: bool = False,
        degeneracy: str = "allow", resolver: str = "expand_beam", per_pos_limit: int = 29,
        resolver_limit: int = 8193, **kwargs: Any
    ):
        """'xor-mod' cipher: ct = (pt ^ k) % N."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return (pt ^ k) % N

        spec = CipherSpec.user_map2(
            function=f, N=N, degeneracy=degeneracy, resolver=resolver,
            per_pos_limit=per_pos_limit, resolver_limit=resolver_limit,
        )
        key = KeySpec.repeat(len=key_len) if (default_key and key_len and key_len > 0) else None
        return spec, key

    @staticmethod
    def _beaufort(
        *, key_len: int | None = None, default_key: bool = False,
        degeneracy: str = "forbid", resolver: str = "first", per_pos_limit: int = 29,
        resolver_limit: int = 8193, **kwargs: Any
    ):
        """Classical Beaufort: ct = (k - pt) mod N"""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return (k - pt) % N

        spec = CipherSpec.user_map2(
            function=f, N=N, degeneracy=degeneracy, resolver=resolver,
            per_pos_limit=per_pos_limit, resolver_limit=resolver_limit,
        )
        key = KeySpec.repeat(len=key_len) if (default_key and key_len and key_len > 0) else None
        return spec, key

    @staticmethod
    def _variant_vigenere(
        *, key_len: int | None = None, default_key: bool = False,
        degeneracy: str = "forbid", resolver: str = "first", per_pos_limit: int = 29,
        resolver_limit: int = 8193, **kwargs: Any
    ):
        """Variant Vigenère (aka Beaufort-variant): ct = (pt - k) mod N"""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return (pt - k) % N

        spec = CipherSpec.user_map2(
            function=f, N=N, degeneracy=degeneracy, resolver=resolver,
            per_pos_limit=per_pos_limit, resolver_limit=resolver_limit,
        )
        key = KeySpec.repeat(len=key_len) if (default_key and key_len and key_len > 0) else None
        return spec, key

    @staticmethod
    def _hill(*, key_n: int | None = None, default_key: bool = False, **kwargs: Any):
        """
        Hill cipher wrapper. 'key_n' is the matrix size n (key length = n*n).
        Falls back to n=2 if not provided.
        """
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy import
        n = int(key_n) if key_n and key_n > 1 else 2
        N = _pull_N(kwargs)  # alphabet size, defaults to 29

        # Prefer a concrete core wrapper if present; otherwise just name it "hill".
        # api.py exposes an internal '_wrapper' builder, we reuse it for consistency.
        spec = getattr(CipherSpec, "_wrapper")(name="hill", core_name="hill", N=N)

        key = KeySpec.matrix(n=n, A=N) if default_key else None
        return spec, key


    # @staticmethod
    # def _columnar(
    #     *, key_len: int | None = None, default_key: bool = False,
    #     degeneracy: str = "forbid", resolver: str = "first", per_pos_limit: int = 1, **kwargs: Any
    # ):
    #     """Columnar transposition: values unchanged, positions permuted."""
    #     from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
    #     N = _pull_N(kwargs)
    #     def f(pt: int, k: int) -> int:
    #         return pt
    #     spec = CipherSpec.user_map2(function=f, N=N,
    #                                 degeneracy=degeneracy, resolver=resolver,
    #                                 per_pos_limit=per_pos_limit)
    #     # todo add this to other ciphers
    #     key = KeySpec.permutation(key_len) if (default_key and key_len and key_len > 0) else None
    #     return spec, key

    @staticmethod
    def _railfence(
        *,
        rails: int | None = None,
        min_rails: int | None = None,
        max_rails: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Railfence cipher: scalar key controlling the number of rails."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec

        spec = CipherSpec._wrapper(name="railfence", core_name="railfence")
        extras = spec.extra

        if rails is not None:
            fixed = int(rails)
            if fixed < 2:
                raise ValueError("railfence requires rails >= 2")
            extras["rails"] = fixed
            extras["min_rails"] = fixed
            extras["max_rails"] = fixed
        else:
            min_hint = max(2, int(min_rails) if min_rails is not None else 2)
            if max_rails is None:
                max_hint = max(min_hint, 8)
            else:
                max_hint = max(min_hint, int(max_rails))
            extras["min_rails"] = min_hint
            extras["max_rails"] = max_hint

        key = KeySpec.scalar(max_val=extras["max_rails"]) if default_key else None
        return spec, key

    @staticmethod
    def _autokey(
        *,
        seed_len: int | None = None,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Autokey cipher: search over the seed of length `seed_len`."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec

        seed = int(seed_len) if seed_len is not None else 3
        if seed <= 0:
            raise ValueError("autokey requires seed_len >= 1")
        alphabet = int(alphabet_size) if alphabet_size is not None else 29
        if alphabet <= 0:
            raise ValueError("autokey alphabet_size must be positive")

        spec = CipherSpec._wrapper(name="autokey", core_name="autokey", N=alphabet)
        spec.extra["seed_length"] = seed
        spec.extra["alphabet_size"] = alphabet

        key = KeySpec.repeat(len=seed) if default_key else None
        return spec, key

    @staticmethod
    def _route(
        *, cols: int | None = None, default_key: bool = False, **kwargs: Any
    ):
        """Route cipher: permute column order in a grid."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return pt
        resolver_limit_raw = kwargs.get("resolver_limit", 8193)
        resolver_limit = 8193 if resolver_limit_raw is None else int(resolver_limit_raw)
        spec = CipherSpec.user_map2(
            function=f, N=N,
            degeneracy="forbid", resolver="first",
            per_pos_limit=29, resolver_limit=resolver_limit,
        )
        #key = KeySpec.permutation(cols) if (default_key and cols and cols > 0) else None
        key = KeySpec.permutation(len=int(cols)) if (default_key and cols and cols > 0) else None
        return spec, key

    @staticmethod
    def _double_transposition(
        *, key_len1: int | None = None, key_len2: int | None = None,
        default_key: bool = False, **kwargs: Any
    ):
        """Double transposition: two permutations applied in sequence."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return pt
        resolver_limit_raw = kwargs.get("resolver_limit", 8193)
        resolver_limit = 8193 if resolver_limit_raw is None else int(resolver_limit_raw)
        spec = CipherSpec.user_map2(
            function=f, N=N,
            degeneracy="forbid", resolver="first",
            per_pos_limit=29, resolver_limit=resolver_limit,
        )
        if default_key and key_len1 and key_len2:
            return spec, (KeySpec.permutation(len=int(key_len1)), KeySpec.permutation(len=int(key_len2)))
        return spec, None

    @staticmethod
    def _blockperm(
        *, block_size: int | None = None, default_key: bool = False, **kwargs: Any
    ):
        """Block permutation cipher: permute letters inside fixed-size blocks."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        N = _pull_N(kwargs)
        def f(pt: int, k: int) -> int:
            return pt
        resolver_limit_raw = kwargs.get("resolver_limit", 8193)
        resolver_limit = 8193 if resolver_limit_raw is None else int(resolver_limit_raw)
        spec = CipherSpec.user_map2(
            function=f, N=N,
            degeneracy="forbid", resolver="first",
            per_pos_limit=29, resolver_limit=resolver_limit,
        )
        #key = KeySpec.permutation(block_size) if (default_key and block_size and block_size > 0) else None
        key = KeySpec.permutation(len=int(block_size)) if (default_key and block_size and block_size > 0) else None
        return spec, key

    @staticmethod
    def _foursquare(
        *, default_key: bool = False, **kwargs: Any
    ):
        """Four-square cipher: two keyword squares (two permutations of 25)."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        N = _pull_N(kwargs)
        def f(p1: int, p2: int, k1: list[int], k2: list[int]) -> tuple[int,int]:
            return (p1, p2)
        resolver_limit_raw = kwargs.get("resolver_limit", 8193)
        resolver_limit = 8193 if resolver_limit_raw is None else int(resolver_limit_raw)
        spec = CipherSpec.user_map3(
            function=f, N=N,
            degeneracy="allow", resolver="expand_beam",
            per_pos_limit=29, resolver_limit=resolver_limit,
        )
        if default_key:
            return spec, (KeySpec.permutation(len=25), KeySpec.permutation(len=25))
        return spec, None

    @staticmethod
    def _columnar(
        *, key_len: int | None = None, key_length: int | None = None, cols: int | None = None,
        default_key: bool = False, **kwargs: Any
    ):
        """
        Columnar transposition wrapper. Accepts either `key_len` or `key_length`
        so callers can provide the permutation width irrespective of the alias.
        The resolved length is stored in `spec.extra` for direct cipher_instance()
        use (encryption previews/tests) where no CipherConfig exists yet.
        """
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec

        spec = CipherSpec._wrapper(name="columnar", core_name="columnar")
        cols = key_length if key_length is not None else (key_len if key_len is not None else cols)
        if cols is not None:
            cols = int(cols)
            if cols > 0:
                if cols > 255:
                    raise ValueError("columnar requires columns <= 255 (uint8 key limit)")
                spec.extra["key_length"] = cols
        key = None
        if default_key and cols and cols > 0:
            key = KeySpec.permutation(len=cols)
        return spec, key

    @staticmethod
    def _mono(*, key_len: int | None = None, default_key: bool = False, **kwargs: Any):
        """
        Monoalphabetic substitution (permutation of N symbols).
        UX wrapper that targets the core 'substitution' cipher.
        """
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec  # lazy
        N = _pull_N(kwargs)
        spec = CipherSpec._wrapper(name="substitution", core_name="substitution", N=N)
        # For mono, a “key” is a permutation of the alphabet (length = N)
        if default_key:
            L = key_len if (key_len and key_len > 0) else N
            return spec, KeySpec.permutation(len=L)
        return spec, None

    @staticmethod
    def _periodic_substitution(
        *,
        period: int | None = None,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Periodic substitution cipher wrapper."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        if period is None or int(period) <= 0:
            raise ValueError("periodic_substitution requires period >= 1")
        A = int(alphabet_size) if alphabet_size is not None else _pull_N(kwargs)
        if A <= 0:
            raise ValueError("periodic_substitution requires alphabet_size >= 1")

        spec = CipherSpec._wrapper(name="periodic_substitution", core_name="periodic_substitution", N=A)
        spec.extra["period"] = int(period)
        spec.extra["alphabet_size"] = int(A)

        key = KeySpec.periodic_substitution(period=int(period), alphabet_size=int(A)) if default_key else None
        return spec, key

    @staticmethod
    def _periodic_columnar(
        *,
        period: int | None = None,
        columns: int | None = None,
        cols: int | None = None,
        order: str | None = None,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Periodic substitution + columnar transposition wrapper."""
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec
        if period is None or int(period) <= 0:
            raise ValueError("periodic_columnar requires period >= 1")
        col_raw = columns if columns is not None else cols
        if col_raw is None or int(col_raw) <= 0:
            raise ValueError("periodic_columnar requires columns >= 1")
        if int(col_raw) > 255:
            raise ValueError("periodic_columnar requires columns <= 255 (uint8 column limit)")
        A = int(alphabet_size) if alphabet_size is not None else _pull_N(kwargs)
        if A <= 0:
            raise ValueError("periodic_columnar requires alphabet_size >= 1")

        spec = CipherSpec._wrapper(name="periodic_columnar", core_name="periodic_columnar", N=A)
        spec.extra["period"] = int(period)
        spec.extra["columns"] = int(col_raw)
        spec.extra["alphabet_size"] = int(A)
        spec.extra["order"] = str(order or "sub_then_col")

        key = (
            KeySpec.periodic_columnar(period=int(period), columns=int(col_raw), alphabet_size=int(A))
            if default_key
            else None
        )
        return spec, key

    @staticmethod
    def _scheduled_stream_lookup(
        *,
        streams,
        schedule: str = "overlay",
        operation: str = "add",
        mask=None,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Generic scheduled stream lookup wrapper.

        This is the public wrapper for the real engine cipher. Preset aliases
        below only build this same wrapper with convenient defaults.
        """
        from rune_decrypter_prime.api.specs import CipherSpec, KeySpec

        A = int(alphabet_size) if alphabet_size is not None else _pull_N(kwargs)
        spec = CipherSpec._wrapper(
            name="scheduled_stream_lookup",
            core_name="scheduled_stream_lookup",
            N=A,
        )
        spec.extra["streams"] = list(streams)
        spec.extra["schedule"] = str(schedule)
        spec.extra["operation"] = str(operation)
        spec.extra["alphabet_size"] = A
        if mask is not None:
            spec.extra["mask"] = list(mask)

        # Preserve scheduled-stream knobs instead of silently dropping them.
        for field in (
            "degeneracy", "per_pos_limit", "resolver_limit", "lookup",
            "alternating_start", "a_start", "b_start", "a_end", "b_end",
        ):
            if field in kwargs and kwargs[field] is not None:
                spec.extra[field] = kwargs[field]

        key_length = 0
        for stream in spec.extra["streams"]:
            if not isinstance(stream, dict):
                continue
            kind = str(stream.get("kind", "periodic")).strip().lower()
            if kind in {"sequence", "known_sequence", "fixed_sequence"}:
                kind = "fixed"
            if kind == "periodic":
                key_length += int(stream.get("period", 0))
            elif kind not in {"fixed", "primes", "prime"}:
                raise ValueError(f"unknown stream kind {kind!r}")
        key = KeySpec.repeat(len=key_length) if default_key and key_length > 0 else None
        return spec, key

    @staticmethod
    def _periodic_plus_primes(
        *,
        period: int = 13,
        prime_offset: int = 0,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Preset alias: unknown periodic stream plus generated prime stream."""
        streams = [
            {"name": "A", "kind": "periodic", "period": int(period)},
            {"name": "P", "kind": "primes", "offset": int(prime_offset)},
        ]
        return by_name._scheduled_stream_lookup(
            streams=streams,
            schedule="overlay",
            operation="add",
            alphabet_size=alphabet_size,
            default_key=default_key,
            **kwargs,
        )

    @staticmethod
    def _periodic_plus_sequence(
        *,
        period: int = 13,
        sequence=None,
        alphabet_size: int | None = None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Preset alias: unknown periodic stream plus caller-supplied sequence."""
        if sequence is None:
            raise ValueError("periodic_plus_sequence requires sequence=[...]")
        streams = [
            {"name": "A", "kind": "periodic", "period": int(period)},
            {
                "name": "S",
                "kind": "sequence",
                "values": [_wrapper_int(v, "periodic_plus_sequence.sequence") for v in sequence],
            },
        ]
        return by_name._scheduled_stream_lookup(
            streams=streams,
            schedule="overlay",
            operation="add",
            alphabet_size=alphabet_size,
            default_key=default_key,
            **kwargs,
        )

    @staticmethod
    def _two_period_vigenere(
        *,
        period_a: int = 13,
        period_b: int = 31,
        alphabet_size: int | None = None,
        schedule: str = "overlay",
        mask=None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Preset alias: two unknown periodic streams combined additively."""
        streams = [
            {"name": "A", "kind": "periodic", "period": int(period_a)},
            {"name": "B", "kind": "periodic", "period": int(period_b)},
        ]
        return by_name._scheduled_stream_lookup(
            streams=streams,
            schedule=schedule,
            operation="add",
            mask=mask,
            alphabet_size=alphabet_size,
            default_key=default_key,
            **kwargs,
        )

    @staticmethod
    def _two_period_arithmetic(
        *,
        period_a: int = 13,
        period_b: int = 31,
        alphabet_size: int | None = None,
        operation: str = "add_sub",
        schedule: str = "overlay",
        mask=None,
        default_key: bool = False,
        **kwargs: Any,
    ):
        """Preset alias: two unknown periodic streams with selectable arithmetic."""
        streams = [
            {"name": "A", "kind": "periodic", "period": int(period_a)},
            {"name": "B", "kind": "periodic", "period": int(period_b)},
        ]
        return by_name._scheduled_stream_lookup(
            streams=streams,
            schedule=schedule,
            operation=operation,
            mask=mask,
            alphabet_size=alphabet_size,
            default_key=default_key,
            **kwargs,
        )

    _REG: Dict[str, Callable[..., Tuple["CipherSpec", "KeySpec | tuple[KeySpec, KeySpec] | None"]]] = {
        "vigenere": _vigenere.__func__,
        "caesar": _caesar.__func__,
        "affine": _affine.__func__,
        "xor-mod": _xor_mod.__func__,
        "beaufort": _beaufort.__func__,
        "variant-vigenere": _variant_vigenere.__func__,
        "columnar": _columnar.__func__,
        "railfence": _railfence.__func__,
        "autokey": _autokey.__func__,
        "route": _route.__func__,
        "double_transposition": _double_transposition.__func__,
        "blockperm": _blockperm.__func__,
        "foursquare": _foursquare.__func__,
        "mono": _mono.__func__,
        "substitution": _mono.__func__,
        "periodic_substitution": _periodic_substitution.__func__,
        "periodic_columnar": _periodic_columnar.__func__,
        "scheduled_stream_lookup": _scheduled_stream_lookup.__func__,
        "periodic_plus_sequence": _periodic_plus_sequence.__func__,
        "periodic_plus_primes": _periodic_plus_primes.__func__,
        "two_period_vigenere": _two_period_vigenere.__func__,
        "two_period_arithmetic": _two_period_arithmetic.__func__,
    }
