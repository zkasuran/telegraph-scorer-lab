#!/usr/bin/env python3
"""Watch the registrations from this round until the node has ruled on each one."""
import json, subprocess, sys, time, os
NODE="https://devnode.telegraphprotocol.com"
WALLET="0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287"
SINCE=int(sys.argv[1]) if len(sys.argv)>1 else 2020
def ed(w):
    e=w.get('EvalDetails')
    if isinstance(e,str):
        try: e=json.loads(e)
        except Exception: e={}
    return e or {}
while True:
    r=subprocess.run(["curl","-s","--max-time","90",f"{NODE}/engine/validator/v1/addresses/{WALLET}"],capture_output=True,text=True)
    try: ws=[w for w in json.loads(r.stdout).get('wasm',[]) if isinstance(w,dict)]
    except Exception:
        time.sleep(60); continue
    new=[w for w in ws if (w.get('RegistrationID') or 0)>SINCE]
    new.sort(key=lambda w:w.get('RegistrationID'))
    lines=[time.strftime("%H:%M:%S")+f"  {len(new)} regs since {SINCE}"]
    for w in new:
        e=ed(w); sp=e.get('spearman')
        if isinstance(sp,dict): sp=next(iter(sp.values()),None)
        st=w.get('ActivationStatus') or 'pending'
        f=(w.get('WasmURL') or '').rsplit('/',1)[-1]
        rr=(w.get('RejectionReason') or '').split(':')[0][:44]
        lines.append(f"  reg{w.get('RegistrationID')} {w.get('IntentID'):24} {st:11} m={e.get('candidate_margin')} champ={e.get('champion_margin')} sp={sp} rows={e.get('historical_rows_evaluated')} {f}  {rr}")
    open('/tmp/pollreg.txt','w').write("\n".join(lines)+"\n")
    done = {'active','superseded','rejected','withdrawn'}
    if len(new) >= 14 and all(str(w.get('ActivationStatus') or '').lower() in done for w in new): break
    time.sleep(75)
