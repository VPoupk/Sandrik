#!/usr/bin/env python3
"""Reprice the 'Est. proceeds' cells in pool-outflows.html and
insider-outflows.html using ground-truth on-chain disposal data.

Method (faithful to "price on the day sold / sent to CEX"):
  For each recipient row, take the SOLD amount = captured - holds, then value it
  FIFO against the wallet's actual dated outbound transfers — i.e. the earliest
  disposals are priced at the AKE/USD price on those exact days. Proceeds =
  sum(min(remaining, day_amount) * day_price).

Rows are SKIPPED untouched when there is no clean disposal data (holders,
Binance-Alpha/airdrop and other special insider rows, out-of-scope wallets).
ake-analysis.html is never modified.
"""
import os, re, sys, json
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PRC = json.load(open(os.path.join(HERE, "data", "proceeds.json")))

DOCS = {
    "pool-outflows.html": "pool",       # cols: Recipient, Received[num0], Holds[num1], ...
    "insider-outflows.html": "insider",  # cols: Date, Recipient, Amount[num0], Txs, Holds, ...
}
ADDR = re.compile(r"/address/(0x[0-9a-fA-F]{40})")
NUMTD = re.compile(r'<td class="num">([\d,]+)</td>')
HILITE = re.compile(r'<td class="num" style="color:var\(--highlight\)">.*?</td>', re.S)


def fmt_usd(v):
    if v >= 1e6:
        return "~$%.2fM" % (v / 1e6)
    if v >= 1e4:
        return "~$%dK" % round(v / 1e3)
    if v >= 1e3:
        return "~$%.1fK" % (v / 1e3)
    return "~$%d" % round(v)


def fmt_dates(dlist):
    ds = sorted(set(dlist))
    f = lambda s: datetime.strptime(s, "%Y-%m-%d").strftime("%b %-d, %Y")
    if not ds:
        return ""
    return f(ds[0]) if len(ds) == 1 else "%s – %s" % (f(ds[0]), f(ds[-1]))


def fifo_value(sold, bydate):
    rem, proc, used = sold, 0.0, []
    for dt in sorted(bydate):
        amt = bydate[dt]["ake"]
        pr = bydate[dt]["price"] or 0
        take = min(rem, amt)
        if take > 0:
            proc += take * pr
            used.append(dt)
            rem -= take
        if rem <= 1e-6:
            break
    return proc, used, rem


def count_rows():
    """How many repriceable proceeds rows each wallet appears in (across both
    docs). Wallets in >1 row are multi-pool: price each row at the wallet VWAP
    so the rows sum correctly instead of FIFO double-counting early disposals."""
    cnt = {}
    for doc in DOCS:
        html = open(os.path.join(REPO, doc)).read()
        for part in re.split(r"(?=<tr)", html):
            if "highlight" not in part:
                continue
            am = ADDR.search(part)
            if not am:
                continue
            a = am.group(1).lower()
            rec = PRC.get(a)
            if rec and rec.get("bydate") and rec.get("wavg_price") is not None:
                cnt[a] = cnt.get(a, 0) + 1
    return cnt


def main(write=False):
    rowcount = count_rows()
    total_changes = 0
    for doc, kind in DOCS.items():
        path = os.path.join(REPO, doc)
        html = open(path).read()
        parts = re.split(r"(?=<tr)", html)
        changes = 0
        for i, part in enumerate(parts):
            if "highlight" not in part:
                continue
            am = ADDR.search(part)
            if not am:
                continue
            addr = am.group(1).lower()
            rec = PRC.get(addr)
            if not rec or not rec.get("bydate") or rec.get("wavg_price") is None:
                continue  # holder / special / out-of-scope -> leave untouched
            nums = [float(n.replace(",", "")) for n in NUMTD.findall(part)]
            if not nums:
                continue
            captured = nums[0]
            holds = nums[1] if (kind == "pool" and len(nums) > 1) else 0.0
            sold = max(captured - holds, 0.0)
            sold = min(sold, rec["gross_outbound"])  # can't sell more than disposed
            if sold <= 0:
                continue
            if rowcount.get(addr, 1) > 1:
                # multi-pool wallet: VWAP so its rows sum without double-counting
                proc = sold * rec["wavg_price"]
                used = sorted(rec["bydate"])
            else:
                proc, used, _ = fifo_value(sold, rec["bydate"])
            new_td = ('<td class="num" style="color:var(--highlight)">%s<br>'
                      '<span style="font-size:10px;color:var(--muted)">@ sold %s</span></td>'
                      % (fmt_usd(proc), fmt_dates(used)))
            new_part, n = HILITE.subn(new_td, part, count=1)
            if n == 0:
                print("  !! no highlight cell matched for %s in %s" % (addr[:10], doc))
                continue
            old_usd = re.search(r"~?\$[0-9.,]+\s*[KMB]?", part)
            print("  %-20s %-12s captured=%-15s sold=%-15s  %s -> %s  (%s)"
                  % (doc, addr[:10], "%g" % captured, "%g" % sold,
                     old_usd.group(0) if old_usd else "?", fmt_usd(proc),
                     fmt_dates(used)))
            parts[i] = new_part
            changes += 1
        if write and changes:
            open(path, "w").write("".join(parts))
        print(">>> %s: %d cells %s\n" % (doc, changes, "REPRICED" if write else "would change"))
        total_changes += changes
    print("TOTAL: %d cells %s" % (total_changes, "written" if write else "(dry run)"))


if __name__ == "__main__":
    main(write=("--write" in sys.argv))
