# FAQ

**Why did my result change?**  
Check the solver seed, `TextDirection`, input permutation, scoring configuration,
asset profile and compute/backend choices. A fixed seed only makes a comparison
meaningful when the rest of the effective run is the same.

**Can I use a GPU?**  
Yes. Runs default to `api.ComputeDevice.CPU`; request
`api.ComputeDevice.CUDA` when you want CUDA execution. The source installer can
provision and verify a supported NVIDIA/Torch runtime, but availability does not
silently change the requested device. See
[CUDA provisioning](development/cuda_installation.md) and
[compute device and scorer backend](setup/scorer_backend_selection.md).

**How do I add my own cipher or solver?**  
See [add a cipher](howto/add_cipher.md) and
[add a solver](howto/add_solver.md).
