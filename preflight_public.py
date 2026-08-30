#!/usr/bin/env python3
"""Pre-flight gate for flipping telegraph-scorer-lab public.

Run this, get a clean report, then flip. Every check is a thing that has to be true
before the repo is readable by anyone, and each one failed at least once during the
licence pass.

    python3 preflight_public.py            # check only
    python3 preflight_public.py --flip     # check, then flip if clean

The checks:
  licence      LICENSE, NOTICE and LICENSES/ exist and NOTICE names every component
  secrets      no key material, no .env, no wallet private key in the tree or in history
  model ids    the gateway's exact model ids appear nowhere
  weights      no third-party parameter blob is tracked
  staleness    no hardcoded "45/45 held" claim that a live board contradicts
  style        no em dashes in our own prose
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = "zkasuran/telegraph-scorer-lab"

# The exact ids the house gateway serves. Never outward, per the workspace rules.
MODEL_IDS = ["gpt-4o-mini", "gemini-2.5-flash", "deepseek-v4-flash", "qwen3.6-27b",
             "kimi-k2.5", "glm-5.1"]
SECRET_PAT = re.compile(
    r"BEGIN [A-Z ]*PRIVATE KEY|TELEGRAPH_PRIVATE_KEY\s*=\s*0x|passphrase\s*[:=]\s*\S")
SENSITIVE_NAME = re.compile(r"(^|/)\.(env|wallet)|\.pem$|passphrase|id_rsa|\.p12$")
# Third-party parameter data: ours to use, not ours to publish as our own.
FOREIGN_BLOBS = {"module/src/vectors-champ.bin", "module/src/gte-small.bin",
                 "module/src/gte-mix.bin", "module/src/gte-int4.bin"}
PROSE = re.compile(r"\.(md|txt)$|^(LICENSE|NOTICE)$")


def git(*a, cwd=ROOT):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True).stdout


def tracked():
    return [f for f in git("ls-files").split("\n") if f]


def check_licence(files):
    bad = []
    for need in ("LICENSE", "NOTICE"):
        if need not in files:
            bad.append(f"{need} is not tracked")
    if not any(f.startswith("LICENSES/") for f in files):
        bad.append("LICENSES/ carries no licence text")
    if "NOTICE" in files:
        notice = open(os.path.join(ROOT, "NOTICE")).read()
        for component in ("all-MiniLM", "gte-small", "GloVe", "wazero", "walrus"):
            if component not in notice:
                bad.append(f"NOTICE does not name {component}")
    return bad


def check_secrets(files):
    bad = [f"sensitive filename tracked: {f}" for f in files if SENSITIVE_NAME.search(f)]
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 4_000_000:
            continue
        try:
            body = open(p, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        m = SECRET_PAT.search(body)
        if m:
            bad.append(f"possible secret in {f}: {m.group(0)[:40]}")
    # history matters as much as the tip: a public repo publishes every reachable blob
    for line in git("log", "--all", "--name-only", "--pretty=format:").split("\n"):
        if line and SENSITIVE_NAME.search(line):
            bad.append(f"sensitive filename in git history: {line}")
    return sorted(set(bad))


def check_model_ids(files):
    bad = []
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 4_000_000:
            continue
        body = open(p, encoding="utf-8", errors="ignore").read()
        hits = [m for m in MODEL_IDS if m in body]
        if hits:
            bad.append(f"{f} names {', '.join(hits)}")
    return bad


def check_weights(files):
    return [f"third-party parameter blob tracked: {f}" for f in files if f in FOREIGN_BLOBS]


def check_staleness(files):
    bad = []
    for f in files:
        if not PROSE.search(os.path.basename(f)) and not f.endswith(".md"):
            continue
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        body = open(p, encoding="utf-8", errors="ignore").read()
        # a headline count of held slots in a badge or a status table goes stale in hours
        for m in re.finditer(r"(45\s*/\s*45|45%2F45)[^\n]{0,40}(held|intents)", body):
            if f.startswith("worklogs/"):
                continue          # the ledger is dated history, that is its job
            bad.append(f"{f} claims a live slot count: {m.group(0)[:50]}")
    return bad


def check_style(files):
    bad = []
    for f in files:
        if not f.endswith((".md", ".txt")) and os.path.basename(f) not in ("LICENSE", "NOTICE"):
            continue
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        n = open(p, encoding="utf-8", errors="ignore").read().count("—")
        if n:
            bad.append(f"{f} has {n} em dash{'es' if n > 1 else ''}")
    return bad


def main():
    files = tracked()
    checks = [
        ("licence", check_licence),
        ("secrets", check_secrets),
        ("model ids", check_model_ids),
        ("weights", check_weights),
        ("staleness", check_staleness),
        ("style", check_style),
    ]
    failed = 0
    print(f"{len(files)} tracked files\n")
    for name, fn in checks:
        problems = fn(files)
        if problems:
            failed += 1
            print(f"FAIL  {name}")
            for p in problems[:12]:
                print(f"        {p}")
            if len(problems) > 12:
                print(f"        ... and {len(problems) - 12} more")
        else:
            print(f"ok    {name}")
    print()
    if failed:
        print(f"{failed} check{'s' if failed > 1 else ''} failed. Do not flip yet.")
        return 1
    print("clean. safe to flip:")
    print(f"  gh api -X PATCH repos/{REPO} -F private=false")
    print(f"  curl -s -o /dev/null -w '%{{http_code}}\\n' https://github.com/{REPO}")
    if "--flip" in sys.argv:
        print("\nflipping...")
        r = subprocess.run(["gh", "api", "-X", "PATCH", f"repos/{REPO}", "-F", "private=false"],
                           capture_output=True, text=True)
        if r.returncode:
            print("flip failed:", r.stderr[-300:])
            return 1
        vis = json.loads(r.stdout).get("visibility")
        print(f"visibility now {vis}")
        code = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               f"https://github.com/{REPO}"], capture_output=True,
                              text=True).stdout
        print(f"anonymous fetch of the repo page: {code}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
