#!/usr/bin/env python3
"""
Read the entity label OKLink (first-party BSC block explorer) publishes for a
list of addresses, straight from the rendered address page. No aggregator, no
analytics vendor. Writes pipeline/data/oklink_labels.json.

Usage: oklink_labels.py <addr-list.json | comma-separated addrs> [out_name]
"""
import json, re, subprocess, sys, os, time, html

OUT = 'pipeline/data/%s.json' % (sys.argv[2] if len(sys.argv) > 2 else 'oklink_labels')

arg = sys.argv[1]
if os.path.exists(arg):
    d = json.load(open(arg))
    addrs = list(d) if isinstance(d, dict) else list(d)
else:
    addrs = [a.strip().lower() for a in arg.split(',') if a.strip()]

res = json.load(open(OUT)) if os.path.exists(OUT) else {}

# OKLink embeds the label in its Next.js payload as  "label":"Binance"  and
# "tagName":"Binance. Hot Wallet_4" ; also as visible text next to the address.
RE_ENTITY = re.compile(r'"entityTag"\s*:\s*"([^"]{1,80})"')
RE_ETAGS  = re.compile(r'"entityTags"\s*:\s*\[([^\]]{0,400})\]')
RE_PTAGS  = re.compile(r'"propertyTags"\s*:\s*\[([^\]]{0,400})\]')
RE_ISC    = re.compile(r'"isContract"\s*:\s*(true|false)')

for a in addrs:
    a = a.lower()
    if a in res and res[a].get('ok'):
        continue
    url = 'https://www.oklink.com/bsc/address/' + a
    try:
        p = subprocess.run(['curl', '-sS', '--max-time', '45', url,
                            '-H', 'user-agent: Mozilla/5.0 (X11; Linux x86_64) '
                                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36'],
                           capture_output=True, text=True, timeout=60)
        body = p.stdout
    except Exception as e:
        res[a] = {'ok': False, 'error': str(e)}
        continue

    ent = RE_ENTITY.findall(body)
    et  = RE_ETAGS.findall(body)
    pt  = RE_PTAGS.findall(body)
    isc = RE_ISC.findall(body)
    res[a] = {'ok': len(body) > 20000,
              'entity': html.unescape(ent[0]) if ent else None,
              'entity_tags': [html.unescape(x.strip('"')) for x in (et[0].split('","') if et and et[0] else [])],
              'property_tags': [html.unescape(x.strip('"')) for x in (pt[0].split('","') if pt and pt[0] else [])],
              'is_contract': (isc[0] == 'true') if isc else None,
              'bytes': len(body)}
    print(f"{a}  entity={res[a]['entity']}  prop={res[a]['property_tags'][:2]}", flush=True)
    json.dump(res, open(OUT, 'w'), indent=1)
    time.sleep(1.0)

print('wrote', OUT, len(res), 'addresses')
