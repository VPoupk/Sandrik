#!/usr/bin/env python3
"""
Rebuild pipeline/data/daily_series.json and tracker_daily.json from every scan
segment on disk, and refuse to write if the venue segments do not tile the
chain without a hole.

The incremental version of this bit me: venue_s11 was added on top of an
existing daily_series.json, the window between s10 and s11 had never been
scanned, and 2 September - the single most important day in the window -
silently reported zero exchange flow and an inflated coverage ratio. A gap in
a set of scan ranges is invisible in the output unless something checks for
it, so this checks for it.

Usage: rebuild_daily.py
Data-only: writes to pipeline/data only. Never HTML, never git.
"""
import json, glob, collections, bisect, datetime, sys, os

D = 'pipeline/data/'
POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

TS = json.load(open(D + 'blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    if i == 0:
        return _tv[0]
    if i >= len(_tb):
        return _tv[-1]
    return _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])


def bd(bn):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime('%Y-%m-%d')


def check_tiling(name, segs, head):
    """segs: list of (from, to). Must cover [min, head] with no hole."""
    segs = sorted(segs)
    lo = segs[0][0]
    cur = lo
    holes = []
    for a, b in segs:
        if a > cur:
            holes.append((cur, a - 1))
        cur = max(cur, b + 1)
    if cur <= head:
        holes.append((cur, head))
    if holes:
        print(f'  !! {name}: {len(holes)} GAP(S)')
        for a, b in holes:
            print(f'       {a:,} - {b:,}   ({bd(a)} .. {bd(b)})   {b-a+1:,} blocks')
        return False
    print(f'  {name}: continuous {lo:,} -> {head:,}')
    return True


def main():
    head = json.load(open(D + 'head_now.json'))['head']
    V = json.load(open(D + 'venues_scan.json'))

    print('coverage check')
    vsegs = []
    for f in sorted(glob.glob(D + 'venue_s*.json')):
        c = json.load(open(f))
        vsegs.append((c['from'], c['last_block']))
    ok = check_tiling('venue segments', vsegs, head)
    if not ok:
        print('\nrefusing to write: fill the gaps and re-run')
        sys.exit(1)

    # ---- exchange flow, from every segment
    day = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    for f in sorted(glob.glob(D + 'venue_s*.json')):
        c = json.load(open(f))
        for v, cps in c['agg'].items():
            g = V[v]['group']
            for p, dd in cps.items():
                for d, q in dd.items():
                    day[d][g][0] += int(q[0]); day[d][g][1] += int(q[1])

    # ---- allocation-pool outflow, from every segment
    pool = collections.defaultdict(lambda: [0, 0, collections.Counter()])
    for f in sorted(glob.glob(D + 'poolflow_*.json')):
        for r in json.load(open(f))['rows']:
            fr, to, v = r[1].lower(), r[2].lower(), int(r[3])
            d = bd(r[0])
            if fr in POOLS and to not in POOLS:
                pool[d][0] += v; pool[d][2][POOLS[fr]] += v
            if to in POOLS and fr not in POOLS:
                pool[d][1] += v

    json.dump({'exchange': {d: {g: [str(x[0]), str(x[1])] for g, x in v.items()}
                            for d, v in day.items()},
               'pool': {d: [str(v[0]), str(v[1]), {k: str(x) for k, x in v[2].items()}]
                        for d, v in pool.items()}},
              open(D + 'daily_series.json', 'w'))
    print(f'\ndaily_series: {len(day)} exchange days, {len(pool)} pool days')

    # ---- merged tracker series
    cg = json.load(open(D + 'cg_daily_pv.json'))
    dexd = json.load(open(D + 'dex_daily.json'))
    rng = json.load(open(D + 'range_pcs.json'))
    mintday = collections.Counter()
    for bn, tl, tu, liq, a0, a1, tx in rng['rows']:
        mintday[bd(bn)] += int(a0)

    out = []
    last = bd(head)
    for d in sorted(cg):
        if d < '2026-06-01' or d > last:
            continue
        p, vol, mc = cg[d]['price'], cg[d]['volume'], cg[d]['mcap']
        e = day.get(d, {})
        cin, cout = (x / 1e18 for x in e.get('cex', [0, 0]))
        bi, bo = (x / 1e18 for x in e.get('binance', [0, 0]))
        di, do = (int(x) for x in dexd.get(d, ['0', '0']))
        thr = (di + do) / 1e18
        mint = mintday.get(d, 0) / 1e18
        dex_usd = (thr - mint) * p if thr > mint else thr * p
        cex_usd = (cin + cout + bi + bo) * p
        out.append({'d': d, 'p': p, 'vol': vol, 'mc': mc, 'turn': vol / mc if mc else 0,
                    'cin': cin, 'cout': cout, 'bin': bi, 'bout': bo,
                    'pool_out': pool.get(d, [0, 0, {}])[0] / 1e18,
                    'dex_ake': thr, 'dex_mint': mint, 'dex_usd': dex_usd,
                    'onchain_usd': cex_usd, 'onchain_total': dex_usd + cex_usd,
                    'ratio': vol / cex_usd if cex_usd > 1000 else None,
                    'cov': (dex_usd + cex_usd) / vol if vol else 0})
    json.dump(out, open(D + 'tracker_daily.json', 'w'), indent=1)
    zero = [r['d'] for r in out if r['onchain_usd'] == 0]
    print(f'tracker_daily: {len(out)} days, {out[0]["d"]} .. {out[-1]["d"]}')
    print(f'days with zero exchange flow: {len(zero)}' + (f'  {zero}' if zero else ''))


if __name__ == '__main__':
    main()
