from __future__ import annotations

import re

from rune_decrypter_prime.data.liber_primus.lp_registry import LPPageRef


_CANON_JPG_RE = re.compile(r"^(?P<num>\d+)\.jpg$", re.IGNORECASE)
_BOUND_PAGE_RE = re.compile(r"^(?:page\s*|p)(?P<num>\d+)$", re.IGNORECASE)
_CANON_NUM_RE = re.compile(r"^(?P<num>\d+)$")


def parse_page_token(token: str) -> LPPageRef:
    value = token.strip()
    if not value:
        raise ValueError("token must be non-empty")

    jpg_match = _CANON_JPG_RE.match(value)
    if jpg_match:
        return LPPageRef.canon_page(int(jpg_match.group("num")))

    compact = value.replace(" ", "")
    bound_match = _BOUND_PAGE_RE.match(compact)
    if bound_match:
        return LPPageRef.bound_book_page(int(bound_match.group("num")))

    canon_num_match = _CANON_NUM_RE.match(value)
    if canon_num_match:
        return LPPageRef.canon_page(int(canon_num_match.group("num")))

    raise ValueError(f"Unsupported page token: {token!r}")


__all__ = ["parse_page_token"]
