# ============================================================
# rune_decrypter_prime/ciphers/base_keyops.py
# ============================================================
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np


# todo nto realy used properly yet
class KeyOpsBase(ABC):
    @abstractmethod
    def random(self, rng: np.random.Generator) -> np.ndarray: ...
    @abstractmethod
    def mutate(self, key: np.ndarray, rng: np.random.Generator) -> np.ndarray: ...
    @abstractmethod
    def normalize(self, key: np.ndarray) -> np.ndarray: ...
    # optional:
    def crossover(self, k1: np.ndarray, k2: np.ndarray, rng: np.random.Generator) -> np.ndarray: ...
