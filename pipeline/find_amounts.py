#!/usr/bin/env python3
"""
Test a claimed airdrop against the chain.

Reads every AKE Transfer in a block range and counts how often each exact
value appears. A tiered airdrop paid on-chain leaves an unmistakable
signature: the same handful of values repeated hundreds or thousands of times.
If those values never appear, the distribution did not happen on-chain at
this contract, which is itself a finding.

Usage: find_amounts.py <from> <to> <out_name> [target_ake,target_ake,...]
Data-only.
"""
import json, urllib.request, time, os, sys, collections

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

A    = int(sys.argv[1])
B    = int(sys.argv[2])
CKPT = 'pipeline/data/%s.json' % sys.argv[3]
# NOTE: must be exact integer arithmetic. int(float('155555') * 10**18) is
# 155554999999999992954880 - float64 cannot hold 24 significant digits, and the
# silent drift made an earlier run report zero matches for amounts that occur
# thousands of times.
TARGETS = {int(x.strip()) * 10**18 for x in sys.argv[4].split(',')} if len(sys.argv) > 4 else set()
STEP = 24_999


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
    freq = collections.Counter()
    hits = []
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('from') == A and c.get('to') == B:
            freq = collections.Counter({k: v for k, v in c['freq'].items()})
            hits = c['hits']; start = c['last_block'] + 1
            print('resume at %d' % start, flush=True)

    print('amount scan %d -> %d  targets=%s' %
          (A, B, [t // 10**18 for t in TARGETS]), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        for L in get(b, e):
            if len(L['topics']) < 3:
                continue
            v = int(L['data'], 16)
            freq[str(v)] += 1
            if v in TARGETS:
                hits.append([int(L['blockNumber'], 16),
                             '0x' + L['topics'][1][-40:], '0x' + L['topics'][2][-40:],
                             str(v), L['transactionHash']])
        json.dump({'from': A, 'to': B, 'last_block': e,
                   'freq': dict(freq), 'hits': hits}, open(CKPT, 'w'))
        print('%d-%d (%.1f%%) distinct=%d target_hits=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(freq), len(hits)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
