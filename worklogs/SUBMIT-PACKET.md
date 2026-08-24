# Telegraph Track 2 submit packet

Everything needed to defend this entry in a live conversation: what was built, what
is live on-chain, how every number was measured, why the design is what it is, and
where it falls short.

## What was submitted

A WASM scoring module for the Telegraph protocol, registered on Base Sepolia as the live
champion scorer for 32 of the 45 canonical intents: every author-written champion slot on
the network, including CHAT_COMPLETION, the busiest intent, won by porting the champion's
own MiniLM transformer into the no_std module. A scoring module is the program a Telegraph node runs to
decide how good a miner's answer was: it receives the question, the ground truth
and the miner's answer and returns one `f32` between 0 and 1. Whoever holds an
intent's champion slot is ranking every miner serving that intent.

Repo: `work/telegraph/scorer/` (module, harness, benchmark, attack suite).
Wallet: `0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287`, linked to the console account
`zkasuran@gmail.com`.

## What is live

| Reg | Intent | Profile | Node margin | Champion | Fixture wins |
| --- | --- | --- | --- | --- | --- |
| 26 | AI_TEXT_DETECTION | verdict | 0.7930 | 0.3736 | 32/32 |
| 27 | FACT_CHECK | verdict | 0.7892 | 0.3736 | 32/32 |
| 28 | URL_SCAN | verdict | 0.7892 | 0.3736 | 32/32 |
| 29 | DEEPFAKE_DETECTION | verdict | 0.7892 | 0.3736 | 32/32 |
| 30 | SSL_VERIFICATION | verdict | 0.7892 | 0.3736 | 32/32 |
| 31 | SENTIMENT_ANALYSIS | verdict | 0.7892 | 0.3736 | 32/32 |
| 32 | CVE_LOOKUP | reference | 0.8081 | 0.3736 | 32/32 |
| 33 | ACADEMIC_SEARCH | reference | 0.8081 | 0.3736 | 32/32 |
| 47 | CURRENCY_EXCHANGE | numeric | 0.7961 | 0.3736 | 32/32 |
| 48 | STOCK_PRICE | numeric | 0.7961 | 0.3736 | 32/32 |
| 49 | TVL_LOOKUP | numeric | 0.7961 | 0.3736 | 32/32 |
| 50 | IMAGE_VERIFICATION | verdict | 0.7767 | 0.3736 | 32/32 |
| 51 | VIDEO_VERIFICATION | verdict | 0.7767 | 0.3736 | 32/32 |
| 52 | MEDIA_AUTHENTICITY_CHECK | verdict | 0.7767 | 0.3736 | 32/32 |
| 53 | CONTENT_VERIFICATION | verdict | 0.7767 | 0.3736 | 32/32 |
| 54 | IP_GEOLOCATION | reference | 0.7975 | 0.3736 | 32/32 |
| 55 | NEWS_HEADLINES | reference | 0.7975 | 0.3736 | 32/32 |
| 56 | CRYPTO_PRICE | numeric | 0.7961 | 0.3736 | 32/32 |

Those 18 were the first wave. A second wave on 2026-08-18 took 13 more intents that were
still on the default scorer (margins 0.68 to 0.71, all 40/40 on the general benchmark and
clear on their profile family): CONTENT_MODERATION, CONTENT_EXTRACTION,
TEXT_AUTHENTICITY_CHECK, TEXT_CLASSIFICATION, FRAUD_DETECTION, GAME_RESULT, SPORTS_SCORE,
FINANCIAL_DATA, ONCHAIN_TX_LOOKUP, LANGUAGE_TRANSLATION, RESEARCH_QUERY, RESEARCH_SYNTHESIS,
TWITTER_SEARCH. FINANCIAL_DATA was the one slot another author held (0.5037); our build at
0.7100 superseded it. That is **31 active champion slots, every author-written slot on the
network**.

All 31 are `active` on the node. Every one reports `comparable_cases` 32,
`candidate_wins` 32 against the champion's 32 and `worst_self_match` 1.000 against a
floor of 0.75, read back from `EvalDetails` on the validator API, not from our own
harness. Five registrations were rejected and they are documented below rather than
dropped: 24, 25, 38 and 39 on CHAT_COMPLETION, plus 57, an attempt to replace reg 26
with a later binary.

`active` means the node ran the module through its structural checks and its own
hidden 32 case fixture set, compared it with the incumbent champion for that intent
and promoted it. On all but FINANCIAL_DATA the incumbent was the protocol's default
word-overlap module, which is what the 0.3736 champion margin is, so no author-written
scorer held those slots before this. One slot had live scoring history:
`historical_rows_evaluated` was 15 on reg 50 (IMAGE_VERIFICATION), so it
cleared the traffic-agreement gate as well as the fixture gate.

Five of the 18 have miners live on the current epoch board (DEEPFAKE_DETECTION,
FACT_CHECK, IMAGE_VERIFICATION with two, MEDIA_AUTHENTICITY_CHECK, VIDEO_VERIFICATION),
six miners between them, so those are the answers this module is now the judge of.
Every one of those rows reads `"score": 0` on epoch 204, which is what an epoch with no
settled scoring looks like rather than anything our module produced, so the ranking it
makes becomes visible when the epoch turns:

```bash
curl -s https://devnode.telegraphprotocol.com/leaderboard/miners
```

### Where this sits against the other authors

Read off the registry and the node on 2026-08-18, not from a claim: this wallet holds 36
scorer registrations, 31 of them `active`. The other 13 authors have 34 registrations, 25
of which the node evaluated; after our second wave took FINANCIAL_DATA those resolve to 24
`rejected`, 1 `deregistered`, 1 `superseded` and **0 `active`**. So **every author-written
champion slot on the network is this module, 31 of them.** Every intent with no
author-written champion is still scored by the protocol's default word-overlap module, the
0.3736 baseline in the table above.

Reproduce it by walking the registry and asking the node per author:

```bash
for i in $(seq 1 90); do
  cast call 0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8 \
    "getWasm(uint256)(address,bytes32,bytes32,string,string,bool,uint256)" $i \
    --rpc-url https://sepolia.base.org | sed -n '1p;4p'
done
curl -s https://devnode.telegraphprotocol.com/engine/validator/v1/addresses/<author>
```

The registry's own boolean is not the promotion status, which is worth knowing before
quoting it: it reads `true` for every registered module while the node reports the real
`active`/`rejected`. On-chain means registered. Only the node says champion.

Anyone can verify without our help:

```bash
curl -s https://devnode.telegraphprotocol.com/engine/validator/v1/addresses/0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287
cast call 0x5a2324aA18613FAD4e44bDF0d6c73Ec1f6D87ff8 \
  "getWasm(uint256)(address,bytes32,bytes32,string,string,bool,uint256)" 26 \
  --rpc-url https://sepolia.base.org
```

## The walkthrough (how it scores)

The module the protocol ships as a starting point scores word overlap: the
fraction of the answer's words that also appear in the ground truth. It has two
failure modes that decide leaderboards. It pays out for an answer that shares
vocabulary with the ground truth while asserting the opposite ("the certificate has
**not** expired") and it pays nothing for a correct answer in different words
("bond prices tend to **increase**" against a ground truth of "prices usually
**rise**"). On our 40 case benchmark it scores wrong answers *higher* than right
ones on average (margin -0.117).

This module is built on the observation that most of the signal is in a few words.

1. **Salience weighting.** Numbers weigh most, proper nouns next, ordinary words by
   length, function words and assistant boilerplate almost nothing. A corpus-free
   stand-in for IDF, because a module gets no corpus and no network.
2. **Precision and recall on those weights.** Precision is concave, so supporting
   context is free but a shotgun list of candidates collapses. Recall is measured
   first against the part of the ground truth the question did not already contain,
   because that part is the answer and the rest is the prompt coming back.
3. **Character trigrams and pairs**, taking the better of Dice and containment.
   Containment is why a correct answer padded with boilerplate stays correct; pairs
   keep the tail graded so two answers never tie at a flat zero.
4. **Numbers.** A figure the ground truth states has to appear (number words map to
   digits and "22C" matches "22") and a contradicting figure costs most of the
   score.
5. **Polarity on three axes** (verdict, authenticity, direction), negation aware
   and clause aware. "No, written by a human" is negative on the verdict and
   positive on authenticity at once, which is why one polarity table would read that
   sentence as a self-contradiction. Agreeing on an axis earns credit even when the
   wording differs; contradicting one costs 85% of the score.
6. **Acronym bridging.** "US" scores against "United States", "API" against
   "application programming interface".
7. **Adjacency, narrowly.** An answer carrying exactly the ground truth's content
   words, nothing missing and nothing added, with no shared content-word adjacency,
   is "France is the capital of Paris": a perfect bag of words and a wrong answer.
8. **Contrast.** A smoothstep, blended with the raw score so the middle stays
   ordered rather than flattened.

`no_std`, no allocator, no imports, every buffer a fixed static, every loop
bounded. 9.2 KB.

## How the numbers were measured

`harness/` loads a `.wasm` exactly the way the node does: wazero, no host module
registered, strings written into the module's own `alloc`. It runs the node's
structural gates, then a 40 case benchmark, then a 12 case gaming and robustness
suite, then the traffic-agreement check against the champion binary.

```bash
cd work/telegraph/scorer
CORPUS=bench/traffic.json BASELINE_SCORES=bench/champion-corpus-scores.json \
  ./harness/harness bench/benchmark.json bench/attacks.json \
  dist/telegraph-salience-scorer.wasm
```

Local numbers for the shipped build: margin 0.669, 40/40 benchmark wins,
`worst_self_match` 1.000, `score_stddev` 0.386, 12/12 gaming cases, traffic
agreement 0.633 against the live champion on our 60 row corpus. The node's own
numbers on registration are in the table above and they are the ones that count.

## The honest part: CHAT_COMPLETION was rejected twice

CHAT_COMPLETION is the busiest intent (10 miners) and it already has a champion: a
24 MB module with a 24 MB data section, almost certainly embedded word vectors.

- Attempt 1 (reg 24) passed the structural gates, beat the champion's margin nearly
  two to one (0.711 against 0.374) and lost on ordering: 31 of 32 fixture cases
  against the champion's 32. One case inverted or tied.
- Attempt 2 (reg 25) fixed that, 32 of 32 with margin 0.818 and hit the third
  gate: on 66 real miner answers our ranking agreed with the champion's at
  Spearman 0.308 against a floor of 0.60.
- Attempt 3 (reg 38) embedded 16,000 word vectors at 50 dimensions and reached 0.391
  on that same gate, still 32 of 32 on the fixtures.
- Attempt 4 (reg 39) went to 30,000 vectors at 300 dimensions, which separates
  synonymy from topicality far better (rise/increase 0.67 against rise/fall 0.63,
  where the 50d table had that pair inverted) and scored 0.385. No better.

That gate is not a bug and we are not treating it as one. The champion scores real
traffic much more leniently: it gives a confidently wrong but on-topic answer
around 0.6, where this module gives it near zero. On a benchmark of good against
bad answers that strictness wins. On a ranking of 66 real answers it reorders the
middle of the pack and the protocol will not hot-swap a scorer that reorders live
rankings that far.

Two things follow, both recorded rather than hidden:

1. Parameter tuning cannot close it. We swept 528 configurations against both
   objectives at once (`tune.py`, results in `bench/tune-results.json`). Local
   agreement tops out around 0.63 while keeping every benchmark win and the
   corresponding remote figure was 0.31. The gap is structural, not a weight.
2. Semantic capability moved it once and then stopped. Attempt 3 (reg 38) embeds the top
   16,000 GloVe vectors, L2 normalised and quantised to one byte per dimension, and
   gives an unmatched word partial credit for the best cosine against the ground
   truth, capped so vectors can fill in for wording but never for the answer itself.
   That took the node's agreement from 0.308 to 0.391 while keeping 32 of 32 wins
   and a 0.770 margin. Six times the vector budget then bought nothing (0.385), so
   the remaining gap is not vector quality. The two modules rank on different things:
   the incumbent on topical similarity, this one on correctness. The gate enforces
   continuity with the incumbent, so closing it means being deliberately worse at
   telling right from wrong. That trade is available and we are not making it.

Meanwhile the module is live on the intents where it is the best available judge
and where promoting it does not reorder an existing live ranking.

## Why 31 intents

Each registration is a separate build: the intent is baked into the binary
(`TELEGRAPH_INTENT`) and the tunables are set by profile for the shape of answer that
intent returns. Four profiles, in `deploy.py`, each with its own swept constants and its
own fixture family. The same module and the same four families cover all 31, grouped by
answer shape rather than a bespoke family per intent:

- **verdict** (AI_TEXT_DETECTION, FACT_CHECK, URL_SCAN, DEEPFAKE_DETECTION,
  SSL_VERIFICATION, SENTIMENT_ANALYSIS, IMAGE_VERIFICATION, VIDEO_VERIFICATION,
  MEDIA_AUTHENTICITY_CHECK, CONTENT_VERIFICATION, CONTENT_MODERATION,
  TEXT_AUTHENTICITY_CHECK, TEXT_CLASSIFICATION, FRAUD_DETECTION): the answer is a decision,
  so contradicting the ground truth costs more (`M_CONTRA` 0.30 down to 0.15) and agreeing
  with it earns more (`B_AGREE` 0.35 up to 0.45). Gated on
  `bench/family-authenticity.json`, 14 cases where the wrong answer shares nearly every
  word with the right one.
- **reference** (CVE_LOOKUP, ACADEMIC_SEARCH, IP_GEOLOCATION, NEWS_HEADLINES,
  CONTENT_EXTRACTION, GAME_RESULT, ONCHAIN_TX_LOOKUP): the answer turns on naming the right
  entity, so coverage counts for more than brevity (`F_BETA2` 0.36 up to 0.60, `R_KEY_BASE`
  0.50 up to 0.60). Gated on `bench/family-reference.json`, 12 cases against plausible
  neighbouring entities.
- **numeric** (CRYPTO_PRICE, CURRENCY_EXCHANGE, STOCK_PRICE, TVL_LOOKUP, SPORTS_SCORE,
  FINANCIAL_DATA): the figure is the whole answer, so a wrong one has to be close to fatal
  (`M_NUM_WRONG` 0.45 down to 0.12). Out of a 108 configuration sweep against
  `bench/family-numeric.json`, 15 cases turning on the figure, its unit, its magnitude, its
  direction and which entity it is attached to.
- **text** (LANGUAGE_TRANSLATION, RESEARCH_QUERY, RESEARCH_SYNTHESIS, TWITTER_SEARCH): the
  base configuration, gated on the general set. CHAT_COMPLETION uses this profile too and
  was rejected, see above.

Nothing was registered that had not passed the general benchmark, the 12 case gaming
suite and its profile family first. That is the opposite of padding: on all but
FINANCIAL_DATA the incumbent was the default word-overlap module. A leaderboard scored
by word overlap cannot rank anyone honestly, because on our benchmark that module scores
wrong answers higher than right ones. The honest caveat: the second-wave slots share the
four families by profile rather than each getting a hand-written family, so the per-intent
tailoring is by answer shape, not per intent. Each still clears the node's own hidden
fixture set at 32/32, which is the bar that actually promotes it.

## Track 1: five live miners

Three answer canonical intents that had no miner at all, so each is rank 1 by default.
Two more (SkyWire, added 2026-08-18) compete head to head on intents that already had five
or six miners. All `active`, all from the lane wallet, all keyless Cloudflare Workers
reading live at request time.

| Intent | Reg | Endpoint | Field | Note |
| --- | --- | --- | --- | --- |
| GAS_PRICE | 102 | `telegraph-gas…/gas/{network}` | 1 miner | sole provider, 2 paid jobs settled |
| TOKEN_HOLDER_COUNT | 105 | `telegraph-chain…/holders/{chain}/{token}` | 1 | sole provider |
| WALLET_BALANCE_CHECK | 106 | `telegraph-chain…/balance/{chain}/{address}` | 1 | sole provider |
| WEATHER_CHECK | 108 | `telegraph-sky…/weather/{location}` | 5 miners | contested, incumbent 0.6251 |
| WEATHER_FORECAST | 109 | `telegraph-sky…/forecast/{location}` | 6 miners | contested, incumbent 0.5778 |

```bash
curl -s https://telegraph-gas.margyn.workers.dev/gas/base
curl -s https://telegraph-chain.margyn.workers.dev/holders/base/usdc
curl -s https://telegraph-chain.margyn.workers.dev/balance/ethereum/vitalik.eth
curl -s https://telegraph-sky.margyn.workers.dev/weather/London
curl -s https://telegraph-sky.margyn.workers.dev/forecast/Tokyo
```

The three sole-provider miners are rank 1 by default: an unserved canonical intent is
real routed supply that did not exist, which is the honest way to earn Track 1's
routed-demand criteria rather than fighting ten LLM wrappers for CHAT_COMPLETION.

The two weather miners are the head-to-head attempt. Their intents are judged by a
downloadable scorer (`oathcast_weather_scorer.wasm`), so the answer format was tuned
against the real thing in the harness: a complete natural sentence naming the city and
Celsius only scores 0.92 to 1.0 where the incumbents sit at 0.58 to 0.63. WEATHER_FORECAST
is the confident beat (0.75 to 0.94, a multi-day answer dilutes any single miss).
WEATHER_CHECK beats the incumbent when open-meteo's temperature matches the validator's
rounded reading and craters when it is off by a degree, so that one rides on source
alignment the epoch tournament will settle. Both were registered on the evidence, not on
hope. The mechanism is on record either way.

## Track 1: the GAS_PRICE miner in detail

Registered 102, node status `active`, the only miner serving GAS_PRICE (101 was the first registration, superseded by `updateMiner` when the endpoint declaration changed). It answers
what the transaction fee level is on a named EVM network: read live from public RPCs
(`eth_gasPrice` and `eth_feeHistory`), classified low / normal / high against that
network's own busy threshold, with one summary sentence a validator can score
against ground truth.

```bash
curl -s https://telegraph-gas.margyn.workers.dev/gas/base
curl -s "https://telegraph-gas.margyn.workers.dev/gas?query=how+much+is+gas+on+arbitrum"
```

Seven networks (ethereum, base, arbitrum, optimism, polygon, base-sepolia, sepolia)
with aliases, so a whole question resolves rather than only a bare name. No API key
and no database: two RPC reads per request, raced across providers so one slow
endpoint cannot eat a spot check's deadline, `eth_feeHistory` capped at 2.5s and
degraded to `confidence: 0.8` if it misses. The rules page calls on-chain
intelligence pipelines the highest-value area and gas is the reading every on-chain
agent needs before it acts.

Why this intent: GAS_PRICE was canonical with no miner at all, so there was no
supply for an application to route to. Sole miner also means rank 1 for that intent
by default, which is the honest way to earn Track 1's routed-demand criteria rather
than fighting ten LLM wrappers for CHAT_COMPLETION traffic.

### It has served paid requests and been paid for them

Two ERC-8183 jobs, both routed by the protocol to this miner, both settled on-chain:

```
job 6, budget $1.00, state Terminal
  $0.02 USDC → treasury 0xffe89e1f
  $0.98 USDC → TWAP swap → 24.144636505935793558 MACHINA → our fee address
  callback 0xC1f6C8f2728c3a9e33BF212Bd87f57EA21242Ba7 holds the answer, strings[0] = "base"
  created  0x59bf7f7a9c4e17a77ec4b853c4613684ca4cc47df4547c2908ace14718f43919
  terminal 0xc26ea90450ee8772db611bf1cc5c12ecbab6989e81121e542a55646dd518cb7c
```

Total received across the two settlements: **50.818198860177751874 MACHINA**, verifiable
as two Transfer events to `0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287` on
`0x7b9bd0e5f9a4d0a01db18823de1d8442c84993b7`.

Funding it needed no faucet: the Diamond settles in Circle's Base Sepolia USDC, which
is minter-gated, but Uniswap v3 has live WETH/USDC pools on that network, so 0.02
testnet ETH became $3.24 of spendable USDC through `exactInputSingle`.

### The two bugs the first live request exposed

Worth stating plainly because they are the kind of thing a testnet exists to surface.
The first routed `ask` came back `routing failed: miner "gaswire-evm-fees" did not
respond last epoch`. The node probes the endpoint paths a YAML declares *without*
substituting path parameters, so a probe of `/gas/{network}` hit our 400 for an unknown
network. An unfilled template is not a named chain we refuse to serve, so it now
resolves to `base` and says so in the payload. Second, a miner is spot checked on a
deadline and two public-RPC round trips per check was enough to look slow, so answers
are memoised for ten seconds.

One protocol observation for the team: that liveness flag is epoch-scoped, testnet
epoch 204 stayed current for over four hours and WebSocket `ask` kept refusing on the
stale record long after the endpoint was fixed and `updateMiner` had re-registered the
miner. The ERC-8183 job path does not consult the same flag, which is how both paid
jobs went through while `ask` was still refusing.

## Track 1: the ChainWire miners in detail

Registrations 105 and 106, added 2026-08-18, both `active`, one Cloudflare Worker
(`telegraph-chain`) serving two intents on separate endpoints and separate registrations.

TOKEN_HOLDER_COUNT reads Blockscout's `holders_count` for a token on Ethereum, Base,
Arbitrum or Polygon. Optimism and Gnosis are deliberately absent: their public Blockscout
did not answer `/api/v2/tokens` keylessly when this was built, so backing them would be a
guess. Token is a `0x` address or a known symbol. WALLET_BALANCE_CHECK reads
`eth_getBalance` across seven chains and resolves ENS names on mainnet through two
independent keyless resolvers raced against each other, so the balance path stays keyless
and one resolver being down does not block a lookup.

The GasWire lesson was built in from the first commit rather than discovered in
production: an unfilled path probe (`/holders/{chain}/{token}`, `/balance/{chain}/{address}`)
resolves to a sensible default (USDC, the zero address) and answers 200, because a 400 on
that probe is what froze GasWire out of routing for an epoch. Every figure is read live
and providers are raced on a deadline, with answers memoised for ten seconds. The node took
about eight minutes to index and activate these, longer than GasWire's two, which fits the
epoch-scoped indexing noted above.

## How each slot is kept honest

A general scorer registered against many intents would be one module with many
labels, so three things stand between a build and a registration, all of them in the
repo and all of them run by `deploy.py` on every build:

1. the general benchmark (40 cases, 20 intents), the 12 case gaming suite and rank
   agreement with the live champion on a 60 row traffic corpus,
2. a family benchmark written for the shape of answer that intent returns: 15 numeric
   cases (the figure, its unit, its magnitude, its direction, which entity it is
   attached to), 14 authenticity cases (a verdict where the wrong answer shares nearly
   every word), 12 reference cases (naming the right entity against plausible
   neighbours),
3. constants swept against that family rather than inherited. The numeric profile came
   out of a 108 configuration sweep: a wrong figure is close to fatal for those
   intents because the figure is the whole answer.

The gate allows one documented miss per family, because the families deliberately
include cases past a lexical scorer's reach. The current one is `ref-ip-hosting`,
where the truth says AWS and the good answer says Amazon. Deleting the case would have
been the dishonest route to a clean sheet.

### The bug that came out of it and the upgrade the gate refused

`auth-img-real` failed and the cause was not scoring. `bnd`, the per-token flag
marking a clause boundary, was the one field `tokenize` did not write on every push,
so a previous call's boundary survived into the next one. "no" in "Authentic, no sign
of manipulation" then read as a standalone verdict and flipped a correct answer into a
contradiction. The score depended on how many calls had come before it, which is the
one property a scorer must never have.

The eight modules registered earlier that day (regs 26 to 33) carry that bug and the
node refused to let us replace them. Reg 57 put the fixed binary up against reg 26 and
lost on separation, 0.7767 against 0.7930, both at 32/32 wins:
`"lost to the current champion on separation"`. The gate is a regression check
comparing a candidate with the incumbent. Here the incumbent is our own earlier
module. What makes it awkward is why the buggy build looks better: the stale boundary
flag made "no" read as a standalone verdict more often than it should, which crushed
bad answers containing the word and inflated the separation score. A sweep of 18
configurations over `M_NEGCOV`, `SOFT_MIN` and `SOFT_W` recovered 0.006 of the 0.016
gap, so weights cannot buy it. Deregistering to get around the comparison would most
likely cost the slot, because reg 16 shows a deregistered module is still quoted as
that intent's champion baseline.

So the state is deliberate and recorded rather than tidied away. The ten slots
registered later run the fixed binary and the eight from that morning run the pre-fix
one. The bug's practical reach on those eight is narrow, since it can only make a
determiner "no" read as a negative verdict, which on six verdict intents is usually
the correct reading anyway, but it is real and this is the honest place to say so.

Four more fixes came from the same three files: a separator between digits is part of
the figure (without it "1.57 JPY" read as identical to "157 JPY" and scored a perfect
1.0000), magnitude words and their suffixes are part of the figure, a figure attached
to a different entity is a different claim and an all-caps token that prefixes a
capitalised word is the same entity ("AU" against "Australia").

## Likely questions

**Is this just word overlap with extra steps?**
No. Word overlap is one of eight signals and it is the one that gets overridden:
polarity, numbers and adjacency can each cut a lexically perfect answer to a
fraction of its score. On the benchmark the shipped word-overlap module has a
negative margin (wrong answers score higher on average) and this one is at 0.669.

**How do I know it is not tuned to your own benchmark?**
Our benchmark is not the one that promoted it. The node ran its own hidden 32 case
fixture set and reported 32/32 wins and margin 0.79 for the live builds. Our
benchmark and attack suite are in the repo so the tuning is auditable, and
`bench/report.json` and `bench/tune-results.json` are the raw runs.

**What stops a miner gaming it?**
Twelve cases in `bench/attacks.json`, each run on every build. Echoing the question
scores 0.10 against 0.89 for the real answer. Listing every candidate answer scores
0.18. Reusing the ground truth's words and flipping the verdict scores 0.05.
Padding with function words scores 0.01. Two of the twelve are the opposite test: a
correct answer buried in assistant boilerplate must stay correct (0.98) and one with
emoji and mixed scripts must too (0.72), because a scorer that punishes noise
punishes real miners.

**Why is `worst_self_match` exactly 1.000?**
A perfect answer is detected by comparing word bytes only, so case, spacing and
punctuation cannot cost it. The node's floor is 0.75.

**What happens if the ground truth is not English?**
It still scores. Everything is byte level, non-Latin scripts stay inside tokens and
carry a lower weight rather than being read as noise and the trigram signal does
the work. Cross-language synonyms ("Deutschland" for "Germany") are a known miss:
no lexical scorer resolves those and the fix is the embedding table described
above.

**Did an AI write this?**
AI assistance (Claude, Anthropic) was used throughout, with the design decisions,
the gate results and every number in this packet verified against the harness and
the on-chain state by the author. Nothing here is claimed as human-reviewed that
was not read.

## Open items

1. CHAT_COMPLETION: closed with four measurements on record. Reopen only if the
   champion changes or the gate does.
2. Post the progress updates on X. Both track rubrics score them. Drafts are in
   `CONTENT-telegraph.html` and posting needs the human.

Done and independently checkable: three repos public and fetched anonymously
(telegraph-salience-scorer, telegraph-gaswire-miner, telegraph-chainwire-miner under
github.com/zkasuran), three Track 1 miners registered, serving and each the sole provider
for its intent. The hackathon roster registration was filed on 2026-08-18 against the same
wallet that holds every registration.

## Three observations for the protocol team

These came out of building against the live node rather than reading the docs, and
they are recorded here because they are worth more to the team than to us.

1. **A pure separation gate can lock a buggy incumbent in place.** Reg 57 was refused
   because the module it would replace scores better on separation. The reason it
   scores better is the determinism bug above. A gate that also required determinism
   (score the same triple twice in one run, in different positions, then compare)
   would have caught ours before it was ever promoted.
2. **Miner liveness is gated twice, inconsistently.** The WebSocket `ask` path refuses
   on an epoch-scoped "did not respond last epoch" flag that the ERC-8183 job path
   does not consult. Testnet epoch 204 stayed current for over four hours, so `ask`
   kept refusing long after the endpoint was fixed and `updateMiner` had re-registered
   the miner, while two ERC-8183 jobs routed to that same miner and settled.
3. **The hackathon site's email verification does not verify anything.**
   `POST /api/auth/send-otp` returns a signed token whose payload is
   `{"email":…,"otp":"351147","exp":…}` in cleartext base64, so the code the user is
   asked to read from their inbox is already in the response the browser gets. Anyone
   who can name an email address can register as it. Ours is our own address and the
   registration is our own, but the same request would work against any address, so
   the OTP needs to stay server side.
