"""Wallet-watching / anticipatory-distribution analysis.
Tests whether other holders sell in reaction to (a) the subject becoming a visible
loaded whale (2026-02-20 vesting claim), (b) the subject's vesting unlocks, and
(c) the subject's individual sells."""
import json
from datetime import datetime, timezone
from collections import defaultdict
DAY=86400
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
sells=[s for s in json.load(open('sells.json')) if not s['seller'].startswith("COW:")]
cow=json.load(open('cow_sells.json'))
fin={r['addr']:r for r in json.load(open('final_table.json'))}
dao=json.load(open('dao_origin.json'))
bal=json.load(open('bal_authoritative.json'))
allt=json.load(open('all_transfers.json'))
ts_map={int(k):v for k,v in json.load(open('ts_map.json')).items()}
urcv={int(k):v for k,v in json.load(open('user_recv_ts.json')).items()}
V3P="0x8071df1889d60a1c6329ef79976fb1f2e50599af"; MGR="0x000000000004444c5dc75cb358380d2e3de08a90"
COW="0x9008d19f58aabd9ed0d60971565aa8510560ab41"; ZERO="0x"+"0"*40; VEN={V3P,MGR}

ev=[(s['ts'],s['seller'],s['ath'],s['usd']) for s in sells+cow]  # all sell legs
# user sells (collapse to per-timestamp)
user_sell_ts=sorted({s['ts'] for s in sells+cow if s['seller']==USER})
# derive user receipts (inbound, non-market) and their timestamps from data
def rts(bn): return ts_map.get(bn) or urcv.get(str(bn))
recs=[]
for x in allt:
    if x['to']==USER and x['from'] not in VEN and x['from']!=ZERO:
        recs.append((rts(x['bn']),x['val']))
recs=sorted(t for t in recs if t[0])
PREMARKET=[r for r in recs if r[0]<1767225600]          # 2023 original allocation
UNLOCKS=[r for r in recs if r[0]>=1767225600]           # 2026 vesting claims (Feb20, May27)
VISIBLE=UNLOCKS[0][0]                                    # wallet first loaded for trading
LATEST=max(ts_map.values())

def dstr(ts): return datetime.fromtimestamp(ts,tz=timezone.utc).strftime("%Y-%m-%d")
def within_after(s, anchors, days):
    w=days*DAY
    return any(0<=s-a<=w for a in anchors)
def within_before(s, anchors, days):
    w=days*DAY
    return any(0<=a-s<=w for a in anchors)

# ---- baseline coverage of "<=7d after a user sell" within the watchable window ----
def coverage(anchors, days, lo, hi):
    segs=sorted((a,a+days*DAY) for a in anchors)
    merged=[];
    for a,b in segs:
        a=max(a,lo); b=min(b,hi)
        if a>=b: continue
        if merged and a<=merged[-1][1]: merged[-1]=(merged[-1][0],max(merged[-1][1],b))
        else: merged.append((a,b))
    cov=sum(b-a for a,b in merged); return cov/(hi-lo)
base7=coverage(user_sell_ts,7,VISIBLE,LATEST)
base3=coverage(user_sell_ts,3,VISIBLE,LATEST)
print(f"User became a visible loaded whale: {dstr(VISIBLE)} (333,333 ATH claim)")
print(f"User sell days: {[dstr(t) for t in user_sell_ts]}")
print(f"Baseline timeline coverage in watchable window: <=7d-after-user-sell = {base7*100:.0f}%, <=3d = {base3*100:.0f}%\n")

# ---- per non-bot seller reactivity ----
# acquisition time per wallet (first inbound ATH ever)
first_in={}
for x in allt:
    if x['to'] not in (ZERO,) and x['from']!=x['to']:
        w=x['to']
        if w not in first_in or ts_map.get(x['bn'],10**12)<first_in[w]:
            ts=ts_map.get(x['bn'])
            if ts and (w not in first_in or ts<first_in[w]): first_in[w]=ts

rows=[]
for a,r in fin.items():
    if a==USER or r['cls']=="arb/MM bot": continue
    es=[(t,ath) for (t,who,ath,usd) in ev if who==a]
    if not es: continue
    tot=sum(a2 for _,a2 in es);
    first=min(t for t,_ in es); last=max(t for t,_ in es)
    after_vis=sum(a2 for t,a2 in es if t>=VISIBLE)
    r7=sum(a2 for t,a2 in es if within_after(t,user_sell_ts,7))
    r3=sum(a2 for t,a2 in es if within_after(t,user_sell_ts,3))
    ru=sum(a2 for t,a2 in es if within_after(t,[u for u,_ in UNLOCKS],14))
    b3=sum(a2 for t,a2 in es if within_before(t,user_sell_ts,3))
    rows.append({'addr':a,'cls':r['cls'],'dao':dao.get(a,0),'tot':tot,'usd':r['usd_sold'],
        'first':first,'last':last,'hold':bal.get(a,0),
        'after_vis_pct':100*after_vis/tot,
        'react7_pct':100*r7/tot,'react3_pct':100*r3/tot,'unlock14_pct':100*ru/tot,'before3_pct':100*b3/tot,
        'started_after_vis':first>=VISIBLE,'acq':first_in.get(a)})
rows.sort(key=lambda r:-r['react7_pct'])
print("=== Non-bot >$1k sellers — reactivity to the SUBJECT (sorted by % volume sold <=7d after a user sell) ===")
print(f"baseline(random)= {base7*100:.0f}% for react7\n")
print(f"{'address':42}{'ATHsold':>9}{'1stSell':>11}{'started':>8}{'r<=7d':>7}{'r<=3d':>7}{'unlk14d':>8}{'bfr3d':>7}{'DAO%':>5}")
for r in rows:
    print(f"{r['addr']}{r['tot']:>9,.0f}{dstr(r['first']):>11}{'AFTER' if r['started_after_vis'] else 'before':>8}"
          f"{r['react7_pct']:>6.0f}%{r['react3_pct']:>6.0f}%{r['unlock14_pct']:>7.0f}%{r['before3_pct']:>6.0f}%{r['dao']:>4.0f}%")

# ---- post-receipt windows ----
print("\n=== Activity in the 14 days AFTER each USER receipt/unlock ===")
for uts,amt in PREMARKET+UNLOCKS:
    lab=dstr(uts)
    seg=[(t,who,ath) for (t,who,ath,usd) in ev if 0<=t-uts<=14*DAY and who!=USER]
    byw=defaultdict(float)
    for t,who,ath in seg: byw[who]+=ath
    nb={w:v for w,v in byw.items() if fin.get(w,{}).get('cls')!="arb/MM bot"}
    print(f"\n  after {lab} (+{amt:,} ATH claim): {len(seg)} sell-legs by others; non-bot sellers:")
    if uts<1700000000:
        print("    [DEX pool not created until Dec 2023 — no market existed yet; selling impossible]")
    for w,v in sorted(nb.items(),key=lambda kv:-kv[1])[:8]:
        first=first_in.get(w); fa = "acq-after-claim" if (first and first>=uts-DAY) else ""
        print(f"    {w}  {v:>9,.0f} ATH  [{fin.get(w,{}).get('cls','<$1k')}] {fa}")

# ---- chart data ----
chart={'user_sells':[{'ts':t} for t in user_sell_ts],
       'unlocks':[{'ts':u,'amt':a} for u,a in UNLOCKS],
       'visible':VISIBLE,'latest':LATEST,'start':min(t for t,_,_,_ in ev),
       'series':[]}
# include user + top non-bot sellers by volume
keep=[USER]+[r['addr'] for r in sorted(rows,key=lambda r:-r['tot'])[:8]]
for a in keep:
    pts=[{'ts':t,'ath':ath} for (t,who,ath,usd) in ev if who==a]
    chart['series'].append({'addr':a,'is_user':a==USER,'cls':('you' if a==USER else fin.get(a,{}).get('cls')),
        'dao':dao.get(a,0),'tot':sum(p['ath'] for p in pts),'pts':pts})
json.dump(chart,open('watch_chart.json','w'))
json.dump(rows,open('watch_rows.json','w'),default=str)
print("\nsaved watch_chart.json, watch_rows.json")
