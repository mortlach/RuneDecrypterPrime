# import numpy as np
# from rune_decrypter_prime.patche_old_ui.api import define_map, preview, KeySpec
#
# N = 29
# def add_map(pt, k): return (pt + k) % N
# spec = define_map(function=add_map, N=N, name="add-map")
#
# ct = np.array([1,2,3,4,5], dtype=np.uint8)
# key = KeySpec.const(value=3)  # fully specified key for preview
#
# pt = preview(ct, cipher=spec, key=key, direction="decrypt", device="cpu")
# print("pt:", pt)
