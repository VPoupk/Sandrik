#!/usr/bin/env python3
"""
Find the BNB gas funder of an EOA using only standard archive RPC:
  1. binary-search eth_getBalance to find the first block where balance > 0
  2. fetch that block's full transactions and find the tx that credited it
Direct on-chain verification -- does not rely on any explorer label. Data-only.
"""
import json, urllib.request, time, sys

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
LO, HI = 57_000_000, None


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
            time.sleep(min(60, 2 * (1.7 ** i)))


def bal(a, b):
    return int(rpc('eth_getBalance', [a, hex(b)]), 16)


def first_funded_block(a, lo, hi):
    if bal(a, hi) == 0 and bal(a, lo) == 0:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if bal(a, mid) == 0:
            lo = mid + 1
        else:
            hi = mid
    return lo


def main():
    addrs = json.load(open(sys.argv[1]))
    head = int(rpc('eth_blockNumber', []), 16)
    out = {}
    for a in addrs:
        try:
            b = first_funded_block(a, LO, head)
            if b is None:
                out[a] = {'err': 'never funded / zero at head'}
                print(a, 'never funded', flush=True)
                continue
            blk = rpc('eth_getBlockByNumber', [hex(b), True])
            hits = [t for t in blk['transactions']
                    if (t.get('to') or '').lower() == a and int(t['value'], 16) > 0]
            out[a] = {'block': b,
                      'ts': int(blk['timestamp'], 16),
                      'funders': [{'from': t['from'],
                                   'bnb': int(t['value'], 16) / 1e18,
                                   'hash': t['hash']} for t in hits]}
            f = ', '.join(f"{h['from']} {h['bnb']:.4f} BNB" for h in out[a]['funders']) or '(internal tx)'
            print(f'{a}  blk {b}  <- {f}', flush=True)
        except Exception as e:
            out[a] = {'err': str(e)}
            print(a, 'ERR', e, flush=True)
        json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
