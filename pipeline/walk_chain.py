#!/usr/bin/env python3
"""
Walk a pass-through chain upstream inside a narrow block window.

When a chain layers the same amount through many fresh wallets on a single
day, a lifetime scan per hop is wasteful - every hop happens inside a few
hours. This walks hop by hop using a tight window, so each step costs a
handful of RPC calls instead of a full-history scan.

Usage: walk_chain.py <start_addr> <from_block> <to_block> [max_hops]
Data-only.
"""
import json, sys, urllib.request, time, bisect, datetime

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
STEP  = 49_999

D = 'pipeline/data/'
TS = json.load(open(D + 'blk_ts.json')); _tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]
V = json.load(open(D + 'venues.json'))
lab = json.load(open(D + 'all_labels_final.json'))
POOLS = {
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
    '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1 (Advisors)',
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool',
}


def rpc(m, p, tries=12):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=180).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(60, 1.5 * (1.8 ** i)))


def bdt(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M')


def name(a):
    a = a.lower()
    if a in POOLS:
        return 'ALLOCATION POOL: ' + POOLS[a]
    if a in V:
        return f"{V[a]['name']} [{V[a]['group']}]"
    e = (lab.get(a, {}) or {}).get('entity')
    return e or '(no explorer label)'


def inbound(a, lo, hi):
    pad = '0x' + '0' * 24 + a[2:]
    rows = []
    b = lo
    while b <= hi:
        e = min(b + STEP, hi)
        for L in rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC, None, pad],
                                      'fromBlock': hex(b), 'toBlock': hex(e)}]):
            rows.append((int(L['blockNumber'], 16), '0x' + L['topics'][1][-40:],
                         int(L['data'], 16), L['transactionHash']))
        b = e + 1
    return rows


def main():
    cur = sys.argv[1].lower()
    lo, hi = int(sys.argv[2]), int(sys.argv[3])
    maxh = int(sys.argv[4]) if len(sys.argv) > 4 else 12
    seen = set()
    chain = []
    for hop in range(maxh):
        if cur in seen:
            print(f'  loop at {cur}'); break
        seen.add(cur)
        rows = inbound(cur, lo, hi)
        if not rows:
            print(f'hop {hop}: {cur}  [{name(cur)}]  <- NO inbound in window')
            break
        rows.sort(key=lambda r: -r[2])
        bn, src, v, tx = rows[0]
        print(f'hop {hop}: {cur}\n   [{name(cur)}]\n   <- {v/1e24:,.1f}mn  {bdt(bn)}  from {src}\n'
              f'      [{name(src)}]  tx {tx}', flush=True)
        chain.append([hop, cur, src, str(v), bn, tx])
        if src in POOLS or src in V:
            print(f'\nTERMINATES at {name(src)}')
            break
        cur = src
    json.dump(chain, open(D + 'walk_chain_out.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
