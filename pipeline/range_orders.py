#!/usr/bin/env python3
"""
Find every single-sided V3 liquidity position ever opened on a pool.

A Uniswap/Pancake V3 position funded with only token0 and no token1 is a
limit sell: the range sits entirely above spot, and as price rises through
it the token is sold for the quote asset. The reverse - only token1 - is a
limit buy. Neither ever appears as a transfer to an exchange, so a
transfer-based sales ledger misses them completely. This is the channel
that finds them.

Emits every Mint whose AKE leg exceeds the threshold, tagged BID / ASK /
TWO-SIDED, with the tick range converted to a price so the intended fill
level is readable.

Usage: range_orders.py <pool> <from> <to> <ckpt_name> [min_mn]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, os, sys, datetime, math

RPC  = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
MINT = '0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'

POOL = sys.argv[1].lower()
A    = int(sys.argv[2])
B    = int(sys.argv[3])
CKPT = 'pipeline/data/%s.json' % sys.argv[4]
MIN  = int(float(sys.argv[5]) * 1e6 * 10**18) if len(sys.argv) > 5 else 10**6 * 10**18
STEP = 49_999


def rpc(m, p, tries=14):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=200).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 1.5 * (1.8 ** i)))


def t24(x):
    x &= 0xffffff
    return x - (1 << 24) if x >= (1 << 23) else x


def main():
    out = []
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('pool') == POOL and c.get('from') == A and c.get('to') == B:
            out = c['rows']
            start = c['last_block'] + 1
            print('resume at %d' % start, flush=True)

    print('range orders %s  %d -> %d  min %.2fmn' % (POOL, A, B, MIN / 1e24), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        for L in rpc('eth_getLogs', [{'address': POOL, 'topics': [MINT],
                                      'fromBlock': hex(b), 'toBlock': hex(e)}]):
            d = L['data'][2:]
            w = [d[i*64:(i+1)*64] for i in range(len(d) // 64)]
            a0 = int(w[2], 16)          # AKE
            a1 = int(w[3], 16)          # WBNB
            if a0 < MIN:
                continue
            out.append([int(L['blockNumber'], 16), t24(int(L['topics'][2], 16)),
                        t24(int(L['topics'][3], 16)), str(int(w[1], 16)),
                        str(a0), str(a1), L['transactionHash']])

        json.dump({'pool': POOL, 'from': A, 'to': B, 'last_block': e, 'rows': out,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT, 'w'))
        print('%d-%d (%.1f%%) rows=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(out)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
