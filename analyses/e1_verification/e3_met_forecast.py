"""E3: does meteorology add forecast skill to the causal model, and does it take attribution from the slow channel?

Same lb7 windows, splits, model and seeds as E1. Added blocks:
  METPAST : ERA5 on the 7 input days (t-6..t), 6 variables: log BLH, wind, log ventilation, T2m, RH, sqrt precip.
            Available at forecast time (reanalysis used as a stand-in for observations/analyses).
  METTGT  : the same 6 variables on the target day t+1 ("perfect prognosis": an upper bound for using a
            meteorological forecast; reanalysis is not a forecast).
  DOY     : sin/cos of the target day of year (a pure seasonal clock, control for METTGT acting as a calendar).
Arms: CAUSAL, CAUSAL+DOY, CAUSAL+METPAST, CAUSAL+METTGT, CAUSAL+METPAST+METTGT, RAW+METTGT.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

from common import CHANNELS, FEATURES, NS, OUT, build_lb7, city_calendars, load_causal, load_df
from e1_leakage_contrast import PARAMS, SEEDS, SEQ, r2

MV = ['lblh', 'wind', 'lvent', 't2m', 'rh', 'sprecip']


def main() -> None:
    df = load_df()
    cities = city_calendars(df)
    raw = build_lb7(cities, SEQ)
    met = pd.read_csv(OUT / 'era5_daily.csv', parse_dates=['Date'])
    met['lblh'], met['lvent'], met['sprecip'] = np.log(met['blh']), np.log(met['vent']), np.sqrt(met['precip'])
    names = list(cities)
    blocks = {k: [] for k in ('POL', 'AQI', 'DEC', 'METPAST', 'METTGT', 'DOY', 'CITY')}
    meta = []
    for ci, c in enumerate(names):
        info, r = cities[c], raw[c]
        st = r['starts']
        days = st[:, None] + np.arange(SEQ)[None, :]
        cal_dates = pd.to_datetime(info['cal']['Date'])
        m = met[met.City == c].set_index('Date').reindex(cal_dates)[MV].to_numpy()
        assert np.isfinite(m).all()
        blocks['POL'].append(r['pol'][days].reshape(len(st), -1))
        blocks['AQI'].append(info['y'][days])
        blocks['DEC'].append(NS['c5_window_channels'](load_causal(c, info), st, SEQ).reshape(len(st), -1))
        blocks['METPAST'].append(m[days].reshape(len(st), -1))
        blocks['METTGT'].append(m[st + SEQ])
        doy = cal_dates.dt.dayofyear.to_numpy()[st + SEQ]
        blocks['DOY'].append(np.column_stack([np.sin(2 * np.pi * doy / 365.25), np.cos(2 * np.pi * doy / 365.25)]))
        oh = np.zeros((len(st), len(names)))
        oh[:, ci] = 1
        blocks['CITY'].append(oh)
        n_tr, n_trv, n = r['splits']
        meta.append(pd.DataFrame({'city': c, 'split': ['train'] * n_tr + ['val'] * (n_trv - n_tr) + ['test'] * (n - n_trv),
                                  'y': info['y'][st + SEQ]}))
    B = {k: np.vstack(v) for k, v in blocks.items()}
    meta = pd.concat(meta, ignore_index=True)
    fam = {'POL': [f for d in range(SEQ) for f in FEATURES], 'AQI': ['AQI'] * SEQ,
           'DEC': [ch for d in range(SEQ) for ch in CHANNELS], 'METPAST': ['met_past'] * (SEQ * len(MV)),
           'METTGT': ['met_target'] * len(MV), 'DOY': ['doy'] * 2, 'CITY': ['city'] * len(names)}
    arms = {'CAUSAL': ['POL', 'DEC'], 'CAUSAL+DOY': ['POL', 'DEC', 'DOY'], 'CAUSAL+METPAST': ['POL', 'DEC', 'METPAST'],
            'CAUSAL+METTGT': ['POL', 'DEC', 'METTGT'], 'CAUSAL+METPAST+METTGT': ['POL', 'DEC', 'METPAST', 'METTGT'],
            'RAW+METTGT': ['POL', 'AQI', 'METTGT']}
    tr, va, te = ((meta['split'] == s).to_numpy() for s in ('train', 'val', 'test'))
    y = meta['y'].to_numpy()
    rows = []
    for a, parts in arms.items():
        X = np.hstack([B[p] for p in parts + ['CITY']])
        f = np.array(sum((fam[p] for p in parts + ['CITY']), []))
        assert len(f) == X.shape[1]
        for s in SEEDS:
            mdl = xgb.XGBRegressor(random_state=s, **PARAMS)
            mdl.fit(X[tr], y[tr], eval_set=[(X[va], y[va])], verbose=False)
            p = mdl.predict(X[te])
            cb = np.abs(mdl.get_booster().predict(xgb.DMatrix(X[te]), pred_contribs=True)[:, :-1]).mean(axis=0)
            sh = {g: float(cb[f == g].sum() / cb.sum() * 100) for g in np.unique(f)}
            row = dict(arm=a, seed=s, val_r2=r2(y[va], mdl.predict(X[va])), test_r2=r2(y[te], p),
                       test_mae=float(np.mean(np.abs(y[te] - p))),
                       slow=sh.get('Slow', np.nan), osc=sum(sh.get(ch, 0) for ch in CHANNELS[:4]),
                       aqi=sh.get('AQI', np.nan), pm25=sh['PM2.5'], met_past=sh.get('met_past', np.nan),
                       met_target=sh.get('met_target', np.nan), doy=sh.get('doy', np.nan))
            rows.append(row)
            print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}, flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / 'e3_met_forecast.csv', index=False)
    print(out.groupby('arm', sort=False).agg(['mean', 'std']).drop(columns='seed').round(3).T.to_string())


if __name__ == '__main__':
    main()
