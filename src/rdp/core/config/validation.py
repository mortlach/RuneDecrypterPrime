from __future__ import annotations

from numbers import Integral
from typing import Any


def strict_positive_int(value: Any, field: str) -> int:
    """Apply the accepted strict-integer policy and require a positive value."""
    if isinstance(value, bool):
        raise TypeError(f"{field} must be an integer, not bool")
    if isinstance(value, Integral):
        result = int(value)
    elif isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            result = int(text)
        else:
            raise TypeError(f"{field} must be an integer")
    else:
        raise TypeError(f"{field} must be an integer")

    if result <= 0:
        raise ValueError(f"{field} must be greater than zero")
    return result


__all__ = ["strict_positive_int"]
