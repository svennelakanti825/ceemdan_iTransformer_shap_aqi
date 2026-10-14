"""E5: weather x timescale drivers beyond climatology, on development folds only (rules fixed before the run).

Same LB7 windows, causal CEEMDAN cache, XGBoost settings and seeds as E1/E3. Only windows with target < 2019-04-01
are used. Forward-chaining folds F1/F2, early stopping on the last 10% of the fit period. Met = causal filter bank
(trailing means, bands sum to the daily value) at the origin day; null = same calendar day from another year.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from common import CHANNELS, FEATURES, NS, OUT, build_lb7, city_calendars, load_causal, load_df
from e1_leakage_contrast import PARAMS, SEEDS, SEQ

MV = ['lblh', 'wind', 'lvent', 't2m', 'rh', 'sprecip']
BANDS = ['syn', 'intra', 'subs', 'seas']           # <7 d, 7-31 d, 31-91 d, >91 d
TRAIN_END = np.datetime64('2019-04-01')
FOLDS = {'F1': (np.datetime64('2017-04-01'), np.datetime64('2018-04-01')),
         'F2': (np.datetime64('2018-04-01'), np.datetime64('2019-04-01'))}
N_NULL = 4
MIN_CITY_EVAL = 150
DATA_START, DATA_END = pd.Timestamp('2015-04-01'), pd.Timestamp('2020-07-01')   # full 91-d ERA5 history from here


def met_bank(met: pd.DataFrame) -> pd.DataFrame:
    """Per city and date: 6 variables x 4 causal bands. Trailing means over calendar days (ERA5 has no gaps)."""
    out = []
    for c, g in met.groupby('City'):
        g = g.sort_values('Date').set_index('Date')
        assert (g.index.to_series().diff().dropna() == pd.Timedelta('1D')).all()
        cols = {}
        for v in MV:
            s = g[v]
            m7, m31, m91 = (s.rolling(k, min_periods=k).mean() for k in (7, 31, 91))
            cols.update({f'{v}|syn': s - m7, f'{v}|intra': m7 - m31, f'{v}|subs': m31 - m91, f'{v}|seas': m91})
        b = pd.DataFrame(cols)
        assert np.allclose(sum(b[f'{MV[0]}|{k}'] for k in BANDS).dropna(), g[MV[0]].loc[b.dropna().index])
        b['City'] = c
        out.append(b.reset_index())
    return pd.concat(out, ignore_index=True)


def swap_dates(dates: pd.DatetimeIndex, k: int) -> pd.DatetimeIndex:
    """Same calendar day in another year; k cycles through the valid years of that day (Feb 29 -> Feb 28)."""
    res = []
    for d in dates:
        md = (d.month, 28 if (d.month == 2 and d.day == 29) else d.day)
        years = [y for y in range(2015, 2021) if DATA_START <= pd.Timestamp(y, *md) <= DATA_END]
        i = years.index(d.year)
        res.append(pd.Timestamp(years[(i + k) % len(years)], *md))
    return pd.DatetimeIndex(res)


def build() -> tuple[dict, pd.DataFrame, np.ndarray, list[str]]:
    df = load_df()
    cities = city_calendars(df)
    raw = build_lb7(cities, SEQ)
    met = pd.read_csv(OUT / 'era5_daily.csv', parse_dates=['Date'])
    met['lblh'], met['lvent'], met['sprecip'] = np.log(met['blh']), np.log(met['vent']), np.sqrt(met['precip'])
    bank = met_bank(met)
    mcols = [f'{v}|{b}' for v in MV for b in BANDS]
    names = list(cities)
    blocks = {k: [] for k in ['POL', 'DEC', 'CITY', 'MET', 'MET_PP'] + [f'NULL_{k}' for k in range(1, N_NULL + 1)]
              + [f'NULL_PP_{k}' for k in range(1, N_NULL + 1)]}
    meta = []
    for ci, c in enumerate(names):
        info, r = cities[c], raw[c]
        st = r['starts']
        cal_dates = pd.to_datetime(info['cal']['Date']).to_numpy()
        tgt = cal_dates[st + SEQ]
        keep = tgt < TRAIN_END                                   # development data only: test/val never loaded
        st = st[keep]
        days = st[:, None] + np.arange(SEQ)[None, :]
        b = bank[bank.City == c].set_index('Date')[mcols]
        origin = pd.DatetimeIndex(cal_dates[st + SEQ - 1])
        target = pd.DatetimeIndex(cal_dates[st + SEQ])
        blocks['POL'].append(r['pol'][days].reshape(len(st), -1))
        blocks['DEC'].append(NS['c5_window_channels'](load_causal(c, info), st, SEQ).reshape(len(st), -1))
        oh = np.zeros((len(st), len(names)))
        oh[:, ci] = 1
        blocks['CITY'].append(oh)
        for arm, when in (('MET', origin), ('MET_PP', target)):
            x = b.reindex(when).to_numpy()
            assert np.isfinite(x).all(), (c, arm)
            blocks[arm].append(x)
            for k in range(1, N_NULL + 1):
                xs = b.reindex(swap_dates(when, k)).to_numpy()
                assert np.isfinite(xs).all(), (c, arm, k)
                blocks[arm.replace('MET', 'NULL') + f'_{k}'].append(xs)
        meta.append(pd.DataFrame({'city': c, 'target': target, 'y': info['y'][st + SEQ]}))
    B = {k: np.vstack(v) for k, v in blocks.items()}
    meta = pd.concat(meta, ignore_index=True)
    fam = ([f'POL|{f}' for d in range(SEQ) for f in FEATURES] + [f'DEC|{ch}' for d in range(SEQ) for ch in CHANNELS]
           + ['CITY'] * len(names))
    return B, meta, np.array(fam), mcols


def main() -> None:
    B, meta, fam_base, mcols = build()
    y = meta['y'].to_numpy()
    tdates = meta['target'].to_numpy()
    arms = {'BASE': None, 'MET': 'MET', 'MET_PP': 'MET_PP'}
    arms.update({f'NULL_{k}': f'NULL_{k}' for k in range(1, N_NULL + 1)})
    arms.update({f'NULL_PP_{k}': f'NULL_PP_{k}' for k in range(1, N_NULL + 1)})
    base = np.hstack([B['POL'], B['DEC'], B['CITY']])
    rows, crow = [], []
    for fold, (ev0, ev1) in FOLDS.items():
        fit = tdates < ev0
        ev = (tdates >= ev0) & (tdates < ev1)
        cut = np.sort(tdates[fit])[int(0.9 * fit.sum())]          # unit-safe 90% date of the fit period
        tr, es = fit & (tdates < cut), fit & (tdates >= cut)
        ev_cities = meta.loc[ev, 'city'].value_counts()
        assert tr.sum() > 0 and es.sum() > 0 and ev.sum() > 0
        print(f'{fold}: fit {fit.sum()} (train {tr.sum()}, early-stop {es.sum()}), eval {ev.sum()}, '
              f'cities eval>={MIN_CITY_EVAL}: {int((ev_cities >= MIN_CITY_EVAL).sum())}', flush=True)
        for arm, blk in arms.items():
            X = base if blk is None else np.hstack([base, B[blk]])
            fam = fam_base if blk is None else np.concatenate([fam_base, np.array([f'MET|{m}' for m in mcols])])
            for s in SEEDS:
                mdl = xgb.XGBRegressor(random_state=s, **PARAMS)
                mdl.fit(X[tr], y[tr], eval_set=[(X[es], y[es])], verbose=False)
                p = mdl.predict(X[ev])
                contrib = np.abs(mdl.get_booster().predict(xgb.DMatrix(X[ev]), pred_contribs=True)[:, :-1])
                def shares(mask_rows: np.ndarray) -> dict:
                    cb = contrib[mask_rows].mean(axis=0)
                    t = cb.sum()
                    d = {'pol': cb[np.char.startswith(fam, 'POL')].sum() / t * 100,
                         'dec_osc': sum(cb[fam == f'DEC|{ch}'].sum() for ch in CHANNELS[:4]) / t * 100,
                         'dec_slow': cb[fam == 'DEC|Slow'].sum() / t * 100,
                         'pm25': cb[fam == 'POL|PM2.5'].sum() / t * 100,
                         'met': cb[np.char.startswith(fam, 'MET')].sum() / t * 100}
                    for bnd in BANDS:
                        d[f'met_{bnd}'] = cb[np.char.endswith(fam, f'|{bnd}') & np.char.startswith(fam, 'MET')].sum() / t * 100
                    for v in MV:
                        d[f'met_{v}'] = cb[np.char.startswith(fam, f'MET|{v}|')].sum() / t * 100
                    return d
                yv = y[ev]
                row = dict(fold=fold, arm=arm, seed=s, n_eval=int(ev.sum()), best_iter=int(mdl.best_iteration),
                           mae=float(np.mean(np.abs(yv - p))), rmse=float(np.sqrt(np.mean((yv - p) ** 2))),
                           r2=float(1 - np.sum((yv - p) ** 2) / np.sum((yv - yv.mean()) ** 2)),
                           **shares(np.ones(ev.sum(), bool)))
                rows.append(row)
                cev = meta.loc[ev, 'city'].to_numpy()
                for c in ev_cities.index[ev_cities >= MIN_CITY_EVAL]:
                    m = cev == c
                    crow.append(dict(fold=fold, arm=arm, seed=s, city=c, n=int(m.sum()),
                                     mae=float(np.mean(np.abs(yv[m] - p[m]))), **shares(m)))
                print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in row.items()
                       if k in ('fold', 'arm', 'seed', 'best_iter', 'mae', 'r2', 'met', 'met_syn', 'met_intra',
                                'met_subs', 'met_seas')}, flush=True)
    res, cres = pd.DataFrame(rows), pd.DataFrame(crow)
    res.to_csv(OUT / 'e5_pooled.csv', index=False)
    cres.to_csv(OUT / 'e5_city.csv', index=False)
    evaluate(res, cres)


def evaluate(res: pd.DataFrame, cres: pd.DataFrame) -> None:
    """Apply the pre-registered rules; print a verdict per hypothesis and fold."""
    g = res.groupby(['fold', 'arm']).mean(numeric_only=True)
    lines = []
    for pp in ('', '_PP'):
        real, nulls = f'MET{pp}', [f'NULL{pp}_{k}' for k in range(1, N_NULL + 1)]
        h1 = h2 = True
        for fold in FOLDS:
            mae_real, mae_null = g.loc[(fold, real), 'mae'], [g.loc[(fold, n), 'mae'] for n in nulls]
            base = g.loc[(fold, 'BASE'), 'mae']
            short = lambda a: g.loc[(fold, a), 'met_syn'] + g.loc[(fold, a), 'met_intra']
            sr, sn = short(real), [short(n) for n in nulls]
            seas_r, seas_n = g.loc[(fold, real), 'met_seas'], [g.loc[(fold, n), 'met_seas'] for n in nulls]
            ok1 = mae_real < min(mae_null)
            ok2 = (sr - max(sn) >= 2.0) and (min(seas_n) <= seas_r <= max(seas_n))
            h1, h2 = h1 and ok1, h2 and ok2
            lines.append(f'{real} {fold}: MAE base {base:.2f} real {mae_real:.2f} null {min(mae_null):.2f}-{max(mae_null):.2f} '
                         f'-> H1 {ok1} | short-band share real {sr:.2f} null max {max(sn):.2f}, seasonal real {seas_r:.2f} '
                         f'null {min(seas_n):.2f}-{max(seas_n):.2f} -> H2 {ok2}')
        cg = cres.groupby(['fold', 'arm', 'city']).mean(numeric_only=True)['met'].unstack('arm')
        ex = cg[real] - cg[nulls].mean(axis=1)
        h3_pos = all((ex.loc[f] > 0).mean() >= 2 / 3 for f in FOLDS)
        both = ex.unstack('fold').dropna()
        rho, p = spearmanr(both['F1'], both['F2']) if len(both) >= 4 else (np.nan, np.nan)
        lines.append(f'{real}: per-city excess share >0 in ' +
                     ', '.join(f'{f} {(ex.loc[f] > 0).sum()}/{len(ex.loc[f])}' for f in FOLDS) +
                     f'; cross-fold Spearman rho {rho:.2f} (p {p:.3f}, n {len(both)}) -> H3 {h3_pos and rho >= 0.5 and p < 0.05}')
        lines.append(f'{real}: VERDICT H1 {h1} H2 {h2} -> {"GO" if h1 and h2 else "NO-GO"} for a positive weather x timescale result')
    txt = '\n'.join(lines)
    print(txt)
    (OUT / 'e5_verdict.txt').write_text(txt + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
