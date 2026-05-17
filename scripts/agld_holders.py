#!/usr/bin/env python3
"""Scan all AGLD Transfer events and compute full holder snapshot. Resumable."""
import urllib.request, json, time, sys, os
from collections import defaultdict

RPCS = [
    "https://ethereum.publicnode.com",
    "https://eth-mainnet.public.blastapi.io",
    "https://eth.merkle.io",
]
AGLD = "0x32353a6c91143bfd6c7d363b546e62a9a2489a20"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

DEPLOY_BLOCK = 13142000
END_BLOCK = 25117157
CHUNK = 40000
CKPT = "output/agld_scan_ckpt.json"

def call(method, params, tries=8):
    last_err = None
    for i in range(tries):
        rpc = RPCS[i % len(RPCS)]
        try:
            req = urllib.request.Request(rpc,
                data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                headers={"Content-Type":"application/json","User-Agent":"curl/8"})
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** i, 15))
    raise last_err

# resume
balances = defaultdict(int)
b = DEPLOY_BLOCK
total_events = 0
mint_total = 0
burn_total = 0
if os.path.exists(CKPT):
    with open(CKPT) as f:
        c = json.load(f)
    b = c["next_block"]
    total_events = c["total_events"]
    mint_total = int(c["mint_total"])
    burn_total = int(c["burn_total"])
    for a, v in c["balances"].items():
        balances[a] = int(v)
    print(f"resuming from block {b}, events={total_events}", file=sys.stderr, flush=True)

ckpt_save_at = 0
while b <= END_BLOCK:
    to_b = min(b + CHUNK - 1, END_BLOCK)
    try:
        r = call("eth_getLogs", [{"address": AGLD, "topics": [TOPIC], "fromBlock": hex(b), "toBlock": hex(to_b)}])
    except Exception as e:
        print(f"  hard err at {b}: {e}", file=sys.stderr, flush=True)
        time.sleep(5)
        continue
    if "error" in r:
        if CHUNK > 2000:
            CHUNK = CHUNK // 2
            print(f"  shrink chunk to {CHUNK}", file=sys.stderr, flush=True)
            continue
        print(f"  err at {b}: {r['error']}", file=sys.stderr, flush=True)
        b = to_b + 1
        continue
    logs = r.get("result", [])
    for l in logs:
        frm = "0x" + l["topics"][1][-40:]
        to  = "0x" + l["topics"][2][-40:]
        amt = int(l["data"], 16)
        if frm != "0x0000000000000000000000000000000000000000":
            balances[frm] -= amt
        else:
            mint_total += amt
        if to == "0x0000000000000000000000000000000000000000":
            burn_total += amt
        else:
            balances[to] += amt
        total_events += 1
    b = to_b + 1
    if b - ckpt_save_at > 500000 or b > END_BLOCK:
        os.makedirs("output", exist_ok=True)
        with open(CKPT, "w") as f:
            json.dump({
                "next_block": b,
                "total_events": total_events,
                "mint_total": str(mint_total),
                "burn_total": str(burn_total),
                "balances": {a: str(v) for a, v in balances.items() if v != 0}
            }, f)
        ckpt_save_at = b
        print(f"  ckpt at block {b}: events={total_events} mint={mint_total/10**18:,.0f}", file=sys.stderr, flush=True)

# Filter out zero balances
holders = {a: v for a, v in balances.items() if v > 0}
print(f"\nfinal: holders={len(holders)} total_minted={mint_total/10**18:,.2f} total_burned={burn_total/10**18:,.2f}", file=sys.stderr)

out = {
  "total_events": total_events,
  "total_minted": str(mint_total),
  "total_burned": str(burn_total),
  "holders": {a: str(v) for a, v in sorted(holders.items(), key=lambda x: -x[1])}
}
os.makedirs("output", exist_ok=True)
with open("output/agld_holders.json", "w") as f:
    json.dump(out, f)
print(f"wrote output/agld_holders.json", file=sys.stderr)
