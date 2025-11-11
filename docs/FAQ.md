# FAQ

**How do I install without the command line?**  
Open in PyCharm -> add a Virtualenv -> install packages via the Packages panel -> mark `rune_decrypter_prime/` as a source root.

**Why did my result change?**  
Check the solver seed, `Direction`, and any input permutation. Ensure scorer objective and model match.

**Can I use GPU?**  
v1 surface is CPU. Torch back-end exists; enable only if your environment supports it.

**How do I add my own cipher/solver?**  
See `howto/add_cipher.md` and `howto/add_solver.md`.

