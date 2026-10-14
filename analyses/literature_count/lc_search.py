"""Literature count, step 1: run the fixed searches and save the raw exports (protocol section 2).

Sources: OpenAlex (no key), Scopus Search API and ScienceDirect Search API (Elsevier key). The key is read from the
file ~/.elsevier_api_key (one line) or the ELSEVIER_API_KEY environment variable. It is never printed or saved.

Outputs (outputs/search/): <source>_raw.jsonl (every record as returned), <source>_records.csv (DOI, title, year,
venue, type, open-access fields, abstract where returned), search_log.json (date, exact queries, counts, file hashes).

Usage:
  python lc_search.py check        # key present? entitlement test with one tiny request per Elsevier API, no export
  python lc_search.py run          # full searches and exports (only after the protocol is fixed)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs' / 'search'
MAILTO = os.environ.get('OPENALEX_MAILTO', '')
YEARS = (2015, 2025)

DEC = ('"empirical mode decomposition" OR CEEMDAN OR EEMD OR "variational mode decomposition" OR VMD OR wavelet OR '
       '"singular spectrum analysis"')
AQ = '"air quality" OR AQI OR "PM2.5" OR PM10 OR "particulate matter" OR NO2 OR ozone'
QUERIES = {
    'openalex': f'({DEC}) AND ({AQ}) AND (forecast OR forecasting OR prediction)',
    'scopus': (f'TITLE-ABS-KEY(({DEC}) AND ({AQ}) AND (forecast* OR predict*)) AND PUBYEAR > {YEARS[0] - 1} AND '
               f'PUBYEAR < {YEARS[1] + 1} AND (DOCTYPE(ar) OR DOCTYPE(cp))'),
    'sciencedirect': f'({DEC}) AND ({AQ}) AND (forecast OR forecasting OR prediction)',
}


def api_key() -> str | None:
    f = Path.home() / '.elsevier_api_key'
    if f.exists():
        k = f.read_text(encoding='utf-8').strip()
        return k or None
    return os.environ.get('ELSEVIER_API_KEY') or None


def get_json(url: str, headers: dict | None = None, data: bytes | None = None, method: str = 'GET',
             tries: int = 5) -> dict:
    for i in range(tries):
        req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(5 * (i + 1))
                continue
            body = e.read().decode('utf-8', 'replace')[:300]
            raise RuntimeError(f'HTTP {e.code} for {url.split("?")[0]}: {body}') from None
    raise RuntimeError('unreachable')


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def abstract_from_index(inv: dict | None) -> str:
    if not inv:
        return ''
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return ' '.join(w for _, w in pos)


def search_openalex() -> list[dict]:
    flt = (f'title_and_abstract.search:{QUERIES["openalex"]},publication_year:{YEARS[0]}-{YEARS[1]},'
           f'type:article|proceedings-article')
    out, cursor = [], '*'
    while cursor:
        url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(
            {'filter': flt, 'per-page': 200, 'cursor': cursor, 'mailto': MAILTO})
        d = get_json(url)
        out += d['results']
        cursor = d['meta'].get('next_cursor')
        time.sleep(1)
    return out


def elsevier_headers(key: str) -> dict:
    return {'X-ELS-APIKey': key, 'Accept': 'application/json'}


def search_scopus(key: str, limit: int | None = None) -> list[dict]:
    out, start = [], 0
    while True:
        url = 'https://api.elsevier.com/content/search/scopus?' + urllib.parse.urlencode(
            {'query': QUERIES['scopus'], 'start': start, 'count': 25, 'view': 'STANDARD'})
        d = get_json(url, elsevier_headers(key))['search-results']
        entries = [e for e in d.get('entry', []) if 'error' not in e]
        out += entries
        total = int(d.get('opensearch:totalResults', 0))
        start += 25
        if not entries or start >= total or (limit and len(out) >= limit):
            return out
        time.sleep(0.5)


def search_sciencedirect(key: str, limit: int | None = None) -> list[dict]:
    out, offset = [], 0
    while True:
        body = json.dumps({'qs': QUERIES['sciencedirect'], 'date': f'{YEARS[0]}-{YEARS[1]}',
                           'display': {'offset': offset, 'show': 100}}).encode()
        h = {**elsevier_headers(key), 'Content-Type': 'application/json'}
        d = get_json('https://api.elsevier.com/content/search/sciencedirect', h, body, 'PUT')
        res = d.get('results', [])
        out += res
        offset += 100
        if not res or offset >= int(d.get('resultsFound', 0)) or (limit and len(out) >= limit):
            return out
        time.sleep(0.5)


def to_frame(source: str, recs: list[dict]) -> pd.DataFrame:
    rows = []
    for r in recs:
        if source == 'openalex':
            loc = r.get('best_oa_location') or {}
            rows.append({'doi': (r.get('doi') or '').replace('https://doi.org/', '').lower(), 'title': r.get('title'),
                         'year': r.get('publication_year'), 'venue': ((r.get('primary_location') or {}).get('source')
                                                                      or {}).get('display_name'),
                         'type': r.get('type'), 'is_oa': (r.get('open_access') or {}).get('is_oa'),
                         'oa_url': loc.get('pdf_url') or loc.get('landing_page_url'),
                         'abstract': abstract_from_index(r.get('abstract_inverted_index')), 'source_id': r.get('id')})
        elif source == 'scopus':
            rows.append({'doi': (r.get('prism:doi') or '').lower(), 'title': r.get('dc:title'),
                         'year': str(r.get('prism:coverDate', ''))[:4], 'venue': r.get('prism:publicationName'),
                         'type': r.get('subtypeDescription'), 'is_oa': r.get('openaccessFlag'), 'oa_url': None,
                         'abstract': '', 'source_id': r.get('eid')})
        else:
            rows.append({'doi': (r.get('doi') or '').lower(), 'title': r.get('title'),
                         'year': str(r.get('publicationDate', ''))[:4], 'venue': r.get('sourceTitle'),
                         'type': None, 'is_oa': r.get('openAccess'), 'oa_url': r.get('uri'),
                         'abstract': '', 'source_id': r.get('pii')})
    return pd.DataFrame(rows)


def check() -> None:
    key = api_key()
    print('Elsevier key found:', bool(key))
    print('OpenAlex hit count:', get_json('https://api.openalex.org/works?' + urllib.parse.urlencode(
        {'filter': f'title_and_abstract.search:{QUERIES["openalex"]},publication_year:{YEARS[0]}-{YEARS[1]},'
                   f'type:article|proceedings-article', 'per-page': 1, 'mailto': MAILTO}))['meta']['count'])
    if not key:
        return
    for name, fn in (('Scopus', search_scopus), ('ScienceDirect', search_sciencedirect)):
        try:
            n = len(fn(key, limit=1))
            print(f'{name}: request accepted, first page returned {n} record(s)')
        except RuntimeError as e:
            print(f'{name}: {str(e).replace(key, "<key>")}')


def run() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    key = api_key()
    log = {'run_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'years': YEARS, 'queries': QUERIES,
           'sources': {}}
    plan = [('openalex', search_openalex)]
    if key:
        plan += [('scopus', lambda: search_scopus(key))]   # ScienceDirect: key not authorised (protocol section 2)
    for name, fn in plan:
        try:
            recs = fn()
        except RuntimeError as e:
            log['sources'][name] = {'error': str(e).replace(key or '\0', '<key>')}
            print(name, 'failed:', log['sources'][name]['error'])
            continue
        raw = OUT / f'{name}_raw.jsonl'
        raw.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in recs) + '\n', encoding='utf-8')
        csv = OUT / f'{name}_records.csv'
        to_frame(name, recs).to_csv(csv, index=False)
        log['sources'][name] = {'records': len(recs), 'raw_sha256': sha(raw), 'csv_sha256': sha(csv)}
        print(name, len(recs), 'records')
    (OUT / 'search_log.json').write_text(json.dumps(log, indent=2), encoding='utf-8')


if __name__ == '__main__':
    {'check': check, 'run': run}[sys.argv[1] if len(sys.argv) > 1 else 'check']()
