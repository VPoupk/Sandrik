#!/usr/bin/env python3
"""
Who actually sold into / bought out of a V3 pool.

The Swap event's sender/recipient are routers, so they name the aggregator, not
the trader. The AKE Transfer legs do name the trader: in a V3 swap the pay
callback moves the token straight from the payer to the pool, so
Transfer(from=X, to=pool) is X selling, and Transfer(from=pool, to=X) is X
buying.

Aggregates per counterparty, and keeps a per-day total plus the largest single
transfers so a big one-off can be traced back to its tx.

Usage: xferpool.py <pool> <from> <to> <ckpt_name>
Writes only to pipeline/data/<ckpt_name>.json
"""
import json, urllib.request, time, os, sys, datetime, bisect, collections

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TRANSFER = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

BASE = '/home/user/Sandrik'
POOL = sys.argv[1].lower()
A    = int(sys.argv[2])
B    = int(sys.argv[3])
CKPT = os.path.join(BASE, 'pipeline/data/%s.json' % sys.argv[4])
STEP = 49_999

TS = json.load(open(os.path.join(BASE, 'pipeline/data/blk_ts.json')))
_tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    if i == 0:
        return _tv[0]
    if i >= len(_tb):
        return _tv[-1] + (bn - _tb[-1]) * 0.75
    return _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])


def day(bn):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime('%Y-%m-%d')


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=14):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=240).read())
            if 'error' in j:
                msg = str(j['error'])
                if ('exceeds the limit' in msg or 'query returned more than' in msg
                        or 'TooManyLogs' in msg or 'too many logs' in msg.lower()):
                    raise TooManyLogs(msg)
                raise RuntimeError(msg)
            return j['result']
        except TooManyLogs:
            raise
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 1.5 * (1.8 ** i)))


def topic_addr(a):
    return '0x' + a[2:].lower().rjust(64, '0')


def get(frm, to, topics):
    try:
        return rpc('eth_getLogs', [{'address': AKE, 'topics': topics,
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get(frm, mid, topics) + get(mid + 1, to, topics)


def main():
    sell = collections.Counter()   # addr -> wei sold into pool
    buy  = collections.Counter()   # addr -> wei bought out of pool
    nsell = collections.Counter()
    nbuy = collections.Counter()
    first_seen, last_seen = {}, {}
    daily = {}                     # day -> [in_wei, out_wei, n_in, n_out]
    big = []                       # largest single transfers either way
    start = A

    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('pool') == POOL and c.get('from') == A and c.get('to') == B:
            sell = collections.Counter({k: int(v) for k, v in c['sell'].items()})
            buy = collections.Counter({k: int(v) for k, v in c['buy'].items()})
            nsell = collections.Counter(c['nsell'])
            nbuy = collections.Counter(c['nbuy'])
            first_seen = c.get('first_seen', {})
            last_seen = c.get('last_seen', {})
            daily = {k: [int(v[0]), int(v[1]), v[2], v[3]]
                     for k, v in c['daily'].items()}
            big = c.get('big', [])
            start = c['last_block'] + 1
            print('resume at %d (%d sellers)' % (start, len(sell)), flush=True)

    print('xferpool %s %d -> %d' % (POOL, A, B), flush=True)
    PT = topic_addr(POOL)
    b = start
    t0 = time.time()
    while b <= B:
        e = min(b + STEP, B)
        # into the pool  = somebody selling
        for L in get(b, e, [TRANSFER, None, PT]):
            frm = '0x' + L['topics'][1][-40:]
            v = int(L['data'], 16)
            bn = int(L['blockNumber'], 16)
            sell[frm] += v
            nsell[frm] += 1
            first_seen.setdefault(frm, bn)
            last_seen[frm] = bn
            d = daily.setdefault(day(bn), [0, 0, 0, 0])
            d[0] += v; d[2] += 1
            if v > 20_000_000 * 10**18:
                big.append(['in', bn, L['transactionHash'], frm, str(v)])
        # out of the pool = somebody buying
        for L in get(b, e, [TRANSFER, PT, None]):
            to = '0x' + L['topics'][2][-40:]
            v = int(L['data'], 16)
            bn = int(L['blockNumber'], 16)
            buy[to] += v
            nbuy[to] += 1
            d = daily.setdefault(day(bn), [0, 0, 0, 0])
            d[1] += v; d[3] += 1
            if v > 20_000_000 * 10**18:
                big.append(['out', bn, L['transactionHash'], to, str(v)])

        json.dump({'pool': POOL, 'from': A, 'to': B, 'last_block': e,
                   'sell': {k: str(v) for k, v in sell.items()},
                   'buy': {k: str(v) for k, v in buy.items()},
                   'nsell': dict(nsell), 'nbuy': dict(nbuy),
                   'first_seen': first_seen, 'last_seen': last_seen,
                   'daily': {k: [str(v[0]), str(v[1]), v[2], v[3]]
                             for k, v in daily.items()},
                   'big': big,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        pct = 100.0 * (e - A + 1) / (B - A + 1)
        el = time.time() - t0
        print('%d-%d (%.1f%%) sellers=%d buyers=%d el=%.0fs eta=%.0fs' %
              (b, e, pct, len(sell), len(buy), el,
               el * (100 - pct) / max(pct, 0.01)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
