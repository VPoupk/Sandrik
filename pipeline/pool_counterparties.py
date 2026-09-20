#!/usr/bin/env python3
"""
Every AKE Transfer in or out of one DEX pool over a window, with each
counterparty classified against the sets that establish affiliation.

The swap series says what the price did; this says who was on the other side.
A transfer INTO the pool is AKE being sold; a transfer OUT is AKE being
bought. Routers sit in the middle of most trades, so the immediate
counterparty is usually an aggregator - the script therefore also resolves the
transaction's sender (tx.from), which is the wallet that actually initiated
the trade, and classifies that.

Affiliation tests, strongest first:
  pool_recipient  - received AKE directly from one of the eight allocation
                    pools at any time in the token's life (22k addresses)
  watchlist       - on the master watchlist built from earlier work
  labelled        - has an on-chain entity label (exchange, router, pool)

Usage: pool_counterparties.py <pool> <from> <to> <out_name> [min_mn]
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, os, sys, datetime, bisect, collections

RPC   = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE   = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
D     = 'pipeline/data/'
STEP  = 9_999

POOL = sys.argv[1].lower()
A, B = int(sys.argv[2]), int(sys.argv[3])
OUT  = D + sys.argv[4] + '.json'
MIN  = int(float(sys.argv[5]) * 1e6 * 10**18) if len(sys.argv) > 5 else 0

K    = json.load(open(D + 'known_sets.json'))
RECIP = set(a.lower() for a in K['direct pool recipient (lifetime)'])
WATCH = set(a.lower() for a in K['master watchlist']) | set(
    a.lower() for a in K['doc wallet']) | set(
    a.lower() for a in K['TeamPool2 recipient (21 Aug)'])
LAB  = json.load(open(D + 'all_labels_final.json'))
TS   = json.load(open(D + 'blk_ts.json'))
_kb  = sorted(int(x) for x in TS); _kv = [TS[str(x)] for x in _kb]
HR   = json.load(open(D + 'ake_hourly_cg.json'))
_hk  = sorted(int(x) for x in HR); _hv = [HR[str(x)] for x in _hk]


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=14):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=200).read())
            if 'error' in j:
                msg = str(j['error'])
                if 'exceeds the limit' in msg or 'query returned more than' in msg:
                    raise TooManyLogs(msg)
                raise RuntimeError(msg)
            return j['result']
        except TooManyLogs:
            raise
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 1.5 * (1.8 ** i)))


def get(frm, to, topics):
    try:
        return rpc('eth_getLogs', [{'address': AKE, 'topics': topics,
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get(frm, mid, topics) + get(mid + 1, to, topics)


def bts(bn):
    """block -> unix seconds, linear between sampled blocks"""
    i = bisect.bisect_left(_kb, bn)
    if i == 0:
        return _kv[0]
    if i >= len(_kb):
        return _kv[-1]
    return _kv[i-1] + (_kv[i]-_kv[i-1]) * (bn-_kb[i-1]) / (_kb[i]-_kb[i-1])


def px(ts):
    """CoinGecko hourly price interpolated to this exact second - never a flat
    daily price, which is the whole point of holding an hourly series."""
    i = bisect.bisect_left(_hk, ts)
    if i == 0:
        return _hv[0]
    if i >= len(_hk):
        return _hv[-1]
    t0, t1 = _hk[i-1], _hk[i]
    p0, p1 = _hv[i-1], _hv[i]
    return p0 + (p1 - p0) * (ts - t0) / (t1 - t0) if t1 > t0 else p0


def cls(a):
    tags = []
    if a in RECIP:
        tags.append('pool-recipient')
    if a in WATCH:
        tags.append('watchlist')
    e = (LAB.get(a) or {}).get('entity')
    if e:
        tags.append(e)
    return tags


def main():
    pad = '0x' + '0' * 24 + POOL[2:]
    rows, seen = [], set()
    ck = OUT.replace('.json', '_ckpt.json')
    b = A
    if os.path.exists(ck):
        c = json.load(open(ck))
        if c['from'] == A and c['to'] == B and c['pool'] == POOL:
            rows = c['rows']; b = c['last_block'] + 1
            seen = {(r[0], r[1]) for r in rows}
            print('resume at %d (%d rows)' % (b, len(rows)), flush=True)

    while b <= B:
        e = min(b + STEP, B)
        for pos in (1, 2):
            t = [TOPIC, None, None]
            t[pos] = pad
            for L in get(b, e, t):
                bn, li = int(L['blockNumber'], 16), int(L['logIndex'], 16)
                if (bn, li) in seen:
                    continue
                seen.add((bn, li))
                f = '0x' + L['topics'][1][-40:]
                d = '0x' + L['topics'][2][-40:]
                v = int(L['data'], 16)
                if v < MIN:
                    continue
                rows.append([bn, li, f, d, str(v), L['transactionHash']])
        json.dump({'pool': POOL, 'from': A, 'to': B, 'last_block': e, 'rows': rows},
                  open(ck, 'w'))
        print('%d-%d (%.1f%%) rows=%d' %
              (b, e, 100.0 * (e - A + 1) / (B - A + 1), len(rows)), flush=True)
        b = e + 1

    # resolve tx senders - the wallet that actually initiated each trade
    txs = sorted({r[5] for r in rows})
    print('resolving %d transaction senders' % len(txs), flush=True)
    sender = {}
    for i in range(0, len(txs), 50):
        grp = txs[i:i+50]
        req = urllib.request.Request(
            RPC, data=json.dumps([{'jsonrpc': '2.0', 'id': j,
                                   'method': 'eth_getTransactionByHash',
                                   'params': [h]} for j, h in enumerate(grp)]).encode(),
            headers={'Content-Type': 'application/json'})
        for _ in range(10):
            try:
                res = json.loads(urllib.request.urlopen(req, timeout=180).read())
                break
            except Exception:
                time.sleep(3)
        else:
            continue
        by = {r['id']: r.get('result') for r in res}
        for j, h in enumerate(grp):
            if by.get(j):
                sender[h] = by[j]['from'].lower()

    out = []
    for bn, li, f, d, v, h in rows:
        ts = int(bts(bn))
        val = int(v)
        p = px(ts)
        side = 'sell' if d == POOL else 'buy'      # into pool = sold, out = bought
        cp = f if d == POOL else d
        out.append({'block': bn, 'ts': ts,
                    'when_utc': datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S'),
                    'side': side, 'ake': val / 1e18, 'price': p, 'usd': val / 1e18 * p,
                    'counterparty': cp, 'cp_tags': cls(cp),
                    'trader': sender.get(h), 'trader_tags': cls(sender.get(h, '')),
                    'tx': h})
    out.sort(key=lambda r: (r['block'], r['side']))
    json.dump({'pool': POOL, 'from': A, 'to': B, 'n': len(out),
               'note': 'USD at the CoinGecko hourly AKE/USD rate interpolated to the '
                       'block timestamp, never a flat daily price. side=buy means AKE '
                       'left the pool (someone bought); side=sell means AKE entered it.',
               'trades': out}, open(OUT, 'w'), indent=1)
    print('wrote %s  (%d transfers)' % (OUT, len(out)), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
