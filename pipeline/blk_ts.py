#!/usr/bin/env python3
"""Exact UTC timestamp for a specific list of blocks (batched). Data-only.
Usage: blk_ts.py <blocks.json> <out.json>"""
import json, urllib.request, time, sys, os

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'


def batch(calls, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps(calls).encode(),
                headers={'Content-Type': 'application/json'})
            return json.loads(urllib.request.urlopen(req, timeout=150).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 2 * (1.7 ** i)))


blocks = sorted(set(int(b) for b in json.load(open(sys.argv[1]))))
out = json.load(open(sys.argv[2])) if os.path.exists(sys.argv[2]) else {}
todo = [b for b in blocks if str(b) not in out]
print('fetch', len(todo), 'of', len(blocks), flush=True)
B = 60
for i in range(0, len(todo), B):
    grp = todo[i:i + B]
    res = batch([{'jsonrpc': '2.0', 'id': j, 'method': 'eth_getBlockByNumber',
                  'params': [hex(b), False]} for j, b in enumerate(grp)])
    by = {r['id']: r.get('result') for r in res}
    for j, b in enumerate(grp):
        if by.get(j):
            out[str(b)] = int(by[j]['timestamp'], 16)
    json.dump(out, open(sys.argv[2], 'w'))
    time.sleep(0.1)
print('done', len(out), flush=True)
