#!/usr/bin/env python3
"""
Follow every pool release to its destination, through as many hops as it takes,
instead of stopping one transfer from the recipient.

This exists because the one-hop version got an answer wrong. It reported that
nothing from any release since June 2026 had reached an exchange. The 19 June
release had in fact been sold: the recipient passed it to a second wallet the
next day, that wallet passed it to a third a month later, and the third
deposited the whole 2.0000bn into Gate.io custody on 23 July. One hop saw none
of that. A release is not a hold merely because the wallet that received it
handed the problem to another wallet.

Method. For each recipient, find its outgoing transfers by bisecting on
balanceOf rather than scanning logs across millions of blocks — a wallet's
balance only changes when it transacts, so binary search lands on the exact
block in about twenty calls. Follow each destination in turn, up to MAXHOP,
stopping a branch when it reaches exchange custody, a DEX pool, a pool
contract, or a wallet that still holds.

Every branch ends in one of four states, and the totals are what the document
reports:
    sold        reached custody at an exchange other than Binance
    to_binance  reached a Binance-labelled wallet
    to_dex      reached a DEX pool, i.e. sold into the on-chain book
    holding     still sitting in a wallet at the head block

Usage: trace_release_trail.py [max_hops]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, sys, time, bisect, datetime, collections, urllib.request

D = 'pipeline/data/'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
MAXHOP = int(sys.argv[1]) if len(sys.argv) > 1 else 6
DUST = 10**24 // 100          # 10k AKE — below this it is address-poisoning noise

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

V = json.load(open(D + 'venues_scan.json'))
LAB = json.load(open(D + 'all_labels_final.json'))
DEX = set(json.load(open(D + 'ake_pools.json')))
ROUTER = {a for a in V if 'Router' in (LAB.get(a, {}).get('property_tags') or [])}
CUSTODY = {a for a in V if a not in ROUTER}
TS = json.load(open(D + 'blk_ts.json'))
_kb = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]
_calls = 0


def rpc(m, p, tries=10):
    global _calls
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=120).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            _calls += 1
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(1.5 * 1.6 ** i)


def bts(bn):
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def ut(bn):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime('%Y-%m-%d %H:%M:%S')


def kind(a):
    if a in CUSTODY:
        return 'binance' if V[a]['group'] == 'binance' else 'cex'
    if a in DEX:
        return 'dex'
    if a in POOLS:
        return 'pool'
    if a in ROUTER:
        return 'router'
    return 'wallet'


def name(a):
    if a in CUSTODY:
        return V[a].get('name', a)
    if a in DEX:
        return 'DEX pool'
    if a in POOLS:
        return POOLS[a] + ' Pool'
    return (LAB.get(a) or {}).get('entity') or ''


def outgoing(w, since, head):
    """every outgoing transfer, found by bisecting on balance rather than
    scanning logs — a balance only moves when the wallet transacts"""
    cache = {}

    def bal(b):
        if b not in cache:
            cache[b] = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + w[2:]},
                                            hex(b)]), 16)
        return cache[b]

    out, cur = [], since
    for _ in range(40):
        v0 = bal(cur)
        if v0 == 0 or bal(head) == v0:
            break
        a, b = cur, head
        while b - a > 1:
            mid = (a + b) // 2
            if bal(mid) == v0:
                a = mid
            else:
                b = mid
        for L in rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC, '0x' + '0'*24 + w[2:], None],
                                      'fromBlock': hex(b), 'toBlock': hex(b)}]):
            out.append((b, '0x' + L['topics'][2][-40:], int(L['data'], 16)))
        cur = b + 1
    return out


def main():
    head = json.load(open(D + 'head_now.json'))['head']
    head = int(rpc('eth_blockNumber', []), 16)
    led = json.load(open(D + 'pool_net_ledger.json'))

    result = {}
    for d in sorted(led['days']):
        seeds = collections.defaultdict(int)
        first_block = min(l[0] for l in led['days'][d]['legs'])
        for bn, ts, k, pool, cp, v in led['days'][d]['legs']:
            if k == 'out':
                seeds[cp] += int(v)
        net = int(led['days'][d]['net_total'])
        if len(seeds) > 60:
            result[d] = {'net': str(net), 'recipients': len(seeds), 'walked': False,
                         'note': 'too many recipients to walk; see the consolidation figure'}
            print(f'{d}: {len(seeds)} recipients — not walked', flush=True)
            continue

        buckets = collections.Counter()
        trails = []
        seen = set()
        # each queue entry carries the block at which THIS wallet received the
        # tokens. Bisecting from the release day's first block instead was the
        # bug that hid the 19 June trail: the second wallet's balance was still
        # zero there, so the search concluded it had never moved anything.
        queue = [(a, v, 1, first_block, [('release', d, a, str(v))])
                 for a, v in seeds.items()]
        while queue:
            w, amt, hop, since, path = queue.pop(0)
            if amt < DUST:
                continue
            k = kind(w)
            if k in ('cex', 'binance', 'dex', 'pool'):
                buckets[{'cex': 'sold', 'binance': 'to_binance',
                         'dex': 'to_dex', 'pool': 'returned'}[k]] += amt
                trails.append({'end': k, 'amount': str(amt), 'where': w,
                               'name': name(w), 'path': path})
                continue
            if hop > MAXHOP or (w, hop) in seen:
                buckets['unresolved'] += amt
                trails.append({'end': 'depth limit', 'amount': str(amt), 'where': w,
                               'name': name(w), 'path': path})
                continue
            seen.add((w, hop))
            outs = [o for o in outgoing(w, since, head) if o[2] >= DUST]
            moved = sum(o[2] for o in outs)
            held = max(0, amt - moved)
            if held:
                buckets['holding'] += held
                trails.append({'end': 'holding', 'amount': str(held), 'where': w,
                               'name': name(w), 'path': path})
            for bn, to, v in outs:
                share = min(v, amt)
                if share < DUST:
                    continue
                queue.append((to, share, hop + 1, bn,
                              path + [(ut(bn), name(to) or kind(to), to, str(share))]))
                amt -= share
                if amt <= 0:
                    break
        result[d] = {'net': str(net), 'recipients': len(seeds), 'walked': True,
                     'buckets': {k: str(v) for k, v in buckets.items()},
                     'trails': trails}
        print(f'{d}: net {net/1e27:,.4f}bn, {len(seeds)} recipients -> ' +
              ', '.join(f'{k} {v/1e27:,.4f}bn' for k, v in buckets.most_common()), flush=True)

    json.dump({'head': head, 'max_hops': MAXHOP, 'rpc_calls': _calls, 'days': result},
              open(D + 'release_trails.json', 'w'), indent=1)
    print(f'\n{_calls} RPC calls; wrote {D}release_trails.json')
    print('DONE')


if __name__ == '__main__':
    main()
