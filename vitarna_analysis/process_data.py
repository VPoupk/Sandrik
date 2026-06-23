#!/usr/bin/env python3
"""
Final analytical pass for VitaRNA. Reads raw_data.json + enrich.json + funder_vet.json.
Produces data/processed.json consumed (inlined) by the HTML report.

Connection methodology:
  - Distribution HUBS (token contract, pools, routers, genesis distributor, treasury,
    deployer, vesting/crowdsale/Safe contracts, and any wallet with >40 counterparties)
    are NEVER used to glue wallets together — receiving an allocation from the project
    is not a peer relationship.
  - Transfer-peer clusters: union-find over direct VITARNA transfers between NON-hub wallets.
  - Funding clusters: wallets sharing a funder whose out-degree is small (personal wallet),
    i.e. NOT a CEX/disperse service (those are discounted).
  - The two signals are merged into entity groups.
"""
import json, os
from collections import defaultdict
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DEC = 18; UNIT = 10**DEC
ZERO = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"
W36 = 36*3600
HUB_CP = 40           # >this many counterparties => treat as hub
SERVICE_DEG = 40      # funder out-degree >= this => service/CEX, discount

KNOWN = {
    ZERO: ("Mint / Burn (0x0)", "zero"),
    DEAD: ("Burn (0xdead)", "zero"),
    "0xa28b1854a654e35e94d51ea2f4f34208d9ba79a2": ("Uniswap V3: VITARNA/VITA", "pool"),
    "0x998f67995b996d7c47b965566c1db4e2fe710053": ("Uniswap V3: VITARNA/WETH", "pool"),
    "0x000000000004444c5dc75cb358380d2e3de08a90": ("Uniswap V4: PoolManager (BIO pool)", "pool"),
    "0x452f3b60129fdb3cdc78178848c63ec23f38c80d": ("Genesis Distributor Safe", "distributor"),
    "0xf5307a74d1550739ef81c6488dc5c7a6a53e5ac2": ("VitaDAO: Treasury (vitadao.eth)", "treasury"),
    "0x58eb89c69cb389dbef0c130c6296ee271b82f436": ("Token Deployer", "deployer"),
    "0x66a9893cc07d91d95644aedd05d03f95e1dba8af": ("Uniswap: Universal Router", "router"),
    "0x3fc91a3afd70395cd496c647d5a6cc9d4b2b7fad": ("Uniswap: Universal Router (old)", "router"),
    "0x68b3465833fb72a70ecdf485e0e4c7bd8665fc45": ("Uniswap: SwapRouter02", "router"),
    "0xef1c6e67703c7bd7107eed8303fbe6ec2554bf6b": ("Uniswap: Universal Router 2", "router"),
    "0x6ff5693b99212da76ad316178a184ab56d299b43": ("Uniswap V4: Universal Router", "router"),
    "0x6a000f20005980200259b80c5102003040001068": ("Uniswap V4: Universal Router", "router"),
    "0x1111111254eeb25477b68fb85ed929f73a960582": ("1inch v5 Router", "router"),
    "0x111111125421ca6dc452d289314280a0f8842a65": ("1inch v6 Router", "router"),
    "0x0000000071727de22e5e9d8baf0edac6f37da032": ("ERC-4337 EntryPoint", "router"),
    "0xd152f549545093347a162dce210e7293f1452150": ("Disperse.app", "router"),
    # DEX aggregators / settlers (buys route through these, not personal wallets)
    "0x7f54f05635d15cde17a49502fedb9d1803a3be8a": ("0x: MainnetSettler", "router"),
    "0x4c82d1fbfe28c977cbb58d8c7ff8fcf9f70a2cca": ("Uniswap: UniversalRouter", "router"),
    "0xb92fe925dc43a0ecde6c8b1a2709c170ec4fff4f": ("Relay: RouterV3", "router"),
    "0x74de5d4fcbf63e00296fd95d33236b9794016631": ("Aggregator: Spender", "router"),
    "0x9008d19f58aabd9ed0d60971565aa8510560ab41": ("CoW Protocol: GPv2Settlement", "router"),
    "0x8f10b468b06c6fd214b65f87778827f7d113f996": ("Aggregator/MM settler (unverified)", "router"),
    "0xaf11ff2f56ee3bf46ba9661ee3ae52983594b0b2": ("Distribution / MM contract", "contract"),
}


def load(name):
    p = os.path.join(DATA_DIR, name)
    return json.load(open(p)) if os.path.exists(p) else {}


def main():
    raw = load("raw_data.json")
    enrich = load("enrich.json")
    fvet = load("funder_vet.json")
    meta = raw["meta"]
    holders_auth = raw["holders"]
    transfers = sorted(raw["transfers"], key=lambda t: (t["block"], t.get("ts", 0)))
    total_supply = int(meta["total_supply_raw"])
    now_ts = max(t["ts"] for t in transfers)
    cutoff36 = now_ts - W36

    ewallets = enrich.get("wallets", {})
    eflabels = enrich.get("funder_labels", {})

    # ---------- labels & kinds ----------
    label, kind, is_contract = {}, {}, {}
    for h in holders_auth:
        a = h["address"]; is_contract[a] = h.get("is_contract", False)
        nm = h.get("ens") or h.get("name")
        tags = [t for t in ((h.get("public_tags") or []) + (h.get("meta_tags") or [])) if t]
        if tags and not nm: nm = tags[0]
        if nm: label[a] = nm
        low = (" ".join(tags) + " " + (nm or "")).lower()
        if any(x in low for x in ["binance","coinbase","kraken","okx","exchange","gate.io","mexc","bybit","kucoin","htx","bitget"]):
            kind[a] = "cex"
        elif "sablier" in low or "lockup" in low or "vest" in low: kind[a] = "vesting"
        elif "crowdsale" in low or "crowd sale" in low: kind[a] = "crowdsale"
        elif "treasury" in low or "vitadao" in low: kind[a] = "treasury"
        elif "safe" in low or "gnosis" in low: kind[a] = "safe"
        elif h.get("is_contract"): kind[a] = "contract"
        else: kind[a] = "eoa"
    # enrich labels for non-holders (buyers/past sellers)
    for a, rec in ewallets.items():
        info = rec.get("info") or {}
        if a not in label and info.get("label"): label[a] = info["label"]
        if a not in kind:
            if info.get("is_contract"): kind[a] = "contract"
            else: kind[a] = "eoa"
        is_contract.setdefault(a, info.get("is_contract", False))
    for a, (nm, k) in KNOWN.items():
        label[a] = nm; kind[a] = k; is_contract.setdefault(a, k != "eoa")

    def lab(a): return label.get(a) or (a[:8] + "…" + a[-4:])
    def short(a): return a[:6] + "…" + a[-4:]

    # ---------- reconstruct balances, peaks, stats, flows ----------
    bal = defaultdict(int); peak = defaultdict(int); peak_ts = {}
    first_ts, last_ts = {}, {}
    sent_cnt = defaultdict(int); recv_cnt = defaultdict(int)
    counterparties = defaultdict(set)
    bought_dex = defaultdict(int); sold_dex = defaultdict(int)
    in_from = defaultdict(lambda: defaultdict(int))   # a <- src volume
    out_to = defaultdict(lambda: defaultdict(int))    # a -> dst volume
    POOLS = {a for a,(_,k) in KNOWN.items() if k=="pool"}
    for t in transfers:
        s,d,v,ts = t["from"],t["to"],t["value"],t["ts"]
        if s != ZERO:
            bal[s]-=v; sent_cnt[s]+=1; counterparties[s].add(d)
            last_ts[s]=ts; first_ts.setdefault(s,ts); out_to[s][d]+=v
        bal[d]+=v; recv_cnt[d]+=1; counterparties[d].add(s)
        last_ts[d]=ts; first_ts.setdefault(d,ts); in_from[d][s]+=v
        if bal[d]>peak[d]: peak[d]=bal[d]; peak_ts[d]=ts
        if s in POOLS and d not in POOLS: bought_dex[d]+=v
        if d in POOLS and s not in POOLS: sold_dex[s]+=v

    auth_bal = {h["address"]: int(h["value_raw"]) for h in holders_auth}
    mism = sum(1 for a,b in auth_bal.items() if abs(bal.get(a,0)-b) > UNIT)
    print(f"Validation: {mism}/{len(auth_bal)} holders off by >1 token (complete data)")
    def cur_bal(a): return auth_bal.get(a, max(bal.get(a,0),0))

    # ---------- hub set ----------
    hubs = set(a for a,(_,k) in KNOWN.items() if k in ("zero","pool","router","distributor","treasury","deployer"))
    for a in set(list(counterparties)+list(auth_bal)):
        if is_contract.get(a) or kind.get(a) in ("vesting","crowdsale","safe","contract","cex","treasury","distributor"):
            hubs.add(a)
        if len(counterparties.get(a,())) > HUB_CP:
            hubs.add(a)
    def is_hub(a): return a in hubs

    # ---------- funders ----------
    funder_of = {}; funder_ts = {}
    for a, rec in ewallets.items():
        f = rec.get("funder")
        if f: funder_of[a] = f["funder"]; funder_ts[a] = f["ts"]
    # which funders are personal (not service)
    personal_funders = {}
    for f, info in fvet.items():
        if info.get("out_degree_sampled", 999) < SERVICE_DEG:
            personal_funders[f] = info

    # =================== 1) CURRENT HOLDERS ===================
    holders = []
    for h in holders_auth:
        a=h["address"]; b=int(h["value_raw"])
        holders.append({
            "address":a,"label":label.get(a),"kind":kind.get(a,"eoa"),
            "is_contract":h.get("is_contract",False),
            "balance":b/UNIT,"percent":b/total_supply*100,
            "peak":peak.get(a,b)/UNIT,
            "first_ts":first_ts.get(a),"last_ts":last_ts.get(a),
            "recv_cnt":recv_cnt.get(a,0),"sent_cnt":sent_cnt.get(a,0),
            "counterparties":len(counterparties.get(a,())),
            "bought_dex":bought_dex.get(a,0)/UNIT,"sold_dex":sold_dex.get(a,0)/UNIT,
            "funder":funder_of.get(a),
        })
    holders.sort(key=lambda x:x["balance"],reverse=True)
    for i,h in enumerate(holders,1): h["rank"]=i
    cum=0.0
    for h in holders:
        cum+=h["percent"]; h["cumulative_percent"]=cum
    def topn(n): return sum(h["percent"] for h in holders[:n])

    # supply buckets
    buckets = defaultdict(float)
    for h in holders:
        k = h["kind"]
        if k in ("treasury","distributor"): buckets["Treasury / Distributor"]+=h["percent"]
        elif k=="vesting": buckets["Vesting (Sablier)"]+=h["percent"]
        elif k=="crowdsale": buckets["Crowdsale contract"]+=h["percent"]
        elif k=="safe": buckets["Multisig (Safe)"]+=h["percent"]
        elif k=="pool": buckets["DEX liquidity"]+=h["percent"]
        elif k=="contract": buckets["Other contracts"]+=h["percent"]
        elif k=="cex": buckets["CEX"]+=h["percent"]
        else: buckets["EOA float"]+=h["percent"]
    float_pct = buckets.get("EOA float",0.0)

    vals=sorted(h["balance"] for h in holders); n=len(vals); s=sum(vals)
    gini=(sum((2*i-n-1)*v for i,v in enumerate(vals))/(n*s)) if s else 0

    # =================== 2) 36H BUYERS ===================
    ROUTERS={a for a,(_,k) in KNOWN.items() if k=="router"}
    VEST={a for a in counterparties if kind.get(a) in ("vesting","crowdsale")}
    SRCPROJ={a for a,(_,k) in KNOWN.items() if k in ("treasury","distributor")}
    def src_cat(a):
        if a in POOLS: return "DEX"
        if a in ROUTERS: return "aggregator"
        if a in VEST: return "vesting claim"
        if a in SRCPROJ: return "allocation"
        if kind.get(a)=="eoa": return "transfer (EOA)"
        return "transfer (contract)"
    win=[t for t in transfers if t["ts"]>=cutoff36]
    net=defaultdict(int); gin=defaultdict(int); gout=defaultdict(int)
    din=defaultdict(int); dout=defaultdict(int); wcp=defaultdict(set); wtx=defaultdict(list)
    cat_in=defaultdict(lambda: defaultdict(int))
    for t in win:
        s,d,v=t["from"],t["to"],t["value"]
        if s!=ZERO:
            net[s]-=v; gout[s]+=v; wcp[s].add(d)
            if d in POOLS or d in ROUTERS: dout[s]+=v
            wtx[s].append({"dir":"out","cp":d,"v":v/UNIT,"ts":t["ts"],"hash":t["hash"]})
        net[d]+=v; gin[d]+=v; wcp[d].add(s)
        if s in POOLS or s in ROUTERS: din[d]+=v
        cat_in[d][src_cat(s)] += v
        wtx[d].append({"dir":"in","cp":s,"v":v/UNIT,"ts":t["ts"],"hash":t["hash"]})
    buyers=[]
    for a,nv in net.items():
        if a in POOLS or a==ZERO or a in ROUTERS or nv<=0: continue
        topsrc = max(in_from[a].items(), key=lambda x:x[1])[0] if in_from[a] else None
        # dominant inbound category over the window
        via = max(cat_in[a].items(), key=lambda x:x[1])[0] if cat_in[a] else "transfer"
        buyers.append({
            "address":a,"label":label.get(a),"kind":kind.get(a,"eoa"),
            "net":nv/UNIT,"gross_in":gin[a]/UNIT,"gross_out":gout[a]/UNIT,
            "dex_in":din[a]/UNIT,"dex_out":dout[a]/UNIT,
            "via":via,
            "main_source":lab(topsrc) if topsrc else None,
            "main_source_addr":topsrc,
            "cur_balance":cur_bal(a)/UNIT,"cur_pct":cur_bal(a)/total_supply*100,
            "first_ts":first_ts.get(a),"is_new":first_ts.get(a,0)>=cutoff36,
            "funder":funder_of.get(a),
            "txs":sorted(wtx[a],key=lambda x:x["ts"]),
        })
    buyers.sort(key=lambda x:x["net"],reverse=True)
    sellers=[]
    for a,nv in net.items():
        if a in POOLS or a==ZERO or kind.get(a)=="router" or nv>=0: continue
        sellers.append({"address":a,"label":label.get(a),"kind":kind.get(a,"eoa"),
            "net":nv/UNIT,"dex_out":dout[a]/UNIT,"cur_balance":cur_bal(a)/UNIT,
            "via":"DEX" if dout[a]>0 else "transfer"})
    sellers.sort(key=lambda x:x["net"])

    # =================== 3) PAST HOLDERS WHO SOLD ===================
    past=[]
    for a,pk in peak.items():
        if is_hub(a) or kind.get(a) in ("treasury","distributor","deployer"): continue
        cb=cur_bal(a); pkt=pk/UNIT
        if pkt<2000: continue
        if cb/pk < 0.10 and (pk-cb)/UNIT >= 2000:
            dests = sorted(out_to[a].items(), key=lambda x:x[1], reverse=True)[:3]
            srcs = sorted(in_from[a].items(), key=lambda x:x[1], reverse=True)[:2]
            past.append({
                "address":a,"label":label.get(a),"kind":kind.get(a,"eoa"),
                "peak":pkt,"peak_pct":pk/total_supply*100,"peak_ts":peak_ts.get(a),
                "current":cb/UNIT,"sold_total":(pk-cb)/UNIT,"sold_dex":sold_dex.get(a,0)/UNIT,
                "exit_via":"DEX" if sold_dex.get(a,0)>0.5*(pk-cb) else "transfer/internal",
                "first_ts":first_ts.get(a),"last_ts":last_ts.get(a),
                "main_dest":[(lab(d),v/UNIT) for d,v in dests],
                "main_source":[(lab(sc),v/UNIT) for sc,v in srcs],
                "funder":funder_of.get(a),
            })
    past.sort(key=lambda x:x["peak"],reverse=True)

    # =================== 4) CLUSTERING ===================
    node_addrs = set(h["address"] for h in holders[:120])
    node_addrs |= set(b["address"] for b in buyers)
    node_addrs |= set(p["address"] for p in past[:40])
    node_addrs = {a for a in node_addrs if not is_hub(a)}

    parent={a:a for a in node_addrs}
    def find(x):
        while parent[x]!=x: parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        if a in parent and b in parent:
            ra,rb=find(a),find(b)
            if ra!=rb: parent[rb]=ra

    # transfer-peer edges (non-hub <-> non-hub)
    edge_map=defaultdict(lambda:{"count":0,"vol":0})
    for t in transfers:
        s,d,v=t["from"],t["to"],t["value"]
        if s in node_addrs and d in node_addrs and s!=d:
            key=tuple(sorted([s,d])); edge_map[key]["count"]+=1; edge_map[key]["vol"]+=v
            union(s,d)
    # funding edges (shared personal funder)
    fund_edges=[]
    by_pf=defaultdict(list)
    for a in node_addrs:
        f=funder_of.get(a)
        if f and f in personal_funders: by_pf[f].append(a)
        # also if the funder itself is a node (entity wallet funding a holder)
    for f,ws in by_pf.items():
        for i in range(len(ws)):
            for j in range(i+1,len(ws)):
                union(ws[i],ws[j]); fund_edges.append((ws[i],ws[j],f))
        # link funder to fundees if funder is also in node set
        if f in node_addrs:
            for w in ws: union(f,w); fund_edges.append((f,w,f))

    comp=defaultdict(list)
    for a in node_addrs: comp[find(a)].append(a)
    clusters=sorted([c for c in comp.values() if len(c)>=2], key=lambda c:(-sum(cur_bal(m) for m in c), -len(c)))
    cluster_of={}
    for cid,members in enumerate(clusters):
        for m in members: cluster_of[m]=cid

    edges=[]
    for (a,b),info in edge_map.items():
        edges.append({"source":a,"target":b,"tx_count":info["count"],"volume":info["vol"]/UNIT,"type":"transfer"})
    for a,b,f in fund_edges:
        edges.append({"source":a,"target":b,"tx_count":1,"volume":0,"type":"funding","funder":f})
    edges.sort(key=lambda e:e["tx_count"],reverse=True)

    bl={h["address"]:h for h in holders}
    nodes=[]
    buyset={b["address"] for b in buyers}; pastset={p["address"] for p in past}
    for a in node_addrs:
        h=bl.get(a); cb=cur_bal(a)
        nodes.append({
            "id":a,"label":label.get(a),"short":short(a),"kind":kind.get(a,"eoa"),
            "balance":cb/UNIT,"percent":cb/total_supply*100,"peak":peak.get(a,0)/UNIT,
            "cluster_id":cluster_of.get(a,-1),"rank":h["rank"] if h else None,
            "first_ts":first_ts.get(a),"last_ts":last_ts.get(a),
            "counterparties":len(counterparties.get(a,())),
            "bought_dex":bought_dex.get(a,0)/UNIT,"sold_dex":sold_dex.get(a,0)/UNIT,
            "is_buyer_36h":a in buyset,"is_past_seller":a in pastset,
            "funder":funder_of.get(a),
        })

    cluster_summ=[]
    for cid,members in enumerate(clusters):
        ms=sorted(members,key=lambda m:cur_bal(m),reverse=True)
        tot=sum(cur_bal(m) for m in members)/UNIT
        # evidence
        pf=set()
        for m in members:
            f=funder_of.get(m)
            if f in personal_funders: pf.add(f)
        cluster_summ.append({
            "cluster_id":cid,"size":len(members),
            "members":ms,"labels":[lab(m) for m in ms],
            "balances":[cur_bal(m)/UNIT for m in ms],
            "roles":[("buyer" if m in buyset else "")+("/past-seller" if m in pastset else "") or "holder" for m in ms],
            "total_balance":tot,"total_pct":tot*UNIT/total_supply*100,
            "shared_funders":[short(f) for f in pf],
            "has_transfer_link": any(e["type"]=="transfer" and e["source"] in members and e["target"] in members for e in edges),
        })

    # ===== summary =====
    summary={
        "token":meta["token"],"name":meta["name"],"symbol":meta["symbol"],"decimals":DEC,
        "total_supply":total_supply/UNIT,"total_holders":len(holders),"total_transfers":len(transfers),
        "minted":sum(t["value"] for t in transfers if t["from"]==ZERO)/UNIT,
        "price_usd":float(meta.get("exchange_rate_usd") or 0),
        "market_cap":float(meta.get("circulating_market_cap") or 0),
        "volume_24h":float(meta.get("volume_24h") or 0),
        "now_ts":now_ts,"cutoff36":cutoff36,"first_ts":transfers[0]["ts"],"first_block":transfers[0]["block"],
        "top1_pct":topn(1),"top3_pct":topn(3),"top5_pct":topn(5),"top10_pct":topn(10),
        "top20_pct":topn(20),"top50_pct":topn(50),"float_pct":float_pct,"gini":gini,
        "buckets":dict(buckets),
        "n_buyers_36h":len(buyers),"n_sellers_36h":len(sellers),"n_past_sellers":len(past),
        "n_clusters":len(clusters),
        "processed_at":datetime.now(timezone.utc).isoformat(),
    }
    out={"summary":summary,"holders":holders,"buyers36h":buyers,"sellers36h":sellers,
         "past_sellers":past,"clusters":cluster_summ,"nodes":nodes,"edges":edges,
         "funder_vet":fvet,"labels":label,"kinds":kind}
    json.dump(out, open(os.path.join(DATA_DIR,"processed.json"),"w"), default=str)
    print(f"Saved processed.json ({os.path.getsize(os.path.join(DATA_DIR,'processed.json'))//1024} KB)")

    # report
    print("\n=== SUPPLY BUCKETS ===")
    for k,v in sorted(buckets.items(),key=lambda x:-x[1]): print(f"  {k:26s}{v:6.2f}%")
    print(f"\nConcentration: top1={summary['top1_pct']:.1f}% top3={summary['top3_pct']:.1f}% "
          f"top10={summary['top10_pct']:.1f}% float={float_pct:.1f}% gini={gini:.3f}")
    print(f"\n36h buyers: {len(buyers)} | sellers: {len(sellers)} | past sellers: {len(past)} | clusters: {len(clusters)}")
    print("\nTop 8 36h buyers:")
    for b in buyers[:8]:
        print(f"  {short(b['address'])} +{b['net']:>11,.0f} {b['via']:8s} new={str(b['is_new']):5s} src={b['main_source']}")
    print("\nClusters:")
    for c in cluster_summ:
        print(f"  C{c['cluster_id']} n={c['size']} bal={c['total_balance']:,.0f} "
              f"funders={c['shared_funders']} tlink={c['has_transfer_link']}")
        for m,l,b in list(zip(c['members'],c['labels'],c['balances']))[:6]:
            print(f"       {short(m)} {l[:30]:30s} {b:,.0f}")


if __name__ == "__main__":
    main()
