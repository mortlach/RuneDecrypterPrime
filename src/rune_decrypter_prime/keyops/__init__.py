# -*- coding: utf-8 -*-
# rune_decrypter_prime/keyops/__init__.py
from __future__ import annotations
from rune_decrypter_prime.keyops.base_keyops import KeyOpBase, KeyCaps
from rune_decrypter_prime.keyops.registry import register_keyop, has, get, available

# from rune_decrypter_prime.keyops.matrix import MatrixKey, MatrixKeyConfig  # ensures 'matrix' is registered
from rune_decrypter_prime.keyops.permutation_ops import (
    PermutationKeyOps,
    PermutationKeyConfig,
)
from rune_decrypter_prime.keyops.vector import VectorKeyOps, VectorKeyConfig
from rune_decrypter_prime.keyops.composite import CompositeKeyOps, CompositeKeyConfig
# from rune_decrypter_prime.keyops.affine import AffineKey, AffineKeyConfig

__all__ = [
    "KeyCaps",
    "KeyOpBase",
    "register_keyop",
    "has",
    "get",
    "available",
    #   "MatrixKey", "MatrixKeyConfig",
    # "KeySpec",
    "PermutationKeyOps",
    "PermutationKeyConfig",
    "VectorKeyOps",
    "VectorKeyConfig",
    "CompositeKeyOps",
    "CompositeKeyConfig",
    #   "AffineKey", "AffineKeyConfig",
]
__all__.extend(["VectorKeyOps", "VectorKeyConfig"])
