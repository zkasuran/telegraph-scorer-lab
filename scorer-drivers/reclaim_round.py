#!/usr/bin/env python3
"""Build reclaim challengers for the currently-lost scorer slots, then print the
reg_batch command. One round at a time. Edit ROUND, run, then reg_batch --send.

  python3 reclaim_round.py            # builds the wasm for this round
"""
import os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import variants as V

# intent -> (variant_name, step_t). Traffic-gated all four, so a moderate step keeps the
# ranking for the agreement gate while the lexical gate (rawG35p) buys fixture separation.
ROUND = {
    "CURRENCY_EXCHANGE":    ("rawG35p", 0.62),
    "FRAUD_DETECTION":      ("rawG35p", 0.62),
    "SPORTS_SCORE":         ("rawG35p", 0.72),
    "WALLET_BALANCE_CHECK": ("rawG35p", 0.62),
}

def main():
    pairs = []
    for intent, (name, step) in ROUND.items():
        label = f"{intent.lower()}_{name}_s{str(step).replace('.', '')}"
        ok = V.build(name, intent, label, {"STEP_T": step})
        p = os.path.join(ROOT, "dist", "xfmr", label + ".wasm")
        if ok and os.path.exists(p):
            pairs.append(f"{intent}={p}")
        else:
            print(f"  BUILD FAILED for {intent}")
    print("\nreg_batch command:")
    print("python3 reg_batch.py " + " ".join(pairs) + " --send")

if __name__ == "__main__":
    main()
