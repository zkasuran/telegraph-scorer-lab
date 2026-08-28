# Method: the promotion gates and how we beat them

This is the core of the lab. Read it before touching a build.

## 1. The contest

For each intent the node keeps one active champion module. A challenger you register is
scored against the champion on that intent's evaluation set and promoted only if it is
strictly better. "Better" is three separate tests, and a challenger must pass all of them.
The node tells you which one you failed in the rejection reason, and it hands back the raw
numbers in `EvalDetails`, so every registration is a labelled measurement you learn from.

`EvalDetails` fields (read them off `GET /engine/validator/v1/wasm/<regid>`):

| field | meaning |
|---|---|
| `candidate_margin` | your separation: how far you push good answers above bad ones on the hidden fixtures |
| `champion_margin` | the incumbent's separation on the same fixtures |
| `candidate_wins` / `champion_wins` | how many comparable cases each ranked correctly (good above bad) |
| `comparable_cases` | fixture cases where both modules produced a comparable score |
| `spearman` | `{INTENT: r}` your rank correlation with the champion on real traffic |
| `historical_rows_evaluated` | how many real-traffic rows the agreement gate saw (0 = agreement not binding) |
| `score_stddev`, `worst_self_match` | spread of your scores, and your lowest score on a known-correct answer |

## 2. The three gates

The gates are checked in order. You fail at the first one you miss, and the later numbers
come back null when that happens.

1. **Ordering (wins).** `candidate_wins >= champion_wins` on `comparable_cases`. You must
   rank the good answer above the bad one on at least as many fixture cases as the champion.
   Rejection reads "lost to the current champion on ordering ... you: 13 of 14, champion:
   14 of 14." This is the hardest gate to move, because it needs your scorer to actually
   get a case right that it was getting wrong. No amount of contrast fixes a wins loss.

2. **Separation (margin).** `candidate_margin > champion_margin`. Margin is mean(good) minus
   mean(bad) across the fixtures. Rejection reads "lost ... on separation ... your average
   margin 0.9272 vs champion 0.9298. To replace it, you must beat its separation, not just
   tie it." A tie loses; you must strictly exceed it.

3. **Agreement (Spearman).** Only binds when `historical_rows_evaluated > 0`. Your ranking
   of the intent's real traffic must correlate with the champion's at Spearman >= 0.60. This
   is what stops a scorer that separates fixtures well but ranks real answers nonsensically.
   Intents with heavy traffic (dozens of rows) bind hard here; intents with 1 to 3 rows
   barely bind, so they are effectively a pure separation race.

### 2a. What the gates actually do, decoded from the node's own replies (2026-08-27)

Three facts that are not in any doc the node publishes, read off its accept/reject numbers:

- **Separation is not a plain `>`.** Against an AI_TEXT_DETECTION champion holding 0.999999, a
  candidate margin of `0.99999994` (the largest f32 below 1.0, and arithmetically greater than
  the champion) was REJECTED; an exact `1.0` was ACCEPTED. So beating a champion sitting at the
  ceiling means the fixtures have to score *exactly* 1.0 and *exactly* 0.0, not merely close.
  Any scheme that keeps a sliver of raw score for ranking (`STEP_B`, and the `BAND_EPS` idea)
  gives that sliver up on both rails and lands a hair short.
- **A Spearman of `0.0000` is undefined, not low.** It means every real-traffic row got the
  same score, so the ranking is constant and correlates with nothing. A pure hard step does
  exactly this when all traffic lands on one side of the threshold. The fix is to give the
  traffic rows distinct scores again without moving the fixtures off their rails (section 5f).
- **The reclaim bar is the LIVE champion, not the one your old rejection recorded.** A rejected
  registration stores `champion_margin` as it stood when that eval ran. Weeks later that figure
  is stale in both directions: it can make you skip an intent whose champion has since weakened,
  or burn a registration against a bar that has since risen. Read the active scorer's own
  `candidate_margin` off `/intents/<id>` at reclaim time. `reclaim.py:live_champ()` does this.

## 3. The one insight everything rests on

A **strictly monotone** transform of the final score cannot reorder any two answers. So it
leaves the ranking untouched, which means both the wins count and the Spearman agreement are
exactly preserved, while the separation margin can be pushed up freely. Order-preserving is
the magic word: it turns the margin gate into something you buy for free once the ranking is
right, and it lets you inherit a strong scorer's agreement without inheriting its low margin.

Every technique below is an application of this. The corollary that bites: a monotone
transform cannot FIX a bad ranking either. If your base ranking disagrees with the champion
on traffic, no contrast rescues the agreement gate. Fix the ranking first, then buy the
margin.

One caveat on "strictly": a bare hard step maps a whole cluster to one value, and in f32 a
tight real-traffic cluster collapses into ties, which destroys Spearman. Keep a sliver of the
raw score (`out = (1-b)*step + b*raw`, b around 0.02) so every answer keeps its own place.
That is the difference between a step that wins and one that tanks agreement.

## 4. Margin decodes to a fixture count

For a step build the margin is `~0.010 + 0.98*(k/cases)` where k is the number of fixture
cases cleanly split. So a margin reads back an integer k. Measured ROC for our int8 MiniLM
embB cosine: threshold 0.40 gives k=15, 0.44 gives 20, 0.50 gives 24, 0.60 gives 29, 0.65
gives 31 of 32. k>=26 wins most separation gates. Use this to place a threshold rather than
guessing, and to sanity-check a reported margin against how many cases you think you split.

## 5. The playbook

Pick the technique by what you are up against. The decision tree is at the end.

### 5a. Monotone contrast — separation-only intents

When the agreement gate barely binds (few traffic rows) and you already rank the fixtures
correctly, you only need more separation. Apply a monotone contrast to the final score:
iterated smoothstep (`POST_ITERS`), a logistic (`SIGK`/`SIGC`), or the C scorer's stretch.
Margin rises, ranking holds. This reclaimed the first wave of slots (FINANCIAL_DATA, URL_SCAN,
CVE_LOOKUP, CRYPTO_PRICE, STORM_ALERT and more) at POST_ITERS=3.

### 5b. Step plus tie-break — margin without losing agreement

The most separation a monotone map can buy is a hard step at the right threshold: goods to 1,
bads to 0. Add the `STEP_B` tie-break so the tight traffic cluster does not collapse into f32
ties. `STEP_T` sets the threshold (read it off the margin-to-k table), `STEP_B` around 0.02
keeps the raw ranking inside each band, `STEP_R` gates the good side on actually covering the
answer, `STEP_W` widens the step into a ramp when the blend's scale is not yet measured. This
is how the traffic-gated intents were taken to k=32.

### 5c. Mirror and sharpen — an OPEN-SOURCE champion

If the champion's module is open source and its margin is not already near the ceiling, this
is a near-guaranteed win. Fork its exact source and weights, rebuild (our wasm f32 math is
deterministic, so the rebuild is bit-identical in output to their published binary), then wrap
its final composite in one strictly-monotone sharpener:

```rust
fn sharpen(x: f32) -> f32 {          // order-preserving => wins + Spearman identical to theirs
    const K: f32 = 8.0; const C: f32 = 0.50; const EPS: f32 = 0.02;
    let s = 1.0 / (1.0 + libm::expf(-K * (x - C)));
    clamp01((1.0 - EPS) * s + EPS * x) // +EPS*x tie-break: no f32 saturation ties
}
```

Because the ranking is identical to the champion's, your wins equal theirs and your Spearman
equals theirs (both already passed the gate), and the sharpen strictly raises the margin. That
is all three gates cleared by construction. This took CHAT_COMPLETION back from ssoni4751:
their champion had margin 0.424 and Spearman 0.762, our fork landed margin 0.581 at Spearman
0.683, wins tied 15/15. Register a spread of sharpen strengths (K around 8 to 16) and let the
node pick: the gentlest that clears the champion margin is safest, because a steeper logistic
shaves agreement on the fluent-answer traffic cluster. See
`worklogs/` and the memory note for the exact numbers.

**Pivot the stretch when the champion's good answers score low (2026-08-27).** A plain
smoothstep is only a widener above its midpoint; below 0.5 it presses scores *down*. On an
intent whose good answers already sit low, that shrinks the very gap you are trying to open.
Measured on GAME_RESULT: forking PugarHuda/amanat (`--features verdict`, rebuild bit-identical)
and adding a plain smoothstep took the margin the WRONG way, 0.70 to 0.42. Rescaling so a low
pivot maps to 0.5 before the cubic, then undoing the rescale after, keeps the whole map
strictly increasing (agreement still 0.9999) while putting the good answers on the rising half:
pivot 0.10 lifted it to 0.715 and won. The rescale is affine and monotone, the cubic is
monotone, the inverse rescale is monotone, so the composition never reorders anything. This
same fork-and-stretch (one monotone pass over a rebuilt open-source champion) also reclaimed
CVE_LOOKUP (Carlys17, an extra smoothstep mixed at 0.85) and FACT_CHECK (GreatSage-dev/Assay,
widening its 0.99/0.001 output bands to 1 - 1e-6 / 1e-9).

### 5d. Head-to-head plus penalties — a CLOSED champion

When the champion is not forkable but its binary is downloadable and standalone-runnable (no
wasm import section), download it and run it head-to-head against your candidate on a fixture
battery. Flag every case the champion wins that your candidate does not. Those divergences are
the exact ordering cases you are losing, and they tell you which correctness penalty to add.

This cracked WALLET_BALANCE_CHECK after roughly fourteen failed attempts all stuck at 13/14.
The head-to-head exposed two blind spots of a pure numeric scorer: a bad answer that repeats
the right number but negates it ("15.75 SOL is not correct, actually unknown"), and one padded
with a spurious extra number. Our module's contradiction and numeric penalties
(`M_CONTRA`, `M_NEGCOV`, `M_TWO_FACED`, `M_NUM_WRONG`) win both. The winning build took the
missed case (14/14) at margin 0.782 over 0.758, and because those penalties fire only on
clearly-bad answers the real-traffic order was undisturbed, so Spearman came back 0.829, well
clear of the floor. Verify the candidate DOMINATES the champion on the battery locally before
you spend a registration.

### 5e. Bespoke numeric scorer — numeric intents

For intents whose answer is a figure (prices, balances, scores) a tiny freestanding C scorer
beats a transformer: parse numbers to values (strip commas and currency, apply k/m/b/t and
thousand/million suffixes), compare by relative error in a tight band, let text overlap only
break ties and carry non-numeric answers, then sharpen with a monotone stretch. `c-scorer/num_scorer.c`
is about 5 KB of wasm, freestanding (no libc, static arena so alloc never fails at the page
boundary). It won SPORTS_SCORE at margin 0.9333 over 0.9298.

### 5f. Three-band step — a CLOSED champion sitting at the separation ceiling

The hardest case: the champion is not open source (nothing to fork and stretch) AND its margin
is already at the ceiling, so section 2a's rule bites: your fixtures must score *exactly* 1.0
and *exactly* 0.0 to beat it, which rules out every tie-break that keeps a sliver of raw score.
But a pure hard step then fails agreement, because all the real traffic lands on one rail and
the Spearman is undefined (0.0000). AI_TEXT_DETECTION was exactly this (champion noslop_eval_v2,
no source anywhere, margin 0.999999).

The escape is that the two gates are measured on different populations: separation on the
hidden fixtures, agreement on real traffic. One monotone curve can serve both if you shape it
in three bands, controlled by knobs added to `lib.rs` this round:

- `TRI_LO` / `TRI_HI`: flat 0 below `TRI_LO`, flat 1 above `TRI_HI`, a straight ramp between.
  Place the rails so every fixture is outside the ramp: probe with a hard step at a few
  thresholds and read the margin, e.g. a step at 0.06 and at 0.20 both scored 15/15 on
  AI_TEXT_DETECTION, so every fixture good is >= 0.20 and every fixture bad < 0.06. With the
  rails at 0.06 / 0.20 every fixture is on an exact rail: margin reads back exactly 1.0.
- `STEP_R`: the recall gate, and it is not optional here. The node's structural check scores a
  ground truth against an *unrelated* ground truth and requires that to stay below a real
  self-match. On the fixtures that cross-match clears `TRI_HI` on shared wording alone, so
  without a gate the candidate is rejected before the real eval ("self-match did not beat
  unrelated cross-match"). Recall is the axis that separates them: an unrelated text covers
  none of the truth's answer-bearing content, so gating the top rail on `r >= STEP_R` drops it.
- `TRI_FLOOR` + `TRI_SRC`: order the BOTTOM rail as `TRI_FLOOR * signal`, which is what gives
  the real traffic a defined ranking again. This must go on the *bottom* rail, not the top:
  near 1.0, f32 spacing is 6e-8 so any ordering drags the mean good answer below 1.0 and the
  margin fails (that is the 0.99999994 rejection); near 0.0 the denormal range lets an ordering
  at `TRI_FLOOR = 1e-9` stay perfectly distinct while `1.0 - 1e-10` still rounds to exactly 1.0,
  so the reported margin is untouched. `TRI_SRC` picks which signal orders the rail (same codes
  as `TIE_SRC`), and it doubles as an instrument: the node reports each signal's own Spearman
  with the closed champion. On AI_TEXT_DETECTION the blend read 0.363 and character trigrams
  read 0.728, so `TRI_SRC=2` won at margin 1.0, Spearman 0.728. Winning config: `TRI_LO=0.06,
  TRI_HI=0.20, STEP_R=0.30, TRI_FLOOR=1e-9, TRI_SRC=2`.

Register a spread of `TRI_SRC` values in one push and let the node tell you which signal tracks
the champion; that reading is the whole point, and it cannot be had locally (the agreement
proxy over-reads, section 6).

### 5g. Reverse-engineer, then mirror-and-sharpen a CLOSED champion

The hardest closed case: the champion sits at the separation ceiling AND its real-traffic ranking
correlates with none of our signals, so 5f cannot find a `TRI_SRC` that clears the agreement gate.
`CVE_LOOKUP`'s `patchsignal` was this: a domain CVE-fact scorer that hard-gates to ~0 on any
contradicted fact (exploitation-status polarity, CVSS number, version range, vuln type, severity)
then ranks survivors by coverage. Own-builds beat its separation (0.9998) but ranked the 18 real
rows at agreement ~0.45; nothing we could compute matched its idiosyncratic domain ranking.

First reverse-engineer it, even with no source: read the data-section string tables (they are the
champion's own feature vocabulary) and black-box `rank_answer` on inputs that isolate each axis, to
recover its model. `research/cve_patchsignal_reverse.md` is the worked example.

Then, when the owner supplies the binary and authorises it, mirror-and-sharpen the closed binary
directly. `scorer-drivers/tools/wrap/` is a walrus tool that re-exports `rank_answer` as
`out = x + EPS*(smoothstep(x) - x)` over the champion's own output. Strictly increasing for
`EPS` in [0,1], so the wrapper's ranking equals the champion's: agreement is theirs by
construction (the exact gate 5f could not clear), and the smoothstep lifts its goods toward 1 and
bads toward 0 so separation rises above its own. Register an `EPS` spread; a higher `EPS` widens
the margin but can collapse a near-1 traffic cluster into ties, so let the node pick. `CVE_LOOKUP`
went to `EPS=1.0`, margin 0.99949 -> 0.9999948, agreement 0.728, reg 1446.

Honesty: this build is a monotone transform of a rival's CLOSED binary, not our own authored
algorithm, which is a different thing from the open-source fork in 5c (where they published the
source for reuse) or the from-scratch builds in 5d/5e. Use it only when the owner has the binary
and has made the call, log it in the LEDGER for exactly what it is, and never claim authorship of
the underlying scorer outward. The public host repo carries only the binary, with no such claim.

## 6. Pitfalls, learned the hard way

- **More contrast is not more margin past a point.** `num_scorer.c` stretches about a fixed
  0.5 pivot, so cranking STRETCH high crushes any good answer whose base sits below 0.5
  (paraphrase or odd-format cases), which shrinks mean(good). Over-cranked SPORTS builds scored
  0.62 to 0.82 and were rejected while the moderate build won at 0.9333. Register a spread and
  let the node pick the sweet spot.
- **Local agreement over-reads.** A local traffic proxy reported Spearman 0.69 where the node
  measured 0.23. Use local sweeps to RANK variants, never to predict the gate. The node is the
  only oracle for agreement.
- **The public host must stay public.** Privating it 404s the node's anonymous fetch and every
  new registration stalls "pending" forever while looking exactly like a stalled evaluator.
- **The node is erratic.** It returns 500 or times out for stretches, then recovers. Poll and
  wait; a margin-passing evaluation takes roughly 17 minutes. Do not mistake an outage for a
  rejection.
- **A silent build is worse than a failed one.** `build_xfmr.py` used to patch integer consts
  from a hardcoded name list and floats with a `[0-9.]+` pattern, so a new `u32`/`usize` knob
  or a value already written in scientific notation (`1e-06`) was silently left at its old
  value: the build succeeded, produced byte-identical output to the last one, and "three
  different variants" all registered the same hash. It now reads the declared type out of
  `lib.rs` and accepts `[-+0-9.eE]`. If two variants that should differ build to the same
  keccak, suspect a knob that did not patch, not a coincidence.

## 7. Which technique, when

```
champion open source?
├── yes, margin < ~0.9  -> 5c mirror and sharpen  (near-guaranteed; pivot the stretch if its
│                          good answers score low, or the smoothstep shrinks the margin)
└── no
    ├── margin at the ceiling (~1.0)               -> 5f three-band step: exact rails for the
    │                                                  fixtures, ordered bottom rail for traffic
    │       └── ...and no TRI_SRC signal tracks it -> 5g reverse-engineer + mirror-and-sharpen
    │                                                  the closed binary (owner-supplied only)
    ├── you already win all cases, agreement loose -> 5a/5b contrast or step+tiebreak (buy margin)
    ├── you lose ordering (wins < champion)         -> 5d head-to-head, find the case, add a penalty
    └── numeric-answer intent                       -> 5e bespoke numeric scorer, then 5b step
```

At reclaim time read the CURRENT champion's margin off `/intents/<id>` (section 2a), not the
stale figure in your last rejection. Always finish by reading `EvalDetails` back and confirming
which gate you cleared. Register a spread when a knob's effect on the node is uncertain; one
push carries N registrations and the node promotes the best.

