from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from rdp.api.specs import SolverSpec
from rune_decrypter_prime.core.types import SolverKind

TWO_PERIOD_CRIBS_SOLVER_NAME = "two_period_cribs"
TWO_PERIOD_CRIBS_CONTRACT = "two_period_cribs.v1"
DEFAULT_SEED = 0


@dataclass(frozen=True, slots=True)
class TwoPeriodCribsRequest:
    fixed_cribs: tuple[tuple[str, int], ...]
    candidate_words: tuple[str, ...]
    candidate_positions: tuple[tuple[str, tuple[int, ...]], ...]
    starts: int
    requested_seed: int | None
    effective_seed: int

    def positions_for(self, word: str) -> tuple[int, ...] | None:
        return dict(self.candidate_positions).get(word)

    def normalized_params(self) -> dict[str, Any]:
        return {
            "contract": TWO_PERIOD_CRIBS_CONTRACT,
            "fixed_cribs": [[word, start] for word, start in self.fixed_cribs],
            "candidate_words": list(self.candidate_words),
            "candidate_positions": {
                word: list(positions) for word, positions in self.candidate_positions
            },
            "starts": self.starts,
        }


def _word(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} entries must be strings")
    word = value.strip().lower()
    if not word or not word.isascii() or not word.isalpha():
        raise ValueError(f"{field} entries must contain only ASCII letters")
    return word


def _positions(value: Any, field: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{field} must be a sequence of non-negative integers")
    out: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise TypeError(f"{field} must contain non-negative integers")
        if item < 0:
            raise ValueError(f"{field} must contain non-negative integers")
        out.append(item)
    return tuple(sorted(set(out)))


def build_two_period_cribs_spec(
    *,
    fixed_cribs: Sequence[tuple[str, int]] = (),
    candidate_words: Sequence[str] = (),
    candidate_positions: Mapping[str, Sequence[int]] | None = None,
    starts: int = 96,
    seed: int | None = None,
) -> SolverSpec:
    if isinstance(fixed_cribs, (str, bytes)) or not isinstance(fixed_cribs, Sequence):
        raise TypeError("fixed_cribs must be a sequence of (word, start) pairs")
    fixed: list[tuple[str, int]] = []
    for item in fixed_cribs:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise TypeError("fixed_cribs entries must be (word, start) pairs")
        word, start = item
        if isinstance(start, bool) or not isinstance(start, int):
            raise TypeError("fixed crib starts must be non-negative integers")
        if start < 0:
            raise ValueError("fixed crib starts must be non-negative integers")
        fixed.append((_word(word, "fixed_cribs"), start))

    if isinstance(candidate_words, (str, bytes)) or not isinstance(
        candidate_words, Sequence
    ):
        raise TypeError("candidate_words must be a sequence of words")
    words = tuple(
        sorted(set(_word(word, "candidate_words") for word in candidate_words))
    )

    if candidate_positions is None:
        positions: dict[str, tuple[int, ...]] = {}
    elif not isinstance(candidate_positions, Mapping):
        raise TypeError("candidate_positions must be a mapping from word to positions")
    else:
        positions = {}
        for raw_word, raw_positions in candidate_positions.items():
            word = _word(raw_word, "candidate_positions")
            if word not in words:
                raise ValueError(f"candidate_positions contains unknown word {word!r}")
            positions[word] = _positions(
                raw_positions, f"candidate_positions[{word!r}]"
            )

    if isinstance(starts, bool) or not isinstance(starts, int):
        raise TypeError("starts must be a positive integer")
    if starts <= 0:
        raise ValueError("starts must be a positive integer")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise TypeError("seed must be an integer or None")
    if not fixed and not words:
        raise ValueError("at least one fixed crib or candidate word is required")

    return SolverSpec.two_period_cribs(
        fixed_cribs=tuple(sorted(set(fixed))),
        candidate_words=words,
        candidate_positions={word: positions[word] for word in sorted(positions)},
        starts=starts,
        seed=seed,
    )


def is_two_period_cribs_solver(solver: SolverSpec) -> bool:
    return isinstance(solver, SolverSpec) and solver.kind is SolverKind.TWO_PERIOD_CRIBS


def normalize_two_period_cribs_request(solver: SolverSpec) -> TwoPeriodCribsRequest:
    if not is_two_period_cribs_solver(solver):
        raise ValueError("solver is not a two_period_cribs request")
    params = dict(solver.parameters)
    rebuilt = build_two_period_cribs_spec(
        fixed_cribs=params.pop("fixed_cribs", ()),
        candidate_words=params.pop("candidate_words", ()),
        candidate_positions=params.pop("candidate_positions", None),
        starts=params.pop("starts", 96),
        seed=solver.seed,
    )
    if params:
        raise ValueError(f"unsupported two_period_cribs parameters: {sorted(params)}")
    normalized = rebuilt.parameters
    return TwoPeriodCribsRequest(
        fixed_cribs=tuple((str(w), int(p)) for w, p in normalized["fixed_cribs"]),
        candidate_words=tuple(normalized["candidate_words"]),
        candidate_positions=tuple(
            (word, tuple(int(value) for value in values))
            for word, values in (normalized["candidate_positions"] or {}).items()
        ),
        starts=int(normalized["starts"]),
        requested_seed=solver.seed,
        effective_seed=DEFAULT_SEED if solver.seed is None else solver.seed,
    )


__all__ = [
    "TWO_PERIOD_CRIBS_CONTRACT",
    "TWO_PERIOD_CRIBS_SOLVER_NAME",
    "TwoPeriodCribsRequest",
    "build_two_period_cribs_spec",
    "is_two_period_cribs_solver",
    "normalize_two_period_cribs_request",
]
