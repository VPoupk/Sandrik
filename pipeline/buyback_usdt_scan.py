#!/usr/bin/env python3
"""Full-history AKE transfer scan (in AND out) for the node-buyback eligible
wallet list. Topic-filtered, 50k chunks, resumable. Data-only."""
import json, urllib.request, time, os, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x55d398326f99059ff775485246999027b3197955'  # BSC-USD (USDT)
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
CKPT  = 'pipeline/data/buyback_usdt_checkpoint.json'
A, B  = 57_840_000, 113_384_906
SRC   = '/tmp/claude-0/-home-user-Sandrik/4d5dfae8-d9f1-59c8-a7af-703ef8978ed1/scratchpad/buyback_addrs.json'

ADDRS = json.load(open(SRC))
pad = lambda a: '0x' + '0' * 24 + a[2:]
TOPICS = [pad(a) for a in ADDRS]


def rpc(m, p, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=150).read())
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
    print(f'buyback scan {frm} -> {B} ({len(ADDRS)} wallets)', flush=True)
    n = 0
    while frm <= B:
        to = min(frm + 49999, B)
        for tp in ([TOPIC, TOPICS], [TOPIC, None, TOPICS]):
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
        if n % 40 == 0:
            print(f'{frm}-{to} ({100.0*(to-A)/(B-A):.1f}%) rows={len(rows)}', flush=True)
        frm = to + 1
    print(f'DONE rows={len(rows)}', flush=True)


if __name__ == '__main__':
    main()
