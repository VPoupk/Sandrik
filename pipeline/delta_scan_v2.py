#!/usr/bin/env python3
"""
Delta scan v2 of ALL AKE Transfer events -> chain head.
Keeps: per-address aggregates, >=50M transfers, per-10k-block DEX-pool flow buckets,
and per-address curated rows (high-frequency infra excluded to keep checkpoint small).
Checkpoint written after EVERY chunk per CLAUDE.md rule #2. Data-only.
"""
import json, urllib.request, time, os, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CHUNK = 49999
BIG   = 50_000_000 * 10**18
BUCK  = 10_000
JOB   = 'ake_delta_v2'
CKPT  = f'pipeline/data/{JOB}_checkpoint.json'
START = 102_669_787

# high-frequency infra: aggregate only, never store individual rows
NOROW = {
    '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d',  # PancakeSwap V3 AKE/USDT
    '0x278d858f05b94576c1e6f73285886876ff6ef8d2',
    '0xb300000b72deaeb607a12d5f54773d1c19c7028d',  # Alpha relayer proxy
    '0x6aba0315493b7e6989041c91181337b662fb1b90',  # Alpha router proxy
    '0xbd97306a087ed0c46b783cfbfdcdc6c12c7a2866',
    '0x7817dbf38e9d1c95671625f0052c147864692fe0',
    '0x9d1aae9cd3db793fb00dc8d768b517953722a96d',
    '0xc58102fd6ebf241d845ece964131aed8dc4968ac',
}
POOLS = {'0x4d3bf29ba30f8bfe4624e7678709afa195689c5d'}
WATCH = set(json.load(open('/tmp/watchlist.json'))) - NOROW


class TooManyLogs(Exception):
    pass


def rpc(method, params, tries=12):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': method, 'params': params}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=180).read())
            if 'error' in r:
                msg = str(r['error'])
                # provider caps a single response at 50k logs -> caller must split
                if 'exceeds the limit' in msg or 'query returned more than' in msg:
                    raise TooManyLogs(msg)
                raise RuntimeError(msg)
            return r['result']
        except TooManyLogs:
            raise
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 2 * (1.7 ** i)))


def get_logs(frm, to):
    """eth_getLogs with automatic range-halving when the 50k response cap is hit."""
    try:
        return rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        print(f'  split {frm}-{to} (>50k logs)', flush=True)
        return get_logs(frm, mid) + get_logs(mid + 1, to)


def main():
    head = int(rpc('eth_blockNumber', []), 16)
    st = json.load(open(CKPT))
    frm = st['last_block'] + 1
    agg, big = st['agg'], st['big']
    rows, dexb = st['rows'], st['dexb']
    chunks = st['chunks_done']
    print(f'RESUME {frm} -> {head} ({chunks} chunks done)', flush=True)
    total = head - START + 1

    while frm <= head:
        to = min(frm + CHUNK, head)
        logs = get_logs(frm, to)
        for lg in logs:
            tp = lg['topics']
            if len(tp) < 3:
                continue
            s = '0x' + tp[1][-40:]
            d = '0x' + tp[2][-40:]
            v = int(lg['data'], 16)
            bn = int(lg['blockNumber'], 16)

            a = agg.setdefault(s, [0, 0, 0, 0]); a[0] += v; a[1] += 1
            b = agg.setdefault(d, [0, 0, 0, 0]); b[2] += v; b[3] += 1

            if s in POOLS or d in POOLS:
                k = str((bn // BUCK) * BUCK)
                e = dexb.setdefault(k, [0, 0, 0, 0])  # out_of_pool, n, into_pool, n
                if s in POOLS:
                    e[0] += v; e[1] += 1
                else:
                    e[2] += v; e[3] += 1

            if v >= BIG:
                big.append([bn, s, d, str(v), lg['transactionHash']])
            elif (s in WATCH or d in WATCH) and s not in NOROW and d not in NOROW:
                rows.append([bn, s, d, str(v)])

        chunks += 1
        json.dump({'job': JOB, 'last_block': to, 'total_blocks': total,
                   'chunks_done': chunks, 'head': head, 'agg': agg, 'big': big,
                   'rows': rows, 'dexb': dexb,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        pct = 100.0 * (to - START + 1) / total
        print(f'chunk {chunks}: {frm}-{to} ({pct:.1f}%) logs={len(logs)} '
              f'addrs={len(agg)} big={len(big)} rows={len(rows)}', flush=True)
        frm = to + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
