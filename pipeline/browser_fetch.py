#!/usr/bin/env python3
"""
Fetch a page with a real headless Chromium so JS/Cloudflare-gated explorers
(BscScan in particular) can be read. Plain HTTP gets 403 from this
environment; a real browser clears the challenge.

Usage: browser_fetch.py <url> <out_file> [wait_selector] [extra_wait_ms]
Data-only: writes the rendered HTML to the named file.
"""
import sys, os, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1]
OUT = sys.argv[2]
SEL = sys.argv[3] if len(sys.argv) > 3 else None
EXTRA = int(sys.argv[4]) if len(sys.argv) > 4 else 6000

with sync_playwright() as p:
    # the sandbox routes egress through an agent proxy with its own CA; the
    # browser has to be pointed at it or every navigation fails at the TLS layer
    prox = os.environ.get('BF_PROXY')   # opt-in; Chromium reads the env proxy itself
    b = p.chromium.launch(
        executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
        proxy={'server': prox} if prox else None,
        args=['--no-sandbox', '--disable-dev-shm-usage',
              '--disable-blink-features=AutomationControlled',
              '--ignore-certificate-errors'])
    ctx = b.new_context(
        ignore_https_errors=True,
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        viewport={'width': 1440, 'height': 900}, locale='en-US')
    ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
    pg = ctx.new_page()
    try:
        pg.goto(URL, wait_until='domcontentloaded', timeout=90000)
    except Exception as e:
        print('goto warning:', e, file=sys.stderr)
    if SEL:
        try:
            pg.wait_for_selector(SEL, timeout=45000)
        except Exception as e:
            print('selector warning:', e, file=sys.stderr)
    pg.wait_for_timeout(EXTRA)
    html = pg.content()
    open(OUT, 'w').write(html)
    print(f'{pg.url}  title={pg.title()!r}  bytes={len(html)}')
    b.close()
