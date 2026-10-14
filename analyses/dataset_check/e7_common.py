"""E7 shared loaders: CPCB bulletin AQI on the run-of-record D1 calendar (rules in E7_DECISION_RULES.md)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'e1_verification'))
from common import NS  # noqa: E402  (executes the run-of-record helper cells)

BULLETIN = HERE / 'data_bulletins' / 'AllIndiaBulletinsMaster2025_openrefined.csv'
KAGGLE = HERE.parents[1] / 'data' / 'city_day.csv'
OUT = HERE / 'outputs'
OUT.mkdir(exist_ok=True)
DECOMP = OUT / 'decomp'
DECOMP.mkdir(exist_ok=True)

D2_CITIES = sorted(['Amaravati', 'Amritsar', 'Bengaluru', 'Chennai', 'Delhi', 'Gurugram', 'Hyderabad', 'Jaipur',
                    'Kolkata', 'Lucknow', 'Mumbai', 'Patna', 'Thiruvananthapuram', 'Visakhapatnam'])
SEQ, HORIZONS, ORIGIN_STEP = 7, (1, 7), 5
EXTENSION = 'ar'


def load_bulletin() -> pd.DataFrame:
    b = pd.read_csv(BULLETIN, parse_dates=['date'])
    b = b.rename(columns={'date': 'Date', 'city': 'City', 'aqi': 'AQI'})
    b['AQI'] = pd.to_numeric(b['AQI'], errors='coerce')
    b = b.dropna(subset=['AQI'])
    assert not b.duplicated(['City', 'Date']).any()
    return b[['City', 'Date', 'AQI']]


def city_calendar(b: pd.DataFrame, city: str) -> dict:
    df_c = b[b.City == city].sort_values('Date').reset_index(drop=True)
    cal, observed, available = NS['d1_calendar_city'](df_c, ['AQI'])
    return dict(cal=cal, observed=observed, available=available, y=cal['AQI'].to_numpy(np.float64),
                dates=pd.to_datetime(cal['Date']).to_numpy(), seed=123 + D2_CITIES.index(city))


def origins(info: dict) -> np.ndarray:
    """Last input days of usable L=7 windows: inputs available, >=180 available days, index % 5 == 0,
    and an observed target at origin+1 or origin+7."""
    av, ob = np.asarray(info['available'], bool), np.asarray(info['observed'], bool)
    n = len(av)
    csum = np.concatenate([[0], np.cumsum(av)])
    o = np.arange(SEQ - 1, n)
    ok = (csum[o + 1] - csum[o + 1 - SEQ] == SEQ) & (csum[o + 1] >= NS['C5_MIN_HISTORY']) & (o % ORIGIN_STEP == 0)
    tgt_ok = np.zeros(len(o), bool)
    for h in HORIZONS:
        t = o + h
        tgt_ok |= (t < n) & ob[np.minimum(t, n - 1)]
    return o[ok & tgt_ok]
