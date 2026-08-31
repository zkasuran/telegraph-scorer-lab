#!/usr/bin/env python3
"""Build a lexical (no-blob, ~1MB) scorer per intent and measure its ROC ceiling locally.

Why this shape. The four remaining winnable slots run 24MB transformer builds that the node's
fixture gate times out on (twelve recorded time-budget rejections, all at 24MB; every sub-1.1MB
build tonight was ruled on in minutes). A foreign small carrier evaluated fine but only reached
j=13 because it was tuned for another intent. So the carrier has to be small AND tuned for the
intent it serves, which is exactly a lexical build with W_EMB=0.

The gate here is local only, to rank configs before spending registrations: what matters is whether
a config reaches j=15 (all fixture pairs split at one threshold), since the champions sit at
0.9986-0.9998 and only f32(15/15)=1.0 clears them.
"""
import json, os, re, subprocess, sys

ROOT = os.environ.get("SCORER_ROOT", os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scorer")))
LIB = os.path.join(ROOT, "module", "src", "lib.rs")
WASM = os.path.join(ROOT, "module/target/wasm32-unknown-unknown/release/telegraph_scorer.wasm")

def patch(intent, vals):
    s = open(LIB).read()
    s = re.sub(r'(TELEGRAPH_INTENT: \[u8; 32\] = \*b")[^"]+(")',
               lambda m: m.group(1) + intent.ljust(32)[:32] + m.group(2), s)
    for k, v in vals.items():
        decl = re.search(rf"const {k}: (f32|u32|usize) = ", s)
        if not decl:
            print(f"    (skip {k}: not in lib.rs)"); continue
        ty = decl.group(1)
        rep = repr(float(v)) if ty == "f32" else str(int(v))
        s = re.sub(rf"const {k}: {ty} = [^;]+;", f"const {k}: {ty} = {rep};", s)
    open(LIB, "w").write(s)

def build(out):
    r = subprocess.run(["cargo", "build", "--release", "--target", "wasm32-unknown-unknown"],
                       cwd=os.path.join(ROOT, "module"), capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-400:]); return None
    subprocess.run(["cp", WASM, out], check=True)
    return os.path.getsize(out)

def roc(P):
    N = len(P); best = (None, -9)
    for t in sorted({v for p in P for v in p}):
        v = (sum(1 for g, _ in P if g >= t) - sum(1 for _, b in P if b >= t)) / N
        if v > best[1]: best = (t, v)
    return best

def measure(w):
    out = "/tmp/sc-" + os.path.basename(w) + ".json"
    r = subprocess.run(["/tmp/dump", w, "/tmp/tri.json", out], capture_output=True, text=True)
    if r.returncode != 0: return None
    s = json.load(open(out))["scores"]
    ids = sorted(k[:-5] for k in s if k.endswith("|good"))
    P = [(s[i + "|good"], s[i + "|bad"]) for i in ids]
    t, k = roc(P)
    return k, t, sum(1 for g, b in P if g > b), len(P), sum(1 for g, b in P if g >= t and b >= t)

CFGS = json.load(open(sys.argv[1]))
orig = open(LIB).read()
print(f"{'name':18} {'intent':22} {'bytes':>9} {'ROC j/N':>9} {'t*':>11} {'wins':>7} {'hi':>3}")
try:
    for c in CFGS:
        patch(c["intent"], c["vals"])
        out = f"/tmp/lex-{c['name']}.wasm"
        sz = build(out)
        if sz is None: continue
        m = measure(out)
        if m is None: print(f"{c['name']:18} {c['intent']:22} {sz:>9} load failed"); continue
        k, t, wins, N, hi = m
        print(f"{c['name']:18} {c['intent']:22} {sz:>9} {k:9.4f} {t:11.6g} {str(wins)+'/'+str(N):>7} {hi:3}")
finally:
    open(LIB, "w").write(orig)
    print("\nlib.rs restored")
