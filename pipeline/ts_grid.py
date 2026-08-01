#!/usr/bin/env python3
"""Timestamp grid every 25k blocks over the full AKE history, via batched RPC.
Used to map any block -> UTC date by linear interpolation (error << 1 block).
Data-only."""
import json, urllib.request, time, os

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
OUT = 'pipeline/data/ts_grid.json'
STEP = 25_000
START = 57_800_000


def batch(calls, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps(calls).encode(),
                headers={'Content-Type': 'application/json'})
            return json.loads(urllib.request.urlopen(req, timeout=120).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (2 ** i))


def main():
    head = int(json.loads(urllib.request.urlopen(urllib.request.Request(
        RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                              'method': 'eth_blockNumber', 'params': []}).encode(),
        headers={'Content-Type': 'application/json'}), timeout=60).read())['result'], 16)

    grid = json.load(open(OUT)) if os.path.exists(OUT) else {}
    blocks = list(range(START, head, STEP)) + [head]
    todo = [b for b in blocks if str(b) not in grid]
    print('grid points to fetch:', len(todo), 'head', head, flush=True)

    B = 50
    for i in range(0, len(todo), B):
        grp = todo[i:i + B]
        calls = [{'jsonrpc': '2.0', 'id': j, 'method': 'eth_getBlockByNumber',
                  'params': [hex(b), False]} for j, b in enumerate(grp)]
        res = batch(calls)
        by = {r['id']: r for r in res}
        for j, b in enumerate(grp):
            r = by.get(j, {})
            if r.get('result'):
                grid[str(b)] = int(r['result']['timestamp'], 16)
        json.dump(grid, open(OUT + '.tmp', 'w'))
        os.replace(OUT + '.tmp', OUT)
        if i % (B * 5) == 0:
            print(f'{i+len(grp)}/{len(todo)}', flush=True)
        time.sleep(0.1)
    print('DONE points=', len(grid), flush=True)


if __name__ == '__main__':
    main()
