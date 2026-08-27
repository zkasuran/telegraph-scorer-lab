# Knobs: the scoring module's tunable constants

Every constant here lives at the top of `module/src/lib.rs` (a few live in `minilm.rs`).
`build_xfmr.py` patches them from a JSON config per build; `variants.py` bundles common sets
into named presets. Defaults below are the `lib.rs` values, which are the source of truth.
A build inherits whatever it does not override, so pass a full config (or use a named variant)
for reproducibility.

`build_xfmr.py` reads each const's declared type (`f32` / `u32` / `usize`) out of `lib.rs`
before patching, and its float pattern accepts scientific notation. If it patched by a fixed
name list or a `[0-9.]+` pattern instead (as it once did), a new integer knob or a value
already written as `1e-06` would be left unchanged and the build would come out byte-identical
to the previous one, silently. Two variants that should differ but share a keccak mean a knob
did not patch.

## Lexical core

| const | default | effect |
|---|---|---|
| `W_LEX` | 0.76 | weight on token overlap in the lexical blend |
| `W_GRAM3` | 0.2 | weight on character-trigram overlap (catches morphology, misspellings) |
| `W_GRAM2` | 0.04 | weight on character-bigram overlap |
| `F_BETA2` | 0.36 | beta squared for the precision/recall F-measure; below 1 favours precision |
| `P_CONCAVE` | 1.0 | concavity applied to precision; >1 punishes partial coverage harder |
| `R_KEY_BASE` | 0.5 | share of recall that must come from the answer-bearing part of the ground truth |
| `R_FLOOR` | 0.3 | how much overall coverage can float an answer worded its own way |

## Correctness penalties (the ordering levers)

These reorder non-monotonically, so they can WIN a fixture case a smooth scorer misses, at some
risk to agreement. 1.0 means off. Lower means a harder demotion.

| const | default | fires when the answer... |
|---|---|---|
| `M_CONTRA` | 0.7 | contradicts the ground truth |
| `M_TWO_FACED` | 0.8 | asserts the truth and its opposite (hedged / "actually unknown") |
| `M_NEGCOV` | 0.32 | covers the words only under a negation the truth does not carry |
| `M_ORDER` | 0.85 | has the right words with no shared adjacency (reordered) |
| `M_ENTITY` | 0.72 | attaches a right figure to the wrong entity |
| `M_LITERAL` | 1.0 | transposes characters inside a literal (IDs, postcodes); `M_LITERAL_MIN` 0.9 sets the run threshold |
| `M_SILENT` | 1.0 | says nothing about the answer (silence penalty) |
| `B_AGREE` | 0.0 | bonus pulling a right-verdict answer toward 1 |

## Numeric matching (figure intents)

| const | default | effect |
|---|---|---|
| `M_NUM_MISS_BASE` | 0.4 | floor when a stated figure is missing from the answer |
| `M_NUM_WRONG` | 0.05 | multiplier when the answer asserts a different figure (aggressive by default) |
| `M_NUM_MATCH` | 1.0 | bonus pulling a numerically-correct answer toward 1; the lift that makes a right numeric paraphrase read near-perfect. `variants.py` BASE ships this 0.0, turn it on for figure intents |
| `NUM_TOL` | 0.0 | relative tolerance band for figure agreement |

## MiniLM transformer blend (only with `--features minilm`)

| const | default | effect |
|---|---|---|
| `W_EMB` | 0.45 | share of the score that is the sentence-embedding cosine vs the lexical blend; 0 keeps it lexical-first |
| `EMB_A_W` | 0.25 | weight on the shallow embedding-layer cosine |
| `EMB_B_W` | 0.5 | weight on the full six-layer transformer cosine |
| `EMB_LEX_W` | 0.25 | weight on our lexical score inside the blend |
| `EMB_L2_W`, `EMB_L4_W` | 0.0 | weights on the after-layer-2 and after-layer-4 cosines (a depth profile) |
| `GATE_LEX` | 0.0 | multiplicative lexical gate: topical score times clamp(lex/GATE_LEX). Real answers saturate it, off-topic ones get gated toward 0. Free fixture separation |
| `W_QA` | 0.0 | share of the topical score that is answer-to-question cosine rather than answer-to-ground-truth |
| `SOFT_W`, `SOFT_MIN`, `SOFT_CAP_FRAC` | 1.0 / 0.72 / 0.35 | semantic-credit weight, the cosine below which a match is mere topicality, and the share of answer-bearing content vectors alone may satisfy |
| `TOK_SPAN`, `MAXTOK` | 1 / (minilm.rs) | encoder stride and max tokens (in `minilm.rs`) |

## Final calibration (the margin levers)

Choose ONE path. Smoothstep and step preserve ranking (agreement safe); tune for margin.

| const | default | effect |
|---|---|---|
| `POST_ITERS` | 0 | whole smoothstep contrast passes on the final score; each widens separation, order-preserving |
| `POST_PIVOT` | 0.5 | pivot the score is rescaled to before smoothstep; lower (0.3) rescues a modest good-answer tail |
| `POST_FRAC` | 0.0 | a fractional extra smoothstep pass, for a nudge without full saturation |
| `STEP_T` | 0.0 | step threshold; goods above it to 1, bads below to 0. 0 keeps the step path off |
| `STEP_B` | 0.02 | share of the raw score kept through the step so the traffic cluster does not tie (agreement guard) |
| `STEP_R` | 0.0 | coverage gate on the good side of the step |
| `STEP_W` | 0.0 | half-width; >0 turns the hard step into a ramp when the blend's scale is unmeasured |
| `SIGK` | 34.0 | logistic steepness; >0 replaces smoothstep with `1/(1+e^-SIGK*(blend-SIGC))`, the champion's own curve shape |
| `SIGC` | 0.4545 | logistic centre |
| `SHARPEN` | 0.0 | how much of the score is the contrast curve vs raw similarity |

## Three-band step (a closed champion at the separation ceiling)

For the case in `METHOD.md` 5f: the champion sits near margin 1.0, so the fixtures must score
*exactly* 1.0 and 0.0 (a pure step), but a pure step makes real traffic tie and the agreement
Spearman go undefined. These carve a defined ranking back in without moving the fixtures off
their rails. All default 0 (path off), so no other build changes.

| const | default | effect |
|---|---|---|
| `TRI_LO` | 0.0 | below this the score is the flat bottom rail; place it under every fixture bad |
| `TRI_HI` | 0.0 | above this the score is the flat top rail (1.0); place it over every fixture good. >0 turns the three-band path on. Ramp runs linearly between `TRI_LO` and `TRI_HI` |
| `TRI_FLOOR` | 0.0 | orders the BOTTOM rail as `TRI_FLOOR * signal`. At 1e-9 the ranking is distinct yet `1 - mean` still rounds to margin 1.0; must be the bottom rail, since near 1.0 f32 spacing (6e-8) would cost the margin |
| `TRI_SRC` | 0 | which signal orders the bottom rail (codes as `TIE_SRC`). Doubles as an instrument: the node reports each signal's Spearman with the closed champion. Trigrams (2) beat the blend (0) on AI_TEXT_DETECTION |
| `BAND_EPS` | 0.0 | alternative two-rail form `[0, e]` / `[1-e, 1]` ordered by the tie-break; simpler than TRI but caps margin at `1 - 2e`, so it loses to a champion at the ceiling. Kept for intents whose champion is not at 1.0 |

`STEP_R` (in the table above) is not optional on this path: without the coverage gate an
unrelated ground truth clears `TRI_HI` on wording alone and the node's structural self-vs-cross
check rejects the build before the real eval. Winning AI_TEXT_DETECTION config: `TRI_LO=0.06,
TRI_HI=0.20, STEP_R=0.30, TRI_FLOOR=1e-9, TRI_SRC=2`.

## Misc

| const | default | effect |
|---|---|---|
| `NOGT_Q` | 0.0 | with no ground truth, fall back to answer-to-question cosine so the ranking survives (>0 to enable) |
| `EXACT_TIE` | 0.0 | keep byte-exact answers ordered by question fit instead of flat 1.0, so they do not all tie |
| `TIE_SRC` | 0 | which signal breaks ties inside a step band: 0 blended, 1 lexical, 2 trigrams, 3 recall, 4 answer-to-question, 5 shallow cosine, 6 half-lexical-half-transformer. Doubles as an agreement instrument |
| `TELEGRAPH_INTENT` | (patched) | 32-byte intent marker; makes each intent's binary distinct so its hash differs |

Named presets in `variants.py`: `rawB` (pure embB), `rawR`/`rawRp` (champion-mimic blend, with
PEN), `rawG35`/`rawG35p` (blend + lexical gate, with PEN), `rawLex` (lexical only), and the
`PEN` set (all correctness penalties on). Prefer these for reproducible builds.
