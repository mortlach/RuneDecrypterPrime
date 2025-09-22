# # ----------------------------------------------------------------------
# # RuneAlphabet – minimal interface expected by ciphers / scorer
# # ----------------------------------------------------------------------
# from ..utils.runeglish import Runeglish
# from typing import List, Optional, Sequence
#
#
# from typing import List, Sequence
#
# class RuneAlphabet:
#     def __init__(self):
#         self.runes = [
#             "ᚠ", "ᚢ", "ᚦ", "ᚩ", "ᚱ", "ᚳ", "ᚷ", "ᚹ", "ᚻ", "ᚾ", "ᛁ", "ᛂ", "ᛇ", "ᛈ", "ᛉ", "ᛋ", "ᛏ",
#             "ᛒ", "ᛖ", "ᛗ", "ᛚ", "ᛝ", "ᛟ", "ᛞ", "ᚪ", "ᚫ", "ᚣ", "ᛡ", "ᛠ"
#         ]
#         self.positions = list(range(len(self.runes)))
#         self.latin_canon = [
#             "F", "U", "TH", "O", "R", "C", "G", "W", "H", "N", "I", "J", "EO", "P", "X", "S",
#             "T", "B", "E", "M", "L", "(I)NG", "OE", "D", "A", "AE", "Y", "IO", "EA"
#         ]
#
#         # Rune ↔ Position
#         self.rune2pos = {r: p for p, r in enumerate(self.runes)}
#         self.rune2pos["ᛄ"] = self.rune2pos["ᛂ"]
#         self.pos2rune = {p: r for p, r in enumerate(self.runes)}
#
#         # Rune ↔ Latin
#         self.rune2latin = {r: l for r, l in zip(self.runes, self.latin_canon)}
#         self.rune2latin["ᛄ"] = self.rune2latin["ᛂ"]
#         self.latin2rune = {l: r for l, r in zip(self.latin_canon, self.runes)}
#         self.latin2pos = {l: p for p, l in enumerate(self.latin_canon)}
#         self.pos2latin = {p: l for p, l in enumerate(self.latin_canon)}
#
#         # Normalization mappings
#         self.latin2rune.update({
#             'ING': self.latin2rune["(I)NG"],
#             'NG': self.latin2rune["(I)NG"],
#             'Z': self.latin2rune["S"],
#             'K': self.latin2rune["C"],
#             'Q': self.latin2rune["C"],
#             'IA': self.latin2rune["IO"],
#             'V': self.latin2rune["U"],
#         })
#         self.latin2pos.update({
#             'ING': self.latin2pos["(I)NG"],
#             'NG': self.latin2pos["(I)NG"],
#             'Z': self.latin2pos["S"],
#             'K': self.latin2pos["C"],
#             'Q': self.latin2pos["C"],
#             'IA': self.latin2pos["IO"],
#             'V': self.latin2pos["U"],
#         })
#
#         self.BIGRAMS = {'TH', 'EO', 'NG', 'OE', 'AE', 'IA', 'IO', 'EA'}
#         self.TRIGRAM = 'ING'
#
#     def latin_to_rune(self, latin: str) -> str:
#         return self.latin2rune.get(latin, latin)
#
#     def latin_to_pos(self, latin: str) -> int:
#         return self.latin2pos.get(latin, latin)
#
#     def rune_to_latin(self, rune: str) -> str:
#         return self.rune2latin.get(rune, rune)
#
#     def rune_to_pos(self, rune: str) -> int:
#         return self.rune2pos.get(rune, rune)
#
#     def pos_to_rune(self, pos: int) -> str:
#         return self.pos2rune.get(pos, pos)
#
#     def pos_to_latin(self, pos: int) -> str:
#         return self.pos2latin.get(pos, pos)
#
#     def translate_to_gematria(self, word: str) -> str:
#         word = word.upper().replace("QU", "KW").translate(str.maketrans({"Q": "K"}))
#         res = []
#         i = 0
#         while i < len(word):
#             if word[i:i+3] == self.TRIGRAM:
#                 res.append(self.TRIGRAM)
#                 i += 3
#                 continue
#             if word[i:i+2] in self.BIGRAMS:
#                 res.append(word[i:i+2])
#                 i += 2
#                 continue
#             if word[i] in {"'", '"'}:
#                 i += 1
#                 continue
#             res.append(word[i])
#             i += 1
#         return ''.join([self.latin_to_rune(l) for l in res])
#
#     def get_wli_data_str(self, runewords_string: str) -> List[List[int]]:
#         words = runewords_string.split(" ")
#         return [[i, len(word)] for word in words for i, _ in enumerate(word)]
#
#     def get_wli_data_list(self, runewords: List[str]) -> List[List[int]]:
#         return [[i, len(word)] for word in runewords for i, _ in enumerate(word)]
#
#
#     def to_rune_latin(self, pt: Sequence[int], wli: Sequence[Sequence[int]], limit: int | None = None) -> str:
#         words, cur = [], []
#         for i, sym in enumerate(pt):
#             cur.append(self.pos_to_latin(sym))
#             if wli[i][0] == wli[i][1] - 1:
#                 words.append(''.join(cur))
#                 cur = []
#             if limit and len(' '.join(words)) >= limit:
#                 break
#         if cur:
#             words.append(''.join(cur))
#         return ' '.join(words)
#
#     def to_rune(self, pt: Sequence[int], wli: Sequence[Sequence[int]], limit: int | None = None) -> str:
#         words, cur = [], []
#         for i, sym in enumerate(pt):
#             cur.append(self.pos_to_rune(sym))
#             if wli[i][0] == wli[i][1] - 1:
#                 words.append(''.join(cur))
#                 cur = []
#             if limit and len(' '.join(words)) >= limit:
#                 break
#         if cur:
#             words.append(''.join(cur))
#         return ' '.join(words)
#
#     @property
#     def size(self) -> int:
#         return len(self.runes)
