#!/usr/bin/env python3
"""Targeted scan: every AKE transfer OUT of the 8 pool contracts, and every
transfer IN/OUT of Binance Alpha, over a block range. Uses a topic OR-filter so
each chunk returns few logs -- far faster than a full scan. Data-only."""
import json, urllib.request, time, os, datetime, sys

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CHUNK = 49999

POOLS = ['0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
         '0xaf66503770451c83a4f12a1146a32271893508ce',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015']
ALPHA = '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db'
pad = lambda a: '0x' + '0' * 24 + a[2:]

JOB = 'pool_out'
CKPT = f'pipeline/data/{JOB}_checkpoint.json'
START = int(sys.argv[1]) if len(sys.argv) > 1 else 100_940_328


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            r = json.loads(urllib.request.urlopen(req, timeout=150).read())
            if 'error' in r:
                raise RuntimeError(r['error'])
            return r['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.7 ** i)))


def main():
    head = int(rpc('eth_blockNumber', []), 16)
    if os.path.exists(CKPT):
        st = json.load(open(CKPT))
        frm, rows, alpha, ch = st['last_block'] + 1, st['rows'], st['alpha'], st['chunks_done']
    else:
        frm, rows, alpha, ch = START, [], [], 0
    print(f'pool_out scan {frm} -> {head}', flush=True)

    while frm <= head:
        to = min(frm + CHUNK, head)
        # pool outflows (from-topic OR filter)
        for lg in rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm), 'toBlock': hex(to),
                                       'topics': [TOPIC, [pad(p) for p in POOLS]]}]):
            rows.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                         '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16))])
        # alpha in + out
        for tp in ([TOPIC, None, pad(ALPHA)], [TOPIC, pad(ALPHA)]):
            for lg in rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                                           'toBlock': hex(to), 'topics': tp}]):
                alpha.append([int(lg['blockNumber'], 16), '0x' + lg['topics'][1][-40:],
                              '0x' + lg['topics'][2][-40:], str(int(lg['data'], 16))])
        ch += 1
        json.dump({'job': JOB, 'last_block': to, 'chunks_done': ch, 'head': head,
                   'rows': rows, 'alpha': alpha,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        print(f'{ch}: {frm}-{to} ({100.0*(to-START)/(head-START):.1f}%) '
              f'pool={len(rows)} alpha={len(alpha)}', flush=True)
        frm = to + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
