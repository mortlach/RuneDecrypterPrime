from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence
_ROOT = Path(__file__).resolve().parents[3]
_SRC = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from rune_decrypter_prime.api import Direction, KeySpec, SolverSpec, by_name, run
from rune_decrypter_prime.utils.pretty import print_run_report
from rune_decrypter_prime.utils.runeglish import Runeglish
from rune_decrypter_prime.utils.tutorial_utils import oracle_stop_score, print_stop_summary
from rune_decrypter_prime.data.cipher_tests.plaintext import plaintext_english_string


"""
Tutorial: Railfence (zig-zag) transposition without word boundaries.

This walkthrough:
    1. Encodes an Alice-in-Wonderland plaintext into runes (RTL) and strips spaces.
    2. Encrypts with a 3-rail fence to produce ciphertext lacking WLI.
    3. Builds the production railfence wrapper + scalar key spec (rails search range).
    4. Runs a small beam search to recover both plaintext and rail count.
    5. Prints a run, telemetry-friendly summary via `print_run_report`.
"""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TUTORIAL_SEED = 4242
TRUE_RAILS = 3


def encrypt_railfence(pt: str, rails: int) -> str:
    """Zig-zag write across rails, then read row-by-row."""
    if rails <= 1:
        return pt

    rows = [""] * rails
    r = 0
    step = 1
    for ch in pt:
        rows[r] += ch
        if r == 0:
            step = 1
        elif r == rails - 1:
            step = -1
        r += step
    return "".join(rows)


def _match_ratio(recovered: Sequence[int], reference: Sequence[int]) -> float:
    limit = min(len(recovered), len(reference))
    if limit == 0:
        return 0.0
    matches = sum(1 for i in range(limit) if recovered[i] == reference[i])
    return matches / float(limit)


def main() -> None:
    direction = Direction.RTL
    pt_latin = plaintext_english_string
    pt_idx, _, pt_runes = Runeglish.encode_english_to_runes(pt_latin, direction=direction.value)
    pt_runes_nosp = pt_runes.replace(" ", "")

    ct_runes = encrypt_railfence(pt_runes_nosp, TRUE_RAILS)
    ct_idx = Runeglish.rune_to_pos(ct_runes)

    cipher_spec = by_name.cipher("railfence", min_rails=2, max_rails=6)
    key_spec = KeySpec.scalar(max_val=6)
    scorer_params = dict(
        objective="pct.logp.win10",
        include_char=True,
        use_word_breaks=False,  # ciphertext lost spacing during transposition
        char_weights={2: 1.0},
        wli_weights={},
        encoding_dir=direction,
    )

    stop = oracle_stop_score(
        pt_idx,
        None,
        scorer_params,
        device="cpu",
        encoding_dir=direction,
        margin=0.02,
        min_score=0.50,
        fallback=0.54,
    )
    print_stop_summary("Railfence Beam", stop)

    solver_spec = SolverSpec.beam(
        beam_width=64,
        log_interval=20,
        stop_score=stop.stop_score,
        plateau_rounds=40,
        plateau_min_delta=1e-4,
        seed=TUTORIAL_SEED,
    )

    solution = run(
        text=ct_runes,
        cipher=cipher_spec,
        key=key_spec,
        solver=solver_spec,
        device="cpu",
        scorer="rune",
        scorer_params=scorer_params,
        wli_data=None,
        force_no_wli=True,
        encoding_dir=direction,
        telemetry_on=True,
    )

    recovered = getattr(solution, "plaintext_rune", "") or getattr(solution, "plaintext_str", "")
    preview = recovered[:120] + ("..." if len(recovered) > 120 else "")
    print(f"Recovered plaintext preview:\n{preview}")

    match_ratio = _match_ratio(solution.plaintext_idx, pt_idx)
    match_ok = match_ratio >= 0.95

    print_run_report(
        title="Railfence Tutorial",
        cipher="railfence",
        solution=solution,
        match_ok=match_ok,
        app_version="tutorial-1.0",
        key_idx=[TRUE_RAILS],
        key_len=1,
        ct_idx=ct_idx,
        ct_rune=ct_runes,
        pt_rune_ref=pt_runes_nosp,
        pt_idx_ref=pt_idx,
        wli=None,
    )


if __name__ == "__main__":
    main()

