# Lightweight alias so you can `import rdp`
import rune_decrypter_prime as _rdp_pkg
from rune_decrypter_prime import *  # noqa: F401,F403
from rune_decrypter_prime import api as api

__all__ = list(getattr(_rdp_pkg, "__all__", []) or ["rune_decrypter_prime_version"])
if "api" not in __all__:
    __all__.append("api")
