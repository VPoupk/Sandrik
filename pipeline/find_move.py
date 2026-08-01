#!/usr/bin/env python3
"""Binary-search an address's AKE balance to find the block where it changed,
then read that block's AKE Transfer logs. Settles 'who sent what to whom'
without scanning millions of blocks. Data-only.
Usage: find_move.py <addr> [lo] [hi]"""
import json, urllib.request, time, sys

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            if 'error' in r:
                raise RuntimeError(r['error'])
            return r['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(45, 1.5 * (1.7 ** i)))


def bal(a, b):
    r = rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0' * 24 + a[2:]}, hex(b)])
    return int(r, 16) if r and r != '0x' else 0


a = sys.argv[1].lower()
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 57_840_000
hi = int(sys.argv[3]) if len(sys.argv) > 3 else int(rpc('eth_blockNumber', []), 16)
b_lo, b_hi = bal(a, lo), bal(a, hi)
print(f'{a}\n  balance @{lo} = {b_lo/1e18:,.0f}\n  balance @{hi} = {b_hi/1e18:,.0f}', flush=True)

# find first block where balance differs from b_lo
L, H = lo, hi
while L < H:
    mid = (L + H) // 2
    if bal(a, mid) == b_lo:
        L = mid + 1
    else:
        H = mid
print(f'  first change at block {L}', flush=True)

logs = rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                            'fromBlock': hex(L), 'toBlock': hex(L)}])
blk = rpc('eth_getBlockByNumber', [hex(L), False])
import datetime
print('  date', datetime.datetime.utcfromtimestamp(int(blk['timestamp'], 16)).isoformat())
for lg in logs:
    s = '0x' + lg['topics'][1][-40:]
    d = '0x' + lg['topics'][2][-40:]
    v = int(lg['data'], 16) / 1e18
    if s == a or d == a:
        print(f'  {s} -> {d}  {v:,.0f} AKE   tx {lg["transactionHash"]}')
