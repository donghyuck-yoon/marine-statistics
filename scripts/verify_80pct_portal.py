#!/usr/bin/env python3
"""Read-only: compare 80%-valid KMA intraday means with official portal DAILY CSVs.

The 80% rule is applied to each station/day/variable *only to API-derived means*.
Official daily values are never filtered/modified. No uploads to published data.
"""
from __future__ import annotations
import collections
import csv
import datetime as dt
import decimal
import json
import math
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parents[1]
DATES=['2025-09-01','2026-07-25','2026-10-19']
THRESHOLD=math.ceil(0.80*48) # 39 of the 48 scheduled half-hour slots
KEY=os.environ.get('KMA_API_KEY','').strip()
REPORT=pathlib.Path('api-80pct-vs-portal.json')
URL_M='https://apihub.kma.go.kr/api/typ01/url/kma_buoy2.php'
URL_C='https://apihub.kma.go.kr/api/typ01/url/sea_obs.php'


def req(url, query):
    query={**query,'authKey':KEY}
    full=url+'?'+urllib.parse.urlencode(query)
    try:
        r=urllib.request.urlopen(urllib.request.Request(full,headers={'User-Agent':'marine-statistics-80pct-check/1.0'}),timeout=35)
        with r:
            return r.read(1_500_000).decode('utf-8-sig',errors='replace'),r.status
    except urllib.error.HTTPError as exc:
        return None,int(exc.code)
    except urllib.error.URLError:
        return None,0
    # NEVER print query string, response body, or exception text: may include key.


def parse_csv_text(text,kind,expected_tm=None):
    output=[]
    for line in (text or '').splitlines():
        if not line.strip() or line.lstrip().startswith(('#','//','<')):continue
        row=next(csv.reader([line],skipinitialspace=True))
        row=[s.strip() for s in row]
        if kind=='marine':
            if len(row)<16 or not re.fullmatch(r'\d{12}',row[0]) or not re.fullmatch(r'\d{5}',row[1]):continue
            tm,stn=row[0],row[1]
            vals={'sst':row[11]}
        else:
            if len(row)<14 or not re.fullmatch(r'\d{12}',row[1]) or not re.fullmatch(r'\d{5}',row[2]):continue
            tm,stn=row[1],row[2]
            vals={'sst':row[10],'wave':row[6]}
        if expected_tm and tm != expected_tm: continue
        clean={}
        for field,x in vals.items():
            try:v=float(x)
            except (ValueError,TypeError): continue
            if (field=='sst' and -3<=v<=45) or (field=='wave' and 0<=v<=40):
                clean[field]=v
        output.append((tm,stn,clean))
    return output


def reference(net,year):
    f=ROOT/'data'/net/f'{year}.csv'
    vals={}
    with f.open(encoding='utf-8-sig',newline='') as h:
        for row in csv.DictReader(h):
            d=row.get('일시','')
            if not d.startswith(str(year)):continue
            stn=row.get('지점','')
            for field,col in [('sst','평균 수온(°C)'),('wave','평균 유의 파고(m)')]:
                if field=='wave' and net=='marine': continue
                try: value=float(row.get(col,''))
                except (TypeError,ValueError): continue
                if (field=='sst' and -3<=value<=45) or (field=='wave' and 0<=value<=40):
                    vals[(stn,d,field)]=value
    return vals


def api_day(net,day):
    stamp=day.replace('-','')
    observed=collections.defaultdict(dict)
    codes=collections.Counter()
    if net=='marine':
        body,status=req(URL_M,{'tm1':stamp+'0000','tm2':stamp+'2330','stn':'0','help':'0'})
        codes[str(status)]+=1
        if status!=200:return observed,codes
        for tm,stn,values in parse_csv_text(body,'marine'):
            if tm[:8]!=stamp:continue
            for k,v in values.items():observed[(stn,k)][tm]=v
    else:
        for hh in range(24):
            for mm in (0,30):
                tm=stamp+f'{hh:02d}{mm:02d}'
                body,status=req(URL_C,{'tm':tm,'stn':'0','help':'0'})
                codes[str(status)]+=1
                if status==200:
                    for obs_tm,stn,values in parse_csv_text(body,'coastal',expected_tm=tm):
                        for k,v in values.items():observed[(stn,k)][obs_tm]=v
                if status==429:
                    return observed,codes
                time.sleep(0.1)
    return observed,codes


def round_1(x):
    return float(decimal.Decimal(str(x)).quantize(decimal.Decimal('0.1'),rounding=decimal.ROUND_HALF_UP))


def main():
    if not KEY:
        print('KMA_API_KEY secret is missing');return 2
    summary={}
    all_results=[]
    for net in ('marine','coastal'):
        checks=[]
        for date in DATES:
            api,codes=api_day(net,date)
            portal=reference(net,int(date[:4]))
            keys=set(api)
            # Also include portal station/variables without API rows, for coverage diagnostics.
            keys.update((stn,k) for stn,d,k in portal if d==date)
            processed=[]
            for stn,k in sorted(keys):
                samples=list(api.get((stn,k),{}).values())
                n=len(samples)
                orig=portal.get((stn,date,k))
                calc=(sum(samples)/n) if n>=THRESHOLD else None
                if orig is None and n==0:continue
                obj={'network':net,'date':date,'station':stn,'variable':k,
                     'valid_samples':n,'expected_slots':48,'coverage':round(n/48,3),
                     'accepted_80pct':n>=THRESHOLD,'portal':orig}
                if calc is not None:
                    obj['api_mean']=round(calc,4)
                    obj['api_round_1']=round_1(calc)
                    if orig is not None:
                        obj['difference']=round(calc-orig,4)
                        obj['match_rounded_0p1']=round_1(calc)==round_1(orig)
                processed.append(obj)
            compare=[x for x in processed if x.get('accepted_80pct') and x.get('portal') is not None]
            bad=[x for x in compare if x.get('match_rounded_0p1') is False]
            low=[x for x in processed if not x['accepted_80pct'] and x['portal'] is not None]
            print(f'{net} {date}: responses={dict(codes)} portal_day_variables={sum(x.get("portal") is not None for x in processed)} '
                  f'accepted_comparable={len(compare)}, rounded_0p1_match={len(compare)-len(bad)}/{len(compare)}, '
                  f'below80_but_portal_has_day={len(low)}')
            checks.extend(processed)
            all_results.extend(processed)
        for k in (['sst'] if net=='marine' else ['sst','wave']):
            subset=[x for x in checks if x['variable']==k]
            common=[x for x in subset if x['accepted_80pct'] and x.get('portal') is not None]
            mismatches=[x for x in common if x.get('match_rounded_0p1') is False]
            below=[x for x in subset if not x['accepted_80pct'] and x.get('portal') is not None]
            key=net+'_'+k
            summary[key]={
                'comparisons':len(common),'matches_rounded_0p1':len(common)-len(mismatches),
                'match_rate':round((len(common)-len(mismatches))/len(common),4) if common else None,
                'mismatch_count':len(mismatches),'below80_but_official_value':len(below),
                'mismatch_examples':mismatches[:12],
                'below80_examples':below[:10],
            }
    strict_matches=all(v['mismatch_count']==0 and v['comparisons']>0 for v in summary.values())
    result={'mode':'read-only','criterion':'>=80% of 48 half-hourly measurements PER VARIABLE per station/day',
            'minimum_count':THRESHOLD,'dates':DATES,'all_stat_fields_match_at_0p1':strict_matches,
            'decision':'NO_AUTOMATIC_PUBLISHING' if not strict_matches else 'FURTHER_TESTING_REQUIRED',
            'summary':summary,'results':all_results}
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('FINAL strict match:',strict_matches,'-- no public CSV modified.')
    return 0

if __name__=='__main__':raise SystemExit(main())