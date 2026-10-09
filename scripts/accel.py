#!/usr/bin/env python3
"""Ускорение по ценам CoinSpot: изменение средней цены (buy+sell)/2 за 15м, 1ч, 3ч, 6ч.
Пишет data/latest_accel.csv (все монеты) и дописывает топ-15 в data/signals/YYYY-MM-DD.csv."""
import csv,glob,os,datetime
from zoneinfo import ZoneInfo
files=sorted(glob.glob("data/20*.csv"))[-2:]
hist={}
for f in files:
    for r in csv.DictReader(open(f,encoding="utf-8")):
        try:
            t=datetime.datetime.fromisoformat(r["time_aest"]); b=float(r["buy"]); s=float(r["sell"])
        except: continue
        if b<=0 or s<=0: continue
        hist.setdefault(r["coin"],[]).append((t,(b+s)/2,(b-s)/b*100,r["change24h"],r["volume24h"]))
def ago(series,now,mins):
    target=now-datetime.timedelta(minutes=mins); best=None
    for t,m,*_ in series:
        if t<=target+datetime.timedelta(minutes=7): best=(t,m)
    if best and (target-best[0]).total_seconds()<=20*60: return best[1]
    return None
out=[]
for c,ser in hist.items():
    ser.sort(); t,m,sp,ch,vol=ser[-1]
    def pct(mins):
        p=ago(ser,t,mins); return round((m/p-1)*100,2) if p else ""
    r={"coin":c,"time_aest":t.isoformat(),"mid":m,"spread_pct":round(sp,2),"change24h":ch,"volume24h":vol,
       "d15m":pct(15),"d1h":pct(60),"d3h":pct(180),"d6h":pct(360)}
    # оценка: ускорение при не слишком большом спреде
    try: r["score"]=round(float(r["d1h"] or 0)*2+float(r["d3h"] or 0)+float(r["d15m"] or 0)-max(0,sp-4),2)
    except: r["score"]=0
    out.append(r)
out.sort(key=lambda r:-r["score"])
fields=["coin","time_aest","mid","spread_pct","change24h","volume24h","d15m","d1h","d3h","d6h","score"]
with open("data/latest_accel.csv","w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)
os.makedirs("data/signals",exist_ok=True)
now=datetime.datetime.now(ZoneInfo("Australia/Brisbane"))
fn=f"data/signals/{now:%Y-%m-%d}.csv"; new=not os.path.exists(fn)
with open(fn,"a",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields)
    if new: w.writeheader()
    w.writerows(out[:15])
print("accel:",len(out),"top:",[r["coin"] for r in out[:5]])
