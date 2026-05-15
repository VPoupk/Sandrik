#!/usr/bin/env python3
"""
Process raw transfer log data into structured JSON for visualization.
Computes: holder stats, transfer graph edges, cluster detection.
"""

import json
import os
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TOKEN_ADDRESS = "0x54F16Bd3996169914c84dBb2A16635100cF48A0a"
DECIMALS = 18
TOTAL_SUPPLY = 10_000_000 * 10**18
ZERO = "0x0000000000000000000000000000000000000000"

# Anchor: block 45987770 = 1778764887 (confirmed from RPC), 2s block time
ANCHOR_BLOCK = 45987770
ANCHOR_TS = 1778764887
BASE_BLOCK_TIME = 2.0
DEPLOY_BLOCK = 45987717
# Wallets with > this many unique counterparties are treated as DEX/pool/bot
HUB_COUNTERPARTY_THRESHOLD = 50


def block_to_approx_ts(block: int) -> int:
    return int(ANCHOR_TS + (block - ANCHOR_BLOCK) * BASE_BLOCK_TIME)


def load_raw() -> dict:
    path = os.path.join(DATA_DIR, "raw_data.json")
    with open(path) as f:
        return json.load(f)


def build_nodes(holders: list) -> list:
    nodes = []
    for rank, (address, balance_raw) in enumerate(holders, 1):
        balance = balance_raw / 10**DECIMALS
        pct = balance_raw / TOTAL_SUPPLY * 100
        nodes.append({
            "id": address,
            "rank": rank,
            "balance": round(balance, 4),
            "balance_raw": balance_raw,
            "percent": round(pct, 4),
            "label": f"{address[:6]}...{address[-4:]}",
        })
    return nodes


def build_edges_and_stats(transfers: list, top_holders: set, all_holders: set) -> tuple:
    """
    Returns (edges, wallet_stats).
    edges: connections between top holders only.
    wallet_stats: per-wallet transfer stats.
    """
    # Edge map: (src, dst) -> {count, volume}
    edge_map = defaultdict(lambda: {"count": 0, "volume_raw": 0})

    # Per-wallet stats
    stats = defaultdict(lambda: {
        "sent_count": 0, "sent_volume": 0,
        "recv_count": 0, "recv_volume": 0,
        "counterparties": set(),
        "blocks": [],
    })

    for tx in transfers:
        src = tx["from"]
        dst = tx["to"]
        val = tx["value"]
        block = tx["block"]

        if src != ZERO and src in all_holders:
            stats[src]["sent_count"] += 1
            stats[src]["sent_volume"] += val
            stats[src]["counterparties"].add(dst)
            stats[src]["blocks"].append(block)

        if dst in all_holders:
            stats[dst]["recv_count"] += 1
            stats[dst]["recv_volume"] += val
            stats[dst]["counterparties"].add(src)
            stats[dst]["blocks"].append(block)

        # Only add edge if both are top holders
        if src in top_holders and dst in top_holders and src != dst:
            key = (src, dst)
            edge_map[key]["count"] += 1
            edge_map[key]["volume_raw"] += val

    edges = []
    for (src, dst), info in edge_map.items():
        edges.append({
            "source": src,
            "target": dst,
            "tx_count": info["count"],
            "volume": round(info["volume_raw"] / 10**DECIMALS, 4),
            "volume_raw": info["volume_raw"],
        })
    edges.sort(key=lambda e: e["tx_count"], reverse=True)

    wallet_stats = {}
    for addr, s in stats.items():
        blocks = s["blocks"]
        first_block = min(blocks) if blocks else 0
        last_block = max(blocks) if blocks else 0
        wallet_stats[addr] = {
            "sent_count": s["sent_count"],
            "sent_volume": round(s["sent_volume"] / 10**DECIMALS, 4),
            "recv_count": s["recv_count"],
            "recv_volume": round(s["recv_volume"] / 10**DECIMALS, 4),
            "unique_counterparties": len(s["counterparties"]),
            "first_block": first_block,
            "last_block": last_block,
            "first_ts_approx": block_to_approx_ts(first_block) if first_block else 0,
            "last_ts_approx": block_to_approx_ts(last_block) if last_block else 0,
        }

    return edges, wallet_stats


def detect_clusters(edges: list, top_holder_set: set) -> list:
    """
    Simple union-find clustering on wallets connected by direct transfers.
    Returns list of cluster assignments [{address, cluster_id}].
    """
    parent = {addr: addr for addr in top_holder_set}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for edge in edges:
        if edge["tx_count"] >= 1:
            union(edge["source"], edge["target"])

    clusters = defaultdict(list)
    for addr in top_holder_set:
        clusters[find(addr)].append(addr)

    cluster_list = []
    for cid, (root, members) in enumerate(
        sorted(clusters.items(), key=lambda x: -len(x[1]))
    ):
        for member in members:
            cluster_list.append({"address": member, "cluster_id": cid, "cluster_root": root})

    return cluster_list


def main():
    print("Loading raw data...")
    raw = load_raw()

    holders_raw = raw["holders"]  # list of [address, balance_raw]
    transfers = raw["transfers"]  # list of {from, to, value, block, hash}

    # Fix int parsing (JSON may have stored as string via default=str)
    for t in transfers:
        if isinstance(t["value"], str):
            t["value"] = int(t["value"])
        if isinstance(t["block"], str):
            t["block"] = int(t["block"])

    for i, h in enumerate(holders_raw):
        if isinstance(h[1], str):
            holders_raw[i][1] = int(h[1])

    print(f"Holders: {len(holders_raw)}, Transfers: {len(transfers)}")

    # Top N for visualization (too many nodes = unreadable)
    TOP_N = 200
    top_holders = holders_raw[:TOP_N]
    top_holder_set = {h[0] for h in top_holders}
    all_holder_set = {h[0] for h in holders_raw}

    # Build node list
    nodes = build_nodes(top_holders)

    # Build edges and per-wallet stats
    edges, wallet_stats = build_edges_and_stats(transfers, top_holder_set, all_holder_set)

    # Merge stats into nodes
    for node in nodes:
        s = wallet_stats.get(node["id"], {})
        node.update(s)

    # Detect clusters
    clusters = detect_clusters(edges, top_holder_set)
    cluster_map = {c["address"]: c["cluster_id"] for c in clusters}
    for node in nodes:
        node["cluster_id"] = cluster_map.get(node["id"], -1)

    # Compute concentration stats
    cumulative = 0
    for i, node in enumerate(nodes):
        cumulative += node["percent"]
        node["cumulative_percent"] = round(cumulative, 4)

    # Summary stats
    supply_in_top3 = sum(n["percent"] for n in nodes[:3])
    supply_in_top10 = sum(n["percent"] for n in nodes[:10])
    supply_in_top50 = sum(n["percent"] for n in nodes[:50])

    summary = {
        "token_address": TOKEN_ADDRESS,
        "token_name": "Peptai",
        "token_symbol": "PEPTAI",
        "total_supply": 10_000_000,
        "decimals": 18,
        "total_holders": len(holders_raw),
        "total_transfers": len(transfers),
        "deploy_block": DEPLOY_BLOCK,
        "deploy_ts_approx": block_to_approx_ts(DEPLOY_BLOCK),
        "top3_pct": round(supply_in_top3, 2),
        "top10_pct": round(supply_in_top10, 2),
        "top50_pct": round(supply_in_top50, 2),
        "edge_count": len(edges),
        "chain": "base",
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    out = {
        "summary": summary,
        "nodes": nodes,
        "edges": edges[:500],  # cap edges for viz
        "all_holders": [{"address": h[0], "balance": round(h[1] / 10**DECIMALS, 4), "percent": round(h[1] / TOTAL_SUPPLY * 100, 4)} for h in holders_raw],
    }

    out_path = os.path.join(DATA_DIR, "processed.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"\nSaved to {out_path}")
    print(f"\n=== Summary ===")
    print(f"Token: {summary['token_name']} ({summary['token_symbol']})")
    print(f"Total supply: {summary['total_supply']:,}")
    print(f"Holders: {summary['total_holders']:,}")
    print(f"Transfers: {summary['total_transfers']:,}")
    print(f"Top 3  hold: {summary['top3_pct']}%")
    print(f"Top 10 hold: {summary['top10_pct']}%")
    print(f"Top 50 hold: {summary['top50_pct']}%")
    print(f"Edges (direct transfers between top {TOP_N}): {summary['edge_count']}")


if __name__ == "__main__":
    main()
