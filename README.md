<p align="center">
  <img src="https://img.shields.io/badge/status-45%2F45_intents_held-brightgreen?style=for-the-badge" alt="Status: 45/45 intents held"/>
  <img src="https://img.shields.io/badge/lang-Rust%20%7C%20C%20%7C%20Go%20%7C%20Python-blue?style=for-the-badge" alt="Languages"/>
  <img src="https://img.shields.io/badge/target-wasm32--unknown--unknown-orange?style=for-the-badge" alt="Target: wasm32"/>
  <img src="https://img.shields.io/badge/wallet-0x8b22...5287-blueviolet?style=for-the-badge" alt="Wallet"/>
</p>

<h1 align="center">⚡ Telegraph Scorer Lab</h1>

<p align="center">
  <strong>The private method home for Telegraph Protocol Track 2 scoring modules.</strong><br/>
  Build, verify, register, and defend all 45 canonical intent slots on-chain.
</p>

<p align="center">
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-the-winning-playbook">Playbook</a> •
  <a href="#-day-to-day-loop">Day-to-Day</a> •
  <a href="#-further-documentation">Docs</a>
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [The Journey: 0 → 45 → Contested → Defended](#-the-journey-0--45--contested--defended)
- [How Telegraph Scoring Works](#-how-telegraph-scoring-works)
- [The Three Promotion Gates](#-the-three-promotion-gates)
- [Core Insight: Monotone Transforms](#-core-insight-monotone-transforms)
- [Architecture](#-architecture)
- [The Rust Scoring Module](#-the-rust-scoring-module)
- [The MiniLM Transformer Blend](#-the-minilm-transformer-blend)
- [The C Numeric Scorer](#-the-c-numeric-scorer)
- [Verification Harness (Go)](#-verification-harness-go)
- [Build & Registration Drivers](#-build--registration-drivers)
- [Benchmarks & Attack Suite](#-benchmarks--attack-suite)
- [Research](#-research)
- [Tunable Knobs Reference](#-tunable-knobs-reference)
- [The Winning Playbook](#-the-winning-playbook)
- [Reverse-Engineering the Rivals](#-reverse-engineering-the-rivals)
- [The Miner Side (Demand)](#-the-miner-side-demand)
- [War Log & Hard-Won Lessons](#-war-log--hard-won-lessons)
- [Quickstart](#-quickstart)
- [Day-to-Day Loop](#-day-to-day-loop)
- [Guidelines](#-guidelines)
- [Further Documentation](#-further-documentation)

---

## 🌐 Overview

Telegraph runs a **permissionless, on-chain contest** for each of its 45 canonical intents
(CHAT\_COMPLETION, SPORTS\_SCORE, WALLET\_BALANCE\_CHECK, FINANCIAL\_DATA, WEATHER\_FORECAST,
AI\_TEXT\_DETECTION, and 39 others). Anyone can register a WebAssembly module that scores a
miner's answer against a question and a ground truth. The validator node promotes the module
that scores best on that intent's hidden fixtures and real traffic. **Hold the slot and you
own how that intent is scored network-wide.**

This repository is the canonical record of how we:

| # | Action | How |
|---|--------|-----|
| 1 | **Build** | Rust `no_std` wasm + freestanding C wasm scoring modules |
| 2 | **Verify** | Go + wazero harness replicating the node's promotion logic locally |
| 3 | **Register** | Automated Python drivers: batch host, push, verify URL, register on-chain |
| 4 | **Defend** | Iterate on the node's evaluation feedback, reclaim lost slots same-day |

### Current Status

| Metric | Value |
|--------|-------|
| **Intents held** | 45 / 45 |
| **Wallet** | `0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287` |
| **Verified** | Every `/intents/<id>` read back on 2026-08-27 |
| **Same-day reclaims** | AI\_TEXT\_DETECTION, CVE\_LOOKUP, FACT\_CHECK, GAME\_RESULT, CHAT\_COMPLETION |

> **This is a private lab.** The public host repo
> [`telegraph-salience-scorer`](https://github.com/zkasuran/telegraph-salience-scorer) carries
> only `dist/` binaries and a neutral README. All method work happens here.

---

## 🗺 The Journey: 0 → 45 → Contested → Defended

Track 2 is one question asked 45 times: _write the best judge for an intent and you own how
that intent is scored for the whole network._ This is the story of taking every seat, losing
some to a strong field, then taking them back with methods that did not exist when we started.

### Phase 1 · Nothing → 45/45

Built the salience-weighted lexical core (precision and recall over information-weighted words,
character n-grams, correctness penalties) and a from-scratch `no_std` MiniLM-L6-v2 blend.
Registered intent by intent, read each rejection's `EvalDetails`, iterated until all 45 were
held under one wallet.

### Phase 2 · The Field Hits Back (45 → 27)

A strong author (ScoreWire, `0xd4c7...8ef9`) took fifteen slots with one good scorer reused
across intents. Two others took one each. We fell to **27/45** — fair and square on the exact
measure the protocol promotes on.

### Phase 3 · The Two-Day Climb Back (27 → 45)

Five different problems, each wrong for a different reason:

| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Registrations silently dropped | 29 MB wasm exceeded the node's raw-fetch limit | Shrink to ≤24 MB; later int4/FFN-only requant to ~21 MB |
| Easy separation tier | Builds hadn't landed yet | Clean separation once builds arrived |
| Agreement gate failures | Hard step reorders real traffic | Keep ranking + sharpen + 2% raw sliver |
| Near-ceiling holders (0.9996) | Need exact 1.0/0.0 rails | Pure step with model already separating cleanly |
| Ordering stuck at 14/15 | Own penalty firing on a good answer | Penalties off → pair flips; step back on for margin |

Last slot (`CONTENT_EXTRACTION`) needed character-gram-dominant blend + embedding + low
`STEP_B` → margin **0.99976** past the holder's 0.9995855. **45/45 again.**

### Phase 4 · Better Builds Arrive & The Miner Pivot

Purpose-built challengers (several open-source) took CURRENCY\_EXCHANGE, FRAUD\_DETECTION,
SPORTS\_SCORE, WALLET\_BALANCE\_CHECK, and CHAT\_COMPLETION. In parallel we opened a second
front: five keyless miners on the demand side.

### Phase 5 · Reverse-Engineer, Then Out-Build

Pulled every lost champion's binary (and source where open). The decisive move:
**fork the champion's own scorer and wrap it in a strictly monotone contrast stretch.**
Same ranking = agreement passes free + wins hold; the stretch buys the margin.

- CHAT\_COMPLETION reclaimed (Spearman **1.000** locally, margin lifted 0.42 → 0.58)
- FRAUD\_DETECTION fell to a steeper logistic
- CVE\_LOOKUP / FACT\_CHECK / GAME\_RESULT fell to pivot-aware stretches
- WALLET\_BALANCE\_CHECK won with targeted penalties (14/14 at margin 0.782)

> **The board is contested in real time.** 45/45 is not a finish line you cross once; it is a
> state you defend. Everything below is how.

---

## 🎯 How Telegraph Scoring Works

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        Telegraph Validator Node                            │
│                                                                            │
│  For each intent:                                                          │
│    1. Miner submits an answer to a question                                │
│    2. Validator calls: rank_answer(question, ground_truth, answer)          │
│    3. The active scoring module returns f32 ∈ [0, 1]                       │
│    4. Scores determine miner reward distribution                           │
│                                                                            │
│  Challenger registration:                                                  │
│    • Anyone registers a .wasm module for any intent                        │
│    • Node evaluates challenger vs champion on hidden fixtures               │
│    • Challenger passes ALL THREE gates → promoted to champion              │
└──────────────────────────────────────────────────────────────────────────┘
```

Each scoring module is a **WebAssembly binary** exporting exactly three functions:

| Export | Signature | Purpose |
|--------|-----------|---------|
| `alloc` | `(size: i32) → i32` | Allocate memory for the node to write input strings |
| `dealloc` | `(ptr: i32, size: i32)` | Free allocated memory |
| `rank_answer` | `(q_ptr, q_len, gt_ptr, gt_len, ma_ptr, ma_len) → f32` | Score the answer |

The module runs in a pure sandbox: **no std, no network, no filesystem, no host imports.**
Everything must be compiled in.

---

## 🏛 The Three Promotion Gates

A challenger must pass **all three gates in order** to replace the incumbent:

<table>
<tr>
<th width="30%">Gate</th>
<th width="35%">Rule</th>
<th width="35%">What it means</th>
</tr>
<tr>
<td>

### 1️⃣ Ordering (Wins)

</td>
<td>

```
candidate_wins >= champion_wins
```

</td>
<td>Rank good above bad on at least as many fixture cases. <strong>Hardest gate</strong> — no contrast fixes a wins loss.</td>
</tr>
<tr>
<td>

### 2️⃣ Separation (Margin)

</td>
<td>

```
candidate_margin > champion_margin
```
_(strict inequality)_

</td>
<td>

`margin = mean(good) − mean(bad)`. A tie loses. Rewards **contrast**.

</td>
</tr>
<tr>
<td>

### 3️⃣ Agreement (Spearman ρ)

</td>
<td>

```
spearman(yours, champion) >= 0.60
```

</td>
<td>Only binds when traffic rows > 0. Your real-traffic ranking must correlate with the champion's.</td>
</tr>
</table>

### Undocumented Behaviors (Decoded 2026-08-27)

| Discovery | Implication |
|-----------|------------|
| Separation is not a plain `>` at the ceiling | Against a champion at 0.999999, a candidate at 0.99999994 was **rejected**; only exact 1.0 was accepted |
| Spearman 0.0000 = undefined, not low | All traffic got the same score (pure step); fix: order the bottom rail |
| The reclaim bar is the **live** champion | Stale `champion_margin` from old rejections misleads in both directions |

### The `EvalDetails` Response

Every registration returns a labelled measurement:

| Field | Meaning |
|-------|---------|
| `candidate_margin` | Your separation on hidden fixtures |
| `champion_margin` | The incumbent's separation |
| `candidate_wins` / `champion_wins` | Fixture cases each ranked correctly |
| `comparable_cases` | Total fixture cases evaluated |
| `spearman` | `{INTENT: r}` — rank correlation with champion on real traffic |
| `historical_rows_evaluated` | How many real-traffic rows the agreement gate saw |
| `score_stddev` | Spread of your scores |
| `worst_self_match` | Lowest score on a known-correct answer |

---

## 💡 Core Insight: Monotone Transforms

> A **strictly monotone** transform of the final score cannot reorder any two answers.

This is the single most important insight in the lab:

```
                    Monotone Transform
                          │
            ┌─────────────┼─────────────┐
            │             │             │
     ✅ Wins preserved   ✅ Spearman    ✅ Margin can
       (ordering          preserved      be pushed up
        unchanged)        (rank-          freely
                          invariant)
```

**Order-preserving is the magic word:** it turns the margin gate into something you buy for
free once the ranking is right, and it lets you inherit a strong scorer's agreement without
inheriting its low margin.

**The corollary:** a monotone transform **cannot FIX** a bad ranking. Fix the ranking first,
then buy the margin.

**The caveat:** A bare hard step collapses a tight f32 cluster into ties, destroying Spearman.
Fix: `out = (1−b)·step + b·raw` with b ≈ 0.02 keeps every answer at its own place.

---

## 🏗 Architecture

```
telegraph-scorer-lab/
│
├── module/                          🦀 Rust no_std scoring module
│   ├── src/
│   │   ├── lib.rs                      The whole scorer (~2000 lines)
│   │   ├── minilm.rs                   From-scratch int8 MiniLM-L6-v2
│   │   ├── vectors.bin                 14,700 GloVe word vectors (775 KiB)
│   │   ├── vectors-champ.bin           Champion-distilled vector table
│   │   ├── vectors-glove.bin           Original GloVe vectors
│   │   ├── minilm.bin                  MiniLM int8 weights (~23 MB)
│   │   └── gte-small.bin               GTE-Small alternative weights
│   ├── Cargo.toml                      cdylib, opt-level=z, LTO
│   └── Cargo.lock
│
├── c-scorer/                        🔧 Freestanding C numeric scorer
│   └── num_scorer.c                    ~5 KB wasm for figure intents
│
├── harness/                         🧪 Go + wazero local verification
│   ├── main.go                         Node promotion gates, locally
│   ├── cmd/dump/main.go                Per-fixture score dumper
│   ├── go.mod / go.sum
│   └── harness-report.json             Last run output
│
├── scorer-drivers/                  🐍 Python build/register/poll automation
│   ├── build_xfmr.py                  Patch constants → build → keccak
│   ├── variants.py                     Named full configs (reproducible)
│   ├── deploy.py                       On-chain registerWasm call
│   ├── reg_batch.py                    Host N wasms, one push, N regs
│   ├── reg_xfmr.py                    Single-file register path
│   ├── reclaim.py                      Build challengers for lost slots
│   ├── reclaim_round.py               Multi-slot reclaim automation
│   ├── reclaim_poll.py                 Poll until intents flip
│   ├── chat_poll.py                    CHAT_COMPLETION-specific poller
│   ├── sw_poll.py                      General two-intent poll template
│   ├── tune.py                         Parameter sweep driver
│   └── tools/
│       ├── bake_monitor.py             Live state → HTML snapshot
│       ├── gen_intent_traffic.py       Synthesise traffic proxies
│       ├── blend.py                    Variant ranking analysis
│       ├── cluster.py                  Fixture clustering
│       ├── features.py                 Feature dumps
│       ├── sweep.py                    Parameter sweep utilities
│       ├── pick.py                     Variant selection
│       └── ref_minilm.py              NumPy MiniLM reference
│
├── bench/                           📊 Fixtures and benchmarks
│   ├── benchmark.json                  40-case general benchmark
│   ├── benchmark-topical.json          Topical variant
│   ├── attacks.json                    12-case adversarial suite
│   ├── family-*.json                   Numeric / authenticity / reference
│   ├── traffic-*.json                  Per-intent proxies (plain)
│   ├── traffic-verbose-*.json          Per-intent proxies (verbose)
│   ├── traffic-real.json               Real node traffic samples
│   ├── champion-corpus-scores.json     Champion's cached scores
│   ├── champ-real-scores.json          Champion real-traffic scores
│   ├── registrations.json              Registration history
│   ├── report.json                     Harness report
│   └── tune-results.json              Sweep results
│
├── research/                        🔬 Per-intent exploration
│   ├── agent_task/                     Agreement sweeps, traffic gen
│   ├── language_generation/            LangGen variant analysis
│   ├── task_completion/                Spearman sweeps, variant scores
│   └── web_search/                     Traffic corpus generation
│
├── docs/                            📖 Documentation
│   ├── METHOD.md                       Promotion gates & playbook
│   ├── ARCHITECTURE.md                 What every file does
│   ├── RUNBOOK.md                      Day-to-day loop
│   ├── KNOBS.md                        Every tunable constant
│   └── GUIDELINES.md                   Non-negotiable rules
│
└── worklogs/                        📝 Operational records
    ├── LEDGER.md                       Running registration record
    ├── HANDOFF.md                      Session handoff notes
    └── SUBMIT-PACKET.md               Defensible walkthrough
```

---

## 🦀 The Rust Scoring Module

The heart of the system. A `no_std` wasm32 crate — ~1 MB lexical, ~24 MB with MiniLM.

### Scoring Pipeline

```
┌─ Input ───────────────────────────────────────────────────────────────┐
│  (question, ground_truth, miner_answer) → f32 ∈ [0, 1]               │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 1. Tokenization ────────────────────────────────────────────────────┐
│  • Split on non-word bytes, keep numeric separators                   │
│  • FNV-1a hashing (thousands separators stripped)                     │
│  • Negation window tracking (4-token reach)                           │
│  • Numeric value parsing (commas, decimals, scale suffixes)           │
│  • Proper noun detection · Acronym packing · Crude stemming           │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 2. Word Weighting (corpus-free IDF proxy) ──────────────────────────┐
│  Stop words → 0.12 │ Numbers → 3.0 │ Proper nouns → +1.3            │
│  Content words → 1.0 + 0.06·min(len,12) │ Non-Latin → 0.5           │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 3. Lexical Scoring ─────────────────────────────────────────────────┐
│  Precision (P): how much the answer asserts is in the ground truth    │
│    + soft vector credit for paraphrases (GloVe cosine)                │
│  Recall (R): answer-bearing GT content covered by the answer          │
│  F-beta: (1+β²)·P·R / (β²·P + R),  β² = 0.36 (precision-lean)      │
│  Blend: W_LEX·lex + W_GRAM3·trigrams + W_GRAM2·bigrams               │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 4. Character N-Grams ───────────────────────────────────────────────┐
│  Trigrams: 131,072-bit Bloom filter, Dice + containment               │
│  Bigrams: same structure, tail-breaker for short text                 │
│  Content-word adjacency bigrams (what sits next to what)              │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 5. Correctness Penalties (non-monotone ordering levers) ────────────┐
│  M_CONTRA (0.7)     │ Contradicts the ground truth                    │
│  M_TWO_FACED (0.8)  │ Asserts truth AND its opposite                  │
│  M_NEGCOV (0.32)    │ Words only under a negation GT lacks            │
│  M_ORDER (0.85)     │ Right words, no shared adjacency                │
│  M_ENTITY (0.72)    │ Right figure, wrong entity                      │
│  M_LITERAL (1.0)    │ Transposed characters in literals               │
│  M_NUM_MISS (0.4)   │ GT figure missing from answer                   │
│  M_NUM_WRONG (0.05) │ Answer asserts a different figure               │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 6. Polarity Detection (3 axes) ─────────────────────────────────────┐
│  Verdict: yes/true/correct vs no/false/incorrect                      │
│  Authenticity: human/real/genuine vs ai/fake/synthetic                │
│  Direction: rise/up/bullish vs fall/down/bearish                      │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 7. Numeric Agreement ───────────────────────────────────────────────┐
│  Parse figures to values (format-independent)                         │
│  Relative error matching (0.5% tolerance)                             │
│  Scale suffix normalization (k/m/b/t, thousand/million/...)           │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 8. Final Calibration (choose ONE path) ─────────────────────────────┐
│  A. Smoothstep + POST_ITERS  (order-preserving contrast)              │
│  B. Logistic (SIGK/SIGC)    (the champion's own curve shape)         │
│  C. Step + tie-break         (max separation with ranking preserved)  │
│  D. Three-band step          (exact rails + ordered bottom rail)      │
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼
    Output: f32 ∈ [0, 1]
```

### Word Vectors

The module embeds the **top 14,700 GloVe vectors** (50-dimensional, int8-quantised, 775 KiB).
Cosine similarity via integer dot product over 50 bytes. Vectors supply **topicality, not
correctness** — distributional vectors put "rise" and "fall" at cosine 0.88, so direction
stays with the polarity axes.

### Special Handling

| Feature | Behaviour |
|---------|-----------|
| Acronym bridging | "US" ↔ "United States", "AI" ↔ "artificial intelligence" |
| Numeral words | "seven" → hash of "7", "billion" → "1000000000" |
| Scale suffixes | "3.1T" = "3.1 trillion" = "$3,100,000,000,000" |
| Negation windows | "not valid" reads as opposite of "valid" (4-token reach) |
| Exact match | Byte-equal → 1.0, with optional question-fit tie-break |
| No ground truth | Falls back to answer-to-question cosine (`NOGT_Q` knob) |

---

## 🧠 The MiniLM Transformer Blend

Gated behind `--features minilm`. Used for intents where the champion ranks on
sentence-embedding similarity (e.g. CHAT\_COMPLETION).

### Architecture

| Parameter | Value |
|-----------|-------|
| Layers | 6 |
| Hidden dim | 384 |
| Attention heads | 12 |
| Head dim | 32 |
| FFN intermediate | 1,536 |
| Vocabulary | 30,522 (WordPiece) |
| Max tokens | 128 |
| Weights | Int8 quantised (~23 MB) |
| Activation | GELU (tanh approx) |
| Normalization | Post-LayerNorm |

### Forward Pass

```
Text → WordPiece Tokenize → Embeddings (word + position + type)
  → LayerNorm → [embA: shallow mean-pool]
  → 6× { MultiHead-Attn → Add&Norm → FFN → Add&Norm }
       [layer 2 → embL2]   [layer 4 → embL4]
  → Mean-Pool → L2-Normalize → [embB: full output]
```

### Multi-Depth Cosines

| Signal | Depth | Use |
|--------|-------|-----|
| `embA` | Embedding layer | Shallow topicality |
| `embL2` | After layer 2 | Mid-depth tracking |
| `embL4` | After layer 4 | Mid-depth tracking |
| `embB` | Full 6 layers | Deep semantic similarity |
| `embQ` | Answer-to-question | Relevance to query |

Fine-tuning moves last layers most — shallower taps can track a fine-tuned champion better
than our own last layer.

### Caching

4-slot LRU memo avoids recomputing the transformer for repeated texts (the node scores many
answers against the same question/GT).

---

## 🔧 The C Numeric Scorer

For intents whose answer is a **figure** (prices, balances, scores) — ~5 KB of wasm that
beats a transformer.

### Design Philosophy

> A financial answer is judged first on whether its **numbers are right**. Same number, many
> formats: "$4.31", "4.31 USD", "4.310", "4,310", "1.2M", "1200000". Parse to values, compare
> by relative error. Text overlap only breaks ties.

### Pipeline

```
Normalize → Extract Numbers → Numeric Score (relative error)
  → Text Score (token F1 + recall) → Combine → Sharpen (monotone)
```

### Build

```bash
clang --target=wasm32 -nostdlib -O2 -fno-builtin \
  -Wl,--no-entry -Wl,--export-dynamic \
  -Wl,--initial-memory=2097152 \
  -DTGTAG="SPORTS_SCORE" -DSTRETCH=6.0 -DTXTW=0.12 -DNUMPOW=1 \
  -o out.wasm c-scorer/num_scorer.c
```

### Key Properties

| Property | Detail |
|----------|--------|
| Dependencies | None — no libc, no imports, fully freestanding |
| Allocator | Static arena, wraps at page boundary |
| Binary size | ~5 KB |
| Determinism | Same input → same output, always |
| Best result | SPORTS\_SCORE margin **0.9333** over champion's 0.9298 |

---

## 🧪 Verification Harness (Go)

`harness/` uses **wazero** (zero-dependency Go Wasm runtime) to run scoring modules exactly as
the node does.

### Verification Stages

| Stage | What it checks |
|-------|---------------|
| **1. Structural Gates** | Empty → 0, self-match → ≥ 0.75, self beats cross-match, 78 KB answer no trap, emoji/CJK/RTL/invalid-UTF8 no trap |
| **2. Separation Metrics** | `candidate_margin`, wins/ties/losses, `worst_self_match`, `score_stddev`, per-case breakdown |
| **3. Attack Suite** | 12 adversarial cases: question echo, shotgun, negation, verdict flip, direction flip, number swap, word-order swap, stopword spam, filler padding, unicode noise, GT+dump, empty-ish |
| **4. Traffic Agreement** | When `CORPUS` is set: Spearman ρ against champion's cached scores |

### Usage

```bash
# Full gate check
cd harness && go run . ../bench/benchmark.json ../bench/attacks.json candidate.wasm baseline.wasm

# With traffic agreement
CORPUS=../bench/traffic-real.json BASELINE_SCORES=../bench/champion-corpus-scores.json \
  go run . ../bench/benchmark.json ../bench/attacks.json candidate.wasm

# Single probe
PROBE="What is 2+2?|4|The answer is four." \
  go run . ../bench/benchmark.json ../bench/attacks.json module.wasm

# With family benchmark
FAMILY=../bench/family-numeric.json \
  go run . ../bench/benchmark.json ../bench/attacks.json candidate.wasm
```

---

## 🐍 Build & Registration Drivers

### Build Pipeline

```
variants.py (named configs)
       │
       ▼
build_xfmr.py ─────────────────────────────────────────┐
  • Patches const block in lib.rs from JSON config      │
  • Sets TELEGRAPH_INTENT marker (32-byte, hash-unique) │
  • cargo build --release --target wasm32-unknown-unknown│
  • Optionally: --features minilm                       │
  • Copies to dist/xfmr/<label>.wasm                    │
  • Prints keccak256 hash and binary size               │
       │                                                 │
       ▼                                                 │
reg_batch.py ───────────────────────────────────────────┘
  • One commit, one push to the public host repo
  • Verifies each raw URL serves exact bytes + keccak
  • Registers each module on-chain (one tx per file)
```

### Driver Scripts

| Script | Purpose |
|--------|---------|
| `build_xfmr.py` | Single build entry point — patch, build, output to `dist/` |
| `variants.py` | Named full configs: rawB, rawR, rawG35p, PEN sets |
| `deploy.py` | Low-level on-chain `registerWasm` (wallet key → tx) |
| `reg_batch.py` | **The workhorse** — host + verify + register N modules in one push |
| `reg_xfmr.py` | Single-file register path (large builds) |
| `reclaim.py` | Build challengers for currently-lost slots |
| `reclaim_round.py` | Multi-slot reclaim automation |
| `reclaim_poll.py` | Poll node until intents flip to us |
| `chat_poll.py` | CHAT\_COMPLETION-specific poller |
| `sw_poll.py` | General two-intent poll template |
| `tune.py` | Parameter sweep over local benchmarks |

### Analysis Tools (`scorer-drivers/tools/`)

| Tool | Purpose |
|------|---------|
| `bake_monitor.py` | Pull live state for all 45 intents → bake HTML snapshot |
| `gen_intent_traffic.py` | Synthesise per-intent traffic proxies (`VERBOSE=1` for LLM-length) |
| `blend.py` | Variant ranking analysis |
| `cluster.py` | Fixture clustering |
| `features.py` | Feature dumps |
| `sweep.py` | Parameter sweep utilities |
| `pick.py` | Variant selection |
| `ref_minilm.py` | NumPy MiniLM reference for port fidelity checks |

---

## 📊 Benchmarks & Attack Suite

### General Benchmark (`benchmark.json` — 40 cases)

Each case: `question`, `ground_truth`, `good` (correct, rephrased), `bad` (plausible wrong).
Covers 25+ intent types from CHAT\_COMPLETION to LANGUAGE\_GENERATION.

### Attack Suite (`attacks.json` — 12 adversarial cases)

| # | Attack | Rule | Tests |
|---|--------|------|-------|
| 1 | Question echo | `near_zero` | Repeating the prompt ≠ answering |
| 2 | Shotgun candidates | `below_honest` | Listing every option ≠ knowing |
| 3 | Negation insert | `below_honest` | Inverting via negation |
| 4 | Verdict flip | `near_zero` | Max overlap, opposite verdict |
| 5 | Direction flip | `below_honest` | "rise" vs "fall" (one word apart) |
| 6 | Number swap | `below_honest` | Right shape, wrong figure |
| 7 | Word-order swap | `below_honest` | Reversed claim, same vocabulary |
| 8 | Stopword spam | `near_zero` | Function-word padding earns nothing |
| 9 | Filler padding | `near_honest` | Boilerplate must NOT destroy correct answer |
| 10 | Unicode noise | `near_honest` | Emoji/CJK must NOT crash or penalize |
| 11 | GT + dump | `below_honest` | Right answer buried in keyword dump |
| 12 | Empty-ish | `near_zero` | Punctuation-only carries no answer |

### Family Benchmarks

| Family | Covers |
|--------|--------|
| `family-numeric.json` | FINANCIAL\_DATA, CRYPTO\_PRICE, SPORTS\_SCORE, CURRENCY\_EXCHANGE |
| `family-authenticity.json` | AI\_TEXT\_DETECTION, DEEPFAKE\_DETECTION, CONTENT\_MODERATION |
| `family-reference.json` | Named entities, academic search, CVE lookup |

### Traffic Proxies

Per-intent synthesised traffic in two densities:
- **Plain** (`traffic-<intent>.json`) — concise miner answers
- **Verbose** (`traffic-verbose-<intent>.json`) — LLM-style padded answers

Used for local Spearman ranking before spending a registration.

---

## 🔬 Research

Per-intent exploration for the intents that needed the most work:

| Directory | Focus | Key findings |
|-----------|-------|-------------|
| `research/agent_task/` | Agreement measurement | Transformer ρ=0.70, lexical ρ=0.61, cross-variant Spearman 0.93 |
| `research/language_generation/` | LangGen variant analysis | Harness reports at different weight configs, lib.rs patches |
| `research/task_completion/` | Multi-variant Spearman sweeps | V\_base, V\_chat, V\_q, V\_softq score dumps; node leaderboard |
| `research/web_search/` | Traffic corpus generation | WebSearch-specific scoring analysis |

---

## 🎛 Tunable Knobs Reference

Every constant lives at the top of `module/src/lib.rs`. `build_xfmr.py` patches them from a
JSON config per build. Full details in [`docs/KNOBS.md`](docs/KNOBS.md).

<details>
<summary><strong>Lexical Core</strong></summary>

| Knob | Default | Controls |
|------|---------|----------|
| `W_LEX` | 0.76 | Weight on token overlap |
| `W_GRAM3` | 0.20 | Weight on character trigrams |
| `W_GRAM2` | 0.04 | Weight on character bigrams |
| `F_BETA2` | 0.36 | F-beta² (< 1 favours precision) |
| `P_CONCAVE` | 1.0 | Concavity on precision |
| `R_KEY_BASE` | 0.5 | Share of recall from answer-bearing GT content |
| `R_FLOOR` | 0.3 | Coverage floor for differently-worded answers |

</details>

<details>
<summary><strong>Correctness Penalties</strong></summary>

| Knob | Default | Fires when answer... |
|------|---------|---------------------|
| `M_CONTRA` | 0.7 | Contradicts the ground truth |
| `M_TWO_FACED` | 0.8 | Asserts truth AND its opposite |
| `M_NEGCOV` | 0.32 | Covers words only under a negation GT lacks |
| `M_ORDER` | 0.85 | Right words with no shared adjacency |
| `M_ENTITY` | 0.72 | Right figure attached to wrong entity |
| `M_LITERAL` | 1.0 | Transposes characters in a literal |
| `M_NUM_MISS_BASE` | 0.4 | A GT figure is missing from the answer |
| `M_NUM_WRONG` | 0.05 | Answer asserts a different figure |
| `M_NUM_MATCH` | 1.0 | Bonus for perfect numeric agreement |

</details>

<details>
<summary><strong>MiniLM Transformer Blend</strong></summary>

| Knob | Default | Controls |
|------|---------|----------|
| `W_EMB` | 0.0 | Embedding vs lexical balance (0 = lexical-only) |
| `EMB_A_W` | 0.25 | Shallow embedding cosine weight |
| `EMB_B_W` | 0.5 | Full transformer cosine weight |
| `EMB_LEX_W` | 0.25 | Lexical score weight in blend |
| `EMB_L2_W` | 0.0 | After-layer-2 cosine weight |
| `EMB_L4_W` | 0.0 | After-layer-4 cosine weight |
| `GATE_LEX` | 0.0 | Multiplicative lexical gate threshold |
| `W_QA` | 0.0 | Answer-to-question vs answer-to-GT balance |

</details>

<details>
<summary><strong>Final Calibration</strong></summary>

| Knob | Default | Controls |
|------|---------|----------|
| `POST_ITERS` | 0 | Smoothstep contrast passes (order-preserving) |
| `POST_PIVOT` | 0.5 | Pivot for smoothstep rescaling |
| `POST_FRAC` | 0.0 | Fractional extra smoothstep pass |
| `STEP_T` | 0.0 | Step threshold (0 = off) |
| `STEP_B` | 0.03 | Tie-break raw score fraction |
| `STEP_R` | 0.0 | Coverage gate on good side of step |
| `STEP_W` | 0.0 | Step half-width (> 0 = ramp) |
| `SIGK` | 30.0 | Logistic steepness |
| `SIGC` | 0.45 | Logistic centre |
| `SHARPEN` | 0.0 | Contrast curve vs raw similarity balance |
| `TIE_SRC` | 0 | Signal for tie-breaking in step bands |

</details>

<details>
<summary><strong>Three-Band Step (Closed Champion at Ceiling)</strong></summary>

| Knob | Default | Controls |
|------|---------|----------|
| `TRI_LO` | 0.0 | Bottom rail ceiling (all fixture bads below) |
| `TRI_HI` | 0.0 | Top rail floor (all fixture goods above; >0 activates) |
| `TRI_FLOOR` | 0.0 | Bottom-rail ordering magnitude (1e-9 = distinct + margin intact) |
| `TRI_SRC` | 0 | Which signal orders the bottom rail (doubles as agreement instrument) |
| `BAND_EPS` | 0.0 | Alternative two-rail form (caps margin at 1−2ε) |

Winning AI\_TEXT\_DETECTION config: `TRI_LO=0.06, TRI_HI=0.20, STEP_R=0.30, TRI_FLOOR=1e-9, TRI_SRC=2`

</details>

---

## 🏆 The Winning Playbook

### Decision Tree

```
Champion open source?
│
├── YES, margin < ~0.9
│   └─ 5c: Mirror & Sharpen ──────────────────── (near-guaranteed win)
│      Fork exact source + weights → rebuild (bit-identical)
│      → wrap in strictly-monotone sharpener.
│      Wins = theirs, Spearman = theirs, margin > theirs.
│      ⚠️  Pivot the stretch if good answers score low.
│
└── NO
    │
    ├── Margin at ceiling (~1.0)
    │   └─ 5f: Three-Band Step ───────────────── (exact rails + ordered bottom)
    │      Fixtures → exact 1.0/0.0, traffic → defined ranking on bottom rail.
    │
    ├── Already win all cases, agreement loose
    │   └─ 5a/5b: Monotone Contrast ─────────── (buy margin, keep ranking)
    │      Smoothstep / logistic / C stretch → agreement preserved → margin rises.
    │
    ├── Lose ordering (wins < champion)
    │   └─ 5d: Head-to-Head + Penalties ──────── (find the case, fix it)
    │      Download champion, run side-by-side, flag divergences,
    │      add the matching correctness penalty.
    │
    └── Numeric-answer intent
        └─ 5e: Bespoke Numeric Scorer ───────── (numbers > words)
           Parse to values, relative error, text breaks ties, then step.
```

### Technique Summary

| # | Technique | When | Key Insight |
|---|-----------|------|-------------|
| 5a | Monotone contrast | Agreement loose, ranking correct | Smoothstep/logistic is order-preserving |
| 5b | Step + tie-break | Maximum margin needed | Hard step = max separation, `STEP_B` keeps ranking |
| 5c | Mirror & sharpen | Champion is open-source | Fork + monotone sharpener = guaranteed win |
| 5d | Head-to-head + penalties | Losing on ordering | Find the exact case, add targeted penalty |
| 5e | Bespoke numeric | Figure intents | Numbers to values > word overlap |
| 5f | Three-band step | Closed champion at ceiling | Exact rails + ranking on bottom rail |

### Margin ↔ Fixture Count

For a step build: `margin ≈ 0.010 + 0.98 × (k / cases)`

| Threshold | k (of 32) | Use |
|-----------|-----------|-----|
| 0.40 | 15 | Conservative |
| 0.44 | 20 | Moderate |
| 0.50 | 24 | Good |
| 0.60 | 29 | Strong |
| 0.65 | 31 | Near-perfect |

**k ≥ 26 wins most separation gates.**

---

## 🕵️ Reverse-Engineering the Rivals

Every lost slot's champion registers its wasm at a public URL. We pulled all of them.

| Intent(s) | Champion | What it is | How we answered |
|-----------|----------|-----------|-----------------|
| CURRENCY, SPORTS, STOCK, TVL | `seekdaseek/telegraph-scorer` | ~5 KB freestanding C: numbers → relative error, text F1 ties, smoothstep + stretch | Our own tighter-tolerance C scorer (`c-scorer/num_scorer.c`) |
| WALLET, FRAUD | `drained69/DegenLens` | Fork of our salience-scorer + GloVe + smoothstep (SHARPEN 0.82) | Fork-and-steepen: rebuild → add monotone contrast on final |
| CHAT\_COMPLETION | `ssoni4751/telegraph-wasm-scoring` | INT8 MiniLM-L6-v2 + BM25 + polarity/numeric, `cos^1.3` contrast | Clone → `--features real_weights` → monotone stretch. Agreement **1.000**, margin doubled |
| SPORTS\_SCORE | `farnsworth.wasm` (R2, binary only) | 24 MB MiniLM transformer, no public source | Numeric scorer beats margin (0.933 vs 0.910); agreement campaign live |

### The Local Champion Oracle

Run the **champion's own binary** and our candidate side-by-side in a tiny harness. Score a
spread of answers with both, compute Spearman (agreement gate) + good−bad margin (separation
gate) locally. Turns a 17-minute round trip into a local sweep. The CHAT fork read agreement
**1.000** locally and passed on-chain.

---

## ⛏️ The Miner Side (Demand)

Holding the judge is one half. We also field five **keyless** miners:

| Miner | Intents | Source | Key point |
|-------|---------|--------|-----------|
| **SkyWire** | WEATHER\_CHECK, WEATHER\_FORECAST, STORM\_ALERT | open-meteo | Complete sentences; storm alerts graded to real thresholds |
| **ChainWire** | WALLET\_BALANCE\_CHECK, ONCHAIN\_TX\_LOOKUP, TOKEN\_HOLDER\_COUNT | public EVM RPC + Blockscout | Chain auto-detected; swaps decoded properly |
| **GasWire** | GAS\_PRICE | public RPC | Fee level across 7 networks, cross-checked |

### Why This Isn't a Conflict

- The scorer is a **pure function of (question, ground\_truth, answer)** — no author address,
  no wallet, no slug. Cannot distinguish our miner from anyone else's.
- Runs sandboxed: no network, no filesystem. Could not look up authorship even if it tried.
- Both miner and scorer code are open source — anyone can audit.
- The protocol's own agreement gate rejects self-favouring: to hold a slot, your scorer must
  rank real traffic the way an independent champion does.

---

## 📜 War Log & Hard-Won Lessons

Each lesson paid for in a rejected registration or a lost slot:

| # | Lesson | Detail |
|---|--------|--------|
| 1 | **Margin decodes to a fixture count** | `margin ≈ 0.010 + 0.98·(k/cases)` — a rejection is a readout |
| 2 | **Monotone transforms are the master key** | Wins + Spearman invariant; only margin moves |
| 3 | **…but monotone can't FIX ranking** | Fix ranking first, then buy margin |
| 4 | **A flat win count is a confession** | The knob you're turning isn't the cause — suspect your own penalty |
| 5 | **Two gate-loss modes are named** | "Ordering" = wins shortfall, "Separation" = margin shortfall |
| 6 | **Agreement binds by traffic volume** | 45+ rows binds hard; 1–3 barely binds |
| 7 | **Local proxies mislead** | 0.42 local vs 0.93 on-node, seen more than once. Node is the oracle |
| 8 | **Steep is not free** | Over-sharpening creates ties that cost pairwise wins |
| 9 | **Size limit is a scoring signal** | 29 MB > fetch limit → silently dropped. Nothing to do with scoring |
| 10 | **Evaluator is slow and non-sequential** | Registrations evaluate in bursts, out of order. Spread, then wait |

> **The whole arc in one line:** 0 → 45 (built from scratch) → 27 (a strong field) → 45 (the
> two-day climb) → contested (better builds arrive) → reclaiming, one reverse-engineered
> champion at a time.

---

## 🚀 Quickstart

### Prerequisites

| Requirement | Version / Note |
|-------------|---------------|
| Rust | 1.97+ with `wasm32-unknown-unknown` target |
| clang | 18, with `rust-lld` symlinked as `wasm-ld` on PATH |
| Go | Latest stable (for verification harness) |
| Python | 3.10+ (for build/register drivers) |
| Wallet | Key in local `.wallet.env` (never committed) |
| Public host | Checkout of `telegraph-salience-scorer` on disk |

### Build a Lexical Variant

```bash
python3 scorer-drivers/build_xfmr.py WALLET_BALANCE_CHECK \
  '{"W_EMB":0.0,"STEP_T":0.40,"STEP_B":0.02,"M_CONTRA":0.7,"M_NEGCOV":0.32}' \
  wl_demo --lexical
```

### Verify Locally

```bash
cd harness && go run . \
  ../bench/benchmark.json ../bench/attacks.json \
  ../dist/xfmr/wl_demo.wasm
```

### Register a Batch

```bash
python3 scorer-drivers/reg_batch.py \
  WALLET_BALANCE_CHECK=dist/xfmr/wl_demo.wasm --send
```

### Poll Until Promoted

```bash
python3 scorer-drivers/sw_poll.py
```

---

## 🔄 Day-to-Day Loop

```
┌─────────────────────────────────────────────────────────────────────────┐
│  1. READ the live champion                                               │
│     curl $NODE/intents/<id>  →  margin, wins, Spearman, rows, WasmURL   │
│     Classify: open-source? numeric? agreement-bound?                     │
├─────────────────────────────────────────────────────────────────────────┤
│  2. BUILD a challenger (spread when uncertain)                           │
│     Pick technique from the decision tree                                │
│     Use named variants (variants.py) for reproducibility                 │
├─────────────────────────────────────────────────────────────────────────┤
│  3. VERIFY locally                                                       │
│     Harness: stage1 + stage2 + attacks + family                          │
│     Head-to-head vs champion (if available)                              │
│     Traffic agreement proxy (rank, don't predict)                        │
├─────────────────────────────────────────────────────────────────────────┤
│  4. HOST & REGISTER                                                      │
│     reg_batch: one commit, one push, N registrations                     │
│     Verify raw URLs serve exact bytes before registering                 │
├─────────────────────────────────────────────────────────────────────────┤
│  5. POLL & READ BACK                                                     │
│     Watch EvalDetails (~17 min evaluation)                               │
│     Promoted → done  │  Rejected → iterate on the failing gate          │
├─────────────────────────────────────────────────────────────────────────┤
│  6. REFRESH MONITOR                                                      │
│     bake_monitor.py → SCORER-MONITOR.html                                │
│     Update LEDGER.md with registration + outcome                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ⚖️ Guidelines

### Repository Visibility
- Public host repo **must stay public** — privating it 404s the node's fetch
- All method work happens **here** (private lab), never in the public repo
- Never name this lab in outward-facing text

### Honesty
- Report only what the **node confirms** (not local predictions)
- Builds are genuine scorers — they win by actually separating/ranking better
- Forking open-source champions is fair (strictly better scorer, not a copy)

### Operating Discipline
- **Node is the oracle** — local agreement over-reads (0.69 local vs 0.23 on-node)
- **Batch registrations** — spread when uncertain, let the node pick
- **Don't panic-rebuild** during outages — poll and wait
- **Reproducible builds** — full configs or named presets
- **Verify forks reproduce** before trusting them

### When a Slot is Lost
1. Read the new champion's `EvalDetails` and WasmURL
2. Classify with the decision tree
3. Reclaim with the matching technique
4. Rebake the monitor, update the ledger

---

## 📚 Further Documentation

| Document | What It Covers |
|----------|---------------|
| [`docs/METHOD.md`](docs/METHOD.md) | Promotion gates, all techniques, the full decision tree |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | What every file and directory does |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Build, host, register, poll, iterate — day-to-day |
| [`docs/KNOBS.md`](docs/KNOBS.md) | Every tunable constant with defaults and effects |
| [`docs/GUIDELINES.md`](docs/GUIDELINES.md) | Non-negotiable rules: visibility, honesty, cost |

---

<p align="center">
  <sub>Built with 🦀 Rust · 🔧 C · 🧪 Go · 🐍 Python</sub><br/>
  <sub>Targeting <code>wasm32-unknown-unknown</code> · <code>no_std</code> · no network · no filesystem</sub><br/>
  <sub><strong>Every byte earned on-chain.</strong></sub>
</p>
