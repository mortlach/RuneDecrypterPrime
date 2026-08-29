from __future__ import annotations
import sys
from pathlib import Path
from typing import Any, Dict, List, cast

_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for path in (_SRC,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
import numpy as np
from rdp import api
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview

ALPHABET = 29
DEMO_TEXT = "THERE WAS A TABLE SET OUT UNDER A TREE"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _demo_ciphertext() -> Dict[str, Any]:
    encoding_dir = api.TextDirection.RIGHT_TO_LEFT
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        DEMO_TEXT, direction=encoding_dir.value
    )
    key_nums: List[int] = [3, 1, 4, 1]
    encrypted = api.encrypt(
        tuple(int(value) for value in pt_idx),
        cipher=api.CipherSpec.vigenere(),
        key=tuple(int(value) for value in key_nums),
    )
    ct_idx = [int(value) for value in list(encrypted)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    return {
        "ciphertext": ct_runes,
        "ciphertext_idx": ct_idx,
        "wli": wli,
        "encoding_dir": encoding_dir,
        "secret_key": key_nums,
        "plaintext": pt_runes,
        "plaintext_idx": pt_idx,
    }


def _solution_match_ratio(solution, pt_idx: list[int]) -> float:
    guess = solution.plaintext or None
    if not guess:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    if n <= 0:
        return 0.0
    return float(np.mean(a[:n] == b[:n]))


def _make_scorer_params(demo: Dict[str, Any]) -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _display_scorer_params(demo: Dict[str, Any]) -> api.ScoringConfig:
    return api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
        objective=api.advanced.ScoringObjective.percentile_log_probability(
            window_size=10
        ),
    )


def _display_spec(
    demo: Dict[str, Any],
    cipher_spec: api.CipherSpec,
    key_spec: api.KeySpec,
    solver_spec: api.SolverSpec,
) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.RuneIndexInput(
            indices=cast(List[int], demo["ciphertext_idx"]),
            word_lengths=cast(List[List[int]], demo["wli"]),
        ),
        cipher=cipher_spec,
        key_space=key_spec,
        solver=solver_spec,
        scoring=_display_scorer_params(demo),
        text_direction=cast(api.TextDirection, demo["encoding_dir"]),
        telemetry_enabled=True,
    )


def solve_with_wrappers(
    demo: Dict[str, Any],
    cipher_spec: api.CipherSpec,
    key_spec: api.KeySpec,
    scorer_params: api.ScoringConfig,
) -> None:
    """Interface demonstration with the known key supplied as an initial key."""
    solver_spec = api.SolverSpec.beam_search(width=18, rounds=0, seed=1337)
    result = api.run(
        problem_input=api.RuneIndexInput(
            indices=demo["ciphertext_idx"], word_lengths=demo["wli"]
        ),
        cipher=cipher_spec,
        key_space=key_spec,
        solver=solver_spec,
        scoring=scorer_params,
        initial_keys=tuple((tuple(item) for item in [demo["secret_key"]])),
        text_direction=demo["encoding_dir"],
        telemetry_enabled=True,
    )
    _print_summary(
        "Wrapper Beam (known key supplied)",
        result,
        demo,
        _display_spec(demo, cipher_spec, key_spec, solver_spec),
    )


def solve_with_general_map(
    demo: Dict[str, object], scorer_params: api.ScoringConfig
) -> None:
    """Same ciphertext, but the cipher is declared with define_map()."""

    def vigenere_cell(pt: int, k: int) -> int:
        return (pt + k) % ALPHABET

    cipher_spec = api.experimental.define_cipher_map(
        vigenere_cell, alphabet_size=ALPHABET
    )
    key_len = len(cast(List[int], demo["secret_key"]))
    key_spec = api.KeySpec.repeating(length=key_len)
    solver_spec = api.SolverSpec.beam_search(width=96, rounds=0, seed=4242)
    result = api.run(
        problem_input=api.RuneIndexInput(
            indices=demo["ciphertext_idx"], word_lengths=demo["wli"]
        ),
        cipher=cipher_spec,
        key_space=key_spec,
        solver=solver_spec,
        scoring=scorer_params,
        text_direction=demo["encoding_dir"],
        telemetry_enabled=True,
    )
    _print_summary(
        "General Map Beam",
        result,
        cast(Dict[str, Any], demo),
        _display_spec(cast(Dict[str, Any], demo), cipher_spec, key_spec, solver_spec),
    )


def _print_summary(label: str, result, demo: Dict[str, Any], spec: api.RunSpec) -> None:
    pt_idx = demo.get("plaintext_idx")
    reference_idx = list(pt_idx) if pt_idx is not None else None
    print(f"\n[{label}] standard summary")
    pretty.print_summary_spacer()
    api.display.print_summary(
        api.display.build_summary(
            result,
            spec=spec,
            reference_idx=reference_idx,
            tutorial_entry={
                "path": "Tutorial_Start_Here.py",
                "title": f"Start Here pretty-print {label}",
                "gate": "v1_smoke_pretty_print",
                "acceptance_kind": "exact",
                "min_match_ratio": 1.0,
            },
            options=api.display.SummaryOptions.for_tutorial(),
        )
    )


def main():
    pretty.print_rdp_identity()
    pretty.print_initialising()
    pretty.print_result_note(
        "Tutorial",
        [
            ("name", "Start here: seeded Vigenere interface and general-map solve"),
            ("cipher", "vigenere / general map"),
            ("solver", "beam"),
            ("direction", "rtl"),
            ("expected result", "exact solve"),
            (
                "truth/reference use",
                "known key supplied to wrapper interface demo; terminal-only for General Map",
            ),
        ],
    )
    demo = _demo_ciphertext()
    print("The wrapper example supplies the known key to demonstrate the interface;")
    print(
        "it is not an independent cryptanalytic recovery. The General Map run is unseeded."
    )
    print_tutorial_debug_preview(
        label="plaintext",
        idx=cast(List[int], demo["plaintext_idx"]),
        wli=cast(List[List[int]], demo["wli"]),
        direction=cast(api.TextDirection, demo["encoding_dir"]),
    )
    print_tutorial_debug_preview(
        label="ciphertext",
        idx=cast(List[int], demo["ciphertext_idx"]),
        wli=cast(List[List[int]], demo["wli"]),
        direction=cast(api.TextDirection, demo["encoding_dir"]),
    )
    key_len = len(cast(List[int], demo["secret_key"]))
    cipher_spec, key_spec = (
        api.CipherSpec.vigenere(),
        api.KeySpec.repeating(length=key_len),
    )
    scorer_params = _make_scorer_params(demo)
    solve_with_wrappers(demo, cipher_spec, key_spec, scorer_params)
    solve_with_general_map(demo, scorer_params)


if __name__ == "__main__":
    main()
