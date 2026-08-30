#!/usr/bin/env python3
"""Score a miner answer the way the node scores it, against the intent's live module.

The node grades a miner by pulling `signal_mapping.label_field` out of the miner's JSON
response and scoring that text with the intent's currently active scoring module, against
a ground truth the node writes itself. The ground truth is not published, so this harness
reconstructs the grading from two things we can read:

  * the active module, resolved from /engine/validator/v1 and downloaded byte for byte
  * a ground-truth proxy: on most intents the leading miner scores ~1.0, which means its
    answer IS the node's ground truth to within the module's tolerance

Given those, `rank <INTENT>` scores any number of candidate answers and prints them in
order, so an answer-shape change is measured before it is deployed rather than after an
epoch has passed.

    python3 rank.py sync                     refresh the board, the modules and the proxies
    python3 rank.py board                    live rank per intent, ours against the leader
    python3 rank.py rank <INTENT> [file]     score candidates (JSON list of strings)
    python3 rank.py check <INTENT>           score our live answer as it stands right now
    python3 rank.py why <INTENT>             the probe log: what the node built, what failed

Modules are 1 to 29 MB and take seconds to instantiate, so scoring is batched: one load
per intent, every candidate scored inside it.
"""
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
NODE = "https://devnode.telegraphprotocol.com"
US = "0x8b224783fe5b3c52b7db0cb9b1754f8812b75287"
CACHE = os.path.join(ROOT, ".rank")
MODULES = os.path.join(CACHE, "modules")
DUMP = os.path.join(ROOT, "..", "scorer", "harness", "dumpscores")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")


def keccak(s):
    from Crypto.Hash import keccak as k
    h = k.new(digest_bits=256)
    h.update(s.encode())
    return h.hexdigest()


def curl(url, timeout=60):
    r = subprocess.run(["curl", "-sL", "--max-time", str(timeout), "-A", UA, url],
                       capture_output=True, text=True)
    return r.stdout


def jget(url, tries=3, timeout=60):
    for _ in range(tries):
        body = curl(url, timeout)
        if len(body) > 20:
            try:
                return json.loads(body)
            except Exception:
                pass
    return {}


def our_slugs():
    d = jget(NODE + "/api/miners")
    ms = d if isinstance(d, list) else d.get("miners", [])
    return {m["slug"] for m in ms if (m.get("wallet_address") or "").lower() == US}, ms


def sync():
    os.makedirs(MODULES, exist_ok=True)
    ours, ms = our_slugs()
    intents = sorted({i for m in ms if m["slug"] in ours
                      for i in (m.get("supported_intents") or [])})
    print(f"{len(ours)} miners of ours over {len(intents)} intents")

    def module_of(intent):
        d = jget(f"{NODE}/engine/validator/v1/intents/{keccak(intent)}")
        act = [w for w in (d.get("wasm") or []) if str(w.get("status", "")).lower() == "active"]
        if not act:
            return {"intent": intent, "module": None}
        rid = act[0]["registration_id"]
        w = (jget(f"{NODE}/engine/validator/v1/wasm/{rid}") or {}).get("wasm") or {}
        return {"intent": intent, "reg": rid, "url": w.get("WasmURL"),
                "hash": w.get("WasmHash"),
                "author": "US" if (w.get("AuthorAddress") or "").lower() == US else
                          (w.get("AuthorAddress") or "")[:10]}

    with ThreadPoolExecutor(max_workers=12) as ex:
        mods = list(ex.map(module_of, intents))

    def fetch(rec):
        if not rec.get("url"):
            return rec["intent"], "no active module"
        path = os.path.join(MODULES, rec["intent"] + ".wasm")
        if os.path.exists(path):
            got = hashlib.sha256(open(path, "rb").read()).hexdigest()
            if got == (rec.get("hash") or ""):
                return rec["intent"], f"cached {os.path.getsize(path) >> 20} MB"
        subprocess.run(["curl", "-sL", "--max-time", "300", rec["url"], "-o", path], check=False)
        got = hashlib.sha256(open(path, "rb").read()).hexdigest() if os.path.exists(path) else ""
        ok = "hash ok" if got == (rec.get("hash") or "") else f"HASH MISMATCH {got[:12]}"
        return rec["intent"], f"{os.path.getsize(path) >> 20} MB {ok}"

    with ThreadPoolExecutor(max_workers=6) as ex:
        for intent, note in ex.map(fetch, mods):
            print(f"  {intent:24} {note}")
    json.dump(mods, open(os.path.join(CACHE, "modules.json"), "w"), indent=1)

    scores = {}
    for intent in intents:
        d = jget(f"{NODE}/scores?intent={intent}&limit=500")
        scores[intent] = d.get("scores") or []
    json.dump(scores, open(os.path.join(CACHE, "scores.json"), "w"))
    print(f"probe log: {sum(len(v) for v in scores.values())} rows")


def board():
    ours, ms = our_slugs()
    by = {}
    for m in ms:
        for s in (m.get("scores") or []):
            by.setdefault(s["intent_id"], []).append((m["slug"], s))
    mine = sorted({i for m in ms if m["slug"] in ours for i in (m.get("supported_intents") or [])})
    won = 0
    print(f"{'intent':24} {'rank':>5} {'ours':>12} {'leader':>12}  leader slug")
    for intent in mine:
        rows = sorted(by.get(intent, []), key=lambda t: (t[1].get("rank") or 999))
        us = [(sl, s) for sl, s in rows if sl in ours]
        if not rows or not us:
            print(f"{intent:24} {'-':>5} {'unscored':>12}")
            continue
        sl, s = us[0]
        top = rows[0]
        if top[0] in ours:
            won += 1
        print(f"{intent:24} {s.get('rank'):>5} {s.get('score'):12.6g} "
              f"{top[1].get('score'):12.6g}  {top[0]}")
    print(f"\nrank 1 on {won} of {len(mine)}")


def proxy(intent):
    p = os.path.join(ROOT, "gt", intent + ".json")
    if not os.path.exists(p):
        sys.exit(f"no ground-truth proxy for {intent}: write {p} first "
                 '({"question": "...", "ground_truth": "...", "source": "..."})')
    return json.load(open(p))


def score(intent, cands):
    """Score {label: answer} under the intent's live module. Returns {label: score}."""
    gt = proxy(intent)
    mod = os.path.join(MODULES, intent + ".wasm")
    if not os.path.exists(mod):
        sys.exit(f"no module cached for {intent}: run `rank.py sync`")
    trips = [{"id": k, "q": gt["question"], "gt": gt["ground_truth"], "a": v}
             for k, v in cands.items()]
    tin = os.path.join(CACHE, "in.json")
    tout = os.path.join(CACHE, "out.json")
    json.dump(trips, open(tin, "w"))
    r = subprocess.run([DUMP, mod, tin, tout], capture_output=True, text=True)
    if not os.path.exists(tout):
        sys.exit(f"dump failed: {r.stdout}{r.stderr}")
    return json.load(open(tout))["scores"]


def call_ours(intent):
    """Call our live miner for this intent and return the text the node would grade."""
    live = json.load(open(os.path.join(ROOT, "live.json")))
    if intent not in live:
        sys.exit(f"no live call recorded for {intent} in live.json")
    url, params, field = live[intent]["url"], live[intent]["params"], live[intent].get("field", "summary")
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    body = jget(url + ("?" + q if q else ""), tries=2, timeout=45)
    return body.get(field), url + ("?" + q if q else "")


def main():
    os.makedirs(CACHE, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "board"
    if cmd == "sync":
        return sync()
    if cmd == "board":
        return board()
    if cmd == "check":
        intent = sys.argv[2]
        text, url = call_ours(intent)
        gt = proxy(intent)
        s = score(intent, {"ours_live": text, "gt_self": gt["ground_truth"]})
        print(f"{intent}\n  {url}\n  ours: {text}\n  gt:   {gt['ground_truth']}")
        print(f"  score {s['ours_live']:.6f}   (ground truth against itself {s['gt_self']:.6f})")
        return
    if cmd == "rank":
        intent = sys.argv[2]
        cands = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else json.load(sys.stdin)
        if isinstance(cands, list):
            cands = {f"c{i}": c for i, c in enumerate(cands)}
        gt = proxy(intent)
        cands = dict(cands, gt_self=gt["ground_truth"])
        s = score(intent, cands)
        for k, v in sorted(s.items(), key=lambda kv: -kv[1]):
            print(f"  {v:.6f}  {k:18} {cands[k][:96]}")
        return
    if cmd == "why":
        intent = sys.argv[2]
        rows = json.load(open(os.path.join(CACHE, "scores.json")))[intent]
        ours, _ = our_slugs()
        for r in sorted(rows, key=lambda r: -r["epoch_id"]):
            if r["miner_slug"] not in ours:
                continue
            print(f"  ep{r['epoch_id']} rank {r['rank']:>2} score {r['score']:.6g}"
                  + (f"\n      FAIL {r['failure_reason'][:200]}" if r["failure_reason"] else ""))
        return
    sys.exit(__doc__)


if __name__ == "__main__":
    main()
