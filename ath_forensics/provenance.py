"""Trace where each >$1k seller's ATH came from (DAO/treasury vs DEX vs wallet)."""
import json
from collections import defaultdict
from datetime import datetime, timezone

GEN="0x4d754910d570b30f9a0150eeb7281cb3ce0cf42f"
ZERO="0x"+"0"*40
V3P="0x8071df1889d60a1c6329ef79976fb1f2e50599af"
MGR="0x000000000004444c5dc75cb358380d2e3de08a90"
COW="0x9008d19f58aabd9ed0d60971565aa8510560ab41"
USER="0xf0940b14e8a4be798cd713a6807e95f47b769d9c"
BASE_BRIDGE="0x3154cf16ccdb4c6d922629664174b904d80f2c35"

allt=json.load(open('all_transfers.json'))
rows=json.load(open('table_rows.json'))

# DAO-controlled set = genesis + contracts that received large direct allocations from genesis
# (vesting/treasury). Pools & bridge excluded.
out_from_gen=defaultdict(float)
for x in allt:
    if x['from']==GEN: out_from_gen[x['to']]+=x['val']
DAO_VESTING={a for a,v in out_from_gen.items() if v>=300000 and a not in (V3P,MGR,BASE_BRIDGE)}
DAO={GEN}|DAO_VESTING
POOLS={V3P,MGR}
def src_class(a):
    if a==GEN: return "DAO genesis/treasury"
    if a in DAO_VESTING: return "DAO vesting/treasury contract"
    if a in POOLS: return "DEX pool (market buy)"
    if a==COW: return "CoW settlement (market buy)"
    if a==BASE_BRIDGE: return "Base bridge"
    if a==ZERO: return "mint"
    return "wallet"

# inbound per address (all-time)
inbound=defaultdict(lambda:defaultdict(lambda:[0.0,0,None,None]))  # addr -> src -> [ath,legs,first,last]
for x in allt:
    d=inbound[x['to']][x['from']]
    d[0]+=x['val']; d[1]+=1
    if d[2] is None or x['bn']<d[2]: d[2]=x['bn']
    if d[3] is None or x['bn']>d[3]: d[3]=x['bn']

def dts(bn): return bn

print("=== PROVENANCE of each >$1k seller (all-time inbound ATH sources) ===\n")
prov_out={}
for r in sorted(rows,key=lambda r:-r['usd_sold']):
    a=r['addr']
    if a.startswith("COW:"): continue
    srcs=inbound.get(a,{})
    tot=sum(v[0] for v in srcs.values())
    # bucket by class
    bucket=defaultdict(float)
    for s,v in srcs.items(): bucket[src_class(s)]+=v[0]
    dao_amt=bucket.get("DAO genesis/treasury",0)+bucket.get("DAO vesting/treasury contract",0)
    dao_pct=100*dao_amt/tot if tot else 0
    tag='YOU' if a==USER else ('CONTRACT' if r['contract'] else '')
    print(f"{a} [{r['class']}] {tag}")
    print(f"   sold {r['ath_sold']:,.0f} ATH / ${r['usd_sold']:,.0f} | holds {r['holdings']:,.0f} | total inbound (all time) {tot:,.0f} ATH")
    print(f"   DAO-sourced: {dao_pct:.0f}%  | source breakdown:")
    for s,v in sorted(srcs.items(),key=lambda kv:-kv[1][0])[:6]:
        print(f"      {v[0]:>12,.0f} ATH from {s} [{src_class(s)}]  ({v[1]} legs)")
    prov_out[a]={'total_inbound':tot,'dao_pct':dao_pct,'buckets':dict(bucket),
                 'top_sources':[(s,inbound[a][s][0]) for s in sorted(srcs,key=lambda s:-srcs[s][0])[:6]]}
    print()
json.dump({'dao_set':sorted(DAO),'dao_vesting':sorted(DAO_VESTING),'prov':prov_out},open('provenance.json','w'))
print("DAO vesting/treasury contracts identified:")
for a in sorted(DAO_VESTING): print("   ",a, f"{out_from_gen[a]:,.0f} from genesis")
