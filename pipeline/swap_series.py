#!/usr/bin/env python3
"""
Build a bucketed price / volume / net-flow / liquidity series for one V3 pool
straight from its Swap events.

Transfer logs say how much AKE moved; only the Swap event says at what price,
in which direction, and against how much active liquidity. Bucketing keeps the
output small enough to hold a multi-day window while still resolving a
five-minute break.

Per bucket: open/high/low/close price, AKE sold in, AKE bought out, BNB in,
BNB out, swap count, min/max active liquidity, and the largest single swap.

Usage: swap_series.py <pool> <from> <to> <ckpt_name> [bucket_seconds]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, os, sys, datetime, bisect, collections

RPC  = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
# PancakeV3 Swap(address,address,int256,int256,uint160,uint128,int24,uint128,uint128)
SWAP_PCS  = '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83'
# UniswapV3 Swap(address,address,int256,int256,uint160,uint128,int24)
SWAP_UNI  = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'

POOL = sys.argv[1].lower()
A    = int(sys.argv[2])
B    = int(sys.argv[3])
CKPT = 'pipeline/data/%s.json' % sys.argv[4]
BUCK = int(sys.argv[5]) if len(sys.argv) > 5 else 900
STEP = 9_999

TS  = json.load(open('pipeline/data/blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    if i == 0:
        return _tv[0]
    if i >= len(_tb):
        return _tv[-1]
    return _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=14):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=200).read())
            if 'error' in j:
                msg = str(j['error'])
                if 'exceeds the limit' in msg or 'query returned more than' in msg:
                    raise TooManyLogs(msg)
                raise RuntimeError(msg)
            return j['result']
        except TooManyLogs:
            raise
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 1.5 * (1.8 ** i)))


def get(frm, to):
    try:
        return rpc('eth_getLogs', [{'address': POOL, 'topics': [[SWAP_PCS, SWAP_UNI]],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get(frm, mid) + get(mid + 1, to)


def s256(x):
    return x - (1 << 256) if x >= (1 << 255) else x


def blank():
    # o h l c  sold_in bought_out bnb_in bnb_out  n  liq_lo liq_hi  big_amt big_blk big_side
    return [None, 0.0, 0.0, None, 0, 0, 0, 0, 0, None, 0, 0, 0, '']


def main():
    buck = {}
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('pool') == POOL and c.get('from') == A and c.get('to') == B:
            buck = {int(k): v for k, v in c['buckets'].items()}
            start = c['last_block'] + 1
            print('resume at %d' % start, flush=True)

    print('swap series %s  %d -> %d  bucket=%ds' % (POOL, A, B, BUCK), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        for L in get(b, e):
            d = L['data'][2:]
            w = [d[i*64:(i+1)*64] for i in range(len(d) // 64)]
            a0 = s256(int(w[0], 16))
            a1 = s256(int(w[1], 16))
            sp = int(w[2], 16)
            liq = int(w[3], 16)
            bn = int(L['blockNumber'], 16)
            px = (sp / 2**96) ** 2
            k = int(bts(bn)) // BUCK * BUCK
            q = buck.setdefault(k, blank())
            if q[0] is None:
                q[0] = px; q[1] = px; q[2] = px
            q[1] = max(q[1], px); q[2] = min(q[2], px); q[3] = px
            if a0 > 0:
                q[4] += a0; q[7] += -a1          # AKE in, BNB out
            else:
                q[5] += -a0; q[6] += a1          # AKE out, BNB in
            q[8] += 1
            q[9] = liq if q[9] is None else min(q[9], liq)
            q[10] = max(q[10], liq)
            if abs(a0) > q[11]:
                q[11] = abs(a0); q[12] = bn; q[13] = 'sell' if a0 > 0 else 'buy'

        json.dump({'pool': POOL, 'from': A, 'to': B, 'last_block': e, 'bucket': BUCK,
                   'buckets': {str(k): [v[0], v[1], v[2], v[3], str(v[4]), str(v[5]),
                                        str(v[6]), str(v[7]), v[8], v[9], v[10],
                                        str(v[11]), v[12], v[13]]
                               for k, v in buck.items()},
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT, 'w'))
        print('%d-%d (%.1f%%) buckets=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(buck)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
