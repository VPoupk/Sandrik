#!/usr/bin/env python3
"""
Cross-token overlap collector. For every notable VITARNA wallet (all current holders plus
36h buyers, past sellers and cluster members), fetch exact VITA and BIO balances.
Saves data/crosstoken.json  ->  {address: {"vita": float, "bio": float}}
"""
import json, os, time
import requests

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session(); S.headers.update({"User-Agent": "vitarna-analysis/1.0"})
VITA = "0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321"
BIO  = "0xcb1592591996765Ec0eFc1f92599A19767ee5ffA"
# infra we don't want in the "whale overlap" (pool reserves / router pass-through)
SKIP_KINDS = {"pool", "router", "zero"}


def bal(tok, addr, tries=5):
    for i in range(tries):
        try:
            r = S.get("https://eth.blockscout.com/api",
                      params={"module": "account", "action": "tokenbalance",
                              "contractaddress": tok, "address": addr}, timeout=20)
            if r.status_code == 200:
                v = r.json().get("result", "0")
                return int(v) / 1e18
            time.sleep(1.0 * (i + 1))
        except Exception:
            time.sleep(1.0 * (i + 1))
    return 0.0


def main():
    p = json.load(open(os.path.join(DATA, "processed.json")))
    kinds = p["kinds"]
    targets = []
    seen = set()
    pools_routers = {a for a, k in kinds.items() if k in SKIP_KINDS}
    def add(a):
        a = a.lower()
        if a and a not in seen and a not in pools_routers:
            seen.add(a); targets.append(a)
    for h in p["holders"]:
        add(h["address"])
    for b in p["buyers36h"]:
        add(b["address"])
    for s in p["past_sellers"]:
        add(s["address"])
    for c in p["clusters"]:
        for m in c["members"]:
            add(m)
    for n in p["nodes"]:
        add(n["id"])

    print(f"cross-token targets: {len(targets)}")
    out = {}
    for i, a in enumerate(targets, 1):
        out[a] = {"vita": bal(VITA, a), "bio": bal(BIO, a)}
        if i % 40 == 0:
            print(f"  {i}/{len(targets)}")
        time.sleep(0.03)
    json.dump(out, open(os.path.join(DATA, "crosstoken.json"), "w"))
    print(f"Saved crosstoken.json ({len(out)} wallets)")
    # quick report
    nv = sum(1 for v in out.values() if v["vita"] > 1)
    nb = sum(1 for v in out.values() if v["bio"] > 1)
    nboth = sum(1 for v in out.values() if v["vita"] > 1 and v["bio"] > 1)
    print(f"hold VITA: {nv} | hold BIO: {nb} | hold both: {nboth} | of {len(out)}")


if __name__ == "__main__":
    main()
