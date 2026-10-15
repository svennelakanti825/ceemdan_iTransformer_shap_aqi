"""E2: timescale-resolved AQI variability and its meteorological coupling, per city (descriptive, no forecasting).

Bands on the daily calendar of observed AQI (log scale), from centred moving averages (MA) that need at least
60% of their window observed:
  B1 <7 d  : x - MA7        B2 7-31 d : MA7 - MA31     B3 31-91 d : MA31 - MA91     B4 >91 d : MA91 - mean
Centred filters use later days. That is acceptable here because nothing is forecast; this is a retrospective
description of the record, not a model input.
Meteorological coupling: per city and band, OLS of the AQI band on the same band of five ERA5 variables
(log ventilation coefficient, precipitation^0.5, temperature, relative humidity, wind speed); R^2 with a
95% interval from a moving-block bootstrap (block 60 days, 500 resamples).
Fixed period bands replace IMF indices, so cities are compared on the same timescales (R1.2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT, load_df

BANDS = ['B1 <7d', 'B2 7-31d', 'B3 31-91d', 'B4 >91d']
MET = ['lvent', 'sprecip', 't2m', 'rh', 'wind']
RNG = np.random.default_rng(0)


def ma(s: pd.Series, w: int) -> pd.Series:
    return s.rolling(w, center=True, min_periods=int(np.ceil(0.6 * w))).mean()


def bands(s: pd.Series) -> pd.DataFrame:
    m7, m31, m91 = ma(s, 7), ma(s, 31), ma(s, 91)
    return pd.DataFrame({BANDS[0]: s - m7, BANDS[1]: m7 - m31, BANDS[2]: m31 - m91, BANDS[3]: m91 - s.mean()})


def ols_r2(y: np.ndarray, X: np.ndarray) -> float:
    X1 = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    res = y - X1 @ beta
    return float(1 - res @ res / ((y - y.mean()) @ (y - y.mean())))


def block_boot_r2(y: np.ndarray, X: np.ndarray, block: int = 60, n_boot: int = 500) -> tuple[float, float]:
    n = len(y)
    nb = int(np.ceil(n / block))
    out = []
    for _ in range(n_boot):
        st = RNG.integers(0, max(n - block, 1), nb)
        idx = np.concatenate([np.arange(s, min(s + block, n)) for s in st])[:n]
        out.append(ols_r2(y[idx], X[idx]))
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main() -> None:
    df = load_df()
    df['Date'] = pd.to_datetime(df['Date'])
    met = pd.read_csv(OUT / 'era5_daily.csv', parse_dates=['Date'])
    met['lvent'] = np.log(met['vent'])
    met['sprecip'] = np.sqrt(met['precip'])
    modelled = sorted(f.stem.replace('fullrec_', '') for f in OUT.glob('fullrec_*.npz'))   # the 18 modelled cities
    assert len(modelled) == 18
    var_rows, r2_rows = [], []
    for c in modelled:
        a = df[df.City == c].set_index('Date')['AQI']
        cal = pd.date_range(a.index.min(), a.index.max(), freq='D')
        x = np.log(a.reindex(cal))
        b = bands(x)
        m = met[met.City == c].set_index('Date').reindex(cal)
        mb = {v: bands(m[v]) for v in MET}
        tot = sum(b[k].var() for k in BANDS)
        var_rows.append({'city': c, 'n_obs': int(a.notna().sum()),
                         **{k: 100 * b[k].var() / tot for k in BANDS}})
        for k in BANDS:
            X = np.column_stack([mb[v][k] for v in MET])
            y = b[k].to_numpy()
            ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
            lo, hi = block_boot_r2(y[ok], X[ok])
            r2_rows.append({'city': c, 'band': k, 'n': int(ok.sum()), 'r2': ols_r2(y[ok], X[ok]), 'lo': lo, 'hi': hi,
                            # single-variable correlations, signs show the physical direction
                            **{f'corr_{v}': float(np.corrcoef(y[ok], mb[v][k].to_numpy()[ok])[0, 1]) for v in MET}})
    v = pd.DataFrame(var_rows)
    r = pd.DataFrame(r2_rows)
    v.to_csv(OUT / 'e2_band_variance.csv', index=False)
    r.to_csv(OUT / 'e2_band_met_r2.csv', index=False)
    print(v.round(1).to_string(index=False))
    print(r.pivot(index='city', columns='band', values='r2').round(2).to_string())
    print('median R2 by band:', r.groupby('band')['r2'].median().round(2).to_dict())
    print('median corr lvent by band:', r.groupby('band')['corr_lvent'].median().round(2).to_dict())


if __name__ == '__main__':
    main()
