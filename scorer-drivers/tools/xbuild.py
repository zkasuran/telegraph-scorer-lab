#!/usr/bin/env python3
"""Build a TRANSFORMER (--features minilm, ~24MB) scorer per intent and measure its ROC ceiling.

Every build in the last few rounds was compiled without the feature, so `W_EMB` was inert and the
blob absent: those runs measured the lexical path only. The two slots that flipped tonight
(IMAGE_VERIFICATION, TELEGRAPH_KNOWLEDGE) won at exactly 1.0 on transformer builds, so the embedding
path plainly reaches the ceiling on this fixture set. This runs the same shape for the intents where
it was never tried.
"""
import json, os, re, subprocess, sys
ROOT = os.environ.get("SCORER_ROOT", os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scorer")))
LIB=os.path.join(ROOT,"module/src/lib.rs")
WASM=os.path.join(ROOT,"module/target/wasm32-unknown-unknown/release/telegraph_scorer.wasm")

def patch(intent, vals):
    s=open(LIB).read()
    s=re.sub(r'(TELEGRAPH_INTENT: \[u8; 32\] = \*b")[^"]+(")',
             lambda m: m.group(1)+intent.ljust(32)[:32]+m.group(2), s)
    for k,v in vals.items():
        d=re.search(rf"const {k}: (f32|u32|usize) = ",s)
        if not d: print(f"    (skip {k})"); continue
        ty=d.group(1); rep=repr(float(v)) if ty=="f32" else str(int(v))
        s=re.sub(rf"const {k}: {ty} = [^;]+;",f"const {k}: {ty} = {rep};",s)
    open(LIB,"w").write(s)

def roc(P):
    N=len(P); best=(None,-9)
    for t in sorted({v for p in P for v in p}):
        v=(sum(1 for g,_ in P if g>=t)-sum(1 for _,b in P if b>=t))/N
        if v>best[1]: best=(t,v)
    return best

CFGS=json.load(open(sys.argv[1]))
orig=open(LIB).read()
print(f"{'name':8} {'intent':22} {'bytes':>9} {'ROC j/N':>9} {'t*':>11} {'wins':>7} {'hi':>3}")
try:
    for c in CFGS:
        patch(c["intent"], c["vals"])
        r=subprocess.run(["cargo","build","--release","--target","wasm32-unknown-unknown",
                          "--features","minilm"],cwd=os.path.join(ROOT,"module"),
                         capture_output=True,text=True)
        if r.returncode!=0:
            print(f"{c['name']:8} BUILD FAILED: {r.stderr[-200:]}"); continue
        out=f"/tmp/x-{c['name']}.wasm"
        subprocess.run(["cp",WASM,out],check=True)
        sz=os.path.getsize(out)
        sc=f"/tmp/sc-x-{c['name']}.json"
        d=subprocess.run(["/tmp/dump",out,"/tmp/tri.json",sc],capture_output=True,text=True)
        if d.returncode!=0:
            print(f"{c['name']:8} {c['intent']:22} {sz:>9} load failed: {d.stdout.strip()[:40]}"); continue
        s=json.load(open(sc))["scores"]
        ids=sorted(k[:-5] for k in s if k.endswith("|good"))
        P=[(s[i+"|good"],s[i+"|bad"]) for i in ids]
        t,k=roc(P)
        print(f"{c['name']:8} {c['intent']:22} {sz:>9} {k:9.4f} {t:11.6g} "
              f"{str(sum(1 for g,b in P if g>b))+'/'+str(len(P)):>7} "
              f"{sum(1 for g,b in P if g>=t and b>=t):3}")
finally:
    open(LIB,"w").write(orig); print("\nlib.rs restored")
