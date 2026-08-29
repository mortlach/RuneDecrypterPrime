from __future__ import annotations

from typing import Tuple, Union

from rdp.api.specs import CipherSpec, KeySpec


def resolve_cipher_kind(cipher: CipherSpec) -> str:
    kind = getattr(cipher, "kind", None)
    if not kind:
        raise ValueError("CipherSpec must define a 'kind' attribute")
    return str(kind)


def resolve_key_length(key_spec: Union[KeySpec, Tuple[KeySpec, KeySpec]], ciphertext_len: int) -> int:
    if isinstance(key_spec, tuple):
        return 1
    if not isinstance(key_spec, KeySpec):
        raise TypeError("Expected KeySpec when resolving key length")

    plan = key_spec.plan
    if plan == "repeat":
        length = int(key_spec.params.get("len", 0) or 0)
    elif plan in {"perm", "otp", "keystream", "const"}:
        length = int(ciphertext_len)
    elif plan == "scalar":
        length = 1
    elif plan == "periodic_structured":
        period = int(key_spec.params.get("period", 0) or 0)
        A = int(key_spec.params.get("alphabet_size", 29) or 29)
        columns = key_spec.params.get("columns", None)
        if period <= 0:
            raise ValueError("periodic_structured requires period >= 1")
        if A <= 0:
            raise ValueError("periodic_structured requires alphabet_size >= 1")
        if columns is None:
            length = int(period * A)
        else:
            columns = int(columns)
            if columns <= 0:
                raise ValueError("periodic_structured requires columns >= 1")
            length = int(period * A + columns)
    else:
        length = int(key_spec.params.get("len", 1) or 1)

    if length <= 0:
        raise ValueError(f"Unable to infer key length for plan '{plan}'")
    return length


def expect_key_plan(key_spec: KeySpec, plan: str, message: str) -> KeySpec:
    if not isinstance(key_spec, KeySpec) or key_spec.plan != plan:
        raise ValueError(message)
    return key_spec
