"""Try a period-eight Vigenere model on Welcome Pilgrim.

We supply the cipher family and key length, then ask RDP to find the eight
values. This leaves out part of the known construction. Watch for readable
stretches, but check the complete text before calling it a recovery.
"""

from rdp import api

# The period comes from the known solution; the eight key values are searched.
KEY_LENGTH = 8


def main() -> None:
    """Search the incomplete model, then compare with the solved text."""
    request = api.RunSpec(
        problem_input=api.liber_primus.source("welcome_pilgrim"),
        cipher=api.CipherSpec.vigenere(),
        key_space=api.KeySpec.repeating(length=KEY_LENGTH),
        solver=api.SolverSpec.beam_search(
            width=64,
            expansion=api.advanced.BeamExpansionMode.SWEEP,
            plateau_rounds=5,
            plateau_minimum_delta=0.0001,
            seed=2026,
            rounds=None,
        ),
        scoring=api.ScoringConfig(
            character_lane_enabled=True,
            wli_lane_enabled=True,
            character_order_weights={1: 0.3, 2: 0.7},
            wli_order_weights={1: 0.3, 2: 0.7},
            objective=api.advanced.ScoringObjective.percentile_log_probability(
                window_size=10
            ),
        ),
        text_direction=api.TextDirection.LTR,
    )

    result = api.run(request)
    if result.plaintext_runes is None:
        raise RuntimeError("the search did not return a candidate")

    print("Recovered key:", result.key)
    print("Score        :", result.score)
    print("Plaintext    :", result.plaintext_runes)

    exact_match = result.plaintext_runes == REFERENCE_RUNES
    print("Matches the complete solved text:", exact_match)
    if exact_match:
        raise AssertionError("the expected incomplete-model outcome changed")
    print("The search ran, but this model did not recover the complete text.")
    print("Next: allow positions that leave the rune and key cursor unchanged.")


# Canonical solved text, rendered as runes. Keep the source spelling WIDSOM.
# This reference is also used by the detailed Welcome Pilgrim workbook.
REFERENCE_RUNES = (
    "ᚹᛖᛚᚳᚩᛗᛖ ᚹᛖᛚᚳᚩᛗᛖ ᛈᛁᛚᚷᚱᛁᛗ ᛏᚩ ᚦᛖ ᚷᚱᛠᛏ ᛂᚩᚢᚱᚾᛖᚣ ᛏᚩᚹᚪᚱᛞ ᚦᛖ ᛖᚾᛞ ᚩᚠ ᚪᛚᛚ ᚦᛝᛋ "
    "ᛁᛏ ᛁᛋ ᚾᚩᛏ ᚪᚾ ᛠᛋᚣ ᛏᚱᛁᛈ ᛒᚢᛏ ᚠᚩᚱ ᚦᚩᛋᛖ ᚹᚻᚩ ᚠᛁᚾᛞ ᚦᛖᛁᚱ ᚹᚪᚣ ᚻᛖᚱᛖ ᛁᛏ ᛁᛋ ᚪ "
    "ᚾᛖᚳᛖᛋᛋᚪᚱᚣ ᚩᚾᛖ ᚪᛚᚩᛝ ᚦᛖ ᚹᚪᚣ ᚣᚩᚢ ᚹᛁᛚᛚ ᚠᛁᚾᛞ ᚪᚾ ᛖᚾᛞ ᛏᚩ ᚪᛚᛚ ᛋᛏᚱᚢᚷᚷᛚᛖ ᚪᚾᛞ "
    "ᛋᚢᚠᚠᛖᚱᛝ ᚣᚩᚢᚱ ᛁᚾᚾᚩᚳᛖᚾᚳᛖ ᚣᚩᚢᚱ ᛁᛚᛚᚢᛋᛡᚾᛋ ᚣᚩᚢᚱ ᚳᛖᚱᛏᚪᛁᚾᛏᚣ ᚪᚾᛞ ᚣᚩᚢᚱ ᚱᛠᛚᛁᛏᚣ "
    "ᚢᛚᛏᛁᛗᚪᛏᛖᛚᚣ ᚣᚩᚢ ᚹᛁᛚᛚ ᛞᛁᛋᚳᚩᚢᛖᚱ ᚪᚾ ᛖᚾᛞ ᛏᚩ ᛋᛖᛚᚠ ᛁᛏ ᛁᛋ ᚦᚱᚩᚢᚷᚻ ᚦᛁᛋ ᛈᛁᛚᚷᚱᛁᛗᚪᚷᛖ ᚦᚪᛏ ᚹᛖ "
    "ᛋᚻᚪᛈᛖ ᚩᚢᚱᛋᛖᛚᚢᛖᛋ ᚪᚾᛞ ᚩᚢᚱ ᚱᛠᛚᛁᛏᛁᛖᛋ ᛂᚩᚢᚱᚾᛖᚣ ᛞᛖᛖᛈ ᚹᛁᚦᛁᚾ ᚪᚾᛞ ᚣᚩᚢ ᚹᛁᛚᛚ ᚪᚱᚱᛁᚢᛖ ᚩᚢᛏᛋᛁᛞᛖ "
    "ᛚᛁᚳᛖ ᚦᛖ ᛁᚾᛋᛏᚪᚱ ᛁᛏ ᛁᛋ ᚩᚾᛚᚣ ᚦᚱᚩᚢᚷᚻ ᚷᚩᛝ ᚹᛁᚦᛁᚾ ᚦᚪᛏ ᚹᛖ ᛗᚪᚣ ᛖᛗᛖᚱᚷᛖ ᚹᛁᛞᛋᚩᛗ ᚣᚩᚢ ᚪᚱᛖ ᚪ ᛒᛖᛝ "
    "ᚢᚾᛏᚩ ᚣᚩᚢᚱᛋᛖᛚᚠ ᚣᚩᚢ ᚪᚱᛖ ᚪ ᛚᚪᚹ ᚢᚾᛏᚩ ᚣᚩᚢᚱᛋᛖᛚᚠ ᛠᚳᚻ ᛁᚾᛏᛖᛚᛚᛁᚷᛖᚾᚳᛖ ᛁᛋ ᚻᚩᛚᚣ ᚠᚩᚱ ᚪᛚᛚ ᚦᚪᛏ ᛚᛁᚢᛖᛋ ᛁᛋ "
    "ᚻᚩᛚᚣ ᚪᚾ ᛁᚾᛋᛏᚱᚢᚳᛏᛡᚾ ᚳᚩᛗᛗᚪᚾᛞ ᚣᚩᚢᚱ ᚩᚹᚾ ᛋᛖᛚᚠ"
)


if __name__ == "__main__":
    main()
