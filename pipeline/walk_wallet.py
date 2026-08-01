#!/usr/bin/env python3
"""Walk an address's AKE balance history by repeated binary search, printing
every block at which its balance changed and the transfers in that block.
Data-only. Usage: walk_wallet.py <addr> <from_block> [max_steps]"""
import json, urllib.request, time, sys, datetime

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
cur = int(sys.argv[2])
steps = int(sys.argv[3]) if len(sys.argv) > 3 else 12
head = int(rpc('eth_blockNumber', []), 16)

for _ in range(steps):
    b0 = bal(a, cur)
    if bal(a, head) == b0:
        print(f'  (no further change; balance stays {b0/1e18:,.0f})')
        break
    L, H = cur + 1, head
    while L < H:
        mid = (L + H) // 2
        if bal(a, mid) == b0:
            L = mid + 1
        else:
            H = mid
    logs = rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                                'fromBlock': hex(L), 'toBlock': hex(L)}])
    blk = rpc('eth_getBlockByNumber', [hex(L), False])
    dt = datetime.datetime.utcfromtimestamp(int(blk['timestamp'], 16)).strftime('%Y-%m-%d %H:%M')
    print(f'blk {L}  {dt}   (balance was {b0/1e18:,.0f})', flush=True)
    for lg in logs:
        s = '0x' + lg['topics'][1][-40:]
        d = '0x' + lg['topics'][2][-40:]
        v = int(lg['data'], 16) / 1e18
        if s == a or d == a:
            arrow = 'OUT ->' if s == a else 'IN  <-'
            other = d if s == a else s
            print(f'   {arrow} {other}  {v:,.0f} AKE')
    cur = L
