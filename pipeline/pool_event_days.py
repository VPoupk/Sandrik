#!/usr/bin/env python3
"""
Build the per-event record behind every day since June 2026 on which a
team-controlled pool moved tokens, and follow each recipient forward to the
head block.

A release is only half the story. The question that matters is what the
recipients did next, and the only answer the chain gives is a balance and a
list of onward transfers. So for each event day this records:

  - every transfer out of (and back into) a pool, priced at the CoinGecko
    hourly rate interpolated to that transfer's own block timestamp
  - the transaction that caused it, its caller, and whether it went through
    the owner Safe
  - for each recipient: how much it received, what it holds now, how much it
    has sent on, and how much of that reached exchange custody

The "reached an exchange" test uses the venue registry and the accounting
rule this project works to: a transfer into any exchange except Binance is
treated as a sale; anything still sitting in a wallet, however widely
distributed, is a hold.

Usage: pool_event_days.py [since]          default since=2026-06-01
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, glob, sys, time, bisect, datetime, collections, urllib.request

D    = 'pipeline/data/'
RPC  = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE  = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
SAFE = '0x551a841742733bef96646b44e3475ce6a01da5eb'
SINCE = sys.argv[1] if len(sys.argv) > 1 else '2026-06-01'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

V   = json.load(open(D + 'venues_scan.json'))
LAB = json.load(open(D + 'all_labels_final.json'))
K   = json.load(open(D + 'known_sets.json'))
RECIP = set(a.lower() for a in K['direct pool recipient (lifetime)'])
WATCH = set(a.lower() for a in K['master watchlist']) | set(
    a.lower() for a in K['doc wallet']) | set(
    a.lower() for a in K['TeamPool2 recipient (21 Aug)'])
ROUTER = {a for a in V if 'Router' in (LAB.get(a, {}).get('property_tags') or [])}
CUSTODY = {a for a in V if a not in ROUTER}

TS = json.load(open(D + 'blk_ts.json'))
_kb = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]
HR = json.load(open(D + 'ake_hourly_cg.json'))
_hk = sorted(int(x) for x in HR); _hv = [HR[str(x)] for x in _hk]


def rpc(m, p, tries=12):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=200).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(40, 1.5 * (1.8 ** i)))


def bts(bn):
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def px(ts):
    """hourly CoinGecko rate interpolated to this exact second"""
    i = bisect.bisect_left(_hk, ts)
    if i == 0:
        return _hv[0]
    if i >= len(_hk):
        return _hv[-1]
    t0, t1, p0, p1 = _hk[i-1], _hk[i], _hv[i-1], _hv[i]
    return p0 + (p1 - p0) * (ts - t0) / (t1 - t0) if t1 > t0 else p0


def ut(ts, f='%Y-%m-%d %H:%M:%S'):
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime(f)


def tags(a):
    t = []
    if a in POOLS:
        t.append('allocation pool: ' + POOLS[a])
    if a in RECIP:
        t.append('prior pool recipient')
    if a in WATCH:
        t.append('watchlist')
    e = (LAB.get(a) or {}).get('entity')
    if e:
        t.append(e)
    if a in V and not e:
        t.append(V[a].get('name', ''))
    return t


def main():
    head = json.load(open(D + 'head_now.json'))['head']

    rows = []
    for f in sorted(glob.glob(D + 'poolflow_*.json')):
        rows.extend(json.load(open(f))['rows'])
    print('%d pool-touching transfers on disk' % len(rows), flush=True)

    days = collections.defaultdict(list)
    for r in rows:
        bn, fr, to, v = r[0], r[1].lower(), r[2].lower(), int(r[3])
        if fr not in POOLS and to not in POOLS:
            continue
        d = ut(bts(bn), '%Y-%m-%d')
        if d < SINCE:
            continue
        days[d].append([bn, fr, to, v])

    out = {}
    for d in sorted(days):
        legs = sorted(days[d])
        gross_out = sum(v for _, f, t, v in legs if f in POOLS and t not in POOLS)
        gross_in = sum(v for _, f, t, v in legs if t in POOLS and f not in POOLS)
        by_pool = collections.defaultdict(lambda: [0, 0])
        recips = collections.defaultdict(int)
        for bn, f, t, v in legs:
            if f in POOLS and t not in POOLS:
                by_pool[POOLS[f]][0] += v
                recips[t] += v
            if t in POOLS and f not in POOLS:
                by_pool[POOLS[t]][1] += v

        # The transactions that caused it, and who signed them. A day like
        # 22 July spans thousands of blocks; the mechanism is identical in all
        # of them, so sample the first and last few rather than pulling every
        # block with full transaction bodies.
        blks = sorted({l[0] for l in legs})
        sample = blks if len(blks) <= 8 else blks[:4] + blks[-4:]
        txs = {}
        for bn in sample:
            blk = rpc('eth_getBlockByNumber', [hex(bn), True])
            for tx in blk['transactions']:
                to = (tx.get('to') or '').lower()
                if to in POOLS or to == SAFE:
                    txs[tx['hash']] = {
                        'block': bn, 'to': to, 'via_safe': to == SAFE,
                        'caller': tx['from'].lower(), 'selector': tx['input'][:10],
                        'calldata_bytes': len(tx['input']) // 2 - 1}
        print('  %s: %d blocks, sampled %d, %d causing tx' %
              (d, len(blks), len(sample), len(txs)), flush=True)

        out[d] = {
            'date': d,
            'gross_out': str(gross_out), 'gross_in': str(gross_in),
            'net_out': str(gross_out - gross_in),
            'usd_net': sum(v * px(int(bts(bn))) / 1e18
                           for bn, f, t, v in legs if f in POOLS and t not in POOLS)
                     - sum(v * px(int(bts(bn))) / 1e18
                           for bn, f, t, v in legs if t in POOLS and f not in POOLS),
            'by_pool': {k: [str(a), str(b)] for k, (a, b) in by_pool.items()},
            'n_recipients': len(recips),
            'first_ts': int(bts(legs[0][0])), 'last_ts': int(bts(legs[-1][0])),
            'txs': txs,
            'legs': [[bn, f, t, str(v), int(bts(bn)), v / 1e18 * px(int(bts(bn)))]
                     for bn, f, t, v in legs],
            'recipients': {a: str(v) for a, v in
                           sorted(recips.items(), key=lambda x: -x[1])},
        }
        print('%s  out %.4fbn  in %.4fbn  %d recipients' %
              (d, gross_out / 1e27, gross_in / 1e27, len(recips)), flush=True)

    # follow the recipients of the days with few enough of them to walk
    print('\nfollowing recipients forward to block %d' % head, flush=True)
    for d, e in out.items():
        rs = list(e['recipients'])
        if len(rs) > 200:
            e['followed'] = None
            print('  %s: %d recipients, too many to walk individually' % (d, len(rs)),
                  flush=True)
            continue
        fol = {}
        for a in rs:
            bal = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + a[2:]},
                                       hex(head)]), 16)
            fol[a] = {'received': e['recipients'][a], 'holds_now': str(bal),
                      'sent_on': [], 'to_exchange': '0', 'to_binance': '0'}
        # one pass over every onward transfer from these wallets
        pad = ['0x' + '0'*24 + a[2:] for a in rs]
        b = min(l[0] for l in e['legs'])
        while b <= head:
            en = min(b + 49_999, head)
            for L in rpc('eth_getLogs', [{'address': AKE, 'topics': [TOPIC, pad, None],
                                          'fromBlock': hex(b), 'toBlock': hex(en)}]):
                f = '0x' + L['topics'][1][-40:]
                t = '0x' + L['topics'][2][-40:]
                v = int(L['data'], 16)
                if f not in fol:
                    continue
                ts = int(bts(int(L['blockNumber'], 16)))
                fol[f]['sent_on'].append([int(L['blockNumber'], 16), t, str(v), ts,
                                          v / 1e18 * px(ts)])
                if t in CUSTODY:
                    g = V[t]['group']
                    key = 'to_binance' if g == 'binance' else 'to_exchange'
                    fol[f][key] = str(int(fol[f][key]) + v)
            b = en + 1
        e['followed'] = fol
        held = sum(int(x['holds_now']) for x in fol.values())
        ex = sum(int(x['to_exchange']) for x in fol.values())
        bi = sum(int(x['to_binance']) for x in fol.values())
        print('  %s: %d recipients, still holding %.4fbn, to non-Binance exchanges '
              '%.4fbn, to Binance %.4fbn' % (d, len(rs), held/1e27, ex/1e27, bi/1e27),
              flush=True)

    json.dump({'since': SINCE, 'head': head, 'days': out},
              open(D + 'pool_event_days.json', 'w'), indent=1)
    print('\nwrote %spool_event_days.json' % D, flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
