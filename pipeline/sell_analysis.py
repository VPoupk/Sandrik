#!/usr/bin/env python3
"""
Classify every AKE destination since the Jul-26 pool unlocks and price the
exchange sends at the CoinGecko daily average for the day of the transfer.
Binance venues are tracked separately and excluded from the "sold" total,
per the analysis definition. Data-only.
"""
import json, collections, bisect

D = 'pipeline/data/'
S = json.load(open(D + 'sells_jul26_agg.json'))
CG = json.load(open(D + 'ake_daily_prices_cg.json'))
_pk = sorted(CG)


def px(d):
    return CG[d] if d in CG else CG[_pk[max(0, bisect.bisect_right(_pk, d) - 1)]]


# ---- venue classification ------------------------------------------------
BINANCE = {
    '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db': 'Binance Alpha 2.0',
    '0x6aba0315493b7e6989041c91181337b662fb1b90': 'Alpha Router',
    '0xb300000b72deaeb607a12d5f54773d1c19c7028d': 'Alpha Relayer',
    '0x653dd7677aea3030eab68c97ed3594bacf560158': 'Alpha Relayer 2',
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': 'Binance 51',
    '0x515b72ed8a97f42c568d6a143232775018f133c8': 'Binance: Hot Wallet 12',
    '0xdccf3b77da55107280bd850ea519df3705d1a75a': 'Binance: Hot Wallet 9',
    '0xbd612a3f30dca67bf60a39fd0d35e39b7ab80774': 'Binance: Hot Wallet 13',
    '0x01c952174c24e1210d26961d456a77a39e1f0bb0': 'Binance: Hot Wallet 23',
    '0xf977814e90da44bfa03b6295a0616a897441acec': 'Binance: Hot Wallet 20',
    '0xeb2d2f1b8c558a40207669291fda468e50c8a0bb': 'Binance: Hot Wallet 10',
    '0x631fc1ea2270e98fbd9d92658ece0f5a269aa161': 'Binance: Hot Wallet',
}
CEX = {
    '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'Gate.io 1',
    '0xc882b111a75c0c657fc507c04fbfcd2cc984f071': 'Gate.io 5',
    '0x53f78a071d04224b8e254e243fffc6d9f2f3fa23': 'KuCoin: Hot Wallet 2',
    '0x635308e731a878741bfec299e67f5fd28c7553d9': 'KuCoin: DepositAndWithdraw_5',
    '0xf5988713400da6fc8a58ec9515e2b0df9b40b115': 'OKX: DepositAndWithdraw_173',
    '0x7c0629bbbaf7d68ffaa393e3fedc9b633679fa5f': 'OKX: Hot Wallet',
    '0x559432e18b281731c054cd703d4b49872be4ed53': 'OKX: Hot Wallet 5',
    '0x6cc5f688a315f3dc28a7781717a9a798a59fda7b': 'OKX',
    '0x3b5a23f6207d87b423c6789d2625ea620423b32d': 'OKX 35',
}
DEX = {
    '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d': 'PancakeSwap V3 AKE/USDT',
}
# cohorts on the sending side
TEN = {
    '0x7986fa5f64a0997f3b50990f2ba64f81d829ff9c': 'Pool Recipient 1',
    '0x30a603dbd14981417b520ce96d2005d96c6fd275': 'Pool Recipient 2',
    '0xcfbbe27f7fb368d15d3a278da85415e62e9706fa': 'Pool Recipient 3',
    '0x998ef0e79a7574952d098d9b4e01f87d3fd864a8': 'Pool Recipient 4',
    '0xa8da77a990638b75963ac923e6cc617dc7e20377': 'Pool Recipient 5',
    '0x86ea348705c21fe04ed58061878b9bb507868dd4': 'Pool Recipient 6',
    '0xc970decb237c291b255b16884b9707c357250b26': 'Pool Recipient 7',
    '0xac7aea82b35320dd050c79e413234423894a321a': 'Pool Recipient 8',
    '0xe26c27d9c5fea9a032ea770d057338a46740213f': 'Pool Recipient 9',
    '0x248e4158b775444b8e33e5aa37a46524bf880b15': 'Pool Recipient 10',
}


def main():
    recv = {k: int(v) / 1e18 for k, v in S['recv'].items()}
    byday = {k: {d: int(x) / 1e18 for d, x in v.items()} for k, v in S['byday'].items()}

    def rollup(group):
        tot = 0.0; usd = 0.0
        days = collections.Counter(); dusd = collections.Counter()
        per = {}
        for a, nm in group.items():
            if a not in recv:
                continue
            t = recv[a]; u = 0.0
            for d, x in byday.get(a, {}).items():
                u += x * px(d); days[d] += x; dusd[d] += x * px(d)
            per[nm] = (t, u, a)
            tot += t; usd += u
        return tot, usd, per, days, dusd

    cex_t, cex_u, cex_per, cex_days, cex_dusd = rollup(CEX)
    dex_t, dex_u, dex_per, dex_days, dex_dusd = rollup(DEX)
    bin_t, bin_u, bin_per, _, _ = rollup(BINANCE)

    print(f'Window: block {S["last_block"]:,} back to 112,252,392 (26 Jul 2026 13:43 UTC)')
    print(f'distinct receiving addresses: {len(recv)}\n')
    print('=== NON-BINANCE CEX SENDS (counted as sells) ===')
    for nm, (t, u, a) in sorted(cex_per.items(), key=lambda kv: -kv[1][0]):
        print(f'  {nm:30} {t/1e6:10.1f}mn  ${u:>12,.0f}   {a}')
    print(f'  {"TOTAL CEX (ex-Binance)":30} {cex_t/1e6:10.1f}mn  ${cex_u:>12,.0f}')
    print()
    print('=== DEX SENDS ===')
    for nm, (t, u, a) in sorted(dex_per.items(), key=lambda kv: -kv[1][0]):
        print(f'  {nm:30} {t/1e6:10.1f}mn  ${u:>12,.0f}   {a}')
    print(f'  {"TOTAL DEX (gross in)":30} {dex_t/1e6:10.1f}mn  ${dex_u:>12,.0f}')
    sent = {k: int(v) / 1e18 for k, v in S['sent'].items()}
    for a, nm in DEX.items():
        out = sent.get(a, 0.0)
        print(f'  {"  " + nm + " — AKE OUT (buys)":30} {out/1e6:10.1f}mn')
        print(f'  {"  net directional sell":30} {(recv.get(a,0)-out)/1e6:10.1f}mn')
    print()
    print('=== BINANCE VENUES (excluded from the sold total, shown for scale) ===')
    for nm, (t, u, a) in sorted(bin_per.items(), key=lambda kv: -kv[1][0]):
        print(f'  {nm:30} {t/1e6:10.1f}mn  ${u:>12,.0f}')
    print(f'  {"TOTAL BINANCE":30} {bin_t/1e6:10.1f}mn  ${bin_u:>12,.0f}')
    print()
    print('=== NON-BINANCE EXCHANGE SENDS BY DAY ===')
    print(f'{"date":12}{"CEX AKE":>13}{"DEX AKE":>13}{"price":>13}{"CEX $":>13}{"DEX $":>13}')
    alld = sorted(set(cex_days) | set(dex_days))
    for d in alld:
        print(f'{d:12}{cex_days.get(d,0)/1e6:12.1f}m{dex_days.get(d,0)/1e6:12.1f}m'
              f'{px(d):>13.8f}${cex_dusd.get(d,0):>12,.0f}${dex_dusd.get(d,0):>12,.0f}')
    print(f'{"TOTAL":12}{cex_t/1e6:12.1f}m{dex_t/1e6:12.1f}m{"":>13}${cex_u:>12,.0f}${dex_u:>12,.0f}')

    # who sent the big ones
    print('\n=== TRANSFERS >= 5mn INTO A NON-BINANCE VENUE ===')
    tgt = set(CEX) | set(DEX)
    rows = [r for r in S['big'] if r[2] in tgt]
    print(f'{len(rows)} such transfers')
    agg = collections.Counter()
    for bn, s, d, v in rows:
        agg[(s, CEX.get(d) or DEX.get(d))] += int(v) / 1e18
    for (s, d), v in agg.most_common(20):
        tag = TEN.get(s, '')
        print(f'  {s} {("["+tag+"]") if tag else "":22} -> {d:26} {v/1e6:9.1f}mn')

    json.dump({'cex': {k: list(v) for k, v in cex_per.items()},
               'dex': {k: list(v) for k, v in dex_per.items()},
               'binance': {k: list(v) for k, v in bin_per.items()},
               'cex_days': dict(cex_days), 'cex_dusd': dict(cex_dusd),
               'dex_days': dict(dex_days), 'dex_dusd': dict(dex_dusd),
               'totals': {'cex': [cex_t, cex_u], 'dex': [dex_t, dex_u],
                          'binance': [bin_t, bin_u]},
               'last_block': S['last_block']},
              open(D + 'sell_breakdown.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
