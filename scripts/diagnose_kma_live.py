#!/usr/bin/env python3
"""Read-only capability probe for approved KMA Ocean API endpoints.

Never logs request URLs, API keys, response bodies, or user-agent errors.
Does not modify public site data or manifest.
"""
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from xml.etree import ElementTree as ET

KEY = os.getenv("KMA_API_KEY", "").strip()
HOST = "https://apihub.kma.go.kr"
REPORT = Path("api-live-diagnostics.json")
CASES = [
    ("1.1_current_all", "/api/typ01/url/sea_obs.php",
     {"tm":"202610191200","stn":"0","help":"0"}),
    ("1.2_buoy_recent", "/api/typ01/url/kma_buoy2.php",
     {"tm1":"202610180000","tm2":"202610192300","stn":"22101","help":"0"}),
    ("1.2_buoy_archive", "/api/typ01/url/kma_buoy2.php",
     {"tm1":"202509010000","tm2":"202509022300","stn":"22101","help":"0"}),
    ("3.8_monthly_2025_xml", "/api/typ02/openApi/SeaMtlyInfoService/getDailyBuoy",
     {"pageNo":"1","numOfRows":"100","dataType":"XML","year":"2025","month":"09","station":"22101"}),
    ("3.8_monthly_2026_xml", "/api/typ02/openApi/SeaMtlyInfoService/getDailyBuoy",
     {"pageNo":"1","numOfRows":"100","dataType":"XML","year":"2026","month":"09","station":"22101"}),
    ("3.14_monthly_2025_xml", "/api/typ02/openApi/SeaMtlyInfoService/getDailyWaveBuoy",
     {"pageNo":"1","numOfRows":"100","dataType":"XML","year":"2025","month":"09","station":"22441"}),
]
def get(name,path,params):
    result={"case":name,"endpoint":path.rsplit("/",1)[-1],"http_status":None,
            "encoding":None,"items":0,"observed_rows":0,"result_code":None}
    if not KEY: result["error"]="secret_not_present"; return result
    args={**params,"authKey":KEY}
    url=HOST+path+"?"+urllib.parse.urlencode(args)
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"KMA-API-read-only-diagnostic/1.0"})
        with urllib.request.urlopen(req,timeout=30) as response:
            body=response.read(250000).decode("utf-8-sig",errors="replace")
            result["http_status"]=response.status
    except urllib.error.HTTPError as exc:
        result["http_status"]=exc.code
        result["error"]="http_error"
        return result
    except urllib.error.URLError:
        result["error"]="network_error"
        return result
    except Exception:
        result["error"]="connection_error"
        return result

    stripped=body.lstrip()
    if stripped.startswith("<"):
        result["encoding"]="xml"
        try:
            root=ET.fromstring(stripped)
            for item in root.iter(): item.tag=item.tag.split("}")[-1]
            code=root.findtext(".//resultCode")
            if code: result["result_code"]=str(code)[:12]
            els=root.findall(".//item")
            result["items"]=len(els)
            if els:
                one=els[0]
                result["first_item_fields"]=[c.tag[:40] for c in list(one)[:20]]
                def safe_num(k):
                    t=one.findtext(k)
                    if t is not None and re.fullmatch(r"[-+]?[0-9]{1,16}([.\-:][0-9]{1,16})*",t.strip()):
                        return t.strip()[:25]
                    return None
                result["sample"]={k:safe_num(k) for k in ["tm","tw","wh_sig","stn_id"] if safe_num(k)}
        except Exception:
            result["error"]="invalid_xml"
    elif stripped.startswith(("{","[")):
        result["encoding"]="json"
        try:
            obj=json.loads(stripped)
            if isinstance(obj,dict):
                result["top_keys"]=list(obj.keys())[:15]
                response=obj.get("response",obj)
                if isinstance(response,dict):
                    header=response.get("header") or {}
                    if isinstance(header,dict):result["result_code"]=str(header.get("resultCode",""))[:12]
                    body2=response.get("body") or {}
                    if isinstance(body2,dict):
                        items=body2.get("items") or {}
                        if isinstance(items,dict):items=items.get("item") or []
                        if isinstance(items,dict):items=[items]
                        if isinstance(items,list):
                            result["items"]=len(items)
                            if items and isinstance(items[0],dict):
                                result["first_item_fields"]=list(items[0].keys())[:24]
                                result["sample"]={k:str(items[0][k])[:30] for k in ["tm","tw","wh_sig","stn_id"] if k in items[0] and re.fullmatch(r"[-+0-9.:\-]+",str(items[0][k]))}
                else: result["response_type"]=type(response).__name__
            elif isinstance(obj,list): result["items"]=len(obj)
        except Exception:
            result["error"]="invalid_json"
    else:
        result["encoding"]="text"
        lines=[ln.strip() for ln in body.splitlines() if ln.strip()]
        data=[ln for ln in lines if not ln.startswith(("#","//"))]
        result["observed_rows"]=len(data)
        if data:
            first=data[0].split()
            result["field_count"]=len(first)
            # Sampling ONLY timestamps and station IDs matching a strict numeric pattern.
            numeric=[x[:15] for x in first[:3] if re.fullmatch(r"[0-9.\-]+",x)]
            result["numeric_prefix_fields"]=numeric
        result["comment_lines"]=len(lines)-len(data)
    return result

def main():
    records=[]
    for name,path,params in CASES:
        row=get(name,path,params); records.append(row)
        print(f"{name}: HTTP={row.get('http_status')} kind={row.get('encoding')} "
              f"observations={row.get('observed_rows')} items={row.get('items')} "
              f"code={row.get('result_code')} error={row.get('error')}")
    REPORT.write_text(json.dumps({"read_only":True,"cases":records},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0  # Diagnostic, never change actual data or signal a green light.

if __name__=="__main__":
    raise SystemExit(main())
