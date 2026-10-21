#!/usr/bin/env python3
"""Merge official KMA portal daily CSV into existing GitHub Pages year files.

Uploads must be named OBS_BUOY_DD_*.csv or OBS_CWBUOY_DD_*.csv.
Existing station/day values outside the uploaded date ranges are preserved.
Outputs remain compatible with Stage 2-A manifest and client-side data engine.
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
M = ('지점', '일시', '평균 수온(°C)')
C = M + ('최고 수온(°C)', '최저 수온(°C)', '평균 유의 파고(m)',
         '평균 파고(m)', '최고 유의 파고(m)', '최고 최대 파고(m)',
         '평균 파주기(sec)', '최고 파주기(sec)')
COLUMNS = {'marine': M, 'coastal': C}
PATTERN = re.compile(r'^OBS_(BUOY|CWBUOY)_DD_[0-9A-Za-z_-]+\.csv$', re.I)


def csv_bytes(rows, cols):
    out = io.StringIO(newline='')
    w = csv.writer(out, lineterminator='\n')
    w.writerow(cols)
    for key in sorted(rows, key=lambda k: (int(k[0]), k[1])):
        w.writerow(rows[key])
    return ('\ufeff' + out.getvalue()).encode('utf-8')


def read_csv(path, expected_cols, upload=False):
    raw = path.read_bytes()
    if not raw or len(raw) > 25_000_000:
        raise ValueError(f'{path.name}: empty file or larger than 25MB')
    encodings = ('utf-8-sig', 'cp949') if upload else ('utf-8-sig',)
    for enc in encodings:
        try:
            content = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f'{path.name}: neither UTF-8 nor CP949')
    reader = csv.reader(io.StringIO(content, newline=''))
    hdr = next(reader, None)
    if not hdr:
        raise ValueError(f'{path.name}: missing CSV header')
    hdr = [s.strip().lstrip('\ufeff') for s in hdr]
    if tuple(hdr) != expected_cols:
        raise ValueError(f'{path.name}: unexpected columns; use original KMA daily CSV with full columns')
    result = {}
    max_day = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date() + dt.timedelta(days=1)
    for lineno, values in enumerate(reader, 2):
        if not values or all(not str(v).strip() for v in values):
            continue
        if len(values) != len(hdr):
            raise ValueError(f'{path.name} line {lineno}: column count {len(values)} not {len(hdr)}')
        vals = [v.strip() for v in values]
        station, date = vals[:2]
        if not re.fullmatch(r'\d{5}', station):
            raise ValueError(f'{path.name} line {lineno}: invalid station number')
        try:
            parsed_date = dt.date.fromisoformat(date)
        except ValueError:
            raise ValueError(f'{path.name} line {lineno}: invalid date') from None
        if not (dt.date(1990, 1, 1) <= parsed_date <= max_day):
            raise ValueError(f'{path.name} line {lineno}: date outside supported period')
        for i, value in enumerate(vals[2:], 2):
            if value in ('', '-', 'NaN'):
                vals[i] = ''
                continue
            try:
                v = float(value)
            except ValueError:
                raise ValueError(f'{path.name} line {lineno}: nonnumeric observation in {hdr[i]}') from None
            if not (v == v and abs(v) < 1e6):
                raise ValueError(f'{path.name} line {lineno}: invalid numeric observation')
            # Preserve the portal's original numeric values, including its
            # sometimes anomalous QC/sentinel values (e.g. 90 m, 825.6 C).
            # These must be inspected separately, not silently replaced here.
        key = (station, date)
        if key in result and result[key] != vals:
            raise ValueError(f'{path.name}: conflicting duplicate station+date {station} {date}')
        result[key] = vals
        if len(result) > 600_000:
            raise ValueError(f'{path.name}: unusually many rows')
    if not result:
        raise ValueError(f'{path.name}: no observation records')
    return result


def classify(path):
    if not PATTERN.fullmatch(path.name):
        raise ValueError(f'{path.name}: upload official OBS_BUOY_DD_*.csv or OBS_CWBUOY_DD_*.csv only')
    return 'marine' if path.name.upper().startswith('OBS_BUOY_DD_') else 'coastal'


def update_manifest(manifest, repo_root, stats, originals, names):
    for item in manifest['datasets']:
        path = repo_root / item['path']
        raw = path.read_bytes()
        network, year_str = item['source'], str(item['year'])
        info = stats[(network, int(year_str))]
        item['rows'] = info['rows']
        item['last_observation'] = info['last']
        item['bytes'] = len(raw)
        item['sha256'] = hashlib.sha256(raw).hexdigest()
    for network in ('marine', 'coastal'):
        all_rows = [v for (n, _), v in stats.items() if n == network]
        manifest['summary'][network] = {
            'records': sum(v['rows'] for v in all_rows),
            'stations_with_history': len(set().union(*(v['stations'] for v in all_rows))),
            'first_observation': min(v['first'] for v in all_rows),
            'last_observation': max(v['last'] for v in all_rows),
        }
    manifest['update_mode'] = 'semi-automatic-official-portal-csv'
    manifest['autoupdate'] = False
    manifest['description'] = 'Official KMA data portal daily CSV; manually uploaded, automatically validated and merged'
    manifest['last_portal_import_at_kst'] = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec='seconds')
    manifest['last_portal_import_files'] = names
    # The initial download date remains historical provenance; the most recent
    # user-upload time is separate because the original download date is unknown.
    return manifest


def merge(repo, upload_folder, apply):
    incoming = sorted(upload_folder.glob('*.csv'))
    other = [p.name for p in upload_folder.iterdir() if p.is_file() and p.name != 'README.md' and p.suffix.lower() != '.csv']
    if other:
        raise ValueError('Unexpected file in uploads/: ' + ', '.join(other[:6]))
    if not incoming:
        print('No new portal CSVs; nothing to change.')
        return {'changed': False, 'files': []}
    parsed = defaultdict(dict)
    names = []
    for path in incoming:
        network = classify(path)
        rows = read_csv(path, COLUMNS[network], upload=True)
        for key, vals in rows.items():
            if key in parsed[network] and parsed[network][key] != vals:
                raise ValueError(f'{path.name}: conflicts with another uploaded file for station/day {key}')
            parsed[network][key] = vals
        names.append(path.name)
    manifest_path = repo / 'data/manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest.get('format_version') != 1:
        raise ValueError('Unknown manifest format')
    index = {(item['source'], int(item['year'])): item for item in manifest['datasets']}
    changed_files = {}
    counters = dict(added=0, corrected=0, unchanged=0, changed_years=[])
    modified = defaultdict(dict)
    for network, rows in parsed.items():
        by_year = defaultdict(dict)
        for key, value in rows.items():
            by_year[int(key[1][:4])][key] = value
        for year, updates in sorted(by_year.items()):
            path = repo / f'data/{network}/{year}.csv'
            existing = read_csv(path, COLUMNS[network]) if path.exists() else {}
            for key, value in updates.items():
                before = existing.get(key)
                if before is None: counters['added'] += 1
                elif before != value: counters['corrected'] += 1
                else: counters['unchanged'] += 1
                existing[key] = value
            raw_new = csv_bytes(existing, COLUMNS[network])
            if not path.exists() or raw_new != path.read_bytes():
                changed_files[path] = raw_new
                counters['changed_years'].append(f'{network}/{year}')
            modified[(network, year)] = existing
            if (network, year) not in index:
                item = {'source': network, 'year': year, 'path': f'data/{network}/{year}.csv'}
                manifest['datasets'].append(item)
                index[(network, year)] = item
    # All validations are completed before any filesystem write.
    if apply:
        for path, data in changed_files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    stats = {}
    for item in manifest['datasets']:
        network, year = item['source'], int(item['year'])
        rows = modified.get((network, year))
        if rows is None:
            rows = read_csv(repo / item['path'], COLUMNS[network])
        keys = list(rows)
        stats[(network, year)] = {
            'rows': len(rows), 'stations': {key[0] for key in keys},
            'first': min(key[1] for key in keys), 'last': max(key[1] for key in keys)
        }
    if apply:
        if changed_files:
            manifest['datasets'].sort(key=lambda r: (r['source'], r['year']))
            update_manifest(manifest, repo, stats, index, names)
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        for path in incoming:
            path.unlink()
    print(json.dumps({'uploaded_csvs': names, 'apply': apply, **counters}, ensure_ascii=False, indent=2))
    return {'changed': bool(changed_files), 'files': names, **counters}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        merge(args.repo, args.repo / 'uploads', apply=args.apply)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('IMPORT REJECTED:', exc)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())