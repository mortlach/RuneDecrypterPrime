# rune_decrypter_prime/ciphers/substitution_cipher.py
import numpy as np
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin, ArrayU8
from rune_decrypter_prime.keyops.permutation_ops import PermutationOps
from rune_decrypter_prime.ciphers.registry import register_cipher


@register_cipher("substitution")   # canonical name used by engine/tests
@register_cipher("mono")           # UX/Tutorial alias expected by users
class MixedAlphabetSubstitutionCipher(CipherPipelineMixin):
    """
    Monoalphabetic substitution over RuneGlish (A=29).
    Key is a permutation mapping C -> P of length A.
    Decrypt core: pt[i] = key_map[ct[i]].
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        # Config is single source of truth; pass pipeline modes from cfg
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg

        # default interrupters from config (accept exact or legacy)
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = (
            np.asarray(chosen, dtype=np.intp) if chosen is not None else None
        )
        # --- NEW: KeyOps for monoalphabetic mapping size A ---
        self.keyops = PermutationOps(cfg.key_length)

        # not additive
        self._additive_debug = False

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        # keys_tr: (B, A) permutation rows mapping C->P
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        return keys_tr[:, ct_tr]  # (B, L)
