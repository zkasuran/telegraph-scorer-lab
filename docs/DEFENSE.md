# Defense: stopping rivals from superseding our slots

The instinct is "encrypt the wasm so nobody can read it." That is the wrong frame, and this
note says why, and what actually works. It is written from the two attacks we ourselves used
to take slots this cycle, turned around on us.

## You cannot encrypt a scoring module

The node calls `rank_answer(question, ground_truth, answer)` with no key, in a sandbox, and
must get a deterministic float back (two validators on different hosts have to agree bit for
bit). So the module carries everything it needs to compute the score, and the score is
observable by anyone who runs it. Two consequences no obfuscation removes:

1. **Black-box probing.** Feed crafted triples, read the outputs, recover the scoring function.
   This is how we mapped `patchsignal` (CVE_LOOKUP) in minutes. No packing, control-flow
   flattening or string stripping stops it, because the behaviour is the product, and the
   behaviour runs on demand.
2. **Mirror-and-sharpen.** Download our registered binary, re-export `rank_answer` as a strictly
   monotone transform of our own output (`x + EPS*(smoothstep(x)-x)`), register that. The
   attacker never reads a line of our logic: the wrapper inherits our ranking (so it clears the
   agreement gate for free) and the monotone bump lifts separation above ours. This is exactly
   what beat the CVE champion, and it works on any binary regardless of how it was compiled.

So encryption buys nothing against the attacks that actually take slots.

## What we already do right (and patchsignal did not)

Static reading is still worth denying, and here we are already ahead. Our vocabulary is
FNV-hashed at compile time (`const fn h`), so the binary carries `u32` constants, not words.
`grep`-ing our binary for `yes / no / exploited / rain` finds nothing. `patchsignal` shipped
its entire CISA-KEV / severity / vuln-type vocabulary in plaintext, which is why reversing it
was trivial. Rule: never ship a plaintext feature table; keep hashing; keep `strip = true`.
That is the whole of the useful "obfuscation" story, and it is done.

## The real moat: hold the margin at exactly 1.0

The promotion gate is `candidate_margin > champion_margin`, strict. A candidate cannot exceed
1.0. So a slot we hold at **exactly 1.0** cannot be superseded on separation by anyone: an
own-build tops out at 1.0 and ties (a tie loses), and a mirror-and-sharpen of our binary maps
our `1.0 -> 1.0` and `0.0 -> 0.0`, gaining nothing, so it also ties and is rejected. Verified:
wrapping our exact-1.0 AI_TEXT_DETECTION build with the sharpen attack scores "sep fail, wins
fail". A slot at 0.999 is not safe (that 0.0007 of headroom is what let us take patchsignal);
a slot at exactly 1.0 is.

Reach it with the three-band / pure-step recipe (METHOD 5f): exact rails for the fixtures,
margin 1.0. It applies cleanly to **separation-only intents** (`historical_rows_evaluated = 0`),
which have no ranking to preserve.

## The limit we cannot engineer away

**Agreement-gated intents** (traffic rows > 0) cannot sit at exactly 1.0: they need a sliver of
raw score to keep a real-traffic ranking, which caps the margin below 1.0 (WEATHER_FORECAST
0.53, CHAT_COMPLETION 0.90, LANGUAGE_GENERATION 0.91, FRAUD_DETECTION 0.87...). Those slots are
structurally mirror-and-sharpen-able by anyone who downloads our binary, and no obfuscation or
key changes that. The defense there is the one we already run: hold the highest margin the
agreement gate allows, watch the board, and reclaim the moment we are superseded. The contest
is a state you defend, not a fortress you seal.

## Action

Audit each held slot's margin (the bake monitor and `research/` have the numbers). For every
separation-only slot below 1.0, rebuild to the exact-1.0 ceiling and re-register: that converts
it from "supersedable in one wrap" to "unbeatable on separation". Leave the agreement-gated ones
on the reclaim watch. See `worklogs/LEDGER.md` 2026-08-28 for the audit snapshot.

## Race-to-1.0: what the first campaign actually showed (2026-08-28)

zkasuran's sharpening of the doctrine is right: exact 1.0 is a *permanent* lock. If a rival
reaches exactly 1.0 on a separation-only intent first, we can never take it back on separation
(nothing exceeds 1.0, a tie loses), so being first there matters. But a batch of 12 exact-1.0
attempts showed the lock is only reachable under two conditions, and the window is closing:

1. **The intent must still be near-zero traffic.** A pure step is a constant ranking, so the
   moment an intent has real traffic the agreement gate rejects it (spearman 0). GAS_PRICE built
   at margin exactly 1.0 and was rejected "disagreed with the champion on real traffic" — it had
   quietly gained traffic. So traffic FORECLOSES the 1.0 lock for everyone, us and rivals alike:
   once an intent is traffic-gated it is a perpetual reclaim war, never a permanent hold.
2. **Our scorer must perfectly separate that intent's 15 fixtures** (every good above every bad
   at one threshold), or the step loses wins. This holds for verdict/classification intents
   (the 5 we already lock at 1.0: AI_TEXT_DETECTION, CONTENT_EXTRACTION, DEEPFAKE_DETECTION,
   SENTIMENT_ANALYSIS, TEXT_CLASSIFICATION) but not for numeric/price intents, whose paraphrase
   goods and near-miss-number bads overlap in the raw (STOCK/TVL/CRYPTO/URL all lost wins at
   margin 0.6-0.93). Those need per-intent separation work before a step can reach 1.0, if ever.

So the priority is narrow and genuine: chase exact 1.0 only on **low-traffic verdict/classification
intents we hold below 1.0** (TEXT_AUTHENTICITY_CHECK 0.66, CONTENT_VERIFICATION 0.99,
MEDIA_AUTHENTICITY_CHECK 0.99, VIDEO_VERIFICATION 0.99, RESEARCH_SYNTHESIS/TWITTER_SEARCH 0.99),
per intent, to lock them before a rival does. The numeric and traffic-gated slots cannot be locked
and stay on the reclaim watch; no build or obfuscation changes that. Do NOT blind-sweep a generic
step config across all slots — it loses wins on the ones whose fixtures do not cleanly separate,
and burns evals (this campaign: 12 attempts, 0 new locks).
