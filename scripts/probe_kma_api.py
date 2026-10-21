#!/usr/bin/env python3
"""Non-destructive KMA API probe. Never publishes or modifies station data."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = "https://apihub.kma.go.kr/api/typ02/openApi/SeaMtlyInfoService/"
STATIONS = [
    ("marine", "getDailyBuoy", "22101"),
    ("coastal", "getDailyWaveBuoy", "22441"),
]
PERIODS = [(2025, 9), (2026, 9), (2026, 10)]
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "api-probe-report.json"


def parse_response(content: bytes):
    body = content.decode("utf-8-sig", errors="replace").strip()
    if body.startswith("{") or body.startswith("["):
        obj = json.loads(body)
        obj = obj.get("response", obj) if isinstance(obj, dict) else obj
        if isinstance(obj, list):
            return obj, "JSON", None
        header = obj.get("header", {})
        code = str(header.get("resultCode", "00"))
        if code not in ("00", "0", "NORMAL_SERVICE", "200"):
            return [], "JSON", "API resultCode=" + code
        info = obj.get("body", obj)
        if isinstance(info, list):
            return info, "JSON", None
        items = info.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items or [], "JSON", None
    if body.startswith("<"):
        root = ET.fromstring(body)
        ns_strip = lambda key: key.rsplit("}", 1)[-1]
        for element in root.iter():
            element.tag = ns_strip(element.tag)
        code = root.findtext(".//resultCode")
        if code and code not in ("00", "0", "NORMAL_SERVICE", "200"):
            return [], "XML", "API resultCode=" + code
        items = []
        for item in root.findall(".//item"):
            items.append({child.tag: (child.text or "").strip() for child in item})
        return items, "XML", None
    return [], "UNKNOWN", "response is not XML or JSON"


def query(endpoint: str, station: str, year: int, month: int, key: str):
    params = {
        "pageNo": "1", "numOfRows": "100", "dataType": "JSON",
        "year": str(year), "month": f"{month:02d}", "station": station,
        "authKey": key,
    }
    url = BASE + endpoint + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(
        url, headers={"User-Agent": "marine-statistics-validation/1.0", "Accept": "application/json, application/xml, */*"}
    )
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            raw = response.read(500_000)
            status = response.status
    except Exception as exc:
        # Never print exception text: urllib errors may contain the query-string API key.
        return [], {"http_status": None, "error": "request_failed_" + type(exc).__name__}
    rows, fmt, error = parse_response(raw)
    return rows, {"http_status": status, "response_format": fmt, "error": error}


def normalize_day(value):
    if value is None:
        return None
    s = str(value).strip()
    digits = re.sub(r"[^0-9]", "", s)
    if len(digits) < 8:
        return None
    try:
        return dt.datetime.strptime(digits[:8], "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def numeric(value):
    if value is None or str(value).strip().lower() in ("", "-", "null", "nan", "-999.0", "-999"):
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def local_data(network: str, year: int, station: str):
    p = ROOT / "data" / network / f"{year}.csv"
    if not p.is_file():
        raise FileNotFoundError(f"expected repository data absent: {network}/{year}")
    result = {}
    with p.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("지점") == station:
                date = normalize_day(row.get("일시"))
                if date:
                    result[date] = numeric(row.get("평균 수온(°C)"))
    return result


def inspect_case(network, endpoint, station, year, month, key):
    remote, meta = query(endpoint, station, year, month, key)
    report = {
        "network": network, "station": station, "year": year, "month": month,
        "requested_endpoint": endpoint, **meta,
        "api_records": len(remote), "matching_month_records": 0,
        "overlapping_days": 0, "value_matches_0p11C": 0, "max_abs_error_C": None,
    }
    reference = local_data(network, year, station)
    max_error = 0.0
    for item in remote:
        if not isinstance(item, dict):
            continue
        item = {str(k).lower(): v for k, v in item.items()}
        date = normalize_day(item.get("tm"))
        if not date or not date.startswith(f"{year}-{month:02d}-"):
            continue
        # Ignore an unexpected station number; the request was station-scoped.
        station_id = item.get("stn_id") or item.get("stn")
        if station_id and str(station_id) != station:
            continue
        report["matching_month_records"] += 1
        a, b = numeric(item.get("tw")), reference.get(date)
        if a is not None and b is not None:
            report["overlapping_days"] += 1
            error = abs(a - b)
            max_error = max(max_error, error)
            if error <= 0.11:
                report["value_matches_0p11C"] += 1
    if report["overlapping_days"]:
        report["max_abs_error_C"] = round(max_error, 3)
    return report


def main():
    key = os.environ.get("KMA_API_KEY", "").strip()
    if not key:
        print("NOT READY: GitHub Secret KMA_API_KEY has not been configured.")
        return 2
    checks = []
    for network, endpoint, station in STATIONS:
        for year, month in PERIODS:
            result = inspect_case(network, endpoint, station, year, month, key)
            checks.append(result)
            print(
                f"{network} station={station} {year}-{month:02d}: "
                f"HTTP={result.get('http_status')} API_rows={result['api_records']} "
                f"same_month={result['matching_month_records']} "
                f"overlap={result['overlapping_days']} match={result['value_matches_0p11C']}"
                + (f" error={result['error']}" if result.get("error") else "")
            )
    # Both finalized-month observations must reconcile with the existing portal CSV.
    required = [c for c in checks if c["month"] == 9]
    passed = all(
        c["overlapping_days"] >= 5
        and c["value_matches_0p11C"] / c["overlapping_days"] >= 0.95
        for c in required
    )
    report = {
        "purpose": "Read-only API eligibility, freshness, and data-equivalence test",
        "does_not_modify_data": True,
        "passed": passed,
        "criteria": "For BOTH networks in Sep 2025 and Sep 2026: >=5 common days and >=95% water-temperature agreement within 0.11 C",
        "warning": "getDaily* belongs to the marine monthly bulletin; year/month may refer to publication rather than live observation. Oct 2026 is diagnostic only.",
        "checks": checks,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("VALIDATION " + ("PASSED" if passed else "NOT PASSED") + " — existing website data left unchanged.")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
