#!/usr/bin/env python3
"""Probe, per intent, our miner and the intent's leading rival on the same question.

The node grades a miner by pulling `signal_mapping.label_field` out of the miner's JSON
and scoring that text with the intent's live wasm against the node's own ground truth.
We cannot read the ground truth, but on several intents the leader scores ~1.0, which
means its answer IS the ground truth to within the scorer's tolerance. So the leader's
live answer is a usable ground-truth proxy, and the pair (leader answer, our answer)
scored under the live wasm reproduces the grading we are losing.

Writes .scratch/pairs/<INTENT>.json: {question, leader:{slug,label,text}, ours:{...}}
"""
import json
import os
import subprocess
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "pairs")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/151.0.0.0 Safari/537.36")

# One canonical question per intent, taken from the node's own probe text where a
# rejection leaked it (.scratch/leaked-questions.json) and otherwise written to match
# the intent description on /engine/v1/intents.
QUESTIONS = {
    "ACADEMIC_SEARCH": "Find recent peer-reviewed papers on climate change adaptation.",
    "CONTENT_EXTRACTION": "Extract the main text content from https://example.com",
    "CRYPTO_PRICE": "What is the current price of Bitcoin (BTC) in USD?",
    "CURRENCY_EXCHANGE": "What is the current exchange rate from USD to EUR?",
    "CVE_LOOKUP": "What is CVE-2021-44228 and how severe is it?",
    "FINANCIAL_DATA": "What is the market cap and 24 hour trading volume of Ethereum (ETH)?",
    "GAME_RESULT": "Who won the most recent Los Angeles Lakers game and what was the score?",
    "GAS_PRICE": "What is the current gas price on Ethereum?",
    "IP_GEOLOCATION": "Where is the IP address 8.8.8.8 located?",
    "LANGUAGE_TRANSLATION": "Translate 'Good morning, how are you?' into Spanish.",
    "NEWS_HEADLINES": "What are the top technology news headlines today?",
    "NEWS_SEARCH": "Find recent news articles about artificial intelligence regulation.",
    "ONCHAIN_TX_LOOKUP": ("Look up Ethereum transaction "
                          "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"),
    "RESEARCH_QUERY": "What does the research say about the effect of sleep on memory consolidation?",
    "RESEARCH_SYNTHESIS": "Synthesise what recent studies conclude about intermittent fasting.",
    "SPORTS_SCORE": "What was the score of the latest Manchester United match?",
    "SSL_VERIFICATION": "Is the TLS certificate for example.com valid?",
    "STOCK_PRICE": "What is the current stock price of AAPL?",
    "STORM_ALERT": "Will there be disruptive wind gusts in Chicago, Illinois over the next 48 hours?",
    "TOKEN_HOLDER_COUNT": "How many holders does USDT on Ethereum have?",
    "TVL_LOOKUP": "What is the total value locked in Aave?",
    "URL_SCAN": "Is https://example.com safe to visit?",
    "WALLET_BALANCE_CHECK": ("What is the current native-coin balance of address "
                             "0x742d35Cc6634C0532925a3b844Bc454e4438f44e on Ethereum?"),
    "WEATHER_CHECK": "What is the current temperature and feels-like temperature in Tokyo, Japan?",
    "WEATHER_FORECAST": "What is the weather forecast for London over the next 3 days?",
}

# How to call each miner: (path, {param: value}). Built from the miner's own declared
# endpoints and input_schema on /api/miners, so every call is one the miner documents.
OURS = {
    "ACADEMIC_SEARCH": ("https://telegraph-scholar.margyn.workers.dev/papers", {"topic": "climate change adaptation"}),
    "CONTENT_EXTRACTION": ("https://telegraph-net.margyn.workers.dev/extract", {"url": "https://example.com"}),
    "CRYPTO_PRICE": ("https://telegraph-fin.margyn.workers.dev/price", {"symbol": "BTC"}),
    "CURRENCY_EXCHANGE": ("https://telegraph-fin.margyn.workers.dev/fx", {"from": "USD", "to": "EUR"}),
    "CVE_LOOKUP": ("https://telegraph-sec.margyn.workers.dev/cve", {"cve_id": "CVE-2021-44228"}),
    "FINANCIAL_DATA": ("https://telegraph-fin.margyn.workers.dev/financial", {"query": "ethereum"}),
    "GAME_RESULT": ("https://telegraph-sport.margyn.workers.dev/game", {"team": "Lakers"}),
    "GAS_PRICE": ("https://telegraph-gas.margyn.workers.dev/gas", {"network": "ethereum"}),
    "IP_GEOLOCATION": ("https://telegraph-net.margyn.workers.dev/ip-geolocate", {"ip": "8.8.8.8"}),
    "LANGUAGE_TRANSLATION": ("https://telegraph-lang.margyn.workers.dev/translate",
                             {"text": "Good morning, how are you?", "to": "es"}),
    "NEWS_HEADLINES": ("https://telegraph-news.margyn.workers.dev/headlines", {"category": "technology"}),
    "NEWS_SEARCH": ("https://telegraph-news.margyn.workers.dev/news", {"q": "artificial intelligence regulation"}),
    "ONCHAIN_TX_LOOKUP": ("https://telegraph-chain.margyn.workers.dev/tx",
                          {"hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060"}),
    "RESEARCH_QUERY": ("https://telegraph-scholar.margyn.workers.dev/research",
                       {"question": "effect of sleep on memory consolidation"}),
    "RESEARCH_SYNTHESIS": ("https://telegraph-scholar.margyn.workers.dev/synthesis",
                           {"topic": "intermittent fasting"}),
    "SPORTS_SCORE": ("https://telegraph-sport.margyn.workers.dev/score", {"team": "Manchester United"}),
    "SSL_VERIFICATION": ("https://telegraph-net.margyn.workers.dev/ssl-check", {"domain": "example.com"}),
    "STOCK_PRICE": ("https://telegraph-fin.margyn.workers.dev/stock", {"symbol": "AAPL"}),
    "STORM_ALERT": ("https://telegraph-sky.margyn.workers.dev/storm", {"location": "Chicago", "hours": "48"}),
    "TOKEN_HOLDER_COUNT": ("https://telegraph-chain.margyn.workers.dev/holders",
                           {"chain": "ethereum", "token": "USDT"}),
    "TVL_LOOKUP": ("https://telegraph-fin.margyn.workers.dev/tvl", {"protocol": "aave"}),
    "URL_SCAN": ("https://telegraph-net.margyn.workers.dev/url-scan", {"url": "https://example.com"}),
    "WALLET_BALANCE_CHECK": ("https://telegraph-chain.margyn.workers.dev/balance",
                             {"chain": "ethereum", "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}),
    "WEATHER_CHECK": ("https://telegraph-sky.margyn.workers.dev/weather", {"location": "Tokyo"}),
    "WEATHER_FORECAST": ("https://telegraph-sky.margyn.workers.dev/forecast", {"location": "London", "days": "3"}),
}

LEADERS = {
    "CVE_LOOKUP": ("patchsignal-cve", "description",
                   "https://169.58.206.25.sslip.io/cve", {"cve_id": "CVE-2021-44228"}),
    "ONCHAIN_TX_LOOKUP": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/tx",
                          {"hash": "0x5c504ed432cb51138bcf09aa5e8a410dd4a1e204ef84bfed1be16dfba1b22060",
                           "chain": "ethereum"}),
    "URL_SCAN": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/urlscan",
                 {"url": "https://example.com"}),
    "WEATHER_CHECK": ("isobar-weather", "answer", "https://weather.isobars.xyz/weather", {"q": "Tokyo"}),
    "WEATHER_FORECAST": ("isobar-weather", "answer", "https://weather.isobars.xyz/forecast",
                         {"q": "London", "days": "3"}),
    "STOCK_PRICE": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/stock", {"symbol": "AAPL"}),
    "CRYPTO_PRICE": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/price", {"symbol": "BTC"}),
    "CURRENCY_EXCHANGE": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/fx",
                          {"base": "USD", "quote": "EUR"}),
    "TOKEN_HOLDER_COUNT": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/holders",
                           {"chain": "ethereum", "symbol": "USDT"}),
    "TVL_LOOKUP": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/tvl", {"protocol": "aave"}),
    "FINANCIAL_DATA": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/financial",
                       {"symbol": "ETH"}),
    "GAS_PRICE": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/gas", {"chain": "ethereum"}),
    "WALLET_BALANCE_CHECK": ("chainsight-oracle", "signal", "https://hub.shadrakbessanh.me/balance",
                             {"chain": "ethereum", "address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"}),
    "STORM_ALERT": ("livecert", "verdict", "https://miner-wine.vercel.app/storm-alert",
                    {"location": "Chicago", "hours": "48"}),
    "SSL_VERIFICATION": ("livecert", "verdict", "https://miner-wine.vercel.app/ssl-check",
                         {"domain": "example.com"}),
    "IP_GEOLOCATION": ("livecert", "verdict", "https://miner-wine.vercel.app/ip-geolocate", {"ip": "8.8.8.8"}),
    "ACADEMIC_SEARCH": ("livecert", "verdict", "https://miner-wine.vercel.app/papers",
                        {"topic": "climate change adaptation"}),
    "NEWS_SEARCH": ("gnews", "", "", {}),
    "GAME_RESULT": ("fourcast-sports-intelligence", "score", "https://miner.sportwarren.com/query",
                    {"team": "Lakers", "intent": "GAME_RESULT"}),
    "RESEARCH_QUERY": ("sarzops-transaction-risk", "signal",
                       "https://telegraph-intelligence-stack-production.up.railway.app/research/query",
                       {"query": "effect of sleep on memory consolidation"}),
    "CONTENT_EXTRACTION": ("microlink-url-extraction", "title", "https://api.microlink.io/",
                           {"url": "https://example.com"}),
}


def fetch(url, params):
    if not url:
        return None, "no url"
    q = "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())
    full = url + ("?" + q if q else "")
    r = subprocess.run(["curl", "-sL", "--max-time", "40", "-A", UA, full],
                       capture_output=True, text=True)
    body = r.stdout
    try:
        return json.loads(body), full
    except Exception:
        return None, full + " :: " + body[:200].replace("\n", " ")


def pick(obj, field):
    """Pull the label field out of a miner payload, following one level of nesting."""
    if obj is None:
        return None
    if isinstance(obj, list):
        for o in obj:
            v = pick(o, field)
            if v:
                return v
        return None
    if not isinstance(obj, dict):
        return None
    if field and isinstance(obj.get(field), str) and obj[field].strip():
        return obj[field]
    for k in ("summary", "answer", "signal", "verdict", "description", "text", "result", "message"):
        if isinstance(obj.get(k), str) and obj[k].strip():
            return obj[k]
    for v in obj.values():
        if isinstance(v, (dict, list)):
            got = pick(v, field)
            if got:
                return got
    return None


def one(intent):
    rec = {"intent": intent, "question": QUESTIONS.get(intent)}
    url, params = OURS.get(intent, ("", {}))
    body, full = fetch(url, params)
    rec["ours"] = {"url": full, "text": pick(body, "summary"),
                   "readings": (body or {}).get("readings") if isinstance(body, dict) else None,
                   "raw_keys": sorted(body)[:20] if isinstance(body, dict) else None}
    slug, field, lurl, lparams = LEADERS.get(intent, ("", "", "", {}))
    lbody, lfull = fetch(lurl, lparams)
    rec["leader"] = {"slug": slug, "field": field, "url": lfull, "text": pick(lbody, field)}
    return rec


def main():
    os.makedirs(OUT, exist_ok=True)
    intents = sys.argv[1:] or sorted(QUESTIONS)
    with ThreadPoolExecutor(max_workers=10) as ex:
        for rec in ex.map(one, intents):
            with open(os.path.join(OUT, rec["intent"] + ".json"), "w") as f:
                json.dump(rec, f, indent=1)
            o = (rec["ours"]["text"] or "!! none")[:96].replace("\n", " ")
            l = (rec["leader"]["text"] or "!! none")[:96].replace("\n", " ")
            print(f"{rec['intent']:22} OURS   {o}")
            print(f"{'':22} LEADER {l}")


if __name__ == "__main__":
    main()
