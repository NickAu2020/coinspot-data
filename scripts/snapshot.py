#!/usr/bin/env python3
"""Снимок всех монет со страницы https://www.coinspot.com.au/tradecoins (цены в AUD).
Дописывает строки в data/YYYY-MM-DD.csv (дата по Брисбену)."""
import re, csv, datetime, urllib.request, os
from zoneinfo import ZoneInfo
req=urllib.request.Request("https://www.coinspot.com.au/tradecoins",headers={"User-Agent":"Mozilla/5.0"})
h=urllib.request.urlopen(req,timeout=60).read().decode("utf-8")
now=datetime.datetime.now(ZoneInfo("Australia/Brisbane"))
rows=[]
for m in re.finditer(r"<tr class='tradeitem coinrow[^>]*data-coin='([^']+)'>(.*?)</tr>",h,re.S):
    coin,body=m.groups()
    v=re.findall(r"data-value=['\"]([^'\"]*)['\"]",body)
    if len(v)>=5: rows.append([now.isoformat(timespec="seconds"),coin,v[0],v[1],v[2],v[3],v[4]])
if len(rows)<100: raise SystemExit(f"too few rows: {len(rows)}")
os.makedirs("data",exist_ok=True)
fn=f"data/{now:%Y-%m-%d}.csv"; new=not os.path.exists(fn)
with open(fn,"a",newline="",encoding="utf-8") as f:
    w=csv.writer(f)
    if new: w.writerow(["time_aest","coin","buy","sell","mcap","volume24h","change24h"])
    w.writerows(rows)
print(fn,len(rows))
