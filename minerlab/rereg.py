#!/usr/bin/env python3
"""Re-register every miner descriptor whose YAML changed, one at a time.

The node's endpoint validator matches the path it built as an exact string, so a declared
`{template}` path never matches and the probe is rejected as undeclared. The templates came
out of all 25 descriptors, which means the on-chain YAML has to be replaced. Re-registration
keeps the miner's scores: the slug is unchanged, so the node updates the descriptor rather
than starting a new grace period.

Writes a progress line per lane and skips a lane already done in a previous run.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".scratch", "rereg-state.json")


def intent_of(yaml_path):
    t = open(yaml_path).read()
    m = re.search(r"(?ms)^\s+supported_intents:\n((?:\s+- \S+\n)+)", t)
    return re.findall(r"- (\S+)", m.group(1))[0] if m else None


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    lanes = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "*", "*.yaml")))
    for y in lanes:
        rel = os.path.relpath(y, ROOT)
        if state.get(rel, {}).get("status") == "0x1":
            print(f"{rel:46} done already, tx {state[rel]['tx'][:14]}", flush=True)
            continue
        intent = intent_of(y)
        r = subprocess.run(["python3", os.path.join(ROOT, "register-miner.py"), rel, intent],
                           capture_output=True, text=True, cwd=ROOT, timeout=600)
        out = r.stdout + r.stderr
        tx = re.search(r"tx (0x[0-9a-f]{64})\s+status (0x[0-9a-f]+)", out)
        if tx:
            state[rel] = {"intent": intent, "tx": tx.group(1), "status": tx.group(2)}
            print(f"{rel:46} {intent:22} tx {tx.group(1)[:14]} status {tx.group(2)}", flush=True)
        else:
            state[rel] = {"intent": intent, "status": "failed", "log": out[-400:]}
            print(f"{rel:46} {intent:22} FAILED", flush=True)
            print("   " + out.strip().splitlines()[-1][:180], flush=True)
        json.dump(state, open(STATE, "w"), indent=1)
        time.sleep(2)
    ok = sum(1 for v in state.values() if v.get("status") == "0x1")
    print(f"\n{ok} of {len(state)} registered")


if __name__ == "__main__":
    main()
