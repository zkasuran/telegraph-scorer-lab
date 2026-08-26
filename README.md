# telegraph-scorer-lab (private)

The method home for our Telegraph Protocol Track 2 scorers. Everything that wins and
holds scorer slots lives here: the scoring module source, the bespoke numeric scorer,
the build and registration drivers, the verification harness, the research sweeps, and
the worklogs.

Status as of 2026-08-26: **45 / 45 canonical intents held** by our wallet
`0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287`.

## What this is

Telegraph runs a permissionless, on-chain contest for each of its 45 canonical intents
(CHAT_COMPLETION, SPORTS_SCORE, WALLET_BALANCE_CHECK, and so on). Anyone can register a
WebAssembly module that scores a miner's answer against a question and a ground truth.
The validator node promotes the module that scores best on that intent's hidden fixtures
and real traffic. Hold the slot and you own how that intent is scored network-wide.

We compete by building better scoring modules and reading the node's own evaluation back
to learn the exact gate, then iterating until we hold every slot. This repo is the
canonical record of how.

## The public repo is a host only

`zkasuran/telegraph-salience-scorer` is public and must stay public: the node fetches a
registered module from its commit-pinned `raw.githubusercontent.com/.../<sha>/dist/*.wasm`
URL anonymously, so making it private silently breaks every live registration. That repo
carries only `dist/` binaries, the harness, `LICENSE` and a neutral README. All method
work happens here. See `docs/GUIDELINES.md`.

## Layout

```
module/src/        Rust no_std scoring module: lexical + numeric + optional MiniLM blend
c-scorer/          bespoke freestanding C numeric scorer (num_scorer.c), ~5 KB wasm
scorer-drivers/    build, gate, register, poll automation (Python) + tools/
harness/           Go + wazero harness that runs the node's promotion gates locally
bench/             fixtures, attack suite, family + traffic benchmarks
research/          agreement/Spearman sweeps, score dumps, per-intent notes
worklogs/          LEDGER, HANDOFF, SUBMIT-PACKET
docs/              this documentation set
```

## Documentation

Read them in this order:

1. `docs/METHOD.md` — how the promotion gates work and the full winning playbook. Start here.
2. `docs/ARCHITECTURE.md` — what every file and directory does.
3. `docs/RUNBOOK.md` — build, host, register, poll, iterate. The day-to-day loop.
4. `docs/KNOBS.md` — every tunable constant in the scoring module and what it changes.
5. `docs/GUIDELINES.md` — the non-negotiable rules (repo visibility, honesty, cost, secrecy).

## Quickstart

```bash
# build one lexical variant for an intent and print its keccak + size
python3 scorer-drivers/build_xfmr.py WALLET_BALANCE_CHECK \
  '{"W_EMB":0.0,"STEP_T":0.40,"STEP_B":0.02,"M_CONTRA":0.7,"M_NEGCOV":0.32}' wl_demo --lexical

# host + register a batch on the public repo, one commit, one push, N registrations
python3 scorer-drivers/reg_batch.py WALLET_BALANCE_CHECK=dist/xfmr/wl_demo.wasm --send

# watch the node evaluate our challengers until we hold the slot
python3 scorer-drivers/sw_poll.py
```

The drivers assume a checkout of the public host repo on disk (its `origin` is
`telegraph-salience-scorer`); they build from `./module`, commit the built binary to that
repo's `dist/`, push, then register the raw URL. See `docs/RUNBOOK.md`.
