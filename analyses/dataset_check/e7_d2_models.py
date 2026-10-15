"""E7 D2: do causal temporal modes carry stable, city-specific forecast information over 2015-2025 bulletin AQI?
Rules P1-P3 fixed in E7_DECISION_RULES.md. Uses the decompositions cached by e7_decompose.py."""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import spearmanr

from e7_common import D2_CITIES, DECOMP, HERE, HORIZONS, NS, OUT, SEQ, city_calendar, load_bulletin

sys.path.insert(0, str(HERE.parent / 'e1_verification'))
from e1_leakage_contrast import PARAMS, SEEDS  # noqa: E402

EVAL_YEARS = list(range(2019, 2026))
SHORT_YEARS = [2023, 2024, 2025]
MA_WINDOWS = (3, 7, 14, 31)
MAL_WINDOWS = (3, 7, 14, 31, 91, 182, 365)        # addendum 1, D2b: matched 365-day memory
ARMS = {'RAW': ['AQI'], 'RAW+MA': ['AQI', 'MA'], 'RAW+MA+OSC': ['AQI', 'MA', 'OSC'], 'DEC': ['DEC'],
        'RAW+MAL': ['AQI', 'MAL'], 'RAW+MAL+OSC': ['AQI', 'MAL', 'OSC']}


def build(h: int) -> tuple[dict, pd.DataFrame, dict]:
    b = load_bulletin()
    blocks = {k: [] for k in ('AQI', 'MA', 'MAL', 'OSC', 'DEC', 'CITY')}
    meta = []
    for ci, c in enumerate(D2_CITIES):
        info = city_calendar(b, c)
        d = np.load(DECOMP / f'e7_{c}.npz')
        m = json.loads(str(d['meta']))
        fp = NS['c5_fingerprint'](info['cal']['Date'], info['y'], info['available'], info['seed'])
        assert m['fingerprint'] == fp, c
        o = d['days']
        n = len(info['y'])
        t = o + h
        ok = (t < n)
        ok[ok] = info['observed'][t[ok]]
        rows = np.flatnonzero(ok)
        o, t = o[rows], t[rows]
        days = o[:, None] - np.arange(SEQ - 1, -1, -1)[None, :]            # input days o-6..o
        assert info['available'][days].all()
        s = pd.Series(np.where(info['available'], info['y'], np.nan))
        ma = np.column_stack([s.rolling(k, min_periods=1).mean().to_numpy()[o] for k in MA_WINDOWS])
        mal = np.column_stack([s.rolling(k, min_periods=1).mean().to_numpy()[o] for k in MAL_WINDOWS])
        pos = np.flatnonzero(info['available'])                               # addendum 1, D2c: gap-free histories
        first = pos[np.maximum(0, np.searchsorted(pos, o, side='right') - NS['C5_W_MAX'])]
        clean = (o - first + 1) == d['history_len'][rows]
        ch = np.empty((len(o), SEQ, 5))
        for i, r in enumerate(rows):
            k = int(d['n_components'][r])
            ch[i] = NS['c5_channels'](d['tail'][r, :k, -SEQ:]).T
        blocks['AQI'].append(info['y'][days])
        blocks['MA'].append(ma)
        blocks['MAL'].append(mal)
        blocks['OSC'].append(ch[:, :, :4].reshape(len(o), -1))
        blocks['DEC'].append(ch.reshape(len(o), -1))
        oh = np.zeros((len(o), len(D2_CITIES)))
        oh[:, ci] = 1
        blocks['CITY'].append(oh)
        meta.append(pd.DataFrame({'city': c, 'target': info['dates'][t], 'y': info['y'][t], 'clean': clean}))
    B = {k: np.vstack(v) for k, v in blocks.items()}
    fam = {'AQI': np.array(['AQI'] * SEQ), 'MA': np.array(['MA'] * len(MA_WINDOWS)), 'MAL': np.array(['MA'] * len(MAL_WINDOWS)),
           'OSC': np.array([f'IMF{j + 1}' for _ in range(SEQ) for j in range(4)]),
           'DEC': np.array([(f'IMF{j + 1}' if j < 4 else 'Slow') for _ in range(SEQ) for j in range(5)]),
           'CITY': np.array(['CITY'] * len(D2_CITIES))}
    return B, pd.concat(meta, ignore_index=True), fam


def fit_eval(B, meta, fam, parts, fit, ev, seed):
    tdates = meta['target'].to_numpy()
    y = meta['y'].to_numpy()
    cut = np.sort(tdates[fit])[int(0.9 * fit.sum())]
    tr, es = fit & (tdates < cut), fit & (tdates >= cut)
    assert tr.sum() > 0 and es.sum() > 0 and ev.sum() > 0
    X = np.hstack([B[p] for p in parts + ['CITY']])
    f = np.concatenate([fam[p] for p in parts + ['CITY']])
    mdl = xgb.XGBRegressor(random_state=seed, **PARAMS)
    mdl.fit(X[tr], y[tr], eval_set=[(X[es], y[es])], verbose=False)
    p = mdl.predict(X[ev])
    cb = np.abs(mdl.get_booster().predict(xgb.DMatrix(X[ev]), pred_contribs=True)[:, :-1]).mean(axis=0)
    osc = np.isin(f, ['IMF1', 'IMF2', 'IMF3', 'IMF4'])
    return p, {'osc_share': float(cb[osc].sum() / cb.sum() * 100), 'slow_share': float(cb[f == 'Slow'].sum() / cb.sum() * 100)}


def main() -> None:
    rows, crow = [], []
    for h in HORIZONS:
        B, meta, fam = build(h)
        y, tdates = meta['y'].to_numpy(), meta['target'].to_numpy()
        yr = pd.DatetimeIndex(tdates).year.to_numpy()
        print(f'h{h}: windows {len(meta)}, per year {pd.Series(yr).value_counts().sort_index().to_dict()}', flush=True)
        clean = meta['clean'].to_numpy()
        runs = ([(Y, 'long', yr < Y) for Y in EVAL_YEARS] + [(Y, 'short', (yr < Y) & (yr >= Y - 3)) for Y in SHORT_YEARS]
                + [(Y, 'clean', (yr < Y) & clean) for Y in EVAL_YEARS])
        for Y, hist, fit in runs:
            ev = (yr == Y) & (clean if hist == 'clean' else True)
            arms = ARMS if hist == 'long' else {k: ARMS[k] for k in ('RAW+MA', 'RAW+MA+OSC')}
            for arm, parts in arms.items():
                for s in SEEDS:
                    p, sh = fit_eval(B, meta, fam, parts, fit, ev, s)
                    yv = y[ev]
                    rows.append(dict(h=h, year=Y, hist=hist, arm=arm, seed=s, n=int(ev.sum()),
                                     mae=float(np.mean(np.abs(yv - p))), **sh))
                    cev = meta.loc[ev, 'city'].to_numpy()
                    for c in D2_CITIES:
                        m = cev == c
                        if m.sum():
                            crow.append(dict(h=h, year=Y, hist=hist, arm=arm, seed=s, city=c, n=int(m.sum()),
                                             mae=float(np.mean(np.abs(yv[m] - p[m])))))
            g = pd.DataFrame([r for r in rows if r['h'] == h and r['year'] == Y and r['hist'] == hist])
            print(f'  h{h} {Y} {hist}: ' + ', '.join(f'{a} {v:.2f}' for a, v in g.groupby('arm', sort=False)['mae'].mean().items()), flush=True)
    res, cres = pd.DataFrame(rows), pd.DataFrame(crow)
    res.to_csv(OUT / 'e7_d2_pooled.csv', index=False)
    cres.to_csv(OUT / 'e7_d2_city.csv', index=False)
    evaluate(res, cres)


def p1_rule(m: pd.DataFrame, base: str, plus: str) -> tuple[bool, list[str]]:
    """P1 rule: pooled gain of `plus` over `base` > 2 x larger seed s.d., in at least 5 of the 7 years."""
    ok, txt = [], []
    for Y in EVAL_YEARS:
        gain = m.loc[(Y, base), 'mean'] - m.loc[(Y, plus), 'mean']
        thr = 2 * max(m.loc[(Y, base), 'std'], m.loc[(Y, plus), 'std'])
        ok.append(gain > thr)
        txt.append(f'{Y} {gain:+.2f}/{thr:.2f}')
    return sum(ok) >= 5, [f'{sum(ok)}/7 [' + ', '.join(txt) + ']']


def p2_rule(cres: pd.DataFrame, h: int, hist: str, base: str, plus: str) -> tuple[bool, str, pd.Series]:
    """P2 rule: Spearman of per-city mean % gain, 2019-2021 against 2022-2025, rho >= 0.6 and p < 0.05; plus ICC."""
    c = cres[(cres.h == h) & (cres['hist'] == hist)].groupby(['city', 'year', 'arm'])['mae'].mean().unstack('arm')
    g = ((c[base] - c[plus]) / c[base] * 100).unstack('year')
    a, b_ = g[[2019, 2020, 2021]].mean(axis=1), g[[2022, 2023, 2024, 2025]].mean(axis=1)
    ok_rows = a.notna() & b_.notna()
    rho, p = spearmanr(a[ok_rows], b_[ok_rows])
    x = g.to_numpy()
    k_, n_ = x.shape
    msb = n_ * np.nanvar(np.nanmean(x, axis=1), ddof=1)
    msw = np.nansum((x - np.nanmean(x, axis=1, keepdims=True)) ** 2) / (np.isfinite(x).sum() - k_)
    icc = (msb - msw) / (msb + (n_ - 1) * msw)
    return (rho >= 0.6 and p < 0.05), f'halves rho {rho:.2f} (p {p:.3f}, n {int(ok_rows.sum())}), ICC {icc:.2f}', g.mean(axis=1)


def evaluate(res: pd.DataFrame, cres: pd.DataFrame) -> None:
    lines = []
    for h in HORIZONS:
        r = res[(res.h == h)]
        L = r[r['hist'] == 'long']
        m = L.groupby(['year', 'arm'])['mae'].agg(['mean', 'std'])
        for Y in EVAL_YEARS:
            lines.append(f'h{h} {Y}: MAE ' + ' '.join(f'{a} {m.loc[(Y, a), "mean"]:.2f}' for a in ARMS) +
                         f' | OSC share DEC {L[(L.year == Y) & (L.arm == "DEC")].osc_share.mean():.1f}%, '
                         f'RAW+MAL+OSC {L[(L.year == Y) & (L.arm == "RAW+MAL+OSC")].osc_share.mean():.1f}%')
        p1, t1 = p1_rule(m, 'RAW+MA', 'RAW+MA+OSC')
        p1b, t1b = p1_rule(m, 'RAW+MAL', 'RAW+MAL+OSC')
        p2, t2, g = p2_rule(cres, h, 'long', 'RAW+MA', 'RAW+MA+OSC')
        S = r[r['hist'] == 'short'].groupby(['year', 'arm'])['mae'].agg(['mean', 'std'])
        p3_years = []
        for Y in SHORT_YEARS:
            gl = m.loc[(Y, 'RAW+MA'), 'mean'] - m.loc[(Y, 'RAW+MA+OSC'), 'mean']
            gs = S.loc[(Y, 'RAW+MA'), 'mean'] - S.loc[(Y, 'RAW+MA+OSC'), 'mean']
            thr = 2 * max(m.loc[(Y, 'RAW+MA+OSC'), 'std'], S.loc[(Y, 'RAW+MA+OSC'), 'std'])
            p3_years.append(gl - gs > thr)
            lines.append(f'h{h} {Y}: OSC gain long history {gl:.2f} vs short (3 y) {gs:.2f} (thr {thr:.2f})')
        p3 = sum(p3_years) >= 2
        C = r[r['hist'] == 'clean'].groupby(['year', 'arm'])['mae'].agg(['mean', 'std'])
        p1c, t1c = p1_rule(C, 'RAW+MA', 'RAW+MA+OSC')
        p2c, t2c, gc = p2_rule(cres, h, 'clean', 'RAW+MA', 'RAW+MA+OSC')
        lines.append(f'h{h}: per-city OSC gain % (all windows): ' + ', '.join(f'{ci} {v:.1f}' for ci, v in g.sort_values().items()))
        lines.append(f'h{h}: per-city OSC gain % (gap-free): ' + ', '.join(f'{ci} {v:.1f}' for ci, v in gc.sort_values().items()))
        lines.append(f'h{h}: P1 {p1} {t1[0]}')
        lines.append(f'h{h}: P1b (beyond 365-d memory) {p1b} {t1b[0]}')
        lines.append(f'h{h}: P2 {p2} ({t2}) | P3 {p3} ({sum(p3_years)}/3)')
        lines.append(f'h{h}: gap-free P1 {p1c} {t1c[0]} | gap-free P2 {p2c} ({t2c})')
    txt = '\n'.join(lines)
    print(txt)
    (OUT / 'e7_d2_verdict.txt').write_text(txt + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
