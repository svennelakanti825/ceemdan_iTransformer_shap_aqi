"""E4: weekly (day-of-week) cycle in AQI and NO2 per city: an anthropogenic activity signature.

Series: log of the observed daily value minus its centred 31-day mean (removes seasonal and sub-seasonal
variation; descriptive, no forecasting). Amplitude = max - min of the seven day-of-week means, in percent
(exp(diff) - 1). Null: the day-of-week labels are shifted by a random calendar offset of 1-6 days relative to
the series, and the record is cut into 8-week blocks with an independent offset per block, which keeps
autocorrelation and breaks the alignment with the real week. 2000 surrogates; p = share of surrogate
amplitudes >= observed. Benjamini-Hochberg over the 18 cities per variable.
Period: before 25 March 2020, so the lockdown does not set the result.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import OUT, load_df

RNG = np.random.default_rng(2)


def dow_amp(v: np.ndarray, dow: np.ndarray) -> tuple[float, np.ndarray]:
    means = np.array([np.nanmean(v[dow == d]) for d in range(7)])
    return float(np.exp(means.max() - means.min()) - 1) * 100, means


def bh(p: np.ndarray) -> np.ndarray:
    n = len(p)
    o = np.argsort(p)
    q = np.empty(n)
    q[o] = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    return np.minimum(q, 1)


def main() -> None:
    df = pd.read_csv(OUT.parent.parent.parent / 'data' / 'city_day.csv')
    df['Date'] = pd.to_datetime(df['Date'])
    df = df[df['Date'] < '2020-03-25']
    cities = sorted(f.stem.replace('fullrec_', '') for f in OUT.glob('fullrec_*.npz'))
    rows = []
    for c in cities:
        for var in ('AQI', 'NO2'):
            s = df[df.City == c].set_index('Date')[var]
            s = s[s > 0].dropna()
            if len(s) < 365:
                continue
            cal = pd.date_range(s.index.min(), s.index.max(), freq='D')
            x = np.log(s.reindex(cal))
            hp = (x - x.rolling(31, center=True, min_periods=19).mean()).to_numpy()
            dow = cal.dayofweek.to_numpy()
            amp, means = dow_amp(hp, dow)
            blocks = np.arange(len(cal)) // 56
            null = np.empty(2000)
            for i in range(2000):
                off = RNG.integers(1, 7, blocks.max() + 1)[blocks]
                null[i] = dow_amp(hp, (dow + off) % 7)[0]
            rows.append({'city': c, 'var': var, 'n_days': int(np.isfinite(hp).sum()), 'amp_pct': amp,
                         'null_p95': float(np.percentile(null, 95)), 'p': float((null >= amp).mean()),
                         'max_day': int(np.argmax(means)), 'min_day': int(np.argmin(means))})
    r = pd.DataFrame(rows)
    r['q'] = r.groupby('var')['p'].transform(lambda p: bh(p.to_numpy()))
    r.to_csv(OUT / 'e4_weekly_cycle.csv', index=False)
    days = 'Mon Tue Wed Thu Fri Sat Sun'.split()
    r['max_day'] = r['max_day'].map(lambda d: days[d])
    r['min_day'] = r['min_day'].map(lambda d: days[d])
    print(r.round(3).to_string(index=False))
    print(r.groupby('var').apply(lambda g: pd.Series({'n': len(g), 'sig_q05': int((g.q < 0.05).sum()),
                                                       'median_amp': g.amp_pct.median(),
                                                       'min_on_sun': int((g.min_day == 'Sun').sum())})).to_string())


if __name__ == '__main__':
    main()
