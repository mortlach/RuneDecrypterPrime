# ============================================================
# rune_decrypter_prime/ui/__init__.py   (UI package manifest)
# Simple-by-default, expert-when-needed UI surface.
# Expose explicit submodules for stable imports.
# ============================================================

"""
UI layer: simple-by-default, expert-when-needed.

Import submodules explicitly, e.g.:
    from rune_decrypter_prime.ui.api import CipherSpec, KeySpec, SolveSpec, run
    from rune_decrypter_prime.ui.maps_api import define_map, define_cipher, preview, run_map
"""
__all__ = ["api", "maps_api", "wrappers"]
