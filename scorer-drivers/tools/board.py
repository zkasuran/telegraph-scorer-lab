#!/usr/bin/env python3
"""Read the live 45-slot board: who holds each canonical intent, with EvalDetails."""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
from Crypto.Hash import keccak

NODE = "https://devnode.telegraphprotocol.com"
US = "0x8b224783fe5b3c52b7db0cb9b1754f8812b75287"

def kec(s):
    h = keccak.new(digest_bits=256); h.update(s.encode()); return h.hexdigest()

def get(url, t=40):
    r = subprocess.run(["curl","-s","--max-time",str(t),url], capture_output=True, text=True)
    try: return json.loads(r.stdout)
    except Exception: return None

def ed(w):
    e = w.get("EvalDetails")
    if isinstance(e,str):
        try: e=json.loads(e)
        except Exception: e={}
    return e or {}

INTENTS = json.load(open(".scratch/intent-names.json")) if os.path.exists(".scratch/intent-names.json") else None
if INTENTS is None:
    INTENTS = [x["intent"] for x in json.load(open(".scratch/board.json"))]

def one(it):
    d = get(f"{NODE}/engine/validator/v1/intents/{kec(it)}") or {}
    ws = d.get("wasm") or []
    act = [w for w in ws if str(w.get("status","")).lower()=="active"]
    row = {"intent": it, "n_regs": len(ws)}
    if not act:
        row["holder"]="NONE"; return row
    rid = act[0].get("registration_id")
    w = (get(f"{NODE}/engine/validator/v1/wasm/{rid}") or {}).get("wasm") or {}
    e = ed(w)
    auth = (w.get("AuthorAddress") or "").lower()
    sp = e.get("spearman")
    if isinstance(sp,dict): sp = next(iter(sp.values()),None)
    row.update(holder = "US" if auth==US else auth[:10],
               reg=rid, m=e.get("candidate_margin"), champ=e.get("champion_margin"),
               wins=e.get("candidate_wins"), cases=e.get("comparable_cases"),
               rows=e.get("historical_rows_evaluated"), sp=sp,
               url=w.get("WasmURL"), hash=w.get("WasmHash"),
               keys=sorted(e.keys()))
    return row

with ThreadPoolExecutor(max_workers=12) as ex:
    rows = list(ex.map(one, INTENTS))
rows.sort(key=lambda r: r["intent"])
# The devnode goes 500 / empty for stretches and recovers on its own. An outage reads back as
# every intent having no active scorer, which would overwrite a good snapshot with nothing, so
# refuse to save that and keep the last known board instead.
live = sum(1 for r in rows if r["holder"] != "NONE")
if live < len(rows) // 2:
    print(f"node outage: only {live}/{len(rows)} intents report an active scorer, keeping the "
          f"previous snapshot")
else:
    json.dump(rows, open(".scratch/board.json","w"), indent=1)
us=[r for r in rows if r["holder"]=="US"]
print(f"total {len(rows)}  US {len(us)}  rival {len(rows)-len(us)}")
for r in rows:
    if r["holder"]!="US":
        print(f"{r['intent']:26} {r['holder']:12} reg{r.get('reg')} m={r.get('m')} wins={r.get('wins')}/{r.get('cases')} rows={r.get('rows')} sp={r.get('sp')}")
print("\nEvalDetails keys sample:", rows[0].get("keys"))
