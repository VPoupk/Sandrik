#!/usr/bin/env python3
"""
Unfiltered sweep of every AKE Transfer in a block window, aggregated by sender
and by receiver, with every transfer >= BIG kept in full.

The venue scans answer "what reached a known exchange or pool". This answers
the prior question - "who moved size at all" - which is what you need when a
price move has no matching venue inflow and the seller is therefore somewhere
the venue registry does not yet name.

Usage: window_sweep.py <from> <to> <ckpt_name> [big_mn]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, os, sys, datetime, collections

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

A    = int(sys.argv[1])
B    = int(sys.argv[2])
CKPT = 'pipeline/data/%s.json' % sys.argv[3]
BIG  = int(float(sys.argv[4]) * 1e6 * 10**18) if len(sys.argv) > 4 else 5_000_000 * 10**18
STEP = 9_999


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
        return rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get(frm, mid) + get(mid + 1, to)


def main():
    sent = collections.defaultdict(int); sct = collections.Counter()
    recv = collections.defaultdict(int); rct = collections.Counter()
    big  = []
    nlog = 0
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('from') == A and c.get('to') == B:
            for k, v in c['sent'].items():
                sent[k] = int(v)
            for k, v in c['recv'].items():
                recv[k] = int(v)
            sct.update(c['sct']); rct.update(c['rct'])
            big = c['big']; nlog = c['nlog']
            start = c['last_block'] + 1
            print('resume at %d' % start, flush=True)

    print('sweep %d -> %d' % (A, B), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        for L in get(b, e):
            nlog += 1
            f = '0x' + L['topics'][1][-40:]
            d = '0x' + L['topics'][2][-40:]
            v = int(L['data'], 16)
            sent[f] += v; sct[f] += 1
            recv[d] += v; rct[d] += 1
            if v >= BIG:
                big.append([int(L['blockNumber'], 16), f, d, str(v),
                            L['transactionHash']])

        json.dump({'job': sys.argv[3], 'from': A, 'to': B, 'last_block': e,
                   'sent': {k: str(v) for k, v in sent.items()},
                   'recv': {k: str(v) for k, v in recv.items()},
                   'sct': dict(sct), 'rct': dict(rct),
                   'big': big, 'nlog': nlog,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT, 'w'))
        print('%d-%d (%.1f%%) logs=%d addrs=%d big=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), nlog, len(sent), len(big)),
              flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
