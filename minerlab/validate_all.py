#!/usr/bin/env python3
"""Sandbox-validate every miner descriptor against its live worker.

The console's /api/validate calls each declared endpoint the way the node will and reports the
status it got, which is the only check that catches a descriptor whose paths no longer match the
deployed worker. Run it after any worker or YAML change and before spending gas on a
re-registration.

    python3 .scratch/validate_all.py [yaml ...]
"""
import glob
import json
import os
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONSOLE = "https://integrate.telegraphprotocol.com"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")


def validate(path):
    body = json.dumps({"yaml": open(path).read(), "api_key": "none"}).encode()
    req = urllib.request.Request(
        CONSOLE + "/api/validate", data=body, method="POST",
        headers={"content-type": "application/json",
                 "cookie": open(os.path.join(ROOT, ".tg-session")).read().strip(),
                 "user-agent": UA, "origin": CONSOLE, "referer": CONSOLE + "/"})
    try:
        with urllib.request.urlopen(req, timeout=240) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
    except Exception as e:
        return {"error": str(e)}
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        # The console answers with an HTML error page when its own sandbox is overloaded, which is
        # not a descriptor problem, so it is reported as retryable rather than as invalid.
        return {"error": f"non-JSON reply, {len(raw)} bytes: {raw[:120]!r}"}


def main():
    files = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "*", "*.yaml")))
    bad = []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        v = validate(path)
        probes = " ".join(f"{r['path']}->{r['status']}{'' if r['success'] else '!'}"
                          for r in v.get("results", []))
        ok = v.get("valid")
        print(f"{'OK ' if ok else 'BAD'} {rel:46} {probes or v.get('error', '')[:60]}", flush=True)
        if not ok:
            bad.append((rel, v))
        time.sleep(1)
    if bad:
        print()
        for rel, v in bad:
            print(f"{rel}: {json.dumps(v.get('errors') or v)[:220]}")
    print(f"\n{len(files) - len(bad)} of {len(files)} valid")


if __name__ == "__main__":
    main()
