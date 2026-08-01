#!/usr/bin/env python3
"""Exact first-block-of-each-UTC-day index for the analysis window.
Binary search on eth_getBlockByNumber timestamps. Data-only."""
import json, urllib.request, time, datetime, os

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
OUT = 'pipeline/data/day_first_block.json'
cache = {}


def rpc(m, p, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=60).read())
            if 'error' in r:
                raise RuntimeError(r['error'])
            return r['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.2 * (2 ** i))


def ts(bn):
    if bn not in cache:
        b = rpc('eth_getBlockByNumber', [hex(bn), False])
        cache[bn] = int(b['timestamp'], 16)
    return cache[bn]


def first_block_at_or_after(target_ts, lo, hi):
    while lo < hi:
        mid = (lo + hi) // 2
        if ts(mid) < target_ts:
            lo = mid + 1
        else:
            hi = mid
    return lo


def main():
    head = int(rpc('eth_blockNumber', []), 16)
    idx = json.load(open(OUT)) if os.path.exists(OUT) else {}
    lo_anchor = 57_840_000
    d = datetime.date(2025, 8, 16)
    end = datetime.datetime.utcfromtimestamp(ts(head)).date()
    lo = lo_anchor
    while d <= end:
        k = str(d)
        if k in idx:
            lo = idx[k]
        else:
            tgt = int(datetime.datetime(d.year, d.month, d.day,
                                        tzinfo=datetime.timezone.utc).timestamp())
            b = first_block_at_or_after(tgt, lo, head)
            idx[k] = b
            lo = b
            json.dump(idx, open(OUT, 'w'), indent=0)
            print(k, b, flush=True)
        d += datetime.timedelta(days=1)
    idx['_head'] = head
    json.dump(idx, open(OUT, 'w'), indent=0)
    print('days indexed:', len(idx) - 1)


if __name__ == '__main__':
    main()
