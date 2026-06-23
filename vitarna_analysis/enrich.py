#!/usr/bin/env python3
"""
Enrich target wallets with:
  - Blockscout label / contract name / ENS / is_contract / creator
  - first native-ETH funder (who sent this wallet its first ETH)
Then label the funders themselves (CEX / disperse / wallet) so we can detect
common-funder clusters. Saves data/enrich.json
"""
import json, os, time
import requests

BS = "https://eth.blockscout.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session(); S.headers.update({"User-Agent": "vitarna-analysis/1.0"})


def get(url, params=None, tries=5):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return {"_404": True}
            time.sleep(1.2 * (i + 1))
        except Exception:
            time.sleep(1.2 * (i + 1))
    return {}


def addr_info(a):
    d = get(f"{BS}/api/v2/addresses/{a}")
    if d.get("_404"):
        return {"label": None, "is_contract": False, "ens": None, "creator": None, "tags": []}
    tags = []
    md = d.get("metadata") or {}
    for t in (md.get("tags") or []):
        tags.append(t.get("name"))
    pub = [ (t.get("display_name") if isinstance(t, dict) else t) for t in (d.get("public_tags") or []) ]
    label = d.get("ens_domain_name") or d.get("name") or (pub[0] if pub else None) or (tags[0] if tags else None)
    return {
        "label": label,
        "is_contract": d.get("is_contract", False),
        "ens": d.get("ens_domain_name"),
        "name": d.get("name"),
        "creator": d.get("creator_address_hash"),
        "tags": [t for t in (tags + pub) if t],
    }


def first_funder(a):
    """Earliest inbound ETH transfer -> funder."""
    d = get(f"{BS}/api", {"module": "account", "action": "txlist",
                          "address": a, "sort": "asc", "page": 1, "offset": 25})
    res = d.get("result")
    if not isinstance(res, list):
        return None
    for t in res:
        frm = (t.get("from") or "").lower()
        to = (t.get("to") or "").lower()
        try:
            val = int(t.get("value", "0"))
        except Exception:
            val = 0
        if to == a.lower() and frm and frm != a.lower() and val > 0:
            return {"funder": frm, "ts": int(t.get("timeStamp", "0")),
                    "hash": t.get("hash"), "value_eth": val / 1e18}
    return None


def main():
    targets = json.load(open(os.path.join(DATA_DIR, "targets.json")))
    out = {}
    funders_needed = set()
    for i, a in enumerate(targets, 1):
        info = addr_info(a)
        rec = {"info": info, "funder": None}
        if not info["is_contract"]:
            f = first_funder(a)
            rec["funder"] = f
            if f:
                funders_needed.add(f["funder"])
        out[a] = rec
        if i % 20 == 0:
            print(f"  {i}/{len(targets)} enriched")
        time.sleep(0.05)

    # label the funders
    print(f"Labelling {len(funders_needed)} unique funders...")
    funder_labels = {}
    for i, f in enumerate(funders_needed, 1):
        fi = addr_info(f)
        funder_labels[f] = fi
        if i % 20 == 0:
            print(f"  {i}/{len(funders_needed)} funders")
        time.sleep(0.05)

    json.dump({"wallets": out, "funder_labels": funder_labels},
              open(os.path.join(DATA_DIR, "enrich.json"), "w"))
    print(f"Saved enrich.json ({len(out)} wallets, {len(funder_labels)} funders)")

    # quick common-funder report
    from collections import defaultdict
    by_funder = defaultdict(list)
    for a, rec in out.items():
        f = rec.get("funder")
        if f:
            by_funder[f["funder"]].append(a)
    print("\n=== Shared funders (>=2 target wallets) ===")
    for f, ws in sorted(by_funder.items(), key=lambda x: -len(x[1])):
        if len(ws) >= 2:
            fl = funder_labels.get(f, {})
            print(f"  funder {f[:10]}… [{fl.get('label') or ('contract' if fl.get('is_contract') else 'EOA')}] -> {len(ws)} wallets")


if __name__ == "__main__":
    main()
