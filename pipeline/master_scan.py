#!/usr/bin/env python3
"""
Master AKE Transfer scanner. Aggregates on the fly so the checkpoint stays small:
  - per-address received / sent totals + counts
  - per-address per-day received totals (for date-priced valuation)
  - every transfer >= BIG kept in full
  - every transfer touching a WATCH address kept in full
Handles the provider's 50k-log response cap by halving the range. Resumable.
Usage: master_scan.py <from> <to> <ckpt_name> [big_mn]
Data-only: writes to pipeline/data only, never HTML, never git.
"""
import json, urllib.request, time, os, datetime, collections, bisect, sys

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

A    = int(sys.argv[1])
B    = int(sys.argv[2])
CKPT = 'pipeline/data/%s.json' % sys.argv[3]
BIG  = int(float(sys.argv[4]) * 1e6 * 1e18) if len(sys.argv) > 4 else 5_000_000 * 10**18
STEP = 24_999

WATCH = set(json.load(open('pipeline/data/watch_master.json')))

TS = json.load(open('pipeline/data/blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=12):
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
        nrecv = collections.Counter(st['nrecv']); nsent = collections.Counter(st['nsent'])
        byday = {k: collections.Counter({d: int(x) for d, x in v.items()})
                 for k, v in st['byday'].items()}
        big, wrows = st['big'], st['wrows']
    else:
        frm = A
        recv, sent = collections.Counter(), collections.Counter()
        nrecv, nsent = collections.Counter(), collections.Counter()
        byday, big, wrows = {}, [], []
    print(f'master scan {frm} -> {B}  (BIG={BIG/1e18/1e6:.0f}mn, {len(WATCH)} watched)', flush=True)
    while frm <= B:
        to = min(frm + STEP, B)
        logs = get_logs(frm, to)
        for lg in logs:
            tp = lg['topics']
            if len(tp) < 3:
                continue
            s = '0x' + tp[1][-40:]; d = '0x' + tp[2][-40:]
            v = int(lg['data'], 16); bn = int(lg['blockNumber'], 16)
            recv[d] += v; sent[s] += v; nrecv[d] += 1; nsent[s] += 1
            byday.setdefault(d, collections.Counter())[bd(bn)] += v
            if v >= BIG:
                big.append([bn, s, d, str(v)])
            elif s in WATCH or d in WATCH:
                wrows.append([bn, s, d, str(v)])
        json.dump({'last_block': to, 'from': A,
                   'recv': {k: str(v) for k, v in recv.items()},
                   'sent': {k: str(v) for k, v in sent.items()},
                   'nrecv': dict(nrecv), 'nsent': dict(nsent),
                   'byday': {k: {d: str(x) for d, x in v.items()} for k, v in byday.items()},
                   'big': big, 'wrows': wrows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        print(f'{frm}-{to} ({100.0*(to-A)/max(1,B-A):.1f}%) logs={len(logs)} '
              f'addrs={len(recv)} big={len(big)} w={len(wrows)}', flush=True)
        frm = to + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
