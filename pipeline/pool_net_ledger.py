#!/usr/bin/env python3
"""
The authoritative net ledger for the eight allocation pools, built from the
complete lifetime transfer record and reconciled against balanceOf at head.

Gross figures mislead. A pool that sends 4.0734bn and receives 2.0734bn back
within twenty-four minutes has released 2.0000bn, and quoting the 4.0734bn
overstates it by more than double. Every number this produces is therefore net,
and every pool is checked against the chain: allocation minus net released must
equal balanceOf exactly, or the script says so and refuses to be trusted.

Definitions used throughout, so there is no ambiguity about what "net" means:
  allocation    the funding transfer that created the pool's balance — the
                first inbound transfer, which in every case is the whole
                allocation in one move
  returned      any later inbound transfer, i.e. tokens sent back to the pool
  net released  (everything the pool ever sent) minus (everything returned)
  holds now     balanceOf(pool) at the head block

Per event day the same applies: net released that day is what left minus what
came back that day.

Usage: pool_net_ledger.py
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, glob, bisect, datetime, collections, urllib.request, time

D = 'pipeline/data/'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
SINCE = '2026-06-01'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

TS = json.load(open(D + 'blk_ts.json'))
_kb = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]


def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=120).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * 1.6 ** i)


def bts(bn):
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def bd(bn):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime('%Y-%m-%d')


def main():
    head = int(rpc('eth_blockNumber', []), 16)
    rows = []
    for f in sorted(glob.glob(D + 'poolflow_*.json')):
        rows.extend(json.load(open(f))['rows'])
    rows.sort()
    print(f'{len(rows):,} pool-touching transfers, lifetime\n')

    # per pool: funding transfer, everything out, everything returned
    fund, out, back = {}, collections.Counter(), collections.Counter()
    for bn, f, t, v, *_ in ((r[0], r[1].lower(), r[2].lower(), int(r[3])) for r in rows):
        if f in POOLS and t not in POOLS:
            out[POOLS[f]] += v
        if t in POOLS and f not in POOLS:
            n = POOLS[t]
            if n not in fund:
                fund[n] = {'block': bn, 'when': bd(bn), 'amount': v, 'from': f}
            else:
                back[n] += v

    bal = {}
    for a, n in POOLS.items():
        bal[n] = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + a[2:]},
                                      hex(head)]), 16)

    print('LIFETIME, NET — allocation minus net released must equal balanceOf\n')
    print(f"{'pool':<11}{'allocation':>14}{'sent ever':>14}{'returned':>13}"
          f"{'NET RELEASED':>15}{'holds now':>14}{'check':>8}")
    life = {}
    ok = True
    for n in ('Investors', 'Team 2', 'Team 1', 'Nodes 1', 'Nodes 2', 'Nodes 3',
              'KOL', 'Community'):
        alloc = fund[n]['amount']
        net = out[n] - back[n]
        chk = alloc - net - bal[n]
        ok &= (chk == 0)
        life[n] = {'allocation': str(alloc), 'sent_ever': str(out[n]),
                   'returned': str(back[n]), 'net_released': str(net),
                   'holds_now': str(bal[n]), 'reconciles': chk == 0,
                   'funded_on': fund[n]['when'], 'funded_by': fund[n]['from'],
                   'pct_released': 100.0 * net / alloc}
        print(f'{n:<11}{alloc/1e27:>11,.4f}bn{out[n]/1e27:>11,.4f}bn{back[n]/1e27:>10,.4f}bn'
              f'{net/1e27:>12,.4f}bn{bal[n]/1e27:>11,.4f}bn{"EXACT" if chk == 0 else chk:>8}')
    ta = sum(int(v['allocation']) for v in life.values())
    tn = sum(int(v['net_released']) for v in life.values())
    tb = sum(bal.values())
    print(f'{"TOTAL":<11}{ta/1e27:>11,.4f}bn{"":>14}{"":>13}{tn/1e27:>12,.4f}bn{tb/1e27:>11,.4f}bn'
          f'{"EXACT" if ta - tn - tb == 0 else ta - tn - tb:>8}')
    if not ok:
        print('\n!! a pool does not reconcile — do not use these figures')

    # per day, net, since SINCE
    day = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
    legs = collections.defaultdict(list)
    for r in rows:
        bn, f, t, v = r[0], r[1].lower(), r[2].lower(), int(r[3])
        d = bd(bn)
        if d < SINCE:
            continue
        if f in POOLS and t not in POOLS:
            day[d][POOLS[f]][0] += v
            legs[d].append([bn, int(bts(bn)), 'out', POOLS[f], t, str(v)])
        if t in POOLS and f not in POOLS:
            day[d][POOLS[t]][1] += v
            legs[d].append([bn, int(bts(bn)), 'back', POOLS[t], f, str(v)])

    print(f'\nNET RELEASED PER POOL PER DAY, since {SINCE}\n')
    print(f"{'day':<12}{'pool':<11}{'sent':>13}{'returned':>13}{'NET':>13}{'running net, that pool':>26}")
    run = collections.Counter()
    days = {}
    for d in sorted(day):
        tot = 0
        pp = {}
        for p, (o, i_) in sorted(day[d].items(), key=lambda x: -(x[1][0] - x[1][1])):
            net = o - i_
            if net == 0 and o == 0:
                continue
            run[p] += net
            tot += net
            pp[p] = {'sent': str(o), 'returned': str(i_), 'net': str(net),
                     'running_net_since': str(run[p])}
            print(f'{d:<12}{p:<11}{o/1e27:>10,.4f}bn{i_/1e27:>10,.4f}bn{net/1e27:>10,.4f}bn'
                  f'{run[p]/1e27:>23,.4f}bn')
        days[d] = {'by_pool': pp, 'net_total': str(tot), 'legs': sorted(legs[d])}
        print(f'{"":<12}{"day total":<11}{"":>13}{"":>13}{tot/1e27:>10,.4f}bn')
    print(f'\ntotal net released since {SINCE}: '
          f'{sum(int(v["net_total"]) for v in days.values())/1e27:,.4f}bn')

    json.dump({'head': head, 'since': SINCE, 'lifetime': life, 'days': days,
               'reconciles': ok},
              open(D + 'pool_net_ledger.json', 'w'), indent=1)
    print(f'\nwrote {D}pool_net_ledger.json')
    print('DONE')


if __name__ == '__main__':
    main()
