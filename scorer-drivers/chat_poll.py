#!/usr/bin/env python3
"""Poll CHAT_COMPLETION until our forked+sharpened scorer becomes active champion."""
import json, subprocess, sys, time
NODE="https://devnode.telegraphprotocol.com/engine/validator/v1"
CHAT="ccd42820467c59d6f703fb6d0fe57d6303fbfaa893759ee493c29293adfdc1f7"
OURL="0x8b224783fe5b3c52b7db0cb9b1754f8812b75287"
CHAMP=0.42408657

def get(u):
    for _ in range(3):
        r=subprocess.run(["curl","-s","--max-time","25",u],capture_output=True,text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2)
    return None

def evd(w):
    try: return json.loads(w["EvalDetails"]) if w.get("EvalDetails") else {}
    except Exception: return {}

budget=int(sys.argv[1]) if len(sys.argv)>1 else 3000
start=time.time()
while True:
    d=get(f"{NODE}/intents/{CHAT}") or {}
    ws=d.get("wasm",[])
    act=[w for w in ws if str(w.get("status","")).lower()=="active"]
    ts=time.strftime("%H:%M:%S")
    if act and str(act[0].get("address","")).lower()==OURL:
        print(f"[{ts}] *** WON CHAT_COMPLETION *** active regid {act[0]['registration_id']} is US")
        sys.exit(0)
    champ=act[0]['registration_id'] if act else '?'
    ours=sorted([w for w in ws if str(w.get('address','')).lower()==OURL and w['registration_id']>1040],key=lambda w:w['registration_id'])
    lines=[]
    for w in ours:
        rid=w['registration_id']; st=w.get('status')
        e=evd((get(f"{NODE}/wasm/{rid}") or {}).get("wasm",{}))
        m,wn,cs,sp=e.get('candidate_margin'),e.get('candidate_wins'),e.get('comparable_cases'),e.get('spearman')
        rr=(get(f"{NODE}/wasm/{rid}") or {}).get("wasm",{}).get("RejectionReason")
        if m is not None:
            lines.append(f"    reg{rid} st={st} margin={m:.4f}(champ {CHAMP:.4f}) wins={wn}/{cs} sp={sp} rej={rr}")
        else:
            lines.append(f"    reg{rid} st={st} not-evaluated-yet")
    print(f"[{ts}] champ regid {champ} (ssoni) still active; our challengers:")
    print("\n".join(lines) if lines else "    (none indexed yet)")
    if time.time()-start>=budget:
        print("budget elapsed"); sys.exit(1)
    time.sleep(100)
