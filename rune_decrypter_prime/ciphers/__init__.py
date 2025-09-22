# -*- coding: utf-8 -*-
"""
Package export for the engine-level cipher registry.

The solver engine does:
    from rune_decrypter_prime.ciphers import registry as cipher_registry

By re-exporting the registry module here, that import works as intended.
"""
from . import registry as registry  # <-- re-export the module so cipher_registry.has/get work
