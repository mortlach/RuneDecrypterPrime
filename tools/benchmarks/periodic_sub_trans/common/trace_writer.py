from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rune_decrypter_prime.io.artifact_policy import artifact_json_value


@dataclass
class StageTraceWriter:
    output_path: Path

    def append(self, event: dict[str, Any]) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        trace_root = self.output_path.parent.resolve()
        payload = artifact_json_value(dict(event), root=trace_root)
        with self.output_path.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )

