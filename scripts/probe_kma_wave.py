#!/usr/bin/env python3
"""Check historical coastal-wave station snapshots through KMA sea_obs; READ ONLY."""
import csv, json, os, urllib.parse, urllib.request, urllib.error
from pathlib import Path

KEY=os.getenv("KMA_API_KEY","").strip()
BASE="https://apihub.kma.go.kr/api/typ01/url/sea_obs.php"
EXAMPLES=["202509010000","202509011200","202610190000","202610191200"]
TARGET="22441"
OUT=Path("wave-observation-probe.json")
def sample(stamp):
    params={"tm":stamp,"stn":TARGET,"help":"0","authKey":KEY}
    url=BASE+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"marine-stats-wave-read-only/1.0"})
    result={"requested":stamp,"station":TARGET,"http_status":None,"matched_rows":0}
    try:
        with urllib.request.urlopen(req,timeout=25) as resp:
            result["http_status"]=resp.status
            body=resp.read(100000).decode("utf-8-sig",errors="replace")
    except urllib.error.HTTPError as e:
        result["http_status"]=e.code; result["error"]="http_error";return result
    except Exception as e:
        result["error"]=type(e).__name__;return result
    for line in body.splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        fields=next(csv.reader([line],skipinitialspace=True))
        if len(fields)<12:continue
        if fields[2].strip()!=TARGET:continue
        typ,t,stn=fields[0].strip(),fields[1].strip(),fields[2].strip()
        def num(idx):
            try: return float(fields[idx].strip())
            except: return None
        result["matched_rows"]+=1
        result["type"]=typ
        result["observed_timestamp"]=t
        result["water_temp_C"]=num(10)
        result["significant_wave_height_m"]=num(6)
    return result

def main():
    if not KEY:return 2
    rows=[sample(x) for x in EXAMPLES]
    for row in rows:
        print(f"{row['requested']} station={TARGET}: HTTP={row['http_status']} "
              f"rows={row['matched_rows']} tm={row.get('observed_timestamp')} "
              f"SST={row.get('water_temp_C')} wave={row.get('significant_wave_height_m')} error={row.get('error')}")
    OUT.write_text(json.dumps({"read_only":True,"results":rows},indent=2)+"\n",encoding="utf-8")
    return 0
if __name__=="__main__":raise SystemExit(main())
