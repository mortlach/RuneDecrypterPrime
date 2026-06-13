from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Sequence


class LPBuiltInPageScheme(str, Enum):
    TRANSCRIPT_PAGE_ID = "transcript_page_id"
    BOUND_BOOK_PAGE = "bound_book_page"
    CANON_UNSOLVED_PAGE = "canon_unsolved_page"


class LPBuiltInPartitionScheme(str, Enum):
    LEGACY_SECTIONS = "legacy_sections"
    RED_RUNE_17 = "red_rune_17"
    SIDE_ART_10 = "side_art_10"
    SIDE_ART_RED_RUNE_NESTED = "side_art_red_rune_nested"
    SOLVED_PLAINTEXT_PAGES = "solved_plaintext_pages"


@dataclass(frozen=True, order=True)
class LPRegistryLabel:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        if not self.namespace.strip():
            raise ValueError("namespace must be non-empty")
        if not self.name.strip():
            raise ValueError("name must be non-empty")


@dataclass(frozen=True, order=True)
class LPSectionOrdinal:
    parts: tuple[int, ...]

    @classmethod
    def of(cls, *parts: int) -> LPSectionOrdinal:
        if not parts:
            raise ValueError("LPSectionOrdinal requires at least one part")
        if any(part <= 0 for part in parts):
            raise ValueError("ordinal parts must be positive integers")
        return cls(tuple(parts))

    def render(self, *, sep: str = "-") -> str:
        return sep.join(str(part) for part in self.parts)


@dataclass(frozen=True)
class LPPageRef:
    scheme: LPBuiltInPageScheme
    number: int

    @classmethod
    def transcript_page(cls, number: int) -> LPPageRef:
        if number < 0:
            raise ValueError("transcript page id must be >= 0")
        return cls(LPBuiltInPageScheme.TRANSCRIPT_PAGE_ID, number)

    @classmethod
    def bound_book_page(cls, number: int) -> LPPageRef:
        if number <= 0:
            raise ValueError("bound-book page number must be >= 1")
        return cls(LPBuiltInPageScheme.BOUND_BOOK_PAGE, number)

    @classmethod
    def canon_page(cls, number: int) -> LPPageRef:
        if number < 0:
            raise ValueError("canon page number must be >= 0")
        return cls(LPBuiltInPageScheme.CANON_UNSOLVED_PAGE, number)


@dataclass(frozen=True)
class LPFragmentLocator:
    page_ref: LPPageRef
    line: int | None = None
    line_end: int | None = None
    word: int | None = None
    word_end: int | None = None


@dataclass(frozen=True)
class LPPartitionEntry:
    scheme: LPBuiltInPartitionScheme
    ordinal: LPSectionOrdinal
    start_page: LPPageRef
    end_page: LPPageRef
    display_name: str | None = None
    tags: tuple[str, ...] = ()

    def canon_page_range(self) -> tuple[int, int]:
        if self.start_page.scheme is not LPBuiltInPageScheme.CANON_UNSOLVED_PAGE:
            raise ValueError("start_page must use CANON_UNSOLVED_PAGE")
        if self.end_page.scheme is not LPBuiltInPageScheme.CANON_UNSOLVED_PAGE:
            raise ValueError("end_page must use CANON_UNSOLVED_PAGE")
        if self.end_page.number < self.start_page.number:
            raise ValueError("end_page must be >= start_page")
        return self.start_page.number, self.end_page.number


@dataclass(frozen=True)
class LPPageFeature:
    page: LPPageRef
    tags: tuple[str, ...] = ()
    display_name: str | None = None
    aliases: tuple[LPRegistryLabel, ...] = ()


@dataclass
class LPRegistry:
    page_aliases: Dict[LPRegistryLabel, LPPageRef] = field(default_factory=dict)
    partitions: Dict[LPBuiltInPartitionScheme | LPRegistryLabel, tuple[LPPartitionEntry, ...]] = (
        field(default_factory=dict)
    )
    page_features: Dict[int, LPPageFeature] = field(default_factory=dict)

    def register_page_alias(self, label: LPRegistryLabel, target: LPPageRef) -> None:
        if label in self.page_aliases:
            raise KeyError(f"page alias already registered: {label}")
        self.page_aliases[label] = target

    def resolve_page_alias(self, label: LPRegistryLabel) -> LPPageRef:
        return self.page_aliases[label]

    def register_partition(
        self,
        key: LPBuiltInPartitionScheme | LPRegistryLabel,
        entries: Sequence[LPPartitionEntry],
    ) -> None:
        if key in self.partitions:
            raise KeyError(f"partition already registered: {key}")
        self.partitions[key] = tuple(entries)

    def get_partition(
        self,
        key: LPBuiltInPartitionScheme | LPRegistryLabel,
    ) -> tuple[LPPartitionEntry, ...]:
        return self.partitions[key]


@dataclass(frozen=True)
class LPResolutionContext:
    total_pages: int
    canon_page_count: int = 58

    @property
    def canon_offset(self) -> int:
        offset = self.total_pages - self.canon_page_count
        if offset < 0:
            raise ValueError("total_pages is smaller than canon_page_count")
        return offset


def resolve_page_ref(page_ref: LPPageRef, *, context: LPResolutionContext) -> int:
    if page_ref.scheme is LPBuiltInPageScheme.TRANSCRIPT_PAGE_ID:
        transcript_page_id = page_ref.number
    elif page_ref.scheme is LPBuiltInPageScheme.BOUND_BOOK_PAGE:
        transcript_page_id = page_ref.number - 1
    elif page_ref.scheme is LPBuiltInPageScheme.CANON_UNSOLVED_PAGE:
        transcript_page_id = context.canon_offset + page_ref.number
    else:
        raise TypeError(f"Unsupported page scheme: {page_ref.scheme}")

    if not 0 <= transcript_page_id < context.total_pages:
        raise IndexError(f"page reference resolves out of range: {page_ref}")
    return transcript_page_id


def resolve_relative_index(length: int, index: int) -> int:
    if length <= 0:
        raise IndexError("cannot index into an empty container")
    resolved = index if index >= 0 else length + index
    if not 0 <= resolved < length:
        raise IndexError(f"index {index} out of range for length {length}")
    return resolved


def build_red_rune_17_partition() -> tuple[LPPartitionEntry, ...]:
    ranges = (
        (1, 0, 2, None),
        (2, 3, 3, None),
        (3, 3, 6, None),
        (4, 6, 7, None),
        (5, 7, 7, None),
        (6, 8, 14, None),
        (7, 15, 15, None),
        (8, 15, 22, None),
        (9, 23, 26, None),
        (10, 27, 32, None),
        (11, 33, 33, None),
        (12, 33, 39, None),
        (13, 39, 39, None),
        (14, 40, 53, None),
        (15, 54, 55, None),
        (16, 56, 56, None),
        (17, 57, 57, None),
    )
    return tuple(
        LPPartitionEntry(
            scheme=LPBuiltInPartitionScheme.RED_RUNE_17,
            ordinal=LPSectionOrdinal.of(section_id),
            start_page=LPPageRef.canon_page(start),
            end_page=LPPageRef.canon_page(end),
            display_name=display_name,
        )
        for section_id, start, end, display_name in ranges
    )


def build_side_art_10_partition() -> tuple[LPPartitionEntry, ...]:
    ranges = (
        (1, 0, 2, "sign_post_cross"),
        (2, 3, 7, "spirals"),
        (3, 8, 14, "branches"),
        (4, 15, 22, "mobius"),
        (5, 23, 26, "mayfly"),
        (6, 27, 32, "wing_tree"),
        (7, 33, 39, "cuneiform"),
        (8, 40, 55, "spiral_branches"),
        (9, 56, 56, "an_end"),
        (10, 57, 57, "parable"),
    )
    return tuple(
        LPPartitionEntry(
            scheme=LPBuiltInPartitionScheme.SIDE_ART_10,
            ordinal=LPSectionOrdinal.of(section_id),
            start_page=LPPageRef.canon_page(start),
            end_page=LPPageRef.canon_page(end),
            display_name=display_name,
            tags=(display_name,),
        )
        for section_id, start, end, display_name in ranges
    )


def build_nested_side_art_red_rune_partition(
    *,
    side_art_entries: Sequence[LPPartitionEntry] | None = None,
    red_rune_entries: Sequence[LPPartitionEntry] | None = None,
) -> tuple[LPPartitionEntry, ...]:
    parents = tuple(side_art_entries or build_side_art_10_partition())
    children = tuple(red_rune_entries or build_red_rune_17_partition())
    nested: list[LPPartitionEntry] = []

    for parent in parents:
        parent_start, parent_end = parent.canon_page_range()
        overlap_count = 0
        for child in children:
            child_start, child_end = child.canon_page_range()
            overlap_start = max(parent_start, child_start)
            overlap_end = min(parent_end, child_end)
            if overlap_start > overlap_end:
                continue
            overlap_count += 1
            nested.append(
                LPPartitionEntry(
                    scheme=LPBuiltInPartitionScheme.SIDE_ART_RED_RUNE_NESTED,
                    ordinal=LPSectionOrdinal.of(parent.ordinal.parts[0], overlap_count),
                    start_page=LPPageRef.canon_page(overlap_start),
                    end_page=LPPageRef.canon_page(overlap_end),
                    display_name=f"{parent.ordinal.render()}-{overlap_count}",
                    tags=tuple(sorted({*(parent.tags or ()), "red_runes"})),
                )
            )
    return tuple(nested)


__all__ = [
    "LPBuiltInPageScheme",
    "LPBuiltInPartitionScheme",
    "LPRegistryLabel",
    "LPSectionOrdinal",
    "LPPageRef",
    "LPFragmentLocator",
    "LPPartitionEntry",
    "LPPageFeature",
    "LPRegistry",
    "LPResolutionContext",
    "resolve_page_ref",
    "resolve_relative_index",
    "build_red_rune_17_partition",
    "build_side_art_10_partition",
    "build_nested_side_art_red_rune_partition",
]
