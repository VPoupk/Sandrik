#!/usr/bin/env python3
"""Full-history AKE transfers in/out of a named set of pool contracts.
Single-address topic filters -> fast per chunk. Resumable. Data-only."""
import json, urllib.request, time, os, datetime, sys

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
A, B  = 57_840_000, 113_384_906
CKPT  = 'pipeline/data/pool_full_checkpoint.json'

POOLS = ['0x27333bd8c321a263b0565e69eea3b736b9d1f42c',   # Investors
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457',   # Team 2
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248']   # Team 1
pad = lambda a: '0x' + '0' * 24 + a[2:]


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def main():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT)); frm, rows = st['last_block'] + 1, st['rows']
    else:
        frm, rows = A, []
    print(f'pool full scan {frm} -> {B}', flush=True)
    n = 0
    while frm <= B:
        to = min(frm + 49999, B)
        for tp in ([TOPIC, [pad(p) for p in POOLS]],
                   [TOPIC, None, [pad(p) for p in POOLS]]):
            for lg in rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                                           'toBlock': hex(to), 'topics': tp}]):
                rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                             '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16)),
                             lg['transactionHash']])
        json.dump({'last_block': to, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        n += 1
        if n % 60 == 0:
            print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print(f'DONE rows={len(rows)}', flush=True)


if __name__ == '__main__':
    main()
