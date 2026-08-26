#!/usr/bin/env python3
"""Poll SPORTS_SCORE + WALLET_BALANCE_CHECK until both are held by us. Reports each
of our pending challengers' EvalDetails (margin/wins/spearman/rejection) as they evaluate."""
import json, subprocess, sys, time
from Crypto.Hash import keccak
NODE="https://devnode.telegraphprotocol.com/engine/validator/v1"
OURL="0x8b224783fe5b3c52b7db0cb9b1754f8812b75287"
TARGETS={"SPORTS_SCORE":0.9298, "WALLET_BALANCE_CHECK":0.7378}
def kec(s): h=keccak.new(digest_bits=256); h.update(s.encode()); return h.hexdigest()
def get(u):
    for _ in range(3):
        r=subprocess.run(["curl","-s","--max-time","25",u],capture_output=True,text=True)
        try:
            j=json.loads(r.stdout)
            if j is not None: return j
        except Exception: time.sleep(2)
    return None
def evd(w):
    try: return json.loads(w["EvalDetails"]) if w.get("EvalDetails") else {}
    except Exception: return {}
budget=int(sys.argv[1]) if len(sys.argv)>1 else 3300
start=time.time()
while True:
    ts=time.strftime("%H:%M:%S"); held=0; out=[]
    for name,champ in TARGETS.items():
        d=get(f"{NODE}/intents/{kec(name)}") or {}
        ws=d.get("wasm",[])
        act=[w for w in ws if str(w.get("status","")).lower()=="active"]
        act_us = act and str(act[0].get("address","")).lower()==OURL
        if act_us:
            held+=1; out.append(f"  {name}: HELD by US (regid {act[0]['registration_id']})"); continue
        cm=act[0]['registration_id'] if act else '?'
        ours=sorted([w for w in ws if str(w.get('address','')).lower()==OURL],key=lambda w:w['registration_id'])[-4:]
        lines=[]
        for w in ours:
            det=(get(f"{NODE}/wasm/{w['registration_id']}") or {}).get("wasm",{})
            e=evd(det); rej=det.get("RejectionReason")
            if e.get('candidate_margin') is not None:
                lines.append(f"      reg{w['registration_id']} {w.get('status')}: m={e.get('candidate_margin'):.4f}(t>{champ}) wins={e.get('candidate_wins')}/{e.get('comparable_cases')} sp={e.get('spearman')}"+(f" REJ:{str(rej)[:75]}" if rej else ""))
            else:
                lines.append(f"      reg{w['registration_id']} {w.get('status')}: not-evaluated")
        out.append(f"  {name}: champ regid {cm} active; ours:\n"+"\n".join(lines))
    print(f"[{ts}] {held}/2 held")
    print("\n".join(out)); sys.stdout.flush()
    if held==2:
        print("*** BOTH HELD — SPORTS + WALLET RECLAIMED ***"); sys.exit(0)
    if time.time()-start>=budget:
        print("budget elapsed"); sys.exit(1)
    time.sleep(110)
