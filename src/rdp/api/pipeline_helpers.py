from __future__ import annotations


def coerce_wli_for_config(wli):
    """Convert public WLI pairs into the mutable core-configuration shape."""
    if wli is None:
        return None
    converted = []
    for pair in wli:
        if pair is None:
            continue
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise ValueError("wli entries must be (pos_in_word, word_len) pairs")
        pos = int(pair[0])
        ln = int(pair[1])
        converted.append([pos, ln])
    return converted
