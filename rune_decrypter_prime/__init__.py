# Pull-through modules so legacy names still resolve
from importlib import import_module
# interruptor = import_module("rune_decrypter.utils.interrupter")
# transposition = import_module("rune_decrypter.utils.transposition")
# ----------------------------------------------------------------------
# Debug flags (env controlled)
# ----------------------------------------------------------------------
import os

# Enable extra, potentially expensive, asserts when TRUE.
RUNE_DEBUG_CORE = os.getenv("RUNE_DEBUG_CORE", "0") == "1"
