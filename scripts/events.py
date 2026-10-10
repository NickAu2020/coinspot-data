#!/usr/bin/env python3
"""Hourly free news + listings collector (no keys). Runs inside snapshot workflow; skips if last run <55 min ago.
Saves raw responses to data/events/YYYY-MM-DD/HHMM_<source>.<ext> and appends a normalized line per new item to data/events/events.jsonl
with first_seen_at (UTC). GDELT: single request, 6s pause before it (limit 1 per 5s)."""
import json, os, time, urllib.request, hashlib, re, datetime as dt
ROOT = os.path.join(os.path.dirname(__file__), "..", "data", "events")
os.makedirs(ROOT, exist_ok=True)
STAMP = os.path.join(ROOT, ".last_run")
now = dt.datetime.now(dt.timezone.utc)
if os.path.exists(STAMP) and time.time() - float(open(STAMP).read() or 0) < 55*60 and not os.environ.get("FORCE_EVENTS"):
    print("events: skip (<55 min)"); raise SystemExit(0)
UA = {"User-Agent": "Mozilla/5.0 coinspot-data-events"}
SRC = {
 "upbit": "https://api-manager.upbit.com/api/v1/announcements?os=web&page=1&per_page=20&category=trade",
 "binance_listing": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=48&pageNo=1&pageSize=20",
 "binance_delist": "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query?type=1&catalogId=161&pageNo=1&pageSize=20",
 "cg_trending": "https://api.coingecko.com/api/v3/search/trending",
 "coinbase_products": "https://api.exchange.coinbase.com/products",
 "rss_cointelegraph": "https://cointelegraph.com/rss",
 "rss_coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
 "rss_theblock": "https://www.theblock.co/rss.xml",
 "gdelt": "https://api.gdeltproject.org/api/v2/doc/doc?query=(crypto%20OR%20token)%20(listing%20OR%20delisting%20OR%20hack%20OR%20exploit%20OR%20unlock)&mode=artlist&format=json&maxrecords=50&timespan=2h",
}
def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r: return r.read()
day = os.path.join(ROOT, now.strftime("%Y-%m-%d")); os.makedirs(day, exist_ok=True)
seen_f = os.path.join(ROOT, "seen_ids.txt"); seen = set(open(seen_f).read().split()) if os.path.exists(seen_f) else set()
items = []
def add(src, title, url, published=None, extra=None):
    h = hashlib.sha1(f"{src}|{url or title}".encode()).hexdigest()[:16]
    if h in seen: return
    seen.add(h); items.append({"id": h, "source": src, "title": title, "url": url, "published_at": published,
        "first_seen_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), **(extra or {})})
for name, url in SRC.items():
    if name == "gdelt": time.sleep(6)
    try: raw = get(url)
    except Exception as e: print(f"{name}: ERROR {e}"); continue
    ext = "xml" if name.startswith("rss") else "json"
    if name != "coinbase_products":
        open(os.path.join(day, f"{now:%H%M}_{name}.{ext}"), "wb").write(raw)
    print(f"{name}: {len(raw)} bytes")
    try:
        if name == "upbit":
            for n in json.loads(raw)["data"]["notices"]: add(name, n["title"], f"https://upbit.com/service_center/notice?id={n['id']}", n.get("listed_at"))
        elif name.startswith("binance"):
            for c in json.loads(raw)["data"]["catalogs"]:
                for a in c["articles"]: add(name, a["title"], f"https://www.binance.com/en/support/announcement/{a['code']}", dt.datetime.fromtimestamp(a["releaseDate"]/1000, dt.timezone.utc).isoformat())
        elif name == "coinbase_products":
            cur = sorted(p["id"] for p in json.loads(raw)); pf = os.path.join(ROOT, "coinbase_products.json")
            prev = set(json.load(open(pf))) if os.path.exists(pf) else None
            if prev is not None:
                for pid in cur:
                    if pid not in prev: add("coinbase_new_product", pid, None)
            json.dump(cur, open(pf, "w"))
        elif name.startswith("rss"):
            for m in re.finditer(r"<item>(.*?)</item>", raw.decode("utf-8", "ignore"), re.S):
                b = m.group(1)
                g = lambda t: (re.search(rf"<{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{t}>", b, re.S) or [None, None])[1]
                add(name, (g("title") or "").strip(), (g("link") or "").strip(), g("pubDate"))
        elif name == "gdelt":
            for a in json.loads(raw).get("articles", []): add(name, a.get("title"), a.get("url"), a.get("seendate"))
    except Exception as e: print(f"{name}: parse error {e}")
with open(os.path.join(ROOT, "events.jsonl"), "a") as f:
    for it in items: f.write(json.dumps(it, ensure_ascii=False) + "\n")
open(seen_f, "w").write("\n".join(sorted(seen)))
open(STAMP, "w").write(str(time.time()))
print(f"events: {len(items)} new items")
