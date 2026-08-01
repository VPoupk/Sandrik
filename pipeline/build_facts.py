#!/usr/bin/env python3
"""
Compute every number that goes into ake-analysis.html and dump to
pipeline/data/facts.json. USD is ALWAYS priced at the CoinGecko daily price
for the UTC date of the block in which the transfer landed.
Data-only: never touches HTML, never runs git.
"""
import json, bisect, datetime, os, collections, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names import nick, short, NAMES

D = 'pipeline/data/'
CK = json.load(open(D + 'ake_delta_v2_checkpoint.json'))
GAP = json.load(open(D + 'ake_gap_may_jun_2026_checkpoint.json'))
CG = json.load(open(D + 'ake_daily_prices_cg.json'))
TS = json.load(open(D + 'blk_ts.json')) if os.path.exists(D + 'blk_ts.json') else {}

_tb = sorted(int(k) for k in TS)
_tv = [TS[str(b)] for b in _tb]
_pk = sorted(CG)

POOLS = {
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 25_000_000_000,
    '0xaf66503770451c83a4f12a1146a32271893508ce': 16_000_000_000,
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 15_000_000_000,
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62':  8_000_000_000,
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b':  7_500_000_000,
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248':  5_000_000_000,
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5':  1_700_000_000,
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015':  1_000_000_000,
}
ALPHA = '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db'
DEXP = '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d'


def bdate(bn):
    bn = int(bn)
    if str(bn) in TS:
        t = TS[str(bn)]
    else:
        i = bisect.bisect_left(_tb, bn)
        if i == 0:
            t = _tv[0]
        elif i >= len(_tb):
            t = _tv[-1]
        else:
            t = _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def px(d):
    if d in CG:
        return CG[d]
    i = bisect.bisect_right(_pk, d) - 1
    return CG[_pk[max(0, i)]]


def all_rows():
    """every transfer captured in the delta window, (blk, from, to, ake)"""
    out = []
    for src in (GAP, CK):
        for r in src.get('rows', []) + src.get('watch_rows', []):
            out.append((r[0], r[1], r[2], int(r[3]) / 1e18))
        for r in src['big']:
            out.append((r[0], r[1], r[2], int(r[3]) / 1e18))
    seen, uniq = set(), []
    for r in out:
        k = (r[0], r[1], r[2], r[3])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return sorted(uniq)


def main():
    rows = all_rows()
    facts = {'window': {'from_block': 100_940_328, 'to_block': CK['last_block'],
                        'from_date': bdate(100_940_328), 'to_date': bdate(CK['last_block'])}}

    # ---- pool outflows, priced per transfer date -------------------------
    pool = {}
    for bn, s, d, v in rows:
        if s in POOLS:
            e = pool.setdefault(s, {'total': 0.0, 'usd': 0.0, 'n': 0,
                                    'dest': collections.Counter(),
                                    'byday': collections.defaultdict(lambda: [0.0, 0.0])})
            dt = bdate(bn)
            u = v * px(dt)
            e['total'] += v; e['usd'] += u; e['n'] += 1
            e['dest'][d] += v
            e['byday'][dt][0] += v
            e['byday'][dt][1] += u
    for a, e in pool.items():
        e['dest'] = e['dest'].most_common(12)
        e['byday'] = {k: v for k, v in sorted(e['byday'].items())}
        e['wavg'] = e['usd'] / e['total'] if e['total'] else 0
    facts['pool_out'] = pool

    # ---- Binance Alpha in/out, priced per date --------------------------
    ai = {'in': 0.0, 'in_usd': 0.0, 'out': 0.0, 'out_usd': 0.0,
          'src': collections.Counter(), 'dst': collections.Counter(),
          'byday': collections.defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])}
    for bn, s, d, v in rows:
        dt = bdate(bn); p = px(dt)
        if d == ALPHA:
            ai['in'] += v; ai['in_usd'] += v * p; ai['src'][s] += v
            ai['byday'][dt][0] += v; ai['byday'][dt][1] += v * p
        if s == ALPHA:
            ai['out'] += v; ai['out_usd'] += v * p; ai['dst'][d] += v
            ai['byday'][dt][2] += v; ai['byday'][dt][3] += v * p
    ai['src'] = ai['src'].most_common(25)
    ai['dst'] = ai['dst'].most_common(25)
    ai['byday'] = {k: v for k, v in sorted(ai['byday'].items())}
    facts['alpha'] = ai

    # ---- >=50mn transfers with date + price ------------------------------
    big = []
    for r in sorted(GAP['big'] + CK['big'], key=lambda x: x[0]):
        bn, s, d, v = r[0], r[1], r[2], int(r[3]) / 1e18
        dt = bdate(bn)
        big.append({'blk': bn, 'date': dt, 'from': s, 'to': d, 'ake': v,
                    'price': px(dt), 'usd': v * px(dt),
                    'from_n': nick(s), 'to_n': nick(d),
                    'tx': r[4] if len(r) > 4 else None})
    facts['big'] = big

    # ---- per-address net flow over the window ---------------------------
    m = {}
    for src in (GAP['agg'], CK['agg']):
        for a, v in src.items():
            e = m.setdefault(a, [0, 0, 0, 0])
            for i in range(4):
                e[i] += v[i]
    net = sorted(((a, (v[2]-v[0])/1e18, v[0]/1e18, v[2]/1e18, v[1], v[3])
                  for a, v in m.items()), key=lambda r: -r[1])
    facts['top_gainers'] = [
        {'addr': a, 'net': n, 'out': o, 'in': i, 'n_out': no, 'n_in': ni, 'nick': nick(a)}
        for a, n, o, i, no, ni in net[:40]]
    facts['top_losers'] = [
        {'addr': a, 'net': n, 'out': o, 'in': i, 'n_out': no, 'n_in': ni, 'nick': nick(a)}
        for a, n, o, i, no, ni in net[-40:]][::-1]
    facts['n_addresses_touched'] = len(m)

    # ---- DEX pool flow by day -------------------------------------------
    dex = collections.defaultdict(lambda: [0.0, 0.0, 0, 0])
    for src in (GAP, CK):
        for k, v in src.get('dexb', {}).items():
            dt = bdate(int(k))
            e = dex[dt]
            e[0] += v[0]/1e18; e[1] += v[2]/1e18; e[2] += v[1]; e[3] += v[3]
    facts['dex_byday'] = {k: dex[k] for k in sorted(dex)}

    json.dump(facts, open(D + 'facts.json', 'w'), indent=1, default=str)
    print('facts.json written')
    print('window', facts['window'])
    print('pools moved:', {nick(a): round(e['total']/1e9, 3) for a, e in pool.items()})
    print('alpha in', round(ai['in']/1e9, 3), 'bn  out', round(ai['out']/1e9, 3), 'bn')
    print('big transfers', len(big), ' addresses touched', len(m))


if __name__ == '__main__':
    main()
