#!/usr/bin/env python3
"""Dated AKE transfers in and out of Binance Alpha 2.0 across the April-2026
burst and the run-up to the May snapshot. Handles the provider's 50k-log
response cap by halving the range. Resumable. Data-only."""
import json, urllib.request, time, os, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
ALPHA = '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db'
A, B  = 90_000_000, 100_940_327
CKPT  = 'pipeline/data/alpha_apr_checkpoint.json'
pad = lambda a: '0x' + '0' * 24 + a[2:]


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
        print(f'  split {frm}-{to}', flush=True)
        return get_logs(frm, mid, tp) + get_logs(mid + 1, to, tp)


def main():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT)); frm, rows = st['last_block'] + 1, st['rows']
    else:
        frm, rows = A, []
    print(f'alpha apr scan {frm} -> {B}', flush=True)
    n = 0
    while frm <= B:
        to = min(frm + 49999, B)
        for tp in ([TOPIC, [pad(ALPHA)]], [TOPIC, None, [pad(ALPHA)]]):
            for lg in get_logs(frm, to, tp):
                rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                             '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16))])
        json.dump({'last_block': to, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        n += 1
        if n % 30 == 0:
            print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print(f'DONE rows={len(rows)}', flush=True)


if __name__ == '__main__':
    main()
