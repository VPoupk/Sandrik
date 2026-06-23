#!/usr/bin/env python3
"""Build self-contained index_v2.html: inline D3 + inject processed_v2.json into template_v2.html."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "template_v2.html")).read()
data = open(os.path.join(HERE, "data", "processed_v2.json")).read()
json.loads(data)
d3path = os.path.join(HERE, "vendor", "d3.v7.min.js")
d3 = open(d3path).read()
assert "</script>" not in d3
cdn = '<script src="https://d3js.org/d3.v7.min.js"></script>'
assert cdn in tpl, "CDN script tag not found"
tpl = tpl.replace(cdn, "<script>/* d3.v7.min.js (inlined) */\n" + d3 + "\n</script>")
out = tpl.replace("/*__DATA__*/", data)
assert "/*__DATA__*/" not in out
open(os.path.join(HERE, "index_v2.html"), "w").write(out)
print(f"index_v2.html built: {len(out)//1024} KB")
