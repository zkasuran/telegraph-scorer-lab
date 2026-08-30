#!/usr/bin/env python3
"""Pick the rail that is both promotable and wrap-proof, per base, instead of guessing `top`.

Three constraints fight each other, and the reason reg2055 came out with a 1.1e-6 crack is that
`top` was picked by hand rather than solved for.

  ordering   a pair with BOTH scores above T sits on the top rail, so it needs
             top*(g-b) to survive f32 rounding near 1.0 (ulp there is ~6e-8):
                 top > 6e-8 / (g - b)          for every such pair
  wrap-proof any wrap of our rail can report at most j/N, and we report
             j/N - (top/N)*Sum(1-b) over the top-rail bads, so the most a rival can
             extract is that difference. It must stay under the node's promotion epsilon:
                 top < EPS*N / Sum(1-b)
  margin     j itself, which grows with T until T starts cutting above a fixture good.

So for each threshold there is an interval of safe `top`, empty when a top-rail pair is too
tight to separate at a `top` small enough to be wrap-proof. The best rail is the largest j whose
interval is non-empty, and `top` is then set at the geometric middle of that interval rather than
at either edge. When no pair straddles T at all the interval is unbounded below: top = 0, a flat
rail, exactly j/N, nothing to extract.

usage: optrail.py <dump.json> [N_fixtures]
"""
import json, glob, os, struct, sys

EPS = 1e-6
ULP1 = 2 ** -24          # half-spacing of f32 just below 1.0, ~6e-8

def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]

def load(p):
    s = json.load(open(p))["scores"]
    ids = sorted(k[:-5] for k in s if k.endswith("|good"))
    return [(s[i + "|good"], s[i + "|bad"]) for i in ids]

def solve(pairs, T, N):
    """Return (j, lost, top_lo, top_hi) for a rail at T over these fixture pairs."""
    j = lost = 0
    need_lo = 0.0
    sum_bad = 0.0
    for g, b in pairs:
        if g >= T > b:
            j += 1
        elif b >= T > g:
            lost += 1                       # the bad is railed above the good: a lost win
        elif g >= T and b >= T:
            if g <= b:
                lost += 1
                continue
            need_lo = max(need_lo, 2 * ULP1 / (g - b))
            sum_bad += (1.0 - b)
        # both below T: the low*s rail keeps their order, nothing to do
    top_hi = float("inf") if sum_bad == 0 else EPS * N / sum_bad
    return j, lost, need_lo, top_hi

def best(pairs, N):
    grid = sorted({round(v, 6) for g, b in pairs for v in (g, b)} | {0.05 * i for i in range(1, 20)})
    out = []
    for T in grid:
        if not 0 < T < 1: continue
        j, lost, lo, hi = solve(pairs, T, N)
        if lost: continue
        if lo >= hi: continue               # cannot be both ordered and wrap-proof here
        top = 0.0 if lo == 0 else (lo * hi) ** 0.5
        out.append((j, T, top, lo, hi))
    out.sort(key=lambda r: (-r[0], r[2]))
    return out

for p in sorted(sys.argv[1:] or glob.glob("/tmp/sc-*.wasm.json")):
    N = 15
    pairs = load(p)
    rows = best(pairs, N)
    name = os.path.basename(p)[6:-10]
    print(f"=== {name}  ({len(pairs)} local pairs, sizing for N={N}) ===")
    if not rows:
        print("   no threshold is both orderable and wrap-proof on the local bench")
        continue
    for j, T, top, lo, hi in rows[:4]:
        kind = "FLAT, nothing to extract" if top == 0 else f"top in ({lo:.2e}, {hi:.2e})"
        print(f"   j={j:3}/{len(pairs)}  T={T:<9.6g} top={top:.3e}  {kind}")
