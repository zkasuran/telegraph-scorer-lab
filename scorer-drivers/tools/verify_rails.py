#!/usr/bin/env python3
"""Load each rail in wazero and confirm it computes the map we asked for.

mkrails predicts the rail's output from a dump of the base. This runs the rail itself and
checks the prediction, so a mis-encoded threshold or a broken code section is caught here
rather than by the node after a registration is already spent.
"""
import os
import json, os, struct, subprocess, sys
ROOT = os.environ.get("SCORER_ROOT", os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scorer")))
def f32(x): return struct.unpack("<f",struct.pack("<f",x))[0]
def rail(s,T,top,low):
    s=f32(s)
    if s>=f32(T): return f32(1.0) if top<=0 else f32(1.0-f32(f32(top)*f32(1.0-s)))
    return f32(f32(low)*s)
jobs=json.load(open(sys.argv[1]))
print(f"{'rail':20} {'base':26} {'T':>5} {'top':>7} {'checked':>8} {'bad':>4} verdict")
ok=[]
for j in jobs:
    out=os.path.join(ROOT,"dist/lock",j["name"]+".wasm")
    if not os.path.exists(out): print(f"{j['name']:20} MISSING"); continue
    bs=json.load(open("/tmp/sc-"+os.path.basename(j["base"])+".json"))["scores"]
    rs="/tmp/vr-"+j["name"]+".json"
    r=subprocess.run(["/tmp/dump",out,"/tmp/tri.json",rs],cwd=ROOT,capture_output=True,text=True)
    if r.returncode!=0:
        print(f"{j['name']:20} {os.path.basename(j['base']):26} FAILED TO LOAD: {r.stdout.strip()[:60]}"); continue
    got=json.load(open(rs))["scores"]
    bad=[k for k in bs if got[k]!=rail(bs[k],j["t"],j["top"],j.get("low",1e-9))]
    print(f"{j['name']:20} {os.path.basename(j['base']):26} {j['t']:5} {j['top']:7g} {len(bs):8} {len(bad):4} "
          f"{'ok' if not bad else 'MAP MISMATCH '+str(bad[:2])}")
    if not bad: ok.append(f"{j['intent']}=dist/lock/{j['name']}.wasm")
open("/tmp/verified.txt","w").write(" ".join(ok)+"\n")
print(f"\n{len(ok)}/{len(jobs)} verified in wazero -> /tmp/verified.txt")
