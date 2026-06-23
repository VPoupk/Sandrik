#!/usr/bin/env python3
"""
Pull the COMPLETE token-transfer history via Blockscout v2 cursor pagination
(deduplicated, with log_index). Overwrites transfers in raw_data.json.
"""
import json, os, time
import requests

TOKEN = "0x7b66E84Be78772a3afAF5ba8c1993a1B5D05F9C2"
BS = "https://eth.blockscout.com"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session()
S.headers.update({"User-Agent": "vitarna-analysis/1.0"})


def get(url, params, tries=6):
    for i in range(tries):
        try:
            r = S.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            time.sleep(1.5 * (i + 1))
        except Exception as e:
            time.sleep(1.5 * (i + 1))
    return {}


def main():
    url = f"{BS}/api/v2/tokens/{TOKEN}/transfers"
    params = {}
    seen = {}
    page = 0
    while True:
        page += 1
        d = get(url, params)
        items = d.get("items", [])
        for it in items:
            tot = it.get("total") or {}
            try:
                v = int(tot.get("value", "0"))
            except Exception:
                v = 0
            h = it.get("transaction_hash") or it.get("tx_hash")
            li = it.get("log_index")
            key = (h, li)
            frm = (it.get("from") or {}).get("hash", "").lower()
            to = (it.get("to") or {}).get("hash", "").lower()
            ts = it.get("timestamp")
            # convert ISO ts -> epoch
            import datetime as _dt
            ep = 0
            if ts:
                try:
                    ep = int(_dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp())
                except Exception:
                    ep = 0
            seen[key] = {
                "hash": h, "from": frm, "to": to, "value": v,
                "block": it.get("block_number") or 0, "ts": ep,
                "method": it.get("method") or "",
            }
        if page % 25 == 0:
            print(f"  page {page}: total {len(seen)}")
        npp = d.get("next_page_params")
        if not npp:
            break
        params = npp
        time.sleep(0.1)

    transfers = sorted(seen.values(), key=lambda x: (x["block"], x["ts"]))
    print(f"Done. {len(transfers)} transfers over {page} pages.")

    raw_path = os.path.join(DATA_DIR, "raw_data.json")
    with open(raw_path) as f:
        raw = json.load(f)
    raw["transfers"] = transfers
    raw["meta"]["transfers_fetched_v2"] = len(transfers)
    with open(raw_path, "w") as f:
        json.dump(raw, f)
    print(f"Updated {raw_path}")


if __name__ == "__main__":
    main()
