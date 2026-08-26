# Architecture: what every file does

## module/ — the Rust scoring module

A `no_std` wasm32 crate. Two build modes from one source: lexical (default, ~1 MB) and the
MiniLM transformer blend (`--features minilm`, ~24 MB). One export the node calls,
`rank_answer(q_ptr,q_len, gt_ptr,gt_len, ma_ptr,ma_len) -> f32`, plus `alloc`/`dealloc`.

- `module/src/lib.rs` — the whole scorer. A tunable block of `const`s at the top is what the
  drivers patch per build (see `docs/KNOBS.md`). Below it: tokenisation with numeric-value
  parsing (commas stripped, `228.50` and `1,000` kept as figures, scale suffixes applied),
  salience-weighted lexical scoring (F-beta of content-word overlap, character trigrams,
  ground-truth recall), the correctness penalties (contradiction, negation coverage, entity
  and order binding, numeric miss and numeric wrong), the optional MiniLM blend
  (`embA`/`embB`/mid-layer cosines plus a lexical gate), and the final calibration path
  (smoothstep `POST_ITERS`, logistic `SIGK`, or step-plus-tie-break `STEP_*`). The
  `TELEGRAPH_INTENT` 32-byte marker makes each intent's binary distinct so its hash differs.
- `module/src/minilm.rs` — from-scratch int8 MiniLM-L6-v2 forward pass (6 layers, 384 dims,
  post-LayerNorm, GELU), plus the packed weight table reader. `TOK_SPAN`/`MAXTOK` live here.
- `module/Cargo.toml` — `crate-type = cdylib`, release profile tuned for size, the `minilm`
  feature flag.

## c-scorer/ — the bespoke numeric scorer

- `c-scorer/num_scorer.c` — a freestanding C scorer for figure intents (prices, balances,
  scores). No libc, no imports, a static arena so `alloc` never fails at the 64 KB page
  boundary. Parses numbers to values and compares by relative error in a tight band; text
  overlap only breaks ties. Compile-time knobs `STRETCH` (contrast), `TXTW` (text weight),
  `NUMPOW` (numeric power), `TGTAG` (a string baked in for hash uniqueness). Builds to ~5 KB.

  Build (clang 18, with rust-lld symlinked as wasm-ld on PATH):
  ```
  clang --target=wasm32 -nostdlib -O2 -fno-builtin -Wl,--no-entry -Wl,--export-dynamic \
    -Wl,--initial-memory=2097152 -DTGTAG="tag" -DSTRETCH=6.0 -DTXTW=0.12 -DNUMPOW=1 \
    -o out.wasm num_scorer.c
  ```

## scorer-drivers/ — build, gate, register, poll

- `build_xfmr.py` — patches the `const`s in `lib.rs` from a JSON config, sets the intent
  marker, builds lexical or `--features minilm`, copies to `dist/xfmr/<label>.wasm`, prints
  keccak and size. This is the single build entry point for module variants.
- `variants.py` — named full configs (rawB, rawR, rawG35p, PEN sets, blends). A config here is
  the whole module so two runs of a name give the same binary. Use it for reproducible variants
  and for the `build()` helper the reclaim scripts call.
- `deploy.py` — keccak of a wasm, and the on-chain `registerWasm` call (loads the wallet key,
  sends the tx). The low-level register primitive the batch drivers wrap.
- `reg_batch.py` — the workhorse. Hosts N built wasms on ONE commit and ONE push to the public
  repo, verifies each raw URL serves the exact bytes and hash before it registers, then sends
  one registration per file. `INTENT=path` args, repeatable intent, `--send` to fire.
- `reg_xfmr.py` — the older one-file-per-commit register path; kept for single large builds.
- `reclaim.py`, `reclaim_round.py` — build a round of challengers for the currently-lost slots
  and print the `reg_batch` command. Edit the round map, run, then register.
- `reclaim_poll.py`, `chat_poll.py`, `sw_poll.py` — poll the node until named intents flip to
  us, printing each challenger's `EvalDetails` (margin, wins, Spearman, rejection) as it
  evaluates. `sw_poll.py` is the general two-intent template; copy and edit the target map.
- `tune.py` — parameter sweep driver over local benchmarks.
- `scorer-drivers/tools/` — analysis and monitoring:
  - `bake_monitor.py` — pull live per-intent champion state for all 45 and bake the offline
    `SCORER-MONITOR.html` snapshot. Prints held count and the not-held list.
  - `gen_intent_traffic.py` — synthesise per-intent traffic proxies (VERBOSE=1 for long LLM
    answers) for local agreement ranking.
  - `blend.py`, `cluster.py`, `features.py`, `sweep.py`, `pick.py`, `ref_minilm.py` — variant
    ranking, fixture clustering, feature dumps, a numpy MiniLM reference for port fidelity.

## harness/ — local verification

Go + wazero. Loads a wasm module and runs the node's own promotion logic (ordering, margin,
agreement) over `bench/` fixtures, so a variant can be scored the way the node scores it
before you spend a registration. `harness/cmd/dump` dumps per-fixture scores.

## bench/ — fixtures and benchmarks

Hidden-style fixtures, the attack suite (`attacks.json`: negation, entity swap, numeric wrong,
two-faced), family benchmarks (numeric, reference, authenticity), and traffic proxies per
intent (plain and verbose). `registrations.json` and `report.json` track measured runs.

## research/ — per-intent exploration

Agreement and Spearman sweeps, score dumps and variant diffs for the intents that needed the
most work (agent_task, language_generation, task_completion, web_search).

## worklogs/

`LEDGER.md` (the running record of registrations and outcomes), `HANDOFF.md` (session
handoff), `SUBMIT-PACKET.md` (the defensible walkthrough).
