# import numpy as np
# from rune_decrypter_prime.patche_old_ui.api import define_map, define_cipher, run_map, KeySpec, SolveSpec
#
# N = 29
# perm = np.array([(i*7 + 3) % N for i in range(N)], dtype=np.uint8)
# table = np.zeros((N, 1), dtype=np.uint8)
# table[:, 0] = perm
#
# spec = define_map(table=table, N=N, degeneracy="forbid", name="mono-sub")
# cipher, key = define_cipher(spec=spec, key=KeySpec.repeat(len=1))
# solve = SolveSpec.beam(width=4, seed=11)
#
# ct = np.array([5,1,12,0,28,7,14,21], dtype=np.uint8)
# sol = run_map.solve(text=ct, cipher=cipher, key=key, solve=solve, device="cpu")
#
# print("pt:", sol.plaintext_idx)          # np.ndarray
# print("key:", sol.key)                   # found key indices
# print("telemetry:", sol.meta["telemetry"])
