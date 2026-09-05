"""Search for a repeating key using multiplication modulo 29.

We define the cipher rule ourselves, then pass it to the usual RDP search.
The rest of the request should look familiar from the Vigenere examples.
"""

from __future__ import annotations

import sys

import numpy as np

from rdp import api
from rdp.data.runeglish import Runeglish
from tutorials.v1.data.plaintext_fixtures import plaintext1_rev, word_breaks1_rev
from tutorials.v1.support.tutorial_utils import oracle_stop_score, print_stop_summary

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
N = 29
TUTORIAL_SEED = 12345
KEY_LEN = 13
MIN_MATCH_RATIO = 1.0
DIRECTION = api.TextDirection.RIGHT_TO_LEFT


def mult_map(pt: int, k: int) -> int:
    return pt * k % N


def _preview(label: str, text: str, limit: int = 160) -> None:
    suffix = "..." if len(text) > limit else ""
    print(f"{label} length: {len(text)}")
    print(f"{label} preview: {text[:limit]}{suffix}")


def main() -> None:
    # Leave zero out of the key: multiplying by zero loses the original rune
    # value, so we couldn't undo it.
    rng = np.random.default_rng(TUTORIAL_SEED)
    key_nums = rng.integers(1, N, size=KEY_LEN).tolist()
    pt_idx = [int(v) for v in plaintext1_rev]
    wli = [list(pair) for pair in word_breaks1_rev]
    pt_runes = Runeglish.to_rune(pt_idx, wli)
    stream = [key_nums[i % KEY_LEN] for i in range(len(pt_idx))]
    ct_idx = [int(p * k % N) for p, k in zip(pt_idx, stream)]
    ct_runes = Runeglish.to_rune(ct_idx, wli)
    print("Repeating multiply problem")
    print(f"encoding direction: {DIRECTION.value}")
    print(f"map: ct = pt * k mod {N}")
    print(f"key length: {KEY_LEN}")
    _preview("plaintext runes", pt_runes)
    _preview("ciphertext runes", ct_runes)
    # Pass our multiplication function to define_cipher_map. It gives us a
    # CipherSpec we can use in the same request as before.
    cipher = api.experimental.define_cipher_map(mult_map, alphabet_size=N)
    key_spec = api.KeySpec.repeating(length=KEY_LEN)
    scorer_params = api.ScoringConfig(
        character_lane_enabled=True,
        word_length_lane_enabled=True,
        character_order_weights={2: 0.3},
        word_length_order_weights={2: 0.7},
    )
    # We use the original message to choose a stopping score. That's help we
    # have in this example, but wouldn't have for an unknown plaintext.
    stop = oracle_stop_score(
        pt_idx,
        wli,
        scorer_params,
        device="cpu",
        encoding_dir=DIRECTION,
        margin=0.02,
        min_score=0.5,
        fallback=0.55,
    )
    print_stop_summary("Repeating Multiply Beam", stop)
    # A wider beam keeps more alternatives. The plateau settings let the
    # search stop when it isn't improving enough. Keep the seed fixed and
    # change one setting at a time when comparing runs.
    solve_spec = api.SolverSpec.beam_search(
        width=32,
        maximum_children_per_parent=24,
        plateau_rounds=8,
        plateau_minimum_delta=0.0001,
        target_score=stop.stop_score,
        seed=TUTORIAL_SEED,
        rounds=0,
    )
    request = api.RunSpec(
        problem_input=api.RuneIndexInput(indices=ct_idx, word_lengths=wli),
        cipher=cipher,
        key_space=key_spec,
        solver=solve_spec,
        scoring=scorer_params,
        telemetry_enabled=True,
        text_direction=DIRECTION,
    )
    result = api.run(request)
    recovered = result.plaintext_text or ""
    print(
        "Recovered plaintext preview:",
        str(recovered)[:120] + ("..." if len(str(recovered)) > 120 else ""),
    )
    recovered_idx = [int(value) for value in result.plaintext]
    match_ratio = sum(a == b for a, b in zip(recovered_idx, pt_idx, strict=True)) / len(
        pt_idx
    )
    print(f"Match ratio: {match_ratio:.3f}")
    api.display.print_result(
        result, spec=request, options=api.display.SummaryOptions.for_tutorial()
    )
    if match_ratio < MIN_MATCH_RATIO:
        raise AssertionError(
            "repeating-multiply tutorial did not recover exact plaintext"
        )


if __name__ == "__main__":
    main()
