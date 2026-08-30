#!/usr/bin/env python3
"""Is a promoted rail sitting exactly on its own ROC ceiling, and therefore un-wrappable?

The old doctrine said only an exact-1.0 margin is safe. CONTENT_MODERATION (reg2055) shows that
is too strong. Its rail was promoted at margin exactly f32(12/15) = 0.8 with 15/15 wins, and no
monotone wrap of it can report more than 12/15, because:

  * a wrap g of our rail output cannot exceed  max_t [#(good>=t) - #(bad>=t)] / N  (the ROC
    ceiling of the rail, which a non-decreasing rail inherits from its base), and
  * our rail already reports that value, because the top rail is flat to within half an f32 ulp:
    the correction is (top/N)*Sum(1-g) over the top-rail goods, and where our goods sit near 1.0
    that lands under 3e-8 at 0.8, so it rounds away entirely.

So the test for "safe" is not margin == 1.0. It is  margin == f32(j/N)  where j is the number of
fixture goods the threshold lifts. Any wrap then ties, and a tie loses.

usage: ceilcheck.py <reg-id> [reg-id ...]
"""
import json, subprocess, sys, struct
NODE = "https://devnode.telegraphprotocol.com"
US = "0x8b224783fe5b3c52b7db0cb9b1754f8812b75287"
EPS = 1e-6

def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]

def get(u):
    r = subprocess.run(["curl", "-s", "--max-time", "40", u], capture_output=True, text=True)
    try: return json.loads(r.stdout)
    except Exception: return None

print(f"{'reg':>6} {'intent':24} {'who':6} {'margin':>13} {'wins':>7} {'j/N':>13} "
      f"{'on ceiling':>11} {'headroom':>10} verdict")
for rid in sys.argv[1:]:
    w = (get(f"{NODE}/engine/validator/v1/wasm/{rid}") or {}).get("wasm") or {}
    if not w: print(f"{rid:>6} not found"); continue
    e = w.get("EvalDetails")
    if isinstance(e, str):
        try: e = json.loads(e)
        except Exception: e = {}
    e = e or {}
    m = e.get("candidate_margin"); N = e.get("comparable_cases")
    cw = e.get("candidate_wins")
    who = "OURS" if (w.get("AuthorAddress") or "").lower() == US else "RIVAL"
    it = w.get("IntentID"); st = w.get("ActivationStatus") or "pending"
    if m is None or not N:
        print(f"{rid:>6} {it:24} {who:6} {'-':>13} {'-':>7} {'-':>13} {'-':>11} {'-':>10} {st}")
        continue
    # j is the number of fixture pairs the rail's threshold cleanly splits. m sits at or just
    # below f32(j/N), so round to nearest and only step up when m is genuinely above that rail.
    # Stepping up on a value already equal to f32(j/N) invents a whole extra pair of headroom,
    # which is what made a rail sitting exactly on its ceiling look 7e-2 short.
    j = round(m * N)
    if f32(m) > f32(j / N): j += 1
    ceil = f32(j / N)
    on = (f32(m) == ceil)
    head = ceil - m
    verdict = ("WRAP-PROOF, any wrap ties" if on else
               f"wrappable, a rival can still take {head:.2e}" if head >= EPS else
               "effectively safe, headroom under the promotion epsilon")
    print(f"{rid:>6} {it:24} {who:6} {m:13.9f} {str(cw)+'/'+str(N):>7} {ceil:13.9f} "
          f"{str(on):>11} {head:10.2e} {verdict}")
