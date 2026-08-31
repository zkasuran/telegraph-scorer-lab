#!/usr/bin/env python3
"""Score candidate answers against several ground-truth phrasings at once.

`rank.py rank` scores against one ground-truth proxy, which is a coin flip: the node
writes its truth fresh each epoch, so an answer tuned to one phrasing is tuned to one
epoch. This scores every candidate against every truth in the intent's bank and reports
the worst case as well as the mean, because the shape with the better worst case is the
one that holds rank across epochs.

    python3 sweep.py <INTENT> cands.json      candidates as a JSON list or {label: text}
    python3 sweep.py <INTENT> --live          just our live answer, against the whole bank

The bank is `gtbank/<INTENT>.json`:

    {"question": "...", "truths": [{"label": "leader", "text": "...", "source": "..."}]}

Each truth says where it came from, so a measurement can be told from a guess. A bank
with one truth is a bank that has not been written yet.

HOLD THE VALUE FIXED ON A FIGURE INTENT. The modules gate hard on the rendered digits, so
a truth carrying yesterday's price scores every candidate 0 on the value and measures
nothing about the wording. A bank for a figure intent therefore stores its truths as
templates over named figures, plus a `values` block saying where each figure is read from
the live miner payload:

    {"question": "...",
     "values": {"price": {"field": "price", "url": "...", "params": {...}}},
     "truths": [{"label": "leader", "text": "1 USD = {price:.4f} EUR", "source": "..."}]}

`{price:.4f}` and `{price:,.2f}` are plain Python format specs, so one live reading can be
rendered at every grain a truth might use. Candidates are the live answer or written ones,
and both are scored against the same value, so only the wording varies.
"""
import json
import os
import string
import sys

import rank

ROOT = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(ROOT, "gtbank")


def live_values(spec):
    """Read each named figure from a live miner payload, so truths and candidates agree.

    A spec entry is one of:
      {"url":..., "params":..., "field": "a.b"}   read live from a miner payload
      {"const": 123}                              a fixed value
      {"from": "other", "divide": 1e9}            derived, so "$18.19 billion" and
                                                  "$18,186,347,469" are the same reading
      {"from": "other", "round": -2}              the same reading at a coarser grain, so a
                                                  truth that rounds to the nearest hundred is
                                                  still the same value rather than a wrong one
      {"from":"c","multiply":1.8,"add":32}         a unit conversion, so a truth in Fahrenheit
                                                  states the same reading as one in Celsius
    """
    out = {}
    derived = {}
    for name, how in (spec or {}).items():
        if "from" in how:
            derived[name] = how
            continue
        if "const" in how:
            out[name] = how["const"]
            continue
        url = how["url"]
        q = "&".join(f"{k}={v}" for k, v in (how.get("params") or {}).items())
        body = rank.jget(url + ("?" + q if q else ""), tries=2, timeout=45)
        cur = body
        for key in str(how["field"]).split("."):
            if isinstance(cur, list) and key.isdigit():
                cur = cur[int(key)] if int(key) < len(cur) else None
            else:
                cur = (cur or {}).get(key)
        if cur is None:
            sys.exit(f"value '{name}' read null from {url} field {how['field']}")
        out[name] = cur
    for name, how in derived.items():
        base = out.get(how["from"])
        if base is None:
            sys.exit(f"derived value '{name}' has no base '{how['from']}'")
        v = float(base)
        if how.get("round") is not None:
            v = round(v, int(how["round"]))
        if how.get("divide"):
            v /= float(how["divide"])
        if how.get("multiply"):
            v *= float(how["multiply"])
        if how.get("add"):
            v += float(how["add"])
        out[name] = v
    return out


def bank(intent):
    p = os.path.join(BANK, intent + ".json")
    if not os.path.exists(p):
        sys.exit(f"no ground-truth bank for {intent}: write {p} first")
    b = json.load(open(p))
    if len(b["truths"]) < 2:
        print(f"  ! {intent} bank has {len(b['truths'])} truth(s): a single phrasing "
              f"measures one epoch, not the intent", file=sys.stderr)
    if b.get("values"):
        vals = live_values(b["values"])
        b["resolved_values"] = vals
        fmt = string.Formatter()
        for t in b["truths"]:
            t["text"] = fmt.vformat(t["text"], (), vals)
        b["question"] = fmt.vformat(b["question"], (), vals)
    return b


def score_against(intent, truth_text, question, cands, module=None):
    mod = os.path.join(rank.MODULES, (module or intent) + ".wasm")
    if not os.path.exists(mod):
        sys.exit(f"no module cached for {module or intent}: run `rank.py sync`")
    trips = [{"id": k, "q": question, "gt": truth_text, "a": v} for k, v in cands.items()]
    tin = os.path.join(rank.CACHE, "sweep-in.json")
    tout = os.path.join(rank.CACHE, "sweep-out.json")
    json.dump(trips, open(tin, "w"))
    if os.path.exists(tout):
        os.remove(tout)
    import subprocess
    r = subprocess.run([rank.DUMP, mod, tin, tout], capture_output=True, text=True)
    if not os.path.exists(tout):
        sys.exit(f"dump failed: {r.stdout}{r.stderr}")
    return json.load(open(tout))["scores"]


def sweep(intent, cands, question=None):
    b = bank(intent)
    q = question or b["question"]
    # A bank whose name starts with an underscore is a scratch bank: it studies one intent's
    # module under a hypothesis (a stale figure, a differently framed truth) rather than
    # standing for the intent itself, so it names the module it wants to be scored under.
    module = b.get("module") or (intent.lstrip("_").split("__")[0] if intent.startswith("_") else None)
    cols = []
    table = {k: {} for k in cands}
    for t in b["truths"]:
        cols.append(t["label"])
        s = score_against(intent, t["text"], q, cands, module)
        for k in cands:
            table[k][t["label"]] = s[k]
    return cols, table


def report(intent, cands, question=None):
    cols, table = sweep(intent, cands, question)
    w = max(len(k) for k in cands) + 1
    rows = []
    for k, row in table.items():
        vals = [row[c] for c in cols]
        rows.append((min(vals), sum(vals) / len(vals), k, vals))
    # On a figure-gated intent every candidate can sit at the contradiction floor (1e-13 and
    # below), and that is exactly the regime the live board is in: the node writes its truth at a
    # moment we do not control, so no miner's digits match and rank is decided inside the floor.
    # Fixed-point would print a column of zeros and hide the ordering, so switch to significant
    # digits when nothing clears a thousandth.
    tiny = max((max(v) for _, _, _, v in rows), default=0) < 1e-3
    cell = (lambda v: f"{v:12.4g}") if tiny else (lambda v: f"{v:12.6f}")
    head = f"{'cand':<{w}}" + "".join(f"{c[:11]:>12}" for c in cols) + f"{'worst':>12}{'mean':>12}"
    print(head)
    for worst, mean, k, vals in sorted(rows, key=lambda r: (-r[0], -r[1])):
        print(f"{k:<{w}}" + "".join(cell(v) for v in vals) + cell(worst) + cell(mean))
    return rows


def main():
    intent = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else "--live"
    if arg == "--live":
        text, url = rank.call_ours(intent)
        if not text:
            sys.exit(f"{intent}: live miner returned no label field ({url})")
        cands = {"live": text}
        print(f"{url}\n  {text}\n")
    else:
        cands = json.load(open(arg))
        if isinstance(cands, list):
            cands = {f"c{i}": c for i, c in enumerate(cands)}
    report(intent, cands)


if __name__ == "__main__":
    main()
