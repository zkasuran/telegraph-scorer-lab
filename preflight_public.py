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
  paths        no absolute path from this machine, so a checkout runs anywhere
  style        no em dashes in our own prose
"""
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = "zkasuran/telegraph-scorer-lab"

# The check has to know the ids it is looking for, and this file is public, so they are
# stored as salted digests rather than in the clear. Every token of the right length in a
# tracked file is hashed and compared. Add an id with:
#   python3 -c "import hashlib;print(hashlib.sha256(SALT+b'<id>').hexdigest()[:32])"
MODEL_ID_SALT = b"telegraph-scorer-lab/preflight/v1"
MODEL_ID_HASHES = {
    "fd3d891dfb0450ab6d94faf096dd0c92",
    "c69cb1c8a63c510a270d8a01fa42d15e",
    "b6bf2a3933d2bd4e14ddf76d65dd14de",
    "5cf8e4be38da983e45103c32ce94d83e",
    "abe83cee69f85cbb289fb8e106635dd8",
    "c02710c1de15832e2b6352b65563525b",
}
# a model id looks like this: lowercase, digits, dots and dashes, 6 to 24 characters
TOKEN = re.compile(rb"[a-z][a-z0-9]*(?:[.\-][a-z0-9]+){1,4}")
SECRET_PAT = re.compile(
    r"BEGIN [A-Z ]*PRIVATE KEY|TELEGRAPH_PRIVATE_KEY\s*=\s*0x|passphrase\s*[:=]\s*\S")
SENSITIVE_NAME = re.compile(r"(^|/)\.(env|wallet)|\.pem$|passphrase|id_rsa|\.p12$")
# Third-party parameter data: ours to use, not ours to publish as our own.
FOREIGN_BLOBS = {"module/src/vectors-champ.bin", "module/src/gte-small.bin",
                 "module/src/gte-mix.bin", "module/src/gte-int4.bin"}
PROSE = re.compile(r"\.(md|txt)$|^(LICENSE|NOTICE)$")
# An absolute path from one machine is a leak of the local layout and a bug for anyone
# else running the script. Everything reads an env var or a relative path instead.
LOCAL_PATH = re.compile(r"/home/[a-z0-9_-]+/|/Users/[A-Za-z0-9_-]+/")


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
    """Fail if any tracked file names one of the gateway's exact model ids.

    Compares salted digests, so the ids this gate forbids are not themselves written
    down in a public file. A hit reports the file and the digest, not the id.
    """
    bad = []
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 4_000_000:
            continue
        body = open(p, "rb").read()
        for m in TOKEN.finditer(body):
            tok = m.group(0)
            if not 6 <= len(tok) <= 24:
                continue
            h = hashlib.sha256(MODEL_ID_SALT + tok).hexdigest()[:32]
            if h in MODEL_ID_HASHES:
                bad.append(f"{f} names a gateway model id (digest {h[:12]})")
                break
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


def check_paths(files):
    bad = []
    for f in files:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p) or os.path.getsize(p) > 4_000_000:
            continue
        body = open(p, encoding="utf-8", errors="ignore").read()
        m = LOCAL_PATH.search(body)
        if m:
            bad.append(f"{f} carries a local path: {m.group(0)}")
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
        ("paths", check_paths),
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
