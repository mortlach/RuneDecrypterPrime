# Canonical problem package surface for v1
from .spec import ProblemSpec
from .instance import ProblemInstance
from .runtime import DecryptionProblem  # legacy monolith, preserved under the package

__all__ = ["ProblemSpec", "ProblemInstance", "DecryptionProblem"]
