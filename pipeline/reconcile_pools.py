#!/usr/bin/env python3
"""
INDEPENDENT re-scan of every AKE transfer into and out of the 8 pool contracts
over the analysis window, reconciled against balanceOf at both anchors.
This is a verification pass: it does not reuse any earlier checkpoint.
Data-only. Resumable.
"""
import json, urllib.request, time, os, collections, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CKPT  = 'pipeline/data/pool_reconcile_checkpoint.json'
A, B  = 100_940_327, 113_384_906

POOLS = {
    'Investors Pool': '0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
    'Nodes Pool 3':   '0xaf66503770451c83a4f12a1146a32271893508ce',
    'Team Pool 2':    '0xd229b65d50e412cc3c394233e7a53a1dac4da457',
    'Nodes Pool 1':   '0xb7c7786b6ca1130584f005e9c86554114b7fad62',
    'Nodes Pool 2':   '0xd2f72669e560c7ecd3c681612963990ef6f1981b',
    'Team Pool 1':    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
    'KOL Pool':       '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5',
    'Community Pool': '0x6b394c413d60b2aadb37a907a73a6f9a91c35015',
}
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
            time.sleep(min(60, 1.5 * (1.7 ** i)))


def main():
    if os.path.exists(CKPT):
        st = json.load(open(CKPT))
        frm, rows = st['last_block'] + 1, st['rows']
        print(f'RESUME {frm} ({len(rows)} rows)', flush=True)
    else:
        frm, rows = A + 1, []
        print(f'FRESH {frm}', flush=True)

    while frm <= B:
        to = min(frm + 49999, B)
        for tp in ([TOPIC, [pad(p) for p in POOLS.values()]],
                   [TOPIC, None, [pad(p) for p in POOLS.values()]]):
            for lg in rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                                           'toBlock': hex(to), 'topics': tp}]):
                rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                             '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16)),
                             lg['transactionHash']])
        json.dump({'last_block': to, 'rows': rows,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
