"""Download the CPCB daily AQI bulletin file used by the E7 scripts and check its SHA-256.

The file is not redistributed here. It is the urbanemissions.info compilation (GPL-3.0) at the commit that was current
when it was downloaded for this study (8 Oct 2026). The SHA-256 must match SHA256SUMS.txt in this folder.

Usage: python fetch_bulletins.py
"""
from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = 'AllIndiaBulletinsMaster2025_openrefined.csv'
COMMIT = 'eff4f2b0c0efc5da3e7ad4885a2811921659c7f9'
URL = f'https://raw.githubusercontent.com/urbanemissionsinfo/AQI_bulletins/{COMMIT}/data/Processed/{NAME}'


def expected() -> str:
    for line in (HERE / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest, name = line.split()
        if name.lstrip('*') == NAME:
            return digest
    raise SystemExit(f'{NAME} is not listed in SHA256SUMS.txt')


def main() -> None:
    out = HERE / NAME
    if not out.exists():
        with urllib.request.urlopen(URL, timeout=120) as r:
            out.write_bytes(r.read())
    got = hashlib.sha256(out.read_bytes()).hexdigest()
    if got != expected():
        raise SystemExit(f'{NAME}: SHA-256 {got} does not match SHA256SUMS.txt')
    print(f'{NAME}: SHA-256 matches ({got})')


if __name__ == '__main__':
    main()
