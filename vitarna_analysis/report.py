#!/usr/bin/env python3
import json, os, datetime
from collections import defaultdict
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
d = json.load(open(os.path.join(D, "processed.json")))
raw = json.load(open(os.path.join(D, "raw_data.json")))
def ts(x): return datetime.datetime.utcfromtimestamp(int(x)).strftime("%Y-%m-%d") if x else "?"

print("=== TOP 14 PAST SELLERS (peak -> now), with flows ===")
for p in d["past_sellers"][:14]:
    src = ", ".join(f"{l}:{v:,.0f}" for l, v in (p.get("main_source") or []))
    dst = ", ".join(f"{l}:{v:,.0f}" for l, v in (p.get("main_dest") or []))
    a = p["address"]
    print(f"{a[:12]} peak={p['peak']:>10,.0f} ({p['peak_pct']:.2f}%)@{ts(p['peak_ts'])} now={p['current']:,.0f} via={p['exit_via']}")
    print(f"      from[{src}]")
    print(f"      to  [{dst}]")

print("\n=== 36H BUYERS: source classification ===")
# build addr->is_contract/label from raw holders + enrich
enrich = json.load(open(os.path.join(D, "enrich.json")))
kinds = d["kinds"]; labels = d["labels"]
for b in d["buyers36h"][:20]:
    src = b.get("main_source_addr")
    srclab = labels.get(src) or (src[:10] if src else "?")
    print(f"{b['address'][:12]} +{b['net']:>10,.0f} via={b['via']:8s} new={str(b['is_new']):5s} "
          f"bal_now={b['cur_balance']:>9,.0f} src={srclab}")

print("\n=== EOA sources feeding >=2 distinct 36h buyers (possible distribution) ===")
src_map = defaultdict(list)
for b in d["buyers36h"]:
    s = b.get("main_source_addr")
    if s: src_map[s].append(b["address"])
for s, ws in sorted(src_map.items(), key=lambda x: -len(x[1])):
    if len(ws) >= 2:
        print(f"  source {s[:12]} [{labels.get(s) or kinds.get(s,'?')}] -> {len(ws)} buyers")
