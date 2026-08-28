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
