#!/usr/bin/env python3
"""
Complete lifetime record of every AKE Transfer where one of the eight
allocation pools is the sender or the recipient. Topic-position filtered, so
the node returns only pool-touching logs; de-duplicated on (block, logIndex),
so a pool-to-pool transfer is recorded exactly once.

Every row is kept in full — this IS the primary distribution record, and the
report reconciles it against balanceOf(pool) at head.

Usage: pool_flows_full.py <from> <to> <ckpt_name>
Data-only.
"""
import json, urllib.request, time, os, sys, datetime, bisect

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

POOLS = {
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
    '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1',
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool',
}
PAD = ['0x' + '0' * 24 + a[2:] for a in sorted(POOLS)]

A    = int(sys.argv[1])
B    = int(sys.argv[2])
CKPT = 'pipeline/data/%s.json' % sys.argv[3]
STEP = 49_999


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
    rows, seen, start = [], set(), A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('from') == A and c.get('to') == B:
            rows = c['rows']; seen = {(r[0], r[5]) for r in rows}
            start = c['last_block'] + 1
            print('resume at %d with %d rows' % (start, len(rows)), flush=True)

    print('pool flow scan %d -> %d' % (A, B), flush=True)
    b = start
    while b <= B:
        e = min(b + STEP, B)
        for pos in (1, 2):
            t = [TOPIC, None, None]
            t[pos] = PAD
            for L in get(b, e, t):
                bn = int(L['blockNumber'], 16); li = int(L['logIndex'], 16)
                if (bn, li) in seen:
                    continue
                seen.add((bn, li))
                rows.append([bn, '0x' + L['topics'][1][-40:], '0x' + L['topics'][2][-40:],
                             str(int(L['data'], 16)), L['transactionHash'], li])
        json.dump({'job': sys.argv[3], 'from': A, 'to': B, 'last_block': e, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()}, open(CKPT, 'w'))
        print('%d-%d (%.1f%%) rows=%d' % (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(rows)),
              flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
