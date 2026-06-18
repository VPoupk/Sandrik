"""Broader-timescale co-trading: who sells in the window BEFORE/AFTER each USER sell."""
import json
from datetime import datetime, timezone
from collections import defaultdict

USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
sells=json.load(open('sells.json'))
rows={r['addr']:r for r in json.load(open('table_rows.json'))}
def dt(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
def cls(e): return rows.get(e,{}).get('class','(<$1k seller)')

# aggregate sells per tx (entity, ts, ath, usd, venue)
bytx=defaultdict(lambda:{'ts':0,'ath':0.0,'usd':0.0,'ent':None,'ven':set()})
perentity_tx=defaultdict(list)
for s in sells:
    k=(s['seller'],s['tx'])
    perentity_tx[k]
# build per (entity,tx) sell totals
ent_tx=defaultdict(lambda:{'ts':0,'ath':0.0,'usd':0.0,'ven':set()})
for s in sells:
    r=ent_tx[(s['seller'],s['tx'])]; r['ts']=s['ts']; r['ath']+=s['ath']; r['usd']+=s['usd']; r['ven'].add(s['venue'])
# list of sell-events (entity, ts, ath, usd)
events=[(e,r['ts'],r['ath'],r['usd'],r['ven']) for (e,tx),r in ent_tx.items()]
events.sort(key=lambda x:x[1])

user_sells=sorted([(r['ts'],r['ath'],r['usd']) for (e,tx),r in ent_tx.items() if e==USER])

WINDOWS=[("10m",600),("1h",3600),("6h",21600),("24h",86400)]
# For each user sell, find other-entity sells within window BEFORE
print("=== For each USER sell: other sellers in the 24h BEFORE (sorted by closeness) ===")
before_counts=defaultdict(lambda:defaultdict(int))   # entity -> window -> count
before_ath=defaultdict(lambda:defaultdict(float))
for uts,uath,uusd in user_sells:
    print(f"\nUSER sell {dt(uts)}  {uath:,.0f} ATH (${uusd:,.0f})")
    near=[(uts-ts,e,ath,usd,ven) for (e,ts,ath,usd,ven) in events if e!=USER and 0<=uts-ts<=86400]
    near.sort()
    for dts,e,ath,usd,ven in near[:8]:
        mins=dts/60
        print(f"    -{mins:6.1f} min  {e[:12]} {('/'.join(sorted(ven))):5} {ath:>8,.0f} ATH ${usd:>6,.0f}  [{cls(e)}]")
    for w,sec in WINDOWS:
        for dts,e,ath,usd,ven in near:
            if dts<=sec:
                before_counts[e][w]+=1; before_ath[e][w]+=ath

print("\n\n=== Entities most frequently selling SHORTLY BEFORE the user (across 9 user sells) ===")
print(f"{'entity':44}{'10m':>5}{'1h':>5}{'6h':>5}{'24h':>5}  class")
ranked=sorted(before_counts.items(), key=lambda kv:(-kv[1]['1h'],-kv[1]['6h'],-kv[1]['24h']))
for e,wc in ranked[:20]:
    print(f"{e:44}{wc['10m']:>5}{wc['1h']:>5}{wc['6h']:>5}{wc['24h']:>5}  {cls(e)}")

# Also: who sells shortly AFTER user (reactive)
print("\n=== Entities most frequently selling SHORTLY AFTER the user ===")
after_counts=defaultdict(lambda:defaultdict(int))
for uts,uath,uusd in user_sells:
    near=[(ts-uts,e) for (e,ts,ath,usd,ven) in events if e!=USER and 0<=ts-uts<=86400]
    for dts,e in near:
        for w,sec in WINDOWS:
            if dts<=sec: after_counts[e][w]+=1
ranked2=sorted(after_counts.items(), key=lambda kv:(-kv[1]['1h'],-kv[1]['6h']))
print(f"{'entity':44}{'10m':>5}{'1h':>5}{'6h':>5}{'24h':>5}  class")
for e,wc in ranked2[:15]:
    print(f"{e:44}{wc['10m']:>5}{wc['1h']:>5}{wc['6h']:>5}{wc['24h']:>5}  {cls(e)}")
