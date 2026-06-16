from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from rune_decrypter_prime.data.liber_primus.lp_registry import LPFragmentLocator
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript


BOUNDARY_CANON_PAGE_RANGE = "verified_master_transcript_canon_page_range"
SOURCE_STATUS_SOLVED_TEXT_AVAILABLE = "solved_text_available"


@dataclass(frozen=True)
class LPSourceEntry:
    """Human-facing LP text-source label resolved to master-transcript pages.

    Source labels identify *which LP text fragment* is being used. They must not
    encode the cipher, key, or solving method. Those belong in solve recipes.
    """

    source_label: str
    display_name: str
    source_status: str
    boundary_status: str
    red_rune_label: str
    spreadsheet_sheet: str
    red_rune_sections: tuple[int, ...]
    canon_page_range: tuple[int, int]
    side_art_label: Optional[str] = None
    aliases: tuple[str, ...] = ()
    locator: Optional[LPFragmentLocator] = None
    notes: str = ""

    def __post_init__(self) -> None:
        _require_label(self.source_label, "source_label")
        if not self.source_label.startswith("red_rune."):
            raise ValueError(f"source_label must use red_rune namespace: {self.source_label!r}")
        if not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        if not self.red_rune_label.strip():
            raise ValueError("red_rune_label must be non-empty")
        if not self.spreadsheet_sheet.strip():
            raise ValueError("spreadsheet_sheet must be non-empty")
        if not self.red_rune_sections:
            raise ValueError("red_rune_sections must be non-empty")
        if any(section <= 0 for section in self.red_rune_sections):
            raise ValueError("red_rune_sections must be positive")
        start, end = self.canon_page_range
        if start < 0 or end < start:
            raise ValueError("canon_page_range must be a non-negative inclusive range")
        _reject_method_words(self.source_label, "source_label")
        for alias in self.aliases:
            _require_label(alias, "alias")
            _reject_method_words(alias, "alias")

    @property
    def has_explicit_locator(self) -> bool:
        return self.locator is not None


@dataclass(frozen=True)
class LPSolveRecipeEntry:
    """Named way to solve or replay an LP source entry."""

    recipe_label: str
    source_label: str
    cipher_family: str
    target_kind: str
    priority: str
    reference_key_or_shift: Optional[str] = None
    expected_match: float = 1.0
    notes: str = ""

    def __post_init__(self) -> None:
        _require_label(self.recipe_label, "recipe_label")
        if not self.recipe_label.startswith("recipe."):
            raise ValueError(f"recipe_label must use recipe namespace: {self.recipe_label!r}")
        _require_label(self.source_label, "source_label")
        if not self.cipher_family.strip():
            raise ValueError("cipher_family must be non-empty")
        if not self.target_kind.strip():
            raise ValueError("target_kind must be non-empty")
        if not self.priority.strip():
            raise ValueError("priority must be non-empty")
        if not 0.0 <= float(self.expected_match) <= 1.0:
            raise ValueError("expected_match must be in [0, 1]")


_METHOD_WORDS = frozenset(
    {
        "atbash",
        "cipher",
        "divinity",
        "emirp",
        "fibbo",
        "fibonacci",
        "firfumferenfe",
        "gematria",
        "interrupter",
        "interruptors",
        "key",
        "prime",
        "primes",
        "recipe",
        "shift",
        "stream",
        "vigenere",
    }
)


def _require_label(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have surrounding whitespace")
    if " " in value:
        raise ValueError(f"{field_name} must not contain spaces")


def _reject_method_words(label: str, field_name: str) -> None:
    parts = {part for part in label.replace("-", "_").split(".") for part in part.split("_") if part}
    overlap = sorted(parts & _METHOD_WORDS)
    if overlap:
        raise ValueError(f"{field_name} must not encode solving method words: {overlap}")


_SOURCE_ENTRIES: tuple[LPSourceEntry, ...] = (
    LPSourceEntry(
        source_label="red_rune.warning",
        display_name="A Warning",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="warning",
        spreadsheet_sheet="A Warning",
        red_rune_sections=(1,),
        canon_page_range=(0, 2),
        side_art_label="sign_post_cross",
        aliases=("solved.warning",),
    ),
    LPSourceEntry(
        source_label="red_rune.some_wisdom",
        display_name="Some Wisdom",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="some_wisdom",
        spreadsheet_sheet="Some Wisdom",
        red_rune_sections=(2,),
        canon_page_range=(3, 3),
        side_art_label="spirals",
        aliases=("solved.some_wisdom",),
    ),
    LPSourceEntry(
        source_label="red_rune.welcome_pilgrim",
        display_name="Welcome Pilgrim",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="welcome_pilgrim",
        spreadsheet_sheet="Welcome",
        red_rune_sections=(3,),
        canon_page_range=(3, 6),
        side_art_label="spirals",
        aliases=("solved.welcome_pilgrim",),
    ),
    LPSourceEntry(
        source_label="red_rune.koan_a_man",
        display_name="A Koan: A Man",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="koan_a_man",
        spreadsheet_sheet="A Koan A Man",
        red_rune_sections=(4, 5),
        canon_page_range=(6, 7),
        side_art_label="spirals",
        aliases=("solved.koan_a_man",),
    ),
    LPSourceEntry(
        source_label="red_rune.loss_of_divinity",
        display_name="The Loss of Divinity",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="loss_of_divinity",
        spreadsheet_sheet="The Loss Of",
        red_rune_sections=(6,),
        canon_page_range=(8, 14),
        side_art_label="branches",
        aliases=("solved.loss_of_divinity",),
    ),
    LPSourceEntry(
        source_label="red_rune.koan_during_lesson",
        display_name="A Koan: During a Lesson",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="koan_during_lesson",
        spreadsheet_sheet="A Koan During",
        red_rune_sections=(7, 8),
        canon_page_range=(15, 22),
        side_art_label="mobius",
        aliases=("solved.koan_during_lesson",),
    ),
    LPSourceEntry(
        source_label="red_rune.instruction",
        display_name="An Instruction",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="instruction",
        spreadsheet_sheet="An Instruction",
        red_rune_sections=(15,),
        canon_page_range=(54, 55),
        side_art_label="spiral_branches",
        aliases=("solved.instruction",),
    ),
    LPSourceEntry(
        source_label="red_rune.an_end",
        display_name="AN END",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="an_end",
        spreadsheet_sheet="p56 An End",
        red_rune_sections=(16,),
        canon_page_range=(56, 56),
        side_art_label="an_end",
        aliases=("solved.an_end",),
    ),
    LPSourceEntry(
        source_label="red_rune.parable",
        display_name="Parable",
        source_status=SOURCE_STATUS_SOLVED_TEXT_AVAILABLE,
        boundary_status=BOUNDARY_CANON_PAGE_RANGE,
        red_rune_label="parable",
        spreadsheet_sheet="p57 Parable",
        red_rune_sections=(17,),
        canon_page_range=(57, 57),
        side_art_label="parable",
        aliases=("solved.parable",),
    ),
)

_SOLVE_RECIPES: tuple[LPSolveRecipeEntry, ...] = (
    LPSolveRecipeEntry(
        recipe_label="recipe.warning.reverse_gematria_replay",
        source_label="red_rune.warning",
        cipher_family="reverse_gematria",
        target_kind="reference_replay",
        priority="P1",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.some_wisdom.constant_shift_zero_replay",
        source_label="red_rune.some_wisdom",
        cipher_family="constant_shift_normal_gematria",
        target_kind="reference_replay",
        priority="P1",
        reference_key_or_shift="0",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.welcome_pilgrim.vigenere_interruptors",
        source_label="red_rune.welcome_pilgrim",
        cipher_family="vigenere_with_interruptors",
        target_kind="real_solve",
        priority="P0",
        reference_key_or_shift="DIVINITY",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.koan_a_man.rotated_reverse_gematria_replay",
        source_label="red_rune.koan_a_man",
        cipher_family="rotated_reverse_gematria",
        target_kind="reference_replay",
        priority="P2",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.loss_of_divinity.constant_shift_zero_replay",
        source_label="red_rune.loss_of_divinity",
        cipher_family="constant_shift_normal_gematria",
        target_kind="reference_replay",
        priority="P1",
        reference_key_or_shift="0",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.koan_during_lesson.vigenere_interruptors",
        source_label="red_rune.koan_during_lesson",
        cipher_family="vigenere_with_interruptors",
        target_kind="real_solve",
        priority="P0",
        reference_key_or_shift="FIRFUMFERENFE",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.instruction.constant_shift_zero_replay",
        source_label="red_rune.instruction",
        cipher_family="constant_shift_normal_gematria",
        target_kind="reference_replay",
        priority="P1",
        reference_key_or_shift="0",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.an_end.stream_sequence_interruptors",
        source_label="red_rune.an_end",
        cipher_family="stream_sequence_with_interruptors",
        target_kind="real_solve",
        priority="P0",
        reference_key_or_shift="primes_minus_1",
        notes="Special case: derive candidate sequence from early key material, then solve with interrupters.",
    ),
    LPSolveRecipeEntry(
        recipe_label="recipe.parable.constant_shift_zero_replay",
        source_label="red_rune.parable",
        cipher_family="constant_shift_normal_gematria",
        target_kind="reference_replay",
        priority="P1",
        reference_key_or_shift="0",
    ),
)

_SOURCE_BY_LABEL = {entry.source_label: entry for entry in _SOURCE_ENTRIES}
_SOURCE_ALIAS_TO_LABEL = {alias: entry.source_label for entry in _SOURCE_ENTRIES for alias in entry.aliases}
_RECIPE_BY_LABEL = {entry.recipe_label: entry for entry in _SOLVE_RECIPES}

if len(_SOURCE_BY_LABEL) != len(_SOURCE_ENTRIES):
    raise RuntimeError("duplicate LP source labels in catalogue")
if len(_RECIPE_BY_LABEL) != len(_SOLVE_RECIPES):
    raise RuntimeError("duplicate LP solve recipe labels in catalogue")
for recipe in _SOLVE_RECIPES:
    if recipe.source_label not in _SOURCE_BY_LABEL:
        raise RuntimeError(f"solve recipe references unknown source label: {recipe.recipe_label}")


def list_source_labels(*, include_aliases: bool = False) -> tuple[str, ...]:
    labels = sorted(_SOURCE_BY_LABEL)
    if include_aliases:
        labels.extend(sorted(_SOURCE_ALIAS_TO_LABEL))
    return tuple(labels)


def list_solve_recipe_labels() -> tuple[str, ...]:
    return tuple(sorted(_RECIPE_BY_LABEL))


def resolve_source_label(label: str) -> LPSourceEntry:
    _require_label(label, "label")
    canonical = _SOURCE_ALIAS_TO_LABEL.get(label, label)
    try:
        return _SOURCE_BY_LABEL[canonical]
    except KeyError as exc:
        raise KeyError(f"unknown LP source label: {label!r}") from exc


def resolve_solve_recipe_label(label: str) -> LPSolveRecipeEntry:
    _require_label(label, "label")
    try:
        return _RECIPE_BY_LABEL[label]
    except KeyError as exc:
        raise KeyError(f"unknown LP solve recipe label: {label!r}") from exc


def payload_from_label(label: str, *, doc: LPTranscript | None = None):
    """Return an LP solver payload for a source label.

    The current solved-source catalogue resolves red-rune labels to verified
    canon-page ranges in the bundled master transcript. More precise line-level
    locators can be added later without changing the public label.
    """

    from rune_decrypter_prime.data.liber_primus.lp_adapter import (
        payload_from_locator,
        payload_from_partition_entry,
    )
    from rune_decrypter_prime.data.liber_primus.lp_master import (
        load_master_transcript,
        make_resolution_context,
    )
    from rune_decrypter_prime.data.liber_primus.lp_registry import (
        LPBuiltInPartitionScheme,
        LPPageRef,
        LPPartitionEntry,
        LPSectionOrdinal,
    )

    entry = resolve_source_label(label)
    effective_doc = doc or load_master_transcript(attach_catalogue=True)

    if entry.locator is not None:
        payload = payload_from_locator(effective_doc, entry.locator)
        start_canon = entry.locator.page_ref.number
        end_canon = start_canon
        red_rune_ordinal = "-".join(str(part) for part in entry.red_rune_sections)
    else:
        start_canon, end_canon = entry.canon_page_range
        red_rune_ordinal = "-".join(str(part) for part in entry.red_rune_sections)
        partition_entry = LPPartitionEntry(
            scheme=LPBuiltInPartitionScheme.SOLVED_PLAINTEXT_PAGES,
            ordinal=LPSectionOrdinal.of(*entry.red_rune_sections),
            start_page=LPPageRef.canon_page(start_canon),
            end_page=LPPageRef.canon_page(end_canon),
            display_name=entry.display_name,
            tags=("solved_text", entry.red_rune_label),
        )
        payload = payload_from_partition_entry(effective_doc, partition_entry)

    context = make_resolution_context(effective_doc)
    bound_book_start = context.canon_offset + start_canon + 1
    bound_book_end = context.canon_offset + end_canon + 1
    metadata = {
        **payload.metadata,
        "source_kind": "liber_primus.label",
        "source_label": entry.source_label,
        "display_name": entry.display_name,
        "source_status": entry.source_status,
        "boundary_status": entry.boundary_status,
        "red_rune_label": entry.red_rune_label,
        "red_rune_sections": list(entry.red_rune_sections),
        "red_rune_ordinal": red_rune_ordinal,
        "side_art_label": entry.side_art_label,
        "spreadsheet_sheet": entry.spreadsheet_sheet,
        "canon_start": start_canon,
        "canon_end": end_canon,
        "bound_book_start": bound_book_start,
        "bound_book_end": bound_book_end,
        "line": None,
        "line_end": None,
        "boundary_granularity": "full_canon_pages",
    }
    return type(payload)(ct_idx=payload.ct_idx, wli=payload.wli, metadata=metadata)


__all__ = [
    "BOUNDARY_CANON_PAGE_RANGE",
    "SOURCE_STATUS_SOLVED_TEXT_AVAILABLE",
    "LPSourceEntry",
    "LPSolveRecipeEntry",
    "list_source_labels",
    "list_solve_recipe_labels",
    "payload_from_label",
    "resolve_source_label",
    "resolve_solve_recipe_label",
]
