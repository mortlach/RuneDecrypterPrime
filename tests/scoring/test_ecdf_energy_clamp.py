import numpy as np

from rune_decrypter_prime.scoring.language_model.language_model_prime_runtime import ECDFCache


def test_ecdf_energy_clamps_extremes() -> None:
    p = np.array([0.0, 1.0, 1.0 - 1e-12], dtype=np.float32)
    energy = ECDFCache.energy(p)
    assert np.isfinite(energy).all()
    assert (energy >= 0).all()
