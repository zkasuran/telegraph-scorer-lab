# Reverse-engineering patchsignal (CVE_LOOKUP champion, author 0x236891fe)

Closed source; recovered from the registered binary (`patchsignal-v18c.wasm`, no debug names)
by reading its data-section vocabulary and black-box probing `rank_answer`.

## Feature model (from the string tables it keys on)

It is a domain CVE-fact scorer with these axes:
- **Exploitation status (CISA KEV):** "actively exploited / exploited in the wild / known
  exploited / confirmed exploitation / kev" vs "not known to be actively exploited / no known
  exploitation / not in cisa kev / not exploited". A polarity axis.
- **Severity:** critical / high / medium / moderate / low.
- **Vuln type:** remote/arbitrary code execution, sql/os/command injection, path traversal,
  SSRF, XSS, XXE, unsafe/insecure deserialization, buffer/heap overflow, auth bypass, info
  disclosure/leak.
- **Version ranges:** version(s), through, before, prior to, up to, fixed/patched in, affected
  from/between, `< > <= >=`, earliest affected version.
- **Negation/hedging:** not, is not, isn't, rather than, instead of, without; or, either,
  possibly, maybe, may be.

## Behavior (black-box, rank_answer)

Hard-gates to ~0 on ANY contradicted fact, then ranks survivors by coverage (steeply):
- exact -> 1.0; full correct paraphrase -> ~1.0; extra correct detail -> still 1.0.
- flip exploitation polarity -> 0.0. wrong severity -> 0.0. right severity but wrong CVSS
  number -> 0.0 (strict numeric gate). wrong version -> 0.0. wrong vuln type -> 0.0.
- partial coverage (about half the gt facts) -> ~0.0005; one fact missing of ~6 -> ~0.008.
- refusal / off-topic -> 0.0.

So its real-traffic ranking is dominated by "does the answer get every CVE fact right", then
coverage. Our generic lexical/numeric scorer ranks CVE traffic at agreement ~0.45 with it,
which is why an own-build that beats its separation (0.9998) still fails the 0.60 agreement
gate. See LEDGER 2026-08-27 (c)/(d).
