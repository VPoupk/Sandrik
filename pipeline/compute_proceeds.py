#!/usr/bin/env python3
"""Join dated outbound disposals with daily prices -> data/proceeds.json.

For each in-scope wallet:
  - date every outbound transfer by its block timestamp (exact, cached)
  - bydate[date] = AKE sent out that day
  - proceeds_by_outbound = sum(ake_day * price_on_that_day)
  - net_sold = received - current_balance (fresh on-chain balance)
  - reconcile gross_outbound vs net_sold; flag round-trips (ratio off by >5%)
  - proceeds_net_sold = net_sold * outbound-weighted-avg price (the figure to
    use for the doc when gross != net; documented, not hidden)

Sale date is taken as the wallet's OUTBOUND/disposal date (the day it parted
with the tokens, i.e. sent them to a CEX/DEX). Destinations are recorded raw
for auditability.
"""
import os
from pl_common import (DATA, log, load_json, save_json, set_status,
                       balance_of, blk_date, load_ts, save_ts)


def main():
    wallets = load_json(os.path.join(DATA, "wallets.json"), {})
    raw = load_json(os.path.join(DATA, "disposals_raw.json"), None)
    prices = load_json(os.path.join(DATA, "ake_daily_prices.json"), {})
    merged = load_json(os.path.join(DATA, "rows_merged.json"), {})
    if not raw or not raw.get("events"):
        log("compute_proceeds: no disposal events yet — skipping")
        return
    scope = set(wallets.keys())
    events = [e for e in raw["events"] if e[1].lower() in scope]
    log("compute_proceeds: %d outbound events in scope" % len(events))

    ts = load_ts()
    blocks = sorted({e[0] for e in events})
    log("compute_proceeds: dating %d unique disposal blocks" % len(blocks))
    for i, blk in enumerate(blocks):
        blk_date(blk, ts)
        if i % 50 == 0:
            save_ts(ts)
    save_ts(ts)

    pks = sorted(prices) if prices else []
    pmin, pmax = (pks[0], pks[-1]) if pks else (None, None)

    def price_for(date):
        if not pks:
            return None, None
        if date in prices:
            return prices[date], date
        if date < pmin:
            return prices[pmin], pmin + " (clamped-early)"
        if date > pmax:
            return prices[pmax], pmax + " (clamped-late)"
        prev = [d for d in pks if d <= date]
        chosen = prev[-1] if prev else pks[0]
        return prices[chosen], chosen + " (nearest)"

    out = {}
    anomalies = []
    for a in sorted(scope):
        evs = [e for e in events if e[1].lower() == a]
        bydate, dests = {}, {}
        for blk, frm, to, amt, tx in evs:
            d = ts[str(blk)]
            bydate[d] = bydate.get(d, 0) + amt
            dests[to.lower()] = dests.get(to.lower(), 0) + amt
        gross_out = sum(bydate.values())
        recv = (merged.get(a, {}) or {}).get("recv", 0)
        try:
            bal = balance_of(a)
        except Exception as e:
            log("  balance_of(%s) failed: %s" % (a[:10], e))
            bal = None
        net_sold = (recv - bal) if (recv and bal is not None) else gross_out

        proc = 0.0
        perdate = {}
        for d, amt in sorted(bydate.items()):
            p, used = price_for(d)
            v = amt * (p or 0)
            proc += v
            perdate[d] = {"ake": round(amt, 2), "price": p,
                          "price_date": used, "usd": round(v, 2)}
        wavg = (proc / gross_out) if gross_out else None
        ratio = (gross_out / net_sold) if net_sold else None
        flag = None
        if net_sold and gross_out and abs(ratio - 1) > 0.05:
            flag = "gross_out/net_sold=%.2f (round-trips/non-sale transfers? review)" % ratio
            anomalies.append((a, flag))
        if not evs:
            flag = "NO outbound transfers found in scan range"
            anomalies.append((a, flag))
        proc_net = (net_sold * wavg) if (wavg is not None and net_sold) else proc

        out[a] = {
            "recv": round(recv, 2),
            "balance": (round(bal, 2) if bal is not None else None),
            "net_sold": round(net_sold, 2),
            "gross_outbound": round(gross_out, 2),
            "n_outbound": len(evs),
            "proceeds_by_outbound": round(proc, 2),
            "proceeds_net_sold": round(proc_net, 2),
            "wavg_price": wavg,
            "bydate": perdate,
            "dest_top": sorted(({k: round(v, 1) for k, v in dests.items()}).items(),
                               key=lambda x: -x[1])[:5],
            "pools": (merged.get(a, {}) or {}).get("pools", []),
            "flag": flag,
        }

    save_json(os.path.join(DATA, "proceeds.json"), out)
    log("compute_proceeds: wrote %d wallets; anomalies=%d" % (len(out), len(anomalies)))
    for a, f in anomalies[:30]:
        log("   ANOMALY %s  %s" % (a[:10], f))
    set_status(stage="proceeds_done", proceeds_wallets=len(out),
               anomalies=len(anomalies))


if __name__ == "__main__":
    main()
