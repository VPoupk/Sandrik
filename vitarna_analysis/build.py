#!/usr/bin/env python3
"""Build self-contained index.html: inline D3 + inject processed data into template.html."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(HERE, "template.html")).read()
data = open(os.path.join(HERE, "data", "processed.json")).read()
json.loads(data)  # sanity

# locate vendored d3 (fetched once into vendor/)
d3path = os.path.join(HERE, "vendor", "d3.v7.min.js")
if not os.path.exists(d3path):
    sys.exit("missing vendor/d3.v7.min.js — fetch it from https://d3js.org/d3.v7.min.js")
d3 = open(d3path).read()
assert "</script>" not in d3, "d3 contains </script>, cannot inline safely"

cdn = '<script src="https://d3js.org/d3.v7.min.js"></script>'
assert cdn in tpl, "CDN script tag not found in template"
tpl = tpl.replace(cdn, "<script>/* d3.v7.min.js (inlined) */\n" + d3 + "\n</script>")

out = tpl.replace("/*__DATA__*/", data)
assert "/*__DATA__*/" not in out
open(os.path.join(HERE, "index.html"), "w").write(out)
print(f"index.html built: {len(out)//1024} KB (d3 inlined, data embedded, no external deps)")
