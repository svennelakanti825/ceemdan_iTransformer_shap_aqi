"""E1: does full-record (leaky) decomposition inflate forecast skill AND temporal attribution, everything else fixed?

Arms (identical lb7 windows, splits, cities, target, model, hyperparameters and seeds):
  POL      12 pollutants x 7 days
  RAW      POL + raw AQI x 7 days                      (the paper's raw-history ablation, as features)
  CAUSAL   POL + 5 causal CEEMDAN channels x 7 days    (run-of-record ext_ar cache, block from the origin's decomposition)
  LEAKY    POL + 5 full-record CEEMDAN channels x 7 days (one decomposition of the whole record per city)
All arms add a city one-hot (the iTransformer has a city bias). Model: XGBoost with early stopping on the
validation split; attribution: exact TreeSHAP on all test windows, shares of total mean |SHAP|.
This isolates the leakage effect for a tree model. It does not reproduce the iTransformer numbers.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import xgboost as xgb

from common import CHANNELS, FEATURES, NS, OUT, build_lb7, city_calendars, load_causal, load_df

SEQ = 7
SEEDS = [0, 1, 2]
PARAMS = dict(n_estimators=3000, learning_rate=0.03, max_depth=6, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=5, reg_lambda=1.0, tree_method='hist', early_stopping_rounds=100)


def leaky_window_channels(city: str, info: dict, starts: np.ndarray) -> np.ndarray:
    d = np.load(OUT / f'fullrec_{city}.npz')
    ch, idx = d['channels'], d['avail_idx']
    pos = np.full(len(info['y']), -1)
    pos[idx] = np.arange(len(idx))
    days = starts[:, None] + np.arange(SEQ)[None, :]           # calendar days of each window
    p = pos[days]
    if (p < 0).any():
        raise ValueError(city)
    return np.transpose(ch[:, p], (1, 2, 0))                   # (n, SEQ, 5)


def build(arms: list[str]) -> tuple[dict, list[str], list[str]]:
    df = load_df()
    cities = city_calendars(df)
    raw = build_lb7(cities, SEQ)
    names = list(cities)
    parts = {a: [] for a in arms}
    meta = []
    for ci, c in enumerate(names):
        info, r = cities[c], raw[c]
        st = r['starts']
        days = st[:, None] + np.arange(SEQ)[None, :]
        pol = r['pol'][days]                                     # (n, 7, 12)
        aqi = info['y'][days][:, :, None]                        # (n, 7, 1); filled days hold the copied value
        y = info['y'][st + SEQ]
        onehot = np.zeros((len(st), len(names)))
        onehot[:, ci] = 1
        n_tr, n_trv, n = r['splits']
        split = np.array(['train'] * n_tr + ['val'] * (n_trv - n_tr) + ['test'] * (n - n_trv))
        dates = pd.to_datetime(info['cal']['Date']).to_numpy()[st + SEQ]
        meta.append(pd.DataFrame({'city': c, 'split': split, 'date': dates, 'y': y}))
        feats = {'POL': [pol]}
        if 'RAW' in arms:
            feats['RAW'] = [pol, aqi]
        if 'CAUSAL' in arms:
            feats['CAUSAL'] = [pol, NS['c5_window_channels'](load_causal(c, info), st, SEQ)]
        if 'LEAKY' in arms:
            feats['LEAKY'] = [pol, leaky_window_channels(c, info, st)]
        for a in arms:
            blocks = feats[a]
            x = np.concatenate([b.reshape(len(st), -1) if b.ndim == 3 else b for b in blocks], axis=1)
            parts[a].append(np.concatenate([x, onehot], axis=1))
    X = {a: np.vstack(parts[a]) for a in arms}
    return X, pd.concat(meta, ignore_index=True), names


def colnames(arm: str, names: list[str]) -> list[str]:
    # reshape(n, -1) of (n, 7, k) is day-major, so the name lists are day-major too
    cols = [f'{f}|{d}' for d in range(SEQ) for f in FEATURES]
    if arm == 'RAW':
        cols += [f'AQI|{d}' for d in range(SEQ)]
    if arm in ('CAUSAL', 'LEAKY'):
        cols += [f'{ch}|{d}' for d in range(SEQ) for ch in CHANNELS]
    return cols + [f'city={c}' for c in names]


def r2(y: np.ndarray, p: np.ndarray) -> float:
    return float(1 - np.sum((y - p) ** 2) / np.sum((y - y.mean()) ** 2))


def main(arms: list[str]) -> None:
    X, meta, names = build(arms)
    tr, va, te = ((meta['split'] == s).to_numpy() for s in ('train', 'val', 'test'))
    print('windows', tr.sum(), va.sum(), te.sum(), flush=True)
    y = meta['y'].to_numpy()
    rows, shares = [], []
    for a in arms:
        cols = colnames(a, names)
        assert len(cols) == X[a].shape[1], (a, len(cols), X[a].shape)
        fam = np.array([c.split('|')[0] if '|' in c else 'city' for c in cols])
        for s in SEEDS:
            m = xgb.XGBRegressor(random_state=s, **PARAMS)
            m.fit(X[a][tr], y[tr], eval_set=[(X[a][va], y[va])], verbose=False)
            p = m.predict(X[a][te])
            pv = m.predict(X[a][va])
            rows.append(dict(arm=a, seed=s, val_r2=r2(y[va], pv), test_r2=r2(y[te], p),
                             test_rmse=float(np.sqrt(np.mean((y[te] - p) ** 2))), best_iter=m.best_iteration))
            contrib = m.get_booster().predict(xgb.DMatrix(X[a][te]), pred_contribs=True)[:, :-1]
            mabs = np.abs(contrib).mean(axis=0)
            tot = mabs.sum()
            share = {f: float(mabs[fam == f].sum() / tot * 100) for f in np.unique(fam)}
            share.update(arm=a, seed=s)
            shares.append(share)
            print(rows[-1], flush=True)
            # per-city decomposition share for the three focus cities
            if a in ('CAUSAL', 'LEAKY'):
                for c in ('Delhi', 'Mumbai', 'Bengaluru'):
                    sel = (meta.loc[te, 'city'] == c).to_numpy()
                    mc = np.abs(contrib[sel]).mean(axis=0)
                    dec = sum(mc[fam == ch].sum() for ch in CHANNELS) / mc.sum() * 100
                    osc = sum(mc[fam == ch].sum() for ch in CHANNELS[:4]) / mc.sum() * 100
                    shares.append(dict(arm=a, seed=s, city=c, dec_share=float(dec), osc_share=float(osc)))
    pd.DataFrame(rows).to_csv(OUT / 'e1_accuracy.csv', index=False)
    pd.DataFrame(shares).to_csv(OUT / 'e1_shares.csv', index=False)
    print(pd.DataFrame(rows).groupby('arm')[['val_r2', 'test_r2', 'test_rmse']].agg(['mean', 'std']).round(4))


if __name__ == '__main__':
    main(sys.argv[1].split(',') if len(sys.argv) > 1 else ['POL', 'RAW', 'CAUSAL', 'LEAKY'])
