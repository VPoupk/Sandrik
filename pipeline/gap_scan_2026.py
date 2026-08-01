#!/usr/bin/env python3
"""
Delta scan of ALL AKE Transfer events from the last scanned block to chain head.
Writes checkpoint after EVERY chunk per CLAUDE.md rule #2.
Data-only: writes to pipeline/data/ only. Never edits HTML, never runs git.
"""
import json, urllib.request, time, os, datetime, sys

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CHUNK = 49999
BIG   = 50_000_000 * 10**18       # detail-record threshold: 50M AKE
JOB   = 'ake_gap_may_jun_2026'
CKPT  = f'pipeline/data/{JOB}_checkpoint.json'
START = 100_940_328

WATCH = set(json.load(open('/tmp/watchlist.json')))


def rpc(method, params, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC,
                data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                 'method': method, 'params': params}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=120).read())
            if 'error' in r:
                raise RuntimeError(r['error'])
            return r['result']
        except Exception as e:
            if i == tries - 1:
                raise
            time.sleep(1.5 * (2 ** i))


def topic_addr(t):
    return '0x' + t[-40:]


def main():
    head = 102_669_786

    if os.path.exists(CKPT):
        st = json.load(open(CKPT))
        frm = st['last_block'] + 1
        agg = {k: v for k, v in st['agg'].items()}
        big = st['big']
        watch_rows = st['watch_rows']
        chunks = st['chunks_done']
        print(f'RESUMING from {frm} ({chunks} chunks done)', flush=True)
    else:
        frm = START
        agg = {}
        big = []
        watch_rows = []
        chunks = 0
        print(f'FRESH start at {frm}', flush=True)

    total = head - START + 1
    blk_ts = {}

    while frm <= head:
        to = min(frm + CHUNK, head)
        logs = rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
        for lg in logs:
            tp = lg['topics']
            if len(tp) < 3:
                continue
            s = topic_addr(tp[1])
            d = topic_addr(tp[2])
            v = int(lg['data'], 16)
            bn = int(lg['blockNumber'], 16)

            a = agg.setdefault(s, [0, 0, 0, 0])   # out_amt, out_n, in_amt, in_n
            a[0] += v; a[1] += 1
            b = agg.setdefault(d, [0, 0, 0, 0])
            b[2] += v; b[3] += 1

            if v >= BIG:
                big.append([bn, s, d, str(v), lg['transactionHash']])
            elif s in WATCH or d in WATCH:
                watch_rows.append([bn, s, d, str(v), lg['transactionHash']])

        chunks += 1
        json.dump({'job': JOB, 'last_block': to, 'total_blocks': total,
                   'chunks_done': chunks, 'head': head,
                   'agg': agg, 'big': big, 'watch_rows': watch_rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)

        pct = 100.0 * (to - START + 1) / total
        print(f'chunk {chunks}: {frm}-{to} ({pct:.1f}%) logs={len(logs)} '
              f'addrs={len(agg)} big={len(big)} watch={len(watch_rows)}', flush=True)
        frm = to + 1

    print('DONE', flush=True)


if __name__ == '__main__':
    main()
