from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from types import MappingProxyType

from rdp.data.liber_primus.lp_source_catalogue import resolve_source_label
from rdp.data.runeglish import Runeglish


_TOKEN_SEPARATOR = "·"
_CANONICAL_TOKEN_TO_POSITION = dict(
    zip(Runeglish.latin_canon, Runeglish.positions, strict=True)
)


@dataclass(frozen=True, slots=True)
class SolvedPlaintextData:
    """Immutable known plaintext for one Liber Primus source."""

    source_label: str
    indices: tuple[int, ...]
    word_length_information: tuple[tuple[int, int], ...]
    runes: str
    rune_latin: str
    metadata: Mapping[str, object]


def load_plaintext(label: str) -> SolvedPlaintextData:
    """Load the independently stored solved plaintext for an LP source label."""
    entry = resolve_source_label(label)
    if entry.solved_plaintext_file is None:
        raise ValueError(
            f"no solved plaintext is available for LP source {entry.source_label!r}"
        )
    return _load_resource(
        entry.source_label,
        entry.display_name,
        entry.solved_plaintext_file,
    )


@lru_cache(maxsize=None)
def _load_resource(
    source_label: str,
    display_name: str,
    resource_file: str,
) -> SolvedPlaintextData:
    path = (
        resources.files("rdp.data.liber_primus")
        .joinpath("solved_plaintext")
        .joinpath(resource_file)
    )
    text = path.read_text(encoding="utf-8")
    indices, wli, rune_latin = _parse_canonical_rune_latin(
        text,
        source_label=source_label,
    )
    runes = Runeglish.to_rune(indices, wli)
    metadata = MappingProxyType(
        {
            "source_kind": "liber_primus.solved_plaintext",
            "source_label": source_label,
            "display_name": display_name,
            "resource_file": resource_file,
            "word_count": sum(position == 0 for position, _length in wli),
            "rune_count": len(indices),
        }
    )
    return SolvedPlaintextData(
        source_label=source_label,
        indices=indices,
        word_length_information=wli,
        runes=runes,
        rune_latin=rune_latin,
        metadata=metadata,
    )


def _parse_canonical_rune_latin(
    text: str,
    *,
    source_label: str,
) -> tuple[tuple[int, ...], tuple[tuple[int, int], ...], str]:
    words = text.split()
    if not words:
        raise ValueError(f"solved plaintext resource is empty: {source_label}")

    indices: list[int] = []
    wli: list[tuple[int, int]] = []
    canonical_words: list[str] = []
    for word_number, word in enumerate(words, start=1):
        tokens = word.split(_TOKEN_SEPARATOR)
        if any(not token for token in tokens):
            raise ValueError(
                f"empty RuneLatin token in {source_label}, word {word_number}"
            )
        for token_number, token in enumerate(tokens, start=1):
            try:
                position = _CANONICAL_TOKEN_TO_POSITION[token]
            except KeyError as exc:
                raise ValueError(
                    f"non-canonical RuneLatin token {token!r} in {source_label}, "
                    f"word {word_number}, token {token_number}"
                ) from exc
            indices.append(position)
            wli.append((token_number - 1, len(tokens)))
        canonical_words.append(_TOKEN_SEPARATOR.join(tokens))

    canonical_text = " ".join(canonical_words)
    rendered = Runeglish.to_delimited_rune_latin(indices, wli)
    if rendered != canonical_text:
        raise ValueError(f"RuneLatin round-trip mismatch in {source_label}")
    return tuple(indices), tuple(wli), canonical_text


__all__ = ["SolvedPlaintextData", "load_plaintext"]
