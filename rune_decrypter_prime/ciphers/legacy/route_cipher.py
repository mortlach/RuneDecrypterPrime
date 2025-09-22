# ============================================================
# rune_decrypter_prime/ciphers/route_cipher.py   (Route: snake / spiral_in)
# ============================================================
import numpy as np
from rune_decrypter_prime.ciphers.pipeline import CipherPipelineMixin, ArrayU8

class RouteTranspositionCipher(CipherPipelineMixin):
    """
    Route transposition on a WxH grid filled row-wise with plaintext.
    Key: [route_id, width]
      route_id: 0 = snake (boustrophedon rows)
                1 = spiral_in (clockwise, from top-left, inward)
      width: positive integer; height = ceil(L / width)
    Encryption (reference): ct[i] = pt[ route[i] ] for route over 0..L-1
    Decrypt (implemented):   pt[ route[i] ] = ct[i]
    """
    A = 29

    def __init__(self, cfg, *, text_transposition="fwd", key_transposition="fwd"):
        super().__init__(
            text_transposition=getattr(cfg, "text_transposition", "fwd"),
            key_transposition=getattr(cfg, "key_transposition", "fwd"),
        )
        self.cfg = cfg
        intr_exact  = getattr(cfg, "interruptors_exact", None)
        intr_legacy = getattr(cfg, "interruptors", None)
        chosen = intr_exact if intr_exact is not None else intr_legacy
        self._default_interrupt_idx = np.asarray(chosen, dtype=np.intp) if chosen is not None else None

    def _core_decrypt_batch(self, ct_tr: ArrayU8, keys_tr: ArrayU8) -> ArrayU8:
        if keys_tr.ndim == 1:
            keys_tr = keys_tr[None, :]
        B, K = keys_tr.shape
        assert K == 2, "Route key must be [route_id, width]"
        L = int(ct_tr.size)
        out = np.empty((B, L), dtype=np.uint8)
        for b in range(B):
            route_id = int(keys_tr[b, 0])
            W = int(keys_tr[b, 1])
            route = self._route_indices(L, W, route_id)
            # invert: pt[route[i]] = ct[i]
            pt = np.empty(L, dtype=np.uint8)
            pt[route] = ct_tr
            out[b] = pt
        return out

    @staticmethod
    def _route_indices(L: int, W: int, route_id: int) -> np.ndarray:
        if W <= 0:
            raise ValueError("width must be positive")
        H = (L + W - 1) // W
        # valid positions are 0..L-1 in row-wise indexing (r*W + c)
        if route_id == 0:
            # snake rows: even rows left->right, odd rows right->left
            order = []
            for r in range(H):
                row = [r*W + c for c in range(W)]
                if r % 2 == 1:
                    row.reverse()
                order.extend([idx for idx in row if idx < L])
            return np.asarray(order, dtype=np.int64)
        elif route_id == 1:
            # spiral in, clockwise, from top-left
            top, left, bottom, right = 0, 0, H-1, W-1
            order = []
            def push(r, c):
                idx = r*W + c
                if idx < L:
                    order.append(idx)
            while left <= right and top <= bottom:
                for c in range(left, right+1): push(top, c)
                for r in range(top+1, bottom+1): push(r, right)
                if top < bottom:
                    for c in range(right-1, left-1, -1): push(bottom, c)
                if left < right:
                    for r in range(bottom-1, top, -1): push(r, left)
                top += 1; left += 1; bottom -= 1; right -= 1
            return np.asarray(order, dtype=np.int64)
        else:
            raise ValueError("unknown route_id; use 0=snake, 1=spiral_in")
