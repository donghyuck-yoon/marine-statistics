#!/usr/bin/env python3
"""Wave-buoy 1-day all-station sampling pilot. Read-only; rate-limited."""
import csv,datetime,json,os,time,urllib.parse,urllib.request,urllib.error
from pathlib import Path
KEY=os.environ.get("KMA_API_KEY","").strip()
TARGET="22441"
DAY="2025-09-01"
OUT=Path("wave-daily-reconstruction.json")
ENDPOINT="https://apihub.kma.go.kr/api/typ01/url/sea_obs.php"
def one(tm):
    params={"tm":tm,"stn":"0","help":"0","authKey":KEY}
    url=ENDPOINT+"?"+urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"marine-stats-wave-daily-pilot/1.0"}),timeout=25) as r:
            raw=r.read(125000).decode("utf-8-sig","replace")
    except urllib.error.HTTPError as e:
        return None,int(e.code)
    except Exception:
        return None,0
    for line in raw.splitlines():
        if not line.strip() or line.startswith("#"):continue
        fields=next(csv.reader([line],skipinitialspace=True))
        if len(fields)<14 or fields[2].strip()!=TARGET:continue
        stamp=fields[1].strip()
        if stamp!=tm:return None,-1
        def value(i):
            try:
                v=float(fields[i].strip())
                return v if -2<=v<=40 else None
            except: return None
        return {"tm":stamp,"sst":value(10),"wave":value(6)},200
    return None,200
def main():
    if not KEY:
        print("API secret absent");return 2
    d=datetime.date.fromisoformat(DAY)
    measurements=[]
    errors={}
    for h in range(24):
        for minute in (0,30):
            tm=d.strftime("%Y%m%d")+f"{h:02d}{minute:02d}"
            row,status=one(tm)
            if row is not None:measurements.append(row)
            else:errors[status]=errors.get(status,0)+1
            time.sleep(0.15)
    def avg(k):
        nums=[r[k] for r in measurements if r[k] is not None]
        return (round(sum(nums)/len(nums),3),len(nums)) if nums else (None,0)
    computed_sst,n_sst=avg("sst");computed_wave,n_wave=avg("wave")
    with (Path("data")/"coastal"/"2025.csv").open(encoding="utf-8-sig",newline="") as f:
        match=[r for r in csv.DictReader(f) if r["지점"]==TARGET and r["일시"]==DAY][0]
    reference_sst=float(match["평균 수온(°C)"])
    reference_wave=float(match["평균 유의 파고(m)"])
    diff_sst=round(computed_sst-reference_sst,3) if computed_sst is not None else None
    diff_wave=round(computed_wave-reference_wave,3) if computed_wave is not None else None
    report={"read_only":True,"date":DAY,"station":TARGET,"requested_slots":48,
            "matched_slots":len(measurements),"sst_samples":n_sst,"wave_samples":n_wave,
            "api_sst_C":computed_sst,"portal_sst_C":reference_sst,"sst_difference_C":diff_sst,
            "api_wave_m":computed_wave,"portal_wave_m":reference_wave,"wave_difference_m":diff_wave,
            "missing_or_failed_slots":errors}
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0
if __name__=="__main__":raise SystemExit(main())
