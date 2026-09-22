#!/usr/bin/env python3
"""
Check the figures this project reports against independent published sources,
and record every place they disagree.

The standing rule on this work is to take facts from the chain rather than from
aggregators. That rule is about sourcing, not about humility: an aggregator
that disagrees with the chain is either wrong or measuring something else, and
either way the disagreement is worth knowing. This script therefore pulls
CoinGecko's market and ticker data, compares it to what the chain says, and
writes the result — agreements and contradictions both — so the document can
show its own audit rather than assert accuracy.

What it checks:
  - totalSupply() and decimals against the published supply
  - the eight pools' balances against the "locked" figure the vesting
    trackers publish
  - the venue registry against CoinGecko's ticker list, to find exchanges
    carrying real volume that this project has no custody address for
  - the hourly price series against the OHLC candles, because a series of
    hourly marks cannot show an intraday spike and this token had a 3x one

Usage: thirdparty_check.py
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, urllib.request, time, datetime, collections

D = 'pipeline/data/'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}


def rpc(m, p, tries=8):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': m,
                                      'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(r, timeout=120).read())
            if 'error' in j:
                raise RuntimeError(j['error'])
            return j['result']
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 * 1.6 ** i)


def main():
    cgm = json.load(open(D + 'cg_market_now.json'))
    md = cgm['market_data']
    head = int(rpc('eth_blockNumber', []), 16)
    ts = int(rpc('eth_getBlockByNumber', [hex(head), False])['timestamp'], 16)

    sup = int(rpc('eth_call', [{'to': AKE, 'data': '0x18160ddd'}, hex(head)]), 16)
    dec = int(rpc('eth_call', [{'to': AKE, 'data': '0x313ce567'}, hex(head)]), 16)
    locked = 0
    perpool = {}
    for a, n in POOLS.items():
        b = int(rpc('eth_call', [{'to': AKE, 'data': '0x70a08231' + '0'*24 + a[2:]},
                                 hex(head)]), 16)
        perpool[n] = str(b)
        locked += b

    checks = []

    def add(what, mine, theirs, src, verdict, note=''):
        checks.append({'what': what, 'chain': mine, 'published': theirs,
                       'source': src, 'verdict': verdict, 'note': note})

    add('Contract address', AKE, cgm.get('contract_address'),
        'CoinGecko /coins/akedo',
        'match' if cgm.get('contract_address', '').lower() == AKE else 'MISMATCH')
    add('Total supply', f'{sup/1e18:,.0f}', f"{md.get('total_supply'):,.0f}",
        'CoinGecko', 'match' if abs(sup/1e18 - md['total_supply']) < 1 else 'MISMATCH')
    add('Decimals', str(dec), '18', 'contract / standard',
        'match' if dec == 18 else 'MISMATCH')
    add('Max supply', f'{sup/1e18:,.0f}', f"{md.get('max_supply'):,.0f}",
        'CoinGecko', 'match' if md.get('max_supply') == 100e9 else 'MISMATCH')

    # The one that matters: what "locked" means
    dropstab_locked = 52.77e27
    add('Tokens held inside the eight allocation-pool contracts',
        f'{locked/1e27:,.4f}bn', f'{dropstab_locked/1e27:,.2f}bn reported as "locked"',
        'DropsTab vesting page',
        'DIFFERENT THINGS',
        'The published figure is schedule accounting — tokens not yet due under a '
        'published vesting plan. The chain figure is the only supply a contract can '
        f'actually stop anyone moving. The gap, {(dropstab_locked-locked)/1e27:,.2f}bn, '
        'sits in ordinary wallets that can transact at any moment.')
    add('Circulating supply', 'not a chain concept',
        f"{md.get('circulating_supply'):,.0f}", 'CoinGecko', 'not comparable',
        f'For scale: exchange custody addresses in this project\'s registry hold far '
        f'less than the published circulating figure, and {locked/1e27:,.2f}bn is in '
        'the pools. Circulating is derived from the vesting plan, not measured.')
    add('Market cap', 'n/a', f"${md['market_cap']['usd']:,.0f}", 'CoinGecko', 'noted',
        f"FDV ${md.get('fully_diluted_valuation',{}).get('usd',0):,.0f}. The ratio "
        'between them is entirely a function of the circulating figure above.')

    # price: hourly marks vs candles
    HR = json.load(open(D + 'ake_hourly_cg.json'))
    hk = sorted(int(x) for x in HR)
    ohlc = json.load(open(D + 'cg_daily_ohlc.json'))
    gapdays = []
    for d, r in ohlc.items():
        hrs = [HR[str(k)] for k in hk
               if datetime.datetime.utcfromtimestamp(k).strftime('%Y-%m-%d') == d]
        if not hrs:
            continue
        gapdays.append({'day': d, 'hourly_max': max(hrs), 'hourly_min': min(hrs),
                        'candle_high': r['h'], 'candle_low': r['l'],
                        'high_understated_pct': 100 * (r['h'] / max(hrs) - 1),
                        'true_range_pct': 100 * (r['l'] / r['h'] - 1)})
    gapdays.sort(key=lambda x: -x['high_understated_pct'])
    out_gapdays = gapdays[:6]
    if gapdays:
        g = gapdays[0]
        add('Intraday high', f"${g['hourly_max']:.8f} (highest hourly mark on {g['day']})",
            f"${g['candle_high']:.8f} (candle high, same day)", 'CoinGecko OHLC',
            'HOURLY SERIES UNDERSTATES',
            'An hourly series records a price once an hour; it cannot show a spike that '
            'begins and ends inside the hour. On ' + g['day'] + ' it missed the top by '
            f"{g['high_understated_pct']:.0f}%. Every peak-to-trough claim in this "
            'document is now taken from candles, not from hourly marks. Per-transfer USD '
            'is still the hourly rate, because that values a transfer at a moment rather '
            'than describing a range.')
        for g in gapdays:
            if g['day'] == '2026-09-20':
                add('The 20 September spike and fall',
                    f"hourly marks peak at ${g['hourly_max']:.8f}",
                    f"candle high ${g['candle_high']:.8f}, candle low ${g['candle_low']:.8f}",
                    'CoinGecko OHLC', 'EARLIER FIGURE CORRECTED',
                    f"The real move was {g['true_range_pct']:.1f}% peak to trough inside "
                    'the day, against the −49.6% an hourly series showed. The hourly '
                    'reading was not wrong about direction, it was wrong about size.')

    # venue coverage
    V = json.load(open(D + 'venues_scan.json'))
    covered = {(v.get('name') or '').split('.')[0].strip().lower() for v in V.values()}
    gaps, dexvol, cexvol = [], 0.0, 0.0
    for t in cgm.get('tickers', []):
        vol = t.get('converted_volume', {}).get('usd') or 0
        nm = t['market']['name']
        if t['base'].startswith('0X'):
            dexvol += vol
            continue
        cexvol += vol
        key = nm.split()[0].lower().replace('.com', '')
        if not any(key.startswith(c) or c.startswith(key) for c in covered if c):
            gaps.append({'venue': nm, 'volume_usd': vol})
    gaps.sort(key=lambda x: -x['volume_usd'])
    gapvol = sum(g['volume_usd'] for g in gaps)
    add('Exchange coverage',
        f'{len(V)} custody addresses covering {len(covered)} venues',
        f'{len(gaps)} venue(s) with volume and no custody address here',
        'CoinGecko ticker list',
        'COVERAGE GAP' if gaps else 'complete',
        f'${gapvol:,.0f} of ${cexvol+dexvol:,.0f} reported 24h volume '
        f'({100*gapvol/(cexvol+dexvol):.1f}%) trades on venues this project cannot see '
        'deposits to: ' + ', '.join(g['venue'] for g in gaps) + '. Exchange-deposit '
        'figures in this document are therefore a floor, not a total.')

    binance_listed = any('binance' in t['market']['name'].lower()
                         for t in cgm.get('tickers', []))
    add('Is AKE listed on Binance spot?', 'n/a',
        'yes' if binance_listed else 'no — Binance does not appear in the ticker list',
        'CoinGecko ticker list', 'noted',
        'This matters for the accounting rule used throughout: flows to Binance-labelled '
        'wallets are treated separately from sales precisely because they are not spot '
        'order-book deposits.')

    out = {'generated': datetime.datetime.utcnow().isoformat() + 'Z',
           'head_block': head, 'head_utc': datetime.datetime.utcfromtimestamp(ts).isoformat(),
           'total_supply': str(sup), 'decimals': dec,
           'pool_balances': perpool, 'pools_total': str(locked),
           'cg': {'price': md['current_price']['usd'],
                  'market_cap': md['market_cap']['usd'],
                  'fdv': md.get('fully_diluted_valuation', {}).get('usd'),
                  'volume_24h': md['total_volume']['usd'],
                  'circulating': md.get('circulating_supply'),
                  'total_supply': md.get('total_supply'),
                  'ath': md['ath']['usd'], 'ath_date': md['ath_date']['usd'],
                  'last_updated': cgm.get('last_updated')},
           'venue_gaps': gaps, 'dex_volume_24h': dexvol, 'cex_volume_24h': cexvol,
           'hourly_vs_candles': out_gapdays,
           'checks': checks}
    json.dump(out, open(D + 'thirdparty_check.json', 'w'), indent=1)

    print(f'head {head:,}  {datetime.datetime.utcfromtimestamp(ts)} UTC\n')
    for c in checks:
        print(f"{c['verdict']:<28}{c['what']}")
        print(f"     chain     : {c['chain']}")
        print(f"     published : {c['published']}   [{c['source']}]")
        if c['note']:
            print(f"     -> {c['note']}")
        print()
    print(f'wrote {D}thirdparty_check.json')
    print('DONE')


if __name__ == '__main__':
    main()
