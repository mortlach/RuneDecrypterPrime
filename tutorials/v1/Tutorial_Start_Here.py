from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, cast

# Allow "python tutorials/v1/Tutorial_Start_Here.py" without pip-installing the project
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for path in (_SRC,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import numpy as np

from rdp import api  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402
from rune_decrypter_prime.utils import tutorial_pretty as pretty
from rune_decrypter_prime.utils.tutorial_output import print_tutorial_debug_preview  # noqa: E402

ALPHABET = 29
DEMO_TEXT = "THERE WAS A TABLE SET OUT UNDER A TREE"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def _demo_ciphertext() -> Dict[str, Any]:
    encoding_dir = api.Direction.RTL
    pt_idx, wli, pt_runes = Runeglish.encode_english_to_runes(
        DEMO_TEXT,
        direction=encoding_dir.value,
    )
    key_nums: List[int] = [3, 1, 4, 1]
    cipher = api.cipher_instance(
        "vigenere", key_length=len(key_nums), text_transposition=encoding_dir.value
    )
    encrypted = cipher.encrypt_single(
        plaintext=np.asarray(pt_idx, dtype=np.uint8),
        key=np.asarray(key_nums, dtype=np.uint8),
    )
    ct_idx = [int(value) for value in encrypted.tolist()]
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


def _progress_kwargs(demo: Dict[str, Any]) -> Dict[str, Any]:
    """Console progress prints the entire short demo string each pct update."""
    ct = str(demo.get("ciphertext", "") or "")
    pt = str(demo.get("plaintext", "") or "")
    preview_chars = max(len(ct), len(pt))
    if preview_chars <= 0:
        preview_chars = 120
    return dict(
        verbose=True,
        verbose_console=True,
        print_progress=True,
        progress_pct=1,
        progress_preview_chars=preview_chars,
    )


def _solution_match_ratio(solution, pt_idx: list[int]) -> float:
    guess = getattr(solution, "plaintext_idx", None)
    if not guess:
        return 0.0
    a = np.asarray(guess, dtype=np.int64).reshape(-1)
    b = np.asarray(pt_idx, dtype=np.int64).reshape(-1)
    n = min(a.size, b.size)
    if n <= 0:
        return 0.0
    return float(np.mean(a[:n] == b[:n]))


def _make_scorer_params(demo: Dict[str, Any]) -> Dict[str, Any]:
    return dict(
        include_char=True,
        use_word_breaks=True,
        char_weights={2: 0.3},
        wli_weights={2: 0.7},
        encoding_dir=demo["encoding_dir"],
        objective="pct.logp.win10",
    )


def _display_scorer_params(demo: Dict[str, Any]) -> Dict[str, Any]:
    direction = cast(api.Direction, demo["encoding_dir"])
    return {
        "objective": "pct.logp.win10",
        "include_char": True,
        "use_word_breaks": True,
        "encoding_dir": direction.value,
        "char_order_2_weight": 0.3,
        "wli_order_2_weight": 0.7,
    }


def _display_spec(demo: Dict[str, Any], cipher_spec, key_spec, solver_spec) -> api.RunSpec:
    return api.RunSpec(
        problem_input=api.NormalizedInput(
            ct_idx=cast(List[int], demo["ciphertext_idx"]),
            wli=cast(List[List[int]], demo["wli"]),
        ),
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer="rune",
        scorer_params=_display_scorer_params(demo),
        encoding_dir=cast(api.Direction, demo["encoding_dir"]),
        telemetry_on=True,
    )


def solve_with_wrappers(
    demo: Dict[str, Any],
    cipher_spec,
    key_spec,
    scorer_params: Dict[str, Any],
):
    """Interface demonstration with the known key supplied as an initial key."""
    solver_spec = api.SolverSpec.beam(
        beam_width=18,
        stop_score=0.54,
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        log_interval=25,
        seed=1337,
        **_progress_kwargs(demo),
    )
    result = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(scorer_params),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
        initial_keys=[demo["secret_key"]],
        return_solver_report=True,
    )
    _print_summary("Wrapper Beam (known key supplied)", result, demo, _display_spec(demo, cipher_spec, key_spec, solver_spec))


def solve_with_general_map(demo: Dict[str, object], scorer_params: Dict[str, Any]):
    """Same ciphertext, but the cipher is declared with define_map()."""
    def vigenere_cell(pt: int, k: int) -> int:
        return (pt + k) % ALPHABET

    cipher_spec = api.define_map(function=vigenere_cell, N=ALPHABET)
    key_len = len(cast(List[int], demo["secret_key"]))
    key_spec = api.KeySpec.repeat(len=key_len)
    solver_spec = api.SolverSpec.beam(
        beam_width=96,
        rounds=0,
        top_parents_factor=1.0,
        stop_score=0.62,
        plateau_rounds=10,
        plateau_min_delta=1e-5,
        **_progress_kwargs(cast(Dict[str, Any], demo)),
        seed=4242,
    )
    result = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(scorer_params),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
        return_solver_report=True,
    )
    _print_summary("General Map Beam", result, cast(Dict[str, Any], demo), _display_spec(cast(Dict[str, Any], demo), cipher_spec, key_spec, solver_spec))


def _print_summary(label: str, result, demo: Dict[str, Any], spec: api.RunSpec) -> None:
    pt_idx = demo.get("plaintext_idx")
    reference_idx = list(pt_idx) if pt_idx is not None else None

    print(f"\n[{label}] standard summary")
    pretty.print_summary_spacer()
    api.print_rdp_result(
        result,
        spec=spec,
        reference_idx=reference_idx,
        options=api.RdpDisplayOptions.for_tutorial(),
        tutorial_entry={
            "path": "Tutorial_Start_Here.py",
            "title": f"Start Here pretty-print {label}",
            "gate": "v1_smoke_pretty_print",
            "acceptance_kind": "exact",
            "min_match_ratio": 1.0,
        },
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
    print("it is not an independent cryptanalytic recovery. The General Map run is unseeded.")
    print_tutorial_debug_preview(
        label="plaintext",
        idx=cast(List[int], demo["plaintext_idx"]),
        wli=cast(List[List[int]], demo["wli"]),
        direction=cast(api.Direction, demo["encoding_dir"]),
    )
    print_tutorial_debug_preview(
        label="ciphertext",
        idx=cast(List[int], demo["ciphertext_idx"]),
        wli=cast(List[List[int]], demo["wli"]),
        direction=cast(api.Direction, demo["encoding_dir"]),
    )
    key_len = len(cast(List[int], demo["secret_key"]))
    cipher_spec, key_spec = api.define_cipher(
        name="vigenere",
        key_len=key_len,
        default_key=True,
    )
    scorer_params = _make_scorer_params(demo)
    solve_with_wrappers(demo, cipher_spec, key_spec, scorer_params)
    solve_with_general_map(demo, scorer_params)


if __name__ == "__main__":
    main()
