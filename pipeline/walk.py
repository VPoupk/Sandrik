#!/usr/bin/env python3
"""
Full lifetime AKE transfer history for one or more addresses, straight from
eth_getLogs with a topic-position filter. No aggregation, no sampling: this is
the complete in/out record for each address from the token's deployment block
to head, which is what provenance claims have to rest on.

Usage: walk.py <addr[,addr,...]> [out_name]
Data-only.
"""
import json, sys, bisect, datetime
sys.path.insert(0, 'pipeline')
from probe import rpc

AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
LO, HI = 57_840_341, 114_777_002
STEP = 49_999

D  = 'pipeline/data/'
TS = json.load(open(D + 'blk_ts.json')); _tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]
CG = json.load(open(D + 'ake_daily_prices_cg.json')); _pk = sorted(CG)


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def px(d):
    return CG[d] if d in CG else CG[_pk[max(0, bisect.bisect_right(_pk, d) - 1)]]


def walk(a, lo=LO, hi=HI):
    a = a.lower(); pad = '0x' + '0' * 24 + a[2:]
    rows = []
    for pos in (1, 2):
        b = lo
        while b <= hi:
            e = min(b + STEP, hi)
            t = [TOPIC, None, None]; t[pos] = pad
            for L in rpc('eth_getLogs', [{'address': AKE, 'topics': t,
                                          'fromBlock': hex(b), 'toBlock': hex(e)}]):
                rows.append([int(L['blockNumber'], 16),
                             '0x' + L['topics'][1][-40:], '0x' + L['topics'][2][-40:],
                             str(int(L['data'], 16)), L['transactionHash'],
                             int(L['logIndex'], 16)])
            b = e + 1
    # a self-transfer would surface under both filters
    ded = {(r[0], r[5]): r for r in rows}
    return sorted(ded.values())


def main():
    addrs = [x.strip().lower() for x in sys.argv[1].split(',') if x.strip()]
    out = {}
    for a in addrs:
        rows = walk(a)
        out[a] = rows
        tin = sum(int(r[3]) for r in rows if r[2] == a)
        tout = sum(int(r[3]) for r in rows if r[1] == a)
        print(f'\n=== {a} ===  {len(rows)} transfers   '
              f'IN {tin/1e24:,.1f}mn   OUT {tout/1e24:,.1f}mn   NET {(tin-tout)/1e24:+,.1f}mn')
        for bn, f, t, v, tx, li in rows[:80]:
            d = bd(bn); vv = int(v)
            arrow = 'IN  <-' if t == a else 'OUT ->'
            other = f if t == a else t
            print(f'  {d}  blk {bn:>11,}  {arrow} {other}  {vv/1e24:>10,.2f}mn  '
                  f'${vv/1e18*px(d):>12,.0f}  {tx}')
        if len(rows) > 80:
            print(f'  ... {len(rows)-80} more')
    if len(sys.argv) > 2:
        json.dump(out, open(D + sys.argv[2] + '.json', 'w'))
        print('\nwrote', D + sys.argv[2] + '.json')


if __name__ == '__main__':
    main()
