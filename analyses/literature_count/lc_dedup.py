"""Literature count, step 2: merge the exports, remove duplicates, attach abstracts (protocol sections 2 and 7).

Duplicates are removed by DOI, then by normalised title. Abstracts come from OpenAlex where available (also looked up
by DOI for Scopus-only records), otherwise from the Scopus Abstract Retrieval API, otherwise they stay empty and the
screener uses the landing page. Open-access locations are taken from OpenAlex.

Output: outputs/screening_set.csv (one row per unique record, with its sources) and outputs/flow_counts.json.
Usage: python lc_dedup.py
"""
from __future__ import annotations

import json
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd

import lc_search as L

HERE = Path(__file__).resolve().parent
SRC = HERE / 'outputs' / 'search'
OUT = HERE / 'outputs'


def norm_title(t: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(t or '').lower())


def openalex_by_doi(dois: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for i in range(0, len(dois), 50):
        chunk = [d for d in dois[i:i + 50] if d]
        if not chunk:
            continue
        url = 'https://api.openalex.org/works?' + urllib.parse.urlencode(
            {'filter': 'doi:' + '|'.join(chunk), 'per-page': 50, 'mailto': L.MAILTO})
        for r in L.get_json(url)['results']:
            out[(r.get('doi') or '').replace('https://doi.org/', '').lower()] = r
        time.sleep(1)
    return out


def oa_fields(r: dict) -> dict:
    locs = [l for l in (r.get('locations') or []) if l.get('is_oa')]
    urls = []
    for l in locs:
        for u in (l.get('pdf_url'), l.get('landing_page_url')):
            if u and u not in urls:
                urls.append(u)
    return {'is_oa': (r.get('open_access') or {}).get('is_oa'), 'oa_status': (r.get('open_access') or {}).get('oa_status'),
            'oa_urls': ' | '.join(urls), 'openalex_id': r.get('id'),
            'is_retracted': r.get('is_retracted'), 'oa_abstract': L.abstract_from_index(r.get('abstract_inverted_index'))}


def scopus_abstract(eid: str, key: str) -> str:
    url = f'https://api.elsevier.com/content/abstract/eid/{eid}?' + urllib.parse.urlencode({'view': 'META_ABS'})
    try:
        d = L.get_json(url, L.elsevier_headers(key))
    except RuntimeError:
        return ''
    core = (d.get('abstracts-retrieval-response') or {}).get('coredata') or {}
    return str(core.get('dc:description') or '').strip()


def main() -> None:
    oa = pd.read_csv(SRC / 'openalex_records.csv', dtype=str).fillna('')
    sc = pd.read_csv(SRC / 'scopus_records.csv', dtype=str).fillna('')
    oa['src'], sc['src'] = 'OpenAlex', 'Scopus'
    allr = pd.concat([oa, sc], ignore_index=True)
    allr['tkey'] = allr['title'].map(norm_title)
    n_identified = len(allr)

    # Group: same DOI, or (no DOI match) same normalised title.
    groups: dict[str, int] = {}
    gid = []
    for r in allr.itertuples():
        keys = [f'doi:{r.doi}'] if r.doi else []
        keys.append(f't:{r.tkey}')
        g = next((groups[k] for k in keys if k in groups), None)
        if g is None:
            g = len(set(groups.values()))
        for k in keys:
            groups.setdefault(k, g)
        gid.append(g)
    allr['gid'] = gid
    rows = []
    for g, d in allr.groupby('gid', sort=True):
        first = d.sort_values('src').iloc[0]           # OpenAlex row first when both exist
        rows.append({'doi': next((x for x in d.doi if x), ''), 'title': first.title,
                     'year': next((x for x in d.year if x), ''), 'venue': next((x for x in d.venue if x), ''),
                     'sources': '+'.join(sorted(set(d.src))), 'scopus_eid': next((x for x in d[d.src == 'Scopus'].source_id if x), ''),
                     'abstract': next((x for x in d.abstract if x), '')})
    u = pd.DataFrame(rows)

    # OpenAlex metadata (abstract, open access, retraction) by DOI for every record.
    meta = openalex_by_doi(sorted(set(u.doi) - {''}))
    extra = pd.DataFrame([oa_fields(meta[d]) if d in meta else {} for d in u.doi])
    u = pd.concat([u, extra], axis=1)
    u['abstract_source'] = ''
    has = u.abstract.str.len() > 0
    u.loc[has, 'abstract_source'] = 'OpenAlex'
    fill = ~has & (u.oa_abstract.fillna('').str.len() > 0)
    u.loc[fill, 'abstract'], u.loc[fill, 'abstract_source'] = u.loc[fill, 'oa_abstract'], 'OpenAlex (by DOI)'
    key = L.api_key()
    if key:
        for i in u.index[(u.abstract.str.len() == 0) & (u.scopus_eid != '')]:
            a = scopus_abstract(u.at[i, 'scopus_eid'], key)
            if a:
                u.at[i, 'abstract'], u.at[i, 'abstract_source'] = a, 'Scopus'
            time.sleep(0.3)
    u = u.drop(columns=['oa_abstract'])
    u.insert(0, 'rid', [f'R{i + 1:04d}' for i in range(len(u))])
    u.to_csv(OUT / 'screening_set.csv', index=False)
    flow = {'identified': {'OpenAlex': int(len(oa)), 'Scopus': int(len(sc)), 'total': n_identified},
            'duplicates_removed': n_identified - len(u), 'unique_records': int(len(u)),
            'by_sources': u.sources.value_counts().to_dict(),
            'abstract_source': u.abstract_source.replace('', 'none').value_counts().to_dict(),
            'retracted_flag': int((u.is_retracted == True).sum())}  # noqa: E712
    (OUT / 'flow_counts.json').write_text(json.dumps(flow, indent=2), encoding='utf-8')
    print(json.dumps(flow, indent=2))


if __name__ == '__main__':
    main()
