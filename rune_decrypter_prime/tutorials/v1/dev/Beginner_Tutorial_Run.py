# ============================================================
# File: rune_decrypter_prime/examples/Beginner_Tutorial_Run.py
# Purpose: Canonical beginner runner for the tutorial track.
# - Uses only plain Python types (str, list[int], list[str]).
# - Imports the stable v1 tutorial façade (no NumPy, no expert knobs).
# - Runs bundled examples (incl. forward/reverse where available).
# - Shows how to paste your own ciphertext (string or list[int]/list[str]).
# ============================================================

# --- local-import for direct execution ---
if __name__ == "__main__":
    import sys
    from pathlib import Path
    # /repo/rune_decrypter_prime/examples/Beginner_Tutorial_Run.py → parents[2] == /repo
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "rune_decrypter_prime"))
# --- end local-import shim ---

from rune_decrypter_prime.tutorials.v1 import (
    solve_easy,
    print_solution,
    discover_builtin_examples,
)


def run_bundled_examples() -> None:
    """Execute the built-in tutorial examples shipped with the package."""
    for ex in discover_builtin_examples():
        print(f"\n=== Example: {ex.name} ({ex.cipher}) ===")
        res = solve_easy(ex.cipher, ex.ciphertext)
        print_solution(res)


def main() -> None:
    print("\n▶ Running bundled tutorial examples…")
    run_bundled_examples()

    # ── Try your own ciphertexts (copy/paste) ─────────────────────────────
    # Un-comment one or more of the snippets below and paste your data.

    # 1) String input — preset decides scoring channels automatically
    # my_str_ct = "⟨paste your rune ciphertext here⟩"
    # res1 = solve_easy("vigenere", my_str_ct)
    # print_solution(res1)

    # 2) List[int] input — forces char-only scoring (great teaching aid)
    # my_idx_ct = [7, 12, 1, 0, 5, 5, 8]
    # res2 = solve_easy("caesar", my_idx_ct)
    # print_solution(res2)

    # 3) List[str] input — tokens/runes/words as strings
    # my_tok_ct = ["ra", "nu", "ka", "te"]
    # res3 = solve_easy("mono", my_tok_ct)
    # print_solution(res3)


if __name__ == "__main__":
    main()
