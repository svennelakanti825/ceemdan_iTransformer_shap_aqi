"""Ahmedabad CO and NO columns in city_day.csv, and the significance of the XGBoost proxy check.

1. Days on which Ahmedabad's CO equals its NO (both present), their date range, and a check that every such day
   precedes the first day on which they differ. Also the same count for all other cities, and a scan of every
   city and pair of pollutant columns for other identical pairs.
2. Welch t-test of the other 17 cities' test MAE, NO_AHM against ALL over the ten seeds of gd_ahmedabad_check.py
   (outputs/gd_ahmedabad_check/gd_pooled.csv).

Usage: python ahmedabad_co_no.py
Output: outputs/ahmedabad_co_no.txt
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / 'data' / 'city_day.csv'
POOLED = HERE / 'outputs' / 'gd_ahmedabad_check' / 'gd_pooled.csv'
OUT = HERE / 'outputs' / 'ahmedabad_co_no.txt'
POL = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene']


def main() -> None:
    d = pd.read_csv(DATA, parse_dates=['Date'])
    a = d[d.City == 'Ahmedabad'].dropna(subset=['CO', 'NO'])
    eq, ne = a[a.CO == a.NO], a[a.CO != a.NO]
    assert eq.Date.max() < ne.Date.min(), 'CO equals NO on a day after they first differ'
    o = d[d.City != 'Ahmedabad'].dropna(subset=['CO', 'NO'])
    lines = [f'Ahmedabad, days with CO and NO both present: {len(a)}',
             f'  CO == NO on {len(eq)} days, {eq.Date.min():%d %b %Y} to {eq.Date.max():%d %b %Y}; '
             f'they differ on every day from {ne.Date.min():%d %b %Y} ({len(ne)} days)',
             f'Other cities, days with CO == NO: {int((o.CO == o.NO).sum())} of {len(o)}']
    pairs = []
    for city, g in d.groupby('City'):
        for i, x in enumerate(POL):
            for y in POL[i + 1:]:
                z = g[[x, y]].dropna()
                z = z[(z[x] != 0) | (z[y] != 0)]
                if len(z) >= 30 and (z[x] == z[y]).mean() > 0.5:
                    pairs.append(f'{city} {x}={y} on {100 * (z[x] == z[y]).mean():.1f}% of {len(z)} days')
    lines.append('City and column pairs equal on more than half of the days with both present (at least 30): '
                 + ('; '.join(pairs) if pairs else 'none'))

    p = pd.read_csv(POOLED)
    p = p[(p.scope == 'other_17') & (p.period == 'all')]
    base, out = p[p.arm == 'ALL'].mae, p[p.arm == 'NO_AHM'].mae
    t = stats.ttest_ind(out, base, equal_var=False)
    lines.append(f'Proxy check, other 17 cities, all test windows, {len(base)} seeds per arm: MAE {base.mean():.3f} '
                 f'(ALL) against {out.mean():.3f} (NO_AHM), change {100 * (out.mean() / base.mean() - 1):+.2f}%, '
                 f'Welch t {t.statistic:.3f}, p {t.pvalue:.2e}')
    OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
