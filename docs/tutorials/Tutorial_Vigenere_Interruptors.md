# Vigenere interruptor tutorials

Status: superseded duplicate

Use the active `tutorials/v1/examples/vigenere_interruptors_*.py` files. They
construct typed `api.InterruptorConfig` values and solve through `api.run`.
Tutorial/test ciphertext preparation reuses the existing fixture helper; there
is no public interruptor-specific encryption operation or runtime cipher object.
