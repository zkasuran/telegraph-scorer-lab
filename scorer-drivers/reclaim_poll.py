#!/usr/bin/env python3
"""Poll the 4 reclaim intents until the node evaluates our challengers or a deadline.

Identifies our challenger as the highest-regid registration from our wallet on each
intent (our new challenger outranks the rival champion's regid). Reports WON when the
active author is us, else the challenger's EvalDetails (margin/wins/reason) once evaluated.

  python3 reclaim_poll.py [max_seconds]
Exit 0 when all 4 are held by us, else 1.
"""
import json, subprocess, sys, time
from Crypto.Hash import keccak

NODE = "https://devnode.telegraphprotocol.com/engine/validator/v1"
OURL = "0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287".lower()
INTENTS = {
    "CURRENCY_EXCHANGE":    ("0x609f49e86154424ed6b9e5d40596b20c22e612970f0631baa1f7ce4a2f1e5e8d", 0.7740, 15),
    "FRAUD_DETECTION":      ("0x284ba2cd3b1602cbd5c46c7199870db50e9d85c65f1e78665db4748e68434933", 0.7975, 15),
    "SPORTS_SCORE":         ("0x05fb6f7451a88350c8136f729ebdc175c5edfc3fd3486d7d7b9903a6a3065b07", 0.9098, 15),
    "WALLET_BALANCE_CHECK": ("0x3d6e4e28b4966cb8c9134b983331af9008ab83ed8b67c0e21bdcd49459aea094", 0.7378, 10),
}

def get(u):
    for _ in range(3):
        r = subprocess.run(["curl", "-s", "--max-time", "20", u], capture_output=True, text=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(1)
    return None

def kec(s):
    h = keccak.new(digest_bits=256); h.update(s.encode()); return h.hexdigest()

def evd(w):
    try: return json.loads(w["EvalDetails"]) if w.get("EvalDetails") else {}
    except Exception: return {}

def check():
    held = 0
    lines = []
    for name, (khash, champ, champwins) in INTENTS.items():
        d = get(f"{NODE}/intents/{kec(name)}")
        ws = (d or {}).get("wasm", [])
        active = [s for s in ws if str(s.get("status", "")).lower() == "active"]
        act_us = active and str(active[0].get("address", "")).lower() == OURL
        # our newest registration on this intent
        ours = [s for s in ws if str(s.get("address", "")).lower() == OURL]
        newest = max(ours, key=lambda s: s.get("registration_id", 0)) if ours else None
        if act_us:
            held += 1
            lines.append(f"  HELD  {name}: active is US (regid {active[0].get('registration_id')})")
            continue
        champ_regid = active[0].get("registration_id") if active else "?"
        if newest and (isinstance(champ_regid, int) and newest["registration_id"] > champ_regid or not isinstance(champ_regid, int)):
            w = (get(f"{NODE}/wasm/{newest['registration_id']}") or {}).get("wasm", {})
            e = evd(w)
            m, wn, cs = e.get("candidate_margin"), e.get("candidate_wins"), e.get("comparable_cases")
            rr = w.get("RejectionReason") or e.get("rejection_reason") or ""
            st = str(newest.get("status", "?"))
            if m is not None:
                lines.append(f"  LOST  {name}: reg {newest['registration_id']} status={st} margin={m} (champ {champ}) wins={wn}/{champwins} cases={cs} {str(rr)[:60]}")
            else:
                lines.append(f"  WAIT  {name}: reg {newest['registration_id']} status={st}, not evaluated yet (champ {champ})")
        else:
            lines.append(f"  WAIT  {name}: our challenger not indexed yet (champ {champ}, active regid {champ_regid})")
    return held, lines

def main():
    budget = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    start = time.time()
    while True:
        held, lines = check()
        print(f"[{time.strftime('%H:%M:%S')}] {held}/4 reclaimed (of 4 lost; total {41+held}/45)")
        print("\n".join(lines))
        if held == 4:
            print("ALL 4 RECLAIMED"); sys.exit(0)
        if time.time() - start >= budget:
            sys.exit(1)
        time.sleep(90)

if __name__ == "__main__":
    main()
