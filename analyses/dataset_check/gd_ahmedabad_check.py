"""Ahmedabad data-quality check (13 Oct 2026): how much does Ahmedabad's copied CO column move the other cities' results?

Found through G1: in the Kaggle city_day.csv, Ahmedabad's CO equals its NO on every day with both values up to
9 Apr 2020, and its AQI follows that column.

Model: the XGBoost design of C2's BASE arm (pollutant windows, causal CEEMDAN channels and a city one-hot at lookback 7,
E1 PARAMS, early stopping on validation), built with the frozen C2 window code, unchanged. Five arms, each with the
same 10 seeds:
- ALL: all 18 cities, as C2's BASE;
- NO_AHM: Ahmedabad's training and validation windows removed (its AQI target and its CO input both leave training);
- CO_MASK: all cities, with Ahmedabad's CO input set to missing on every window day up to 9 Apr 2020 (the target stays);
- TRAIN17: Ahmedabad's training windows removed, its validation windows kept (early stopping as ALL);
- VAL17: all training windows kept, Ahmedabad's validation windows removed (early stopping on the other 17 cities).
TRAIN17 and VAL17 were added after the first three arms showed that NO_AHM stops at about three times as many trees,
to separate the training data from the early-stopping set (13 Oct 2026). All five arms are rerun together.
Scored on the test windows of the other 17 cities, pooled (all, pre-lockdown, lockdown/Unlock) and per city.

Usage: python gd_ahmedabad_check.py        (Windows laptop, CPU, n_jobs 8; about 5 min)
"""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy import stats

HERE = Path(__file__).resolve().parent
E1V = HERE.parent / 'e1_verification'
sys.path.insert(0, str(E1V))
import common  # noqa: E402
import c2x_features as cx  # noqa: E402
from e1_leakage_contrast import PARAMS  # noqa: E402

OUT = HERE / 'outputs' / 'gd_ahmedabad_check'
OUT.mkdir(parents=True, exist_ok=True)
CITY = 'Ahmedabad'
LAST_COPIED_DAY = pd.Timestamp('2020-04-09')     # last day on which CO equals NO
SEEDS = tuple(range(10))
N_JOBS = 8
ARMS = ('ALL', 'NO_AHM', 'CO_MASK', 'TRAIN17', 'VAL17')
PERIODS = ('all', 'pre', 'lock')


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    e = y.astype(np.float64) - p.astype(np.float64)
    return {'mae': float(np.mean(np.abs(e))), 'rmse': float(np.sqrt(np.mean(e ** 2))),
            'r2': float(1.0 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2)), 'mean_error': float(np.mean(-e))}


def main() -> int:
    t0 = time.time()
    common.DATA = cx.REPO / cx.DATA_REL
    df = common.load_df()
    meta, base, cols, names = cx.windows(df)
    counts = meta.split.value_counts().to_dict()
    assert counts == cx.EXPECTED_WINDOWS, counts
    split, y, city = meta.split.to_numpy(), meta.y.to_numpy(), meta.city.to_numpy()
    ahm = city == CITY

    # CO_MASK input: Ahmedabad's CO set to missing on window days up to the last copied day
    masked = base.copy()
    origin = pd.DatetimeIndex(meta.origin)
    n_masked = 0
    for d in range(cx.SEQ):
        col = cols.index(f'POL|CO|{d}')
        day = origin - pd.Timedelta(days=cx.SEQ - 1 - d)
        m = ahm & np.asarray(day <= LAST_COPIED_DAY)
        masked[m, col] = np.nan
        n_masked += int(m.sum())

    # the copy itself, checked on the raw file
    a = df[df.City == CITY].dropna(subset=['CO', 'NO'])
    a_dates = pd.to_datetime(a.Date)
    assert (a[a_dates <= LAST_COPIED_DAY].CO == a[a_dates <= LAST_COPIED_DAY].NO).all()

    test_other = (split == 'test') & ~ahm
    test_ahm = (split == 'test') & ahm
    period = meta.period.to_numpy()
    rows, city_rows, preds = [], [], {}
    for arm in ARMS:
        X = masked if arm == 'CO_MASK' else base
        keep_tr = ~ahm if arm in ('NO_AHM', 'TRAIN17') else np.ones(len(y), bool)
        keep_va = ~ahm if arm in ('NO_AHM', 'VAL17') else np.ones(len(y), bool)
        tr, va = (split == 'train') & keep_tr, (split == 'val') & keep_va
        for seed in SEEDS:
            t = time.time()
            model = xgb.XGBRegressor(random_state=seed, n_jobs=N_JOBS, **PARAMS)
            model.fit(X[tr], y[tr], eval_set=[(X[va], y[va])], verbose=False)
            p = model.predict(X[split == 'test']).astype(np.float64)
            full = np.full(len(y), np.nan)
            full[split == 'test'] = p
            preds[f'{arm}__{seed}'] = full[split == 'test']
            for per in PERIODS:
                m = test_other & (np.ones(len(y), bool) if per == 'all' else period == per)
                rows.append({'arm': arm, 'seed': seed, 'scope': 'other_17', 'period': per, 'n': int(m.sum()),
                             'best_iter': int(model.best_iteration), **metrics(y[m], full[m])})
            if True:
                rows.append({'arm': arm, 'seed': seed, 'scope': CITY, 'period': 'all', 'n': int(test_ahm.sum()),
                             'best_iter': int(model.best_iteration), **metrics(y[test_ahm], full[test_ahm])})
            for c in names:
                if c == CITY:
                    continue
                m = test_other & (city == c)
                city_rows.append({'arm': arm, 'seed': seed, 'city': c, 'n': int(m.sum()), **metrics(y[m], full[m])})
            print(f'{arm} seed {seed}: best {model.best_iteration}, other-17 MAE {rows[-4]["mae"]:.3f}'
                  f' ({time.time() - t:.0f} s)', flush=True)

    res, cres = pd.DataFrame(rows), pd.DataFrame(city_rows)
    res.to_csv(OUT / 'gd_pooled.csv', index=False)
    cres.to_csv(OUT / 'gd_city.csv', index=False)
    np.savez_compressed(OUT / 'gd_test_predictions.npz', y_test=y[split == 'test'], city_test=city[split == 'test'],
                        **preds)

    lines = [f'G-D check, {time.strftime("%Y-%m-%d %H:%M")} local, {platform.platform()}, {platform.processor()}',
             f'xgboost {xgb.__version__}, numpy {np.__version__}, pandas {pd.__version__}, n_jobs {N_JOBS}, seeds {SEEDS}',
             f'windows {counts}; Ahmedabad windows train {int((ahm & (split == "train")).sum())}, '
             f'val {int((ahm & (split == "val")).sum())}, test {int(test_ahm.sum())}; CO_MASK cells set missing {n_masked}',
             f'other 17 cities: test windows {int(test_other.sum())}', '']
    for per in PERIODS:
        lines.append(f'Other 17 cities, period {per}: mean +/- s.d. over {len(SEEDS)} seeds')
        sub = res[(res.scope == 'other_17') & (res.period == per)]
        for arm in ARMS:
            g = sub[sub.arm == arm]
            lines.append(f'  {arm:8s} MAE {g.mae.mean():.3f} +/- {g.mae.std(ddof=1):.3f} | RMSE {g.rmse.mean():.3f} '
                         f'+/- {g.rmse.std(ddof=1):.3f} | R2 {g.r2.mean():.4f} +/- {g.r2.std(ddof=1):.4f} | '
                         f'mean error {g.mean_error.mean():+.3f}')
        a0 = sub[sub.arm == 'ALL'].set_index('seed')
        for arm in ARMS[1:]:
            b = sub[sub.arm == arm].set_index('seed')
            for q in ('mae', 'r2'):
                d = b[q] - a0[q]
                w = stats.ttest_ind(b[q], a0[q], equal_var=False)
                lines.append(f'  {arm} - ALL, {q}: {d.mean():+.4f} (seed-paired s.d. {d.std(ddof=1):.4f}); '
                             f'{100 * d.mean() / a0[q].mean():+.2f}% ; Welch p {w.pvalue:.3f}')
        lines.append('')
    bi = res[(res.scope == 'other_17') & (res.period == 'all')].groupby('arm').best_iter.agg(['mean', 'min', 'max'])
    lines.append('Best iteration (early stopping) by arm: ' + '; '.join(
        f'{a} mean {bi.loc[a, "mean"]:.0f} ({bi.loc[a, "min"]:.0f}-{bi.loc[a, "max"]:.0f})' for a in ARMS))
    lines.append('')
    lines.append(f'{CITY} itself (test): mean over seeds')
    for arm in ARMS:
        g = res[(res.scope == CITY) & (res.arm == arm)]
        lines.append(f'  {arm:8s} MAE {g.mae.mean():.3f} +/- {g.mae.std(ddof=1):.3f} | R2 {g.r2.mean():.4f}')
    lines.append('')
    lines.append('Per city (other 17), test MAE, mean over seeds: ALL, then each arm - ALL (' + ', '.join(ARMS[1:]) + '), and the ALL seed s.d.')
    piv = cres.groupby(['city', 'arm']).mae.agg(['mean', 'std']).unstack('arm')
    for c in piv.index:
        diffs = ' '.join(f'{piv.loc[c, ("mean", a)] - piv.loc[c, ("mean", "ALL")]:+8.3f}' for a in ARMS[1:])
        lines.append(f'  {c:18s} {piv.loc[c, ("mean", "ALL")]:8.3f} {diffs}   s.d. {piv.loc[c, ("std", "ALL")]:.3f}')
    for a in ARMS[1:]:
        lower = int((piv[('mean', a)] < piv[('mean', 'ALL')]).sum())
        lines.append(f'  {a} has a lower mean MAE than ALL in {lower} of {len(piv)} cities')
    big = piv.index[(piv[('mean', 'NO_AHM')] - piv[('mean', 'ALL')]).abs() > 2 * piv[('std', 'ALL')]].tolist()
    lines.append(f'  cities where |NO_AHM - ALL| exceeds 2 seed s.d. of ALL: {big}')
    lines.append(f'\nelapsed {time.time() - t0:.0f} s')
    (OUT / 'gd_summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (OUT / 'gd_params.json').write_text(json.dumps({'PARAMS': PARAMS, 'seeds': SEEDS, 'n_jobs': N_JOBS,
                                                    'last_copied_day': str(LAST_COPIED_DAY.date())}, indent=1),
                                        encoding='utf-8')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
