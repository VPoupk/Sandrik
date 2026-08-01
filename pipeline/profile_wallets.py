#!/usr/bin/env python3
"""Profile addresses: EOA/contract, tx nonce, BNB balance, AKE balance,
first funding tx (BNB source) via first inbound transaction. Data-only."""
import json, urllib.request, time, sys

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'


def batch(calls, tries=6):
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
out = {}
for i in range(0, len(addrs), 12):
    grp = addrs[i:i + 12]
    calls = []
    for j, a in enumerate(grp):
        calls += [
            {'jsonrpc': '2.0', 'id': f'{j}:nonce', 'method': 'eth_getTransactionCount', 'params': [a, 'latest']},
            {'jsonrpc': '2.0', 'id': f'{j}:code',  'method': 'eth_getCode',             'params': [a, 'latest']},
            {'jsonrpc': '2.0', 'id': f'{j}:bnb',   'method': 'eth_getBalance',          'params': [a, 'latest']},
            {'jsonrpc': '2.0', 'id': f'{j}:ake',   'method': 'eth_call',
             'params': [{'to': AKE, 'data': '0x70a08231' + '0' * 24 + a[2:]}, 'latest']},
        ]
    res = batch(calls)
    by = {r['id']: r.get('result') for r in res}
    for j, a in enumerate(grp):
        code = by.get(f'{j}:code') or '0x'
        out[a] = {
            'nonce': int(by[f'{j}:nonce'], 16) if by.get(f'{j}:nonce') else None,
            'is_contract': len(code) > 2,
            'code_len': (len(code) - 2) // 2,
            'bnb': int(by[f'{j}:bnb'], 16) / 1e18 if by.get(f'{j}:bnb') else None,
            'ake': int(by[f'{j}:ake'], 16) / 1e18 if by.get(f'{j}:ake') else None,
        }
    time.sleep(0.15)

json.dump(out, open(sys.argv[2], 'w'), indent=1)
for a, p in out.items():
    print(f"{a}  nonce={p['nonce']:<7} {'CONTRACT' if p['is_contract'] else 'EOA':9}"
          f" bnb={p['bnb']:.4f}  ake={(p['ake'] or 0)/1e6:.1f}M")
