#!/usr/bin/env python3
"""
Generated from venue_scan.py (only the venue-registry path differs: it reads
venues_probe.json instead of venues_scan.json). Used to batch-scan an arbitrary
set of addresses in one pass - e.g. the 25 largest exchange depositors, to find
where their AKE came from - instead of walking each address separately.

Gap-free scan of every AKE Transfer that touches a known venue (DEX pool,
non-Binance CEX custody wallet, Binance wallet, or router/aggregator).

Uses topic-position filters (topic1 = from, topic2 = to) with an OR-list of the
venue addresses, so the node returns only venue-touching logs. Every log is
de-duplicated on (block, logIndex), so a transfer between two venues is counted
exactly once regardless of which filter surfaced it.

Aggregation, so checkpoints stay small and per-date pricing stays exact:
    agg[venue][counterparty][YYYY-MM-DD] = [in_wei, out_wei, in_ct, out_ct]
        in  = venue RECEIVED from counterparty
        out = venue SENT to counterparty
Plus every individual transfer >= BIG kept in full for citation.

Usage: venue_scan.py <from> <to> <ckpt_name> [big_mn]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, os, sys, datetime, bisect, collections

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

A    = int(sys.argv[1])
B    = int(sys.argv[2])
CKPT = 'pipeline/data/%s.json' % sys.argv[3]
BIG  = int(float(sys.argv[4]) * 1e6 * 10**18) if len(sys.argv) > 4 else 5_000_000 * 10**18
STEP = 49_999

VENUES = json.load(open('pipeline/data/venues_probe.json'))
VSET   = set(VENUES)
PAD    = ['0x' + '0' * 24 + a[2:] for a in sorted(VSET)]

TS  = json.load(open('pipeline/data/blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


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
    agg = collections.defaultdict(lambda: collections.defaultdict(
        lambda: collections.defaultdict(lambda: [0, 0, 0, 0])))
    big = []
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('from') == A and c.get('to') == B:
            for v, cp in c['agg'].items():
                for p, dd in cp.items():
                    for d, q in dd.items():
                        agg[v][p][d] = [int(q[0]), int(q[1]), q[2], q[3]]
            big = c['big']
            start = c['last_block'] + 1
            print('resume at %d' % start, flush=True)

    print('venue scan %d -> %d  (%d venues)' % (A, B, len(VSET)), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        seen = set()
        for pos in (1, 2):
            t = [TOPIC, None, None]
            t[pos] = PAD
            for L in get(b, e, t):
                key = (L['blockNumber'], L['logIndex'])
                if key in seen:
                    continue
                seen.add(key)
                bn = int(L['blockNumber'], 16)
                f  = '0x' + L['topics'][1][-40:]
                d  = '0x' + L['topics'][2][-40:]
                v  = int(L['data'], 16)
                day = bd(bn)
                if d in VSET:                       # venue received
                    q = agg[d][f][day]; q[0] += v; q[2] += 1
                if f in VSET:                       # venue sent
                    q = agg[f][d][day]; q[1] += v; q[3] += 1
                if v >= BIG:
                    big.append([bn, f, d, str(v), L['transactionHash']])

        json.dump({'job': sys.argv[3], 'from': A, 'to': B, 'last_block': e,
                   'agg': {v: {p: {d: [str(q[0]), str(q[1]), q[2], q[3]]
                                   for d, q in dd.items()}
                               for p, dd in cp.items()} for v, cp in agg.items()},
                   'big': big,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT, 'w'))
        print('%d-%d (%.1f%%) venues=%d big=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(agg), len(big)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
