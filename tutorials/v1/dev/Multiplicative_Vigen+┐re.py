# import numpy as np
# from rune_decrypter_prime.patche_old_ui import define_map, define_cipher, run_map, KeySpec, SolveSpec
#
# N = 29
# def multiply_map(pt: int, k: int) -> int:
#     return (pt * k) % N
#
# spec = define_map(function=multiply_map, N=N, degeneracy="forbid", name="mult-vig")
# cipher, key = define_cipher(spec=spec, key=KeySpec.repeat(len=4))
# solve = SolveSpec.beam(width=6, seed=7)
#
# ct = np.array([5, 1, 12, 0, 28, 7, 14, 21], dtype=np.uint8)
# sol = run_map.solve(text=ct, cipher=cipher, key=key, solve=solve, device="cpu")
#
# print("pt:", sol.plaintext_idx)
# print("key:", sol.key)
# print("telemetry:", sol.meta["telemetry"])
