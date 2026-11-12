#!/usr/bin/env python3
"""
One-pass scan of a V3 pool's Swap + Mint + Burn + Collect logs.

Daily (or N-second) buckets for the swap series, plus every liquidity event
kept raw so same-block JIT pairs can be separated from real withdrawal later.

Usage: poolall.py <pool> <from> <to> <ckpt_name> [bucket_seconds]
Writes only to pipeline/data/<ckpt_name>.json
"""
import json, urllib.request, time, os, sys, datetime, bisect

RPC = 'https://bsc-mainnet.nodereal.io/v1/64a9df0874fb4a93b9d0a3849de012d3'
SWAP_PCS = '0x19b47279256b2a23a1665c810c8d55a1758940ee09377d4f8d26497a3577dc83'
SWAP_UNI = '0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67'
MINT     = '0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde'
BURN     = '0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c'
COLLECT  = '0x70935338e69775456a85ddef226c395fb668b63fa0115f5f20610b388e6ca9c0'

BASE = '/home/user/Sandrik'
POOL = sys.argv[1].lower()
A    = int(sys.argv[2])
B    = int(sys.argv[3])
CKPT = os.path.join(BASE, 'pipeline/data/%s.json' % sys.argv[4])
BUCK = int(sys.argv[5]) if len(sys.argv) > 5 else 86400
STEP = 49_999

TS = json.load(open(os.path.join(BASE, 'pipeline/data/blk_ts.json')))
_tb = sorted(int(k) for k in TS)
_tv = [TS[str(x)] for x in _tb]


def bts(bn):
    i = bisect.bisect_left(_tb, bn)
    if i == 0:
        return _tv[0]
    if i >= len(_tb):
        # extrapolate at 0.75s/block (BSC post-Maxwell)
        return _tv[-1] + (bn - _tb[-1]) * 0.75
    return _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1])


class TooManyLogs(Exception):
    pass


def rpc(m, p, tries=14):
    for i in range(tries):
        try:
            req = urllib.request.Request(
                RPC, data=json.dumps({'jsonrpc': '2.0', 'id': 1,
                                      'method': m, 'params': p}).encode(),
                headers={'Content-Type': 'application/json'})
            j = json.loads(urllib.request.urlopen(req, timeout=240).read())
            if 'error' in j:
                msg = str(j['error'])
                if ('exceeds the limit' in msg or 'query returned more than' in msg
                        or 'TooManyLogs' in msg or 'too many logs' in msg.lower()):
                    raise TooManyLogs(msg)
                raise RuntimeError(msg)
            return j['result']
        except TooManyLogs:
            raise
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(min(90, 1.5 * (1.8 ** i)))


def get(frm, to):
    try:
        return rpc('eth_getLogs', [{'address': POOL,
                                    'topics': [[SWAP_PCS, SWAP_UNI, MINT, BURN, COLLECT]],
                                    'fromBlock': hex(frm), 'toBlock': hex(to)}])
    except TooManyLogs:
        if frm >= to:
            raise
        mid = (frm + to) // 2
        return get(frm, mid) + get(mid + 1, to)


def s256(x):
    return x - (1 << 256) if x >= (1 << 255) else x


def s24(x):
    return x - (1 << 24) if x >= (1 << 23) else x


def blank():
    # 0 o, 1 h, 2 l, 3 c, 4 ake_in, 5 ake_out, 6 bnb_in, 7 bnb_out,
    # 8 nswap, 9 liq_lo, 10 liq_hi, 11 big_amt, 12 big_blk, 13 big_side,
    # 14 nsell, 15 nbuy
    return [None, 0.0, 0.0, None, 0, 0, 0, 0, 0, None, 0, 0, 0, '', 0, 0]


WEI = (4, 5, 6, 7, 11)


def main():
    buck, liq = {}, []
    start = A
    if os.path.exists(CKPT):
        c = json.load(open(CKPT))
        if c.get('pool') == POOL and c.get('from') == A and c.get('to') == B:
            for k, v in c['buckets'].items():
                v = list(v)
                for i in WEI:
                    v[i] = int(v[i])
                buck[int(k)] = v
            liq = c.get('liq', [])
            start = c['last_block'] + 1
            print('resume at %d (%d buckets, %d liq ev)' % (start, len(buck), len(liq)),
                  flush=True)

    print('poolall %s %d -> %d bucket=%ds' % (POOL, A, B, BUCK), flush=True)
    b = start
    t0 = time.time()
    while b <= B:
        e = min(b + STEP, B)
        for L in get(b, e):
            t = L['topics'][0]
            d = L['data'][2:]
            w = [d[i*64:(i+1)*64] for i in range(len(d) // 64)]
            bn = int(L['blockNumber'], 16)
            if t in (SWAP_PCS, SWAP_UNI):
                a0 = s256(int(w[0], 16))
                a1 = s256(int(w[1], 16))
                sp = int(w[2], 16)
                lq = int(w[3], 16)
                px = (sp / 2**96) ** 2
                k = int(bts(bn)) // BUCK * BUCK
                q = buck.setdefault(k, blank())
                if q[0] is None:
                    q[0] = px; q[1] = px; q[2] = px
                q[1] = max(q[1], px); q[2] = min(q[2], px); q[3] = px
                if a0 > 0:
                    q[4] += a0; q[7] += -a1; q[14] += 1   # AKE in (sell), BNB out
                else:
                    q[5] += -a0; q[6] += a1; q[15] += 1   # AKE out (buy), BNB in
                q[8] += 1
                q[9] = lq if q[9] is None else min(q[9], lq)
                q[10] = max(q[10], lq)
                if abs(a0) > q[11]:
                    q[11] = abs(a0); q[12] = bn; q[13] = 'sell' if a0 > 0 else 'buy'
            elif t == MINT:
                liq.append(['M', bn, L['transactionHash'],
                            '0x' + L['topics'][1][-40:],
                            s24(int(L['topics'][2], 16)), s24(int(L['topics'][3], 16)),
                            '0x' + w[0][-40:], str(int(w[1], 16)),
                            str(int(w[2], 16)), str(int(w[3], 16))])
            elif t == BURN:
                liq.append(['B', bn, L['transactionHash'],
                            '0x' + L['topics'][1][-40:],
                            s24(int(L['topics'][2], 16)), s24(int(L['topics'][3], 16)),
                            '', str(int(w[0], 16)),
                            str(int(w[1], 16)), str(int(w[2], 16))])
            elif t == COLLECT:
                liq.append(['C', bn, L['transactionHash'],
                            '0x' + L['topics'][1][-40:],
                            s24(int(L['topics'][2], 16)), s24(int(L['topics'][3], 16)),
                            '0x' + w[0][-40:], '0',
                            str(int(w[1], 16)), str(int(w[2], 16))])

        json.dump({'pool': POOL, 'from': A, 'to': B, 'last_block': e, 'bucket': BUCK,
                   'buckets': {str(k): [v[i] if i not in WEI else str(v[i])
                                        for i in range(len(v))]
                               for k, v in buck.items()},
                   'liq': liq,
                   'timestamp': datetime.datetime.now().isoformat()},
                  open(CKPT + '.tmp', 'w'))
        os.replace(CKPT + '.tmp', CKPT)
        pct = 100.0 * (e - A + 1) / (B - A + 1)
        el = time.time() - t0
        print('%d-%d (%.1f%%) buckets=%d liq=%d el=%.0fs eta=%.0fs' %
              (b, e, pct, len(buck), len(liq), el,
               el * (100 - pct) / max(pct, 0.01)), flush=True)
        b = e + 1
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
