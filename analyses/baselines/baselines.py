"""Persistence and seasonal-climatology baselines on the run-of-record test windows (13 Oct 2026).

The design is fixed in BASELINES_DESIGN.md (written before this script first ran). This script:
1. rebuilds the 6,171 test windows with the frozen helper cells (../e1_verification/common.py, unchanged) and checks
   them against the stored main-model predictions;
2. computes persistence (P) and seasonal climatology (C) forecasts;
3. scores P, C and the main model's 5 seeds on all test windows, before and after 25 Mar 2020, and per city.

Outputs (outputs/): baselines_pooled.csv, baselines_city.csv, baselines_skill.csv, baselines_test_predictions.npz,
baselines_summary.txt. CPU only, seconds.

Usage: python baselines.py
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REV1 = HERE.parent
sys.path.insert(0, str(REV1 / 'e1_verification'))
import common as cm  # noqa: E402  (frozen run-of-record helpers)

OUT = HERE / 'outputs'
DESIGN = HERE / 'BASELINES_DESIGN.md'
PRED = REV1.parent / 'results' / '02_r1_ext' / 'reports' / 'r116_test_predictions_lb7.npz'
SEQ = 7
SEEDS = (123, 42, 2024, 7, 2025)
LOCKDOWN = np.datetime64('2020-03-25')
TRAIN_END = pd.Timestamp('2019-04-01')
HALF_WIDTH = 15          # days either side of the target's day of year (design)
MIN_DAYS = 10            # minimum training days in the window, else the city's training mean (design)


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def doy365(dates: pd.DatetimeIndex) -> np.ndarray:
    """Day of year on a 365-day year, 29 Feb mapped to 28 Feb (1..365)."""
    d = pd.DatetimeIndex(dates)
    md = np.where((d.month == 2) & (d.day == 29), 28, d.day)
    return pd.to_datetime(pd.DataFrame({'year': 2019, 'month': d.month, 'day': md})).dt.dayofyear.to_numpy()


def climatology(info: dict, targets: pd.DatetimeIndex) -> tuple[np.ndarray, int]:
    """Mean observed training-period AQI within ±HALF_WIDTH days of each target's day of year."""
    dates = pd.DatetimeIndex(info['cal']['Date'])
    keep = info['observed'] & (dates < TRAIN_END)
    y_tr, d_tr = info['y'][keep], doy365(dates[keep])
    fallback = float(y_tr.mean())
    out, n_fallback = np.empty(len(targets)), 0
    for i, dt in enumerate(doy365(targets)):
        dist = np.abs(d_tr - dt)
        dist = np.minimum(dist, 365 - dist)
        sel = dist <= HALF_WIDTH
        if sel.sum() >= MIN_DAYS:
            out[i] = y_tr[sel].mean()
        else:
            out[i], n_fallback = fallback, n_fallback + 1
    return out, n_fallback


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    e = p - y
    return {'r2': 1 - float((e ** 2).sum() / ((y - y.mean()) ** 2).sum()), 'rmse': float(np.sqrt((e ** 2).mean())),
            'mae': float(np.abs(e).mean()), 'mape': float((np.abs(e) / y).mean() * 100), 'n': int(len(y))}


def main() -> None:
    OUT.mkdir(exist_ok=True)
    design_sha = sha256_text(DESIGN)

    # 1. Windows, rebuilt with the frozen helpers, and checked against the stored predictions.
    df = cm.load_df()
    cities = cm.city_calendars(df)
    rows = []
    for c, info in cities.items():
        starts, splits = cm.NS['r19_city_windows'](info['cal']['Date'], info['observed'], info['available'], SEQ)
        n_trv = splits[1]
        st = starts[n_trv:]                                     # test windows
        cal_dates = pd.DatetimeIndex(info['cal']['Date'])
        origin, target = cal_dates[st + SEQ - 1], cal_dates[st + SEQ]
        assert ((target - origin) == pd.Timedelta('1D')).all()
        assert info['observed'][st + SEQ].all() and info['available'][st + SEQ - 1].all()
        clim, n_fb = climatology(info, target)
        rows.append(pd.DataFrame({'city': c, 'target': target.to_numpy().astype('datetime64[D]'),
                                  'y': info['y'][st + SEQ], 'persistence': info['y'][st + SEQ - 1],
                                  'origin_filled': ~info['observed'][st + SEQ - 1], 'climatology': clim,
                                  'clim_fallback_city': n_fb}))
    w = pd.concat(rows, ignore_index=True)

    s = np.load(PRED)
    names = [str(x) for x in s['valid_cities']]
    stored = pd.DataFrame({'city': [names[i] for i in s['city_test']], 'target': s['test_dates'], 'y': s['y_test']})
    assert list(cities) == names, 'city order differs from the stored predictions'
    assert len(w) == len(stored) == 6171, (len(w), len(stored))
    same_keys = (w['city'].to_numpy() == stored['city'].to_numpy()).all() and \
        (w['target'].to_numpy() == stored['target'].to_numpy()).all()
    y_gap = float(np.abs(w['y'].to_numpy() - stored['y'].to_numpy()).max())
    assert same_keys and y_gap < 1e-3, ('windows differ from the stored predictions', same_keys, y_gap)

    y = stored['y'].to_numpy()
    fc = {'Persistence': w['persistence'].to_numpy(), 'Climatology': w['climatology'].to_numpy()}
    for sd in SEEDS:
        fc[f'Main model seed {sd}'] = s[f'pred__bias__{sd}']
    pre = s['test_dates'] < LOCKDOWN
    subsets = {'all': np.ones(len(y), bool), 'pre-lockdown': pre, 'lockdown/Unlock': ~pre}

    # 2. Pooled and period metrics.
    pooled = pd.DataFrame([{'forecast': k, 'subset': sub, **metrics(y[m], p[m])}
                           for k, p in fc.items() for sub, m in subsets.items()])
    pooled.to_csv(OUT / 'baselines_pooled.csv', index=False)

    # 3. Skill of the main model against each baseline, per seed.
    sk = []
    for base in ('Persistence', 'Climatology'):
        for sub, m in subsets.items():
            mb = metrics(y[m], fc[base][m])['mae']
            for sd in SEEDS:
                mm = metrics(y[m], fc[f'Main model seed {sd}'][m])['mae']
                sk.append({'baseline': base, 'subset': sub, 'seed': sd, 'mae_model': mm, 'mae_baseline': mb,
                           'skill': 1 - mm / mb})
    pd.DataFrame(sk).to_csv(OUT / 'baselines_skill.csv', index=False)

    # 4. Per city.
    model_mean = np.mean([fc[f'Main model seed {sd}'] for sd in SEEDS], axis=0)
    cr = []
    for ci, c in enumerate(names):
        m = stored['city'].to_numpy() == c
        r = {'city': c, 'n': int(m.sum()), 'origin_filled': int(w.loc[m, 'origin_filled'].sum()),
             'clim_fallback': int(w.loc[m, 'clim_fallback_city'].iloc[0])}
        for k, p in (('persistence', fc['Persistence']), ('climatology', fc['Climatology'])):
            mt = metrics(y[m], p[m])
            r[f'{k}_mae'], r[f'{k}_r2'] = mt['mae'], mt['r2']
        seed_mae = [metrics(y[m], fc[f'Main model seed {sd}'][m])['mae'] for sd in SEEDS]
        seed_r2 = [metrics(y[m], fc[f'Main model seed {sd}'][m])['r2'] for sd in SEEDS]
        r['model_mae_mean'], r['model_mae_sd'] = float(np.mean(seed_mae)), float(np.std(seed_mae, ddof=1))
        r['model_r2_mean'] = float(np.mean(seed_r2))
        r['model_mean_forecast_mae'] = metrics(y[m], model_mean[m])['mae']
        cr.append(r)
    city = pd.DataFrame(cr)
    city.to_csv(OUT / 'baselines_city.csv', index=False)

    np.savez(OUT / 'baselines_test_predictions.npz', y_test=y, city_test=s['city_test'], test_dates=s['test_dates'],
             valid_cities=s['valid_cities'], persistence=fc['Persistence'], climatology=fc['Climatology'],
             origin_filled=w['origin_filled'].to_numpy())

    # 5. Summary.
    def ms(df_: pd.DataFrame, col: str) -> str:
        v = df_[col].to_numpy()
        return f'{v.mean():.4f} ± {v.std(ddof=1):.4f}'
    lines = [f'design SHA-256 {design_sha}',
             f'windows: {len(w)} test windows rebuilt and identical to the stored predictions (max |y| gap {y_gap:.2e})',
             f'origin days filled from the past: {int(w["origin_filled"].sum())}; climatology fallbacks to the city '
             f'mean: {int(city["clim_fallback"].sum())}']
    for sub in subsets:
        p_ = pooled[pooled.subset == sub]
        mm = p_[p_.forecast.str.startswith('Main')]
        lines.append(f'[{sub}] n={int(p_.n.iloc[0])}')
        for base in ('Persistence', 'Climatology'):
            b = p_[p_.forecast == base].iloc[0]
            lines.append(f'  {base:12s} R2 {b.r2:.4f}  RMSE {b.rmse:.3f}  MAE {b.mae:.3f}  MAPE {b.mape:.3f}')
        lines.append(f'  Main model   R2 {ms(mm, "r2")}  RMSE {ms(mm, "rmse")}  MAE {ms(mm, "mae")}  MAPE {ms(mm, "mape")}')
        skd = pd.DataFrame(sk)
        for base in ('Persistence', 'Climatology'):
            v = skd[(skd.baseline == base) & (skd.subset == sub)].skill.to_numpy()
            lines.append(f'  MAE skill against {base}: {v.mean():.4f} ± {v.std(ddof=1):.4f} (seeds {v.min():.4f} to '
                         f'{v.max():.4f})')
    lines.append(f'cities where the main model (seed-mean MAE) beats persistence: '
                 f'{int((city.model_mae_mean < city.persistence_mae).sum())} of {len(city)}; climatology: '
                 f'{int((city.model_mae_mean < city.climatology_mae).sum())} of {len(city)}')
    txt = '\n'.join(lines)
    (OUT / 'baselines_summary.txt').write_text(txt + '\n', encoding='utf-8')
    print(txt)


if __name__ == '__main__':
    main()
