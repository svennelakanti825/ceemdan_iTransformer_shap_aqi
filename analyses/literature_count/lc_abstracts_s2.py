"""Deviation from the protocol's abstract sources: fill missing abstracts from Semantic Scholar's batch lookup by DOI.

Updates outputs/screening_set.csv in place (abstract, abstract_source) and adds the counts to outputs/flow_counts.json.
Usage: python lc_abstracts_s2.py
"""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent / 'outputs'


def s2_batch(dois: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for i in range(0, len(dois), 400):
        ids = [f'DOI:{d}' for d in dois[i:i + 400]]
        req = urllib.request.Request('https://api.semanticscholar.org/graph/v1/paper/batch?fields=abstract,externalIds',
                                     data=json.dumps({'ids': ids}).encode(), headers={'Content-Type': 'application/json'},
                                     method='POST')
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    res = json.load(r)
                break
            except Exception:
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError('Semantic Scholar batch failed')
        for doi, rec in zip(dois[i:i + 400], res):
            if rec and rec.get('abstract'):
                out[doi] = rec['abstract'].strip()
        time.sleep(3)
    return out


def main() -> None:
    u = pd.read_csv(OUT / 'screening_set.csv', dtype=str).fillna('')
    miss = u.index[(u.abstract == '') & (u.doi != '')]
    got = s2_batch([u.at[i, 'doi'] for i in miss])
    for i in miss:
        if u.at[i, 'doi'] in got:
            u.at[i, 'abstract'], u.at[i, 'abstract_source'] = got[u.at[i, 'doi']], 'Semantic Scholar (D1)'
    u.to_csv(OUT / 'screening_set.csv', index=False)
    flow = json.loads((OUT / 'flow_counts.json').read_text(encoding='utf-8'))
    flow['abstract_source_after_D1'] = u.abstract_source.replace('', 'none').value_counts().to_dict()
    (OUT / 'flow_counts.json').write_text(json.dumps(flow, indent=2), encoding='utf-8')
    print(flow['abstract_source_after_D1'])


if __name__ == '__main__':
    main()
