"""Literature count, step 4: fetch the open full text of records in the coding order and extract plain text.

Downloads are untrusted data: they go to outputs/fulltext_cache/ (never executed) and their text to
outputs/fulltext_text/<rid>.txt. Sources, in order: the OpenAlex open-access URLs (PDF first, then landing pages), and for
Elsevier DOIs the Elsevier article API, which serves open-access articles to any key. The retrieval route is logged in
outputs/fulltext_log.csv.

Usage: python lc_fulltext.py <first_rank> <last_rank>
"""
from __future__ import annotations

import html
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

import lc_search as L

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs'
CACHE, TEXT = OUT / 'fulltext_cache', OUT / 'fulltext_text'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36')


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ('script', 'style', 'nav', 'header', 'footer'):
            self.skip += 1
        if tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'li', 'tr', 'br', 'section'):
            self.parts.append('\n')

    def handle_endtag(self, tag: str) -> None:
        if tag in ('script', 'style', 'nav', 'header', 'footer') and self.skip:
            self.skip -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def html_text(raw: bytes) -> str:
    p = _Text()
    p.feed(raw.decode('utf-8', 'replace'))
    t = html.unescape(''.join(p.parts))
    return re.sub(r'\n\s*\n+', '\n\n', re.sub(r'[ \t]+', ' ', t)).strip()


def get(url: str, headers: dict | None = None) -> tuple[bytes, str]:
    url = urllib.parse.quote(url, safe=':/?&=%#+,;@~')
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*', **(headers or {})})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read(), r.headers.get('Content-Type', '')


def pdf_text(path: Path) -> str:
    out = path.with_suffix('.txt')
    subprocess.run(['pdftotext', '-enc', 'UTF-8', str(path), str(out)], check=True, capture_output=True, timeout=120)
    t = out.read_text(encoding='utf-8', errors='replace')
    out.unlink()
    return t


def fetch(rid: str, doi: str, urls: list[str]) -> tuple[str, str, str]:
    """Returns (text, route, note)."""
    notes = []
    for u in sorted(urls, key=lambda x: (not x.lower().endswith('.pdf') and '/pdf' not in x.lower())):
        try:
            raw, ctype = get(u)
        except Exception as e:  # noqa: BLE001  (logged, next URL)
            notes.append(f'{u}: {getattr(e, "code", "") or type(e).__name__}')
            continue
        if raw[:4] == b'%PDF':
            p = CACHE / f'{rid}.pdf'
            p.write_bytes(raw)
            try:
                t = pdf_text(p)
            except subprocess.SubprocessError as e:
                notes.append(f'{u}: pdftotext failed {type(e).__name__}')
                continue
            if len(t) > 5000:
                return t, f'pdf {u}', '; '.join(notes)
            notes.append(f'{u}: pdf text too short ({len(t)})')
        else:
            t = html_text(raw)
            (CACHE / f'{rid}.html').write_bytes(raw)
            if len(t) > 15000 and re.search(r'(?i)\b(method|methodology|materials)\b', t):
                return t, f'html {u}', '; '.join(notes)
            notes.append(f'{u}: html text {len(t)} chars, no full text')
    try:
        import json as _j, urllib.parse as _up
        q = _j.loads(get('https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + _up.urlencode(
            {'query': f'DOI:"{doi}"', 'format': 'json', 'resultType': 'lite'}))[0])
        pmcid = next((x.get('pmcid') for x in q.get('resultList', {}).get('result', []) if x.get('pmcid')), None)
        if pmcid:
            raw, _ = get(f'https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML')
            t = html_text(raw)
            if len(t) > 5000:
                return t, f'europepmc {pmcid}', '; '.join(notes)
            notes.append(f'europepmc {pmcid} text {len(t)}')
    except Exception as e:  # noqa: BLE001  (logged, next route)
        notes.append(f'europepmc {type(e).__name__}')
    manual = OUT / 'manual_pdfs' / f'{rid}.pdf'
    if manual.exists():
        return pdf_text(manual), 'manual download by the first author', '; '.join(notes)
    key = L.api_key()
    if doi.startswith('10.1016/') and key:
        try:
            raw, _ = get(f'https://api.elsevier.com/content/article/doi/{doi}?httpAccept=text/plain',
                         {'X-ELS-APIKey': key, 'Accept': 'text/plain'})
            t = raw.decode('utf-8', 'replace')
            if len(t) > 5000:
                return t, 'elsevier article API (open access)', '; '.join(notes)
            notes.append(f'elsevier API text {len(t)} chars')
        except urllib.error.HTTPError as e:
            notes.append(f'elsevier API HTTP {e.code}')
    return '', 'not obtained', '; '.join(notes)


def main() -> None:
    a, b = int(sys.argv[1]), int(sys.argv[2])
    CACHE.mkdir(parents=True, exist_ok=True)
    TEXT.mkdir(parents=True, exist_ok=True)
    order = pd.read_csv(OUT / 'coding_order.csv', dtype=str).fillna('')
    logp = OUT / 'fulltext_log.csv'
    log = pd.read_csv(logp, dtype=str).fillna('') if logp.exists() else pd.DataFrame(columns=['rank', 'rid', 'route', 'chars', 'note'])
    for r in order[(order['rank'].astype(int) >= a) & (order['rank'].astype(int) <= b)].itertuples():
        if r.rid in set(log[log.route != 'not obtained'].rid):
            continue
        log = log[log.rid != r.rid]
        t, route, note = fetch(r.rid, r.doi, [u.strip() for u in r.oa_urls.split('|') if u.strip()])
        if t:
            (TEXT / f'{r.rid}.txt').write_text(t, encoding='utf-8')
        log = pd.concat([log, pd.DataFrame([{'rank': r.rank, 'rid': r.rid, 'route': route, 'chars': len(t), 'note': note}])])
        print(f'{r.rank:>3} {r.rid} {route[:60]:60s} {len(t):>7}', flush=True)
        log.to_csv(logp, index=False)
        time.sleep(1)
    log.to_csv(logp, index=False)


if __name__ == '__main__':
    main()
