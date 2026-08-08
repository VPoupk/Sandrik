#!/usr/bin/env python3
"""Small resilient RPC helper used for one-off address probes. Data-only."""
import json, urllib.request, time

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'


def rpc(m, p, tries=15):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 2 * (1.7 ** i)))


def code(a, blk='latest'):
    return rpc('eth_getCode', [a, blk])


def bal(a, blk='latest'):
    return int(rpc('eth_getBalance', [a, hex(blk) if isinstance(blk, int) else blk]), 16)


def first_funded(a, lo, hi):
    """binary-search the first block where BNB balance differs from the start"""
    b0 = bal(a, lo)
    if bal(a, hi) == b0:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if bal(a, mid) != b0:
            hi = mid
        else:
            lo = mid + 1
    return lo


def funder(a, blk):
    b = rpc('eth_getBlockByNumber', [hex(blk), True])
    out = []
    for t in b['transactions']:
        if (t.get('to') or '').lower() == a.lower():
            out.append((t['from'], int(t['value'], 16) / 1e18, t['hash']))
    return out
