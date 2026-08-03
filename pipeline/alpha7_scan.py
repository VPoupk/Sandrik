#!/usr/bin/env python3
"""Full AKE transfer history (in and out) for the seven large Binance Alpha
withdrawal wallets. Topic-filtered, resumable. Data-only."""
import json, urllib.request, time, os, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
A, B  = 108_000_000, 113_384_906
CKPT  = 'pipeline/data/alpha7_checkpoint.json'
ADDRS = json.load(open('/tmp/alpha7.json'))
pad = lambda a: '0x' + '0' * 24 + a[2:]
TOPICS = [pad(a) for a in ADDRS]


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


def get_logs(frm, to, tp):
    try:
        return rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                                    'toBlock': hex(to), 'topics': tp}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get_logs(frm, mid, tp) + get_logs(mid + 1, to, tp)


def main():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT)); frm, rows = st['last_block'] + 1, st['rows']
    else:
        frm, rows = A, []
    print(f'alpha7 scan {frm} -> {B}', flush=True)
    n = 0
    while frm <= B:
        to = min(frm + 49999, B)
        for tp in ([TOPIC, TOPICS], [TOPIC, None, TOPICS]):
            for lg in get_logs(frm, to, tp):
                rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                             '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16))])
        json.dump({'last_block': to, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        n += 1
        if n % 20 == 0:
            print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print(f'DONE rows={len(rows)}', flush=True)


if __name__ == '__main__':
    main()
