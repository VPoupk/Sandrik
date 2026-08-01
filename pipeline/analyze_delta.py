#!/usr/bin/env python3
"""
Turn the delta scan checkpoint into the analysis tables for ake-analysis.html.
Every USD figure is priced at the CoinGecko daily close for the UTC date of the
block the transfer landed in -- never a single flat price. Data-only.
"""
import json, bisect, datetime, os, sys

CK = json.load(open('pipeline/data/ake_delta_v2_checkpoint.json'))
GAP = json.load(open('pipeline/data/ake_gap_may_jun_2026_checkpoint.json'))
PRICES = json.load(open('pipeline/data/ake_daily_prices_cg.json'))
TS = json.load(open('pipeline/data/blk_ts.json')) if os.path.exists('pipeline/data/blk_ts.json') else {}

_tsb = sorted(int(k) for k in TS)
_tsv = [TS[str(b)] for b in _tsb]
_pk = sorted(PRICES)


def blk_date(bn):
    """UTC date of a block, exact if fetched, else linear interpolation."""
    if str(bn) in TS:
        t = TS[str(bn)]
    else:
        i = bisect.bisect_left(_tsb, bn)
        if i == 0:
            t = _tsv[0]
        elif i >= len(_tsb):
            t = _tsv[-1]
        else:
            b0, b1 = _tsb[i - 1], _tsb[i]
            t0, t1 = _tsv[i - 1], _tsv[i]
            t = t0 + (t1 - t0) * (bn - b0) / (b1 - b0)
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def price(date):
    """CoinGecko daily price for that exact UTC date; nearest earlier if missing."""
    if date in PRICES:
        return PRICES[date]
    i = bisect.bisect_right(_pk, date) - 1
    return PRICES[_pk[max(0, i)]] if _pk else 0.0


def usd(amt_ake, date):
    return amt_ake * price(date)


def fmt_ake(x):
    a = abs(x)
    if a >= 1e12: return f'{x/1e12:.2f}tn'
    if a >= 1e9:  return f'{x/1e9:.2f}bn'
    if a >= 1e6:  return f'{x/1e6:.1f}mn'
    if a >= 1e3:  return f'{x/1e3:.1f}k'
    return f'{x:.0f}'


def fmt_usd(x):
    a = abs(x)
    if a >= 1e6: return f'${x/1e6:.2f}M'
    if a >= 1e3: return f'${x/1e3:.0f}K'
    return f'${x:.0f}'


def merged_agg():
    m = {}
    for src in (GAP['agg'], CK['agg']):
        for a, v in src.items():
            e = m.setdefault(a, [0, 0, 0, 0])
            for i in range(4):
                e[i] += v[i]
    return m


def merged_big():
    return sorted(GAP['big'] + CK['big'], key=lambda r: r[0])


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'big'
    if mode == 'big':
        print(f'{"date":11} {"blk":>10}  {"from":12} {"to":12} {"AKE":>10} {"USD @ that date":>16}')
        for r in merged_big():
            bn, s, d, v = r[0], r[1], r[2], int(r[3]) / 1e18
            dt = blk_date(bn)
            print(f'{dt:11} {bn:>10}  {s[:12]} {d[:12]} {fmt_ake(v):>10} '
                  f'{fmt_usd(usd(v, dt)):>16}  @${price(dt):.8f}')
    elif mode == 'net':
        m = merged_agg()
        rows = sorted(((a, (v[2] - v[0]) / 1e18, v[0] / 1e18, v[2] / 1e18, v[1], v[3])
                       for a, v in m.items()), key=lambda r: -abs(r[1]))
        for a, net, o, i, on, inn in rows[:int(sys.argv[2]) if len(sys.argv) > 2 else 40]:
            print(f'{a}  net {fmt_ake(net):>10}  out {fmt_ake(o):>10}/{on:<6} in {fmt_ake(i):>10}/{inn}')
