#!/usr/bin/env python3
"""Build the in-scope wallet list (data/wallets.json) from the 3 HTML docs,
plus a merged receive-side map (data/rows_merged.json) from prior pool scans.

In-scope = any wallet address that appears in a table row that shows a
proceeds figure (rows containing 'avg' or '@ sold'), excluding pool/token
contracts. If the prior /tmp scan files are gone (container recycle) but a
good data/wallets.json already exists, it is preserved.
"""
import json, glob, re, os
from pl_common import DATA, log, load_json, save_json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Repricing scope = the two outflow docs only. ake-analysis.html is left
# untouched (its sale-date proceeds were verified correct and its insider rows
# encode hand-tuned sale/hold/non-sale judgments that must not be overwritten).
DOCS = ["pool-outflows.html", "insider-outflows.html"]
POOL_OF = {"ta1": "T&A1", "kol": "KOL", "cn1": "CN1", "cn2": "CN2",
           "cn3": "CN3", "community": "COM", "inv": "INV"}
DENY = set(a.lower() for a in [
    "0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248",  # T&A1
    "0xaf66503770451c83a4f12a1146a32271893508ce",  # CN3
    "0xd2f72669e560c7ecd3c681612963990ef6f1981b",  # CN2
    "0xb7c7786b6ca1130584f005e9c86554114b7fad62",  # CN1
    "0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5",  # KOL
    "0x6b394c413d60b2aadb37a907a73a6f9a91c35015",  # Community
    "0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db",  # AKE token
    "0x0000000000000000000000000000000000000000",
])
ADDR = re.compile(r"0x[0-9a-fA-F]{40}")


def build_merged():
    merged = {}

    def add(addr, recv, first, bal, sold, pool):
        a = addr.lower()
        m = merged.setdefault(a, {"recv": 0, "first": 10 ** 12, "bal": 0,
                                  "sold": 0, "pools": []})
        m["recv"] += recv or 0
        m["first"] = min(m["first"], first or 10 ** 12)
        if bal is not None:
            m["bal"] += bal
        if sold is not None:
            m["sold"] += sold
        if pool not in m["pools"]:
            m["pools"].append(pool)

    def pool_from_name(fn):
        b = os.path.basename(fn)
        for k in POOL_OF:
            if b.startswith(k):
                return POOL_OF[k]
        return "?"

    # One source file PER POOL only. The same pool's data lives in several
    # files (*_full_rows.json, *_rows.json, *_full.json) and globs overlap, so
    # naive summing triple-counts `recv`. Prefer the processed rows file.
    cand = set(glob.glob("/tmp/*_full_rows.json") + glob.glob("/tmp/*_rows.json") +
               glob.glob("/tmp/*_full.json"))
    by_pool = {}
    for fn in cand:
        b = os.path.basename(fn)
        pri = 3 if b.endswith("_full_rows.json") else (2 if b.endswith("_rows.json") else 1)
        pool = pool_from_name(fn)
        if pool not in by_pool or pri > by_pool[pool][0]:
            by_pool[pool] = (pri, fn)
    files = [v[1] for v in by_pool.values()]
    log("extract_wallets: using 1 file per pool: " +
        ", ".join(sorted(os.path.basename(f) for f in files)))
    for fn in files:
        try:
            d = json.load(open(fn))
        except Exception:
            continue
        pool = pool_from_name(fn)
        if isinstance(d, list):
            for r in d:
                add(r.get("addr", ""), r.get("recv"), r.get("first"),
                    r.get("bal"), r.get("sold"), pool)
        elif isinstance(d, dict) and "recips" in d:
            for rec in d["recips"]:
                add(rec[0], rec[1], rec[3], None, None, pool)
    return merged


def main():
    merged = build_merged()
    if merged:
        save_json(os.path.join(DATA, "rows_merged.json"), merged)
        log("extract_wallets: rows_merged = %d receivers" % len(merged))
    else:
        merged = load_json(os.path.join(DATA, "rows_merged.json"), {})
        log("extract_wallets: no /tmp scan files; using existing rows_merged "
            "(%d)" % len(merged))

    scope = {}
    for doc in DOCS:
        path = os.path.join(REPO, doc)
        try:
            html = open(path).read()
        except FileNotFoundError:
            log("extract_wallets: !! %s missing" % doc); continue
        n = 0
        for row in re.split(r"(?=<tr)", html):
            low = row.lower()
            # any row that carries a proceeds figure (highlighted $ cell) or a
            # sale annotation is in scope
            if ("highlight" not in low and "@ sold" not in low and
                    "avg" not in low):
                continue
            addrs = [a.lower() for a in ADDR.findall(row) if a.lower() not in DENY]
            if not addrs:
                continue
            a = addrs[0]
            e = scope.setdefault(a, {"docs": [], "rows": 0})
            if doc not in e["docs"]:
                e["docs"].append(doc)
            e["rows"] += 1
            n += 1
        log("extract_wallets: %s -> %d proceeds rows" % (doc, n))

    if not scope:
        existing = load_json(os.path.join(DATA, "wallets.json"), {})
        if existing:
            log("extract_wallets: no rows parsed; keeping existing wallets.json "
                "(%d)" % len(existing))
            return
    for a, e in scope.items():
        m = merged.get(a)
        e["first_blk"] = int(m["first"]) if (m and m["first"] < 10 ** 12) else 57800000
        e["recv_hint"] = (m["recv"] if m else None)
        e["pools"] = (m["pools"] if m else [])
    save_json(os.path.join(DATA, "wallets.json"), scope)
    log("extract_wallets: IN-SCOPE wallets = %d" % len(scope))


if __name__ == "__main__":
    main()
