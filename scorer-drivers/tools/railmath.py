#!/usr/bin/env python3
"""The rail's two-sided window, derived once and correctly, and the sanity checks that prove it.

The rail is   f(s) = 1 - top*(1-s)   for s >= T,    low*s   for s < T.

Reported margin over N fixture pairs, with G the goods on the top rail (all of them whenever the
rail wins its ordering) and H the bads that also land there:

    margin = (1/N) * [ sum_G (1 - top*(1-g)) + 0 ] - (1/N) * [ sum_H (1 - top*(1-b)) + eps_low ]
           = (|G| - |H|)/N  -  (top/N) * [ sum_G (1-g) - sum_H (1-b) ]  -  eps_low
           = j/N            -  (top/N) * D                              -  eps_low

with j = |G| - |H| and D = sum_G(1-g) - sum_H(1-b). D > 0 whenever any good sits below 1.0, which
is always. So the reported margin is BELOW j/N by (top/N)*D, and that shortfall is exactly what a
rival can still take by wrapping us, because any wrap tops out at j/N (the ROC ceiling).

Two constraints:
    ordering    top * (g-b) > ulp near 1.0 for every top-rail pair, else the pair ties and the
                win count drops. Binding pair is the tightest gap.
    wrap-proof  (top/N) * D < EPS, the node's promotion epsilon.

    =>   2*ulp(1)/min_gap  <  top  <  EPS*N/D

An empty window means that threshold cannot be both ordered and wrap-proof: move T, not top.
Earlier I wrote D as sum_H(1-b) alone, which drops the goods term and understates the correction.
That is corrected here and the assertions below fail if the formula is wrong.
"""
import json, os, struct, sys
ULP1 = 2 ** -24          # 2*half-ulp just below 1.0 = 2^-24
EPS  = 1e-6

def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]
def rail(s, T, top, low=1e-9):
    s = f32(s)
    if s >= f32(T):
        return f32(1.0) if top <= 0 else f32(1.0 - f32(f32(top) * f32(1.0 - s)))
    return f32(f32(low) * s)

def load(p):
    s = json.load(open(p))["scores"]
    ids = sorted(k[:-5] for k in s if k.endswith("|good"))
    return [(s[i + "|good"], s[i + "|bad"]) for i in ids]

def window(P, T, N=None):
    """(j, D, lo, hi, lost) for a rail at T. N defaults to len(P)."""
    N = N or len(P)
    G = [g for g, b in P if g >= T]
    H = [b for g, b in P if b >= T]
    lost = sum(1 for g, b in P if b >= T > g) + sum(1 for g, b in P if g >= T and b >= T and g <= b)
    gaps = [g - b for g, b in P if g >= T and b >= T and g > b]
    D = sum(1.0 - g for g in G) - sum(1.0 - b for b in H)
    lo = 0.0 if not gaps else ULP1 / min(gaps)
    hi = float("inf") if D <= 0 else EPS * N / D
    return len(G) - len(H), D, lo, hi, lost

def predict(P, T, top, N=None):
    N = N or len(P)
    j, D, lo, hi, lost = window(P, T, N)
    return j / N - (top / N) * D, j, D, lo, hi, lost

if __name__ == "__main__":
    # Self-check the algebra against the actual f32 rail on every dump we have.
    import glob
    worst = 0.0
    for p in sorted(glob.glob("/tmp/sc-*.wasm.json")):
        P = load(p)
        for T in (1e-4, 1e-3, 0.01, 0.1, 0.45, 0.5, 0.7, 0.9):
            for top in (0.0, 1e-6, 1e-5, 1e-3, 1e-2):
                pred, j, D, lo, hi, lost = predict(P, T, top)
                g = [rail(x, T, top) for x, _ in P]
                b = [rail(y, T, top) for _, y in P]
                real = sum(g) / len(g) - sum(b) / len(b)
                worst = max(worst, abs(real - pred))
    print(f"formula vs the real f32 rail, worst absolute error over every dump/T/top: {worst:.3e}")
    assert worst < 1e-7, "margin formula is wrong"
    print("margin = j/N - (top/N)*D  confirmed, D = sum_goods(1-g) - sum_hi-bads(1-b)")
