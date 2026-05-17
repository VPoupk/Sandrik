"""
On-chain scraper for Loot (for Adventurers) — 0xff9c1b15b16263c61d017ee9f65c50e4ae0113d7
Fetches tokenURI for all 8,000 tokens via public Ethereum RPC,
decodes the base64 SVG metadata, extracts items, and counts occurrences.
"""

import asyncio
import aiohttp
import base64
import json
import re
import sys
from collections import defaultdict

RPC = "https://ethereum.publicnode.com"
CONTRACT = "0xff9c1b15b16263c61d017ee9f65c50e4ae0113d7"
TOTAL_TOKENS = 8000
BATCH_SIZE = 50      # calls per HTTP request
CONCURRENCY = 8      # simultaneous HTTP requests
RETRY_LIMIT = 4


def build_call_data(token_id: int) -> str:
    return "0xc87b56dd" + hex(token_id)[2:].zfill(64)


def decode_result(raw_hex: str) -> list[str]:
    """ABI-decode eth_call result → list of 8 item strings."""
    hex_data = raw_hex[2:]  # strip 0x
    length = int(hex_data[64:128], 16)
    string_hex = hex_data[128:128 + length * 2]
    uri = bytes.fromhex(string_hex).decode("utf-8")

    b64_json = uri.split(",", 1)[1]
    metadata = json.loads(base64.b64decode(b64_json))

    svg_b64 = metadata["image"].split(",", 1)[1]
    svg = base64.b64decode(svg_b64).decode("utf-8")

    items = re.findall(r"<text[^>]*>([^<]+)</text>", svg)
    return items


async def fetch_batch(session: aiohttp.ClientSession, batch: list[int]) -> dict[int, list[str]]:
    payload = [
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [
                {"to": CONTRACT, "data": build_call_data(tid)},
                "latest",
            ],
            "id": tid,
        }
        for tid in batch
    ]
    for attempt in range(RETRY_LIMIT):
        try:
            async with session.post(RPC, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                results = await resp.json(content_type=None)
                out = {}
                for r in results:
                    tid = r["id"]
                    if "result" in r:
                        try:
                            out[tid] = decode_result(r["result"])
                        except Exception as e:
                            print(f"  decode error token {tid}: {e}", file=sys.stderr)
                    else:
                        print(f"  RPC error token {tid}: {r.get('error')}", file=sys.stderr)
                return out
        except Exception as e:
            wait = 2 ** attempt
            print(f"  request error (attempt {attempt+1}): {e}, retrying in {wait}s", file=sys.stderr)
            await asyncio.sleep(wait)
    return {}


async def main():
    all_items: dict[int, list[str]] = {}      # tokenId → [8 items]
    occurrences: dict[str, int] = defaultdict(int)
    slot_occurrences: dict[str, dict[str, int]] = {
        "weapon": defaultdict(int),
        "chest": defaultdict(int),
        "head": defaultdict(int),
        "waist": defaultdict(int),
        "foot": defaultdict(int),
        "hand": defaultdict(int),
        "neck": defaultdict(int),
        "ring": defaultdict(int),
    }
    slot_names = list(slot_occurrences.keys())

    batches = [
        list(range(i, min(i + BATCH_SIZE, TOTAL_TOKENS + 1)))
        for i in range(1, TOTAL_TOKENS + 1, BATCH_SIZE)
    ]

    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded_fetch(session, batch):
        async with sem:
            return await fetch_batch(session, batch)

    connector = aiohttp.TCPConnector(limit=CONCURRENCY * 2)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [bounded_fetch(session, b) for b in batches]
        done = 0
        for coro in asyncio.as_completed(tasks):
            result = await coro
            for tid, items in result.items():
                all_items[tid] = items
                for i, item in enumerate(items):
                    occurrences[item] += 1
                    if i < len(slot_names):
                        slot_occurrences[slot_names[i]][item] += 1
            done += len(result)
            if done % 500 == 0 or done == TOTAL_TOKENS:
                print(f"  progress: {done}/{TOTAL_TOKENS} tokens fetched", file=sys.stderr)

    print(f"Fetched {len(all_items)} tokens total", file=sys.stderr)

    # Save raw per-token data
    with open("output/tokens.json", "w") as f:
        json.dump({str(k): v for k, v in sorted(all_items.items())}, f, indent=2)

    # Save global occurrence counts sorted by frequency desc
    occ_sorted = dict(sorted(occurrences.items(), key=lambda x: -x[1]))
    with open("output/occurrences.json", "w") as f:
        json.dump(occ_sorted, f, indent=2)

    # Save per-slot occurrence counts
    slot_occ_sorted = {
        slot: dict(sorted(counts.items(), key=lambda x: -x[1]))
        for slot, counts in slot_occurrences.items()
    }
    with open("output/slot_occurrences.json", "w") as f:
        json.dump(slot_occ_sorted, f, indent=2)

    # Produce rarity tiers per item
    def tier(count):
        if count >= 375:  return "Common"
        if count >= 75:   return "Uncommon"
        if count >= 11:   return "Rare"
        if count >= 2:    return "Epic"
        if count == 1:    return "Mythic"
        return "Unknown"

    rarity = {
        item: {"occurrences": cnt, "tier": tier(cnt)}
        for item, cnt in occ_sorted.items()
    }
    with open("output/rarity.json", "w") as f:
        json.dump(rarity, f, indent=2)

    print("\n=== SUMMARY ===")
    print(f"Total unique item strings: {len(occurrences)}")
    from collections import Counter
    tier_counts = Counter(v["tier"] for v in rarity.values())
    for t in ["Common", "Uncommon", "Rare", "Epic", "Mythic"]:
        print(f"  {t}: {tier_counts[t]} unique items")

    print("\n=== TOP 10 MOST COMMON ITEMS ===")
    for item, data in list(rarity.items())[:10]:
        print(f"  {data['occurrences']:5d}x  [{data['tier']}]  {item}")

    print("\n=== RAREST ITEMS (sample of Mythic) ===")
    mythic = [item for item, d in rarity.items() if d["tier"] == "Mythic"]
    for item in mythic[:20]:
        print(f"  1x  [Mythic]  {item}")
    print(f"  ... ({len(mythic)} Mythic items total)")


if __name__ == "__main__":
    import os
    os.makedirs("output", exist_ok=True)
    asyncio.run(main())
