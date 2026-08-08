#!/usr/bin/env python3
"""
Read balanceOf(AKE) at a fixed block for a list of addresses. This is the
authoritative "held" number — it cannot be gamed by routing, and it is the
denominator every flow figure in the report is reconciled against.

Usage: balances_head.py <addr-list.json> <out_name> [block]
Data-only.
"""
import json, sys, os, time
sys.path.insert(0, 'pipeline')
from probe import rpc

AKE  = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
HEAD = int(sys.argv[3]) if len(sys.argv) > 3 else 114_777_002
OUT  = 'pipeline/data/%s.json' % sys.argv[2]

d = json.load(open(sys.argv[1]))
addrs = list(d) if isinstance(d, dict) else list(d)

res = json.load(open(OUT)) if os.path.exists(OUT) else {}
for i, a in enumerate(addrs):
    a = a.lower()
    if a in res:
        continue
    r = rpc('eth_call', [{'to': AKE,
                          'data': '0x70a08231' + a[2:].rjust(64, '0')}, hex(HEAD)])
    res[a] = str(int(r, 16))
    if i % 25 == 0:
        json.dump(res, open(OUT, 'w'))
        print(f'{i}/{len(addrs)}', flush=True)
json.dump(res, open(OUT, 'w'))
print('wrote', OUT, len(res), 'balances at block', f'{HEAD:,}')
