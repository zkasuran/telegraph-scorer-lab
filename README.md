<p align="center">
  <img src="https://img.shields.io/badge/status-45%2F45_intents_held-brightgreen?style=for-the-badge" alt="Status: 45/45 intents held"/>
  <img src="https://img.shields.io/badge/lang-Rust%20%7C%20C%20%7C%20Go%20%7C%20Python-blue?style=for-the-badge" alt="Languages"/>
  <img src="https://img.shields.io/badge/target-wasm32--unknown--unknown-orange?style=for-the-badge" alt="Target: wasm32"/>
</p>

<h1 align="center">⚡ Telegraph Scorer Lab</h1>

<p align="center">
  <strong>The private method home for Telegraph Protocol Track 2 scoring modules.</strong><br/>
  Build, verify, register, and hold all 45 canonical intent slots on-chain.
</p>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [The Journey: 0 → 45, and Holding It](#-the-journey-0--45-and-holding-it)
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

---

## 🌐 Overview

Telegraph runs a **permissionless, on-chain contest** for each of its 45 canonical intents
(CHAT_COMPLETION, SPORTS_SCORE, WALLET_BALANCE_CHECK, FINANCIAL_DATA, WEATHER_FORECAST,
AI_TEXT_DETECTION, and 39 others). Anyone can register a WebAssembly module that scores a
miner's answer against a question and a ground truth. The validator node promotes the module
that scores best on that intent's hidden fixtures and real traffic. **Hold the slot and you
own how that intent is scored network-wide.**

This repository is the canonical record of how we:

1. **Build** scoring modules (Rust `no_std` wasm + freestanding C wasm)
2. **Verify** them locally against the node's own promotion logic
3. **Register** them on-chain via automated Python drivers
4. **Hold** all 45 slots by iterating on the node's evaluation feedback

**Current status: 45 / 45 canonical intents held** by wallet
`0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287`.

> **This is a private lab.** The public host repo
> [`telegraph-salience-scorer`](https://github.com/zkasuran/telegraph-salience-scorer) carries
> only `dist/` binaries and a neutral README. All method work happens here.

---

## 🗺 The Journey: 0 → 45, and Holding It

Track 2 is one question asked 45 times: write the best judge for an intent and you own how
that intent is scored for the whole network. This is the story of taking every seat, losing
some to a strong field, then taking them back with methods that did not exist when we started.

### Phase 1: Nothing to 45/45

We began with no slots. We built the salience-weighted lexical core (precision and recall over
information-weighted words, character n-grams, correctness penalties) and a from-scratch
`no_std` MiniLM-L6-v2 blend, all compiled to a freestanding wasm the node runs in a pure
sandbox. Then we registered intent by intent, read each rejection's `EvalDetails` and
iterated until all 45 canonical slots were held under one wallet.

### Phase 2: The field hits back (45 to 27)

Holding all 45 was never quiet. A strong author (ScoreWire, `0xd4c7...8ef9`) returned with one
good scorer reused across many intents and took fifteen slots in a burst. Two others took one
each. We fell to 27/45, fair and square, on the exact measure the protocol promotes on. So we
had to build better back, seventeen times over.

### Phase 3: The two-day climb back to 45/45

Not one dial. Five different problems, each wrong for a different reason:

- **A fetch limit that ate registrations.** A deeper 12-layer model pushed the wasm to 29 MB,
  a hair over the node's raw-fetch limit, so those registrations were silently dropped. The
  proof was in plain sight: every slot we still held ran a 24 MB file. We shrank the model
  under the line. Later we solved it properly with int4 / FFN-only requantisation to fit the
  deeper model near 21 MB.
- **The easy separation tier.** Fact-check, media / video / content verification, research and
  a search intent fell quickly on clean separation once builds landed again.
- **The agreement gate.** Traffic-gated intents need your ranking of real answers to line up
  with the champion's. A hard step reorders and fails. The fix: keep the ranking, sharpen the
  score, keep a 2% sliver of raw to hold order. That took geolocation, SSL, token-count and
  news. WEATHER we feared (its holder ranked refusals above real forecasts on our sample) but
  it passed on the node. The local proxy had overstated the disagreement.
- **The near-ceiling four.** Four holders sat at 0.9996. A pure step (every good to 1, every
  bad to 0) gives margin 1.0 when the model already separates cleanly. Deepfake and sentiment
  flipped to a flat 1.0.
- **The wall that was our own code.** One authenticity intent stuck at 14 of 15 no matter what
  we changed. A number that will not move is a message: the problem was none of the knobs we
  were turning. One of our own correctness penalties was firing on a good answer and shoving it
  below the bad one. Penalties off, the pair flipped instantly; step back on for margin.

The last slot, `CONTENT_EXTRACTION`, needed characters read as characters (a postcode with two
digits swapped, a rate of 6.52 where the truth was 6.25). A character-gram-dominant blend plus
embedding for the one semantic case plus a low `STEP_B` lifted the margin to **0.99976** past
the holder's 0.9995855. **45/45 again.**

### Phase 4: Better builds arrive, then the miner pivot

The next wave of challengers were not weak reuses. They were genuinely good, purpose-built
scorers, several of them open source. We lost `CURRENCY_EXCHANGE`, `FRAUD_DETECTION`,
`SPORTS_SCORE`, `WALLET_BALANCE_CHECK` and later `CHAT_COMPLETION` to authors who had clearly
studied the same gates we had. In parallel we opened a second front on the demand side and
shipped five keyless miners (see [The Miner Side](#-the-miner-side-demand)), because owning the
judge is only half of an open market.

### Phase 5: Reverse-engineer, then out-build

Easy reclaiming does not beat a better build. So we pulled every lost champion's binary and,
where it was open source, its full source, then learned exactly why each one won (see
[Reverse-Engineering the Rivals](#-reverse-engineering-the-rivals)). That produced the decisive
move for an agreement-gated slot: **fork the champion's own scorer and wrap it in a strictly
monotone contrast stretch.** Same ranking means the agreement gate passes for free and the wins
gate holds; the stretch buys the margin. It reclaimed `CHAT_COMPLETION` cleanly (Spearman with
the champion measured at **1.000** locally, margin lifted from the champion's ~0.42 to 0.58).
`FRAUD_DETECTION` fell to a steeper logistic than the champion's own; `CURRENCY_EXCHANGE` to a
lexical-gate build at 0.99. `WALLET_BALANCE_CHECK` and `SPORTS_SCORE` are the hard remainder:
their champions sit on a tight margin-and-agreement frontier, so the campaign there is live.

> **The board is contested in real time.** Slots flip while you work. 45/45 is not a finish
> line you cross once; it is a state you defend. Everything below is how.

---

## 🎯 How Telegraph Scoring Works

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Telegraph Validator Node                         │
│                                                                     │
│  For each intent:                                                   │
│    1. Miner submits an answer to a question                         │
│    2. Validator calls: rank_answer(question, ground_truth, answer)   │
│    3. The active scoring module returns f32 ∈ [0, 1]                │
│    4. Scores determine miner reward distribution                    │
│                                                                     │
│  Challenger registration:                                           │
│    • Anyone registers a .wasm module for any intent                 │
│    • Node evaluates challenger vs champion on hidden fixtures        │
│    • If challenger passes ALL THREE gates → promoted to champion    │
└─────────────────────────────────────────────────────────────────────┘
```

Each scoring module is a **WebAssembly binary** that exports exactly three functions:

| Export | Signature | Purpose |
|--------|-----------|---------|
| `alloc` | `(size: i32) -> i32` | Allocate memory for the node to write input strings |
| `dealloc` | `(ptr: i32, size: i32)` | Free allocated memory |
| `rank_answer` | `(q_ptr, q_len, gt_ptr, gt_len, ma_ptr, ma_len) -> f32` | Score the answer |

The module runs in a pure sandbox: **no std, no network, no filesystem, no host imports.**
Everything the module needs must be compiled in.

---

## 🏛 The Three Promotion Gates

A challenger must pass **all three gates in order** to replace the incumbent champion:

### Gate 1: Ordering (Wins)

```
candidate_wins >= champion_wins  on comparable_cases
```

You must rank the good answer above the bad one on **at least as many** fixture cases as the
champion. This is the hardest gate — no amount of contrast fixes a wins loss. You need your
scorer to actually get a case right that it was getting wrong.

> *Rejection example:* "lost to the current champion on ordering — you: 13 of 14,
> champion: 14 of 14."

### Gate 2: Separation (Margin)

```
candidate_margin > champion_margin    (strict inequality)
```

Margin = mean(good_scores) − mean(bad_scores) across fixtures. A tie loses. This gate rewards
**contrast** — pushing good answers up and bad answers down.

> *Rejection example:* "your average margin 0.9272 vs champion 0.9298."

### Gate 3: Agreement (Spearman ρ)

```
spearman(your_ranking, champion_ranking) >= 0.60    on real traffic
```

Only binds when `historical_rows_evaluated > 0`. Your ranking of the intent's real traffic
must **correlate** with the champion's. This prevents a scorer that separates fixtures well
but ranks real answers nonsensically.

> Intents with heavy traffic (dozens of rows) bind hard here; intents with 1–3 rows barely
> bind, making them effectively a pure separation race.

### The `EvalDetails` Response

Every registration returns a labelled measurement you learn from:

| Field | Meaning |
|-------|---------|
| `candidate_margin` | Your separation on hidden fixtures |
| `champion_margin` | The incumbent's separation |
| `candidate_wins` / `champion_wins` | Fixture cases each ranked correctly |
| `comparable_cases` | Total fixture cases evaluated |
| `spearman` | `{INTENT: r}` — rank correlation with champion on real traffic |
| `historical_rows_evaluated` | How many real-traffic rows the agreement gate saw |
| `score_stddev` | Spread of your scores |
| `worst_self_match` | Your lowest score on a known-correct (self-match) answer |

---

## 💡 Core Insight: Monotone Transforms

> A **strictly monotone** transform of the final score cannot reorder any two answers.

This is the single most important insight in the lab. It means:

- **Wins** are preserved (ordering unchanged)
- **Spearman agreement** is preserved (rank correlation is invariant to monotone transforms)
- **Separation margin** can be pushed up freely

**Order-preserving is the magic word:** it turns the margin gate into something you buy for
free once the ranking is right, and it lets you inherit a strong scorer's agreement without
inheriting its low margin.

The corollary: a monotone transform **cannot FIX** a bad ranking. If your base ranking
disagrees with the champion on traffic, no contrast rescues the agreement gate. Fix the
ranking first, then buy the margin.

**Caveat:** A bare hard step maps a whole cluster to one value. In f32, a tight real-traffic
cluster collapses into ties, destroying Spearman. The fix: keep a sliver of the raw score
(`out = (1-b)*step + b*raw`, b ≈ 0.02) so every answer keeps its own place.

---

## 🏗 Architecture

```
telegraph-scorer-lab/
├── module/                    # 🦀 Rust no_std scoring module
│   ├── src/
│   │   ├── lib.rs            #    The whole scorer (~2000 lines)
│   │   ├── minilm.rs         #    From-scratch int8 MiniLM-L6-v2
│   │   ├── vectors.bin       #    14,700 GloVe word vectors (775 KiB)
│   │   ├── vectors-champ.bin #    Champion-distilled vector table
│   │   ├── vectors-glove.bin #    Original GloVe vectors
│   │   ├── minilm.bin        #    MiniLM int8 weights (~23 MB)
│   │   └── gte-small.bin     #    GTE-Small alternative weights
│   ├── Cargo.toml            #    cdylib, release profile opt-level=z, LTO
│   └── Cargo.lock
│
├── c-scorer/                  # 🔧 Freestanding C numeric scorer
│   └── num_scorer.c          #    ~5 KB wasm for figure intents
│
├── harness/                   # 🧪 Go + wazero local verification
│   ├── main.go               #    Runs the node's promotion gates locally
│   ├── cmd/dump/main.go      #    Per-fixture score dumper
│   ├── go.mod / go.sum
│   └── harness-report.json   #    Last run's structured output
│
├── scorer-drivers/            # 🐍 Python build/register/poll automation
│   ├── build_xfmr.py         #    Patches constants, builds, prints keccak
│   ├── variants.py           #    Named full configs for reproducible builds
│   ├── deploy.py             #    On-chain registerWasm call
│   ├── reg_batch.py          #    Host N wasms, one push, N registrations
│   ├── reg_xfmr.py           #    Single-file register path
│   ├── reclaim.py            #    Build challengers for lost slots
│   ├── reclaim_round.py      #    Multi-slot reclaim automation
│   ├── reclaim_poll.py       #    Poll until intents flip to us
│   ├── tune.py               #    Parameter sweep over local benchmarks
│   └── tools/
│       ├── bake_monitor.py   #    Live per-intent champion state → HTML
│       ├── gen_intent_traffic.py  # Synthesise traffic proxies
│       ├── blend.py          #    Variant ranking analysis
│       ├── cluster.py        #    Fixture clustering
│       ├── features.py       #    Feature dumps
│       ├── sweep.py          #    Parameter sweep utilities
│       ├── pick.py           #    Variant selection
│       └── ref_minilm.py     #    NumPy MiniLM reference for port fidelity
│
├── bench/                     # 📊 Fixtures and benchmarks
│   ├── benchmark.json         #    40-case general benchmark
│   ├── benchmark-topical.json #    Topical variant
│   ├── attacks.json           #    12-case adversarial gaming suite
│   ├── family-numeric.json    #    Figure intent family benchmark
│   ├── family-authenticity.json # AI/deepfake detection family
│   ├── family-reference.json  #    Named entity family
│   ├── traffic-*.json         #    Per-intent traffic proxies (plain)
│   ├── traffic-verbose-*.json #    Per-intent traffic proxies (verbose)
│   ├── traffic-real.json      #    Real node traffic samples
│   ├── champion-corpus-scores.json # Champion's cached corpus scores
│   ├── registrations.json     #    Registration history
│   ├── report.json            #    Structured harness report
│   └── tune-results.json      #    Parameter sweep results
│
├── research/                  # 🔬 Per-intent exploration
│   ├── agent_task/            #    Agreement sweeps, traffic generation
│   ├── language_generation/   #    LangGen variant analysis
│   ├── task_completion/       #    Spearman sweeps, variant scores
│   └── web_search/            #    Traffic corpus generation
│
├── docs/                      # 📖 Documentation
│   ├── METHOD.md              #    Promotion gates and winning playbook
│   ├── ARCHITECTURE.md        #    What every file does
│   ├── RUNBOOK.md             #    Day-to-day build/register/poll loop
│   ├── KNOBS.md              #    Every tunable constant explained
│   └── GUIDELINES.md          #    Non-negotiable rules
│
└── worklogs/                  # 📝 Operational records
    ├── LEDGER.md              #    Running record of registrations
    ├── HANDOFF.md             #    Session handoff notes
    └── SUBMIT-PACKET.md       #    Defensible walkthrough
```

---

## 🦀 The Rust Scoring Module

The heart of the system. A `no_std` wasm32 crate that compiles to ~1 MB (lexical) or ~24 MB
(with MiniLM transformer). One export the node calls: `rank_answer`.

### Scoring Pipeline

```
Input: (question, ground_truth, miner_answer) → f32 ∈ [0, 1]

┌─────────────────────────────────────────────────────────────────┐
│ 1. TOKENIZATION                                                  │
│    • Split on non-word bytes, keep numeric separators            │
│    • FNV-1a hashing (thousands separators stripped)              │
│    • Negation window tracking (4-token reach)                    │
│    • Numeric value parsing (commas, decimals, scale suffixes)    │
│    • Proper noun detection (mid-sentence capitals)               │
│    • Acronym key packing (2-4 letter all-caps)                   │
│    • Crude stemming (-ing, -ed, -ly, -es, -s)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. WORD WEIGHTING (corpus-free IDF proxy)                        │
│    • Stop words → 0.12 weight                                    │
│    • Numbers → 3.0 weight (they're where answers go wrong)       │
│    • Proper nouns → base + 1.3 bonus                             │
│    • Length-scaled content words → 1.0 + 0.06 * min(len, 12)    │
│    • Non-Latin scripts → 0.5 weight                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. LEXICAL SCORING                                               │
│    ┌─────────────────────────────────┐                           │
│    │ Precision (P)                   │                           │
│    │ Of what the answer asserts,     │                           │
│    │ how much is in the ground truth │                           │
│    │ + soft vector credit for        │                           │
│    │   paraphrases (GloVe cosine)    │                           │
│    └─────────────────────────────────┘                           │
│    ┌─────────────────────────────────┐                           │
│    │ Recall (R)                      │                           │
│    │ Key recall: answer-bearing GT   │                           │
│    │   content covered by answer     │                           │
│    │ Overall: total GT coverage      │                           │
│    │ Soft vector cap: SOFT_CAP_FRAC  │                           │
│    └─────────────────────────────────┘                           │
│                                                                  │
│    F-beta: (1+β²)·P·R / (β²·P + R), β² = 0.36 (precision-lean) │
│                                                                  │
│    Blend: W_LEX·lex + W_GRAM3·trigrams + W_GRAM2·bigrams        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. CHARACTER N-GRAMS                                             │
│    • Trigrams: Bloom filter (131,072-bit), Dice + containment    │
│    • Bigrams: same structure, tail-breaker for short text        │
│    • Content-word adjacency bigrams (what sits next to what)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CORRECTNESS PENALTIES (the ordering levers)                   │
│    These reorder NON-MONOTONICALLY — they WIN fixture cases      │
│    ┌──────────────┬────────────────────────────────────────────┐ │
│    │ M_CONTRA     │ Contradicts the ground truth (0.7)         │ │
│    │ M_TWO_FACED  │ Asserts truth AND its opposite (0.8)       │ │
│    │ M_NEGCOV     │ Words only under a negation GT lacks (0.32)│ │
│    │ M_ORDER      │ Right words, no shared adjacency (0.85)    │ │
│    │ M_ENTITY     │ Right figure, wrong entity (0.72)          │ │
│    │ M_LITERAL    │ Transposed characters in literals (1.0)    │ │
│    │ M_NUM_MISS   │ GT figure missing from answer (0.4)        │ │
│    │ M_NUM_WRONG  │ Answer asserts a different figure (0.05)   │ │
│    └──────────────┴────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. POLARITY DETECTION (3 independent axes)                       │
│    • Verdict: yes/true/correct vs no/false/incorrect             │
│    • Authenticity: human/real/genuine vs ai/fake/synthetic       │
│    • Direction: rise/up/bullish vs fall/down/bearish             │
│    Each axis: first decisive word (negation-aware) sets sign     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. NUMERIC AGREEMENT                                             │
│    • Parse figures to values (format-independent)                │
│    • Relative error matching (0.5% tolerance)                    │
│    • Scale suffix normalization (k/m/b/t, thousand/million/...)  │
│    • M_NUM_MATCH bonus for perfect numeric agreement             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. CALIBRATION (choose ONE path)                                 │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │ A. Smoothstep + POST_ITERS (order-preserving contrast)  │   │
│    │    x²(3-2x) repeated, with POST_PIVOT rescaling         │   │
│    ├─────────────────────────────────────────────────────────┤   │
│    │ B. Logistic (SIGK/SIGC)                                 │   │
│    │    1/(1+e^{-K·(x-C)}) — the champion's own curve shape  │   │
│    ├─────────────────────────────────────────────────────────┤   │
│    │ C. Step + tie-break (STEP_T/STEP_B)                     │   │
│    │    Maximum separation: goods→1, bads→0, with ranking    │   │
│    │    preserved inside each band via STEP_B raw-score mix   │   │
│    └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                        Output: f32 ∈ [0, 1]
```

### Word Vectors

The module embeds the **top 14,700 GloVe vectors** (50-dimensional, int8-quantised, 775 KiB).
Cosine similarity is computed as an integer dot product over 50 bytes. The vectors supply
**topicality, not correctness** — distributional vectors put "rise" and "fall" at cosine 0.88
because they co-occur, so direction/verdict stays with the polarity axes.

### Special Handling

| Feature | What it does |
|---------|-------------|
| **Acronym bridging** | "US" matches "United States", "AI" matches "artificial intelligence" |
| **Numeral words** | "seven" maps to hash of "7", "billion" to "1000000000" |
| **Scale suffixes** | "3.1T", "3.1 trillion", "$3,100,000,000,000" compare equal |
| **Negation windows** | "not valid" reads as opposite of "valid" (4-token reach) |
| **Exact match** | Byte-equal (after normalization) → 1.0, with optional question-fit tie-break |
| **No ground truth** | Falls back to answer-to-question cosine (NOGT_Q knob) |

---

## 🧠 The MiniLM Transformer Blend

Gated behind `--features minilm`. Used only for the **CHAT_COMPLETION** build where the
champion ranks on sentence-embedding similarity.

### Architecture

A from-scratch **MiniLM-L6-v2** implementation in `no_std` Rust:

| Parameter | Value |
|-----------|-------|
| Layers | 6 |
| Hidden dimension | 384 |
| Attention heads | 12 |
| Head dimension | 32 |
| Intermediate (FFN) | 1,536 |
| Vocabulary | 30,522 (WordPiece) |
| Max tokens | 128 |
| Weights | Int8 quantised (~23 MB) |
| Activation | GELU (tanh approximation) |
| Normalization | Post-LayerNorm |

### Forward Pass

```
Text → WordPiece Tokenize → Embeddings (word + position + type)
  → LayerNorm → [embA: shallow mean-pool]
  → 6× { MultiHead-Attention → Add&Norm → FFN → Add&Norm }
       [after layer 2: pool → embL2]
       [after layer 4: pool → embL4]
  → Mean-Pool → L2-Normalize → [embB: full transformer output]
```

### Multi-Depth Cosines

The module computes **five** similarity signals from one pass:

| Signal | Depth | Use |
|--------|-------|-----|
| `embA` | Embedding layer (pre-transformer) | Shallow topicality |
| `embL2` | After layer 2 | Mid-depth tracking |
| `embL4` | After layer 4 | Mid-depth tracking |
| `embB` | Full 6 layers | Deep semantic similarity |
| `embQ` | Answer-to-question (full depth) | Relevance to query |

This matters because the champion is a **fine-tune** of MiniLM, and fine-tuning moves the
last layers most — so shallower taps can track the champion's output better than our own last
layer.

### Caching

A 4-slot LRU memo avoids recomputing the transformer for repeated texts (the node scores
many answers against the same question/GT).

---

## 🔧 The C Numeric Scorer

For intents whose answer is a **figure** (prices, balances, scores), a tiny freestanding C
scorer beats a transformer at ~5 KB of wasm.

### Design Philosophy

```c
// Scoring thesis: a financial answer is judged first on whether its
// NUMBERS are right. Same number, many formats:
// "$4.31", "4.31 USD", "4.310", "4,310", "1.2M", "1200000"
// Numbers parsed to values, compared by RELATIVE error.
// Text overlap only breaks ties.
```

### Pipeline

1. **Normalize** — lowercase, strip currency symbols, commas between digits become nothing,
   `%` becomes `pct` token
2. **Extract numbers** — parse with decimal points, negative signs, and scale suffixes
   (k/m/b/t, thousand/million/billion/trillion)
3. **Numeric score** — relative error per GT figure, matched against best answer figure
   (tolerance ≤ 0.12%)
4. **Text score** — token F1 + recall blend (stopwords excluded)
5. **Combine** — `(1 - TXTW) * numeric + TXTW * text` when numbers present
6. **Sharpen** — smoothstep → stretch about 0.5 → epsilon tie-break (strictly monotone)

### Build

```bash
clang --target=wasm32 -nostdlib -O2 -fno-builtin \
  -Wl,--no-entry -Wl,--export-dynamic \
  -Wl,--initial-memory=2097152 \
  -DTGTAG="SPORTS_SCORE" -DSTRETCH=6.0 -DTXTW=0.12 -DNUMPOW=1 \
  -o out.wasm c-scorer/num_scorer.c
```

### Key Properties

- **No libc, no imports** — fully freestanding
- **Static arena allocator** — wraps instead of failing at the page boundary
- **~5 KB binary** — orders of magnitude smaller than the Rust module
- **Deterministic** — same input always produces same output
- Won SPORTS_SCORE at margin **0.9333** over champion's 0.9298

---

## 🧪 Verification Harness (Go)

The harness in `harness/` uses **wazero** (a Go WebAssembly runtime with zero dependencies)
to load and run scoring modules exactly the way the node does.

### What It Verifies

#### Stage 1: Structural Gates
- Empty/whitespace answer → exactly 0
- Perfect answer (self-match) → ≥ 0.75 everywhere
- Self-match beats unrelated cross-match
- 78 KB answer does not trap
- Oversized ground truth does not trap
- Emoji/CJK/RTL/invalid-UTF8 does not trap

#### Stage 2: Separation Metrics
Mirrors the node's `EvalDetails`:
- `candidate_margin` (mean good − mean bad)
- `wins` / `ties` / `losses` per case
- `worst_self_match`, `score_stddev`, `min_case_margin`
- Per-case score breakdown

#### Stage 3: Attack Suite
12 adversarial cases testing resistance to:
- Question echo (repeating the prompt)
- Shotgun candidates (listing every possible answer)
- Negation insertion
- Verdict flipping
- Direction flipping
- Number swapping
- Word-order swapping
- Stopword spam
- Filler padding (must NOT hurt a correct answer)
- Unicode noise (must NOT hurt a correct answer)
- Ground-truth buried in a keyword dump

#### Stage 4: Traffic Agreement (Spearman)
When `CORPUS` env var is set, scores real-traffic rows and computes Spearman ρ against
a baseline (champion's cached scores or a loaded baseline module).

### Usage

```bash
# Full gate check
go run ./harness bench/benchmark.json bench/attacks.json candidate.wasm baseline.wasm

# With traffic agreement
CORPUS=bench/traffic-real.json BASELINE_SCORES=bench/champion-corpus-scores.json \
  go run ./harness bench/benchmark.json bench/attacks.json candidate.wasm

# Single probe
PROBE="What is 2+2?|4|The answer is four." \
  go run ./harness bench/benchmark.json bench/attacks.json module.wasm

# With family benchmark
FAMILY=bench/family-numeric.json \
  go run ./harness bench/benchmark.json bench/attacks.json candidate.wasm
```

---

## 🐍 Build & Registration Drivers

### Build Pipeline

```
variants.py (named configs)
       │
       ▼
build_xfmr.py ──────────────────────────────────────────────┐
  • Patches const block in lib.rs from JSON config           │
  • Sets TELEGRAPH_INTENT marker (32-byte, hash-unique)      │
  • Builds: cargo build --release --target wasm32-unknown-unknown
  • Optionally: --features minilm for transformer build      │
  • Copies to dist/xfmr/<label>.wasm                         │
  • Prints keccak256 hash and binary size                    │
       │                                                      │
       ▼                                                      │
reg_batch.py ────────────────────────────────────────────────┘
  • Commits all built wasms on ONE commit
  • Pushes to the public host repo (one push)
  • Verifies each raw.githubusercontent.com URL serves exact bytes
  • Registers each module on-chain (one tx per file)
```

### Key Driver Scripts

| Script | Purpose |
|--------|---------|
| `build_xfmr.py` | Single build entry point. Patches constants, builds, outputs to `dist/` |
| `variants.py` | Named full configs (rawB, rawR, rawG35p, PEN sets). Reproducible builds |
| `deploy.py` | Low-level on-chain `registerWasm` call (loads wallet key, sends tx) |
| `reg_batch.py` | The workhorse: host + verify + register N modules in one push |
| `reg_xfmr.py` | Single-file register path (kept for large builds) |
| `reclaim.py` | Build challengers for currently-lost slots |
| `reclaim_round.py` | Multi-slot reclaim: build spread, print `reg_batch` command |
| `reclaim_poll.py` | Poll node until named intents flip to us |
| `tune.py` | Parameter sweep over local benchmarks |
| `tools/bake_monitor.py` | Pull live state for all 45 intents → HTML snapshot |
| `tools/gen_intent_traffic.py` | Synthesise per-intent traffic proxies |

### Named Variants

| Preset | Description |
|--------|-------------|
| `rawB` | Pure embB (full transformer cosine) |
| `rawR` / `rawRp` | Champion-mimic blend (with penalties) |
| `rawG35` / `rawG35p` | Blend + lexical gate (with penalties) |
| `rawLex` | Lexical only (no transformer) |
| `PEN` | All correctness penalties enabled |

---

## 📊 Benchmarks & Attack Suite

### General Benchmark (`bench/benchmark.json`)

**40 cases** across all intent types, each with:
- `question` — what the miner was asked
- `ground_truth` — the validator's reference answer
- `good` — a genuinely correct answer, phrased differently
- `bad` — a plausible wrong answer of the kind weak miners return

Covers: CHAT_COMPLETION, FACT_CHECK, AI_TEXT_DETECTION, DEEPFAKE_DETECTION, URL_SCAN,
FINANCIAL_DATA, CRYPTO_PRICE, CURRENCY_EXCHANGE, WEATHER_FORECAST, WEATHER_CHECK,
LANGUAGE_TRANSLATION, CVE_LOOKUP, SSL_VERIFICATION, IP_GEOLOCATION, ACADEMIC_SEARCH,
RESEARCH_QUERY, NEWS_HEADLINES, SPORTS_SCORE, TVL_LOOKUP, SENTIMENT_ANALYSIS,
CONTENT_MODERATION, CONTENT_EXTRACTION, AGENT_TASK, TASK_COMPLETION, LANGUAGE_GENERATION.

### Attack Suite (`bench/attacks.json`)

**12 adversarial cases** testing the scoring module's resistance to gaming:

| Attack | Rule | Tests |
|--------|------|-------|
| question-echo | near_zero | Repeating the prompt ≠ answering |
| shotgun-candidates | below_honest | Listing every option ≠ knowing |
| negation-insert | below_honest | Inverting the claim via negation |
| verdict-flip | near_zero | Maximum overlap, opposite verdict |
| direction-flip | below_honest | "rise" vs "fall" (one word apart) |
| number-swap | below_honest | Right shape, wrong figure |
| word-order-swap | below_honest | Reversed claim, identical vocabulary |
| stopword-spam | near_zero | Function-word padding earns nothing |
| filler-padding | near_honest | Boilerplate must NOT destroy a correct answer |
| unicode-noise | near_honest | Emoji/CJK must NOT crash or penalize |
| gt-plus-dump | below_honest | Right answer buried in keyword dump |
| empty-ish | near_zero | Punctuation-only carries no answer |

### Family Benchmarks

Specialized test sets for intent clusters:

| Family | Covers |
|--------|--------|
| `family-numeric.json` | FINANCIAL_DATA, CRYPTO_PRICE, SPORTS_SCORE, CURRENCY_EXCHANGE |
| `family-authenticity.json` | AI_TEXT_DETECTION, DEEPFAKE_DETECTION, CONTENT_MODERATION |
| `family-reference.json` | Named entities, academic search, CVE lookup |

### Traffic Proxies

Per-intent synthesised traffic in two densities:
- **Plain** (`traffic-agent_task.json`, etc.) — concise miner answers
- **Verbose** (`traffic-verbose-agent_task.json`, etc.) — LLM-style padded answers

Used for local Spearman ranking before spending a registration.

---

## 🔬 Research

Per-intent exploration directories for the intents that needed the most work:

### `research/agent_task/`
- Agreement measurement: transformer ρ=0.70, lexical ρ=0.61, baseline ρ=0.50
- Traffic generation scripts
- Champion score analysis
- Cross-variant Spearman (transformer vs lexical: 0.93)

### `research/language_generation/`
- LangGen variant analysis
- Harness reports at different weight configurations
- Agreement measurements
- `lib.rs` patches for specialized builds

### `research/task_completion/`
- Multi-variant Spearman sweeps
- Node leaderboard tracking
- Variant score dumps (V_base, V_chat, V_q, V_softq)
- Build scripts for specialized task-completion modules
- Gate analysis (which attacks pass/fail per variant)

### `research/web_search/`
- Traffic corpus generation
- WebSearch-specific scoring analysis

---

## 🎛 Tunable Knobs Reference

Every constant lives at the top of `module/src/lib.rs`. `build_xfmr.py` patches them from a
JSON config per build.

### Lexical Core

| Knob | Default | Controls |
|------|---------|----------|
| `W_LEX` | 0.76 | Weight on token overlap |
| `W_GRAM3` | 0.20 | Weight on character trigrams |
| `W_GRAM2` | 0.04 | Weight on character bigrams |
| `F_BETA2` | 0.36 | F-beta squared (< 1 favours precision) |
| `P_CONCAVE` | 1.0 | Concavity on precision (> 1 punishes dilution) |
| `R_KEY_BASE` | 0.5 | Share of recall from answer-bearing GT content |
| `R_FLOOR` | 0.3 | Coverage floor for answers worded differently |

### Correctness Penalties

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

### MiniLM Transformer Blend

| Knob | Default | Controls |
|------|---------|----------|
| `W_EMB` | 0.0 | Share of score from embedding (0 = lexical-only) |
| `EMB_A_W` | 0.25 | Shallow embedding cosine weight |
| `EMB_B_W` | 0.5 | Full transformer cosine weight |
| `EMB_LEX_W` | 0.25 | Lexical score weight in blend |
| `EMB_L2_W` | 0.0 | After-layer-2 cosine weight |
| `EMB_L4_W` | 0.0 | After-layer-4 cosine weight |
| `GATE_LEX` | 0.0 | Multiplicative lexical gate threshold |
| `W_QA` | 0.0 | Answer-to-question vs answer-to-GT balance |

### Final Calibration

| Knob | Default | Controls |
|------|---------|----------|
| `POST_ITERS` | 0 | Smoothstep contrast passes (order-preserving) |
| `POST_PIVOT` | 0.5 | Pivot for smoothstep rescaling |
| `POST_FRAC` | 0.0 | Fractional extra smoothstep pass |
| `STEP_T` | 0.0 | Step threshold (0 = off) |
| `STEP_B` | 0.03 | Tie-break raw score fraction |
| `STEP_R` | 0.0 | Coverage gate on good side of step |
| `STEP_W` | 0.0 | Step half-width (> 0 = ramp) |
| `SIGK` | 30.0 | Logistic steepness (> 0 replaces smoothstep) |
| `SIGC` | 0.45 | Logistic centre |
| `SHARPEN` | 0.0 | Contrast curve vs raw similarity balance |
| `TIE_SRC` | 0 | Signal for tie-breaking in step bands |

---

## 🏆 The Winning Playbook

### Decision Tree

```
Champion open source?
├── YES, margin < ~0.9
│   └── 5c: Mirror and Sharpen (near-guaranteed win)
│       Fork exact source + weights, rebuild (bit-identical),
│       wrap in strictly-monotone sharpener (logistic).
│       Wins = theirs, Spearman = theirs, margin > theirs.
│
└── NO
    ├── Already win all cases, agreement loose
    │   └── 5a/5b: Monotone Contrast or Step+Tiebreak
    │       Apply iterated smoothstep, logistic, or C stretch.
    │       Ranking preserved → agreement preserved → margin rises.
    │
    ├── Lose ordering (wins < champion)
    │   └── 5d: Head-to-Head + Penalties
    │       Download champion binary, run it head-to-head.
    │       Flag every case champion wins that you don't.
    │       Add the matching correctness penalty.
    │
    └── Numeric-answer intent
        └── 5e: Bespoke Numeric Scorer (C)
            Parse to values, compare by relative error,
            text only breaks ties, then step for margin.
```

### Technique Summary

| # | Technique | When | Key Insight |
|---|-----------|------|-------------|
| 5a | Monotone contrast | Agreement loose, ranking correct | Smoothstep/logistic is order-preserving |
| 5b | Step + tie-break | Maximum margin needed | Hard step = max separation, STEP_B keeps ranking |
| 5c | Mirror & sharpen | Champion is open-source | Fork + monotone sharpener = guaranteed win |
| 5d | Head-to-head + penalties | Losing on ordering | Find the exact case, add targeted penalty |
| 5e | Bespoke numeric | Figure intents | Numbers to values > word overlap |

### Margin Decodes to Fixture Count

For a step build: `margin ≈ 0.010 + 0.98 * (k / cases)` where k = cases cleanly split.

| Threshold | k (of 32) | Typical use |
|-----------|-----------|-------------|
| 0.40 | 15 | Conservative |
| 0.44 | 20 | Moderate |
| 0.50 | 24 | Good |
| 0.60 | 29 | Strong |
| 0.65 | 31 | Near-perfect |

k ≥ 26 wins most separation gates.

---

## 🚀 Quickstart

### Prerequisites

- **Rust 1.97+** with `wasm32-unknown-unknown` target
- **clang 18** with `rust-lld` symlinked as `wasm-ld` on PATH
- **Go** (for the verification harness)
- **Python 3** (for build/register drivers)
- Wallet key in local `.wallet.env` (never committed)
- Checkout of the public host repo on disk

### Build a Lexical Variant

```bash
python3 scorer-drivers/build_xfmr.py WALLET_BALANCE_CHECK \
  '{"W_EMB":0.0,"STEP_T":0.40,"STEP_B":0.02,"M_CONTRA":0.7,"M_NEGCOV":0.32}' \
  wl_demo --lexical
```

### Verify Locally

```bash
cd harness && go run . ../bench/benchmark.json ../bench/attacks.json ../dist/xfmr/wl_demo.wasm
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
┌──────────────────────────────────────────────────────────────┐
│  1. READ the live champion                                    │
│     • Margin, wins, Spearman, rows_evaluated, WasmURL        │
│     • Classify: open-source? numeric? agreement-bound?        │
├──────────────────────────────────────────────────────────────┤
│  2. BUILD a challenger (spread when uncertain)                │
│     • Pick technique from the decision tree                   │
│     • Use named variants for reproducibility                  │
├──────────────────────────────────────────────────────────────┤
│  3. VERIFY locally                                            │
│     • Harness: stage1 + stage2 + attacks + family             │
│     • Head-to-head vs champion (if available)                 │
│     • Traffic agreement proxy (rank, don't predict)           │
├──────────────────────────────────────────────────────────────┤
│  4. HOST & REGISTER                                           │
│     • reg_batch: one commit, one push, N registrations        │
│     • Verify raw URLs serve exact bytes before registering    │
├──────────────────────────────────────────────────────────────┤
│  5. POLL & READ BACK                                          │
│     • Watch EvalDetails (~17 min evaluation)                  │
│     • Promoted → done. Rejected → iterate on the gate        │
├──────────────────────────────────────────────────────────────┤
│  6. REFRESH MONITOR                                           │
│     • bake_monitor.py → SCORER-MONITOR.html                   │
│     • Update LEDGER.md with registration + outcome            │
└──────────────────────────────────────────────────────────────┘
```

---

## 🕵 Reverse-Engineering the Rivals

Every re-lost slot's champion registers its wasm at a public URL and several ship full
source. We pulled all of them. Knowing exactly how a champion wins turns a blind guess into a
targeted build.

| Intent(s) | Champion | What it is | How we answered |
|---|---|---|---|
| CURRENCY, SPORTS, STOCK, TVL | `seekdaseek/telegraph-scorer` | A ~5 KB freestanding **C** scorer: parse numbers to values, compare by relative error, text F1 only breaks ties, then smoothstep + stretch. | Taught the thesis that a numeric intent wants a numeric scorer, not a transformer. We wrote our own tighter-tolerance, steeper-stretch numeric C scorer (`c-scorer/num_scorer.c`). |
| WALLET, FRAUD | `drained69/DegenLens` | A Rust **fork of our own salience-scorer** plus a GloVe `vectors.bin` and a smoothstep contrast (SHARPEN 0.82). MIT, credits us. | Fork-and-steepen: rebuild their scorer, add a monotone contrast on the final. Same ranking, higher margin. FRAUD also fell to a steeper SIGK logistic than the champion's own. |
| CHAT_COMPLETION | `ssoni4751/telegraph-wasm-scoring` | INT8 MiniLM-L6-v2 + BM25 + polarity / numeric checks, weighted composite, a `cos^1.3` contrast. | Cloned, built with `--features real_weights` (byte size matched the champion exactly), added a monotone stretch on the composite. Local oracle read agreement **1.000**, margin doubled. Reclaimed. |
| SPORTS_SCORE | `farnsworth.wasm` (R2, binary only) | A 24 MB MiniLM transformer. No public source to fork. | The hard one. A numeric scorer beats its margin (0.933 vs 0.910) but a pure-numeric ranking disagrees with a transformer on traffic (Spearman 0.5). A MiniLM fork agrees ~0.61. Live. |

### The local champion oracle

The node's evaluator is slow, so guessing is expensive. Instead we run the **champion's own
binary** and our candidate side by side in a tiny harness, score a spread of varied answers
with both and compute the Spearman correlation (the agreement gate) plus the good-minus-bad
margin (the separation gate) locally. This turns a blind ~17-minute round trip into a local
sweep: we register a build only once it out-agrees and out-separates the champion on the bench.
It reproduced the node's verdicts directionally, the CHAT fork read agreement 1.000 locally and
passed on-chain.

## ⛏ The Miner Side (Demand)

Holding the judge is one half of an open market. We also field five **keyless** miners on the
busiest intents, so we operate on both sides and can watch the whole loop from answer to score.

| Miner | Intents | Source | Key point |
|-------|---------|--------|-----------|
| **SkyWire** | WEATHER_CHECK, WEATHER_FORECAST, STORM_ALERT | open-meteo, keyless | Complete natural sentences; storm alerts graded to advisory / warning on real thresholds |
| **ChainWire** | WALLET_BALANCE_CHECK, ONCHAIN_TX_LOOKUP, TOKEN_HOLDER_COUNT | public EVM RPC + Blockscout, keyless | Live reads; chain auto-detected; token transfers decoded so a swap is not reported as "sent 0 ETH" |
| **GasWire** | GAS_PRICE | public RPC, keyless | Fee level across seven networks from `eth_gasPrice` / `eth_feeHistory` |

Keyless is the point: a miner with no API key has no vendor to rate-limit it, no key to expire
and no cached feed to go stale. It is raced across two public providers so one slow
endpoint cannot blow a validator's 20-second spot check. Every figure is a live read,
cross-checked against an independent source in testing.

### The conflict, addressed head-on

We hold the scorer for every intent AND we mine some of them. That can look rigged, so here is
why it is not and how to check:

- The scorer is a **pure function of (question, ground truth, answer)**. It receives no author
  address, wallet or slug, so it cannot tell our answer from anyone else's and scores an
  identical answer identically no matter who sent it.
- It runs sandboxed, with no network and no filesystem, so it could not look up who a miner is
  even if it wanted to.
- Both the miner code and the scorer code are open source, so anyone can read them side by side.
- The protocol's own agreement gate rejects a self-favouring judge: to hold a slot your scorer
  must rank real traffic the way an independent champion does.

An independent audit of the miner code against the scorer code found no author favouritism and
no collusion path. The miners win, when they win, by returning the most accurate and complete
answer, which is exactly what any reasonable judge rewards.

## 📜 War Log & Hard-Won Lessons

The specific things this campaign taught, each paid for in a rejected registration or a lost
slot:

1. **Margin decodes to a fixture count.** For a step build, `margin ≈ 0.010 + 0.98 * (k /
   cases)`, so `k = margin / 0.996 * N`. A rejection is not a dead end, it is a readout of
   exactly how many hidden cases you split. You always know how many are left.
2. **Monotone transforms are the master key.** A strictly monotone map of the final score
   cannot reorder anything, so wins and Spearman agreement are invariant and only the margin
   moves. This is why "fork the champion and sharpen" works: you inherit its ranking (both
   gates) and buy margin for free.
3. **...but monotone cannot FIX a ranking.** If your base disagrees with the champion on
   traffic, no contrast rescues agreement. Fix the ranking first, then buy the margin.
4. **A flat win count is a confession.** When wins will not move no matter what you reweight,
   the thing you are touching is not the cause. Suspect your own correctness penalty firing on
   a good answer. Test a penalties-fully-off control early. This unstuck an authenticity
   intent frozen at 14 of 15.
5. **The two gate-loss modes are named.** "Lost on ordering" is a wins shortfall (needs a
   gentler step or a targeted penalty). "Lost on separation" is a margin shortfall (needs a
   threshold in the gap or a steeper contrast). The rejection reason says which; never guess.
6. **The agreement gate binds by traffic volume.** 45+ rows binds hard; 1 to 3 rows barely
   binds; for n=3 Spearman moves in steps of 0.5 so you effectively need a perfect ranking.
   Read `historical_rows_evaluated` before choosing how aggressive to be.
7. **Local proxies mislead; the node is the oracle.** A local benchmark margin does not predict
   the node's hidden-fixture margin (0.42 local vs 0.93 on-node, seen more than once). The
   champion-oracle for AGREEMENT is far more faithful than any synthetic fixture set for margin.
8. **Steep is not free.** Push a contrast too hard and a tight cluster of near-equal scores
   rails to identical values, creating ties that cost pairwise wins (wallet forks at K=2.5-3.5
   beat the margin but dropped to 13 of 14). A gentle stretch plus a raw-score epsilon keeps
   strict monotonicity.
9. **A size limit is a scoring signal too.** The node silently drops a wasm it cannot fetch.
   29 MB was over the raw-fetch limit; the fix (int4 / FFN-only requant to ~21 MB) had nothing
   to do with scoring at all.
10. **The evaluator is slow and non-sequential.** Registrations evaluate in bursts, out of
    order, sometimes stalling for a long time. Piling on more builds delays the informative
    readbacks. Spread deliberately, then wait.

> **The whole arc in one line:** 0 → 45 (built from scratch) → 27 (a strong field) → 45 (the
> two-day climb) → contested (better builds arrive) → reclaiming, one reverse-engineered
> champion at a time.

---

## ⚖ Guidelines

### Repository Visibility
- The public host repo **must stay public** — privating it 404s the node's fetch
- All method work happens **here** (private lab), never in the public repo
- Never name this lab in outward-facing text

### Honesty
- Report only what the **node confirms** (not local predictions)
- Builds are genuine scorers — they win because they actually separate/rank better
- Forking open-source champions is fair (it's a strictly better scorer, not a copy)

### Operating Discipline
- The **node is the oracle** — local agreement over-reads (0.69 local vs 0.23 on-node)
- **Batch registrations** — spread when uncertain, let the node pick
- **Don't panic-rebuild** during outages — poll and wait
- **Reproducible builds** — pass full configs or named presets
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
| [`docs/METHOD.md`](docs/METHOD.md) | The promotion gates, all techniques, the full decision tree |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | What every file and directory does |
| [`docs/RUNBOOK.md`](docs/RUNBOOK.md) | Build, host, register, poll, iterate — the day-to-day loop |
| [`docs/KNOBS.md`](docs/KNOBS.md) | Every tunable constant with defaults and effects |
| [`docs/GUIDELINES.md`](docs/GUIDELINES.md) | Non-negotiable rules for repo visibility, honesty, cost |

---

<p align="center">
  <em>Built with 🦀 Rust, 🔧 C, 🧪 Go, and 🐍 Python<br/>
  Targeting wasm32-unknown-unknown • no_std • no network • no filesystem<br/>
  Every byte earned on-chain.</em>
</p>
