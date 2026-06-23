#!/usr/bin/env python3
"""
v2 processing: take v1 processed.json + crosstoken.json, attach a cross-token (VITA/BIO)
overlap block, and emit processed_v2.json (a superset of v1's data).
"""
import json, os
import requests

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session(); S.headers.update({"User-Agent": "vitarna-analysis/1.0"})
VITA = "0x81f8f0bb1cB2A06649E51913A151F0E7Ef6FA321"
BIO  = "0xcb1592591996765Ec0eFc1f92599A19767ee5ffA"


def tmeta(a):
    d = S.get(f"https://eth.blockscout.com/api/v2/tokens/{a}", timeout=20).json()
    return {
        "price": float(d.get("exchange_rate") or 0),
        "supply": int(d.get("total_supply") or 0) / 1e18,
        "mcap": float(d.get("circulating_market_cap") or 0),
        "holders": d.get("_") or None,
    }


def main():
    base = json.load(open(os.path.join(DATA, "processed.json")))
    ct = json.load(open(os.path.join(DATA, "crosstoken.json")))
    vm, bm = tmeta(VITA), tmeta(BIO)

    base["crosstoken"] = {
        "meta": {
            "vita_addr": VITA.lower(), "bio_addr": BIO.lower(),
            "vita_price": vm["price"], "bio_price": bm["price"],
            "vita_supply": vm["supply"], "bio_supply": bm["supply"],
            "vita_mcap": vm["mcap"], "bio_mcap": bm["mcap"],
        },
        "balances": ct,
        "analyzed": len(ct),
    }
    out = os.path.join(DATA, "processed_v2.json")
    json.dump(base, open(out, "w"), default=str)
    print(f"Saved {out} ({os.path.getsize(out)//1024} KB)")

    # report
    TH = 1
    nv = sum(1 for v in ct.values() if v["vita"] > TH)
    nb = sum(1 for v in ct.values() if v["bio"] > TH)
    nboth = sum(1 for v in ct.values() if v["vita"] > TH and v["bio"] > TH)
    sv = sum(v["vita"] for v in ct.values()); sb = sum(v["bio"] for v in ct.values())
    print(f"VITA price ${vm['price']:.4f}  BIO price ${bm['price']:.5f}")
    print(f"analyzed {len(ct)} wallets: hold VITA {nv}, BIO {nb}, both {nboth}")
    print(f"sum VITA {sv:,.0f} (${sv*vm['price']/1e6:.2f}M)  sum BIO {sb:,.0f} (${sb*bm['price']/1e6:.2f}M)")
    # top cross holders
    pr = {a: v["vita"]*vm["price"] + v["bio"]*bm["price"] for a, v in ct.items()}
    print("\nTop cross-token holders:")
    labels = base["labels"]
    for a, cv in sorted(pr.items(), key=lambda x: -x[1])[:10]:
        if cv < 1: break
        print(f"  {a[:10]} VITA={ct[a]['vita']:>12,.0f} BIO={ct[a]['bio']:>14,.0f} (${cv:,.0f}) {labels.get(a,'')}")


if __name__ == "__main__":
    main()
