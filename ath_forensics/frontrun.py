"""Front-running / co-trading timing analysis around the USER's sells."""
import json
from datetime import datetime, timezone
from collections import defaultdict

USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()}
sells=json.load(open('sells.json')); buys=json.load(open('buys.json'))

# tx -> (bn, txIndex) from raw logs (have transactionIndex)
txpos={}
for fn in ('ath_transfers_raw.json','v3_swaps_raw.json','v4_swaps_raw.json'):
    for l in json.load(open(fn)):
        txpos[l['transactionHash']]=(int(l['blockNumber'],16), int(l['transactionIndex'],16))

# per-tx swap record
rec=defaultdict(lambda:{'sell':defaultdict(float),'buy':defaultdict(float),'bn':0,'ti':0,'ts':0})
for s in sells:
    r=rec[s['tx']]; r['sell'][s['seller']]+=s['ath']; r['bn'],r['ti']=txpos[s['tx']]; r['ts']=s['ts']
for b in buys:
    r=rec[b['tx']]; r['buy'][b['buyer']]+=b['ath']; r['bn'],r['ti']=txpos[b['tx']]; r['ts']=b['ts']

# index swaps by block
byblock=defaultdict(list)
for tx,r in rec.items(): byblock[r['bn']].append((r['ti'],tx,r))
for b in byblock: byblock[b].sort()

# user sell txs
user_sells=sorted([(r['bn'],r['ti'],tx,r) for tx,r in rec.items() if USER in r['sell']])
print(f"USER has {len(user_sells)} sell txs. Detailed timeline:")
def dt(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
for bn,ti,tx,r in user_sells:
    print(f"  {dt(r['ts'])}  blk {bn} idx {ti:>3}  sold {sum(r['sell'][USER] for _ in [0]):>9,.0f} ATH  tx {tx[:14]}")

# For each user sell, scan same block & neighbor blocks; tally other entities by relative position
SAME_BEFORE=defaultdict(int); SAME_AFTER=defaultdict(int)
PREVBLK=defaultdict(int); NEXTBLK=defaultdict(int)
SAME_BEFORE_SELL=defaultdict(int); SAME_AFTER_BUY=defaultdict(int)
for bn,ti,tx,r in user_sells:
    # same block
    for ti2,tx2,r2 in byblock.get(bn,[]):
        if tx2==tx: continue
        ents=set(r2['sell'])|set(r2['buy'])
        for e in ents:
            if e==USER: continue
            if ti2<ti:
                SAME_BEFORE[e]+=1
                if e in r2['sell']: SAME_BEFORE_SELL[e]+=1
            else:
                SAME_AFTER[e]+=1
                if e in r2['buy']: SAME_AFTER_BUY[e]+=1
    # neighbor blocks (+/-1)
    for nb,bucket in ((bn-1,PREVBLK),(bn+1,NEXTBLK)):
        for ti2,tx2,r2 in byblock.get(nb,[]):
            for e in set(r2['sell'])|set(r2['buy']):
                if e!=USER: bucket[e]+=1

def top(d,n=12): return sorted(d.items(),key=lambda x:-x[1])[:n]
print("\n=== Entities trading in the SAME BLOCK, BEFORE the user (potential front-run) ===")
for e,c in top(SAME_BEFORE):
    print(f"  {e}  before:{c}  (of which SELL-before:{SAME_BEFORE_SELL.get(e,0)})  after:{SAME_AFTER.get(e,0)} (BUY-after:{SAME_AFTER_BUY.get(e,0)})")
print("\n=== Entities trading in the SAME BLOCK, AFTER the user (reactive/back-run) ===")
for e,c in top(SAME_AFTER):
    print(f"  {e}  after:{c}  before:{SAME_BEFORE.get(e,0)}")
print("\n=== Entities in PREVIOUS block (lead by ~12s) ===")
for e,c in top(PREVBLK): print(f"  {e}  prev-blk:{c}")

# Sandwich detection: same entity BEFORE(sell) and AFTER(buy) the same user tx
print("\n=== SANDWICH pattern (same entity sells before AND buys after, same user tx) ===")
sand=defaultdict(int); sand_txs=defaultdict(list)
for bn,ti,tx,r in user_sells:
    blk=byblock.get(bn,[])
    before={e for ti2,tx2,r2 in blk if ti2<ti and tx2!=tx for e in r2['sell']}
    after_buy={e for ti2,tx2,r2 in blk if ti2>ti and tx2!=tx for e in r2['buy']}
    for e in (before & after_buy):
        if e!=USER: sand[e]+=1; sand_txs[e].append(tx[:14])
for e,c in sorted(sand.items(),key=lambda x:-x[1]):
    print(f"  {e}  sandwiches:{c}  e.g. {sand_txs[e][:3]}")
json.dump({'same_before':SAME_BEFORE,'same_after':SAME_AFTER,'prevblk':PREVBLK,'nextblk':NEXTBLK,
           'sandwich':sand},open('frontrun_stats.json','w'))
