# Runbook: the day-to-day loop

The loop is always the same: see what the champion is, build something that beats it, verify
locally, host and register, read the node back, iterate. The node is the oracle; every
registration is a measurement.

## Prerequisites

- Rust 1.97 with the `wasm32-unknown-unknown` target (module builds).
- clang 18 at `~/.local/clang18/usr/bin` with `rust-lld` symlinked as `wasm-ld` on PATH
  (the C scorer). `export PATH="$HOME/.local/bin:$HOME/.local/clang18/usr/bin:$PATH"`.
- The wallet: `TELEGRAPH_ADDRESS` and its key in the local `.wallet.env` that `deploy.py`
  reads. Never commit it.
- A checkout of the PUBLIC host repo `telegraph-salience-scorer` on disk. The drivers commit
  built binaries to its `dist/` and register the raw URL. Run the drivers from there (they
  build from `./module`, which is this lab's module synced into that checkout).
- `node` for the head-to-head harness scripts.

## Step 1 — read the live champion

```bash
# intent id = keccak256(NAME); champion is the active entry
python3 -c "from Crypto.Hash import keccak;h=keccak.new(digest_bits=256);h.update(b'SPORTS_SCORE');print(h.hexdigest())"
curl -s "$NODE/intents/<id>"          # find the active regid + author
curl -s "$NODE/wasm/<regid>"          # WasmURL, WasmHash, EvalDetails
```

Note the champion's margin, wins, Spearman, `historical_rows_evaluated` and its WasmURL. The
URL tells you if it is forkable (open-source github) or closed (IPFS, R2, dropbox). The row
count tells you if agreement binds.

## Step 2 — build a challenger

Module variant:
```bash
python3 scorer-drivers/build_xfmr.py <INTENT> '<json-config>' <label> [--lexical]
```
Numeric C scorer:
```bash
export PATH="/tmp/cscorer/bin:$HOME/.local/bin:$HOME/.local/clang18/usr/bin:$PATH"
clang --target=wasm32 -nostdlib -O2 -fno-builtin -Wl,--no-entry -Wl,--export-dynamic \
  -Wl,--initial-memory=2097152 -DTGTAG="<tag>" -DSTRETCH=<s> -DTXTW=<t> -DNUMPOW=<n> \
  -o dist/xfmr/<label>.wasm c-scorer/num_scorer.c
```

Pick the technique from `docs/METHOD.md` section 5. Build a SPREAD when a knob's node effect
is uncertain; the node promotes the best of them from one push.

## Step 3 — verify locally before spending a registration

For a closed champion, run the head-to-head: download its binary, score it against your
candidate on a fixture battery, and confirm your candidate wins every case the champion wins.
This is what turned WALLET from a guess into a lock.
```bash
curl -sSL -o /tmp/champ.wasm "<champion WasmURL>"
node head2head.js      # loads champ + candidate, flags cases champ wins but candidate loses
```
For an open-source champion, confirm the fork's rebuild reproduces the published binary's
ranking (bit-identical scores) and that the sharpen preserves argsort while raising the margin.
The harness in `harness/` runs the node's gates over `bench/` fixtures for a first-cut read.
Local agreement over-reads, so use it to rank, not to predict the gate.

## Step 4 — host and register

```bash
python3 scorer-drivers/reg_batch.py \
  <INTENT>=dist/xfmr/<a>.wasm <INTENT>=dist/xfmr/<b>.wasm --send
```
`reg_batch` commits all files on one commit, pushes to the public repo, verifies each raw URL
serves the exact bytes and keccak, then registers. A dry run (omit `--send`) prints hashes and
sizes only.

## Step 5 — poll and read back

```bash
python3 scorer-drivers/sw_poll.py     # edit the target-intent map first
```
Watch each challenger's `EvalDetails`. Three outcomes:
- promoted (active author becomes us) — done, move on.
- rejected on ordering — you lost a case; go back to step 3 head-to-head and find it.
- rejected on separation — raise the margin (more step or contrast) but keep the ranking.
- rejected on agreement (rare, only when rows bind) — your ranking diverged; soften whatever
  penalty or contrast reordered real traffic, or move toward the champion's blend.

## Step 6 — refresh the monitor

```bash
python3 scorer-drivers/tools/bake_monitor.py   # rebakes SCORER-MONITOR.html, prints X/45 held
```

## Node erraticness

The devnode returns 500 or times out for stretches, then recovers on its own. A margin-passing
evaluation takes roughly 17 minutes and the indexer can lag another 30 to 45. Symptoms of an
outage look identical to a stalled evaluator. Do not rebuild in a panic: launch a watcher that
polls an intent endpoint and only acts when it returns a real body, and let the poll drivers
wait. If NEW registrations sit "pending" forever while the node is up, check the public repo is
still public (a private repo 404s the anonymous fetch and is the usual self-inflicted cause).

## Troubleshooting

| symptom | cause | fix |
|---|---|---|
| new regs stuck "pending" while node is up | public host repo went private | `gh api -X PATCH repos/zkasuran/telegraph-salience-scorer -F private=false` |
| `reg_batch` skips a file "did not serve exact bytes" | raw URL not propagated yet or hash mismatch | it retries; if persistent, re-push and re-run |
| rejected on separation by a hair | contrast too gentle, or stretch crushing sub-pivot goods | raise STEP/contrast, or LOWER stretch and raise TXTW |
| rejected on ordering repeatedly | a hard fixture your scorer misranks | head-to-head to find it, add the matching correctness penalty |
| Spearman drops below 0.60 | a penalty or steep contrast reordered real traffic | soften the penalty, lower K, or add/raise STEP_B |
| `alloc` failure at ptr 65536 | C scorer arena too small | it uses a static arena that wraps; confirm ARENA_BYTES is ample |
