#!/usr/bin/env python3
"""Build a rail spread on our own bases and verify each one locally before it costs a registration.

The rail is f(s) = 1 - top*(1-s) above T, low*s below. Two things are checked here that the
node will check for real:
  wins      no fixture pair may lose its ordering, so no pair may land on the same f32 level
  ordering  the traffic ranking is the base's, so distinct base scores must stay distinct
Both are read off a dump of the base, which is why one dump per base is enough for the whole
sweep: every rail is a function of the base score alone.
"""
import os
import json, os, struct, subprocess, sys

ROOT = os.environ.get("SCORER_ROOT", os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "scorer")))
DUMP = "/tmp/dump"
TRI  = "/tmp/tri.json"

def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]

def rail(s, T, top, low):
    s = f32(s)
    if s >= f32(T):
        return f32(1.0) if top <= 0 else f32(1.0 - f32(f32(top) * f32(1.0 - s)))
    return f32(f32(low) * s)

def dump(base):
    out = "/tmp/sc-" + os.path.basename(base) + ".json"
    if not os.path.exists(out):
        subprocess.run([DUMP, base, TRI, out], cwd=ROOT, capture_output=True)
    return json.load(open(out))["scores"]

def check(scores, T, top, low):
    ids = sorted(scores)
    mapped = {k: rail(scores[k], T, top, low) for k in ids}
    lost = 0
    for k in ids:
        if not k.endswith("|good"): continue
        b = k[:-5] + "bad"
        if b not in mapped: continue
        if scores[k] > scores[b] and mapped[k] <= mapped[b]:
            lost += 1
    pairs = sorted((scores[k], mapped[k]) for k in ids)
    collapsed = sum(1 for i in range(len(pairs) - 1)
                    if pairs[i][0] != pairs[i + 1][0] and pairs[i][1] == pairs[i + 1][1])
    g = [mapped[k] for k in ids if k.endswith("|good")]
    b = [mapped[k] for k in ids if k.endswith("|bad")]
    return lost, collapsed, f32(sum(g) / len(g) - sum(b) / len(b))

def build(intent, base, T, top, low, name):
    out = os.path.join(ROOT, "dist/lock", name + ".wasm")
    cmd = [sys.executable, "rev/rail.py", "--base", base, "--out", out,
           "--t", repr(T), "--low", repr(low)]
    if top > 0: cmd += ["--top", repr(top)]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  {name}: rail.py failed: {r.stdout}{r.stderr}"); return None
    s = subprocess.run([sys.executable, "rev/stamp.py", out, "--intent", intent],
                       cwd=ROOT, capture_output=True, text=True)
    if s.returncode != 0:
        print(f"  {name}: stamp failed: {s.stdout}{s.stderr}"); return None
    return out

JOBS = json.load(open(sys.argv[1]))
print(f"{'name':20} {'intent':24} {'T':>5} {'top':>7} {'lost':>4} {'tied':>5} {'bench margin':>13}")
plan = []
for j in JOBS:
    sc = dump(j["base"])
    lost, coll, m = check(sc, j["t"], j["top"], j.get("low", 1e-9))
    p = build(j["intent"], j["base"], j["t"], j["top"], j.get("low", 1e-9), j["name"])
    ok = "" if lost == 0 else "  <-- LOSES FIXTURE ORDERING"
    print(f"{j['name']:20} {j['intent']:24} {j['t']:5} {j['top']:7g} {lost:4} {coll:5} {m:13.9f}{ok}")
    if p and lost == 0: plan.append(f"{j['intent']}={os.path.relpath(p, ROOT)}")
open("/tmp/regplan.txt", "w").write(" ".join(plan) + "\n")
print(f"\n{len(plan)} of {len(JOBS)} builds clean, plan written to /tmp/regplan.txt")
