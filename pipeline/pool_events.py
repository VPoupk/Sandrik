#!/usr/bin/env python3
"""Scan every event emitted BY the pool contracts themselves (not AKE transfers)
over full token history, to find when beneficiaries/amounts were registered.
Data-only. Resumable."""
import json, urllib.request, time, os, collections, datetime, sys

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
CKPT = 'pipeline/data/pool_events_checkpoint.json'
A, B = 57_840_000, 113_384_906

POOLS = ['0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
         '0xaf66503770451c83a4f12a1146a32271893508ce',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b']


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
    print(f'pool events {frm} -> {B}', flush=True)
    while frm <= B:
        to = min(frm + 49999, B)
        for lg in rpc('eth_getLogs', [{'address': POOLS,
                                       'fromBlock': hex(frm), 'toBlock': hex(to)}]):
            rows.append([int(lg['blockNumber'], 16), lg['address'].lower(),
                         lg['topics'][0] if lg['topics'] else None,
                         [t for t in lg['topics'][1:]], lg['data'][:200],
                         lg['transactionHash']])
        json.dump({'last_block': to, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        if (to // 50000) % 20 == 0:
            print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print('DONE rows=%d' % len(rows), flush=True)


if __name__ == '__main__':
    main()
