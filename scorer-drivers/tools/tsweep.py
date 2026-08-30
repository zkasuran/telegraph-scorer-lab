#!/usr/bin/env python3
"""Where does a rail threshold actually buy fixture pairs, and at what wrap cost?

Four categories per pair at threshold T:
  split      g >= T > b     the good rails to 1, the bad to ~0. This is the margin.
  lost       b >= T > g     the BAD rails over the good. Fatal, fails the ordering gate.
  both-hi    g,b >= T       both on the top rail. Needs top > 0 to stay ordered, and that
                            top is exactly the crack a rival can wrap. Costly.
  both-lo    g,b <  T       both on low*s. Order preserved for free in the denormal range,
                            contributes nothing to the margin and nothing to wrap exposure.
The sweep so far only looked at T >= 0.45. On these bases the ROC is flat from 0.01 up, so
every one of those probes measured the same point. The interesting region is far lower, where
both-lo pairs turn into splits.
"""
import json, sys, struct
EPS, ULP = 1e-6, 2 ** -24
def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]

def load(p):
    s = json.load(open(p))["scores"]
    ids = sorted(k[:-5] for k in s if k.endswith("|good"))
    return [(s[i + "|good"], s[i + "|bad"]) for i in ids]

def cats(P, T):
    split = lost = hi = lo = 0
    need = 0.0; sb = 0.0
    for g, b in P:
        if g >= T > b: split += 1
        elif b >= T > g: lost += 1
        elif g >= T and b >= T:
            hi += 1
            if g <= b: lost += 1
            else:
                need = max(need, 2 * ULP / (g - b)); sb += (1.0 - b)
        else: lo += 1
    return split, lost, hi, lo, need, sb

label = sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]
P = load(sys.argv[1]); N = len(P)
NF = 15
print(f"=== {label}  ({N} local pairs; wrap bound sized for the node's N={NF}) ===")
print(f"{'T':>10} {'split':>6} {'lost':>5} {'both-hi':>8} {'both-lo':>8} {'top needed >':>13} "
      f"{'top allowed <':>14} feasible")
vals = sorted({g for g, _ in P} | {b for _, b in P})
grid = [1e-6, 1e-5, 3e-5, 5e-5, 8e-5, 1e-4, 1.5e-4, 2e-4, 3e-4, 5e-4, 8e-4, 1e-3, 3e-3, 1e-2, 0.05, 0.45]
for T in grid:
    sp, ls, hi, lo, need, sb = cats(P, T)
    allowed = float("inf") if sb == 0 else EPS * NF / sb
    feas = "-" if ls else ("FLAT top=0" if hi == 0 else ("yes" if need < allowed else "no"))
    print(f"{T:10g} {sp:6} {ls:5} {hi:8} {lo:8} {need:13.2e} {allowed:14.2e} {feas}")
