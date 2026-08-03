#!/usr/bin/env python3
"""
Every AKE transfer from the Jul-26 pool unlocks (block 112,252,392) to chain
head, aggregated on the fly into per-destination and per-destination-per-day
totals so the checkpoint stays small. Also keeps every transfer >= 5mn AKE in
full so large sends can be attributed. Handles the 50k-log cap. Data-only.
"""
import json, urllib.request, time, os, datetime, collections, bisect

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
A, B  = 112_252_392, 113_384_906
CKPT  = 'pipeline/data/sells_jul26_agg.json'
BIG   = 5_000_000 * 10**18

TS = json.load(open('pipeline/data/blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=180).read())
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
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def get_logs(frm, to):
    try:
        return rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get_logs(frm, mid) + get_logs(mid + 1, to)


def main():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT))
        frm = st['last_block'] + 1
        recv = collections.Counter({k: int(v) for k, v in st['recv'].items()})
        sent = collections.Counter({k: int(v) for k, v in st['sent'].items()})
        byday = {k: collections.Counter({d: int(x) for d, x in v.items()})
                 for k, v in st['byday'].items()}
        big = st['big']
    else:
        frm = A
        recv, sent = collections.Counter(), collections.Counter()
        byday, big = {}, []
    print(f'sells agg scan {frm} -> {B}', flush=True)
    while frm <= B:
        to = min(frm + 24999, B)
        logs = get_logs(frm, to)
        for lg in logs:
            tp = lg['topics']
            if len(tp) < 3:
                continue
            s = '0x' + tp[1][-40:]; d = '0x' + tp[2][-40:]
            v = int(lg['data'], 16); bn = int(lg['blockNumber'], 16)
            recv[d] += v; sent[s] += v
            byday.setdefault(d, collections.Counter())[bd(bn)] += v
            if v >= BIG:
                big.append([bn, s, d, str(v)])
        json.dump({'last_block': to,
                   'recv': {k: str(v) for k, v in recv.items()},
                   'sent': {k: str(v) for k, v in sent.items()},
                   'byday': {k: {d: str(x) for d, x in v.items()} for k, v in byday.items()},
                   'big': big,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) logs={len(logs)} '
              f'addrs={len(recv)} big={len(big)}', flush=True)
        frm = to + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
