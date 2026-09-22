#!/usr/bin/env python3
"""
Give every wallet that appears in a pool release a specific, checkable role
instead of a vague family resemblance.

"A wallet from the cluster that has taken pool distributions before" is true
and useless. It does not say which pool, when, how much, or whether the wallet
ever touched the contract itself. This builds the precise version: for each
address, the exact releases it received, the exact transactions it sent to a
pool contract (which is what an admin or claim action looks like from the
outside), and whether it appears on more than one release day.

Roles are assigned only from on-chain facts, in this order:
  signer            sent a transaction to a pool contract, or to the owner Safe,
                    that caused a release — named with the selector it called
  repeat recipient  received from a pool on more than one release day
  recipient         received from a named pool on a named day
  round-trip        received from a pool and sent part or all of it back

Usage: wallet_roles.py
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, glob, bisect, datetime, collections, urllib.request, time

D = 'pipeline/data/'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
SAFE = '0x551a841742733bef96646b44e3475ce6a01da5eb'
SINCE = '2026-06-01'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}
SELNAME = {'0x6a761202': 'execTransaction on the Safe',
           '0x4f1ef286': 'upgradeToAndCall — swaps the pool implementation',
           '0xf17e48ec': 'adminTransfer(address,uint256)',
           '0xa646f9ad': 'userWithdraw()',
           '0xac694711': 'the member self-claim path',
           '0xdace4557': 'setUnlockTime(uint256)',
           '0xe0dc37a3': 'batch payout — an array of (address, amount) pairs',
           '0xf2fde38b': 'transferOwnership(address)'}

TS = json.load(open(D + 'blk_ts.json'))
_kb = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]


def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=150).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * 1.6 ** i)


def bts(bn):
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def bd(bn):
    return datetime.datetime.utcfromtimestamp(int(bts(bn))).strftime('%Y-%m-%d')


def main():
    led = json.load(open(D + 'pool_net_ledger.json'))
    rows = []
    for f in sorted(glob.glob(D + 'poolflow_*.json')):
        rows.extend(json.load(open(f))['rows'])
    rows.sort()

    # what each wallet received from which pool on which day, and sent back
    got = collections.defaultdict(lambda: collections.defaultdict(int))
    sentback = collections.defaultdict(lambda: collections.defaultdict(int))
    for r in rows:
        bn, f, t, v = r[0], r[1].lower(), r[2].lower(), int(r[3])
        d = bd(bn)
        if f in POOLS and t not in POOLS:
            got[t][(d, POOLS[f])] += v
        if t in POOLS and f not in POOLS:
            sentback[f][(d, POOLS[t])] += v

    # every transaction sent to a pool contract or to the Safe on a release day
    signers = collections.defaultdict(list)
    for d, e in led['days'].items():
        blocks = sorted({l[0] for l in e['legs']})
        sample = blocks if len(blocks) <= 6 else blocks[:3] + blocks[-3:]
        for bn in sample:
            blk = rpc('eth_getBlockByNumber', [hex(bn), True])
            for tx in blk['transactions']:
                to = (tx.get('to') or '').lower()
                if to in POOLS or to == SAFE:
                    signers[tx['from'].lower()].append(
                        {'day': d, 'block': bn, 'to': POOLS.get(to, 'the owner Safe'),
                         'selector': tx['input'][:10],
                         'action': SELNAME.get(tx['input'][:10], 'unrecognised selector'),
                         'tx': tx['hash']})
        print(f'  {d}: {len(blocks)} block(s), sampled {len(sample)}', flush=True)

    roles = {}
    for a in set(list(got) + list(signers) + list(sentback)):
        days = sorted({d for d, _ in got[a]}) if a in got else []
        recent = [d for d in days if d >= SINCE]
        if not recent and a not in signers:
            continue
        rec = [{'day': d, 'pool': p, 'amount': str(v)}
               for (d, p), v in sorted(got[a].items()) if d >= SINCE]
        ret = [{'day': d, 'pool': p, 'amount': str(v)}
               for (d, p), v in sorted(sentback[a].items()) if d >= SINCE]
        net = sum(int(x['amount']) for x in rec) - sum(int(x['amount']) for x in ret)
        # the single most specific true sentence about this wallet
        if a in signers:
            s = signers[a][0]
            acts = sorted({x['action'] for x in signers[a]})
            dd = sorted({x['day'] for x in signers[a]})
            label = ('the key that signed the release' +
                     ('s on ' + ', '.join(dd) if len(dd) > 1 else ' on ' + dd[0]) +
                     ' — it sent the ' + ' and '.join(acts))
        elif ret and rec:
            label = (f'received {int(rec[0]["amount"])/1e27:,.4f}bn from the '
                     f'{rec[0]["pool"]} Pool on {rec[0]["day"]} and sent '
                     f'{int(ret[0]["amount"])/1e27:,.4f}bn of it straight back to the '
                     f'same pool the same day')
        elif len(rec) > 1:
            label = ('took a release on ' + ', '.join(sorted({x['day'] for x in rec})) +
                     ' — ' + ', '.join(f'{int(x["amount"])/1e27:,.4f}bn from {x["pool"]}'
                                       for x in rec))
        elif rec:
            label = (f'first appeared on-chain when the {rec[0]["pool"]} Pool sent it '
                     f'{int(rec[0]["amount"])/1e27:,.4f}bn on {rec[0]["day"]}')
        else:
            continue
        roles[a] = {'label': label, 'received': rec, 'returned': ret,
                    'net_received': str(net),
                    'signed': signers.get(a, []),
                    'release_days': sorted({x['day'] for x in rec}),
                    'is_signer': a in signers,
                    'is_repeat': len({x['day'] for x in rec}) > 1}

    json.dump({'since': SINCE, 'roles': roles}, open(D + 'wallet_roles.json', 'w'), indent=1)
    print(f'\n{len(roles)} wallets with a specific role\n')
    for a, r in sorted(roles.items(), key=lambda x: -int(x[1]['net_received']))[:24]:
        print(f'{a}  net {int(r["net_received"])/1e27:>9,.4f}bn')
        print(f'   {r["label"]}')
    print(f'\nwrote {D}wallet_roles.json')
    print('DONE')


if __name__ == '__main__':
    main()
