from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, cast

# Allow "python tutorials/v1/Start_Here.py" without pip-installing the project
_ROOT = Path(__file__).resolve().parents[2]
_SRC = _ROOT / "src"
for path in (_SRC,):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rdp import api  # noqa: E402
from rune_decrypter_prime.utils.runeglish import Runeglish  # noqa: E402

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
    stream = [key_nums[i % len(key_nums)] for i in range(len(pt_idx))]
    ct_idx = [(p + k) % ALPHABET for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    return {
        "ciphertext": ct_runes,
        "wli": wli,
        "encoding_dir": encoding_dir,
        "secret_key": key_nums,
        "plaintext": pt_runes,
    }


def solve_with_wrappers(demo: Dict[str, object]):
    """Minimal Vigenère run using the ergonomic by_name wrapper helpers."""
    key_len = len(cast(List[int], demo["secret_key"]))
    cipher_spec, key_spec = api.define_cipher(
        name="vigenere",
        key_len=key_len,
        default_key=True,
    )
    solver_spec = api.SolverSpec.beam(
        beam_width=18,
        stop_score=0.55,
        patience_rounds=6,
        patience_min_delta=1e-4,
        log_interval=25,
        verbose=False,
        verbose_console=False,
        seed=1337,
    )
    solution = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(
            include_char=True,
            use_word_breaks=True,
            n_char=2,
            n_wli=2,
            encoding_dir=demo["encoding_dir"],
        ),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
        initial_keys=[demo["secret_key"]],
    )
    _print_summary("Wrapper Beam", solution)


def solve_with_general_map(demo: Dict[str, object]):
    """Same ciphertext, but the cipher is declared with define_map()."""
    def vigenere_cell(pt: int, k: int) -> int:
        return (pt + k) % ALPHABET

    cipher_spec = api.define_map(function=vigenere_cell, N=ALPHABET)
    key_len = len(cast(List[int], demo["secret_key"]))
    key_spec = api.KeySpec.repeat(len=key_len)
    solver_spec = api.SolverSpec.ga(
        pop_size=24,
        generations=18,
        elite_frac=0.2,
        mut_prob=0.15,
        stop_score=0.5,
        patience_rounds=4,
        patience_min_delta=1e-4,
        verbose=False,
        verbose_console=False,
        seed=4242,
    )
    solution = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(
            include_char=True,
            use_word_breaks=True,
            n_char=2,
            n_wli=2,
            encoding_dir=demo["encoding_dir"],
        ),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
    )
    _print_summary("General Map Beam", solution)


def _print_summary(label: str, solution):
    score = getattr(solution, "score", None)
    key = getattr(solution, "key", [])
    plaintext = getattr(solution, "plaintext_rune", "") or getattr(solution, "plaintext_str", "")
    snippet = plaintext[:120] + ("…" if len(plaintext) > 120 else "")
    print(f"\n[{label}] score={score:.3f}" if score is not None else f"\n[{label}]")
    print("  Plaintext:", snippet)
    print("  Key:", key)


def main():
    demo = _demo_ciphertext()
    solve_with_wrappers(demo)
    solve_with_general_map(demo)


if __name__ == "__main__":
    main()
