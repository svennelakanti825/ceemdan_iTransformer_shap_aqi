"""C2 feature builder (task C2-T2): every input of the C2 confirmatory weather test, built as pre-registered.

Pre-registration: C2_PREREGISTRATION.md (approved 10 Oct 2026), sections 2-4 and 10. This module fits nothing.
  meta    city, split (train / val / test), origin day t, target day t+1, y (carried, never used to build a
          feature), period (pre / lock on the test split, na otherwise)
  base    12 pollutants x 7 days (N1) + 5 causal CEEMDAN channels x 7 days + city one-hot, as E5 BASE but on all
          three splits (identical to E1's CAUSAL design matrix)
  blocks  MET (weather bank at t), MET_PP (bank at t+1), MET_PP_LONG (MET_PP, subseasonal and seasonal bands only),
          POOL_j / POOL_PP_j (j = 0..9, pool years 2005-2014), E5NULL_k / E5NULL_PP_k (k = 1..4, E5 swap_dates)
Structure: windows() builds meta and BASE from the AQI table; weather_blocks() builds every weather block from
meta's city and dates and the two ERA5 tables only, so AQI cannot enter a weather feature. design() gives the
train / validation / test arrays of one arm (used by the runner and the tests).
Before anything is built, every pinned input is checked against Appendix A of the pre-registration, and the
pre-registration and addendum A1 against their approved hashes. build() takes optional in-memory replacements of the AQI table
and the ERA5 tables (for the tests in tests/test_c2x.py); by default it reads the pinned files.
Usage: python c2x_features.py   -> builds, checks, prints the summary, writes outputs/c2_t2_features_summary.txt
"""
from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import common
from common import CHANNELS, FEATURES, NS, OUT, build_lb7, city_calendars, load_causal, load_df
from e1_leakage_contrast import SEQ
from e5_driver_band_precheck import BANDS, MV, met_bank, swap_dates

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PREREG = HERE / 'C2_PREREGISTRATION.md'
PREREG_SHA256 = 'c3b38c294ba09b1f872e414d48e40623adb1f9d1382473099c2cc78494debd50'   # approved 10 Oct 2026
ADDENDUM_A1 = HERE / 'C2_PREREGISTRATION_ADDENDUM_A1.md'
ADDENDUM_A1_SHA256 = 'c2d32acd5cbe91dede7cd460ee0ceee2deb029755f0d58964e8d39915e134ed7'   # approved 10 Oct 2026
ADDENDUM_A2 = HERE / 'C2_PREREGISTRATION_ADDENDUM_A2.md'          # platform: Linux x86-64 (Colab CPU), n_jobs 2
ADDENDUM_A2_SHA256 = '0f3e15ce2d78ed9dedf2c436f417c4c80e9a81c9e14de38a30c9a2854151348c'   # approved 10 Oct 2026
CACHE_PREFIX = 'Implementation/revision_1/phase4_v2_results_r1/models/c5_decompositions_ext_ar/'
# The pinned AQI file, located relative to the repository. common.py (pinned, unchanged) holds the same file as an
# absolute Windows path; build() points common.DATA here so the build also runs on Linux (Colab, reviewers).
DATA_REL = 'exports/paper_draft_v1/revision_1/Revised_Overleaf/audit_inputs/city_day.csv'
TEXT_SUFFIXES = {'.py', '.md', '.csv', '.txt', '.json'}
N_PINNED = 30

N_POOL, POOL_FIRST, OWN_FIRST = 10, 2005, 2015      # pool rule: P_j(y) = 2005 + ((y - 2015 + j) mod 10)
N_E5 = 4
LOCKDOWN_START = pd.Timestamp('2020-03-25')
SPLITS = ('train', 'val', 'test')
EXPECTED_WINDOWS = {'train': 11569, 'val': 1510, 'test': 6171}
N_CITIES = 18
LONG_BANDS = ('subs', 'seas')
MCOLS = [f'{v}|{b}' for v in MV for b in BANDS]       # bank column order, as E5


@dataclass
class C2Data:
    meta: pd.DataFrame
    base: np.ndarray
    base_cols: list[str]
    blocks: dict[str, np.ndarray]
    block_cols: dict[str, list[str]]
    lookups: dict[str, tuple[pd.DatetimeIndex, pd.DatetimeIndex]]    # block -> (own lookup dates, dates read)
    checks: list[str]


def sha256_rule(path: Path) -> str:
    """Pre-registration section 2: text files after CRLF -> LF, binary files as they are."""
    b = path.read_bytes()
    if path.suffix in TEXT_SUFFIXES:
        b = b.replace(b'\r\n', b'\n')
    return hashlib.sha256(b).hexdigest()


def appendix_a() -> list[tuple[str, Path, str]]:
    """Appendix A of the approved pre-registration: (SHA-256 by the hash rule, path, raw-bytes SHA-256 or '')."""
    app = PREREG.read_text(encoding='utf-8').split('## Appendix A')[1].split('## Appendix B')[0]
    rows = re.findall(r'^\| ([0-9a-f]{64}) \| (\S+)(?: \(raw bytes: ([0-9a-f]{64})\))? \|$', app, re.M)
    if len(rows) != N_PINNED:
        sys.exit(f'STOP: Appendix A lists {len(rows)} files, expected {N_PINNED}')
    return [(want, REPO / (CACHE_PREFIX + rel[4:] if rel.startswith('.../') else rel), raw) for want, rel, raw in rows]


def verify_inputs() -> list[str]:
    """Stop unless the pre-registration is the approved one and every pinned input matches its Appendix A."""
    for doc, want in ((PREREG, PREREG_SHA256), (ADDENDUM_A1, ADDENDUM_A1_SHA256), (ADDENDUM_A2, ADDENDUM_A2_SHA256)):
        got = sha256_rule(doc) if doc.is_file() else 'missing'
        if got != want:
            sys.exit(f'STOP: {doc.name} is not the approved version ({got})')
    rows = appendix_a()
    bad, n_raw = [], 0
    for want, p, raw in rows:
        rel = p.relative_to(REPO).as_posix()
        if not p.is_file() or sha256_rule(p) != want:
            bad.append(rel)
        elif raw:
            n_raw += 1
            if hashlib.sha256(p.read_bytes()).hexdigest() != raw:
                bad.append(rel + ' (raw bytes)')
    if bad:
        sys.exit('STOP: pinned inputs do not match the pre-registration: ' + ', '.join(bad))
    return [f'inputs: pre-registration and addenda A1 and A2 hashes are the approved ones; {len(rows)} pinned files and '
            f'{n_raw} raw ERA5 hashes match Appendix A']


def pool_dates(dates: pd.DatetimeIndex, j: int) -> pd.DatetimeIndex:
    """Pre-registered pool rule: same month and day in year 2005 + ((y - 2015 + j) mod 10); 29 Feb -> 28 Feb."""
    y, m, d = dates.year.to_numpy(), dates.month.to_numpy(), dates.day.to_numpy()
    d = np.where((m == 2) & (d == 29), 28, d)
    py = POOL_FIRST + (y - OWN_FIRST + j) % N_POOL
    return pd.DatetimeIndex(pd.to_datetime(pd.DataFrame({'year': py, 'month': m, 'day': d})))


def read_era5(name: str) -> pd.DataFrame:
    return pd.read_csv(OUT / name, parse_dates=['Date'])


def bank_from(met: pd.DataFrame) -> pd.DataFrame:
    """E5 transforms and band bank (met_bank, imported unchanged) for one daily ERA5 table."""
    met = met.copy()
    met['lblh'], met['lvent'], met['sprecip'] = np.log(met['blh']), np.log(met['vent']), np.sqrt(met['precip'])
    return met_bank(met)


def load_bank(name: str) -> pd.DataFrame:
    return bank_from(read_era5(name))


def block_names() -> list[str]:
    names = ['MET', 'MET_PP']
    for pp in ('', '_PP'):
        names += [f'POOL{pp}_{j}' for j in range(N_POOL)] + [f'E5NULL{pp}_{k}' for k in range(1, N_E5 + 1)]
    return names


def arm_names() -> list[str]:
    """The 32 pre-registered arms, in the order of pre-registration section 4."""
    return (['BASE', 'MET', 'MET_PP', 'MET_PP_LONG'] + [f'POOL_{j}' for j in range(N_POOL)]
            + [f'POOL_PP_{j}' for j in range(N_POOL)] + [f'E5NULL_{k}' for k in range(1, N_E5 + 1)]
            + [f'E5NULL_PP_{k}' for k in range(1, N_E5 + 1)])


def windows(df: pd.DataFrame) -> tuple[pd.DataFrame, np.ndarray, list[str], list[str]]:
    """meta and BASE from the AQI table, with the run-of-record pipeline (common.py, unchanged)."""
    cities = city_calendars(df)
    raw = build_lb7(cities, SEQ)
    names = list(cities)
    base_parts, meta = [], []
    for ci, c in enumerate(names):
        info, r = cities[c], raw[c]
        st = r['starts']
        n_tr, n_trv, n = r['splits']
        assert n == len(st), c
        days = st[:, None] + np.arange(SEQ)[None, :]
        cal_dates = pd.to_datetime(info['cal']['Date']).to_numpy()
        origin, target = pd.DatetimeIndex(cal_dates[st + SEQ - 1]), pd.DatetimeIndex(cal_dates[st + SEQ])
        assert ((target - origin) == pd.Timedelta('1D')).all(), f'{c}: target is not the day after the origin'
        onehot = np.zeros((len(st), len(names)))
        onehot[:, ci] = 1
        base_parts.append(np.concatenate([
            r['pol'][days].reshape(len(st), -1),
            NS['c5_window_channels'](load_causal(c, info), st, SEQ).reshape(len(st), -1),
            onehot], axis=1))
        split = np.array(['train'] * n_tr + ['val'] * (n_trv - n_tr) + ['test'] * (n - n_trv))
        period = np.where(split != 'test', 'na', np.where(target < LOCKDOWN_START, 'pre', 'lock'))
        meta.append(pd.DataFrame({'city': c, 'split': split, 'origin': origin, 'target': target,
                                  'y': info['y'][st + SEQ], 'period': period}))
    base_cols = ([f'POL|{f}|{d}' for d in range(SEQ) for f in FEATURES]
                 + [f'DEC|{ch}|{d}' for d in range(SEQ) for ch in CHANNELS] + [f'CITY|{c}' for c in names])
    return pd.concat(meta, ignore_index=True), np.vstack(base_parts), base_cols, names


def weather_blocks(meta: pd.DataFrame, real: pd.DataFrame, pool: pd.DataFrame
                   ) -> tuple[dict[str, np.ndarray], dict[str, list[str]], dict]:
    """Every weather block from meta's city, origin and target and the two band banks. Nothing else is read."""
    keys = meta[['city', 'origin', 'target']]
    n = len(keys)
    out = {k: np.full((n, len(MCOLS)), np.nan) for k in block_names()}
    own = {k: np.empty(n, dtype='datetime64[ns]') for k in block_names()}
    read = {k: np.empty(n, dtype='datetime64[ns]') for k in block_names()}
    for c in keys['city'].unique():
        idx = np.flatnonzero((keys['city'] == c).to_numpy())
        b_real = real[real.City == c].set_index('Date')[MCOLS]
        b_pool = pool[pool.City == c].set_index('Date')[MCOLS]
        for arm, col in (('MET', 'origin'), ('MET_PP', 'target')):
            when = pd.DatetimeIndex(keys[col].to_numpy()[idx])
            pp = '_PP' if arm == 'MET_PP' else ''
            todo = [(arm, b_real, when)]
            todo += [(f'POOL{pp}_{j}', b_pool, pool_dates(when, j)) for j in range(N_POOL)]
            todo += [(f'E5NULL{pp}_{k}', b_real, swap_dates(when, k)) for k in range(1, N_E5 + 1)]
            for name, bank, dates in todo:
                out[name][idx] = bank.reindex(dates).to_numpy()
                own[name][idx], read[name][idx] = when.to_numpy(), dates.to_numpy()
    long_idx = [i for i, col in enumerate(MCOLS) if col.split('|')[1] in LONG_BANDS]
    out['MET_PP_LONG'] = out['MET_PP'][:, long_idx]
    cols = {k: [f'MET|{m}' for m in MCOLS] for k in out}
    cols['MET_PP_LONG'] = [f'MET|{MCOLS[i]}' for i in long_idx]
    lookups = {k: (pd.DatetimeIndex(own[k]), pd.DatetimeIndex(read[k])) for k in block_names()}
    return out, cols, lookups


def build(df: pd.DataFrame | None = None, real_met: pd.DataFrame | None = None,
          pool_met: pd.DataFrame | None = None) -> C2Data:
    """All C2 inputs. By default from the pinned files; the optional tables replace them in memory (tests only)."""
    checks = verify_inputs()                      # includes the AQI file at REPO / DATA_REL
    common.DATA = REPO / DATA_REL                 # same pinned file as common.py's absolute path, portable
    meta, base, base_cols, names = windows(load_df() if df is None else df)
    real = load_bank('era5_daily.csv') if real_met is None else bank_from(real_met)
    pool = load_bank('era5_daily_pool.csv') if pool_met is None else bank_from(pool_met)
    blocks, block_cols, lookups = weather_blocks(meta, real, pool)
    data = C2Data(meta, base, base_cols, blocks, block_cols, lookups, checks)
    run_checks(data, names)
    return data


def design(data: C2Data, arm: str) -> dict:
    """Train / validation / test arrays of one arm: BASE plus the arm's weather block. Rows keep meta order."""
    if arm not in arm_names():
        raise KeyError(arm)
    x = data.base if arm == 'BASE' else np.hstack([data.base, data.blocks[arm]])
    cols = data.base_cols + ([] if arm == 'BASE' else data.block_cols[arm])
    split, y = data.meta['split'].to_numpy(), data.meta['y'].to_numpy()
    d: dict = {'cols': cols}
    for s in SPLITS:
        m = split == s
        d[f'X_{s}'], d[f'y_{s}'], d[f'rows_{s}'] = x[m], y[m], np.flatnonzero(m)
    return d


def run_checks(data: C2Data, names: list[str]) -> None:
    """Pre-registration section 10, the checks that need no model. Any failure stops the build."""
    meta, ck = data.meta, data.checks
    counts = meta['split'].value_counts().to_dict()
    assert len(names) == N_CITIES, names
    assert counts == EXPECTED_WINDOWS, counts
    ck.append(f'windows: {N_CITIES} cities; train {counts["train"]}, val {counts["val"]}, test {counts["test"]} '
              '(as pre-registered); target = origin + 1 day for every window')
    assert data.base.shape == (len(meta), len(data.base_cols)) == (19250, 137), data.base.shape
    assert np.isfinite(data.base).all(), 'non-finite value in BASE'
    for k, x in data.blocks.items():
        assert x.shape == (len(meta), len(data.block_cols[k])), (k, x.shape)
        assert np.isfinite(x).all(), f'non-finite weather value in {k}'
    ck.append(f'finite: BASE and all {len(data.blocks)} weather blocks')
    for k, (own, read) in data.lookups.items():
        feb29 = (own.month == 2) & (own.day == 29)
        same_md = (read.month == own.month) & ((read.day == own.day) | (feb29 & (read.day == 28)))
        assert same_md.all(), f'{k}: lookup not on the same calendar day'
        if k.startswith('POOL'):
            assert ((read.year >= POOL_FIRST) & (read.year < POOL_FIRST + N_POOL)).all(), f'{k}: outside 2005-2014'
            pairs = pd.DataFrame({'own': own.year, 'pool': read.year}).drop_duplicates()
            assert pairs['own'].is_unique and pairs['pool'].is_unique, f'{k}: own years share a pool year'
        elif k.startswith('E5NULL'):
            assert (read.year != own.year).all(), f'{k}: E5 null used the own year'
        else:
            assert (read == own).all(), f'{k}: real weather not read on its own date'
    ck.append('lookups: real weather on its own date; pool nulls in 2005-2014 on the same calendar day, one pool '
              'year per own year in every set; E5 nulls never the own year')


def climate_check(real: pd.DataFrame, pool: pd.DataFrame) -> pd.DataFrame:
    """Secondary output (pre-registration section 8): bank means, pool years against real years, per city."""
    r = real[(real.Date >= '2015-04-01') & (real.Date <= '2020-07-01')]
    p = pool[(pool.Date >= '2005-01-01') & (pool.Date <= '2014-12-31')]
    rm, pm, rs = r.groupby('City')[MCOLS].mean(), p.groupby('City')[MCOLS].mean(), r.groupby('City')[MCOLS].std()
    t = pd.concat({'real_mean': rm.stack(), 'pool_mean': pm.stack(), 'real_sd': rs.stack()}, axis=1)
    t.index.names = ['city', 'feature']
    t['diff_in_sd'] = (t['pool_mean'] - t['real_mean']) / t['real_sd']
    return t.reset_index()


def array_digest(x: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(x, dtype=np.float64).tobytes()).hexdigest()[:16]


def summary(data: C2Data) -> str:
    m = data.meta
    lines = ['C2-T2 feature build summary (no model fitted; y not summarised)', *data.checks, '',
             f'test periods: pre-lockdown {int((m.period == "pre").sum())}, lockdown/Unlock '
             f'{int((m.period == "lock").sum())}',
             f'BASE {data.base.shape} digest {array_digest(data.base)}',
             'meta digest (city, split, origin, target, period) ' + hashlib.sha256(          # LF: same on every OS
                 m[['city', 'split', 'origin', 'target', 'period']].to_csv(index=False, lineterminator='\n')
                 .encode()).hexdigest()[:16],
             '', 'weather blocks (shape, digest):']
    lines += [f'  {k:14s} {str(x.shape):12s} {array_digest(x)}' for k, x in data.blocks.items()]
    table = pd.DataFrame({j: [POOL_FIRST + (y - OWN_FIRST + j) % N_POOL for y in range(2015, 2021)]
                          for j in range(N_POOL)}, index=pd.Index(range(2015, 2021), name='own year'))
    lines += ['', 'pool year used by null set j (columns) for each own year (rows):', table.to_string()]
    cc = climate_check(load_bank('era5_daily.csv'), load_bank('era5_daily_pool.csv'))
    cc[['var', 'band']] = cc['feature'].str.split('|', expand=True)
    med = cc.groupby(['var', 'band'], sort=False)['diff_in_sd'].median().unstack('band')[list(BANDS)]
    lines += ['', 'climate check: median over cities of (pool mean - real mean) / real s.d.', med.round(3).to_string()]
    return '\n'.join(lines)


if __name__ == '__main__':
    data = build()
    txt = summary(data)
    print(txt)
    with open(OUT / 'c2_t2_features_summary.txt', 'w', encoding='utf-8', newline='\n') as f:   # LF on every OS
        f.write(txt + '\n')
