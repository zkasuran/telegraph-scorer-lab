#!/usr/bin/env python3
"""Is a flat rail at the base's ROC argmax the ceiling of every wrap, even below 1.0?

The doctrine so far says only an exact-1.0 margin is wrap-proof. That is too weak a claim and
it matters, because four of the slots we are taking back cannot reach 1.0 (their fixtures do
not separate perfectly under any threshold). This checks the stronger statement.

Claim. For a base score s and any map g, margin(g) = mean g(good) - mean g(bad). Over
NON-DECREASING g the maximum is  K = max_t [#(good >= t) - #(bad >= t)] / N,  attained by the
step at the argmax. So a flat rail placed there cannot be beaten by any monotone wrap of it,
whatever its numeric value. Exceeding K requires a g that gives some bad a lower value than a
good it outscores in the raw, which reorders a pair and shows up in the node's win count.

Checked three ways per base: many random monotone maps, the exact best step, and a targeted
non-monotone map that is allowed to reorder.
"""
import json, glob, os, random, struct
def f32(x): return struct.unpack('<f', struct.pack('<f', x))[0]

def load(p):
    s = json.load(open(p))['scores']
    ids = sorted(k[:-5] for k in s if k.endswith('|good'))
    return [s[i+'|good'] for i in ids], [s[i+'|bad'] for i in ids]

def roc(g, b):
    N = len(g); best = (None, -9)
    for t in sorted(set(g + b)):
        v = (sum(1 for x in g if x >= t) - sum(1 for x in b if x >= t)) / N
        if v > best[1]: best = (t, v)
    return best

def marg(g, b, f):
    N = len(g)
    return sum(f(x) for x in g)/N - sum(f(x) for x in b)/N

def wins(g, b, f):
    return sum(1 for x, y in zip(g, b) if f(x) > f(y))

rnd = random.Random(11)
def rand_monotone():
    n = rnd.randint(2, 9)
    xs = sorted(rnd.random() for _ in range(n)); ys = sorted(rnd.random() for _ in range(n))
    def f(x):
        if x <= xs[0]:  return ys[0] * (x / xs[0] if xs[0] > 0 else 1.0)
        for i in range(len(xs) - 1):
            if xs[i] <= x <= xs[i+1]:
                w = (x - xs[i]) / (xs[i+1] - xs[i]) if xs[i+1] > xs[i] else 0.0
                return ys[i] + w * (ys[i+1] - ys[i])
        return ys[-1] + (1 - ys[-1]) * (x - xs[-1]) / (1 - xs[-1]) if xs[-1] < 1 else ys[-1]
    return f

def rand_multistep():
    """Several stacked thresholds: the shape a rival reaches for when one rail is not enough."""
    n = rnd.randint(2, 5)
    ts = sorted(rnd.random() for _ in range(n)); vs = sorted(rnd.random() for _ in range(n))
    def f(x):
        out = 0.0
        for t, v in zip(ts, vs):
            if x >= t: out = v
        return out
    return f

print(f"{'base':22} {'N':>3} {'ROC ceiling K':>14} {'t*':>10} {'best monotone':>14} {'best multistep':>15} {'non-monotone':>13} {'its wins':>9}")
for p in sorted(set(glob.glob('/tmp/sc-*.wasm.json'))):
    g, b = load(p)
    N = len(g); t, K = roc(g, b)
    bm = max(marg(g, b, rand_monotone()) for _ in range(6000))
    bs = max(marg(g, b, rand_multistep()) for _ in range(6000))
    # a non-monotone map built to exploit the pairs the base gets wrong: lift every good,
    # crush every bad, ignoring the raw ordering entirely
    gs, bs_ = set(g), set(b)
    def cheat(x, gs=gs): return 1.0 if x in gs else 0.0
    cm = marg(g, b, cheat); cw = wins(g, b, cheat)
    base_w = wins(g, b, lambda x: x)
    print(f"{os.path.basename(p)[6:-10]:22} {N:3} {K:14.9f} {t:10.6f} {bm:14.9f} {bs:15.9f} {cm:13.9f} {cw:>4}/{base_w:<4}")
print()
print("Reading: no monotone or multi-step map ever exceeds K, so a rail placed at t* is the top of")
print("that family. The non-monotone column does exceed it, and its win count is how the node sees")
print("that: it is a different scorer, not a rescaling.")
