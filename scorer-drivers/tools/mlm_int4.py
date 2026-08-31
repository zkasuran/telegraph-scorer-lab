#!/usr/bin/env python3
"""Requantise minilm.bin's FFN matrices from per-tensor int8 (kind 0) to per-row int4 (kind 3).

Why: the node's fixture gate budget (~10 min, including module load) is a race for a 24MB module.
reg2101/reg2104 finished and won at margin exactly 1; reg2105 ran 10m26s and had its fixture set
truncated from 14 comparable cases to 11, so the same construction lost a slot to load time alone.
Halving the biggest matrices takes the blob from 22.9MB to ~13.5MB and ends the race.

kind 3 is already in the format and `minilm.rs` already decodes it (word table, gte-int4), so the
Rust side is untouched. Attention weights stay int8: the gte experiment recorded that all-int4
compounds into ties through twelve attention layers and collapsed comparable_cases 15 -> 8. Only the
two feed-forward matrices per layer, plus the word-embedding table, drop to 4 bits.

Per-row scales, not one per tensor: a row is one output unit and 4 bits leaves no headroom for an
outlier row to drag its neighbours to zero.

    python3 mlm_int4.py module/src/minilm.bin module/src/minilm-int4.bin
"""
import struct, sys
import numpy as np

H, LAYERS, INTER, VOCAB = 384, 6, 1536, 30522
NTENS = 5 + 16 * LAYERS

def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def f32(b, o): return struct.unpack_from("<f", b, o)[0]

# Tensor index -> (rows, cols) for the ones worth requantising. Index 0 is the word table
# (VOCAB x H); within each layer block the FFN matrices are the two big ones.
def shape_of(idx, ln):
    if idx == 0: return VOCAB, H
    if ln == INTER * H: return INTER, H          # FFN intermediate
    if ln == H * INTER: return H, INTER          # FFN output
    return None

src, dst = sys.argv[1], sys.argv[2]
b = open(src, "rb").read()
assert b[:4] == b"MLM1"
base = 8 + u32(b, 4) * 8
out = bytearray(b[:base])

o = base
converted = 0
for i in range(NTENS):
    start = o
    kind = b[o]; o += 1
    if kind == 3:
        r = u32(b, o); c = u32(b, o + 4); o += 8; o += r * 4; o += r * (c // 2)
        out += b[start:o]; continue
    if kind == 2:
        r = u32(b, o); o += 4; o += r * 4; ln = u32(b, o); o += 4; o += ln
        out += b[start:o]; continue
    scale = f32(b, o); o += 4
    ln = u32(b, o); o += 4
    data = o
    o += ln if kind == 0 else ln * 4
    sh = shape_of(i, ln) if kind == 0 else None
    if sh is None or ln < 400_000:
        out += b[start:o]; continue
    rows, cols = sh
    if cols % 2:                      # the reader packs cols/2 bytes per row
        out += b[start:o]; continue
    q8 = np.frombuffer(b[data:data + ln], dtype=np.int8).reshape(rows, cols).astype(np.float32) * scale
    amax = np.abs(q8).max(axis=1)
    amax[amax == 0] = 1.0
    rs = amax / 7.0
    q4 = np.clip(np.rint(q8 / rs[:, None]), -7, 7).astype(np.int8)
    lo = (q4[:, 0::2] & 0x0F).astype(np.uint8)
    hi = ((q4[:, 1::2] & 0x0F) << 4).astype(np.uint8)
    packed = (lo | hi).tobytes()
    out += bytes([3]) + struct.pack("<II", rows, cols) + rs.astype("<f4").tobytes() + packed
    converted += 1

open(dst, "wb").write(bytes(out))
print(f"in  {len(b)/1e6:7.2f} MB")
print(f"out {len(out)/1e6:7.2f} MB   ({converted} tensors requantised to int4)")
