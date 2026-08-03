#!/usr/bin/env python3
"""
Find the first BNB credit to an address even when its balance is zero at both
ends of the search range (the case the simpler tracer misses). Binary-searches
for the first block where the balance differs from the starting balance, then
reads that block's transactions. Data-only.
"""
import json, urllib.request, time, sys, datetime

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
LO = 57_000_000


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=150).read())
            if 'error' in r:
                raise RuntimeError(r['error'])
            return r['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def bal(a, b):
    return int(rpc('eth_getBalance', [a, hex(b)]), 16)


def main():
    addrs = json.load(open(sys.argv[1]))
    head = int(rpc('eth_blockNumber', []), 16)
    out = {}
    for a in addrs:
        try:
            b0 = bal(a, LO)
            if bal(a, head) == b0:
                # balance never differs from the start at the endpoints; probe
                # a mid grid to catch a rise-and-fall
                found = None
                for probe in range(LO, head, (head - LO) // 40):
                    if bal(a, probe) != b0:
                        found = probe
                        break
                if found is None:
                    out[a] = {'err': 'no balance change detected on a 40-point grid'}
                    print(f'{a}  no change detected', flush=True)
                    continue
                hi = found
            else:
                hi = head
            lo = LO
            while lo < hi:
                mid = (lo + hi) // 2
                if bal(a, mid) == b0:
                    lo = mid + 1
                else:
                    hi = mid
            blk = rpc('eth_getBlockByNumber', [hex(lo), True])
            hits = [t for t in blk['transactions']
                    if (t.get('to') or '').lower() == a and int(t['value'], 16) > 0]
            ts = int(blk['timestamp'], 16)
            out[a] = {'block': lo, 'ts': ts,
                      'date': datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M'),
                      'funders': [{'from': t['from'], 'bnb': int(t['value'], 16) / 1e18,
                                   'hash': t['hash']} for t in hits]}
            f = ', '.join(f"{h['from']} {h['bnb']:.4f} BNB" for h in out[a]['funders']) \
                or '(internal / contract call)'
            print(f'{a}  blk {lo}  {out[a]["date"]}  <- {f}', flush=True)
        except Exception as e:
            out[a] = {'err': str(e)}
            print(f'{a}  ERR {e}', flush=True)
        json.dump(out, open(sys.argv[2], 'w'), indent=1)


if __name__ == '__main__':
    main()
