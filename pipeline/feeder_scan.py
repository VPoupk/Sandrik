#!/usr/bin/env python3
"""Every AKE transfer OUT of the five Alpha Feeder aggregators across the
April-2026 burst window, dated and priced. Data-only."""
import json, urllib.request, time, os, datetime, bisect, collections

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ALPHA = '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db'
A, B  = 90_500_000, 101_000_000
CKPT  = 'pipeline/data/feeder_scan_checkpoint.json'
pad = lambda a: '0x' + '0' * 24 + a[2:]

FEED = {
    '0xb40b35fe21be75f6e5c0b7dabab1ec87d87a1395': 'Alpha Feeder A',
    '0xb50de384e012a5f0fd80c4ce85bb6e679256f25c': 'Alpha Feeder B',
    '0xd49ef7def42f4633cd55cb874e016a570ea99f04': 'Alpha Feeder C',
    '0xcfb02194256652c650a02290804456e34e619daa': 'Alpha Feeder D',
    '0x6449b24d8dad7cef8ece12d7d5c8d0e0ef355a48': 'Alpha Feeder E',
}


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def scan():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT)); frm, rows = st['last_block'] + 1, st['rows']
    else:
        frm, rows = A, []
    while frm <= B:
        to = min(frm + 49999, B)
        for lg in rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                                       'toBlock': hex(to),
                                       'topics': [TOPIC, [pad(a) for a in FEED]]}]):
            rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                         '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16))])
        json.dump({'last_block': to, 'rows': rows}, open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        frm = to + 1
    print(f'scan done, {len(rows)} transfers', flush=True)
    return rows


def report(rows):
    CG = json.load(open('pipeline/data/ake_daily_prices_cg.json')); pk = sorted(CG)
    TS = json.load(open('pipeline/data/blk_ts.json'))
    tb = sorted(int(k) for k in TS); tv = [TS[str(x)] for x in tb]

    def bd(bn):
        i = bisect.bisect_left(tb, bn)
        t = tv[0] if i == 0 else (tv[-1] if i >= len(tb) else
                                  tv[i-1] + (tv[i]-tv[i-1]) * (bn-tb[i-1]) / (tb[i]-tb[i-1]))
        return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')

    def px(x):
        return CG[x] if x in CG else CG[pk[max(0, bisect.bisect_right(pk, x) - 1)]]

    print(f'\n{"date":12}{"feeder":16}{"destination":24}{"AKE":>12}{"price":>13}{"$ that day":>14}')
    agg = collections.Counter(); aggu = collections.Counter()
    dts = collections.defaultdict(list); tot = totu = 0
    for bn, s, t, v in sorted(rows):
        v = int(v) / 1e18; dt = bd(bn); p = px(dt); u = v * p
        dest = 'Binance Alpha 2.0' if t == ALPHA else t[:14] + '…'
        print(f'{dt:12}{FEED[s]:16}{dest:24}{v/1e6:11.1f}mn{p:>13.8f}{u:>14,.0f}')
        if t == ALPHA:
            tot += v; totu += u; agg[FEED[s]] += v; aggu[FEED[s]] += u; dts[FEED[s]].append(dt)
    print(f'\n{"feeder":16}{"AKE into Alpha":>17}{"$ at transfer dates":>21}   window')
    for k, v in agg.most_common():
        print(f'{k:16}{v/1e9:16.3f}bn{aggu[k]:>20,.0f}   {min(dts[k])} → {max(dts[k])}')
    print(f'{"TOTAL":16}{tot/1e9:16.3f}bn{totu:>20,.0f}')
    json.dump({k: [agg[k], aggu[k], min(dts[k]), max(dts[k])] for k in agg},
              open('pipeline/data/feeder_alpha_priced.json', 'w'), indent=1)


if __name__ == '__main__':
    report(scan())
