# Telegraph lane: what is left for a human

One decision, then publishing. Everything else in this lane is done and verifiable
without our help.

Update 2026-08-19: the X Article was posted, which was the one human step this round.
Nothing else here needs a human until Track 3 (Apps) opens after 2026-09-07. What is still
moving is machine-side: three LLM-intent lexical scorers are registered on-chain and waiting
on a stalled node indexer, see LEDGER open items. The sections below are kept as the record
of what was published.

## What to post, in plain terms

There is **one article** and there is a **fallback thread**. Post the article if you can.

1. **The article (recommended): `work/telegraph/CONTENT-xarticle-telegraph.html`.**
   This is the single, complete piece. It covers both tracks, the scorer and the five
   miners, the wins and the parts that broke, in one human voice. Open it, click
   **Copy for X (plain text)**, paste into X's Articles editor, follow the five-minute
   formatting map on the page (which 10 lines become headings, which numbers to bold),
   add the cover image, publish, then send the announce post it gives you.
2. **The fallback thread: `work/telegraph/CONTENT-telegraph.html`.** Only if you do not
   have X Premium (Articles need it). Post 1 stands alone, then the six part thread as
   replies, then post 4 (the miner) and post 5 (the miner getting paid). Every block
   copies on click with a live 280 count.

Either way tag `@Telegraphprotoc` (x.com/Telegraphprotoc), not a guessed handle. Both
track rubrics score progress updates on X and the engagement on them, so this is a scored
deliverable rather than promotion. Every number was measured on 2026-08-18; if a few days
pass, re-read `/engine/validator/v1/addresses/0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287`
and confirm the count is still 31.

`CONTENT-article-telegraph.html` (the older scorer-only long article) is **superseded** by
the one-article file above. Ignore it.

## The cover image

The article page carries the image prompt, a negative prompt and the text overlay. The
cover is **5:2**, which is what the Articles editor asks for in its upload slot
(generate 3000 x 1200, upload 1600 x 640). The model draws the field only. The two lines
of text go on afterwards in a vector tool, never in the prompt, because no image model
sets type cleanly. Publishing an Article needs X Premium; without it the fallback thread
carries the same story.

One timing call worth making deliberately: the article explains the design, the gates and
the four rejections in enough detail to help a rival, so publish now for the rubric credit
or hold it until round 1 closes on 2026-09-07.

## 3. Hackathon roster registration: done

Registered at hackathon.telegraphprotocol.com on 2026-08-18 with the email OTP,
`{"ok": true}` back from `/api/register`. This email had already registered for a
different project, so it was a correction rather than a first entry:

| Field | Was | Now |
| --- | --- | --- |
| Project name | Loadline | Telegraph salience scorer + GasWire miner |
| Wallet | `0xb58b6E9b725D7f865FeaC56641B1dFB57ECfB43f` | `0x8b224783FE5b3c52B7DB0cb9B1754f8812b75287` |
| Level | intermediate | advanced |
| Subnets | none | Financial Data, Social Sentiment, On-chain Analytics, AI / LLM Inference, News & Media, Custom / Other |
| Description, tech stack | empty | filled |

The wallet was the part that mattered. The old address holds none of this lane's
work: every registration, every promotion and both settlements sit on `0x8b2247…`,
so a prize keyed on the roster wallet would have missed the entry entirely. Name
(`Asuran`), email, X handle and Discord (`zkasuran`) are kept exactly as the earlier
registration had them.

Re-run or re-correct with `python3 roster-register.py <6-digit-otp>`. The previous
record is saved at `.scratch/roster-previous-record.json`.

## 4. Repos: done

Public since 2026-08-17, both checked anonymously, which is the check that counts:

- https://github.com/zkasuran/telegraph-salience-scorer (module, harness, benchmark, attack suite)
- https://github.com/zkasuran/telegraph-gaswire-miner (the GAS_PRICE miner)
- https://github.com/zkasuran/telegraph-chainwire-miner (the TOKEN_HOLDER_COUNT and WALLET_BALANCE_CHECK miners)
- https://github.com/zkasuran/telegraph-skywire-miner (the WEATHER_CHECK and WEATHER_FORECAST miners)

## Also live, nothing needed from you

**Track 2.** 32 of the 45 canonical intents run this module as their scoring module,
every author-written champion slot plus CHAT_COMPLETION (the flagship, won 2026-08-18 with a
MiniLM transformer ported into the no_std module), all `active`. First wave regs 26 to 33
and 47 to 56, second wave 13 more on 2026-08-18. Every one at 32/32 fixture wins,
`worst_self_match` 1.000 against a 0.75 floor and a separation margin between 0.68 and 0.81
against the incumbent default module's 0.3736.

**Track 1.** Five live miners, all `active`. Three are sole provider for their intent:
GAS_PRICE (reg 102, `telegraph-gas`), TOKEN_HOLDER_COUNT (reg 105) and WALLET_BALANCE_CHECK
(reg 106, the last two on the `telegraph-chain` worker). Two more compete head to head on
contested weather intents: WEATHER_CHECK and WEATHER_FORECAST (SkyWire, `telegraph-sky`),
their answer format tuned against the intent's downloadable scorer. All three workers run
on the Cloudflare account already in `.cloudflare.env`, so there is nothing to keep alive
by hand. GAS_PRICE has two settled ERC-8183 jobs, 50.818198860177751874 MACHINA received.

`SUBMIT-PACKET.md` is the defence document: what was built, every measured number,
the design rationale, the CHAT_COMPLETION rejections and the questions a judge is
most likely to ask.
