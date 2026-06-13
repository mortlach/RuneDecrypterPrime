"""
DEPRECATED MODULE
-----------------
`rune_decrypter_prime.core.factory.build_solver` previously aliased the legacy
`RuneSolverEngine`.  The name is retained for compatibility, but new code should
use the API pipeline or instantiate the Stage-2 engine directly.
"""

from rune_decrypter_prime.core.solver_engine import RuneSolverEngine as build_solver

__all__ = ["build_solver"]
