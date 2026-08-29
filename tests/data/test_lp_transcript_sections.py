from __future__ import annotations
from rune_decrypter_prime.data.liber_primus.lp_transcript import LPTranscript


def test_section_by_label_lookup(tmp_path):
    content = "x-y-/\n%\nz-w-/\n%\n"
    path = tmp_path / "toy_transcript.txt"
    path.write_text(content, encoding="utf-8")
    doc = LPTranscript.from_file(path)
    doc.add_split_from_boundaries(
        "toy", boundaries_word_ids=[0, 2, 4], labels=["1.a", "1.b"]
    )
    section = doc.section_by_label(split="toy", label="1.b")
    assert section.text() == "z w"
