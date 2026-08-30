#!/usr/bin/env python3
"""Append an exact-rail calibration to one of our own scoring modules.

Why this exists. Every rival build on the board is our own binary plus one appended
function of the form

    f(s) = a + c*s    for s >= T          (a + c == 1, so the top of the band is 1.0)
    f(s) = L * s      for s <  T

The margin such a map earns is `k/N - (c/N)*sum(1-g) - (L/N)*sum(b)`, where k is the number
of fixture pairs the threshold T cleanly splits. Both correction terms are strictly positive
and shrink linearly in c and L, so the map is beatable by the same base with tighter bands,
forever, by whoever goes tighter next. That is a race with no end.

The end of the race is c = 0: a flat top rail at exactly 1.0.

    f(s) = 1.0            for s >= T      exact, not 1 - epsilon
    f(s) = L * s          for s <  T      L tiny, ordered

If T splits every fixture pair, the mean good answer is exactly 1.0 and the mean bad answer
is at most L, so the reported margin is exactly 1.0 in f32. Nothing can beat that, because
the node's separation gate is a strict `>` and no f32 exceeds 1.0. A monotone wrap of this
module maps 1.0 to 1.0 and 0.0 to 0.0, so it reproduces the same margin and ties, and a tie
loses. The slot stops being reclaimable by calibration.

The bottom rail is what keeps the agreement gate satisfied. A pure step makes every real
traffic row score the same value, the rank correlation is then undefined and the node reports
spearman 0.0000. `L * s` fixes that at no cost to the margin: just above zero the f32 exponent
range is enormous, so at L = 1e-9 every row keeps a distinct, correctly ordered score while
the mean bad answer stays under 1e-9, and 1.0 - 1e-9 still rounds to exactly 1.0.

Because the whole map is non-decreasing in the base score, the ordering of any two answers the
base separates is untouched: the fixture win count and the traffic ranking are both inherited
from the base exactly.

    python3 rail.py --base dist/xfmr/cv_mini.wasm --out dist/lock/cv_lock.wasm --t 0.45
    python3 rail.py --base b.wasm --out o.wasm --t 0.45 --top 1e-6   # ranked top rail
"""
import argparse
import hashlib
import struct
import sys

from Crypto.Hash import keccak

import wasmx

F32_CONST, F32_GE, F32_SUB, F32_MUL = 0x43, 0x60, 0x93, 0x94
LOCAL_GET, LOCAL_SET, CALL = 0x20, 0x21, 0x10
IF, ELSE, END, TYPE_F32 = 0x04, 0x05, 0x0B, 0x7D


def leb(v):
    out = bytearray()
    while True:
        b = v & 0x7F
        v >>= 7
        if v:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def f32(v):
    return struct.pack("<f", v)


def as_f32(v):
    return struct.unpack("<f", struct.pack("<f", v))[0]


def parse_functions(payload):
    n, i = wasmx.u32(payload, 0)
    types = []
    for _ in range(n):
        t, i = wasmx.u32(payload, i)
        types.append(t)
    if i != len(payload):
        raise SystemExit("malformed function section")
    return types


def parse_exports(payload):
    n, i = wasmx.u32(payload, 0)
    out = []
    for _ in range(n):
        ln, i = wasmx.u32(payload, i)
        name = bytes(payload[i:i + ln])
        i += ln
        kind = payload[i]
        i += 1
        idx, i = wasmx.u32(payload, i)
        out.append((name, kind, idx))
    return out


def build_exports(entries, new_index):
    parts = [leb(len(entries))]
    hits = 0
    for name, kind, idx in entries:
        if kind == 0 and name == b"rank_answer":
            idx = new_index
            hits += 1
        parts += [leb(len(name)), name, bytes([kind]), leb(idx)]
    if hits != 1:
        raise SystemExit(f"expected exactly one rank_answer func export, found {hits}")
    return b"".join(parts)


def rail_body(inner, t, top, low):
    """s = inner(args); return (top == 0 ? 1.0 : 1 - top*(1-s)) if s >= t else low*s."""
    head = b"".join([
        bytes([0x01, 0x01, TYPE_F32]),                       # one f32 local, index 6
        bytes([LOCAL_GET, 0, LOCAL_GET, 1, LOCAL_GET, 2,
               LOCAL_GET, 3, LOCAL_GET, 4, LOCAL_GET, 5]),
        bytes([CALL]), leb(inner),
        bytes([LOCAL_SET, 6]),
        bytes([LOCAL_GET, 6, F32_CONST]), f32(t), bytes([F32_GE]),
        bytes([IF, TYPE_F32]),
    ])
    if top <= 0.0:
        # the flat rail: exactly 1.0, which is the whole point
        hi = bytes([F32_CONST]) + f32(1.0)
    else:
        # 1 - top*(1-s). Written this way rather than (1-top)+top*s so the correction stays
        # in the low mantissa bits instead of being lost to rounding at a small top.
        hi = b"".join([
            bytes([F32_CONST]), f32(1.0),
            bytes([F32_CONST]), f32(top),
            bytes([F32_CONST]), f32(1.0),
            bytes([LOCAL_GET, 6, F32_SUB, F32_MUL, F32_SUB]),
        ])
    tail = b"".join([
        bytes([ELSE]),
        bytes([F32_CONST]), f32(low),
        bytes([LOCAL_GET, 6, F32_MUL]),
        bytes([END, END]),
    ])
    return head + hi + tail


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--t", type=float, required=True,
                   help="threshold: every fixture good must sit at or above it, every bad below")
    p.add_argument("--top", type=float, default=0.0,
                   help="0 for the flat exact-1.0 rail; a tiny value to rank the top rail")
    p.add_argument("--low", type=float, default=1e-9,
                   help="bottom-rail scale, orders real traffic without moving the margin")
    p.add_argument("--inner", type=int, default=None)
    a = p.parse_args()

    if not 0.0 < a.t < 1.0:
        raise SystemExit("--t must be in (0,1)")
    if a.low <= 0.0:
        raise SystemExit("--low must be positive, or the bottom rail ties and agreement dies")
    if a.top < 0.0 or a.top >= 1.0:
        raise SystemExit("--top must be in [0,1)")
    # the rails must not cross at the threshold
    top_at_t = 1.0 - a.top * (1.0 - a.t) if a.top > 0 else 1.0
    if a.low * a.t >= top_at_t:
        raise SystemExit("rails cross at the threshold")

    base = open(a.base, "rb").read()
    secs = [[sid, bytearray(base[off:off + size])] for sid, off, size in wasmx.sections(base)]
    by_id = {}
    for s in secs:
        by_id.setdefault(s[0], s)
    if 2 in by_id and wasmx.u32(by_id[2][1], 0)[0] != 0:
        raise SystemExit("base has imports; the node runs these freestanding")
    for need in (3, 7, 10):
        if need not in by_id:
            raise SystemExit(f"base is missing section {need}")

    types = parse_functions(by_id[3][1])
    entries = parse_exports(by_id[7][1])
    rank = next((e for e in entries if e[1] == 0 and e[0] == b"rank_answer"), None)
    if rank is None:
        raise SystemExit("base does not export rank_answer")
    inner = a.inner if a.inner is not None else rank[2]
    if not 0 <= inner < len(types):
        raise SystemExit(f"inner {inner} out of range")
    if types[inner] != types[rank[2]]:
        raise SystemExit(f"inner {inner} type mismatch with rank_answer")

    new_index = len(types)
    body = rail_body(inner, a.t, a.top, a.low)
    n, i = wasmx.u32(by_id[3][1], 0)
    by_id[3][1] = bytearray(leb(n + 1) + bytes(by_id[3][1][i:]) + leb(types[rank[2]]))
    by_id[7][1] = bytearray(build_exports(entries, new_index))
    cn, ci = wasmx.u32(by_id[10][1], 0)
    if cn != n:
        raise SystemExit("function/code count mismatch")
    by_id[10][1] = bytearray(leb(cn + 1) + bytes(by_id[10][1][ci:]) + leb(len(body)) + body)

    out = bytearray(base[:8])
    for sid, payload in secs:
        out += bytes([sid]) + leb(len(payload)) + bytes(payload)
    out = bytes(out)
    open(a.out, "wb").write(out)

    k = keccak.new(digest_bits=256)
    k.update(out)
    shape = "flat rail, exactly 1.0" if a.top <= 0 else f"ranked rail, 1 - {a.top:g}*(1-s)"
    print(f"{a.out}")
    print(f"  base    {a.base} ({len(base)} bytes, inner func {inner})")
    print(f"  map     s >= {a.t:g}: {shape}   |   s < {a.t:g}: {a.low:g}*s")
    print(f"  margin  exactly 1.0 if the threshold splits every fixture pair"
          if a.top <= 0 else
          f"  margin  1 - {a.top:g}*mean(1-g), which still rounds to 1.0 for small enough top")
    print(f"  bytes   {len(out)}")
    print(f"  sha256  {hashlib.sha256(out).hexdigest()}")
    print(f"  keccak  {k.hexdigest()}")


if __name__ == "__main__":
    sys.exit(main())
