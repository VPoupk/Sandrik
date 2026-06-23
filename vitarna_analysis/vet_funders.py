#!/usr/bin/env python3
"""Vet shared funders: out-degree (distinct ETH recipients) + tx count + VITARNA holding.
High degree => service/CEX/disperse (discount). Low degree => personal funder (real link)."""
import json, os, time
from collections import defaultdict
import requests

BS = "https://eth.blockscout.com"
TOKEN = "0x7b66E84Be78772a3afAF5ba8c1993a1B5D05F9C2".lower()
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
S = requests.Session(); S.headers.update({"User-Agent": "vitarna-analysis/1.0"})

def get(url, params=None):
    for i in range(5):
        try:
            r = S.get(url, params=params, timeout=25)
            if r.status_code == 200: return r.json()
            time.sleep(1.2*(i+1))
        except Exception: time.sleep(1.2*(i+1))
    return {}

def out_degree(a, cap=400):
    """distinct recipients of native ETH from a (sample up to cap txs)."""
    recips=set(); n=0; page=1
    while n < cap:
        d=get(f"{BS}/api", {"module":"account","action":"txlist","address":a,
                            "sort":"asc","page":page,"offset":100})
        res=d.get("result")
        if not isinstance(res,list) or not res: break
        for t in res:
            n+=1
            if (t.get("from") or "").lower()==a.lower():
                to=(t.get("to") or "").lower()
                try: v=int(t.get("value","0"))
                except: v=0
                if to and v>0: recips.add(to)
        if len(res)<100: break
        page+=1
        time.sleep(0.05)
    return len(recips), n

def main():
    e=json.load(open(os.path.join(DATA_DIR,"enrich.json")))
    byf=defaultdict(list)
    for a,rec in e["wallets"].items():
        f=rec.get("funder")
        if f: byf[f["funder"]].append(a)
    shared={f:ws for f,ws in byf.items() if len(ws)>=2}
    holders={h["address"] for h in json.load(open(os.path.join(DATA_DIR,"processed.json")))["holders"]}
    out={}
    for f,ws in sorted(shared.items(),key=lambda x:-len(x[1])):
        deg,sampled=out_degree(f)
        ctr=get(f"{BS}/api/v2/addresses/{f}/counters")
        txc=ctr.get("transactions_count")
        fl=e["funder_labels"].get(f,{})
        verdict = "SERVICE/CEX (discount)" if deg>=40 else ("PERSONAL FUNDER (real link)" if deg<=12 else "AMBIGUOUS")
        out[f]={"funded":ws,"out_degree_sampled":deg,"sampled_txs":sampled,"tx_count":txc,
                "label":fl.get("label"),"is_contract":fl.get("is_contract"),"verdict":verdict,
                "funder_holds_token": f in holders}
        print(f"\nFUNDER {f}  label={fl.get('label')} holds_token={f in holders}")
        print(f"  funded {len(ws)} targets | out-degree~{deg} (of {sampled} txs) | total_txs={txc} | => {verdict}")
        for w in ws:
            print(f"     -> {w}")
    json.dump(out, open(os.path.join(DATA_DIR,"funder_vet.json"),"w"))
    print("\nSaved funder_vet.json")

if __name__=="__main__":
    main()
