#!/usr/bin/env python3
"""
Who sold the AKE that reached a non-Binance exchange after the July unlocks,
and where did each seller get it.

Every deposit is valued at the CoinGecko HOURLY price interpolated to the
block's own timestamp, not a daily average - the July/August price moved far
too fast for a daily mean to be honest.

Provenance is resolved by walking each seller's inbound transfers back up to
three hops, stopping at the first of: an allocation pool, a known insider or
gas-clustered wallet, Binance custody, or another exchange. A seller with no
inbound in the scanned window held its AKE before the window opened and is
labelled as such rather than guessed at.

Data-only. Writes pipeline/data/sale_clusters.json.
"""
import json, collections, bisect, datetime

D = 'pipeline/data/'
TS = json.load(open(D + 'blk_ts.json')); _tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]
H = json.load(open(D + 'ake_hourly_cg.json')); _hk = sorted(int(k) for k in H)
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
INSIDER = {
    '0x55a3319b1cfe8b82cacb0b5cf96c7445bf12066a': 'Whale Insider',
    '0xb40b35fe21be75f6e5c0b7dabab1ec87d87a1395': 'Alpha Feeder A',
    '0xb50de384e012a5f0fd80c4ce85bb6e679256f25c': 'Alpha Feeder B',
    '0xd49ef7def42f4633cd55cb874e016a570ea99f04': 'Alpha Feeder C',
    '0xcfb02194256652c650a02290804456e34e619daa': 'Alpha Feeder D',
    '0x6449b24d8dad7cef8ece12d7d5c8d0e0ef355a48': 'Alpha Feeder E',
    '0xf23abe615b96badcf5e46d390d0697d433986aa4': 'Pool Drain Wallet 1',
    '0xa074027a3bb55b6f01989e20202f532894d7d97c': 'Pool Drain Wallet 2',
    '0x833753f3980c61c5b8f49ad07275b173bca52714': 'Fan-Out Root',
    '0xe73b5aec494cbc76bbd79af4e01ae7da32584370': 'Cold Hold',
    '0x57bdb6b8ee3e755b4df96cc127d97ca5f48ca775': 'Sub-Distributor 1',
    '0x7cd7a04d3730df6e49e1edacb6ded8a1fef5d856': 'Sub-Distributor 2',
    '0x7aa852b62ece614caa9673a9fcde62729becce55': 'Sub-Distributor 3',
    '0x07286aa168b3aa7d091048f090153162960c980b': 'Mega Forwarder',
    '0xc05210c6ba33a79682593b5c164848713c351e86': 'Merge Wallet',
}
CLUSTER_FUNDER = {
    '0x635308e731a878741bfec299e67f5fd28c7553d9': 'userWithdraw cohort (KuCoin-funded, 26 Jul)',
    '0x5ba434b40be6cfc7033bf8d4545320fa609a4268': '22-Jul cluster',
    '0x33387a9a5ffec880487d62f6c7642cdf94fa276f': '22-Jul cluster',
    '0x78a769774684ae68265d2c1d850b975aa7fe87fd': '22-Jul cluster',
}
for a, r in json.load(open(D + 'gas_top60.json')).items():
    for x in (r.get('funders') or []):
        if x['from'].lower() in CLUSTER_FUNDER:
            INSIDER.setdefault(a.lower(), CLUSTER_FUNDER[x['from'].lower()])


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    return _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                                  _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))


def hpx(ts):
    """CoinGecko hourly price linearly interpolated to the exact block time"""
    i = bisect.bisect_left(_hk, int(ts))
    if i == 0:
        return H[str(_hk[0])]
    if i >= len(_hk):
        return H[str(_hk[-1])]
    a, b = _hk[i-1], _hk[i]
    return H[str(a)] + (H[str(b)] - H[str(a)]) * (ts - a) / (b - a)


def load_inbound():
    """counterparty -> total received, merged across every provenance scan"""
    inb = collections.defaultdict(collections.Counter)
    for fn in ('seller_src.json', 'lvl2_src.json'):
        try:
            s = json.load(open(D + fn))
        except Exception:
            continue
        for w, cp in s['agg'].items():
            for c, dd in cp.items():
                for d, q in dd.items():
                    if int(q[0]) > 0:
                        inb[w][c] += int(q[0])
    return inb


def main():
    inb = load_inbound()
    dep = json.load(open(D + 'cex_deposits_all.json'))

    # direct pool recipients, lifetime - used to detect a pool origin at any hop
    poolrec = set()
    _rows = {}
    for _f in ('poolflow_a', 'poolflow_b', 'poolflow_c'):
        for r in json.load(open(D + _f + '.json'))['rows']:
            _rows[(r[0], r[5])] = r
    for bn, f, t, v, tx, li in _rows.values():
        if f in POOLS and t not in POOLS:
            poolrec.add(t)

    def classify(a, depth=0, seen=None):
        """walk upstream to the first meaningful origin, up to 5 hops"""
        seen = seen or set()
        a = a.lower()
        if a in POOLS:
            return POOLS[a], 'Allocation pool (claimed direct)'
        if a in INSIDER:
            return INSIDER[a], 'Insider chain / clustered wallet'
        if a in V:
            g = V[a]['group']
            if g == 'binance':
                return V[a]['name'], 'Binance Alpha'
            if g == 'cex':
                return V[a]['name'], 'Another exchange'
            if g == 'dex_pool':
                return V[a]['name'], 'Bought on a DEX'
            return V[a]['name'], 'Router / aggregator'
        if depth > 0 and a in poolrec:
            return a, 'Pool claimant, sold through an intermediary'
        if depth >= 5 or a in seen:
            return None, None
        seen.add(a)
        src = inb.get(a)
        if not src:
            return None, None
        for c, _ in src.most_common(4):
            n, g = classify(c, depth + 1, seen)
            if g:
                return n, g
        return None, None

    def describe(a):
        """terminal origin, else name the immediate funder rather than guess"""
        n, g = classify(a)
        if g:
            return n, g
        src = inb.get(a)
        if not src:
            return '—', 'Held before 28 May 2026 (no inbound in scan window)'
        top = src.most_common(1)[0][0]
        nm = (lab.get(top, {}) or {}).get('entity') or top[:12] + '\u2026'
        return nm, 'Unlabelled wallet chain (origin not resolved in 5 hops)'

    per = collections.Counter(); peru = collections.Counter()
    grp = collections.Counter(); grpu = collections.Counter()
    wallets = collections.defaultdict(set)
    detail = collections.defaultdict(lambda: [0, 0.0])
    venue = collections.Counter(); venueu = collections.Counter()
    rows_out = []
    for bn, ts, f, t, v, tx in dep:
        d = datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
        if d < '2026-07-22':
            continue
        v = int(v); usd = v / 1e18 * hpx(ts)
        name, g = describe(f)
        grp[g] += v; grpu[g] += usd; wallets[g].add(f)
        detail[(g, name)][0] += v; detail[(g, name)][1] += usd
        venue[V[t]['name']] += v; venueu[V[t]['name']] += usd
        per[f] += v; peru[f] += usd
        rows_out.append([bn, ts, f, t, str(v), usd, name, g, tx])

    tot = sum(grp.values()); totu = sum(grpu.values())
    print(f'SALES 22 Jul – 20 Aug 2026, priced at the CoinGecko hourly rate at each deposit')
    print(f'{tot/1e24:,.1f}mn AKE   ${totu:,.0f}   {len(per):,} selling wallets   {len(rows_out):,} deposits\n')
    print(f'{"source cluster":52}{"wallets":>8}{"AKE":>12}{"USD":>15}{"share":>8}')
    for g, v in grp.most_common():
        print(f'  {g:50}{len(wallets[g]):>8}{v/1e24:>10,.1f}mn${grpu[g]:>14,.0f}{100*grpu[g]/totu:>7,.1f}%')
    print(f'  {"TOTAL":50}{len(per):>8}{tot/1e24:>10,.1f}mn${totu:>14,.0f}')

    print(f'\n{"named origin":52}{"AKE":>12}{"USD":>15}')
    for (g, n), (v, u) in sorted(detail.items(), key=lambda kv: -kv[1][1])[:18]:
        print(f'  {(n + "  [" + g + "]")[:50]:50}{v/1e24:>10,.1f}mn${u:>14,.0f}')

    print(f'\n{"exchange":34}{"AKE":>12}{"USD":>15}')
    for k, v in venue.most_common():
        print(f'  {k:32}{v/1e24:>10,.1f}mn${venueu[k]:>14,.0f}')

    json.dump({'rows': rows_out,
               'groups': {g: [str(grp[g]), grpu[g], sorted(wallets[g])] for g in grp},
               'detail': {f'{g}|{n}': [str(v), u] for (g, n), (v, u) in detail.items()},
               'venues': {k: [str(venue[k]), venueu[k]] for k in venue},
               'sellers': {a: [str(per[a]), peru[a]] for a in per},
               'total_ake': str(tot), 'total_usd': totu},
              open(D + 'sale_clusters.json', 'w'))
    print('\nwrote', D + 'sale_clusters.json')


if __name__ == '__main__':
    main()
