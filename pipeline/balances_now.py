#!/usr/bin/env python3
"""balanceOf(AKE) for every watchlist address at chain head. Data-only."""
import json, urllib.request, time, sys

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'


def rpc_batch(calls, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps(calls).encode(),
                headers={'Content-Type': 'application/json'})
            return json.loads(urllib.request.urlopen(req, timeout=90).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (2 ** i))


addrs = json.load(open(sys.argv[1]))
blk = sys.argv[2] if len(sys.argv) > 2 else 'latest'
out = {}
B = 40
for i in range(0, len(addrs), B):
    grp = addrs[i:i + B]
    calls = [{'jsonrpc': '2.0', 'id': j, 'method': 'eth_call',
              'params': [{'to': AKE, 'data': '0x70a08231' + '0' * 24 + a[2:]}, blk]}
             for j, a in enumerate(grp)]
    res = rpc_batch(calls)
    by = {r['id']: r for r in res}
    for j, a in enumerate(grp):
        r = by.get(j, {})
        out[a] = int(r['result'], 16) / 1e18 if r.get('result') else None
    time.sleep(0.15)
    print(f'{i+len(grp)}/{len(addrs)}', file=sys.stderr)

json.dump(out, open(sys.argv[3] if len(sys.argv) > 3 else
                    'pipeline/data/balances_now.json', 'w'), indent=1)
print('ok', len(out))
