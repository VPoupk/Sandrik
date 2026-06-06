#!/usr/bin/env python3
"""Ensure data/ake_daily_prices.json is present and as current as possible.

Tries CoinGecko for a daily AKE/USD series; on any failure (rate limit,
network policy, unknown coin id) it keeps the existing real price file as the
source of truth. Never destroys existing data.
"""
import os, json, urllib.request, datetime
from pl_common import DATA, log, load_json, save_json, set_status

PRICE = os.path.join(DATA, "ake_daily_prices.json")
COIN_IDS = ["akedo-games", "akedo"]


def main():
    existing = load_json(PRICE, {})
    log("fetch_prices: existing points = %d" % len(existing))
    got = None
    for cid in COIN_IDS:
        url = ("https://api.coingecko.com/api/v3/coins/%s/market_chart"
               "?vs_currency=usd&days=365&interval=daily" % cid)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ake-pipeline"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read())
            prices = d.get("prices", [])
            if prices:
                got = {}
                for ms, p in prices:
                    dt = datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
                    got[dt] = p
                log("fetch_prices: CoinGecko '%s' -> %d daily points" % (cid, len(got)))
                break
        except Exception as e:
            log("fetch_prices: CoinGecko '%s' failed: %s" % (cid, e))

    if got:
        merged = dict(existing)
        merged.update(got)
        save_json(PRICE, merged)
        log("fetch_prices: merged -> %d points (%s..%s)"
            % (len(merged), min(merged), max(merged)))
    else:
        log("fetch_prices: keeping existing price file (no live refresh)")

    final = load_json(PRICE, {})
    set_status(price_points=len(final),
               price_range=("%s..%s" % (min(final), max(final)) if final else None))


if __name__ == "__main__":
    main()
