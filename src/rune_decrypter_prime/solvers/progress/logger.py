from __future__ import annotations
from typing import Any, Dict

class SimpleLogger:
    def write(self, msg: str) -> None:
        print(msg)

class TQDMAdapter(SimpleLogger):
    # Placeholder; in repo use tqdm if available
    pass
