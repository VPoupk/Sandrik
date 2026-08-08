#!/usr/bin/env python3
"""
Where the AKE ended up: sold, parked on Binance, or held.

Accounting rules (as instructed):
  * SALE   = AKE received by a non-Binance exchange custody address, valued at
             the CoinGecko daily average for the date of that transfer.
             Exchange-to-exchange legs are netted out - moving coins between two
             Gate.io wallets is not a sale.
  * DEX    = net inflow to the 19 AKE liquidity pools. Gross inflow counts the
             return leg of every arbitrage round-trip, so only net is a sale.
  * BINANCE= reported separately, never as a sale. AKE is not listed on Binance
             spot (Binance's own page says so), and Alpha is a custody venue
             whose deposit date is not a realisation date.
  * ROUTER = pass-through. A router receives and forwards inside one
             transaction; counting it would double count the pool leg.
  * HOLD   = balanceOf at head for any address that is not a venue.

Reads the four venue_s* segments, asserts they tile the token's entire life
with no gap and no overlap, and reconciles the result against balanceOf.
Data-only.
"""
import json, bisect, collections, datetime, os

D = 'pipeline/data/'
HEAD = 114_777_002
SEGS = [('venue_s1a.json', 57_840_341, 65_000_000),
        ('venue_s1b.json', 65_000_001, 72_500_000),
        ('venue_s1c.json', 72_500_001, 80_000_000),
        ('venue_s2.json', 80_000_001,  98_000_000),
        ('venue_s3.json', 98_000_001, 108_000_000),
        ('venue_s4.json', 108_000_001, HEAD)]

CG = json.load(open(D + 'ake_daily_prices_cg.json')); _pk = sorted(CG)
# venues.json is the full registry (pools, routers, exchanges); venues_scan.json
# is the subset the topic scan covered - exchange custody and Binance only. DEX
# pools are handled by balanceOf instead: they started empty, so their balance
# at head IS their net absorption, and scanning ~1.3M swap legs adds nothing.
V  = json.load(open(D + 'venues.json'))


def px(d):
    return CG[d] if d in CG else CG[_pk[max(0, bisect.bisect_right(_pk, d) - 1)]]


def load():
    """merge the venue segments; assert exact tiling"""
    agg = collections.defaultdict(lambda: collections.defaultdict(
        lambda: collections.defaultdict(lambda: [0, 0, 0, 0])))
    big, prev = [], None
    for fn, a, b in SEGS:
        p = D + fn
        if not os.path.exists(p):
            raise SystemExit(f'missing {fn} - venue scan not finished')
        s = json.load(open(p))
        if s['last_block'] != b:
            raise SystemExit(f'{fn} incomplete: at {s["last_block"]:,}, needs {b:,}')
        if prev is not None and a != prev + 1:
            raise SystemExit(f'gap/overlap before {fn}')
        prev = b
        for v, cp in s['agg'].items():
            for c, dd in cp.items():
                for d, q in dd.items():
                    t = agg[v][c][d]
                    t[0] += int(q[0]); t[1] += int(q[1]); t[2] += q[2]; t[3] += q[3]
        big += s['big']
    print(f'venue coverage {SEGS[0][1]:,} -> {HEAD:,}  (token deployed at 57,840,341)')
    return agg, big


def main():
    agg, big = load()
    VEN = set(V)

    # ---------- per venue: gross in, gross out, and in valued per transfer date
    stats = {}
    for v, cp in agg.items():
        gi = go = 0; usd_in = usd_out = 0.0
        ext_in = 0; ext_in_usd = 0.0          # inflow from NON-venue counterparties
        for c, dd in cp.items():
            for d, q in dd.items():
                gi += q[0]; go += q[1]
                usd_in  += q[0] / 1e18 * px(d)
                usd_out += q[1] / 1e18 * px(d)
                if c not in VEN:
                    ext_in += q[0]; ext_in_usd += q[0] / 1e18 * px(d)
        stats[v] = dict(name=V[v]['name'], group=V[v]['group'],
                        gin=gi, gout=go, usd_in=usd_in, usd_out=usd_out,
                        ext_in=ext_in, ext_in_usd=ext_in_usd)

    def block(grp):
        return sorted([s for s in stats.values() if s['group'] == grp],
                      key=lambda s: -s['ext_in'])

    print('\n' + '=' * 96)
    print('SALES  --  AKE deposited to non-Binance exchange custody, from outside the venue set')
    print('=' * 96)
    print(f'{"venue":36}{"deposits in":>14}{"USD at daily px":>18}{"sent back out":>16}')
    tin = 0; tusd = 0.0; tout = 0
    for s in block('cex'):
        print(f'  {s["name"]:34}{s["ext_in"]/1e24:>12,.1f}mn${s["ext_in_usd"]:>17,.0f}{s["gout"]/1e24:>14,.1f}mn')
        tin += s['ext_in']; tusd += s['ext_in_usd']; tout += s['gout']
    print(f'  {"TOTAL SOLD (CEX deposits)":34}{tin/1e24:>12,.1f}mn${tusd:>17,.0f}{tout/1e24:>14,.1f}mn')

    print('\n' + '=' * 96)
    print('DEX  --  net AKE absorbed by the 19 AKE liquidity pools (derived from balanceOf)')
    print('=' * 96)
    pb = json.load(open(D + 'pool_dex_bal.json'))
    dnet = 0
    for a, r in sorted(pb.items(), key=lambda kv: -int(kv[1]['bal'])):
        if int(r['bal']):
            print(f'  {r["name"]:34}{int(r["bal"])/1e24:>12,.1f}mn')
        dnet += int(r['bal'])
    print(f'  {"NET ABSORBED BY ALL POOLS":34}{dnet/1e24:>12,.1f}mn')
    print('  (pools were created empty, so balance at head == cumulative in minus cumulative out.')
    print('   This nets swap flow against liquidity provision, and is stated as such in the report.)')

    print('\n' + '=' * 96)
    print('BINANCE  --  reported separately; AKE is not listed on Binance spot')
    print('=' * 96)
    bi = bo = 0; busd_i = busd_o = 0.0
    for s in block('binance'):
        if s['gin'] or s['gout']:
            print(f'  {s["name"]:34} in {s["gin"]/1e24:>11,.1f}mn  out {s["gout"]/1e24:>11,.1f}mn'
                  f'  net {(s["gin"]-s["gout"])/1e24:>+11,.1f}mn')
        bi += s['gin']; bo += s['gout']; busd_i += s['usd_in']; busd_o += s['usd_out']
    print(f'  {"ALL BINANCE VENUES":34} in {bi/1e24:>11,.1f}mn  out {bo/1e24:>11,.1f}mn'
          f'  net {(bi-bo)/1e24:>+11,.1f}mn')
    print(f'  deposits valued per date ${busd_i:,.0f} ; withdrawals ${busd_o:,.0f}')

    print('\n' + '=' * 96)
    print('ROUTERS / AGGREGATORS  --  pass-through, excluded from every total above')
    print('=' * 96)
    for s in block('router'):
        if s['gin'] or s['gout']:
            print(f'  {s["name"]:34} in {s["gin"]/1e24:>11,.1f}mn  out {s["gout"]/1e24:>11,.1f}mn'
                  f'  net {(s["gin"]-s["gout"])/1e24:>+11,.1f}mn')

    # ---------- reconcile to balanceOf
    vb = json.load(open(D + 'venue_bal_head.json'))
    print('\n' + '=' * 96)
    print('RECONCILIATION  --  scanned (in - out) must equal balanceOf at head, per venue')
    print('=' * 96)
    bad = 0
    for v, s in sorted(stats.items(), key=lambda kv: -(kv[1]['gin'] - kv[1]['gout'])):
        want = int(vb[v]['bal']); got = s['gin'] - s['gout']
        if want != got:
            bad += 1
            print(f'  MISMATCH {s["name"]:32} scanned {got/1e24:>12,.4f}mn  '
                  f'balanceOf {want/1e24:>12,.4f}mn  diff {(got-want)/1e24:>+12,.4f}mn')
    print(f'  {len(stats)-bad}/{len(stats)} venues reconcile exactly to balanceOf'
          + ('' if not bad else '   <-- INVESTIGATE'))

    json.dump({'stats': {k: {kk: (str(vv) if isinstance(vv, int) else vv)
                             for kk, vv in s.items()} for k, s in stats.items()},
               'sold_ake': str(tin), 'sold_usd': tusd,
               'dex_net_absorbed': str(dnet),
               'binance_in': str(bi), 'binance_out': str(bo),
               'binance_in_usd': busd_i, 'binance_out_usd': busd_o,
               'reconciled': len(stats) - bad, 'venues': len(stats)},
              open(D + 'classify_final.json', 'w'), indent=1)
    print('\nwrote', D + 'classify_final.json')


if __name__ == '__main__':
    main()
