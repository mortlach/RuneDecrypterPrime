# ============================================================
# File: rune_decrypter_prime/ui/beginner.py
# ============================================================
from __future__ import annotations
from typing import List, Union, Sequence

from rune_decrypter_prime.ciphers.vigenere_cipher import A as VIG_A

CiphertextLike = Union[str, List[int], List[str]]

__all__ = [
    "repeat_to_length",
    "encrypt_vigenere_indices",
    "solve_vigenere",
    "solve_beginner",
]

def repeat_to_length(pattern: List[int], length: int) -> List[int]:
    if length < 0:
        raise ValueError("length must be non-negative")
    if not pattern and length > 0:
        raise ValueError("pattern must not be empty when length > 0")
    if length == 0:
        return []
    out: List[int] = []
    i = 0
    L = len(pattern)
    while len(out) < length:
        out.append(int(pattern[i % L]))
        i += 1
    return out[:length]

def encrypt_vigenere_indices(
    pt_idx: List[int],
    key_idx: List[int],
    A: int = int(VIG_A),
) -> List[int]:
    L = len(pt_idx)
    stream = repeat_to_length(key_idx, L)
    return [(int(pt_idx[i]) + int(stream[i])) % A for i in range(L)]


from rune_decrypter_prime.ui import api as _ui_run

# File: rune_decrypter_prime/ui/beginner.py
# --- updated solve_vigenere() only ---
from typing import Any, Dict, List, Optional, Union

from rune_decrypter_prime.ui.api import run as _ui_run
from rune_decrypter_prime.ui.api import define_cipher, SolveSpec

# Accepts ciphertext as list[int] (indices) or rune/latin strings (your normalize handles this).
def solve_vigenere(
    ciphertext: Union[str, List[int]],
    *,
    key_len: int,
    beam_width: int = 32,
    # If you pass wli_data (list[[pos, word_len], ...]) we’ll use WLI in scoring.
    # If you don’t pass it (or explicitly set use_wli=False), we’ll run char-only.
    wli_data: Optional[List[List[int]]] = None,
    use_wli: Optional[bool] = None,
    device: str = "cpu",
    seed: int = 12345,
    scorer_params: Optional[Dict[str, Any]] = None,
    logging: Optional[Dict[str, Any]] = None,
):
    """
    Beginner-friendly Vigenère solve:
      - If wli_data is provided OR use_wli=True  -> use word-break scoring too.
      - If neither is provided (or use_wli=False)-> char-only scoring.
    """

    # Decide WLI usage (explicit flag wins; else presence of wli_data).
    use_wli_final = bool(use_wli) if use_wli is not None else bool(wli_data)

    # Build cipher + default repeating key spec
    cipher_spec, key_spec = define_cipher(name="vigenere", key_len=int(key_len))

    # Optimizer: tiny, deterministic beam with seed propagated
    solve_spec = SolveSpec.beam(beam_width=beam_width, K=int(key_len), seed=int(seed))

    # Scorer prefs: keep it very small and explicit
    sp: Dict[str, Any] = {
        "objective": "pct.logp.win10",
        "n_char": 2,
        "n_wli": 2,
        "win": 10,
        # make intent unambiguous at the UI layer
        "include_char": True,
        "use_word_breaks": use_wli_final,
        # if WLI is off, force char-only weights (avoid accidental renorm)
        "weights": (1.0, 0.0) if not use_wli_final else (0.5, 0.5),
    }
    if scorer_params:
        # Caller overrides last; allow power users to tweak if needed
        sp.update(scorer_params)

    # Call the single UI entrypoint.
    # NOTE: api.run.solve supports wli_data (wired to _normalize_ct_and_wli(..., wli_override=...)).
    return _ui_run.solve(
        ciphertext,
        cipher=cipher_spec,
        key=key_spec,
        solve=solve_spec,
        device=device,
        scorer="rune",
        scorer_params=sp,
        logging=logging,
        wli_data=(wli_data or []),  # [] is accepted; if empty and use_wli_final=False => char-only
    )



def solve_beginner(
    cipher: str,
    text: CiphertextLike,
    *,
    key_len: Optional[int] = None,
    beam_width: Optional[int] = None,
    wli_data: Optional[Sequence[Sequence[int]]] = None,   # <-- NEW
    budgets: Optional[dict] = None,
) -> Any:
    if key_len is not None:
        spec, key_spec = define_cipher(name=cipher, key_len=int(key_len))
    else:
        spec, key_spec = define_cipher(name=cipher)

    kwargs = {}
    if beam_width is not None:
        kwargs["beam_width"] = int(beam_width)
    solve_spec = SolveSpec.beam(**kwargs)

    return _ui_run.solve(
        text=text,
        cipher=spec,
        key=key_spec,
        solve=solve_spec,
        device="cpu",
        scorer="rune",
        scorer_params=None,
        logging=None,
        wli_data=wli_data,   # <-- pass through
    )
