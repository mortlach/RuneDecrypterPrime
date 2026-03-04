from __future__ import annotations

import torch


def pack_char_ngram(pt_t: torch.Tensor, n: int) -> torch.Tensor:
    bsz, length = pt_t.shape
    stride = pt_t.stride()
    width = length - n + 1
    return (pt_t.as_strided((bsz, width, n), (stride[0], stride[1], stride[1])) & 0x1F).to(torch.uint32)


def pack_wli_ngram(pt_t: torch.Tensor, wli_t: torch.Tensor, n: int) -> torch.Tensor:
    bsz, length = pt_t.shape
    s_pt = pt_t.stride()
    s_w = wli_t.stride()
    width = length - n + 1
    pt_win = pt_t.as_strided((bsz, width, n), (s_pt[0], s_pt[1], s_pt[1]))
    w_win = wli_t.as_strided((bsz, width, n, 2), (s_w[0], s_w[1], s_w[1], s_w[2]))
    rune = (pt_win & 0x1F).to(torch.int32)
    pos = (w_win[..., 0] & 0x3F).to(torch.int32)
    ln = (w_win[..., 1] & 0x3F).to(torch.int32)
    toks = torch.stack([rune[..., i] | (pos[..., i] << 5) | (ln[..., i] << 11) for i in range(n)], dim=-1)
    return toks.to(torch.uint32)
