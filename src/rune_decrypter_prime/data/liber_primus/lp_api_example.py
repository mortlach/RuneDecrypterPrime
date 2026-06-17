from pathlib import Path
from lp_transcript import LPTranscript

TRANSCRIPT = Path(r"liber-primus__transcription--master.txt")

doc = LPTranscript.from_file(TRANSCRIPT)
print(doc.summary())

# By page / line / word
p0 = doc.page(0)
print(p0.text())                  # whole page as lines
print(p0.lines()[0].text())        # first line of the page

# Absolute glyph indexing (counting backwards allowed)
pos = doc.glyph_pos(1000)
print(pos)

window = doc.around_glyph(1000, left=40, right=40).text()
print(window)

# Jump to a specific word by page/line/word-in-line coordinates
wid = doc.word_id_at(chapter=0, page=0, line=0, word_in_line=2)
print(doc.word(wid).text())
