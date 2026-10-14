"""Shared loader for the editor-condition-1 verification experiments (8 Oct 2026).

Rebuilds the run-of-record calendar pipeline (D1, R1.9, N1, C5) by executing the exact helper cells in
../tools, so the windows, splits and causal decompositions are the ones the revised manuscript reports.
Nothing here trains the iTransformer; these are local, CPU-only checks.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REV1 = HERE.parent
TOOLS = REV1 / 'tools'
MODELS = REV1 / 'phase4_v2_results_r1' / 'models'
DATA = REV1.parent / 'data' / 'city_day.csv'
OUT = HERE / 'outputs'
OUT.mkdir(exist_ok=True)

FEATURES = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene']
TARGET = 'AQI'
CHANNELS = ['IMF1', 'IMF2', 'IMF3', 'IMF4', 'Slow']

# Execute the run-of-record helper cells in one namespace (they expect np, pd, logger, time).
NS: dict = {'np': np, 'pd': pd, 'logger': logging.getLogger('helpers'), 'time': time}
for cell in ['d1_helper_cell.py', 'r19_helper_cell.py', 'c5_helper_cell.py', 'n1_helper_cell.py']:
    exec(compile((TOOLS / cell).read_text(encoding='utf-8'), cell, 'exec'), NS)


def load_df(target: str = TARGET) -> pd.DataFrame:
    df = pd.read_csv(DATA)
    return df.dropna(subset=[target])


def city_calendars(df: pd.DataFrame, target: str = TARGET) -> dict:
    """Per modelled city: calendar frame, observed, available, target series and C5 seed."""
    all_cities = sorted(df['City'].unique())
    out = {}
    for city in all_cities:
        df_c = df[df['City'] == city].sort_values('Date').reset_index(drop=True)
        cal, observed, available = NS['d1_calendar_city'](df_c, FEATURES + [target])
        if all(NS['r19_city_windows'](cal['Date'], observed, available, L)[1][0] == 0 for L in (7, 14, 21, 30)):
            continue
        out[city] = dict(cal=cal, observed=observed, available=available,
                         y=cal[target].values.astype(np.float64), seed=123 + all_cities.index(city))
    return out


def load_causal(city: str, info: dict, cache: str = 'c5_decompositions_ext_ar') -> dict:
    """Saved causal decomposition, checked against the input fingerprint of this reconstruction."""
    d = np.load(MODELS / cache / f'c5_{city}.npz')
    meta = json.loads(str(d['meta']))
    fp = NS['c5_fingerprint'](info['cal']['Date'], info['y'], info['available'], info['seed'])
    if fp != meta['fingerprint']:
        raise ValueError(f'{city}: reconstruction does not match the saved decomposition input')
    return {k: d[k] for k in ('days', 'tail', 'n_components', 'periods', 'history_len')}


def build_lb7(cities: dict, seq_len: int = 7) -> dict:
    """Windows, splits and N1-filled pollutant arrays exactly as the run of record builds them."""
    raw = {}
    for c, info in cities.items():
        starts, splits = NS['r19_city_windows'](info['cal']['Date'], info['observed'], info['available'], seq_len)
        vals = info['cal'][FEATURES].values.astype(np.float64)
        pol = NS['n1_pollutant_calendar'](vals, info['observed'], info['available'])
        raw[c] = dict(n=len(info['y']), available=info['available'], starts=starts, splits=splits,
                      pol=pol, n1_readings=NS['n1_readings'](vals, info['observed']))
    NS['n1_fill_constant'](raw, 'pol', {c: raw[c]['splits'] for c in raw}, seq_len)
    return raw
