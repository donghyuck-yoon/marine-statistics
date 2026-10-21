#!/usr/bin/env python3
"""Reconstruct day-mean SST from approved KMA period API; NO writes to site data."""
import collections
import csv
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOST="https://apihub.kma.go.kr/api/typ01/url/kma_buoy2.php"
KEY=os.environ.get("KMA_API_KEY","")
ROOT=Path(__file__).resolve().parents[1]
DATES=[("2025-09-01","2025-09-02"),("2026-10-18","2026-10-19")]
STN="22101"
OUT=Path("daily-sst-comparison.json")

def records(a,b):
    q={"tm1":a.replace("-","")+"0000","tm2":b.replace("-","")+"2330","stn":STN,"help":"0","authKey":KEY}
    url=HOST+"?"+urllib.parse.urlencode(q)
    with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"marine-stats-read-only-comparator"}),timeout=30) as response:
        if response.status!=200: raise RuntimeError("non-200 HTTP response")
        text=response.read(300_000).decode("utf-8-sig",errors="replace")
    result=collections.defaultdict(list)
    for line in text.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        row=next(csv.reader([line],skipinitialspace=True))
        if len(row)<12:continue
        stamp=row[0].strip()
        if len(stamp)!=12 or not stamp.isdigit() or row[1].strip()!=STN:continue
        temp=row[11].strip()  # TW in documented KMA buoy field order
        try: value=float(temp)
        except ValueError: continue
        if not -2<=value<=40: continue
        date=stamp[:4]+"-"+stamp[4:6]+"-"+stamp[6:8]
        result[date].append(value)
    return result

def reference(year):
    p=ROOT/"data"/"marine"/f"{year}.csv"
    with p.open(encoding="utf-8-sig",newline="") as f:
        return {row["일시"]:float(row["평균 수온(°C)"])
                for row in csv.DictReader(f)
                if row.get("지점")==STN and row.get("평균 수온(°C)")}

def main():
    if not KEY:
        print("Secret KMA_API_KEY not configured")
        return 2
    results=[]
    for start,end in DATES:
        try:
            observed=records(start,end)
        except urllib.error.HTTPError as e:
            print(f"{start}: HTTP {int(e.code)}")
            return 1
        except Exception as e:
            print(f"{start}: failed {type(e).__name__}")
            return 1
        refs=reference(int(start[:4]))
        date=dt.date.fromisoformat(start)
        while date<=dt.date.fromisoformat(end):
            key=date.isoformat()
            vals=observed.get(key,[])
            mean=sum(vals)/len(vals) if vals else None
            target=refs.get(key)
            difference=round(mean-target,3) if mean is not None and target is not None else None
            row={"date":key,"station":STN,"samples":len(vals),
                 "calculated_api_30min_mean":round(mean,3) if mean is not None else None,
                 "portal_daily_mean":target,"difference":difference}
            results.append(row)
            print(f"{key}: 30min_samples={len(vals)} daily_api_mean={row['calculated_api_30min_mean']} "
                  f"portal={target} difference={difference}")
            date+=dt.timedelta(days=1)
    nmatch=sum(r["difference"] is not None and abs(r["difference"])<=0.11 for r in results)
    OUT.write_text(json.dumps({"read_only":True,"within_0p11C":nmatch,"tested_days":len(results),"days":results},
                 ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"DAY MEAN COMPARISON: {nmatch}/{len(results)} within 0.11 C. No data files changed.")
    return 0

if __name__=="__main__": raise SystemExit(main())
