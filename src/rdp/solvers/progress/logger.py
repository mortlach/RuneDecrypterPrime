from __future__ import annotations

class SimpleLogger:
    def write(self, msg: str) -> None:
        print(msg)

class TQDMAdapter(SimpleLogger):
    # Placeholder; in repo use tqdm if available
    pass
