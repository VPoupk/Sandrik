#!/usr/bin/env python3
"""Scan all AGLD Transfer events and compute full holder snapshot."""
import urllib.request, json, time, sys, os
from collections import defaultdict

RPC = "https://ethereum.publicnode.com"
AGLD = "0x32353a6c91143bfd6c7d363b546e62a9a2489a20"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

DEPLOY_BLOCK = 13142000
END_BLOCK = 25117157  # latest at the time of investigation
CHUNK = 40000  # publicnode limit is 50k

def call(method, params, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(RPC,
                data=json.dumps({"jsonrpc":"2.0","id":1,"method":method,"params":params}).encode(),
                headers={"Content-Type":"application/json","User-Agent":"curl/8"})
            return json.loads(urllib.request.urlopen(req, timeout=45).read())
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)

balances = defaultdict(int)
b = DEPLOY_BLOCK
total_events = 0
mint_total = 0
burn_total = 0

while b <= END_BLOCK:
    to_b = min(b + CHUNK - 1, END_BLOCK)
    r = call("eth_getLogs", [{
        "address": AGLD,
        "topics": [TOPIC],
        "fromBlock": hex(b),
        "toBlock": hex(to_b)
    }])
    if "error" in r:
        # halve and retry
        if CHUNK > 5000:
            CHUNK = CHUNK // 2
            continue
        print(f"  err at {b}: {r['error']}", file=sys.stderr)
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
    print(f"  blocks {b}-{to_b}: events={total_events} mint={mint_total/10**18:,.0f} burn={burn_total/10**18:,.0f}", file=sys.stderr)
    b = to_b + 1

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
