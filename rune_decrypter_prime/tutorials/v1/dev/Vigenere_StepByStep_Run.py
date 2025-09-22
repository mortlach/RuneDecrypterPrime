# ============================================================
# File: rune_decrypter_prime/examples/Vigenere_StepByStep_Run.py
# Purpose: Run the step-by-step tutorial from the console/IDE.
# Supports:
#   - Module: python -m rune_decrypter_prime.examples.Vigenere_StepByStep_Run
#   - Direct: python rune_decrypter_prime/examples/Vigenere_StepByStep_Run.py
# ============================================================

# Local-import shim for direct execution from this file
if __name__ == "__main__" and __package__ is None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from rune_decrypter_prime.tutorials.v1.Vigenere_StepByStep import walkthrough_vigenere

def main() -> None:
    _ = walkthrough_vigenere(explain=True)

if __name__ == "__main__":
    main()
