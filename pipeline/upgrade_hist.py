#!/usr/bin/env python3
"""
Every ERC1967 Upgraded(address) event for a proxy, over its whole life.

Answers the question "is the vesting schedule enforced by the contract, and
is the contract being rewritten to change it" - because if the schedule lived
in immutable code, the implementation would never need to change; and if it
lives in storage, an upgrade is not needed to alter it either. The pattern of
upgrades is the evidence.

Usage: upgrade_hist.py <proxy> <from> <to> [out_name]
Data-only.
"""
import json, sys, bisect, datetime, urllib.request, time

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
UPGRADED = '0xbc7cd75a20ee27fd9adebab32041f755214dbc6bffa90cc0225b39da2e5c2d3b'
STEP = 49_999

D = 'pipeline/data/'
TS = json.load(open(D + 'blk_ts.json')); _tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]


def rpc(m, p, tries=12):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def bdt(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S')


def main():
    proxy = sys.argv[1].lower()
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    out = []
    b = lo
    while b <= hi:
        e = min(b + STEP, hi)
        for L in rpc('eth_getLogs', [{'address': proxy, 'topics': [UPGRADED],
                                      'fromBlock': hex(b), 'toBlock': hex(e)}]):
            bn = int(L['blockNumber'], 16)
            impl = '0x' + L['topics'][1][-40:]
            out.append([bn, bdt(bn), impl, L['transactionHash']])
        b = e + 1
    print(f'{len(out)} implementation changes on {proxy}\n')
    prev = None
    for bn, d, impl, tx in out:
        gap = ''
        if prev:
            secs = int((datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S') -
                        datetime.datetime.strptime(prev, '%Y-%m-%d %H:%M:%S')).total_seconds())
            gap = f'   (+{secs//86400}d {secs%86400//3600}h)' if secs >= 3600 else f'   (+{secs}s)'
        print(f'  {d}  blk {bn:>12,}  -> {impl}{gap}')
        print(f'      tx {tx}')
        prev = d
    if len(sys.argv) > 4:
        json.dump(out, open(D + sys.argv[4] + '.json', 'w'), indent=1)
        print('\nwrote', D + sys.argv[4] + '.json')


if __name__ == '__main__':
    main()
