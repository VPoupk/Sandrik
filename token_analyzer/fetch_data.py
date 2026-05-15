#!/usr/bin/env python3
"""
Token distribution analyzer for Base chain.
Fetches holders, transfers, and detects wallet clusters.
"""

import json
import time
import os
import sys
from collections import defaultdict
from datetime import datetime

import requests

TOKEN_ADDRESS = "0x54F16Bd3996169914c84dBb2A16635100cF48A0a"
CHAIN = "base"
BASESCAN_API = "https://api.basescan.org/api"
BASE_RPC = "https://mainnet.base.org"

# Optional: set BASESCAN_API_KEY env var for higher rate limits (free at basescan.org)
API_KEY = os.environ.get("BASESCAN_API_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)


def basescan_get(params: dict, delay: float = 0.25) -> dict:
    if API_KEY:
        params["apikey"] = API_KEY
    try:
        resp = requests.get(BASESCAN_API, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        time.sleep(delay)
        return data
    except Exception as e:
        print(f"  [warn] BaseScan request failed: {e}")
        return {}


def rpc_call(method: str, params: list) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    try:
        resp = requests.post(BASE_RPC, json=payload, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  [warn] RPC call failed: {e}")
        return {}


def fetch_token_info() -> dict:
    print("Fetching token info...")
    data = basescan_get({
        "module": "token",
        "action": "tokeninfo",
        "contractaddress": TOKEN_ADDRESS,
    })
    result = data.get("result", [{}])
    if isinstance(result, list) and result:
        return result[0]
    return {}


def fetch_top_holders(max_holders: int = 500) -> list:
    print(f"Fetching top {max_holders} holders...")
    holders = []
    page = 1
    page_size = 100

    while len(holders) < max_holders:
        data = basescan_get({
            "module": "token",
            "action": "tokenholderlist",
            "contractaddress": TOKEN_ADDRESS,
            "page": page,
            "offset": page_size,
        }, delay=0.3)

        result = data.get("result", [])
        if not result or data.get("status") == "0":
            break

        holders.extend(result)
        print(f"  Page {page}: got {len(result)} holders (total: {len(holders)})")

        if len(result) < page_size:
            break
        page += 1

    return holders[:max_holders]


def fetch_transfers(max_transfers: int = 5000) -> list:
    print(f"Fetching up to {max_transfers} transfer events...")
    transfers = []
    page = 1
    page_size = 1000

    while len(transfers) < max_transfers:
        data = basescan_get({
            "module": "account",
            "action": "tokentx",
            "contractaddress": TOKEN_ADDRESS,
            "page": page,
            "offset": page_size,
            "sort": "desc",
        }, delay=0.3)

        result = data.get("result", [])
        if not result or data.get("status") == "0":
            break

        transfers.extend(result)
        print(f"  Page {page}: got {len(result)} transfers (total: {len(transfers)})")

        if len(result) < page_size:
            break
        page += 1

    return transfers[:max_transfers]


def detect_clusters(transfers: list, holders_set: set) -> dict:
    """
    Build an adjacency graph between top holders based on direct transfers.
    Returns edges with transfer counts and volumes.
    """
    print("Detecting wallet clusters from transfer graph...")
    edges = defaultdict(lambda: {"count": 0, "volume": 0.0})

    for tx in transfers:
        src = tx.get("from", "").lower()
        dst = tx.get("to", "").lower()
        val_str = tx.get("value", "0")
        decimals = int(tx.get("tokenDecimal", "18"))

        try:
            val = int(val_str) / (10 ** decimals)
        except Exception:
            val = 0.0

        if src in holders_set and dst in holders_set and src != dst:
            key = tuple(sorted([src, dst]))
            edges[key]["count"] += 1
            edges[key]["volume"] += val

    result = []
    for (a, b), info in edges.items():
        result.append({
            "source": a,
            "target": b,
            "tx_count": info["count"],
            "volume": round(info["volume"], 4),
        })

    result.sort(key=lambda x: x["tx_count"], reverse=True)
    return result


def compute_wallet_stats(transfers: list, address: str) -> dict:
    address = address.lower()
    sent = []
    received = []
    counterparties = set()

    for tx in transfers:
        src = tx.get("from", "").lower()
        dst = tx.get("to", "").lower()
        val_str = tx.get("value", "0")
        decimals = int(tx.get("tokenDecimal", "18"))
        try:
            val = int(val_str) / (10 ** decimals)
        except Exception:
            val = 0.0
        ts = int(tx.get("timeStamp", "0"))

        if src == address:
            sent.append({"to": dst, "value": val, "ts": ts, "hash": tx.get("hash", "")})
            counterparties.add(dst)
        elif dst == address:
            received.append({"from": src, "value": val, "ts": ts, "hash": tx.get("hash", "")})
            counterparties.add(src)

    return {
        "total_sent": round(sum(x["value"] for x in sent), 4),
        "total_received": round(sum(x["value"] for x in received), 4),
        "tx_sent": len(sent),
        "tx_received": len(received),
        "unique_counterparties": len(counterparties),
        "first_tx_ts": min(
            ([x["ts"] for x in sent] + [x["ts"] for x in received]) or [0]
        ),
        "last_tx_ts": max(
            ([x["ts"] for x in sent] + [x["ts"] for x in received]) or [0]
        ),
    }


def main():
    print(f"\n=== Token Analyzer: {TOKEN_ADDRESS} on Base ===\n")

    # 1. Token metadata
    token_info = fetch_token_info()
    print(f"Token: {token_info.get('name', '?')} ({token_info.get('symbol', '?')})")
    print(f"Total supply: {token_info.get('totalSupply', '?')}")
    print()

    # 2. Top holders
    holders = fetch_top_holders(500)
    if not holders:
        print("ERROR: Could not fetch holders. Check API access.")
        sys.exit(1)

    print(f"\nFetched {len(holders)} holders")

    # Normalize decimals from holder list
    decimals = 18
    if token_info.get("divisor"):
        try:
            decimals = int(token_info["divisor"])
        except Exception:
            pass

    total_supply_raw = None
    if token_info.get("totalSupply"):
        try:
            total_supply_raw = int(token_info["totalSupply"])
        except Exception:
            pass

    holders_normalized = []
    for h in holders:
        qty_raw = int(h.get("TokenHolderQuantity", "0"))
        qty = qty_raw / (10 ** decimals)
        pct = (qty_raw / total_supply_raw * 100) if total_supply_raw else None
        holders_normalized.append({
            "address": h["TokenHolderAddress"].lower(),
            "balance": round(qty, 4),
            "balance_raw": qty_raw,
            "percent": round(pct, 4) if pct is not None else None,
            "rank": len(holders_normalized) + 1,
        })

    holders_set = {h["address"] for h in holders_normalized}

    # 3. Transfer events
    transfers = fetch_transfers(5000)
    print(f"\nFetched {len(transfers)} transfer events")

    # 4. Per-holder stats
    print("\nComputing per-holder stats...")
    for h in holders_normalized:
        stats = compute_wallet_stats(transfers, h["address"])
        h.update(stats)

    # 5. Cluster edges
    edges = detect_clusters(transfers, holders_set)
    print(f"Found {len(edges)} edges between top holders")

    # 6. Save everything
    out = {
        "meta": {
            "token_address": TOKEN_ADDRESS,
            "chain": CHAIN,
            "token_name": token_info.get("name", ""),
            "token_symbol": token_info.get("symbol", ""),
            "total_supply": token_info.get("totalSupply", ""),
            "decimals": decimals,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "holder_count": len(holders_normalized),
            "transfer_count": len(transfers),
        },
        "holders": holders_normalized,
        "edges": edges,
        "transfers": transfers,
    }

    out_path = os.path.join(DATA_DIR, "token_data.json")
    with open(out_path, "w") as f:
        json.dump(out, f)
    print(f"\nData saved to {out_path}")

    # Print quick summary
    print("\n--- Top 20 Holders ---")
    for h in holders_normalized[:20]:
        pct_str = f"{h['percent']:.2f}%" if h["percent"] is not None else "?"
        print(f"  #{h['rank']:3d}  {h['address'][:10]}...  {h['balance']:>15,.2f}  ({pct_str})")

    print("\n--- Top 10 Edges (connected wallets) ---")
    for e in edges[:10]:
        print(f"  {e['source'][:10]}... <-> {e['target'][:10]}...  txs={e['tx_count']}  vol={e['volume']:,.2f}")

    print("\nDone.")


if __name__ == "__main__":
    main()
