#!/usr/bin/env python3
"""For a set of blocks, pull the AKE Transfer logs and resolve, for each,
the transaction sender (tx.from) and the function selector called.
Distinguishes admin-push from user-pull. Data-only."""
import json, urllib.request, time, sys, collections

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
pad = lambda a: '0x' + '0' * 24 + a[2:]


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
            time.sleep(min(60, 2 * (1.8 ** i)))


def batch(calls, tries=10):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps(calls).encode(),
                headers={'Content-Type': 'application/json'})
            return json.loads(urllib.request.urlopen(req, timeout=150).read())
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 2 * (1.8 ** i)))


def analyse(pool, frm, to, label):
    logs = rpc('eth_getLogs', [{'address': AKE, 'fromBlock': hex(frm),
                               'toBlock': hex(to), 'topics': [TOPIC, pad(pool)]}])
    txs = list(dict.fromkeys(l['transactionHash'] for l in logs))
    print(f'\n=== {label} ===\n  {len(logs)} transfers in {len(txs)} transactions', flush=True)
    sample = txs[:60]
    senders = collections.Counter(); sels = collections.Counter(); tos = collections.Counter()
    for i in range(0, len(sample), 20):
        grp = sample[i:i + 20]
        res = batch([{'jsonrpc': '2.0', 'id': j, 'method': 'eth_getTransactionByHash',
                      'params': [h]} for j, h in enumerate(grp)])
        by = {r['id']: r.get('result') for r in res}
        for j in range(len(grp)):
            t = by.get(j)
            if not t:
                continue
            senders[t['from'].lower()] += 1
            tos[(t.get('to') or '').lower()] += 1
            sels[t['input'][:10]] += 1
        time.sleep(0.2)
    print(f'  sampled {len(sample)} txs')
    print('  tx.from  :', senders.most_common(6))
    print('  tx.to    :', tos.most_common(4))
    print('  selector :', sels.most_common(6))
    # is the tx sender also the token recipient?
    rec_by_tx = {}
    for l in logs:
        rec_by_tx.setdefault(l['transactionHash'], []).append('0x' + l['topics'][2][-40:])
    self_claim = sum(1 for h in sample
                     if h in rec_by_tx and any(r in senders for r in rec_by_tx[h]))
    print(f'  txs where the AKE recipient is also the tx sender (self-claim): {self_claim}/{len(sample)}')
    return {'n_logs': len(logs), 'n_tx': len(txs),
            'senders': senders.most_common(10), 'selectors': sels.most_common(10),
            'to': tos.most_common(5), 'self_claim': self_claim, 'sampled': len(sample)}


if __name__ == '__main__':
    out = {}
    out['nodes3_jul22'] = analyse('0xaf66503770451c83a4f12a1146a32271893508ce',
                                  111428743, 111460000, 'Nodes Pool 3 — Jul 22 distribution')
    out['nodes1_jul22'] = analyse('0xb7c7786b6ca1130584f005e9c86554114b7fad62',
                                  111517896, 111535485, 'Nodes Pool 1 — Jul 22 distribution')
    out['investors_jul26'] = analyse('0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
                                     112252392, 112262000, 'Investors Pool — Jul 26')
    out['team2_jul26'] = analyse('0xd229b65d50e412cc3c394233e7a53a1dac4da457',
                                 112261100, 112262000, 'Team Pool 2 — Jul 26')
    out['team1_jul26'] = analyse('0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248',
                                 112261200, 112262000, 'Team Pool 1 — Jul 26')
    out['investors_jun19'] = analyse('0x27333bd8c321a263b0565e69eea3b736b9d1f42c',
                                     105170374, 105170375, 'Investors Pool — Jun 19 (4.073bn)')
    json.dump(out, open('pipeline/data/tx_origin.json', 'w'), indent=1, default=str)
