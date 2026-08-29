# rune_decrypter_prime/io/rng.py
from __future__ import annotations
import hashlib
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class RNGController:
    """
    Deterministic, namespaced RNG factory.
    - Fixed top-level seed.
    - Child streams derived by (seed, hierarchical name).
    - Uses NumPy Generator(PCG64). No reliance on global np.random.
    """

    seed: int
    prefix: str = ""

    def _qualified(self, name: str) -> str:
        name = str(name)
        if not self.prefix:
            return name
        return f"{self.prefix}.{name}"

    def _derive_uint128(self, qualified_name: str) -> int:
        # hash(seed:name) → 128-bit int for PCG64
        h = hashlib.sha256(
            f"{int(self.seed)}:{qualified_name}".encode("utf-8")
        ).digest()
        return int.from_bytes(h[:16], "big", signed=False)

    def child(self, name: str) -> np.random.Generator:
        """
        Return an independent, deterministic stream named `name`.
        The same (seed, name) yields the same sequence across processes/machines.
        """
        qn = self._qualified(name)
        s128 = self._derive_uint128(qn)
        bitgen = np.random.PCG64(s128)
        return np.random.Generator(bitgen)

    def scope(self, prefix: str) -> "RNGController":
        """
        Create a nested controller so that:
          ctrl.scope('optim').child('SA') == ctrl.child('optim.SA')
        """
        new_prefix = prefix if not self.prefix else f"{self.prefix}.{prefix}"
        return RNGController(seed=int(self.seed), prefix=new_prefix)
