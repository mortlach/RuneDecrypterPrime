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

import numpy as np

from rdp import api  # noqa: E402
from rune_decrypter_prime.api.wrappers.registry import build_cipher_config  # noqa: E402
from rune_decrypter_prime.core.config import ScoringConfig  # noqa: E402
from rune_decrypter_prime.core.engine.builders import build_scorer  # noqa: E402
from rune_decrypter_prime.core.types import Device  # noqa: E402
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
        "ciphertext_idx": ct_idx,
        "wli": wli,
        "encoding_dir": encoding_dir,
        "secret_key": key_nums,
        "plaintext": pt_runes,
        "plaintext_idx": pt_idx,
    }


def _progress_kwargs(demo: Dict[str, Any]) -> Dict[str, Any]:
    """Console progress prints the entire rune string each pct update."""
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


def _make_scorer_params(demo: Dict[str, Any]) -> Dict[str, Any]:
    return dict(
        include_char=True,
        use_word_breaks=True,
        n_char=2,
        n_wli=2,
        encoding_dir=demo["encoding_dir"],
        objective="pct.logp.win10",
    )


def _score_ground_truth(
    cipher_spec,
    key_spec,
    scorer_params: Dict[str, Any],
    demo: Dict[str, Any],
) -> float | None:
    """Compute the pct score for the actual plaintext."""
    try:
        plaintext_idx = demo.get("plaintext_idx")
        if plaintext_idx is None:
            raise ValueError("plaintext_idx missing")
        scoring_cfg = ScoringConfig(**scorer_params)
        scoring_cfg.encoding_dir = demo["encoding_dir"]
        cipher_cfg = build_cipher_config(
            cipher=cipher_spec,
            key=key_spec,
            ciphertext=np.asarray(demo["ciphertext_idx"], dtype=np.uint8),
            wli=demo.get("wli"),
            device=Device.CPU,
            encoding_dir=demo["encoding_dir"],
            initial_text_permutation_indices=None,
            initial_keys=None,
        )
        scorer = build_scorer(cipher_cfg, scoring_cfg)
        return float(scorer.score(plaintext_idx, demo.get("wli")))
    except Exception as exc:
        print(f"[GroundTruth] Unable to score plaintext: {exc}")
        return None


def solve_with_wrappers(
    demo: Dict[str, Any],
    cipher_spec,
    key_spec,
    scorer_params: Dict[str, Any],
):
    """Minimal Vigenere run using the ergonomic by_name wrapper helpers."""
    solver_spec = api.SolverSpec.beam(
        beam_width=18,
        stop_score=0.55,
        plateau_rounds=6,
        plateau_min_delta=1e-4,
        log_interval=25,
        seed=1337,
        **_progress_kwargs(demo),
    )
    solution = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(scorer_params),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
        initial_keys=[demo["secret_key"]],
    )
    _print_summary("Wrapper Beam", solution)


def solve_with_general_map(demo: Dict[str, object], scorer_params: Dict[str, Any]):
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
        plateau_rounds=4,
        plateau_min_delta=1e-4,
        **_progress_kwargs(demo),
        seed=4242,
    )
    solution = api.run(
        text=demo["ciphertext"],
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        scorer_params=dict(scorer_params),
        wli_data=demo["wli"],
        encoding_dir=demo["encoding_dir"],
        telemetry_on=True,
    )
    _print_summary("General Map Beam", solution)


def _print_summary(label: str, solution):
    score = getattr(solution, "score", None)
    key = getattr(solution, "key", [])
    plaintext = getattr(solution, "plaintext_rune", "") or getattr(solution, "plaintext_str", "")
    snippet = plaintext[:120] + ("..." if len(plaintext) > 120 else "")
    print(f"\n[{label}] score={score:.3f}" if score is not None else f"\n[{label}]")
    print("  Plaintext:", snippet)
    print("  Key:", key)


def main():
    demo = _demo_ciphertext()
    key_len = len(cast(List[int], demo["secret_key"]))
    cipher_spec, key_spec = api.define_cipher(
        name="vigenere",
        key_len=key_len,
        default_key=True,
    )
    scorer_params = _make_scorer_params(demo)
    target = _score_ground_truth(cipher_spec, key_spec, scorer_params, demo)
    if target is not None:
        print(f"[GroundTruth] pct.win10 target score: {target:.6f}")
    solve_with_wrappers(demo, cipher_spec, key_spec, scorer_params)
    solve_with_general_map(demo, scorer_params)


if __name__ == "__main__":
    main()

