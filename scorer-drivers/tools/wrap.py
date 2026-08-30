#!/usr/bin/env python3
"""Append a two-rail calibration to one of our scoring modules.

The base module's `rank_answer` is treated as a black-box score s in [0,1]. One
function is appended that calls it and returns

    f(s) = 1 - H*(1 - s)      s >= T      top rail, rises to 1
    f(s) = L * s              s <  T      bottom rail, rises off 0

then the `rank_answer` export is pointed at the new function. Everything else in
the module keeps its original bytes: embeddings, allocator, memory, the intent
marker and every other export.

f is strictly increasing for 0 < H < 1, 0 < L, L*T < 1 - H*(1-T), so the ranking
of any two answers the base separates is untouched. Only the spread moves.

Why 1 - H*(1-s) rather than (1-H) + H*s: with H at 1e-6 the second form loses the
whole correction to rounding, the first keeps it in the low mantissa bits, so the
top rail stays ordered at a far smaller H.

The bottom rail at L=1e-9 lands in the f32 denormal range, where the spacing is
around 1e-45. Every answer below the threshold stays perfectly distinct there
while adding under 1e-9 to the mean, which is invisible to an f32 margin.

    python3 wrap.py --base b.wasm --out o.wasm --t 0.45 --H 1e-6 --L 1e-9
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


def band_body(inner, t, high, low):
    return b"".join([
        bytes([0x01, 0x01, TYPE_F32]),                       # one f32 local, index 6
        bytes([LOCAL_GET, 0, LOCAL_GET, 1, LOCAL_GET, 2,
               LOCAL_GET, 3, LOCAL_GET, 4, LOCAL_GET, 5]),   # forward the six args
        bytes([CALL]), leb(inner),
        bytes([LOCAL_SET, 6]),                               # s = inner(..)
        bytes([LOCAL_GET, 6, F32_CONST]), f32(t), bytes([F32_GE]),
        bytes([IF, TYPE_F32]),
        bytes([F32_CONST]), f32(1.0),
        bytes([F32_CONST]), f32(high),
        bytes([F32_CONST]), f32(1.0),
        bytes([LOCAL_GET, 6, F32_SUB, F32_MUL, F32_SUB]),     # 1 - H*(1-s)
        bytes([ELSE]),
        bytes([F32_CONST]), f32(low),
        bytes([LOCAL_GET, 6, F32_MUL]),                      # L*s
        bytes([END, END]),
    ])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--t", type=float, required=True)
    p.add_argument("--H", type=float, required=True)
    p.add_argument("--L", type=float, default=1e-9)
    p.add_argument("--inner", type=int, default=None,
                   help="function index of the raw scorer; defaults to whatever rank_answer points at")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args()

    if not 0.0 < a.t < 1.0:
        raise SystemExit("--t must be in (0,1)")
    if not 0.0 < a.H < 1.0:
        raise SystemExit("--H must be in (0,1)")
    if not a.L > 0.0:
        raise SystemExit("--L must be positive")
    # the rails must not cross at the threshold, or f stops increasing there
    top_at_t = 1.0 - a.H * (1.0 - a.t)
    if a.L * a.t >= top_at_t:
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
        raise SystemExit(f"inner {inner} type {types[inner]} != rank_answer type {types[rank[2]]}")

    new_index = len(types)                      # zero imports, so this is the next func index
    body = band_body(inner, a.t, a.H, a.L)

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
    if not a.quiet:
        print(f"{a.out}")
        print(f"  base    {a.base} ({len(base)} bytes, inner func {inner})")
        print(f"  map     f(s) = 1 - {a.H:g}*(1-s)  for s >= {a.t:g};  {a.L:g}*s below")
        print(f"  rails   top starts {top_at_t!r}   bottom ends {a.L * a.t!r}")
        print(f"  bytes   {len(out)}")
        print(f"  sha256  {hashlib.sha256(out).hexdigest()}")
        print(f"  keccak  {k.hexdigest()}")
    else:
        print(f"{a.out} {len(out)} {k.hexdigest()}")


if __name__ == "__main__":
    sys.exit(main())
