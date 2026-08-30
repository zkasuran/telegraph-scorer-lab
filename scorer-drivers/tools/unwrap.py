#!/usr/bin/env python3
"""Read the two-band post-map off a champion binary and rebuild its base.

A champion of the m45 family is a base scoring module with one extra function
appended and the `rank_answer` export redirected at it. That function calls the
base scorer and applies

    f(s) = (1 - high) + high * s      s >= threshold
    f(s) = low * s                    s <  threshold

This decodes the appended body (inner function index, threshold, high, low) and
writes the base back out with `rank_answer` pointing at the inner function again,
so the base can be hash-matched against the binary it was cut from.

    python3 unwrap.py <champion.wasm> [--out base.wasm]
"""
import hashlib
import struct
import sys

import wasmx


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


def decode_band(b, off, size):
    """Pull (inner, threshold, high, low) out of an appended band function."""
    body = b[off:off + size]
    # locals vec, then the six args forwarded, then call <inner>
    i = body.index(b"\x20\x05\x10") + 3
    inner, i = wasmx.u32(body, i)
    fl = [v for _, v in wasmx.f32consts(b, off, size)]
    if len(fl) != 4:
        raise SystemExit(f"expected 4 f32 consts in the band body, found {len(fl)}")
    threshold, one_minus_high, high, low = fl
    if abs((1.0 - high) - one_minus_high) > 1e-6:
        raise SystemExit(f"consts are not a two-band step: {fl}")
    return inner, threshold, high, low


def rebuild_base(b, inner):
    """Drop the appended function and point `rank_answer` back at `inner`."""
    secs = [(sid, bytearray(b[off:off + size])) for sid, off, size in wasmx.sections(b)]
    out = bytearray(b[:8])
    for sid, payload in secs:
        if sid == 3:                                    # function
            n, i = wasmx.u32(payload, 0)
            payload = bytearray(leb(n - 1)) + payload[i:-1]
        elif sid == 7:                                  # export
            payload = bytearray(rewrite_exports(payload, inner))
        elif sid == 10:                                 # code
            n, i = wasmx.u32(payload, 0)
            ends = []
            j = i
            for _ in range(n):
                bsz, k = wasmx.u32(payload, j)
                ends.append((j, k + bsz))
                j = k + bsz
            payload = bytearray(leb(n - 1)) + payload[i:ends[-1][0]]
        out += bytes([sid]) + leb(len(payload)) + payload
    return bytes(out)


def rewrite_exports(payload, target_index):
    n, i = wasmx.u32(payload, 0)
    parts = [leb(n)]
    for _ in range(n):
        ln, i = wasmx.u32(payload, i)
        name = payload[i:i + ln]
        i += ln
        kind = payload[i]
        i += 1
        idx, i = wasmx.u32(payload, i)
        if kind == 0 and bytes(name) == b"rank_answer":
            idx = target_index
        parts += [leb(ln), bytes(name), bytes([kind]), leb(idx)]
    return b"".join(parts)


def main():
    path = sys.argv[1]
    out = None
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    b = open(path, "rb").read()
    bodies = wasmx.code_bodies(b)
    inner, t, high, low = decode_band(b, *bodies[-1])
    print(f"{path}")
    print(f"  bytes      {len(b)}")
    print(f"  sha256     {hashlib.sha256(b).hexdigest()}")
    print(f"  inner      func {inner}")
    print(f"  threshold  {t!r}")
    print(f"  high       {high!r}   -> f(s>=t) = {1.0 - high!r} + {high!r}*s")
    print(f"  low        {low!r}   -> f(s<t)  = {low!r}*s")
    base = rebuild_base(b, inner)
    print(f"  base bytes {len(base)}  sha256 {hashlib.sha256(base).hexdigest()}")
    if out:
        open(out, "wb").write(base)
        print(f"  wrote      {out}")


if __name__ == "__main__":
    main()
