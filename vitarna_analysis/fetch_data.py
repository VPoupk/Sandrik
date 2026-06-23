#!/usr/bin/env python3
"""
VitaRNA (VITARNA) token distribution + flow data collector.
Chain: Ethereum mainnet. Source: Blockscout (eth.blockscout.com), no API key needed.

Pulls:
  - token metadata
  - full current holder list (with labels: ENS, contract tags, public tags)
  - full transfer history (via two bulk legacy tokentx calls, deduped)

Saves raw_data.json for process_data.py to crunch.
"""
import json
import os
import time
import sys
from datetime import datetime, timezone

import requests

TOKEN = "0x7b66E84Be78772a3afAF5ba8c1993a1B5D05F9C2"
BS = "https://eth.blockscout.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "vitarna-analysis/1.0"})


def get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = SESSION.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 429:
                time.sleep(2 * (i + 1))
                continue
            print(f"  [warn] {r.status_code} {url}")
            time.sleep(1.5 * (i + 1))
        except Exception as e:
            print(f"  [warn] {e}")
            time.sleep(1.5 * (i + 1))
    return {}


def fetch_token_meta():
    print("Fetching token metadata...")
    d = get(f"{BS}/api/v2/tokens/{TOKEN}")
    c = get(f"{BS}/api/v2/tokens/{TOKEN}/counters")
    d["_counters"] = c
    return d


def fetch_holders():
    print("Fetching all holders (paged)...")
    out = []
    url = f"{BS}/api/v2/tokens/{TOKEN}/holders"
    params = {}
    page = 0
    while True:
        page += 1
        d = get(url, params=params)
        items = d.get("items", [])
        for it in items:
            addr = it.get("address", {})
            tags = []
            md = addr.get("metadata") or {}
            for t in (md.get("tags") or []):
                tags.append(t.get("name"))
            out.append({
                "address": addr.get("hash", "").lower(),
                "value_raw": it.get("value", "0"),
                "ens": addr.get("ens_domain_name"),
                "is_contract": addr.get("is_contract", False),
                "name": addr.get("name"),
                "public_tags": [t.get("display_name") if isinstance(t, dict) else t
                                for t in (addr.get("public_tags") or [])],
                "meta_tags": tags,
                "proxy_type": addr.get("proxy_type"),
                "implementations": [im.get("name") for im in (addr.get("implementations") or [])],
            })
        print(f"  page {page}: +{len(items)} (total {len(out)})")
        npp = d.get("next_page_params")
        if not npp:
            break
        params = npp
        time.sleep(0.2)
    return out


def fetch_all_transfers():
    """
    Legacy tokentx returns up to 10,000 rows/call.
    Two calls (desc newest 10k + asc oldest 10k) cover the full history (total ~15.8k),
    then dedupe on (hash, from, to, value).
    """
    print("Fetching transfers (bulk, 2 calls)...")
    base = f"{BS}/api"
    common = {"module": "account", "action": "tokentx",
              "contractaddress": TOKEN, "page": 1, "offset": 10000}
    rows = {}

    for srt in ("desc", "asc"):
        p = dict(common, sort=srt)
        d = get(base, params=p)
        res = d.get("result") or []
        added = 0
        for t in res:
            key = (t.get("hash"), t.get("from", "").lower(),
                   t.get("to", "").lower(), t.get("value"))
            if key not in rows:
                rows[key] = {
                    "hash": t.get("hash"),
                    "from": t.get("from", "").lower(),
                    "to": t.get("to", "").lower(),
                    "value": int(t.get("value", "0")),
                    "block": int(t.get("blockNumber", "0")),
                    "ts": int(t.get("timeStamp", "0")),
                    "method": t.get("functionName") or t.get("methodId") or "",
                }
                added += 1
        print(f"  sort={srt}: {len(res)} rows, +{added} new (total {len(rows)})")
        time.sleep(0.3)

    transfers = sorted(rows.values(), key=lambda x: (x["block"], x["hash"]))
    return transfers


def main():
    meta = fetch_token_meta()
    print(f"Token: {meta.get('name')} ({meta.get('symbol')}) "
          f"holders={meta.get('_counters', {}).get('token_holders_count')} "
          f"transfers={meta.get('_counters', {}).get('transfers_count')}")

    holders = fetch_holders()
    print(f"Holders fetched: {len(holders)}")

    transfers = fetch_all_transfers()
    print(f"Transfers fetched (deduped): {len(transfers)}")
    if transfers:
        print(f"  block range {transfers[0]['block']} -> {transfers[-1]['block']}")
        print(f"  ts range {transfers[0]['ts']} -> {transfers[-1]['ts']}")

    out = {
        "meta": {
            "token": TOKEN,
            "name": meta.get("name"),
            "symbol": meta.get("symbol"),
            "decimals": int(meta.get("decimals", "18")),
            "total_supply_raw": meta.get("total_supply"),
            "holders_count": meta.get("_counters", {}).get("token_holders_count"),
            "transfers_count": meta.get("_counters", {}).get("transfers_count"),
            "exchange_rate_usd": meta.get("exchange_rate"),
            "circulating_market_cap": meta.get("circulating_market_cap"),
            "volume_24h": meta.get("volume_24h"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
        "holders": holders,
        "transfers": transfers,
    }
    path = os.path.join(DATA_DIR, "raw_data.json")
    with open(path, "w") as f:
        json.dump(out, f)
    print(f"\nSaved {path}  ({os.path.getsize(path)//1024} KB)")


if __name__ == "__main__":
    main()
