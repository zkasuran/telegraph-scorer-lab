#!/usr/bin/env python3
"""Call every declared endpoint with the inputs a node probe actually sends, plus the
inputs that have broken us before, and report anything that is not a 200 with a summary.

A non-200 on a declared route costs the whole scoring epoch whatever the answer would
have been, so the bar is not "handles the happy path". It is "answers 200 with a summary
that says what could not be read", for a missing parameter, a nonsense parameter, an
unsupported subject, a value that is the right shape but does not exist, and the whole
question passed verbatim in every parameter name the descriptor documents.
"""
import json
import os
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = "telegraph-miner-selftest/1.0 (+https://github.com/zkasuran)"

# (base, path, label, params). One row per way a probe can arrive.
ROUTES = {
    "https://telegraph-sky.margyn.workers.dev": [
        ("/weather", "bare", {}),
        ("/weather", "location", {"location": "Tokyo"}),
        ("/weather", "query-full", {"query": "What is the current temperature and 'feels like' "
                                             "temperature in Tokyo, Japan, and will there be any "
                                             "precipitation in the next 24 hours?"}),
        ("/weather", "nonsense-place", {"location": "Zzzqqx Nowhereville"}),
        ("/weather", "empty", {"location": ""}),
        ("/weather", "coords", {"location": "35.6895,139.6917"}),
        ("/weather", "unicode", {"location": "München"}),
        ("/weather", "huge", {"query": "x" * 1500}),
        ("/forecast", "bare", {}),
        ("/forecast", "location-days", {"location": "London", "days": "3"}),
        ("/forecast", "days-absurd", {"location": "London", "days": "99"}),
        ("/forecast", "days-text", {"location": "London", "days": "three"}),
        ("/forecast", "query-full", {"query": "What is the weather forecast for Paris over the "
                                              "next 3 days including rain?"}),
        ("/forecast", "nonsense-place", {"location": "Zzzqqx Nowhereville"}),
        ("/storm", "bare", {}),
        ("/storm", "location-hours", {"location": "Chicago", "hours": "48"}),
        ("/storm", "hours-absurd", {"location": "Chicago", "hours": "100000"}),
        ("/storm", "query-full", {"query": "Will there be disruptive wind gusts exceeding 40 mph "
                                           "in Chicago, Illinois over the next 48 hours, and "
                                           "should I delay my outdoor construction project "
                                           "scheduled for Thursday?"}),
        ("/storm", "nonsense-place", {"location": "Zzzqqx Nowhereville"}),
    ],
    "https://telegraph-fin.margyn.workers.dev": [
        ("/price", "bare", {}),
        ("/price", "symbol", {"symbol": "BTC"}),
        ("/price", "unknown-symbol", {"symbol": "ZZQQXX"}),
        ("/price", "question", {"question": "What is the current price of Bitcoin (BTC) in USD?"}),
        ("/price", "empty", {"symbol": ""}),
        ("/fx", "bare", {}),
        ("/fx", "pair", {"from": "USD", "to": "EUR"}),
        ("/fx", "unknown-pair", {"from": "ZZZ", "to": "QQQ"}),
        ("/fx", "amount-text", {"from": "USD", "to": "EUR", "amount": "lots"}),
        ("/fx", "question", {"question": "What is the exchange rate from USD to JPY today?"}),
        ("/financial", "bare", {}),
        ("/financial", "query", {"query": "ethereum"}),
        ("/financial", "leaked-probe-1", {"question": "What was the average daily trading volume "
                                                     "for Solana (SOL) across all major exchanges "
                                                     "during Q3 2026, and how does this compare to "
                                                     "Bitcoin's average daily volume for the same "
                                                     "period?"}),
        ("/financial", "leaked-probe-2", {"question": "What was the trading volume and price change "
                                                     "percentage for Bitcoin (BTC) and Ethereum "
                                                     "(ETH) on August 15, 2026, and what were the "
                                                     "best bid and ask prices for BTC/USDT on "
                                                     "Binance at that time?"}),
        ("/financial", "unknown", {"query": "zzqqxx corp"}),
        ("/stock", "bare", {}),
        ("/stock", "symbol", {"symbol": "AAPL"}),
        ("/stock", "unknown-symbol", {"symbol": "ZZQQXX"}),
        ("/stock", "question", {"question": "What is the current stock price of MSFT?"}),
        ("/tvl", "bare", {}),
        ("/tvl", "protocol", {"protocol": "aave"}),
        ("/tvl", "unknown-protocol", {"protocol": "zzqqxx-finance"}),
        ("/tvl", "chain", {"chain": "ethereum"}),
        ("/tvl", "question", {"question": "What is the total value locked in Uniswap?"}),
    ],
    "https://telegraph-chain.margyn.workers.dev": [
        ("/balance", "bare", {}),
        ("/balance", "chain-only", {"chain": "base"}),
        ("/balance", "address", {"chain": "ethereum",
                                 "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}),
        ("/balance", "bad-address", {"chain": "ethereum", "address": "0xnothex"}),
        ("/balance", "ens", {"address": "vitalik.eth"}),
        ("/balance", "unknown-chain", {"chain": "zzqqxx",
                                       "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}),
        ("/balance", "query-full", {"query": "What is the current native-coin balance of address "
                                             "0x742d35Cc6634C0532925a3b844Bc454e4438f44e on "
                                             "Ethereum?"}),
        ("/tx", "bare", {}),
        ("/tx", "hash", {"chain": "ethereum",
                         "hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"}),
        ("/tx", "bad-hash", {"hash": "0xdeadbeef"}),
        ("/tx", "unknown-hash", {"chain": "ethereum", "hash": "0x" + "ab" * 32}),
        ("/tx", "query-full", {"query": "Look up Ethereum transaction 0x5c504ed432cb51138bcf09aa5e"
                                        "8a410dd4a1e204ef84bfed1be16dfba1b22060"}),
        ("/holders", "bare", {}),
        ("/holders", "token", {"chain": "ethereum", "token": "USDT"}),
        ("/holders", "address-token", {"chain": "ethereum",
                                       "token": "0x6b175474e89094c44da98b954eedeac495271d0f"}),
        ("/holders", "optimism", {"chain": "optimism",
                                  "token": "0x4200000000000000000000000000000000000042"}),
        ("/holders", "unknown-token", {"chain": "ethereum", "token": "0x" + "11" * 20}),
        ("/holders", "unknown-symbol", {"chain": "ethereum", "token": "ZZQQXX"}),
        ("/holders", "query-full", {"query": "How many holders does USDC on Base have?"}),
    ],
    "https://telegraph-gas.margyn.workers.dev": [
        ("/gas", "bare", {}),
        ("/gas", "network", {"network": "ethereum"}),
        ("/gas", "sepolia", {"network": "sepolia"}),
        ("/gas", "unknown-network", {"network": "zzqqxx"}),
        ("/gas", "query-full", {"query": "What is the current average transaction fee level on the "
                                         "blockchain network as of August 28, 2026?"}),
    ],
    "https://telegraph-net.margyn.workers.dev": [
        ("/ip-geolocate", "bare", {}),
        ("/ip-geolocate", "public", {"ip": "8.8.8.8"}),
        ("/ip-geolocate", "probe-ip", {"ip": "142.251.42.174"}),
        ("/ip-geolocate", "private", {"ip": "192.168.1.100"}),
        ("/ip-geolocate", "bad-ip", {"ip": "999.999.999.999"}),
        ("/ip-geolocate", "ipv6", {"ip": "2001:4860:4860::8888"}),
        ("/ip-geolocate", "query-full", {"query": "Where is the IP address 1.1.1.1 located?"}),
        ("/ssl-check", "bare", {}),
        ("/ssl-check", "domain", {"domain": "example.com"}),
        ("/ssl-check", "no-such-host", {"domain": "zzqqxx-nope-nope.invalid"}),
        ("/ssl-check", "plain-http", {"domain": "neverssl.com"}),
        ("/ssl-check", "url", {"url": "https://example.com/a/b?c=d"}),
        ("/ssl-check", "port", {"domain": "example.com:443"}),
        ("/ssl-check", "query-full", {"query": "Is the TLS certificate for github.com valid?"}),
        ("/url-scan", "bare", {}),
        ("/url-scan", "url", {"url": "https://example.com"}),
        ("/url-scan", "no-such-host", {"url": "https://zzqqxx-nope-nope.invalid/x"}),
        ("/url-scan", "no-scheme", {"url": "example.com"}),
        ("/url-scan", "query-full", {"query": "Is https://github.com safe to visit?"}),
        ("/extract", "bare", {}),
        ("/extract", "url", {"url": "https://example.com"}),
        ("/extract", "no-such-host", {"url": "https://zzqqxx-nope-nope.invalid/x"}),
        ("/extract", "pdf", {"url": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"}),
        ("/extract", "query-full", {"query": "Extract the main text from https://example.com"}),
    ],
    "https://telegraph-news.margyn.workers.dev": [
        ("/headlines", "bare", {}),
        ("/headlines", "topic", {"topic": "technology"}),
        ("/headlines", "unknown-topic", {"topic": "zzqqxx quantum llamas"}),
        ("/headlines", "question", {"question": "What are the top technology news headlines today?"}),
        ("/news", "bare", {}),
        ("/news", "q", {"q": "artificial intelligence regulation"}),
        ("/news", "unknown-q", {"q": "zzqqxx quantum llamas"}),
        ("/news", "leaked-probe", {"question": "Return the top 5 technology news headlines from the "
                                               "UK published in the last 7 days, excluding any "
                                               "articles from the domain 'theguardian.com'."}),
    ],
    "https://telegraph-scholar.margyn.workers.dev": [
        ("/papers", "bare", {}),
        ("/papers", "topic", {"topic": "climate change adaptation"}),
        ("/papers", "unknown-topic", {"topic": "zzqqxx quantum llamas"}),
        ("/papers", "question", {"question": "Find recent peer-reviewed papers on CRISPR."}),
        ("/research", "bare", {}),
        ("/research", "question", {"question": "What does research say about sleep and memory?"}),
        ("/research", "leaked-probe-1", {"question": "For patients with early-stage melanoma, does "
                                                    "the use of sentinel lymph node biopsy compared "
                                                    "to observation affect five-year survival rates "
                                                    "in studies published between 2015 and 2026?"}),
        ("/research", "leaked-probe-2", {"question": "Find me 5 open-access papers published in 2023 "
                                                    "about 'quantitative easing monetary policy' and "
                                                    "return their titles, authors, and publication "
                                                    "venues in a JSON format."}),
        ("/research", "unknown", {"question": "zzqqxx quantum llamas"}),
        ("/synthesis", "bare", {}),
        ("/synthesis", "topic", {"topic": "intermittent fasting"}),
        ("/synthesis", "unknown-topic", {"topic": "zzqqxx quantum llamas"}),
        ("/synthesis", "question", {"question": "Synthesise what studies say about microplastics."}),
    ],
    "https://telegraph-sec.margyn.workers.dev": [
        ("/cve", "bare", {}),
        ("/cve", "id", {"id": "CVE-2021-44228"}),
        ("/cve", "unknown-cve", {"id": "CVE-1999-99999"}),
        ("/cve", "malformed", {"id": "not-a-cve"}),
        ("/cve", "question", {"question": "What is CVE-2014-0160 and how severe is it?"}),
    ],
    "https://telegraph-lang.margyn.workers.dev": [
        ("/translate", "bare", {}),
        ("/translate", "text-to", {"text": "Good morning, how are you?", "to": "es"}),
        ("/translate", "unsupported-pair", {"text": "Good morning", "to": "zu"}),
        ("/translate", "unknown-lang", {"text": "Good morning", "to": "zzqqxx"}),
        ("/translate", "question", {"question": "Translate 'thank you very much' into French."}),
        ("/translate", "empty", {"text": "", "to": "fr"}),
    ],
    "https://telegraph-sport.margyn.workers.dev": [
        ("/score", "bare", {}),
        ("/score", "team", {"team": "Bayern"}),
        ("/score", "unknown-team", {"team": "Zzqqxx United"}),
        ("/score", "us-league", {"team": "Lakers", "league": "nba"}),
        ("/score", "question", {"question": "What was the score of the latest Manchester United "
                                            "match?"}),
        ("/game", "bare", {}),
        ("/game", "team", {"team": "Dortmund"}),
        ("/game", "leaked-probe", {"question": "Who won the 2026 FIFA World Cup and what was the "
                                               "score of the final match?"}),
        ("/game", "unknown-team", {"team": "Zzqqxx United"}),
    ],
}


def call(base, path, label, params):
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    url = base + path + ("?" + q if q else "")
    r = subprocess.run(["curl", "-s", "-o", "-", "-w", "\n%{http_code}", "--max-time", "50",
                        "-A", UA, url], capture_output=True, text=True)
    out = r.stdout.rsplit("\n", 1)
    body, code = (out[0], out[1]) if len(out) == 2 else ("", "000")
    try:
        j = json.loads(body)
        summary = j.get("summary")
    except Exception:
        j, summary = None, None
    return {"base": base, "path": path, "label": label, "url": url, "code": code,
            "summary": summary, "body": body[:300], "json": j is not None}


def main():
    only = sys.argv[1:]
    jobs = [(b, p, l, pr) for b, rows in ROUTES.items() for p, l, pr in rows
            if not only or any(o in b or o == p for o in only)]
    with ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(lambda a: call(*a), jobs))
    bad = []
    for r in res:
        ok = r["code"] == "200" and r["json"] and isinstance(r["summary"], str) and r["summary"].strip()
        tag = "ok  " if ok else "FAIL"
        if not ok:
            bad.append(r)
        host = r["base"].split("//")[1].split(".")[0]
        print(f"{tag} {r['code']} {host:18} {r['path']:14} {r['label']:18} "
              f"{(r['summary'] or r['body'])[:88]}")
    print(f"\n{len(res) - len(bad)} of {len(res)} answered 200 with a summary")
    for r in bad:
        print(f"  BAD {r['code']} {r['url']}\n      {r['body'][:200]}")
    json.dump(res, open(os.path.join(ROOT, ".rank", "probeall.json"), "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
