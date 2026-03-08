from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Path):
        return obj.as_posix()
    raise TypeError(f"Unsupported JSON type: {type(obj).__name__}")


@dataclass
class StageTraceWriter:
    output_path: Path

    def append(self, event: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(event)
        with self.output_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    default=_json_default,
                )
                + "\n"
            )

