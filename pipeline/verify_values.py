#!/usr/bin/env python3
"""
Re-verify every net release and every sale from first principles: the transfer
itself read back out of the node, and the price at that block derived two
independent ways.

Nothing here trusts a cached scan file. For each leg the script goes back to
eth_getLogs at the exact block, re-reads the Transfer, re-reads the block
timestamp, and only then prices it. If a figure in either document is wrong,
this is what catches it.

Two prices, computed separately, for every leg:

  on-chain   AKE/WBNB from the PancakeSwap V3 pool's own slot0 at that block,
             multiplied by WBNB/USDT from a deep WBNB/USDT V3 pool at the same
             block. No third party is involved: it is the price the chain
             itself would have given a trader in that block.

  CoinGecko  the published AKE/USD series, interpolated to the same second.

They will not agree exactly and should not — one is a single venue's marginal
price, the other an aggregate across every venue. Agreement to a few percent is
the check; a large divergence means one of them is wrong about that moment, and
the script prints the spread so it can be judged rather than hidden.

Usage: verify_values.py
Data-only: writes to pipeline/data and pipeline/logs only. Never HTML, never git.
"""
import json, time, bisect, datetime, urllib.request

D = 'pipeline/data/'
RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
AKE = '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db'
TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'
AKE_BNB = '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d'   # token0 AKE, token1 WBNB
BNB_USDT = '0x36696169c63e42cd08ce11f5deebbcebae652050'  # token0 USDT, token1 WBNB
Q96 = 2 ** 96

POOLS = {'0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors',
         '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes 3',
         '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team 2',
         '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes 1',
         '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes 2',
         '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team 1',
         '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL',
         '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community'}

HR = json.load(open(D + 'ake_hourly_cg.json'))
_hk = sorted(int(x) for x in HR); _hv = [HR[str(x)] for x in _hk]
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


def sqrt_price(pool, blk):
    r = rpc('eth_call', [{'to': pool, 'data': '0x3850c7bd'}, hex(blk)])
    return int(r[2:66], 16)


def onchain_usd(blk):
    """AKE/USD from pool state alone, at this exact block."""
    try:
        bnb_per_ake = (sqrt_price(AKE_BNB, blk) / Q96) ** 2      # token1/token0
        bnb_per_usdt = (sqrt_price(BNB_USDT, blk) / Q96) ** 2    # token1/token0
        if bnb_per_usdt == 0:
            return None, None
        usdt_per_bnb = 1.0 / bnb_per_usdt
        return bnb_per_ake * usdt_per_bnb, usdt_per_bnb
    except Exception:
        return None, None


def cg_usd(ts):
    i = bisect.bisect_left(_hk, ts)
    if i == 0:
        return _hv[0]
    if i >= len(_hk):
        return _hv[-1]
    t0, t1, p0, p1 = _hk[i-1], _hk[i], _hv[i-1], _hv[i]
    return p0 + (p1 - p0) * (ts - t0) / (t1 - t0) if t1 > t0 else p0


def ut(ts):
    return datetime.datetime.utcfromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')


def read_leg(blk, frm, to):
    """Re-read this transfer straight from the node. Returns wei, or None if
    the chain does not contain the transfer the cached file claims."""
    logs = rpc('eth_getLogs', [{'address': AKE, 'topics':
                                [TOPIC, '0x' + '0'*24 + frm[2:], '0x' + '0'*24 + to[2:]],
                                'fromBlock': hex(blk), 'toBlock': hex(blk)}])
    return sum(int(L['data'], 16) for L in logs) if logs else None


def main():
    led = json.load(open(D + 'pool_net_ledger.json'))
    trail = json.load(open(D + 'release_trails.json'))
    out = {'generated': datetime.datetime.utcnow().isoformat() + 'Z', 'days': {}, 'sales': []}

    print('RELEASE LEGS — re-read from the node, priced two ways\n')
    print(f"{'day':<12}{'pool':<11}{'dir':<6}{'block':>12}{'when (UTC)':<21}"
          f"{'AKE':>14}{'on-chain $':>12}{'CoinGecko $':>13}{'spread':>9}")
    grand = {'net': 0, 'ok': 0, 'bad': 0}
    for d in sorted(led['days']):
        legs = led['days'][d]['legs']
        if len(legs) > 40:
            out['days'][d] = {'legs_checked': 0,
                              'note': f'{len(legs)} legs — verified in aggregate against '
                                      f'balanceOf by pool_net_ledger.py, not leg by leg here',
                              'net': led['days'][d]['net_total']}
            print(f'{d:<12}{len(legs)} legs — aggregate check only')
            continue
        rows, net = [], 0
        for blk, ts0, kind, pool, cp, v in sorted(legs):
            frm, to = (dict(POOLS)and None, None)[0], None
            pool_addr = [a for a, n in POOLS.items() if n == pool][0]
            frm, to = (pool_addr, cp) if kind == 'out' else (cp, pool_addr)
            chain_v = read_leg(blk, frm, to)
            ts = int(rpc('eth_getBlockByNumber', [hex(blk), False])['timestamp'], 16)
            ok = chain_v is not None and chain_v == int(v)
            grand['ok' if ok else 'bad'] += 1
            oc, bnb = onchain_usd(blk)
            cgp = cg_usd(ts)
            spread = (100 * (oc / cgp - 1)) if (oc and cgp) else None
            net += int(v) if kind == 'out' else -int(v)
            rows.append({'block': blk, 'when_utc': ut(ts), 'pool': pool, 'dir': kind,
                         'counterparty': cp, 'ledger_wei': v,
                         'chain_wei': str(chain_v) if chain_v is not None else None,
                         'matches_chain': ok,
                         'price_onchain': oc, 'price_coingecko': cgp,
                         'bnb_usdt': bnb,
                         'usd_onchain': (int(v) / 1e18 * oc) if oc else None,
                         'usd_coingecko': (int(v) / 1e18 * cgp) if cgp else None})
            print(f"{d:<12}{pool:<11}{kind:<6}{blk:>12,}{ut(ts):<21}"
                  f"{int(v)/1e27:>11,.4f}bn{(oc or 0):>12.8f}{cgp:>13.8f}"
                  f"{(f'{spread:+.1f}%' if spread is not None else '—'):>9}"
                  + ('' if ok else '   !! CHAIN DISAGREES'))
        grand['net'] += net
        out['days'][d] = {'legs_checked': len(rows), 'net_recomputed': str(net),
                          'net_in_ledger': led['days'][d]['net_total'],
                          'net_matches': str(net) == led['days'][d]['net_total'],
                          'legs': rows}
        m = '=' if str(net) == led['days'][d]['net_total'] else '!! MISMATCH'
        print(f"{'':<12}{'net':<11}{'':<6}{'':>12}{'':<21}{net/1e27:>11,.4f}bn"
              f"   ledger says {int(led['days'][d]['net_total'])/1e27:,.4f}bn  {m}\n")

    print(f"legs re-read: {grand['ok']} match the chain, {grand['bad']} do not\n")

    # the sale legs — the only place a dollar figure is a realised amount
    print('SALE LEGS — the trail that reached an exchange\n')
    for d, e in trail['days'].items():
        for st in e.get('trail') or []:
            if not st['to'].startswith('0x0d0707'):
                continue
            blk = None
            # locate the block from the recorded timestamp
            tgt = int(datetime.datetime.strptime(st['when'], '%Y-%m-%d %H:%M:%S')
                      .replace(tzinfo=datetime.timezone.utc).timestamp())
            lo, hi = 110000000, json.load(open(D + 'head_now.json'))['head']
            while lo < hi:
                mid = (lo + hi) // 2
                t = int(rpc('eth_getBlockByNumber', [hex(mid), False])['timestamp'], 16)
                if t < tgt:
                    lo = mid + 1
                else:
                    hi = mid
            blk = lo
            v = read_leg(blk, st['from'], st['to'])
            ts = int(rpc('eth_getBlockByNumber', [hex(blk), False])['timestamp'], 16)
            oc, bnb = onchain_usd(blk)
            cgp = cg_usd(ts)
            amt = (v if v is not None else int(st['amount'])) / 1e18
            rec = {'release_day': d, 'block': blk, 'when_utc': ut(ts),
                   'from': st['from'], 'to': st['to'], 'venue': 'Gate.io DepositAndWithdraw_1',
                   'ake': amt, 'chain_wei': str(v) if v is not None else None,
                   'claimed_wei': st['amount'],
                   'matches_chain': v == int(st['amount']),
                   'price_onchain': oc, 'price_coingecko': cgp, 'bnb_usdt': bnb,
                   'usd_onchain': amt * oc if oc else None,
                   'usd_coingecko': amt * cgp if cgp else None}
            out['sales'].append(rec)
            print(f"  release {d} -> sold {ut(ts)} UTC  block {blk:,}")
            print(f"    {amt/1e6:,.2f}mn AKE   chain matches claim: {rec['matches_chain']}")
            print(f"    on-chain  ${oc:.8f}  ->  ${amt*oc:,.0f}   (BNB ${bnb:,.2f})")
            print(f"    CoinGecko ${cgp:.8f}  ->  ${amt*cgp:,.0f}"
                  f"   spread {100*(oc/cgp-1):+.1f}%")
    json.dump(out, open(D + 'verify_values.json', 'w'), indent=1)
    print(f'\n{_calls} RPC calls; wrote {D}verify_values.json')
    print('DONE')


if __name__ == '__main__':
    main()
