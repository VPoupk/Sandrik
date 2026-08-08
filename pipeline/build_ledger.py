#!/usr/bin/env python3
"""
Merge every completed scan segment into ONE address-level ledger covering an
unbroken block range, and prove the range is unbroken.

Segment formats differ (older scans store `agg` = [recv,rct,sent,sct]; newer
master scans store recv/sent/byday), so each is normalised on read. Segments
are asserted contiguous — a gap or an overlap raises rather than being silently
absorbed, because either one would corrupt every downstream total.

Writes pipeline/data/ledger.json. Data-only.
"""
import json, collections, sys, datetime, bisect

D = 'pipeline/data/'

# (file, first_block, last_block, format)
SEGMENTS = [
    ('master_april.json',                    88_000_000,  96_000_000, 'master'),
    ('master_may.json',                      96_000_001, 100_940_327, 'master'),
    ('ake_gap_may_jun_2026_checkpoint.json', 100_940_328, 102_669_786, 'agg'),
    ('ake_delta_v2_checkpoint.json',         102_669_787, 110_819_786, 'agg'),
    ('master_jul19_26.json',                 110_819_787, 112_252_391, 'master'),
    ('sells_jul26_agg.json',                 112_252_392, 113_384_906, 'master'),
    ('master_recent.json',                   113_384_907, 114_777_002, 'master'),
]

TS  = json.load(open(D + 'blk_ts.json'))
_tb = sorted(int(k) for k in TS); _tv = [TS[str(x)] for x in _tb]


def bd(bn):
    i = bisect.bisect_left(_tb, bn)
    t = _tv[0] if i == 0 else (_tv[-1] if i >= len(_tb) else
                               _tv[i-1] + (_tv[i]-_tv[i-1]) * (bn-_tb[i-1]) / (_tb[i]-_tb[i-1]))
    return datetime.datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d')


def main():
    recv = collections.Counter(); sent = collections.Counter()
    rct  = collections.Counter(); sct  = collections.Counter()
    byday = collections.defaultdict(collections.Counter)     # addr -> day -> recv wei
    big = []
    prev_end = None
    print(f'{"segment":42}{"declared range":>28}  {"actual last":>13}  addrs')
    for fn, a, b, fmt in SEGMENTS:
        s = json.load(open(D + fn))
        last = s['last_block']
        if last != b:
            raise SystemExit(f'FATAL {fn}: declared end {b:,} but checkpoint last_block {last:,}')
        if prev_end is not None and a != prev_end + 1:
            raise SystemExit(f'FATAL gap/overlap before {fn}: {prev_end:,} -> {a:,}')
        prev_end = b

        n = 0
        if fmt == 'master':
            for k, v in s['recv'].items():
                recv[k] += int(v); n += 1
            for k, v in s['sent'].items():
                sent[k] += int(v)
            for k, dd in s['byday'].items():
                for d, x in dd.items():
                    byday[k][d] += int(x)
        else:
            # NOTE the field order in these older checkpoints is
            #   [out_amt, out_n, in_amt, in_n]  -- SENT first, RECEIVED second.
            # Verified against gap_scan_2026.py / delta_scan_v2.py and against
            # an on-chain replay of 0x14804213 (received at block 92,704,309,
            # sent at 108,565,733). Reversing these two is silent and fatal.
            for k, q in s['agg'].items():
                sent[k] += int(q[0]); sct[k] += q[1]
                recv[k] += int(q[2]); rct[k] += q[3]
                n += 1
        big += [r[:5] for r in s.get('big', [])]
        print(f'{fn:42}{a:>13,}-{b:<13,}  {last:>13,}  {n:,}')

    lo, hi = SEGMENTS[0][1], SEGMENTS[-1][2]
    print(f'\nCONTIGUOUS: blocks {lo:,} -> {hi:,}   ({bd(lo)} -> {bd(hi)})')
    print(f'receiving addresses: {len(recv):,}   sending addresses: {len(sent):,}')
    print(f'gross received: {sum(recv.values())/1e24:,.1f}mn   gross sent: {sum(sent.values())/1e24:,.1f}mn')
    print(f'big transfers kept: {len(big):,}')

    json.dump({'from': lo, 'to': hi, 'from_date': bd(lo), 'to_date': bd(hi),
               'recv': {k: str(v) for k, v in recv.items()},
               'sent': {k: str(v) for k, v in sent.items()},
               'byday': {k: {d: str(x) for d, x in dd.items()} for k, dd in byday.items()},
               'big': big},
              open(D + 'ledger.json', 'w'))
    print('wrote', D + 'ledger.json')


if __name__ == '__main__':
    main()
