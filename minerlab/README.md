# The miner lab: measuring an answer before it ships

The scorer side of this lane wins a slot by out-separating a champion binary. The miner side is a
different game with a different measurement, and this directory is that measurement.

The node grades a miner by pulling `signal_mapping.label_field` out of its JSON response and scoring
that text with the intent's currently active scoring module against a ground truth the node writes
itself. The ground truth is never published. Everything here exists to reconstruct that grading
offline, so a wording change is measured before it is deployed rather than after an epoch has passed.

## The tools

| Tool | What it does |
| --- | --- |
| `rank.py sync` | resolves the ACTIVE module for each of our intents from `/engine/validator/v1`, downloads it byte for byte and checks the hash, then pulls the full probe log |
| `rank.py board` | the live rank per intent, ours against the leader |
| `rank.py rank <INTENT> <file>` | scores candidate answers under that intent's own module |
| `rank.py check <INTENT>` | scores our live answer exactly as it stands |
| `rank.py why <INTENT>` | the probe log, including the `failure_reason` the `/api/miners` payload hides |
| `validate_all.py` | calls every declared endpoint the way the node will, through the console sandbox, and reports the status it got |
| `probe_pairs.py` | calls our miner and the intent leader on the same question, to build the ground-truth proxy |
| `gen_licence_docs.py` | regenerates every lane's NOTICE and DATA-SOURCES.md from the per-source licence record |
| `rereg.py` | re-registers each descriptor on-chain, one at a time, resumable |

`gt/<INTENT>.json` holds the ground-truth proxy per intent, with its provenance in the `source`
field. Scoring needs `/tmp/dump`, the wazero `rank_answer` loader built from
`work/telegraph/scorer/harness/cmd/dump`.

## Why the leader's answer is a usable ground truth

On 17 of 25 intents the rank-1 miner's own live answer self-scores >= 0.98 under the live module.
A module that scores an answer 0.98 against itself is telling us that answer IS the node's truth to
within its own tolerance, so the pair (leader answer, our answer) reproduces the grading we are
losing. Where no leader answer is parseable, the proxy is written in the frame the node's own leaked
probe questions use, and `gt/<INTENT>.json` says so in `source` rather than implying a measurement
that did not happen.

## The measurement discipline

Three habits, each learned by getting it wrong first.

**Test against several ground-truth phrasings, never one.** The node writes its truth fresh each
epoch, so an answer tuned to one phrasing is tuned to a coin flip. Report the worst case and the
mean, and prefer the shape with the better worst case.

**Hold everything else fixed.** An early sweep concluded that a coarse figure beat a precise one,
when the real cause was that my candidate's figure happened to equal the ground truth's exactly.
Vary the format with the value fixed, then vary the value with the format fixed.

**A measured gain that costs honesty is not a gain.** Naming a city we cannot verify scored better
on one ground-truth shape than omitting it. It still came out, because only one of two disagreeing
databases can be right and the answer would be asserting the coin flip. The same rule killed a
"0 gwei" rendering, a guessed translation for an unsupported pair, and a host-level malware verdict
that would have accused GitHub of distributing malware.

## What it found

`worklogs/LEDGER.md` 2026-08-30 carries the full record. The short version: four answer levers
(cover every asked aspect, state a figure at several grains, never state many distinct figures,
answer the asked question), one descriptor trap (a declared `{template}` path is never matched by the
node's validator, 13.6% of probes rejected against 0.04%), and one hard rule (any non-200 on a
declared route costs the whole epoch, whatever the answer would have been).
