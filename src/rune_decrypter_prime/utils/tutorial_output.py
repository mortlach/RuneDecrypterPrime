from __future__ import annotations

from collections.abc import Sequence

from rdp.api.display import PrintOptions, format_key_value_block, print_block
from rune_decrypter_prime.core.types import Direction, ensure_direction
from rune_decrypter_prime.utils.runeglish import Runeglish


DEFAULT_DEBUG_PREVIEW_TOKENS = 80


def print_tutorial_debug_preview(
    *,
    label: str,
    idx: Sequence[int],
    wli: Sequence[Sequence[int]] | None,
    direction: Direction | str,
    token_limit: int = DEFAULT_DEBUG_PREVIEW_TOKENS,
) -> None:
    """Print an unambiguous tutorial text preview using the standard style."""
    print_block(
        tutorial_debug_preview_block(
            label=label,
            idx=idx,
            wli=wli,
            direction=direction,
            token_limit=token_limit,
        )
    )


def tutorial_debug_preview_block(
    *,
    label: str,
    idx: Sequence[int],
    wli: Sequence[Sequence[int]] | None,
    direction: Direction | str,
    token_limit: int = DEFAULT_DEBUG_PREVIEW_TOKENS,
    options: PrintOptions | None = None,
) -> str:
    """Return a sectioned debug preview for tutorial/review output."""
    direction_value = ensure_direction(direction)
    idx_values = [int(value) for value in idx]
    if token_limit < 1:
        raise ValueError("token_limit must be >= 1")

    clipped = idx_values[:token_limit]
    suffix = "" if len(idx_values) <= token_limit else f" ... <{len(idx_values) - token_limit} more>"
    return format_key_value_block(
        f"Debug preview: {label}",
        [
            ("encoding_dir", direction_value.value),
            ("latin_tokens", f"{_token_text(clipped, wli)}{suffix}"),
            ("rune_indices", f"{clipped}{suffix}"),
            ("runes", f"{_rune_text(clipped, wli)}{suffix}"),
        ],
        options=options,
    )


def tutorial_debug_preview_lines(
    *,
    label: str,
    idx: Sequence[int],
    wli: Sequence[Sequence[int]] | None,
    direction: Direction | str,
    token_limit: int = DEFAULT_DEBUG_PREVIEW_TOKENS,
) -> list[str]:
    direction_value = ensure_direction(direction)
    idx_values = [int(value) for value in idx]
    if token_limit < 1:
        raise ValueError("token_limit must be >= 1")

    clipped = idx_values[:token_limit]
    suffix = "" if len(idx_values) <= token_limit else f" ... <{len(idx_values) - token_limit} more>"

    return [
        f"Debug preview: {label}",
        "----------------------",
        f"encoding_dir: {direction_value.value}",
        f"latin_tokens: {_token_text(clipped, wli)}{suffix}",
        f"rune_indices: {clipped}{suffix}",
        f"runes: {_rune_text(clipped, wli)}{suffix}",
    ]


def _token_text(idx: Sequence[int], wli: Sequence[Sequence[int]] | None) -> str:
    return _join_words([[str(Runeglish.pos_to_latin(int(value))) for value in word] for word in _word_groups(idx, wli)])


def _rune_text(idx: Sequence[int], wli: Sequence[Sequence[int]] | None) -> str:
    return "  ".join("".join(str(Runeglish.pos_to_rune(int(value))) for value in word) for word in _word_groups(idx, wli))


def _join_words(words: Sequence[Sequence[str]]) -> str:
    return "  ".join("|".join(token for token in word) for word in words)


def _word_groups(idx: Sequence[int], wli: Sequence[Sequence[int]] | None) -> list[list[int]]:
    values = [int(value) for value in idx]
    if not values:
        return []
    if not wli:
        return [values]

    groups: list[list[int]] = []
    current: list[int] = []
    for pos, value in enumerate(values):
        current.append(value)
        try:
            word_pos = int(wli[pos][0])
            word_len = int(wli[pos][1])
        except (IndexError, TypeError, ValueError):
            continue
        if word_pos == word_len - 1:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


__all__ = [
    "DEFAULT_DEBUG_PREVIEW_TOKENS",
    "print_tutorial_debug_preview",
    "tutorial_debug_preview_block",
    "tutorial_debug_preview_lines",
]
