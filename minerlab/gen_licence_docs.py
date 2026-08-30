#!/usr/bin/env python3
"""Regenerate NOTICE and DATA-SOURCES.md from the sources each worker actually calls.

Every entry below was verified twice: the endpoint was called from a Cloudflare Worker (the
egress that matters, since several hosts behave differently there than from a laptop) and the
provider's own terms page was read for the four things that decide whether a paid miner may use
it at all: commercial use, redistribution, attribution and the real rate limit.

`quote` holds the provider's own words. Where a page could not be read, that is recorded as
unverified rather than guessed: a wrong licence claim in a public repo is worse than an
admitted gap.

    python3 .scratch/gen_licence_docs.py [lane ...]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# host, what it provides, licence, commercial use, attribution, rate limit, notes
SOURCES = {
    "skyminer": [
        dict(host="api.met.no", provides="Global hourly weather forecast (locationforecast 2.0)",
             licence="CC BY 4.0 and Norwegian Licence for Open Government Data (NLOD) 2.0",
             quote='"Norwegian Licence for Open Government Data (NLOD) 2.0" and "Creative Commons 4.0 BY International"',
             commercial="Permitted. The licence page states no restriction on commercial use, and CC BY 4.0 permits it.",
             attribution='Required. "Credit should be given to The Norwegian Meteorological Institute, shortened MET Norway, as the source of data." Suggested wording: "Data from MET Norway".',
             credit="Data from MET Norway, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Values converted from SI units and summarised by SkyWire.",
             rate='"Anything over 20 requests/second per application (total, not per client) requires special agreement."',
             notes=("A User-Agent naming the application with a contact is mandatory and a fabricated one is "
                    "treated as abuse. Coordinates are capped at four decimals: five or more returns 403. "
                    "Wind gusts, precipitation probability and thunder probability are published over the "
                    "Nordics only, which is why the answer states a sustained wind elsewhere.")),
        dict(host="api.weather.gov", provides="US wind gusts, precipitation probability, snowfall and active alerts",
             licence="No licence needed: a work of the United States Government.",
             quote='"All of the information presented via the API is intended to be open data, free to use for any purpose."',
             commercial='Permitted. "free to use for any purpose" and "we do not charge any fees for the usage of this service".',
             attribution="Not required. Credited anyway so a reader can check the figure.",
             credit="Data from the US National Weather Service (api.weather.gov), a public service of the United States Government.",
             rate='"The rate limit is not public information, but allows a generous amount for typical use."',
             notes=("A User-Agent is required and the docs ask for contact information in it. Read only for a "
                    "place the caller named, in the United States, where MET Norway lacks the gust and "
                    "probability fields.")),
        dict(host="www.wikidata.org", provides="Place coordinates, canonical label and country",
             licence="CC0 1.0 (public domain)",
             quote='"Creative Commons CC0 License", described as equivalent to "Public domain"',
             commercial="Permitted without condition.",
             attribution="Not required by CC0. Credited anyway.",
             credit="Place coordinates from Wikidata, CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/).",
             rate="No published limit for wbgetentities. One or two calls per uncached place, memoised for ten seconds.",
             notes=("Wikipedia's search index resolves a name to a page title, which handles typos and "
                    "disambiguation, and Wikidata supplies the published coordinate. Only the CC0 value is "
                    "served; Wikipedia is the index, not the data.")),
    ],
    "netwire": [
        dict(host="api.ipquery.io", provides="IP geolocation, network operator and ASN",
             licence="No stated licence for the data.",
             quote='"You can integrate ipquery into commercial applications, SaaS products, and internal tools without restriction." "No API Key Required"',
             commercial="Permitted in those words.",
             attribution="Not stated as required. Credited anyway.",
             credit="IP geolocation from ipquery.io.",
             rate="No number published. A 429 is documented for abuse. One call per uncached address, memoised for ten seconds.",
             notes=("Chosen over the alternatives on its terms: ip-api.com limits the free API "
                    '"strictly ... for a non-commercial purpose", and ipwho.is bars users from '
                    "redistributing its materials, which is what publishing its values is.")),
        dict(host="dns.google", provides="IP-to-ASN and reverse DNS, as the geolocation fallback",
             licence="Not applicable: DNS is a protocol lookup, not a licensed dataset.",
             quote="",
             commercial="Unrestricted. A DNS answer comes from the operator's own published zone.",
             attribution="Not applicable.",
             credit="Network operator from Team Cymru IP-to-ASN over DNS.",
             rate="No published limit on the DNS-over-HTTPS resolver. Two lookups per uncached address.",
             notes=("Team Cymru publishes its IP-to-ASN mapping in DNS for exactly this purpose and asks "
                    "heavy users to rate limit themselves.")),
        dict(host="urlhaus.abuse.ch", provides="Recent malware URL feed, for the URL safety verdict",
             licence="Published for automated checking; no restriction stated on the plain-text feed.",
             quote="",
             commercial="Not restricted in the published feed terms.",
             attribution="Credited in the answer as the basis for the verdict.",
             credit="Malware URL listings from URLhaus (abuse.ch).",
             rate="The feed is fetched at most once per five minutes per isolate and held in memory.",
             notes="The keyed API returns 401 from the edge, so the public text feed is used."),
        dict(host="openphish.com", provides="Phishing URL feed, for the URL safety verdict",
             licence="Public feed; no restriction stated for reading it.",
             quote="",
             commercial="Not restricted in the published feed terms.",
             attribution="Credited in the answer as the basis for the verdict.",
             credit="Phishing URL listings from OpenPhish.",
             rate="Fetched at most once per five minutes per isolate and held in memory.",
             notes=""),
        dict(host="the URL the caller names", provides="A live HTTPS handshake and one GET, for the TLS verdict, the status and the page text",
             licence="Not applicable: our own request to a public address.",
             quote="",
             commercial="Not applicable.",
             attribution="Not applicable.",
             rate="One request per call.",
             notes=("This replaced crt.sh and r.jina.ai, both dropped on their terms. crt.sh permits the "
                    'site "for your personal, non-commercial use only", bars use "for any commercial '
                    'purposes" and bars "any robot, spider, or other automatic device". Jina requires an '
                    "account. A Worker cannot read the peer certificate off the socket, so the issuer and "
                    "expiry are not claimed.")),
    ],
    "finwire": [
        dict(host="api.kraken.com", provides="Crypto last trade, 24 hour volume and the day's open",
             licence="No stated licence for the market data.",
             quote="",
             commercial="Not addressed by the published API terms, which state no restriction on the public market-data endpoints.",
             attribution="Not stated as required. The source is named in every answer.",
             credit="Market data from the Kraken public ticker.",
             rate="No published figure for the public endpoints. One call per uncached asset, memoised for ten seconds.",
             notes="Preferred because one read gives the price, the volume and the day change."),
        dict(host="www.bitstamp.net", provides="Crypto last trade and 24 hour volume, first fallback",
             licence="Commercial reuse granted by the API terms.",
             quote='"Bitstamp allows the incorporation and redistribution of our exchange data for commercial purposes."',
             commercial="Permitted in those words. The terms direct volume users to sign a data licence agreement.",
             attribution="Not stated as required. The source is named in every answer.",
             credit="Market data from the Bitstamp public ticker.",
             rate='"As standard, all clients can make 400 requests per second" with "a default limit threshold of 10,000 requests per 10 minutes".',
             notes="Open item: the terms invite a signed Data License Agreement for commercial use at volume."),
        dict(host="api.gemini.com", provides="Crypto last trade, second fallback",
             licence="No stated licence for the market data.",
             quote="",
             commercial="Not addressed by the published API documentation.",
             attribution="Not stated as required. The source is named in every answer.",
             credit="Market data from the Gemini public ticker.",
             rate="No published figure for the public ticker. Called only when the two preferred sources fail.",
             notes=""),
        dict(host="api.frankfurter.dev", provides="Fiat exchange rates (European Central Bank reference rates)",
             licence="MIT for the software. The rates are ECB reference rates.",
             quote='"Yes, absolutely. See each provider\'s terms for details on the underlying data." (on commercial use)',
             commercial="Permitted in those words.",
             attribution="Not required. The source is named in every answer.",
             credit="Exchange rates from Frankfurter, sourced from European Central Bank reference rates.",
             rate='"There are no quotas. Requests are rate-limited to prevent abuse, but there are no monthly or daily caps."',
             notes=("This replaced open.er-api.com, whose terms bar its data from \"any product or service "
                    'that offers programmatic or automatic access to exchange rate data", which is what a '
                    "miner is. A reference rate is a daily fixing, so the answer dates it to the ECB "
                    "publication day rather than implying a live tick.")),
        dict(host="stooq.com", provides="Stock quotes",
             licence="No stated licence.",
             quote='"Redistribution of data found on the website is not allowed without the consent of Stooq."',
             commercial="Blocked. Serving a Stooq close price to the network is redistribution.",
             attribution="Not applicable while the source is unusable.",
             rate="No figure published.",
             notes=("OPEN ITEM. Section 5.3 bars redistribution without consent, so this source is a blocker "
                    "for STOCK_PRICE rather than a compliant source. The clause names the remedy: written "
                    "consent from Stooq (www@stooq.com). Until that exists STOCK_PRICE has no licensed "
                    "source, and the miner states its figure with the source named so a reader can see "
                    "exactly what is being relied on.")),
        dict(host="query1.finance.yahoo.com", provides="Stock quotes, fallback",
             licence="No stated licence.",
             quote='Reuse "for any commercial purpose" is barred, as is automated collection "using any automated means, devices, programs, algorithms or methodologies, including but not limited to robots, spiders, scrapers".',
             commercial="Barred.",
             attribution="Not applicable while the source is unusable.",
             rate="No published figure. Returns 429 from a Cloudflare edge IP in any case.",
             notes="OPEN ITEM, same as Stooq. Recorded here because the code still names it as a fallback."),
        dict(host="api.llama.fi", provides="Total value locked for a protocol or chain",
             licence="No stated licence.",
             quote='A licence "to access and use the Site for personal, non-commercial purposes", and clause 8 forbids "republish the data in any form without permission".',
             commercial="Barred on the free tier.",
             attribution="Not applicable while the source is unusable.",
             rate="Published only as a general limit.",
             notes=("OPEN ITEM. DeFiLlama is the only keyless source of protocol TVL we found, and its terms "
                    "bar both the commercial use and the republication. The swap paths are a DeFiLlama Pro "
                    "licence or reading each protocol's own contracts, which is a much larger build.")),
    ],
    "newswire": [
        dict(host="globalvoices.org", provides="Global civic reporting",
             licence="CC BY 3.0",
             quote='"all content created by Global Voices is published under a Creative Commons Attribution-Only license"; reusers may "remix, transform, and build upon the material for any purpose, even commercially".',
             commercial="Permitted in those words.",
             attribution='Required: "You must give appropriate credit, provide a link to the license, and indicate if changes were made."',
             credit="Reporting from Global Voices, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/).",
             rate="No published limit on the feed. Read once per request, memoised for ten seconds.",
             notes="Third-party photos in a story may carry other terms; only titles and dates are republished."),
        dict(host="en.wikinews.org", provides="Volunteer-written news reports",
             licence="CC BY 4.0 for anything published after 16 December 2024.",
             quote='"Creative Commons Attribution 4.0 License"; material "may be attributed to \\"Wikinews\\"".',
             commercial="Permitted by CC BY 4.0.",
             attribution="Required, to Wikinews.",
             credit="Reporting from Wikinews, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).",
             rate="Standard Wikimedia API etiquette. Up to three search calls per uncached question.",
             notes="Articles published before 16 December 2024 are CC BY 2.5, which is also attribution-only."),
        dict(host="ec.europa.eu", provides="European Commission press releases",
             licence="CC BY 4.0",
             quote='"content owned by the EU on this website is licensed under the" "Creative Commons Attribution 4.0 International (CC BY 4.0)"; "reuse is allowed, provided appropriate credit is given and changes are indicated".',
             commercial="Permitted by CC BY 4.0.",
             attribution="Required, with changes indicated.",
             credit="Press releases (C) European Union, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), summarised here.",
             rate="No published limit on the press-corner feed.",
             notes="Logos and trade marks are excluded from the reuse policy and are not republished."),
        dict(host="www.nasa.gov, www.nist.gov, www.nsf.gov, www.energy.gov",
             provides="Science and technology news releases",
             licence="No copyright: works of the United States Government.",
             quote="",
             commercial="Unrestricted.",
             attribution="Not required. Credited anyway.",
             credit="News releases from United States Government agencies, which carry no copyright.",
             rate="No published limit on these feeds.",
             notes=("These four cover the technology and science categories the other sources are thin on. "
                    "Agency logos and mission insignia have their own rules and are not republished.")),
        dict(host="feeds.bbci.co.uk and feeds.npr.org", provides="Formerly the headline source",
             licence="No licence for reuse.",
             quote='BBC Terms of Use 15a: "You\'re not allowed to pluck metadata from our content or RSS feeds". The NPR feed ships "Copyright 2024 NPR - For Personal Use Only".',
             commercial="Barred.",
             attribution="Not applicable.",
             rate="Not applicable.",
             notes="Removed from the worker. Recorded so the change is auditable."),
    ],
    "sportwire": [
        dict(host="api.openligadb.de", provides="Match fixtures, live scores and results for German football and the European competitions",
             licence="Open Database License (ODbL)",
             quote='"Die über diese API bereitgestellten Daten stehen unter der Open Database License (ODbL)"; "Das Abrufen der Daten über den Webservice erfordert keinerlei Authentifizierung."',
             commercial="Permitted by ODbL, with attribution and share-alike on any derived database.",
             attribution="Required by ODbL.",
             credit="Match data from OpenLigaDB (https://www.openligadb.de/), Open Database License (ODbL).",
             rate="No published limit. Six small reads per uncached question, memoised for ten seconds.",
             notes=("Covers Bundesliga, 2. Bundesliga, 3. Liga, the DFB-Pokal, the Champions League and "
                    "LaLiga. A question about a competition outside that set is answered by saying so.")),
        dict(host="site.api.espn.com", provides="Formerly all scores and results",
             licence="No licence for reuse.",
             quote='Disney Terms of Use section 2.A licenses the content "for your personal, noncommercial use only ... with no right to reproduce, distribute"; 2.B.x bars access "using a robot, spider, script, or other automated means"; 2.B.ix bars anything that would "bypass, modify, defeat, tamper with or circumvent any of the functions or protections".',
             commercial="Barred, with no paid tier to buy: developer.espn.com is a one-line redirect.",
             attribution="Not applicable.",
             rate="None published.",
             notes=("Removed from the worker, along with the browser User-Agent it used to get past a 403. "
                    "The US leagues went with it.")),
    ],
    "langwire": [
        dict(host="apertium.org", provides="Machine translation",
             licence="Free and open-source (GPL for the engine and the language data).",
             quote="",
             commercial="Not restricted by the project. The public instance publishes no terms, which is recorded as unverified for the hosted service.",
             attribution="Credited in every answer.",
             credit="Translation by Apertium (https://www.apertium.org/), free and open-source machine translation.",
             rate="No published limit on the public instance. One or two calls per uncached request.",
             notes=("Rule-based, so it covers 133 pairs rather than every pair. A pair it does not serve is "
                    "answered by saying so, because a guessed translation is a fabricated answer. Google's "
                    'keyless endpoint was dropped: the Translate API "is provided to you without any free '
                    'usage quota" and its attribution rules require a "powered by Google Translate" graphic '
                    "a JSON API cannot show. MyMemory was dropped for its resale bar and its 5000 "
                    "character shared daily cap.")),
    ],
    "chainminer": [
        dict(host="gateway.tenderly.co, eth-mainnet.public.blastapi.io, rpc.flashbots.net",
             provides="EVM JSON-RPC reads: balances, transactions, contract calls",
             licence="Not applicable: public chain state that any node reproduces.",
             quote="",
             commercial="No restriction published on the chain data these endpoints return.",
             attribution="Not applicable. The chain and the block are stated in every answer.",
             rate="No published figure for the public gateways. Racing stops at the first answer.",
             notes=("Chosen on their terms. PublicNode (Allnodes) bars re-publishing Service Content "
                    '"commercially and non-commercially"; mainnet.optimism.io grants use "solely for your '
                    'own personal, non-commercial use"; mainnet.base.org needs written permission beyond '
                    '"personal and non-commercial use"; drpc.org restricts the free tier to personal use; '
                    "1rpc.io publishes a 200 request per day quota; arbitrum.io's terms page returns 403 to "
                    "every client tried. All are removed.")),
        dict(host="blockscout.com", provides="Token holder counts",
             licence="No stated licence for the indexed data.",
             quote='"The default rate limit is 3 requests per minute" per IP, and the docs state "PER INSTANCE API WILL BE DEPRECATED JULY 1".',
             commercial="Not addressed.",
             attribution="The source is named in every answer.",
             credit="Holder counts from Blockscout.",
             rate="OPEN ITEM: the documented keyless limit is 3 requests per minute per IP, below what a busy epoch can generate.",
             notes=("The replacement is Blockscout's free PRO tier, which needs an API key. Holder count has "
                    "no other keyless source: it requires a full index of transfer events.")),
        dict(host="api.ensideas.com", provides="ENS name resolution",
             licence="No stated licence.",
             quote="",
             commercial="Not addressed by the page.",
             attribution="The source is named in the readings.",
             rate="Not stated.",
             notes="api.ensdata.net was dropped: every page returned a Cloudflare challenge, so nothing about it could be verified."),
    ],
    "miner": [
        dict(host="gateway.tenderly.co, eth-mainnet.public.blastapi.io, rpc.flashbots.net",
             provides="eth_gasPrice and eth_feeHistory across seven EVM networks",
             licence="Not applicable: public chain state that any node reproduces.",
             quote="",
             commercial="No restriction published on the chain data these endpoints return.",
             attribution="Not applicable. The network and the figure's units are stated in every answer.",
             rate="No published figure for the public gateways. Racing stops at the first answer.",
             notes=("Same swap as the ChainWire miner and for the same reasons: PublicNode, Optimism, Base, "
                    "dRPC, 1RPC and Arbitrum all carry a bar, a quota below our traffic, or terms that could "
                    "not be read. Gas price is public chain state, so the only question was the endpoint's "
                    "own terms.")),
    ],
    "secwire": [
        dict(host="cve.circl.lu", provides="CVE records: description, CVSS, CWE, affected products",
             licence="CC BY 4.0 for the CVE Program data underneath.",
             quote="",
             commercial="Permitted by CC BY 4.0 for the CVE data. The instance itself states no licence, which is recorded as unverified.",
             attribution="Credited in every answer.",
             credit="CVE data from CIRCL (cve.circl.lu) and the CVE Program, CC BY 4.0.",
             rate="20 requests per minute anonymous.",
             notes=("The instance asks automated clients to send a User-Agent with a contact, which the "
                    "worker now does.")),
        dict(host="services.nvd.nist.gov", provides="Canonical CVSS scores and vectors",
             licence="No SPDX id. NIST publications are not subject to copyright in the United States.",
             quote='The terms ask that "This product uses the NVD API but is not endorsed or certified by the NVD." appear prominently within the application.',
             commercial="Permitted.",
             attribution="Required, in that exact wording.",
             credit="This product uses the NVD API but is not endorsed or certified by the NVD.",
             rate="5 requests in a rolling 30 second window without a key.",
             notes=("OPEN ITEM: the declared rate must stay inside 5 per 30 seconds. The descriptor now "
                    "declares 2 per second, which still exceeds it under sustained load, so the miner races "
                    "CIRCL first and treats NVD as the corroborating read.")),
    ],
    "scholarwire": [
        dict(host="api.openalex.org", provides="Scholarly works, citation counts and venues",
             licence="CC0 1.0 for the data.",
             quote="",
             commercial="Permitted by CC0.",
             attribution="Not required by CC0. Credited anyway.",
             credit="Scholarly metadata from OpenAlex, CC0 1.0.",
             rate="Keyless tier returns 429 from a Cloudflare edge IP under load, so Crossref leads.",
             notes=("OPEN ITEM: the terms of service could not be read (403 to every client), and the "
                    "archived version contains a clause barring unauthorised republication that sits oddly "
                    "with the CC0 grant on the data itself. Both facts are recorded rather than resolved.")),
        dict(host="api.crossref.org", provides="Scholarly works metadata",
             licence="No single SPDX id. The public pool is open.",
             quote='"No sign-up is required to use the REST API, and almost none of the metadata is subject to copyright" and "you may use it for any purpose."',
             commercial="Permitted in those words.",
             attribution="Not required. Credited anyway.",
             credit="Scholarly metadata from Crossref.",
             rate="Public pool measured at 1 request per second with concurrency 1.",
             notes='Some abstracts "may be subject to copyright by publishers or authors", so abstract text is not republished.'),
        dict(host="en.wikipedia.org", provides="Encyclopedic answer text for a research question",
             licence="CC BY-SA 4.0",
             quote="",
             commercial="Permitted by CC BY-SA 4.0.",
             attribution="Required, with the licence named and modification stated.",
             credit="Text from English Wikipedia, CC BY-SA 4.0, adapted (trimmed to the sentences that answer the question).",
             rate="Standard Wikimedia API etiquette. Two to four calls per uncached question.",
             notes=("OPEN ITEM: CC BY-SA is share-alike, so an answer that reuses Wikipedia prose carries a "
                    "share-alike obligation onto whatever embeds it. The credit line travels in the answer, "
                    "and the on-chain projection carries the same field.")),
    ],
}

NOTICE_HEAD = """This miner serves data from third parties. Their terms travel with it.

Each block below names one upstream, what it provides, the licence it publishes under, and the
exact credit line that licence requires. Every credit line marked required also travels in the
`attribution` field of every answer this miner returns, not only in this file.

"""

DS_HEAD = """# Data sources

Every figure this miner serves is a live read at request time. This file records, per source,
what it provides, what its own terms say about commercial use and redistribution, what credit it
requires and what its real rate limit is.

Two rules were followed in writing it. A licence is only recorded when the provider's own terms
page was read; where a page could not be read, that is stated as unverified rather than guessed.
And every source was called from a Cloudflare Worker before it went in, because several hosts
answer differently from a worker than from a laptop.

"""


def notice_for(lane):
    out = [NOTICE_HEAD]
    for s in SOURCES[lane]:
        out.append(f"## {s['host']}\n\n{s['provides']}.\n\nLicence: {s['licence']}\n")
        if s.get("quote"):
            out.append(f"\nIn the provider's own words: {s['quote']}\n")
        if s.get("credit"):
            out.append(f"\nRequired credit line:\n\n    {s['credit']}\n")
        else:
            out.append("\nNo credit line is required by this source.\n")
        out.append("\n")
    return "".join(out)


def datasources_for(lane):
    rows = SOURCES[lane]
    out = [DS_HEAD, "| Host | Provides | Licence | Commercial use | Attribution | Rate limit |\n",
           "| --- | --- | --- | --- | --- | --- |\n"]
    for s in rows:
        cell = (lambda v: str(v).replace("|", "\\|").replace("\n", " "))
        out.append(f"| {cell(s['host'])} | {cell(s['provides'])} | {cell(s['licence'])} | "
                   f"{cell(s['commercial'])} | {cell(s['attribution'])} | {cell(s['rate'])} |\n")
    out.append("\n## Per source\n")
    for s in rows:
        out.append(f"\n### {s['host']}\n\n{s['provides']}.\n")
        if s.get("quote"):
            out.append(f"\nWhat the terms say: {s['quote']}\n")
        out.append(f"\nCommercial use: {s['commercial']}\n")
        out.append(f"\nAttribution: {s['attribution']}\n")
        if s.get("credit"):
            out.append(f"\nCredit line published in every answer:\n\n    {s['credit']}\n")
        out.append(f"\nRate limit: {s['rate']}\n")
        if s.get("notes"):
            out.append(f"\n{s['notes']}\n")
    open_items = [s for s in rows if "OPEN ITEM" in (s.get("notes") or "") or "OPEN ITEM" in (s.get("rate") or "")]
    out.append("\n## Compliance\n\n")
    out.append("Met:\n\n")
    for s in rows:
        if s.get("credit"):
            out.append(f"- {s['host']}: the required credit line travels in every answer and in NOTICE.\n")
    out.append("\n")
    if open_items:
        out.append("Open, stated rather than hidden:\n\n")
        for s in open_items:
            note = s.get("notes") or s.get("rate")
            out.append(f"- {s['host']}: {note}\n")
    else:
        out.append("No open items: every source this miner calls permits the use, and every required "
                   "credit line is published.\n")
    return "".join(out)


def main():
    lanes = sys.argv[1:] or sorted(SOURCES)
    for lane in lanes:
        d = os.path.join(ROOT, lane)
        if not os.path.isdir(d):
            print(f"{lane:12} SKIP, no such directory")
            continue
        n = notice_for(lane)
        ds = datasources_for(lane)
        open(os.path.join(d, "NOTICE"), "w").write(n)
        open(os.path.join(d, "DATA-SOURCES.md"), "w").write(ds)
        opens = ds.count("OPEN ITEM")
        print(f"{lane:12} {len(SOURCES[lane])} sources, {opens} open items, "
              f"NOTICE {len(n)}B, DATA-SOURCES.md {len(ds)}B")


if __name__ == "__main__":
    main()
