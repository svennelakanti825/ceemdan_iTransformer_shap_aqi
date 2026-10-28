"""Write the LaTeX tables of the revised manuscript and its supplement from the stored result files.

Main-text tables go to ../tables/, supplementary tables to ../si_tables/. Every number is read from a result file
of the revision (paths in SRC) and only formatted, averaged or converted to shares here.

Usage: python make_tables.py
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
TAB, SI = HERE.parent / 'tables', HERE.parent / 'si_tables'
REPO = HERE.parents[2]
R1 = REPO / 'analyses'
RES = REPO / 'results' / '02_r1_ext' / 'reports'
GF = REPO / 'results' / '04_followups' / 'reports'
LC = R1 / 'literature_count' / 'outputs'
SRC = {
    'baselines_pooled': R1 / 'baselines' / 'outputs' / 'baselines_pooled.csv',
    'baselines_city': R1 / 'baselines' / 'outputs' / 'baselines_city.csv',
    'baselines_skill': R1 / 'baselines' / 'outputs' / 'baselines_skill.csv',
    'phase1': REPO / 'results' / '01_baselines' / 'phase1_colab_comparison_metrics.csv',
    'v2_full': RES / 'comparison_v2_full.csv',
    'multiseed': RES / 'multiseed_summary_lb7.csv',
    'g3': GF / 'g3_conditioning_summary_lb7.csv',
    'g3_pred': GF / 'g3_test_predictions_lb7.npz',
    'g1': GF / 'shap' / 'g1_shap18_summary_lb7.csv',
    'g2_anova': GF / 'g2_anova_lb7.csv',
    'e1_acc': R1 / 'x1_shap_recheck' / 'outputs' / 'e1_accuracy.csv',
    'e1_shares': R1 / 'x1_shap_recheck' / 'outputs' / 'e1_shares.csv',
    'e7_pooled': R1 / 'x1_shap_recheck' / 'outputs' / 'e7_d2_pooled.csv',
    'c2_verdict': R1 / 'e1_verification' / 'outputs' / 'c2_runs' / 'T6' / 'c2x_verdict.json',
    'c2_verdict_txt': R1 / 'e1_verification' / 'outputs' / 'c2_runs' / 'T6' / 'c2x_verdict.txt',
    'lc_coding': LC / 'coding_sheet.csv',
    'lc_order': LC / 'coding_order.csv',
}
CAPTION_NOTE = r'\par\smallskip\begin{minipage}{0.98\linewidth}\footnotesize '


def f(x: float, d: int = 2) -> str:
    return '' if x is None or (isinstance(x, float) and math.isnan(x)) else f'{x:,.{d}f}'.replace('-', '$-$')


def pm(m: float, s: float, d: int = 2) -> str:
    return f'{f(m, d)} $\\pm$ {f(s, d)}'


def table(path: Path, label: str, caption: str, cols: str, header: list[str], rows: list[list[str]],
          note: str = '', size: str = '\\small') -> None:
    out = ['\\begin{table}[!htbp]', '\\centering', size, f'\\caption{{{caption}}}\\label{{{label}}}',
           '\\setlength{\\tabcolsep}{4pt}', '\\resizebox{\\linewidth}{!}{%',
           f'\\begin{{tabular}}{{{cols}}}', '\\toprule', ' & '.join(header) + r' \\',
           '\\midrule']
    for r in rows:
        out.append('\\midrule' if r == ['MIDRULE'] else ' & '.join(r) + r' \\')
    out += ['\\bottomrule', '\\end{tabular}}']
    if note:
        out.append(CAPTION_NOTE + note + r'\end{minipage}')
    out.append('\\end{table}')
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('written', path.name)


def table1_performance() -> None:
    bp = pd.read_csv(SRC['baselines_pooled']).set_index(['forecast', 'subset'])
    p1 = pd.read_csv(SRC['phase1']).set_index('label')
    v2 = pd.read_csv(SRC['v2_full'])
    v2 = v2[v2.lookback == 7].set_index('model')
    ms = pd.read_csv(SRC['multiseed']).set_index('model')
    rows = []
    for name in ('Persistence', 'Climatology'):
        a, pre, lock = (bp.loc[(name, s)] for s in ('all', 'pre-lockdown', 'lockdown/Unlock'))
        rows.append([{'Climatology': 'Seasonal climatology'}.get(name, name), f(a.r2, 3), f(a.rmse), f(a.mae),
                     f(pre.mae), f(lock.mae), f(lock.r2, 3)])
    rows.append(['MIDRULE'])
    single = [('XGBoost', p1.loc['XGBoost-LB7'], 'R2', 'RMSE', 'MAE'),
              ('LSTM (Keras)', p1.loc['LSTM-LB7'], 'R2', 'RMSE', 'MAE'),
              ('LSTM (PyTorch)', v2.loc['LSTM'], 'r2', 'rmse', 'mae'),
              ('Augmented model', v2.loc['CEEMDAN+iTransformer-v2'], 'r2', 'rmse', 'mae'),
              ('DLinear', p1.loc['DLinear-LB7'], 'R2', 'RMSE', 'MAE'),
              ('Plain iTransformer', v2.loc['iTransformer'], 'r2', 'rmse', 'mae'),
              ('NLinear', p1.loc['NLinear-LB7'], 'R2', 'RMSE', 'MAE'),
              ('CEEMDAN+LSTM', v2.loc['CEEMDAN+LSTM'], 'r2', 'rmse', 'mae')]
    for name, r, cr2, crm, cma in single:
        rows.append([name, f(r[cr2], 3), f(r[crm]), f(r[cma]), f(r.get('mae_pre', np.nan)),
                     f(r.get('mae_lock', np.nan)), f(r.get('r2_lock', np.nan), 3)])
    rows.append(['MIDRULE'])
    for name, key in [('Augmented model', 'CEEMDAN+iTransformer-v2 (proposed)'),
                      ('Plain iTransformer', 'iTransformer (plain)'),
                      ('Raw-history ablation', '13ch ablation (12 pollutants + lagged AQI)')]:
        r = ms.loc[key]
        rows.append([name + ' (5 seeds)', pm(r.mean_r2, r.std_r2, 3), pm(r.mean_rmse, r.std_rmse),
                     pm(r.mean_mae, r.std_mae), pm(r.mean_mae_pre, r.std_mae_pre), pm(r.mean_mae_lock, r.std_mae_lock),
                     pm(r.mean_r2_lock, r.std_r2_lock, 3)])
    table(TAB / 'table1_performance.tex', 'tab:performance',
          'Next-day AQI forecasts on the 6,171 test windows of 18 cities (lookback 7 days).',
          'lrrrrrr', ['Forecast', '$R^2$', 'RMSE', 'MAE', 'MAE before', 'MAE after', '$R^2$ after'], rows,
          'RMSE and MAE are in AQI units. Before and after refer to target dates before and from 25 March 2020 '
          '(4,502 and 1,669 windows). Persistence repeats the AQI of the forecast origin day. Seasonal climatology is '
          'the city mean over training days within 15 days of the target day of year. The middle block gives single '
          'runs (model seed 123 for the neural models). The last block gives the mean and standard deviation over '
          'model seeds 7, 42, 123, 2024 and 2025. The implementations differ in capacity and tuning.',
          size='\\footnotesize')


def table2_conditioning() -> None:
    g = pd.read_csv(SRC['g3']).set_index('conditioning')
    names = {'bias': 'Scalar city bias (main model)', 'none': 'No city term', 'scale_bias': 'City scale and bias',
             'vector_bias': 'City vector and bias'}
    z = np.load(SRC['g3_pred'])
    late = z['test_dates'] >= np.datetime64('2020-03-25')

    def error_after(arm: str) -> tuple[float, float]:
        e = [(z[f'pred__{arm}__{s}'][late] - z['y_test'][late]).mean() for s in (42, 123, 2024, 7, 2025)]
        return float(np.mean(e)), float(np.std(e, ddof=1))

    rows = []
    for k in ('bias', 'none', 'scale_bias', 'vector_bias'):
        r = g.loc[k]
        rows.append([names[k], pm(r.mean_val_r2, r.std_val_r2, 3), pm(r.mean_test_r2, r.std_test_r2, 3),
                     pm(r.mean_test_mae, r.std_test_mae), pm(r.mean_test_r2_pre, r.std_test_r2_pre, 3),
                     pm(r.mean_test_r2_lock, r.std_test_r2_lock, 3), pm(r.mean_test_mae_lock, r.std_test_mae_lock),
                     pm(*error_after(k), 1)])
    table(TAB / 'table2_conditioning.tex', 'tab:conditioning',
          'City conditioning of the augmented model, mean and standard deviation over five model seeds.',
          'lrrrrrrr', ['Arm', 'Validation $R^2$', 'Test $R^2$', 'Test MAE', '$R^2$ before', '$R^2$ after',
                      'MAE after', 'Mean error after'], rows,
          'Before and after refer to target dates before and from 25 March 2020. Mean error after is the mean of forecast '
          'minus observed AQI over the 1,669 windows from that date, in AQI units. The selection rule was fixed before '
          'the runs and uses validation scores only. The no-city-term arm is a diagnostic outside that rule.',
          size='\\footnotesize')


def si_baselines_city() -> None:
    c = pd.read_csv(SRC['baselines_city'])
    rows = []
    for r in c.itertuples():
        rows.append([r.city, f'{int(r.n):,}', f(r.persistence_mae), f(r.persistence_r2, 3), f(r.climatology_mae),
                     f(r.climatology_r2, 3), pm(r.model_mae_mean, r.model_mae_sd), f(r.model_r2_mean, 3)])
    table(SI / 'tableS_baselines_city.tex', 'tab:s_baselines_city',
          'Persistence, seasonal climatology and the augmented model by city on the test year.',
          'lrrrrrrr', ['City', 'Windows', 'Pers. MAE', 'Pers. $R^2$', 'Clim. MAE', 'Clim. $R^2$', 'Model MAE',
                       'Model $R^2$'], rows,
          'Augmented model: mean (and standard deviation of MAE) over five model seeds. MAE in AQI units.',
          size='\\footnotesize')


def si_g1() -> None:
    g = pd.read_csv(SRC['g1'])
    rows = []
    for r in g.itertuples():
        rows.append([r.city + ('' if r.passes_completeness else '$^{a}$'), f'{int(r.test_n)}', f(r.test_r2, 3),
                     f(r.decomposition_share_pct, 1), f(r.imf1_4_share_pct, 2), f(r.slow_of_decomposition_pct, 1),
                     r.leading_input.replace('PM2.5', 'PM$_{2.5}$')])
    table(SI / 'tableS_g1_all_cities.tex', 'tab:s_g1',
          'Channel attribution of the augmented model in all 18 modelled cities (model seed 123, lookback 7 days).',
          'lrrrrrl', ['City', 'Test windows', 'Test $R^2$', 'Decomposition (\\%)', 'IMF1 to IMF4 (\\%)',
                      'Slow in decomposition (\\%)', 'Leading input'], rows,
          'Shares of the summed mean absolute channel SHAP value over 100 explained test windows, with 50 training '
          'windows as background. $^{a}$Limited data: fails the 80\\% completeness rule and is not interpreted city by '
          'city.', size='\\footnotesize')


def si_g2() -> None:
    a = pd.read_csv(SRC['g2_anova'])
    qn = {'decomposition_share_pct': 'Decomposition share (\\%)', 'imf1_4_share_pct': 'IMF1 to IMF4 (\\%)',
          'slow_of_decomposition_pct': 'Slow in decomposition (\\%)', 'val_r2': 'Validation $R^2$',
          'test_r2': 'Test $R^2$', 'test_mae': 'Test MAE'}
    rows = []
    for r in a[a.quantity.isin(qn)].itertuples():
        d = 4 if 'r2' in r.quantity else 2
        rows.append([r.scope.replace('pooled', 'All cities'), qn[r.quantity], f(r.mean, d), f(r.sd_within, d),
                     f(r.sd_between, d), f(r.F, 2), f(r.p_value, 3), f'{f(r.min, d)} to {f(r.max, d)}'])
    table(SI / 'tableS_g2_realisations.tex', 'tab:s_g2',
          'Four CEEMDAN realisations with five model seeds each: one-way random-effects analysis over realisations.',
          'llrrrrrr', ['Scope', 'Quantity', 'Mean', 'Seed s.d.', 'Between s.d.', '$F_{3,16}$', '$p$', 'Range'], rows,
          'Seed s.d. is the model-seed standard deviation within realisations. Between s.d. is the realisation '
          'standard deviation, set to zero when realisations differ less than model seeds alone would make them. '
          'With 4 groups of 5 the test detects a realisation s.d. of 1.32 times the seed s.d. with 80\\% probability.',
          size='\\footnotesize')


def si_e1() -> None:
    acc = pd.read_csv(SRC['e1_acc'])
    sh = pd.read_csv(SRC['e1_shares'])
    sh = sh[sh.arm.isin(['CAUSAL', 'LEAKY']) & sh.city.isin(['Delhi', 'Mumbai', 'Bengaluru'])].copy()
    sh['osc_share'] = pd.to_numeric(sh.osc_share)
    names = {'POL': 'Pollutants only', 'RAW': 'Pollutants and raw AQI history',
             'CAUSAL': 'Pollutants and past-only decomposition', 'LEAKY': 'Pollutants and whole-record decomposition'}
    rows = []
    for arm in ('POL', 'RAW', 'CAUSAL', 'LEAKY'):
        d = acc[acc.arm == arm]
        osc = [f(sh[(sh.arm == arm) & (sh.city == c)].osc_share.mean(), 2) if arm in ('CAUSAL', 'LEAKY') else ''
               for c in ('Delhi', 'Mumbai', 'Bengaluru')]
        rows.append([names[arm], pm(d.test_r2.mean(), d.test_r2.std(ddof=1), 3), f(d.test_rmse.mean(), 1)] + osc)
    table(SI / 'tableS_e1_leakage.tex', 'tab:s_e1',
          'Leakage contrast with XGBoost: only the source of the five decomposition channels changes.',
          'lrrrrr', ['Arm', 'Test $R^2$', 'Test RMSE', 'Delhi', 'Mumbai', 'Bengaluru'], rows,
          'Mean over model seeds 0, 1 and 2 (standard deviation for $R^2$) on the recorded windows. The last three '
          'columns give the IMF1 to IMF4 share of the summed mean absolute TreeSHAP value (\\%), computed on the '
          'early-stopped model. Pooled over the test windows the share is 3.91\\% with past-only and 26.44\\% with '
          'whole-record decomposition.', size='\\footnotesize')


def si_e7() -> None:
    e = pd.read_csv(SRC['e7_pooled'])
    e = e[e['hist'] == 'long']
    rows = []
    for h in (1, 7):
        for y in sorted(e.year.unique()):
            d = e[(e.h == h) & (e.year == y)]
            m = d.groupby('arm').mae.mean()
            osc = d.groupby('arm').osc_share.mean()
            g1 = 100 * (m['RAW+MA'] - m['RAW+MA+OSC']) / m['RAW+MA']
            g2 = 100 * (m['RAW+MAL'] - m['RAW+MAL+OSC']) / m['RAW+MAL']
            rows.append([str(h), str(y), f(m['RAW+MA']), f(g1, 2), f(m['RAW+MAL']), f(g2, 2),
                         f(osc['RAW+MAL+OSC'], 1), f(osc['DEC'], 1)])
    table(SI / 'tableS_e7_bulletins.tex', 'tab:s_e7',
          'Past-only decomposition modes on the CPCB AQI bulletin series compiled by urbanemissions.info for 14 cities, '
          'yearly folds 2019--2025.',
          'rrrrrrrr', ['$h$', 'Year', 'MAE, history and means', 'Gain (\\%)', 'MAE, with 365-day memory',
                       'Gain (\\%)', 'Mode share (\\%)', 'Mode share, decomposition only (\\%)'], rows,
          'XGBoost, mean over seeds 0, 1 and 2, horizon $h$ in days. Gain is the MAE reduction when IMF1 to IMF4 are '
          'added to raw history with trailing means of 3 to 31 days, or of 3 to 182 days with a 365-day mean. Mode '
          'share is the IMF1 to IMF4 share of the summed mean absolute TreeSHAP value in the model with the '
          '365-day memory and in the model given only the five decomposition channels.', size='\\footnotesize')


def si_c2() -> None:
    v = json.loads(SRC['c2_verdict'].read_text(encoding='utf-8'))
    txt = SRC['c2_verdict_txt'].read_text(encoding='utf-8')

    def grab(label: str) -> list[str]:
        m = re.search(re.escape(label) + r'.*?effect ([+-][\d.]+) \(90% ([+-][\d.]+) to ([+-][\d.]+)\)(?: = ([+-][\d.]+)% '
                      r'\(([+-][\d.]+) to ([+-][\d.]+)\))?(?:\s+p ([\d.]+))?', txt)
        return list(m.groups())

    rows = []
    for lab, key, unit in [('H1, forecast-day weather against same-season nulls (MAE)', 'H1 MAE', 'pct'),
                           ('H2, short-band weather share above nulls (points)', 'H2 short-band', 'pp'),
                           ('H1b, forecast-day weather adds to origin weather (MAE)', 'H1b MAE', 'abs'),
                           ('Weather up to the origin against its nulls (MAE)', 'P H1 MAE', 'pct'),
                           ('Forecast-day weather against no weather (MAE)', 'BASE_minus_MET_PP', 'abs'),
                           ('Same-season weather against no weather (MAE)', 'BASE_minus_POOL_PP', 'abs')]:
        g = grab(key)
        if unit == 'pct':
            est, ci = f'{g[3]}\\%', f'{g[4]} to {g[5]}\\%'
        else:
            est, ci = g[0], f'{g[1]} to {g[2]}'
        rows.append([lab, est.replace('-', '$-$'), ci.replace('-', '$-$'), g[6] or ''])
    gate_pct = v['gate']['g_pct']
    table(SI / 'tableS_c2_rules.tex', 'tab:s_c2',
          'Pre-registered weather diagnostic (XGBoost, 40 seeds per arm): rules and secondary contrasts.',
          'lrrr', ['Contrast', 'Effect', '90\\% interval', 'One-sided $p$'], rows,
          f'Effects are differences in test MAE (AQI units or percent of the null mean) or in attribution share '
          f'(percentage points). H1, H2 and H1b were tested in that order at one-sided 5\\%. Forecast-day weather is a '
          f'perfect-prognosis setting. Gate: the H1 effect of {gate_pct:.2f}\\% is '
          f'below the pre-registered 13\\%, so the iTransformer arm was not run.', size='\\footnotesize')


def si_literature() -> None:
    c = pd.read_csv(SRC['lc_coding'], dtype=str).fillna('')
    o = pd.read_csv(SRC['lc_order'], dtype=str).fillna('')
    c = c[c.status == 'CODED'].merge(o[['rid', 'doi', 'year', 'title']], on='rid', how='left').sort_values('rid')
    t3 = {'i': '(i)', 'ii': '(ii)', 'iii': '(iii)', 'iv': '(iv)', 'v': '(v)'}
    rows = []
    for r in c.itertuples():
        rows.append([r.rid, r.year, f'\\url{{{r.doi}}}', r.T2_method.replace('_', ' '), t3.get(r.T3_timing, r.T3_timing),
                     r.T5_nodec_model, r.T6_persistence, r.T8_interpretation])
    out = ['\\setlength{\\LTleft}{0pt}', '\\setlength{\\LTright}{0pt}', '\\scriptsize',
           '\\begin{longtable}{llp{0.29\\linewidth}p{0.17\\linewidth}llll}',
           '\\caption{Coding of the 60 sampled studies (protocol items T2, T3, T5, T6 and T8).}\\label{tab:s_lit_coding}\\\\',
           '\\toprule', r'ID & Year & DOI & Method & T3 & T5 & T6 & T8 \\', '\\midrule', '\\endfirsthead',
           '\\toprule', r'ID & Year & DOI & Method & T3 & T5 & T6 & T8 \\', '\\midrule', '\\endhead']
    out += [' & '.join(x) + r' \\' for x in rows]
    out += ['\\bottomrule', '\\end{longtable}']
    (SI / 'tableS_lit_coding.tex').write_text('\n'.join(out) + '\n', encoding='utf-8')
    print('written tableS_lit_coding.tex')


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return 100 * max(0.0, c - h), 100 * min(1.0, c + h)


def si_lit_summary() -> None:
    c = pd.read_csv(SRC['lc_coding'], dtype=str).fillna('')
    c = c[c.status == 'CODED']
    n = len(c)
    items = [('Whole series decomposed, then split (i)', c.T3_timing == 'i'),
             ('Test block decomposed separately (ii)', c.T3_timing == 'ii'),
             ('Past-only at each forecast origin (iii)', c.T3_timing == 'iii'),
             ('Other (iv)', c.T3_timing == 'iv'),
             ('Not stated or unclear (v)', c.T3_timing == 'v'),
             ('Order stated in words, among (i)', (c.T3_timing == 'i') & (c.T3_explicit == 'yes')),
             ('Boundary at the forecast origin discussed', c.T4_boundary == 'yes'),
             ('Non-decomposed version of the same model reported', c.T5_nodec_model == 'yes'),
             ('Persistence or naive forecast reported', c.T6_persistence == 'yes'),
             ('Modes read as physical drivers or timings', c.T8_interpretation == 'yes'),
             ('Explanation method applied (SHAP, attention, permutation or other)', c.T9_explanation.isin(['SHAP', 'attention', 'permutation', 'other'])),
             ('Code or data openly available', c.T10_code_data == 'yes')]
    rows = []
    for lab, m in items:
        k = int(m.sum())
        lo, hi = wilson(k, n)
        rows.append([lab, f'{k} of {n}', f'{100 * k / n:.0f}', f'{lo:.0f} to {hi:.0f}'])
    table(SI / 'tableS_lit_summary.tex', 'tab:s_lit_summary',
          f'Coding of {n} randomly sampled open-access studies of decomposition-based air quality forecasting.',
          'lrrr', ['Item', 'Studies', '\\%', '95\\% interval'], rows,
          'Intervals are Wilson score intervals. Leakage-prone timing is (i) or (ii). For (i), the order is either '
          'stated in words or follows from the described pipeline, as set out in the coding rules.',
          size='\\footnotesize')


if __name__ == '__main__':
    for p in SRC.values():
        assert p.exists(), p
    TAB.mkdir(exist_ok=True), SI.mkdir(exist_ok=True)
    table1_performance()
    table2_conditioning()
    si_baselines_city()
    si_g1()
    si_g2()
    si_e1()
    si_e7()
    si_c2()
    si_literature()
    si_lit_summary()
