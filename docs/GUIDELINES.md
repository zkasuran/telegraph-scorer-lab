# Guidelines: the non-negotiable rules

These govern every registration and every commit in this lane. They exist because each has
been paid for at least once.

## Repository visibility

- **The public host repo `telegraph-salience-scorer` must stay public** while any live
  registration points at it. The node fetches a registered module from its commit-pinned
  `raw.githubusercontent.com/.../<sha>/dist/*.wasm` URL anonymously. Privating it 404s that
  fetch and silently stalls every new registration "pending" forever. This looks exactly like
  a node outage and has burned real time. If you must reclaim while it is up, it stays public.
- **Do method work in this lab, not the public repo.** The public tip carries only `dist/`,
  the harness, `LICENSE` and a neutral README. Everything else (module source, drivers,
  research, worklogs, these docs) lives here.
- **Accepted residual:** the public repo's commit HISTORY still contains method from before the
  split, recoverable with `git checkout <old-sha>`, and champion bytes are public by necessity
  (the node fetches them). The split hides the method from casual browsing and keeps NEW work
  private; it does not seal history. Fully sealing would mean migrating every held slot to a
  fresh host, which risks losing slots and was declined.
- **Never name this lab, or any private infrastructure, in outward text.** Not in the public
  repo, commit messages there, PRs, forms, posts or video. Outward, our scorer is "a salience
  scorer with a from-scratch MiniLM blend," which is accurate and enough.

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
