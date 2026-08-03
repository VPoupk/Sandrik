#!/usr/bin/env python3
"""
Analyse the node-buyback eligible wallet list:
  - full AKE (and USDT if scanned) flow per wallet, priced per transfer date
  - counterparty classification
  - cross-connection tests against the AKE insider set
Data-only. Writes pipeline/data/buyback_facts.json
"""
import json, os, bisect, datetime, collections, sys

D = 'pipeline/data/'
S = '/tmp/claude-0/-home-user-Sandrik/4d5dfae8-d9f1-59c8-a7af-703ef8978ed1/scratchpad/'
CG = json.load(open(D + 'ake_daily_prices_cg.json'))
TS = json.load(open(D + 'blk_ts.json')) if os.path.exists(D + 'blk_ts.json') else {}
_tb = sorted(int(k) for k in TS); _tv = [TS[str(b)] for b in _tb]
_pk = sorted(CG)

BB = json.load(open(S + 'buyback_addrs.json'))
BBS = set(BB)

# ---- known AKE-side entities -------------------------------------------
POOLS = {
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': 'Investors Pool',
    '0xaf66503770451c83a4f12a1146a32271893508ce': 'Nodes Pool 3',
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': 'Team Pool 2',
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62': 'Nodes Pool 1',
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b': 'Nodes Pool 2',
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': 'Team Pool 1',
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': 'KOL Pool',
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': 'Community Pool',
}
VENUES = {
    '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db': 'Binance Alpha 2.0',
    '0x6aba0315493b7e6989041c91181337b662fb1b90': 'Alpha Router',
    '0xb300000b72deaeb607a12d5f54773d1c19c7028d': 'Alpha Relayer',
    '0x653dd7677aea3030eab68c97ed3594bacf560158': 'Alpha Relayer 2',
    '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d': 'PancakeSwap AKE/USDT',
    '0x0d0707963952f2fba59dd06f2b425ace40b492fe': 'Gate.io 1',
    '0xc882b111a75c0c657fc507c04fbfcd2cc984f071': 'Gate.io 5',
    '0x53f78a071d04224b8e254e243fffc6d9f2f3fa23': 'KuCoin Hot Wallet 2',
}
# gas funders seen behind the AKE insider set
INSIDER_FUNDERS = {
    '0x515b72ed8a97f42c568d6a143232775018f133c8': 'Binance: Hot Wallet 12  (funded Alpha Feeder A)',
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': 'Binance 51  (funded Alpha Feeder C)',
    '0xdccf3b77da55107280bd850ea519df3705d1a75a': 'Binance: Hot Wallet 9  (funded Alpha Feeder E)',
    '0xbd612a3f30dca67bf60a39fd0d35e39b7ab80774': 'Binance: Hot Wallet 13  (funded Pool Drain Wallet 1)',
    '0x01c952174c24e1210d26961d456a77a39e1f0bb0': 'Binance: Hot Wallet 23  (funded the Whale Insider)',
    '0xf5988713400da6fc8a58ec9515e2b0df9b40b115': 'OKX: DepositAndWithdraw_173  (funded Twin Wallets A/B)',
    '0x635308e731a878741bfec299e67f5fd28c7553d9': 'KuCoin: DepositAndWithdraw_5  (funded all ten Jul-26 wallets)',
    '0x301218ba005e6eacf0d9433337483eca789c7617': 'relay wallet (funded the Silent Whale)',
}
INSIDERS = {
    '0x55a3319b1cfe8b82cacb0b5cf96c7445bf12066a': 'Whale Insider',
    '0x14804213c11a670ac7d9c82e9303a4db08dae296': 'Silent Whale',
    '0x3ce075da773fc527418613c1bd1f604993dd884b': 'Twin Wallet A',
    '0xf97ef431912f62e410d7ba14e3ccf2a45747111f': 'Twin Wallet B',
    '0x76e9225529b174cfadbd1bbde64caa753fa8bcc5': 'Batch Holder',
    '0xf23abe615b96badcf5e46d390d0697d433986aa4': 'Pool Drain Wallet 1',
    '0xa074027a3bb55b6f01989e20202f532894d7d97c': 'Pool Drain Wallet 2',
    '0xb40b35fe21be75f6e5c0b7dabab1ec87d87a1395': 'Alpha Feeder A',
    '0xb50de384e012a5f0fd80c4ce85bb6e679256f25c': 'Alpha Feeder B',
    '0xd49ef7def42f4633cd55cb874e016a570ea99f04': 'Alpha Feeder C',
    '0xcfb02194256652c650a02290804456e34e619daa': 'Alpha Feeder D',
    '0x6449b24d8dad7cef8ece12d7d5c8d0e0ef355a48': 'Alpha Feeder E',
    '0x07286aa168b3aa7d091048f090153162960c980b': 'Mega Forwarder',
    '0xc05210c6ba33a79682593b5c164848713c351e86': 'Merge Wallet',
    '0xe73b5aec494cbc76bbd79af4e01ae7da32584370': 'Cold Hold',
    '0x833753f3980c61c5b8f49ad07275b173bca52714': 'Fan-Out Root',
    '0x6468cce97a300ff9d02d4cad0d3e097cace2eac2': 'Supply Funder (deployer)',
    '0x551a841742733bef96646b44e3475ce6a01da5eb': 'Pool-owner Safe',
}
TEN = ['0x7986fa5f64a0997f3b50990f2ba64f81d829ff9c', '0x30a603dbd14981417b520ce96d2005d96c6fd275',
       '0xcfbbe27f7fb368d15d3a278da85415e62e9706fa', '0x998ef0e79a7574952d098d9b4e01f87d3fd864a8',
       '0xa8da77a990638b75963ac923e6cc617dc7e20377', '0x86ea348705c21fe04ed58061878b9bb507868dd4',
       '0xc970decb237c291b255b16884b9707c357250b26', '0xac7aea82b35320dd050c79e413234423894a321a',
       '0xe26c27d9c5fea9a032ea770d057338a46740213f', '0x248e4158b775444b8e33e5aa37a46524bf880b15']


def bdate(bn):
    bn = int(bn)
    if str(bn) in TS:
        t = TS[str(bn)]
    else:
        i = bisect.bisect_left(_tb, bn)
        if i == 0: t = _tv[0]
        elif i >= len(_tb): t = _tv[-1]
        else: t = _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def px(d):
    if d in CG: return CG[d]
    i = bisect.bisect_right(_pk, d) - 1
    return CG[_pk[max(0, i)]]


def label(a):
    return (POOLS.get(a) or VENUES.get(a) or INSIDERS.get(a)
            or ('another buyback wallet' if a in BBS else None))


def main():
    rows = json.load(open(D + 'buyback_scan_checkpoint.json'))['rows']
    seen = set(); uniq = []
    for r in rows:
        k = tuple(r)
        if k in seen: continue
        seen.add(k); uniq.append(r)
    print(f'AKE rows: {len(uniq)} unique of {len(rows)}')

    w = {a: {'in': 0.0, 'out': 0.0, 'in_usd': 0.0, 'out_usd': 0.0, 'n_in': 0, 'n_out': 0,
             'first': None, 'last': None, 'src': collections.Counter(),
             'dst': collections.Counter(), 'pool_in': 0.0, 'pool_in_usd': 0.0}
         for a in BB}
    for bn, s, t, v, h in uniq:
        v = int(v) / 1e18
        dt = bdate(bn); u = v * px(dt)
        if t in w:
            e = w[t]; e['in'] += v; e['in_usd'] += u; e['n_in'] += 1; e['src'][s] += v
            if s in POOLS: e['pool_in'] += v; e['pool_in_usd'] += u
            e['first'] = min(e['first'] or bn, bn); e['last'] = max(e['last'] or bn, bn)
        if s in w:
            e = w[s]; e['out'] += v; e['out_usd'] += u; e['n_out'] += 1; e['dst'][t] += v
            e['first'] = min(e['first'] or bn, bn); e['last'] = max(e['last'] or bn, bn)

    for a, e in w.items():
        e['src'] = [[x, y, label(x)] for x, y in e['src'].most_common(8)]
        e['dst'] = [[x, y, label(x)] for x, y in e['dst'].most_common(8)]
        e['first_date'] = bdate(e['first']) if e['first'] else None
        e['last_date'] = bdate(e['last']) if e['last'] else None

    out = {'wallets': w, 'n': len(BB)}

    # ---- USDT, if scanned -------------------------------------------------
    up = D + 'buyback_usdt_checkpoint.json'
    if os.path.exists(up):
        ur = json.load(open(up))
        us = {a: {'in': 0.0, 'out': 0.0, 'n_in': 0, 'n_out': 0,
                  'src': collections.Counter(), 'dst': collections.Counter()} for a in BB}
        seen = set()
        for bn, s, t, v, h in ur['rows']:
            k = (bn, s, t, v, h)
            if k in seen: continue
            seen.add(k)
            v = int(v) / 1e18
            if t in us: us[t]['in'] += v; us[t]['n_in'] += 1; us[t]['src'][s] += v
            if s in us: us[s]['out'] += v; us[s]['n_out'] += 1; us[s]['dst'][t] += v
        for a, e in us.items():
            e['src'] = [[x, y, label(x)] for x, y in e['src'].most_common(8)]
            e['dst'] = [[x, y, label(x)] for x, y in e['dst'].most_common(8)]
        out['usdt'] = us
        out['usdt_scanned_to'] = ur['last_block']

    # ---- gas funders ------------------------------------------------------
    gp = D + 'gas_buyback.json'
    if os.path.exists(gp):
        g = json.load(open(gp))
        out['gas'] = {a: {'block': v.get('block'),
                          'ts': v.get('ts'),
                          'funders': [[f['from'], f['bnb']] for f in v.get('funders', [])],
                          'insider_link': [INSIDER_FUNDERS[f['from'].lower()]
                                           for f in v.get('funders', [])
                                           if f['from'].lower() in INSIDER_FUNDERS]}
                      for a, v in g.items()}

    json.dump(out, open(D + 'buyback_facts.json', 'w'), indent=1, default=str)
    print('buyback_facts.json written')

    tot_in = sum(e['in'] for e in w.values()); tot_out = sum(e['out'] for e in w.values())
    print(f'AKE in  {tot_in/1e6:12.3f}mn  (${sum(e["in_usd"] for e in w.values()):,.0f} at per-date prices)')
    print(f'AKE out {tot_out/1e6:12.3f}mn  (${sum(e["out_usd"] for e in w.values()):,.0f})')
    print(f'from project pools: {sum(e["pool_in"] for e in w.values())/1e6:.3f}mn '
          f'(${sum(e["pool_in_usd"] for e in w.values()):,.0f})')


if __name__ == '__main__':
    main()
