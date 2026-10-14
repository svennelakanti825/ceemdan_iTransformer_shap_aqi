"""E7 D0 (bulletin vs Kaggle AQI) and D1 (stability of city timescale signatures over 10 years), see E7_DECISION_RULES.md."""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

from e7_common import HERE, KAGGLE, OUT, load_bulletin

sys.path.insert(0, str(HERE.parent / 'e1_verification'))
from e2_band_met import BANDS, bands  # noqa: E402  (same centred-MA bands as E2)

YEARS = list(range(2016, 2026))
COVER = 0.8


def d0(b: pd.DataFrame) -> pd.DataFrame:
    k = pd.read_csv(KAGGLE, parse_dates=['Date']).dropna(subset=['AQI'])
    rows = []
    for c in sorted(k.City.unique()):
        m = k[k.City == c][['Date', 'AQI']].merge(b[b.City == c][['Date', 'AQI']], on='Date', suffixes=('_kaggle', '_bulletin'))
        if len(m) < 30:
            rows.append(dict(city=c, n=len(m)))
            continue
        rows.append(dict(city=c, n=len(m), r=pearsonr(m.AQI_kaggle, m.AQI_bulletin)[0],
                         median_diff=float(np.median(m.AQI_bulletin - m.AQI_kaggle)),
                         median_kaggle=float(m.AQI_kaggle.median())))
    out = pd.DataFrame(rows)
    out['flag_r_below_0.8'] = out['r'] < 0.8
    return out


def city_year_shares(b: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c, g in b.groupby('City'):
        s = g.set_index('Date')['AQI'].sort_index()
        cal = pd.date_range(s.index.min(), s.index.max(), freq='D')
        x = np.log(s.reindex(cal))
        bd = bands(x)
        for y in YEARS:
            days = pd.date_range(f'{y}-01-01', f'{y}-12-31', freq='D')
            cover = float(x.reindex(days).notna().mean())
            if cover < COVER:
                continue
            by = bd.reindex(days).dropna()
            v = by.var()
            rows.append(dict(city=c, year=y, cover=cover, n_days=len(by), **{k: 100 * v[k] / v.sum() for k in BANDS}))
    return pd.DataFrame(rows)


def icc1(df: pd.DataFrame, col: str) -> float:
    g = df.groupby('city')[col]
    n_i, means = g.size(), g.mean()
    N, k = n_i.sum(), len(n_i)
    grand = df[col].mean()
    msb = float((n_i * (means - grand) ** 2).sum() / (k - 1))
    msw = float(((df[col] - df['city'].map(means)) ** 2).sum() / (N - k))
    n0 = (N - (n_i ** 2).sum() / N) / (k - 1)
    return (msb - msw) / (msb + (n0 - 1) * msw)


def half_rho(cy: pd.DataFrame, col: str, a: list[int], b_: list[int], min_years: int) -> tuple[float, float, int]:
    ma = cy[cy.year.isin(a)].groupby('city')[col].agg(['mean', 'size'])
    mb = cy[cy.year.isin(b_)].groupby('city')[col].agg(['mean', 'size'])
    j = ma.join(mb, lsuffix='_a', rsuffix='_b', how='inner')
    j = j[(j.size_a >= min_years) & (j.size_b >= min_years)]
    r, p = spearmanr(j.mean_a, j.mean_b)
    return float(r), float(p), len(j)


def main() -> None:
    b = load_bulletin()
    d0_tab = d0(b)
    d0_tab.to_csv(OUT / 'e7_d0_comparability.csv', index=False)
    cy = city_year_shares(b)
    elig = cy.groupby('city').size()
    elig = elig[elig >= 8].index
    cy = cy[cy.city.isin(elig)].reset_index(drop=True)
    cy.to_csv(OUT / 'e7_d1_city_year_shares.csv', index=False)
    lines = [f'D0: Kaggle cities with overlap: {int(d0_tab.r.notna().sum())}, median r {d0_tab.r.median():.3f}, '
             f'min r {d0_tab.r.min():.3f} ({d0_tab.loc[d0_tab.r.idxmin(), "city"]}), flagged r<0.8: '
             f'{list(d0_tab.loc[d0_tab["flag_r_below_0.8"], "city"])}',
             f'D1: eligible cities {len(elig)}, city-years {len(cy)}']
    res = []
    for k in BANDS:
        icc = icc1(cy, k)
        r5, p5, n5 = half_rho(cy, k, list(range(2016, 2021)), list(range(2021, 2026)), 3)
        r2, p2, n2 = half_rho(cy, k, [2016, 2017], [2018, 2019], 2)
        adj = [half_rho(cy, k, [y], [y + 1], 1)[0] for y in YEARS[:-1]]
        sb = {f'SB_{m}y': m * icc / (1 + (m - 1) * icc) for m in (1, 2, 5, 10)}
        res.append(dict(band=k, mean_share=cy[k].mean(), icc1=icc, rho_5y_halves=r5, p_5y=p5, n_5y=n5,
                        rho_2y_kaggle_like=r2, p_2y=p2, n_2y=n2, rho_1y_adjacent_mean=float(np.mean(adj)), **sb))
    rt = pd.DataFrame(res)
    rt.to_csv(OUT / 'e7_d1_reliability.csv', index=False)
    lines.append(rt.round(3).to_string(index=False))
    ok = all((rt.set_index('band').loc[k, 'rho_5y_halves'] >= 0.7) and (rt.set_index('band').loc[k, 'p_5y'] < 0.05)
             for k in BANDS[:2])
    lines.append(f'D1 RULE (5-y halves rho >= 0.7, p < 0.05 for B1 and B2): {"PASS" if ok else "FAIL"}')
    p = cy.pivot(index='year', columns='city')
    for band, a, b_, label in ((BANDS[0], 'Gurugram', 'Delhi', '(i) Gurugram B1 > Delhi B1'),
                               (BANDS[1], 'Delhi', 'Gurugram', '(ii) Delhi B2 > Gurugram B2')):
        if a in elig and b_ in elig:
            both = p[band][[a, b_]].dropna()
            wins = int((both[a] > both[b_]).sum())
            lines.append(f'{label}: {wins}/{len(both)} years -> {"PASS" if wins >= 8 else "FAIL"}  '
                         + ', '.join(f'{y}:{both.loc[y, a]:.1f}/{both.loc[y, b_]:.1f}' for y in both.index))
        else:
            lines.append(f'{label}: not eligible ({a in elig}, {b_ in elig})')
    txt = '\n'.join(lines)
    print(txt)
    (OUT / 'e7_d0_d1_verdict.txt').write_text(txt + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
