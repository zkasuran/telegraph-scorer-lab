#!/usr/bin/env python3
"""Sweep the threshold, not just its ROC argmax, when hardening a held slot.

At the argmax the split is largest but pairs often straddle it with a tiny gap, so the window
    ULP(1)/min_gap  <  top  <  half_ulp(j/N)*N / D
is empty: no top is both ordered and rounds away. Moving T up sheds those straddling pairs, which
costs split count but opens the window. The best hardening is the largest j whose window is
non-empty, so enumerate every candidate threshold (the score levels themselves) and pick it.

A slot is only worth re-registering when the rail's j/N beats the margin we already hold; otherwise
the current build stays and the slot is logged as not hardenable with this base.
"""
import os
import json, os, struct, sys
ULP1 = 2 ** -24
HALF = 2 ** -25
def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]

TAG = {'URL_SCAN':'us','AGENT_TASK':'at','TVL_LOOKUP':'tv2','STOCK_PRICE':'sp',
       'MEDIA_AUTHENTICITY_CHECK':'mac','VIDEO_VERIFICATION':'vv','FINANCIAL_DATA':'fd',
       'RESEARCH_SYNTHESIS':'rs'}
W = {r['intent']: r for r in json.load(open(
     os.environ.get("WRAPPABLE", os.path.join(os.path.dirname(__file__), "wrappable.json"))))}

def best(P, N):
    out = []
    for T in sorted({v for p in P for v in p} | {0.05*i for i in range(1,20)}):
        if not 0 < T < 1: continue
        split = sum(1 for g,b in P if g >= T > b)
        lost  = sum(1 for g,b in P if b >= T > g)
        hi    = [(g,b) for g,b in P if g >= T and b >= T]
        if lost or any(g <= b for g,b in hi): continue
        need  = max((ULP1/(g-b) for g,b in hi), default=0.0)
        G = [g for g,b in P if g >= T]; H = [b for g,b in P if b >= T]
        D = sum(1-g for g in G) - sum(1-b for b in H)
        j = len(G) - len(H)
        allow = HALF*N/D if D > 0 else float('inf')
        if need >= allow: continue
        top = (need*allow) ** 0.5 if need > 0 else (0.0 if allow == float('inf') else allow*0.1)
        out.append((j, split, T, top, need, allow))
    out.sort(key=lambda r: (-r[0], r[3]))
    return out

jobs = []
print(f"{'intent':26} {'held m':>12} {'best j/N':>11} {'T':>13} {'top':>10} verdict")
for it in json.load(open('/tmp/zerotraffic.json')):
    p = f"/tmp/sc-live-{it}.json"
    if not os.path.exists(p): print(f"{it:26} no dump"); continue
    s = json.load(open(p))["scores"]
    ids = sorted(k[:-5] for k in s if k.endswith("|good"))
    P = [(s[i+"|good"], s[i+"|bad"]) for i in ids]
    rec = W[it]; N = rec['N']; held = rec['m']
    cands = best(P, N)
    if not cands:
        print(f"{it:26} {held:12.8f} {'-':>11} {'-':>13} {'-':>10} no feasible window at any T")
        continue
    j, split, T, top, need, allow = cands[0]
    local_ratio = j/len(P)
    print(f"{it:26} {held:12.8f} {local_ratio:11.4f} {T:13.8g} {top:10.2e} "
          f"window ({need:.1e},{allow:.1e})")
    jobs.append({"name": f"{TAG[it]}_h", "intent": it, "base": f"/tmp/live-{it}.wasm",
                 "t": float(T), "top": float(top)})
json.dump(jobs, open('/tmp/jobs10.json','w'), indent=1)
print(f"\n{len(jobs)} hardenings queued")
