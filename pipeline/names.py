#!/usr/bin/env python3
"""Canonical wallet nickname registry for the AKE analysis.
Every address that appears in ake-analysis.html resolves through here so the
same wallet always carries the same functional nickname."""

NAMES = {
    # --- launch / supply ---
    '0x6468cce97a300ff9d02d4cad0d3e097cace2eac2': ('Supply Funder',        'deployer EOA; held 100bn at genesis and sent all 11 launch allocations'),
    '0x2c3a8ee94ddd97244a93bc48298f97d2c412f7db': ('AKE Token',            'BEP-20 contract'),

    # --- pool contracts ---
    '0x27333bd8c321a263b0565e69eea3b736b9d1f42c': ('Investors Pool',       'ERC1967 proxy, 25bn at launch'),
    '0xaf66503770451c83a4f12a1146a32271893508ce': ('Nodes Pool 3',         'ERC1967 proxy, 16bn at launch'),
    '0xd229b65d50e412cc3c394233e7a53a1dac4da457': ('Team Pool 2',          'ERC1967 proxy, 15bn at launch'),
    '0xb7c7786b6ca1130584f005e9c86554114b7fad62': ('Nodes Pool 1',         'ERC1967 proxy, 8bn at launch'),
    '0xd2f72669e560c7ecd3c681612963990ef6f1981b': ('Nodes Pool 2',         'ERC1967 proxy, 7.5bn at launch'),
    '0x9009342f6d3b2f685fc9f5fe4dc9d3e30ed0e248': ('Team Pool 1',          'ERC1967 proxy, 5bn at launch'),
    '0xbd6ae2b2a7414934327e2a7da1a8691c792f9ad5': ('KOL Pool',             'ERC1967 proxy, 1.7bn at launch'),
    '0x6b394c413d60b2aadb37a907a73a6f9a91c35015': ('Community Pool',       'ERC1967 proxy, 1bn at launch'),

    # --- day-one EOAs ---
    '0xa38da2eb2d8fd956eb049c9790fe67f6e245715a': ('Founder Wallet',       '13.8bn at launch; deployer-vanity sibling'),
    '0xb05e00183a44bb3d0da10beeacdb01d71ae08cda': ('Shadow Wallet',        '4bn at launch, nonce=1, single onward transfer'),
    '0x432d8577931d0c06707ad8795bd9b9649d6d3a1d': ('Liquidity Wallet',     '3bn at launch; seeded LP / treasury'),

    # --- the 2025-26 obfuscation chain ---
    '0x07286aa168b3aa7d091048f090153162960c980b': ('Mega Forwarder',       'took 11.65bn from Founder Wallet'),
    '0xf3acb8a950bf5df323cb7dfcfef070a36a7b1c3e': ('Gate Hop',             'nonce=1, Gate.io-funded gas, moved the Shadow Wallet 4bn'),
    '0xc05210c6ba33a79682593b5c164848713c351e86': ('Merge Wallet',         'consolidated exactly 11.000bn on 14 Dec 2025'),
    '0xe73b5aec494cbc76bbd79af4e01ae7da32584370': ('Cold Hold',            'held 11.000bn dormant Dec 2025 - Apr 2026'),
    '0x833753f3980c61c5b8f49ad07275b173bca52714': ('Fan-Out Root',         'split 11.000bn into 3 sub-distributors, 9 Apr 2026'),
    '0x57bdb6b8ee3e755b4df96cc127d97ca5f48ca775': ('Sub-Distributor 1',    '3.219bn'),
    '0x7cd7a04d3730df6e49e1edacb6ded8a1fef5d856': ('Sub-Distributor 2',    '4.512bn'),
    '0x7aa852b62ece614caa9673a9fcde62729becce55': ('Sub-Distributor 3',    '3.269bn'),

    # --- insider holders ---
    '0x55a3319b1cfe8b82cacb0b5cf96c7445bf12066a': ('Whale Insider',        'received 4bn from Mega Forwarder, 26 Aug 2025'),
    '0x14804213c11a670ac7d9c82e9303a4db08dae296': ('Silent Whale',         'held 972.5mn dormant 11 months, then exited'),
    '0x3ce075da773fc527418613c1bd1f604993dd884b': ('Twin Wallet A',        'OKX-funded, 561.0mn'),
    '0xf97ef431912f62e410d7ba14e3ccf2a45747111f': ('Twin Wallet B',        'OKX-funded, 380.0mn, same funder+day as Twin A'),
    '0x76e9225529b174cfadbd1bbde64caa753fa8bcc5': ('Batch Holder',         'pool adminTransfer, 9 inbound tranches'),

    # --- Alpha feeders (aggregators) ---
    '0xb40b35fe21be75f6e5c0b7dabab1ec87d87a1395': ('Alpha Feeder A',       'gas from Binance: Hot Wallet 12'),
    '0xb50de384e012a5f0fd80c4ce85bb6e679256f25c': ('Alpha Feeder B',       'gas from Binance: Hot Wallet 16'),
    '0xd49ef7def42f4633cd55cb874e016a570ea99f04': ('Alpha Feeder C',       'gas from Binance 51'),
    '0xcfb02194256652c650a02290804456e34e619daa': ('Alpha Feeder D',       'fed by OKX-funded conduit'),
    '0x6449b24d8dad7cef8ece12d7d5c8d0e0ef355a48': ('Alpha Feeder E',       'gas from Binance: Hot Wallet 9'),

    # --- June-Aug 2026 wave ---
    '0xf23abe615b96badcf5e46d390d0697d433986aa4': ('Pool Drain Wallet 1',  'took 4.073bn straight from Investors Pool; gas from Binance: Hot Wallet 13'),
    '0xa074027a3bb55b6f01989e20202f532894d7d97c': ('Pool Drain Wallet 2',  'took 2.000bn onward; gas from Gate.io 1'),
    '0x011ecaf1ee4c279c8ac69849b62f5e18f81df7f8': ('Alpha Round-Trip',     'nonce=2, pulled 524.8mn out of Alpha and pushed it back'),

    # --- venues ---
    '0x73d8bd54f7cf5fab43fe4ef40a62d390644946db': ('Binance Alpha 2.0',    'buy/sell venue; BscScan "Alpha 2.0 Router" proxy, OKLink "Binance. Hot Wallet_4"'),
    '0x6aba0315493b7e6989041c91181337b662fb1b90': ('Alpha Router',         'Alpha infrastructure proxy'),
    '0xb300000b72deaeb607a12d5f54773d1c19c7028d': ('Alpha Relayer',        'Alpha infrastructure proxy'),
    '0x653dd7677aea3030eab68c97ed3594bacf560158': ('Alpha Relayer 2',      'Alpha infrastructure proxy'),
    '0x4d3bf29ba30f8bfe4624e7678709afa195689c5d': ('PancakeSwap AKE/USDT', 'V3 pool'),
    '0x0d0707963952f2fba59dd06f2b425ace40b492fe': ('Gate.io 1',            'exchange hot wallet'),
    '0xc882b111a75c0c657fc507c04fbfcd2cc984f071': ('Gate.io 5',            'exchange hot wallet'),
    '0x53f78a071d04224b8e254e243fffc6d9f2f3fa23': ('KuCoin Hot Wallet 2',  'exchange hot wallet'),
    '0x681cf37be53aa3493a49bc4d466f81baff7d3966': ('Treasury Proxy',       'AKE owner() since 24 Feb 2026'),

    # --- exchange gas funders ---
    '0x515b72ed8a97f42c568d6a143232775018f133c8': ('Binance: Hot Wallet 12', ''),
    '0x8894e0a0c962cb723c1976a4421c95949be2d4e3': ('Binance 51',            ''),
    '0xdccf3b77da55107280bd850ea519df3705d1a75a': ('Binance: Hot Wallet 9', ''),
    '0xbd612a3f30dca67bf60a39fd0d35e39b7ab80774': ('Binance: Hot Wallet 13', ''),
    '0x01c952174c24e1210d26961d456a77a39e1f0bb0': ('Binance: Hot Wallet 23', ''),
    '0xf5988713400da6fc8a58ec9515e2b0df9b40b115': ('OKX: DepositAndWithdraw_173', ''),
}


def nick(addr, default=None):
    a = (addr or '').lower()
    if a in NAMES:
        return NAMES[a][0]
    return default if default is not None else f'{a[:10]}…{a[-4:]}'


def short(addr):
    a = (addr or '').lower()
    return f'{a[:10]}…{a[-6:]}'
