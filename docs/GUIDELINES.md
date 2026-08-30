# Guidelines: the non-negotiable rules

These govern every registration and every commit in this lane. They exist because each has
been paid for at least once.

## Repository visibility

- **The host repo `telegraph-salience-scorer` must stay public** while any live registration
  points at it. The node fetches a registered module from its commit-pinned
  `raw.githubusercontent.com/.../<sha>/dist/*.wasm` URL anonymously. Privating it 404s that
  fetch and silently stalls every new registration "pending" forever. This looks exactly like
  a node outage and has burned real time.
- **This repository is going public too.** It was private while the method was the edge. The
  edge is now the method plus the licence, and a submission a judge cannot read is worth less
  than one a rival can also read. So the split is by role rather than by secrecy: the host repo
  carries the registered binaries the node fetches, and this one carries the source, the
  drivers, the research and the worklogs behind them.
- **Run `preflight_public.py` before flipping it and before any push once it is public.**
  It gates on licence files, key material in the tree and in history, the gateway's model ids,
  third-party parameter blobs, stale slot counts and em dashes. Every one of those has been
  wrong here at least once.
- **A public flip publishes history, not just the tip.** `git log --all` reaches every blob
  ever committed, including two weight blobs since removed from the tree. That is accepted and
  recorded in `NOTICE` rather than papered over: the removed blobs are third-party parameter
  data whose source model is public and MIT, so nothing secret is exposed by their presence in
  history. Never commit anything here on the assumption that deleting it later will unpublish
  it. It will not.
- **Nothing outward names the gateway or its exact model ids.** Not here, not in the host repo,
  not in a form, a post or a video. In the corpora the models are `model-a` through `model-f`,
  which is all the method needs. Outward, our scorer is "a salience scorer with a from-scratch
  MiniLM blend," which is accurate and enough.

## Licensing a build (every new registration, no exceptions)

The host repo carries `LICENSE`, `NOTICE` and `PROVENANCE.json`, but a node fetches a bare
`.wasm` from a raw URL and nobody downloading that file sees any of them. So the terms go
in the binary.

- **Every new build carries the notice in its bytes.** `tools/stamp.py` writes a custom
  wasm section named `license` holding the licence id, the three URLs and one paragraph
  saying what is and is not permitted. `build_xfmr.py` calls it on every build, and
  `deploy.register` refuses a binary without it, so no driver can skip it. The section is
  inert: a runtime ignores custom sections, the exports are unchanged and `rank_answer`
  returns the same `f32`, checked under wazero against the unstamped build.
- **Never re-stamp an already-registered binary.** Changing one byte changes the keccak,
  which breaks the live registration the node is holding. The 36 slots held before
  2026-08-30 keep their bytes and the MIT terms they were published under.
  `TELEGRAPH_ALLOW_UNSTAMPED=1` exists for exactly that case and for nothing else.
- **A build on someone else's work names them.** If a build forks an upstream module or
  wraps its binary, add it to the host repo's `NOTICE` and its licence text to `LICENSES/`
  in the same push that registers it, not afterwards. `tools/provenance.py` regenerates
  `PROVENANCE.json` from the bytes, so the claim is checkable rather than trusted.
- **No licence upstream means no build.** An upstream with no licence file grants no
  permission to redistribute a modified copy. 44 such binaries were published here and had
  to be withdrawn on 2026-08-30. Check the upstream's licence before building on it, not
  after registering it.

## Honesty and real work

- **Report only what the node confirms.** A slot is ours when the active author on the intent
  is our wallet, verified by reading `/intents/<id>` back. Do not claim a win from a poller
  line alone; confirm on-chain, and quote the real `EvalDetails` (margin, wins, Spearman).
- **The builds are genuine scorers.** This is a permissionless on-chain contest, not a bounty
  PR, so there is no maintainer to disclose to and no AI-disclosure line to attach. But the
  same honesty applies: a scorer wins because it actually separates or ranks better, verified
  against the node's own gates, never by a gate exploit we would be embarrassed to explain.
- **Forking is fair, but respect the ask.** An open-source champion under a permissive license
  is fair to fork-and-sharpen (mirror-and-sharpen, see METHOD 5c); it is a strictly better
  scorer, not a copy. When the operator asks for our own build instead ("no fork"), build our
  own: download the champion only to analyse it head-to-head, then win with our module.

## One identity

- One wallet: `0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287`. Its key lives only in the local
  `.wallet.env` that `deploy.py` reads. Never commit it, never print it, never paste it.

## Operating discipline

- **The node is the oracle.** Local agreement proxies over-read (0.69 local vs 0.23 on-node has
  happened). Use local sweeps and the harness to RANK variants and to catch ordering losses
  before spending a registration, never to predict the agreement gate. Every real decision comes
  off an on-node `EvalDetails`.
- **Batch registrations.** `reg_batch` puts N builds on one commit and one push, then registers
  each. Register a spread when a knob's node effect is uncertain and let the node promote the
  best; do not push one file per commit.
- **Do not panic-rebuild during an outage.** The devnode goes 500 or times out for stretches and
  recovers on its own; a margin-passing eval takes ~17 minutes and the indexer lags after. Poll
  and wait. Rebuild only on a real rejection reason.
- **Reproducible builds.** Pass a full config (or a named `variants.py` preset) so a build is
  the whole module, not whatever the last edit left in `lib.rs`. Record each registration and
  its outcome in `worklogs/LEDGER.md`.
- **Verify the fork reproduces before trusting it.** For mirror-and-sharpen, confirm the rebuilt
  binary's scores are bit-identical to the champion's published binary and that the sharpen
  preserves argsort. That bit-identity is the whole guarantee.

## When a slot is lost again

Slots change hands; the contest is live. On a loss, read the current champion's `EvalDetails`
and WasmURL first, classify it with the METHOD decision tree, and reclaim with the matching
technique. Then rebake the monitor and update the ledger. Never assume the old approach still
applies; the champion may have moved.
