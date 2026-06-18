"""Last-21-day (trailing) >$1k ATH seller aggregation -> window21_rows.json.
Subset of the YTD pipeline restricted to ts >= latest_block_ts - 21 days."""
import json
from datetime import datetime, timezone
from collections import defaultdict
sells=[s for s in json.load(open('sells.json')) if not s['seller'].startswith("COW:")]
cow=json.load(open('cow_sells.json'))
buys=json.load(open('buys.json'))
dao=json.load(open('dao_origin.json'))
bal=json.load(open('bal_authoritative.json'))
fin={r['addr']:r for r in json.load(open('final_table.json'))}
ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()}
T2026=json.load(open('ath_transfers_raw.json'))
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"; ZERO="0x"+"0"*40
V3P="0x8071df1889d60a1c6329ef79976fb1f2e50599af"; MGR="0x000000000004444c5dc75cb358380d2e3de08a90"
COW="0x9008d19f58aabd9ed0d60971565aa8510560ab41"; VENUE_EXT={V3P,MGR,COW}
def taddr(t): return "0x"+t[-40:].lower()
latest_ts=max(ts_map.values()); WIN=latest_ts-21*86400
print("window:",datetime.fromtimestamp(WIN,tz=timezone.utc).isoformat(),"->",datetime.fromtimestamp(latest_ts,tz=timezone.utc).isoformat())

W=defaultdict(lambda:{'ath':0.0,'usd':0.0,'v3':0.0,'v4':0.0,'cow':0.0,'stx':set(),'cowf':0,'first':None,'last':None})
def add(s,iscow=False):
    if s['ts']<WIN: return
    w=W[s['seller']]; w['ath']+=s['ath']; w['usd']+=s['usd']; w['stx'].add(s['tx'])
    w['cow' if iscow else s['venue'].lower()]+=s['ath']; w['cowf']+=1 if iscow else 0
    w['first']=s['ts'] if w['first'] is None else min(w['first'],s['ts'])
    w['last']=s['ts'] if w['last'] is None else max(w['last'],s['ts'])
for s in sells: add(s)
for s in cow: add(s,True)
B=defaultdict(lambda:{'ath':0.0,'tx':set()})
for b in buys:
    if b['ts']>=WIN: B[b['buyer']]['ath']+=b['ath']; B[b['buyer']]['tx'].add(b['tx'])
intx=defaultdict(set); outtx=defaultdict(set)
for l in T2026:
    if ts_map.get(int(l['blockNumber'],16),0)<WIN: continue
    f=taddr(l['topics'][1]); t=taddr(l['topics'][2])
    if f not in VENUE_EXT and t not in VENUE_EXT and f!=ZERO and t!=ZERO:
        outtx[f].add(l['transactionHash']); intx[t].add(l['transactionHash'])
rows=[]
for a,w in W.items():
    if w['usd']<1000: continue
    b=B.get(a,{'ath':0.0,'tx':set()})
    cls=fin.get(a,{}).get('cls','market distributor')
    if cls=='other': cls='market distributor'
    if a==USER: cls='YOU (DAO contributor allocation)'
    elif dao.get(a,0)>=80 and cls!='arb/MM bot': cls='DAO-allocation seller'
    ntx=len(w['stx']|b['tx']|intx.get(a,set())|outtx.get(a,set()))
    rows.append({'addr':a,'is_user':a==USER,'cls':cls,'dao':dao.get(a,0),
        'ath':w['ath'],'usd':w['usd'],'v3':w['v3'],'v4':w['v4'],'cow':w['cow'],
        'stx':len(w['stx']),'cowf':w['cowf'],'bought':b['ath'],'btx':len(b['tx']),
        'net':w['ath']-b['ath'],'hold':bal.get(a,0),'intx':len(intx.get(a,set())),
        'outtx':len(outtx.get(a,set())),'ntx':ntx,'first':w['first'],'last':w['last']})
rows.sort(key=lambda r:-r['usd'])
json.dump(rows,open('window21_rows.json','w'),default=str)
print(">$1k sellers in last 21d:",len(rows),"| total",f"{sum(r['ath'] for r in rows):,.0f} ATH / ${sum(r['usd'] for r in rows):,.0f}")
