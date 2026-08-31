#!/usr/bin/env python3
"""Find a SMALL base that separates an intent, so the rail can actually finish the node's gate.

The four winnable slots were attacked with 24MB transformer builds. The node's fixture gate has a
~10 minute budget including module load, and it has timed out on 24MB builds twelve times, so those
registrations can never be evaluated no matter how well the rail is sized. A sub-1.2MB carrier loads
in a fraction of the time; every reclaim that landed tonight was on one.

What matters in a carrier is its ROC ceiling j/N: the rail can reach f32(j/N) and no more, so the
carrier has to clear champ + 1e-6 at its own j. This dumps each candidate and ranks by that.
"""
import json, os, subprocess, sys
ROOT = os.environ.get("SCORER_ROOT", os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scorer")))
def roc(P):
    N=len(P); best=(None,-9)
    for t in sorted({v for p in P for v in p}):
        v=(sum(1 for g,_ in P if g>=t)-sum(1 for _,b in P if b>=t))/N
        if v>best[1]: best=(t,v)
    return best
def dump(p):
    out="/tmp/sc-"+os.path.basename(p)+".json"
    if not os.path.exists(out):
        r=subprocess.run(["/tmp/dump",p,"/tmp/tri.json",out],cwd=ROOT,capture_output=True,text=True)
        if r.returncode!=0: return None
    s=json.load(open(out))["scores"]
    ids=sorted(k[:-5] for k in s if k.endswith("|good"))
    return [(s[i+"|good"],s[i+"|bad"]) for i in ids]
print(f"{'carrier':38} {'bytes':>9} {'ROC j/N':>9} {'t*':>12} {'wins':>7} {'hi-pairs':>9}")
rows=[]
for p in sys.argv[1:]:
    if not os.path.exists(p): print(f"{p:38} missing"); continue
    P=dump(p)
    if P is None: print(f"{os.path.basename(p):38} load failed"); continue
    t,k=roc(P)
    wins=sum(1 for g,b in P if g>b)
    hi=sum(1 for g,b in P if g>=t and b>=t)
    sz=os.path.getsize(p)
    rows.append((k,sz,p,t,wins,hi,len(P)))
for k,sz,p,t,wins,hi,N in sorted(rows,reverse=True):
    print(f"{os.path.basename(p):38} {sz:>9} {k:9.4f} {t:12.6g} {str(wins)+'/'+str(N):>7} {hi:9}")
