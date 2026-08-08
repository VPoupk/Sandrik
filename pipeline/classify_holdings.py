#!/usr/bin/env python3
"""
Classify every material AKE address at chain head into SOLD / HELD / PASSED-THROUGH
and cluster the holds. Sale = transfer to a non-Binance exchange, priced at the
CoinGecko daily average for the transfer date. Binance venues are tracked
separately because AKE is not listed on Binance spot. Data-only.
"""
import json, os, collections, bisect, datetime

D = 'pipeline/data/'
CG = json.load(open(D + 'ake_daily_prices_cg.json')); _pk = sorted(CG)
TS = json.load(open(D + 'blk_ts.json')); _tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def px(d):
    return CG[d] if d in CG else CG[_pk[max(0, bisect.bisect_right(_pk, d) - 1)]]


# --- venue classification, on-chain-label verified only -------------------
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
DEX = {'0x4d3bf29ba30f8bfe4624e7678709afa195689c5d': 'PancakeSwap V3 AKE/USDT'}


def load(name):
    p = D + name + '.json'
    return json.load(open(p)) if os.path.exists(p) else None


def merge_scans(names):
    """merge master_scan checkpoints into one recv/sent/byday view"""
    recv = collections.Counter(); sent = collections.Counter()
    byday = {}; big = []
    lo, hi = None, None
    for n in names:
        s = load(n)
        if not s:
            continue
        lo = s['from'] if lo is None else min(lo, s['from'])
        hi = s['last_block'] if hi is None else max(hi, s['last_block'])
        for k, v in s['recv'].items():
            recv[k] += int(v)
        for k, v in s['sent'].items():
            sent[k] += int(v)
        for k, v in s['byday'].items():
            t = byday.setdefault(k, collections.Counter())
            for d, x in v.items():
                t[d] += int(x)
        big += s['big']
    return recv, sent, byday, big, lo, hi


def main():
    recv, sent, byday, big, lo, hi = merge_scans(['master_recent', 'master_april'])
    print(f'merged scans cover blocks {lo:,} - {hi:,};  {len(recv):,} receiving addresses')

    def rollup(group):
        tot = 0.0; usd = 0.0; per = {}
        for a, nm in group.items():
            if a not in recv:
                continue
            t = recv[a] / 1e18; u = sum(x / 1e18 * px(d) for d, x in byday.get(a, {}).items())
            per[nm] = (t, u, a, sent.get(a, 0) / 1e18)
            tot += t; usd += u
        return tot, usd, per

    ct, cu, cper = rollup(CEX)
    dt, du, dper = rollup(DEX)
    bt, bu, bper = rollup(BINANCE)

    # net out internal exchange-to-exchange legs
    ex = set(CEX)
    internal = 0.0; internal_u = 0.0
    for bn, s, d, v in big:
        if s in ex and d in ex:
            v = int(v) / 1e18; dt_ = bd(bn)
            internal += v; internal_u += v * px(dt_)

    print('\n=== SALES (non-Binance exchange receipts) ===')
    for nm, (t, u, a, so) in sorted(cper.items(), key=lambda kv: -kv[1][0]):
        print(f'  {nm:30}{t/1e6:11.1f}mn  ${u:>13,.0f}')
    print(f'  {"gross":30}{ct/1e6:11.1f}mn  ${cu:>13,.0f}')
    print(f'  {"less exchange-internal legs":30}{-internal/1e6:11.1f}mn  ${-internal_u:>13,.0f}')
    print(f'  {"NET SALES":30}{(ct-internal)/1e6:11.1f}mn  ${cu-internal_u:>13,.0f}')

    print('\n=== DEX (two-way, net is the meaningful number) ===')
    for nm, (t, u, a, so) in dper.items():
        print(f'  {nm:30} in {t/1e6:10.1f}mn  out {so/1e6:10.1f}mn  NET {(t-so)/1e6:+10.1f}mn  (gross in ${u:,.0f})')

    print('\n=== BINANCE VENUES (AKE is not on Binance spot — reported separately) ===')
    for nm, (t, u, a, so) in sorted(bper.items(), key=lambda kv: -kv[1][0]):
        print(f'  {nm:30} in {t/1e6:10.1f}mn  out {so/1e6:10.1f}mn  net {(t-so)/1e6:+10.1f}mn')
    print(f'  {"TOTAL":30} in {bt/1e6:10.1f}mn')

    json.dump({'cex': {k: list(v) for k, v in cper.items()},
               'dex': {k: list(v) for k, v in dper.items()},
               'binance': {k: list(v) for k, v in bper.items()},
               'internal': internal, 'internal_usd': internal_u,
               'net_sales': ct - internal, 'net_sales_usd': cu - internal_u,
               'covers': [lo, hi]},
              open(D + 'classify_final.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
