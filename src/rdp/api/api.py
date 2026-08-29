# from __future__ import annotations
#
# """Backward-compatible public API surface for rune_decrypter_prime."""
#
# from rdp.api.run import RunAPI, solve
# from rdp.api.wrappers import by_name, cipher_instance
# from rdp.api.specs import CipherSpec, KeySpec, SolverSpec
#
# __all__ = [
#     "run",
#     "solve",
#     "define_map",
#     "define_cipher",
#     "preview",
#     "CipherSpec",
#     "KeySpec",
#     "SolverSpec",
#     "by_name",
#     "cipher_instance",
# ]
#
#
# run = RunAPI
#
#
# def define_map(*args, **kwargs):
#     from rdp.api import maps_api as _maps
#     return _maps.define_map(*args, **kwargs)
#
#
# def define_cipher(*args, **kwargs):
#     from rdp.api import maps_api as _maps
#     return _maps.define_cipher(*args, **kwargs)
#
#
# def preview(*args, **kwargs):
#     from rdp.api import maps_api as _maps
#     return _maps.preview(*args, **kwargs)
