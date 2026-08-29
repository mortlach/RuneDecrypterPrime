from __future__ import annotations

"Offline builder for canonical NOSE/WLI cipher-test book fixtures.\n\nEdit the constants below and run from an IDE. Historical NPZ imports are not\nhandled here: supplied trusted archives remain source material, while new\nfixtures are generated with the current product tokenizer.\n"
import json
import sys
from pathlib import Path
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
from rune_decrypter_prime.utils.runeglish import Runeglish

SOURCE_BOOKS: tuple[Path, ...] = ()
OUTPUT_ROOT = SRC_ROOT / "rune_decrypter_prime" / "data" / "cipher_tests" / "books"
SOURCE_LABEL = "public-domain source supplied by user"
REDISTRIBUTION_NOTE = "Public-domain source selected by user"


def build_one(source_path: Path) -> None:
    source = source_path.resolve()
    text = source.read_text(encoding="utf-8")
    book_id = source.name
    counts: dict[str, int] = {}
    word_counts: dict[str, int] = {}
    for direction in ("ltr", "rtl"):
        pt, wli, _runes = Runeglish.encode_english_to_runes(text, direction=direction)
        pt_array = np.asarray(pt, dtype=np.uint8)
        wli_array = np.asarray(wli, dtype=np.uint8).reshape(-1, 2)
        if len(pt_array) != len(wli_array):
            raise ValueError(f"{source.name}: plaintext/WLI length mismatch")
        np.savez_compressed(
            OUTPUT_ROOT / f"{book_id}_{direction}.npz",
            pt_nose_data=pt_array,
            wli_nose_data=wli_array,
        )
        counts[direction] = len(pt_array)
        word_counts[direction] = int(np.count_nonzero(wli_array[:, 0] == 0))
    if word_counts["ltr"] != word_counts["rtl"]:
        raise ValueError(f"{source.name}: LTR/RTL word counts disagree")
    metadata = {
        "schema_version": 1,
        "book_id": book_id,
        "title": source.stem,
        "source": SOURCE_LABEL,
        "tokenizer": "canonical RDP Runeglish",
        "format": "nose+wli",
        "redistribution_note": REDISTRIBUTION_NOTE,
        "ltr_token_count": counts["ltr"],
        "rtl_token_count": counts["rtl"],
        "word_count": word_counts["ltr"],
    }
    (OUTPUT_ROOT / f"{book_id}.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main() -> None:
    if not SOURCE_BOOKS:
        raise RuntimeError("Configure SOURCE_BOOKS before running the offline builder")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for source in SOURCE_BOOKS:
        build_one(source)


if __name__ == "__main__":
    main()
