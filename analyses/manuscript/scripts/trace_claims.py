"""Recompute every number quoted in the manuscript from the result files of this repository.

Each claim has a manuscript location (section, and the Supplementary table label where one carries it), the value as
printed, the value recomputed here, the file it comes from and, for derived numbers, the formula. A number is DIRECT
when a result file prints it and DERIVED when it is computed here from files that do not print it (a share of a gain,
a count over cities, a difference of two printed values). The script writes

  manuscript/outputs/trace_claims.csv   one row per claim, with the printed and the recomputed value
  manuscript/outputs/derived_numbers.txt every derived number with its inputs
  TRACEABILITY.md                       the table of claims by manuscript section

and exits with an error if any recomputed value differs from the printed one. Run it from the repository root:

  python analyses/manuscript/scripts/trace_claims.py

`--manuscript DIR` additionally checks that each printed value appears in DIR/main.tex or DIR/supplementary.tex.
Rounding: a printed value matches when it equals the recomputed one rounded to the printed number of decimals.
Bounds ("at least", "below") are checked strictly.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get('REPO_ROOT', HERE.parents[2]))
OUT = Path(os.environ.get('TRACE_OUT', HERE.parent / 'outputs'))
MD = Path(os.environ.get('TRACE_MD', REPO / 'analyses' / 'TRACEABILITY.md'))

R = 'results/02_r1_ext/reports'
R0 = 'results/02_r1/reports'
G = 'results/04_followups/reports'
BG = 'results/03_bg_check/bg_check_summary_lb7.csv'
B1 = 'results/01_baselines/phase1_colab_comparison_metrics.csv'
BL = 'analyses/baselines/outputs'
X1 = 'analyses/x1_shap_recheck/outputs'
EV = 'analyses/e1_verification/outputs'
T6 = EV + '/c2_runs/T6'
DC = 'analyses/dataset_check/outputs'
LC = 'analyses/literature_count/outputs'
DEC = 'analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar'


def csv_(p: str, **kw) -> pd.DataFrame:
    return pd.read_csv(REPO / p, **kw)


def jsn(p: str):
    return json.loads((REPO / p).read_text(encoding='utf-8'))


def txt(p: str) -> str:
    return (REPO / p).read_text(encoding='utf-8')


# --------------------------------------------------------------------------------------------------------------------
CLAIMS: list[dict] = []
DERIVED: list[str] = []
NAMES = ['Delhi', 'Mumbai', 'Bengaluru']


def _num(s) -> float | None:
    try:
        return float(str(s).replace(',', '').replace('−', '-'))
    except ValueError:
        return None


def _match(printed, value, kind: str) -> bool:
    p = _num(printed)
    if p is None or isinstance(value, (str, bool, np.bool_)):
        return str(value) == str(printed)
    s = str(printed).replace(',', '')
    dec = len(s.split('.')[1]) if '.' in s else 0
    v = float(value)
    if kind == 'atleast':
        return v >= p
    if kind == 'below':
        return v < p
    return abs(v - p) <= 0.5 * 10 ** -dec + 1e-9


def add(where: str, si: str, claim: str, printed, value, src: str, how: str = '', kind: str = 'direct',
        bound: str = '') -> None:
    """One claim. kind is 'direct' or 'derived'. bound is '', 'atleast' or 'below' for inequality statements."""
    ok = _match(printed, value, bound)
    shown = value if isinstance(value, (str, bool, np.bool_)) else (f'{float(value):.6g}')
    CLAIMS.append(dict(where=where, si=si, claim=claim, printed=str(printed), recomputed=str(shown), ok=bool(ok),
                       kind=kind, source=src, how=how))
    if kind == 'derived':
        DERIVED.append(f'{claim}: printed {printed}, recomputed {shown}. {how} [{src}]')


def rng(where, si, claim, lo, hi, values, src, how='', kind='direct') -> None:
    values = list(values)
    add(where, si, claim + ' (lowest)', lo, min(values), src, how, kind)
    add(where, si, claim + ' (highest)', hi, max(values), src, how, kind)


def msd(where, si, claim, mean, sd, m, s, src, how='', kind='direct') -> None:
    add(where, si, claim + ' (mean)', mean, m, src, how, kind)
    add(where, si, claim + ' (s.d.)', sd, s, src, how, kind)


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


# sections of the manuscript
ABS = 'Abstract'
R1S = 'Results: A leakage-free evaluation on common dates'
R2S = 'Results: Decomposition adds no accuracy and persistence is a strong reference'
R3S = 'Results: Past PM2.5 dominates AQI attribution'
R4S = 'Results: Attribution to past AQI depends on representation and training'
R5S = 'Results: Whole-record decomposition inflates timescale attribution'
R6S = 'Results: Modes can receive attribution without passing a skill test'
R7S = 'Results: Observed weather improves a diagnostic of short-timescale AQI variation'
DIS = 'Discussion'
M1, M2, M3 = 'Methods: Data and target', 'Methods: Calendar windows and missingness', 'Methods: Past-only decomposition'
M5, M6 = 'Methods: Comparators and reference forecasts', 'Methods: Sensitivity analyses'
M7, M8 = 'Methods: Leakage contrast', 'Methods: Official bulletin analysis'
M9, M10 = 'Methods: Weather diagnostic', 'Methods: Literature sample'


# --------------------------------------------------------------------------------------------------------------------
def section_data() -> None:
    da = csv_(EV + '/data_audit.csv')
    mod = da[da.train > 0]
    src = EV + '/data_audit.csv'
    add(R1S, 'tab:coverage', 'Cities in the source file', '26', len(da), src, 'rows of the audit')
    add(R1S, 'tab:coverage', 'Cities meeting the submitted-analysis minimum-history criterion (307 observed AQI days)',
        '20', int((da.valid_aqi >= 307).sum()), src, 'valid_aqi >= 307', 'derived')
    add(R1S, 'tab:windows', 'Modelled cities (at least one eligible training window)', '18', len(mod), src,
        'train > 0', 'derived')
    add(R1S, 'tab:coverage', 'Cities kept in the coverage audit without an eligible training window', 'Coimbatore, Guwahati',
        ', '.join(sorted(da[(da.valid_aqi >= 307) & (da.train == 0)].city)), src, 'valid_aqi >= 307 and train == 0',
        'derived')
    for lab, col, pr in (('training', 'train', '11,569'), ('validation', 'validation', '1,510'), ('test', 'test', '6,171')):
        add(R1S + ' | ' + M2, 'tab:windows', f'Windows, {lab} (lookback 7)', pr, int(mod[col].sum()), src,
            f'sum of {col} over the 18 modelled cities', 'derived')
    add(R1S + ' | ' + M3, 'tab:windows', 'Retained forecast origins (training + validation + test)', '19,250',
        int(mod[['train', 'validation', 'test']].sum().sum()), src, '11,569 + 1,510 + 6,171', 'derived')
    pa = jsn(EV + '/prefix_audit.json')
    add(R1S + ' | ' + M2, '', 'Origins whose availability mask differs when recomputed from the calendar prefix', '0',
        sum(pa['mask_mismatches'].values()), EV + '/prefix_audit.json', 'sum over train, validation, test', 'derived')
    add(R1S + ' | Supplementary Note S1', '', 'Test windows whose final input day uses a short-gap-filled AQI value', '59',
        pa['filled_origins']['test'], EV + '/prefix_audit.json')
    add(R1S, '', 'Same count from the data audit', '59', int(mod.test_filled_origin.sum()), src,
        'sum of test_filled_origin over the 18 modelled cities', 'derived')
    add(M1, '', 'Rows of city_day.csv', '29,531', int(da.raw_rows.sum()), src, 'sum of raw_rows over 26 cities', 'derived')
    csv_bytes = (REPO / 'data' / 'city_day.csv').read_bytes().replace(b'\r\n', b'\n')
    add('Supplementary Note S2', '', 'SHA-256 of city_day.csv after converting line endings to LF',
        '0d84b21c3e4878bbad8df362f2ab05f61ad959538dddf5918e714077ed3c1847', hashlib.sha256(csv_bytes).hexdigest(),
        'data/city_day.csv', 'hashlib.sha256 over the LF-converted bytes', 'derived')
    n_comp = [np.load(f)['n_components'] for f in sorted((REPO / DEC).glob('*.npz'))]
    n_days = [len(np.load(f)['days']) for f in sorted((REPO / DEC).glob('*.npz'))]
    add(M3, '', 'Decomposed city-days', '20,070', int(sum(n_days)), DEC + '/*.npz', 'sum of len(days) over 18 files',
        'derived')
    add(M3 + ' | Discussion', '', 'Fewest components returned on a day', '5', int(min(c.min() for c in n_comp)),
        DEC + '/*.npz', 'min of n_components', 'derived')
    add(M3 + ' | Discussion', '', 'Most components returned on a day', '9', int(max(c.max() for c in n_comp)),
        DEC + '/*.npz', 'max of n_components', 'derived')
    add('Supplementary Note S1 | Discussion', 'tab:windows', 'Test windows with a compressed decomposition history (count)',
        '2,427', int(mod.test_history_compressed.sum()), src, 'sum over the 18 modelled cities', 'derived')
    add('Supplementary Note S1 | Discussion', '', 'Share of the 6,171 test windows with a compressed history (%)', '39.3',
        100 * mod.test_history_compressed.sum() / mod.test.sum(), src, '2,427 / 6,171', 'derived')
    add('Supplementary Note S1', '', 'Longest decomposition history in calendar days', '532',
        int(mod.max_test_history_span.max()), src, 'max of max_test_history_span')
    add(M2 + ' | Supplementary Note S1', 'tab:coverage', 'Modelled cities with at least 80% of 14-day windows retained',
        '13', int((mod.eligible14_pct >= 80).sum()), src, 'eligible14_pct >= 80', 'derived')
    g1 = csv_(G + '/shap/g1_shap18_summary_lb7.csv')
    add(M2 + ' | Results 3', 'tab:s_g1', 'Same screen as used for the 13 interpreted cities', '13',
        int(g1.passes_completeness.sum()), G + '/shap/g1_shap18_summary_lb7.csv', 'sum of passes_completeness', 'derived')
    add('Supplementary Note S1', '', 'Cities that fail the screen',
        'Ahmedabad, Brajrajnagar, Jorapokhar, Talcher, Visakhapatnam',
        ', '.join(sorted(g1[~g1.passes_completeness].city)), G + '/shap/g1_shap18_summary_lb7.csv',
        'passes_completeness is False', 'derived')

    t8 = csv_(R + '/table8_channel_periods.csv')
    med = t8.pivot(index='city', columns='channel', values='median_d')
    for ch, lo, hi in (('IMF1', '3.2', '3.7'), ('IMF2', '6.7', '7.7'), ('IMF3', '14.6', '18.2'), ('IMF4', '33.1', '42.8')):
        rng(R1S, 'tab:periods0', f'Median zero-crossing scale of {ch} across the 18 cities', lo, hi, med[ch],
            R + '/table8_channel_periods.csv', 'min and max over cities of median_d', 'derived')
    chans = ['IMF1', 'IMF2', 'IMF3', 'IMF4', 'IMF5+ (slow)']
    p5 = t8.pivot(index='city', columns='channel', values='p5_d')
    p95 = t8.pivot(index='city', columns='channel', values='p95_d')
    gaps = all((p95[a] < p5[b]).all() for a, b in zip(chans[:-1], chans[1:]))
    add(R1S, 'tab:periods1', "The 5th to 95th percentile range of one channel never overlaps the next, in any city", 'True',
        gaps, R + '/table8_channel_periods.csv', 'p95_d of channel k < p5_d of channel k+1, all cities and channels',
        'derived')
    add(R1S, 'tab:periods1', 'Cities where the slow channel reaches the 364-step limit at its 95th percentile', '13',
        int((p95['IMF5+ (slow)'] >= 364).sum()), R + '/table8_channel_periods.csv', 'p95_d >= 364', 'derived')


def section_accuracy() -> None:
    v2 = csv_(R + '/comparison_v2_full.csv')
    v2 = v2[v2.lookback == 7].set_index('model')
    p1 = csv_(B1).set_index('label')
    ms = csv_(R + '/multiseed_summary_lb7.csv').set_index('model')
    bp = csv_(BL + '/baselines_pooled.csv').set_index(['forecast', 'subset'])
    sk = csv_(BL + '/baselines_skill.csv')
    bc = csv_(BL + '/baselines_city.csv')
    S = R2S + ' | Table 1'
    m = v2.loc['CEEMDAN+iTransformer-v2']
    f1, f2 = R + '/comparison_v2_full.csv', B1
    add(S, 'tab:performance', 'Augmented model, seed 123, test R2', '0.833', m.r2, f1)
    add(S, 'tab:performance', 'Augmented model, seed 123, RMSE', '46.06', m.rmse, f1)
    add(S, 'tab:performance', 'Augmented model, seed 123, MAE', '27.98', m.mae, f1)
    add(S, 'tab:performance', 'XGBoost test R2', '0.855', p1.loc['XGBoost-LB7', 'R2'], f2)
    add(S, 'tab:performance', 'Keras LSTM test R2', '0.844', p1.loc['LSTM-LB7', 'R2'], f2)
    add(S, 'tab:performance', 'PyTorch LSTM test R2', '0.840', v2.loc['LSTM', 'r2'], f1)
    add(S, 'tab:performance', 'DLinear test R2', '0.833', p1.loc['DLinear-LB7', 'R2'], f2)
    key = {'aug': 'CEEMDAN+iTransformer-v2 (proposed)', 'plain': 'iTransformer (plain)',
           'abl': '13ch ablation (12 pollutants + lagged AQI)'}
    f3 = R + '/multiseed_summary_lb7.csv'
    for k, (pm, ps) in {'aug': (('0.821', '0.014')), 'plain': ('0.819', '0.017'), 'abl': ('0.821', '0.034')}.items():
        label = {'aug': 'augmented model', 'plain': 'plain iTransformer', 'abl': 'raw-history ablation'}[k]
        msd(S, 'tab:performance', f'Five-seed test R2, {label}', pm, ps, ms.loc[key[k], 'mean_r2'],
            ms.loc[key[k], 'std_r2'], f3)
    g2m = csv_(G + '/g2_models_lb7.csv')
    an = csv_(G + '/g2_anova_lb7.csv')
    pr = an[(an.scope == 'pooled') & (an.quantity == 'test_r2')].iloc[0]
    add(S, 'tab:s_g2', 'Test R2 over four CEEMDAN realisations x five model seeds (20 models), mean', '0.821',
        g2m.test_r2.mean(), G + '/g2_models_lb7.csv', 'mean over the 20 models', 'derived')
    add(S, 'tab:s_g2', 'Same, the number after the plus-minus sign: the within-realisation (model-seed) s.d.', '0.017',
        pr.sd_within, G + '/g2_anova_lb7.csv', 'sd_within of the pooled test_r2 row. The s.d. over all 20 models is '
        f'{g2m.test_r2.std():.3f} (sd_all)', 'direct')
    add(S, 'tab:s_g2', 'F test of the realisation effect on test R2, F(3,16)', '0.24', pr.F, G + '/g2_anova_lb7.csv')
    add(S, 'tab:s_g2', 'p value of that test', '0.866', pr.p_value, G + '/g2_anova_lb7.csv')

    per = bp.loc[('Persistence', 'all')]
    add(S + ' | Discussion', 'tab:performance', 'Persistence test R2', '0.790', per.r2, BL + '/baselines_pooled.csv')
    add(S + ' | Discussion', 'tab:performance', 'Persistence MAE', '23.86', per.mae, BL + '/baselines_pooled.csv')
    seeds = [123, 42, 2024, 7, 2025]
    rm = np.array([bp.loc[(f'Main model seed {s}', 'all'), 'rmse'] for s in seeds])
    rskill = 1 - rm / per.rmse
    msd(S, '', 'RMSE skill of the augmented model against persistence', '0.078', '0.036', rskill.mean(), rskill.std(ddof=1),
        BL + '/baselines_pooled.csv', '1 - RMSE(model seed) / RMSE(persistence), over the five seeds. The skill file '
        'lists MAE skill only', 'derived')
    msd(S, 'tab:performance', 'Five-seed MAE of the augmented model', '28.71', '2.62', ms.loc[key['aug'], 'mean_mae'],
        ms.loc[key['aug'], 'std_mae'], f3)
    s_all = sk[(sk.baseline == 'Persistence') & (sk.subset == 'all')].skill
    msd(S, '', 'MAE skill against persistence over five seeds', '-0.203', '0.110', s_all.mean(), s_all.std(),
        BL + '/baselines_skill.csv', 'mean and s.d. of skill over the five seeds', 'derived')
    add(S + ' | Discussion', 'tab:s_baselines_city', 'Cities where the five-seed mean MAE is below persistence', '1',
        int((bc.model_mae_mean < bc.persistence_mae).sum()), BL + '/baselines_city.csv',
        'count of model_mae_mean < persistence_mae', 'derived')
    add(S, 'tab:s_baselines_city', 'That city', 'Delhi', ', '.join(bc[bc.model_mae_mean < bc.persistence_mae].city),
        BL + '/baselines_city.csv', '', 'derived')
    s_pre = sk[(sk.baseline == 'Persistence') & (sk.subset == 'pre-lockdown')].skill
    msd(S, 'tab:periodperformance', 'MAE skill before 25 March 2020', '-0.048', '0.076', s_pre.mean(), s_pre.std(),
        BL + '/baselines_skill.csv', 'subset pre-lockdown', 'derived')
    rng(S, 'tab:periodperformance', 'MAE skill before 25 March 2020, over seeds', '-0.121', '0.067', s_pre,
        BL + '/baselines_skill.csv', 'min and max over seeds', 'derived')
    msd(S, 'tab:performance', 'MAE after 25 March 2020 (augmented model, five seeds)', '27.32', '4.07',
        ms.loc[key['aug'], 'mean_mae_lock'], ms.loc[key['aug'], 'std_mae_lock'], f3)
    add(S, 'tab:performance', 'MAE after 25 March 2020 (persistence)', '12.98', bp.loc[('Persistence', 'lockdown/Unlock'), 'mae'],
        BL + '/baselines_pooled.csv')
    add(S + ' | Discussion', 'tab:performance', 'Seasonal climatology test R2', '0.212', bp.loc[('Climatology', 'all'), 'r2'],
        BL + '/baselines_pooled.csv')
    add(S, 'tab:performance', 'XGBoost MAE (the only model with a lower MAE than persistence)', '23.24',
        p1.loc['XGBoost-LB7', 'MAE'], f2)
    rows_t1 = {'XGBoost': (p1.loc['XGBoost-LB7', 'R2'], p1.loc['XGBoost-LB7', 'MAE']),
               'LSTM (Keras)': (p1.loc['LSTM-LB7', 'R2'], p1.loc['LSTM-LB7', 'MAE']),
               'LSTM (PyTorch)': (v2.loc['LSTM', 'r2'], v2.loc['LSTM', 'mae']),
               'Augmented model': (m.r2, m.mae),
               'DLinear': (p1.loc['DLinear-LB7', 'R2'], p1.loc['DLinear-LB7', 'MAE']),
               'Plain iTransformer': (v2.loc['iTransformer', 'r2'], v2.loc['iTransformer', 'mae']),
               'NLinear': (p1.loc['NLinear-LB7', 'R2'], p1.loc['NLinear-LB7', 'MAE']),
               'CEEMDAN+LSTM': (v2.loc['CEEMDAN+LSTM', 'r2'], v2.loc['CEEMDAN+LSTM', 'mae'])}
    add(S + ' | Discussion', 'tab:performance', 'Every model in Table 1 has a higher R2 than persistence', 'True',
        all(r2 > per.r2 for r2, _ in rows_t1.values()), 'Table 1 sources', 'R2 of each single-run row > 0.790', 'derived')
    add(S, 'tab:performance', 'Only XGBoost has a lower MAE than persistence', 'XGBoost',
        ', '.join(k for k, (_, mae) in rows_t1.items() if mae < per.mae), 'Table 1 sources',
        'single-run rows with MAE < 23.86', 'derived')

    lb = jsn(R + '/r113_lookback_selection.json')['val_r2']
    for L, pr_ in (('7', '0.8036'), ('14', '0.7794'), ('21', '0.7716'), ('30', '0.7817')):
        add(S, 'tab:lookback', f'Validation R2 at lookback {L}', pr_, lb[L], R + '/r113_lookback_selection.json')

    g1 = csv_(G + '/shap/g1_shap18_summary_lb7.csv').set_index('city')
    S2 = 'Results: Decomposition adds no accuracy | tab:cityaccuracy'
    add(S2, 'tab:cityaccuracy', 'City-level test R2, lowest (Thiruvananthapuram)', '0.082', g1.test_r2.min(),
        G + '/shap/g1_shap18_summary_lb7.csv')
    add(S2, 'tab:cityaccuracy', 'City-level test R2, highest (Delhi)', '0.917', g1.test_r2.max(),
        G + '/shap/g1_shap18_summary_lb7.csv')
    add(S2, 'tab:cityaccuracy', 'City-level test R2, median over 18 cities', '0.634', g1.test_r2.median(),
        G + '/shap/g1_shap18_summary_lb7.csv', 'median of test_r2', 'derived')
    add(S2, 'tab:cityaccuracy', 'Cities with test R2 below 0.5', 'Amaravati, Bengaluru, Chennai, Thiruvananthapuram',
        ', '.join(sorted(g1[g1.test_r2 < 0.5].index)), G + '/shap/g1_shap18_summary_lb7.csv', 'test_r2 < 0.5', 'derived')
    for c, pr_ in (('Chennai', '0.378'), ('Amaravati', '0.404'), ('Bengaluru', '0.496')):
        add(R3S, 'tab:cityaccuracy', f'Test R2 in {c}', pr_, g1.loc[c, 'test_r2'], G + '/shap/g1_shap18_summary_lb7.csv')
    # pooled standard deviation of the observed AQI, from the persistence row: R2 = 1 - MSE / var
    for sub, pr_ in (('pre-lockdown', '125.8'), ('lockdown/Unlock', '39.7')):
        r = bp.loc[('Persistence', sub)]
        add(S2, 'tab:performance', f'Pooled standard deviation of observed AQI, {sub}', pr_, r.rmse / math.sqrt(1 - r.r2),
            BL + '/baselines_pooled.csv', 'RMSE / sqrt(1 - R2) of the persistence row (the evaluated subset\'s own s.d.)',
            'derived')
    add(S2, 'tab:performance', 'Augmented model R2 after 25 March 2020, five seeds (mean)', '-0.151',
        ms.loc[key['aug'], 'mean_r2_lock'], f3)
    add(S2, 'tab:performance', 'Augmented model R2 after 25 March 2020, five seeds (s.d.)', '0.259',
        ms.loc[key['aug'], 'std_r2_lock'], f3)

    # city conditioning
    g3 = csv_(G + '/g3_conditioning_summary_lb7.csv').set_index('conditioning')
    msd(R2S, 'tab:conditioning', 'Test R2 without the city term', '0.837', '0.020', g3.loc['none', 'mean_test_r2'],
        g3.loc['none', 'std_test_r2'], G + '/g3_conditioning_summary_lb7.csv')
    msd(R2S, 'tab:conditioning', 'Test R2 with the scalar bias', '0.821', '0.014', g3.loc['bias', 'mean_test_r2'],
        g3.loc['bias', 'std_test_r2'], G + '/g3_conditioning_summary_lb7.csv')
    w = csv_(G + '/g3_city_wins_lb7.csv').set_index('arm')
    add(R2S, 'tab:conditioning', 'Cities where the no-city-term model has the lower mean MAE', '15',
        w.loc['none', 'cities_lower_mean_mae'], G + '/g3_city_wins_lb7.csv')
    z = np.load(REPO / G / 'g3_test_predictions_lb7.npz')
    late = z['test_dates'] >= np.datetime64('2020-03-25')
    me = {arm: np.mean([(z[f'pred__{arm}__{s}'][late] - z['y_test'][late]).mean() for s in seeds]) for arm in ('bias', 'none', 'scale_bias', 'vector_bias')}
    me_sd = {arm: np.std([(z[f'pred__{arm}__{s}'][late] - z['y_test'][late]).mean() for s in seeds], ddof=1)
             for arm in me}
    add(R2S, 'tab:conditioning', 'Mean forecast error after 25 March 2020, scalar-bias model (AQI units)', '18.1', me['bias'],
        G + '/g3_test_predictions_lb7.npz', 'mean of (forecast - observed) over the 1,669 windows from 25 March 2020, '
        'averaged over the five seeds. Table 2 prints it (column Mean error after, from make_tables.py), the same predictions '
        'reproduce its MAE-after column', 'derived')
    add(R2S, 'tab:conditioning', 'Mean forecast error after 25 March 2020, no-city-term model (AQI units)', '9.0', me['none'],
        G + '/g3_test_predictions_lb7.npz', 'same for the no-city-term arm', 'derived')
    for arm, lab, m_, s_ in (('scale_bias', 'city scale and bias', '17.0', '6.8'), ('vector_bias', 'city vector and bias', '15.0', '10.0')):
        msd(R2S, 'tab:conditioning', f'Mean forecast error after 25 March 2020, {lab} (AQI units)', m_, s_, me[arm], me_sd[arm],
            G + '/g3_test_predictions_lb7.npz', 'same for this arm', 'derived')
    add(R2S, 'tab:conditioning', 'Mean forecast error after 25 March 2020, scalar-bias model (s.d. over seeds)', '6.4', me_sd['bias'],
        G + '/g3_test_predictions_lb7.npz', 'Table 2, column Mean error after', 'derived')
    add(R2S, 'tab:conditioning', 'Mean forecast error after 25 March 2020, no-city-term model (s.d. over seeds)', '4.1', me_sd['none'],
        G + '/g3_test_predictions_lb7.npz', 'Table 2, column Mean error after', 'derived')
    s2 = csv_(R + '/s2_summary_lb7.csv').set_index('arm')
    f4 = R + '/s2_summary_lb7.csv'
    add(R2S, 'tab:gaps', 'Shared test targets of the three window constructions', '5,828', int(s2.loc['d1b', 'common_n']), f4)
    msd(R2S, 'tab:gaps', 'Test R2, calendar days with short-gap filling (shared targets)', '0.828', '0.015',
        s2.loc['d1b', 'mean_common_r2'], s2.loc['d1b', 'std_common_r2'], f4)
    msd(R2S, 'tab:gaps', 'Test R2, calendar days without filling', '0.813', '0.029', s2.loc['d1a', 'mean_r2'],
        s2.loc['d1a', 'std_r2'], f4)
    msd(R2S, 'tab:gaps', 'Test R2, consecutive observations (shared targets)', '0.824', '0.011',
        s2.loc['steps', 'mean_common_r2'], s2.loc['steps', 'std_common_r2'], f4)
    ne = csv_(R0 + '/multiseed_summary_lb7.csv').set_index('model').loc[key['aug']]
    msd(R2S + ' | Supplementary Note S9', 'tab:gaps', 'Test R2 without the boundary extension', '0.791', '0.024', ne.mean_r2,
        ne.std_r2, R0 + '/multiseed_summary_lb7.csv', 'results/02_r1 is the run without the extension')
    ve = csv_(R + '/r116_conditioning_runs_lb7.csv')
    vn = csv_(R0 + '/r116_conditioning_runs_lb7.csv')
    add(R2S + ' | Supplementary Note S9', '', 'Mean validation R2 without the boundary extension', '0.787',
        vn[vn.conditioning == 'bias'].val_r2.mean(), R0 + '/r116_conditioning_runs_lb7.csv', 'mean over five seeds', 'derived')
    add(R2S + ' | Supplementary Note S9', '', 'Mean validation R2 with the boundary extension', '0.789',
        ve[ve.conditioning == 'bias'].val_r2.mean(), R + '/r116_conditioning_runs_lb7.csv', 'mean over five seeds',
        'derived')
    be = csv_(EV + '/i14_boundary_error.csv')
    be = be[be.channel.isin(['IMF1', 'IMF2', 'IMF3', 'IMF4'])].groupby('variant').rms_pct_of_history_sd.mean()
    add(M3, '', 'Boundary error of IMF1 to IMF4 on training dates, reduction by the autoregressive extension (%)', '18',
        100 * (1 - be['ar'] / be['none']), EV + '/i14_boundary_error.csv',
        '100 x (1 - mean error with the extension / mean error without), mean over IMF1 to IMF4, 3 cities x 20 dates. '
        'Produced by e1_verification/i14_boundary_error.py', 'derived')
    add(M3, '', 'Rule for adopting the extension: boundary-error reduction of at least (%)', '10', 100 * (1 - be['ar'] / be['none']),
        EV + '/i14_boundary_error.csv', 'the reduction exceeds the 10% threshold fixed before the run', 'derived',
        bound='atleast')

    fl = csv_(R + '/r33_s1_filled_lb7.csv').set_index('scope')
    add('Supplementary Note S9', 'tab:gaps', 'Test R2 of windows without filled AQI input days', '0.840',
        fl.loc['all cities', 'r2_observed'], R + '/r33_s1_filled_lb7.csv')
    add('Supplementary Note S9', 'tab:gaps', 'Test R2 of windows with filled AQI input days', '0.767',
        fl.loc['all cities', 'r2_filled'], R + '/r33_s1_filled_lb7.csv')
    add('Supplementary Note S9', 'tab:gaps', 'Windows with filled AQI input days', '343', int(fl.loc['all cities', 'n_filled']),
        R + '/r33_s1_filled_lb7.csv')
    add('Supplementary Note S9', 'tab:gaps', 'Test R2 of windows without filled days, cities with both kinds', '0.812',
        fl.loc['cities with both kinds', 'r2_observed'], R + '/r33_s1_filled_lb7.csv')
    add('Supplementary Note S9', 'tab:gaps', 'Windows without filled days, cities with both kinds', '2,525',
        int(fl.loc['cities with both kinds', 'n_observed']), R + '/r33_s1_filled_lb7.csv')
    add('Supplementary Note S3', 'tab:s_baselines_city', 'Climatology forecasts that fall back to the city training mean', '138',
        int(bc.clim_fallback.sum()), BL + '/baselines_city.csv', 'sum of clim_fallback', 'derived')
    add('Supplementary Note S3', 'tab:s_baselines_city', 'Cities with such fallbacks', '5', int((bc.clim_fallback > 0).sum()),
        BL + '/baselines_city.csv', 'count of clim_fallback > 0', 'derived')
    add('Supplementary Note S3', 'tab:s_baselines_city', 'Origins that are short-gap fills (persistence copies the value)', '59',
        int(bc.origin_filled.sum()), BL + '/baselines_city.csv', 'sum of origin_filled', 'derived')


# --------------------------------------------------------------------------------------------------------------------
def section_attribution() -> None:
    g1 = csv_(G + '/shap/g1_shap18_summary_lb7.csv').set_index('city')
    p13 = g1[g1.passes_completeness]
    src = G + '/shap/g1_shap18_summary_lb7.csv'
    add(R3S, 'tab:s_g1', 'Interpreted cities in which past PM2.5 has the highest attribution', '13',
        int((p13.leading_input == 'PM2.5').sum()), src, 'leading_input == PM2.5 among the 13', 'derived')
    add(R3S, 'tab:s_g1', 'Modelled cities in which PM2.5 leads', '17', int((g1.leading_input == 'PM2.5').sum()), src,
        'leading_input == PM2.5 among the 18', 'derived')
    add(R3S, 'tab:s_g1', 'The city where it does not', 'Ahmedabad', ', '.join(g1[g1.leading_input != 'PM2.5'].index), src,
        '', 'derived')
    rng(ABS + ' | ' + R3S, 'tab:s_g1', 'Share of attribution to the five decomposition channels, 13 cities', '14.5', '26.6',
        p13.decomposition_share_pct, src, 'min and max over the 13 interpreted cities', 'derived')
    rng(R3S, 'tab:s_g1', 'Share to IMF1 to IMF4, 13 cities', '1.40', '4.81', p13.imf1_4_share_pct, src, '', 'derived')
    rng(R3S, 'tab:s_g1', 'Slow channel share of the decomposition share, 13 cities', '74.7', '94.7',
        p13.slow_of_decomposition_pct, src, '', 'derived')
    add(DIS, 'tab:s_g1', 'IMF1 to IMF4 receive less than 5% in every interpreted city', '5', p13.imf1_4_share_pct.max(), src,
        'largest share over the 13 cities', 'derived', bound='below')
    span13 = p13.decomposition_share_pct.max() - p13.decomposition_share_pct.min()
    add(R4S, 'tab:s_g1', 'Span of the decomposition share across the 13 cities at one model seed (points)', '12.1', span13, src,
        'max - min of decomposition_share_pct over the 13 cities', 'derived')
    for c, a, b in (('Delhi', '24.0', '53.2'), ('Mumbai', '17.7', '41.6'), ('Bengaluru', '14.5', '35.5')):
        add(R4S + ' | Fig. 3a', 'tab:s_g1', f'{c}: share to the five decomposition channels', a,
            g1.loc[c, 'decomposition_share_pct'], src)
    ab = csv_(R + '/shap/shap_periods_ablation13ch_lb7.csv')
    ab = ab[ab.period == 'all'].set_index('city')
    for c, b in (('Delhi', '53.2'), ('Mumbai', '41.6'), ('Bengaluru', '35.5')):
        add(R4S + ' | Fig. 3a', '', f'{c}: share to the one raw AQI channel', b, ab.loc[c, 'non_pollutant_share_pct'],
            R + '/shap/shap_periods_ablation13ch_lb7.csv', 'non_pollutant_share_pct of the all-windows row')
    rk = csv_(R + '/shap/ablation13ch_vs_proposed_pollutant_ranking.csv')
    add(R4S, '', 'Spearman correlation of the pollutant ranking, raw channel against decomposition, each city', '0.972',
        float(rk.spearman_rho.min()), R + '/shap/ablation13ch_vs_proposed_pollutant_ranking.csv',
        'the three values are equal at 0.972')
    pv = csv_(R + '/shap/shap_v2_pm25_vs_aqi_lb7.csv').set_index('city')
    pa_ = csv_(R + '/shap/shap_v2_pm25_attribution_lb7.csv').set_index('city')
    for c, a in (('Delhi', '95.7'), ('Mumbai', '94.4'), ('Bengaluru', '94.9')):
        add(R4S + ' | Fig. 3a', '', f'{c}: PM2.5 history share when PM2.5 is the target', a, pv.loc[c, 'imf_share_pm25_pct'],
            R + '/shap/shap_v2_pm25_vs_aqi_lb7.csv')
    for c, a in (('Delhi', '31.7'), ('Mumbai', '21.2'), ('Bengaluru', '36.4')):
        sh = 100 * pa_.loc[c, ['IMF1', 'IMF2', 'IMF3', 'IMF4']].sum() / pa_.loc[c].sum()
        add(R4S + ' | Fig. 3a', '', f'{c}: IMF1 to IMF4 share when PM2.5 is the target', a, sh,
            R + '/shap/shap_v2_pm25_attribution_lb7.csv', 'sum of IMF1..IMF4 over the sum of all channels', 'derived')
    pm = csv_(R + '/multiseed_pm25_lb7.csv')
    msd(R4S, '', 'Test R2 of the PM2.5-target model over five seeds (17 cities)', '0.775', '0.010', pm.r2.mean(), pm.r2.std(),
        R + '/multiseed_pm25_lb7.csv', 'mean and s.d. of r2 over five seeds', 'derived')

    # prominent pollutant on bulletin days
    pp = csv_(DC + '/e7_prominent_pm25_test_year.csv')
    rng(R3S, '', 'Test-year bulletin days naming PM2.5 among the prominent pollutants (%)', '11.0', '97.0', pp.pm25_named_pct,
        DC + '/e7_prominent_pm25_test_year.csv')
    add(R3S, '', 'Cities with PM2.5 named on fewer than half of the days',
        'Amaravati, Amritsar, Jaipur, Mumbai, Thiruvananthapuram', ', '.join(sorted(pp[pp.pm25_named_pct < 50].city)),
        DC + '/e7_prominent_pm25_test_year.csv', 'pm25_named_pct < 50', 'derived')
    txt_ = txt(DC + '/ahmedabad_co_no.txt')
    add(R3S + ' | Supplementary Note S2', '', 'Ahmedabad days with CO equal to NO, 1 January 2015 to 9 April 2020', '1,317',
        int(re.search(r'CO == NO on ([\d,]+) days', txt_).group(1).replace(',', '')), DC + '/ahmedabad_co_no.txt')
    gd = txt(DC + '/gd_ahmedabad_check/gd_summary.txt')
    add(R3S + ' | Supplementary Note S2', '', 'Change in the MAE of the other 17 cities without Ahmedabad (%)', '-9.9',
        float(re.search(r'change ([-\d.]+)%', txt_).group(1)), DC + '/ahmedabad_co_no.txt')
    add(R3S + ' | Supplementary Note S2', '', 'Welch p value of that check across ten seeds', '6.5e-05',
        float(re.search(r'p ([\d.e-]+)', txt_).group(1)), DC + '/ahmedabad_co_no.txt')

    # attribution by period
    pr = csv_(G + '/shap/g1_shap18_periods_lb7.csv')
    shapcols = ['PM2.5', 'PM10', 'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3', 'Benzene', 'Toluene', 'Xylene', 'IMF1', 'IMF2',
                'IMF3', 'IMF4', 'IMF5+ (slow)']
    diffs, lead_both = [], []
    for c in p13.index:
        a = pr[(pr.city == c) & (pr.period == 'pre_lockdown')].iloc[0]
        b = pr[(pr.city == c) & (pr.period == 'lockdown_unlock')].iloc[0]
        diffs.append(b.non_pollutant_share_pct - a.non_pollutant_share_pct)
        lead_both.append(all(r[shapcols].astype(float).idxmax() == 'PM2.5' for r in (a, b)))
    rng(R3S, '', 'Difference of the decomposition share between the two parts of the test year (points)', '-3.3', '5.1', diffs,
        G + '/shap/g1_shap18_periods_lb7.csv', 'lockdown_unlock minus pre_lockdown, per city, 13 cities', 'derived')
    add(R3S, '', 'Median of those differences (points)', '1.1', float(np.median(diffs)),
        G + '/shap/g1_shap18_periods_lb7.csv', '', 'derived')
    add(R3S, '', 'Cities where past PM2.5 leads in both periods', '13', int(sum(lead_both)),
        G + '/shap/g1_shap18_periods_lb7.csv', 'idxmax of the 17 channels is PM2.5 in both rows', 'derived')

    # realisations
    an = csv_(G + '/g2_anova_lb7.csv')
    sh = csv_(G + '/shap/g2_shap_lb7.csv')
    sh = sh[sh.period == 'all']
    s_ = an[an.quantity == 'decomposition_share_pct'].set_index('scope')
    rng(ABS + ' | ' + R4S, 'tab:s_g2', 'Decomposition share across the 20 models, lowest and highest over the three cities',
        '7.5', '34.2', list(s_['min']) + list(s_['max']), G + '/g2_anova_lb7.csv', 'min of min and max of max over cities',
        'derived')
    for c, lo, hi in (('Delhi', '7.5', '32.1'), ('Mumbai', '12.4', '34.2'), ('Bengaluru', '8.5', '31.5')):
        rng(R4S, 'tab:s_g2', f'{c}: decomposition share across 20 models', lo, hi, sh[sh.city == c].decomposition_share_pct,
            G + '/shap/g2_shap_lb7.csv', 'rows with period all')
    d = s_.loc['Delhi']
    add(R4S + ' | Discussion', 'tab:s_g2', 'Delhi: span of the decomposition share across the 20 models (points)', '24.6',
        d['max'] - d['min'], G + '/g2_anova_lb7.csv', 'max - min', 'derived')
    add(R4S, '', 'Ratio of that span to the 12.1-point span across cities (about twice)', '2.0',
        (d['max'] - d['min']) / span13_(), G + '/g2_anova_lb7.csv', '24.6 / 12.1', 'derived')
    rng(R4S, 'tab:s_g2', 'Model-seed s.d. of the decomposition share (points), three cities', '5.9', '7.0', s_.sd_within,
        G + '/g2_anova_lb7.csv', 'sd_within')
    rng(R4S, 'tab:s_g2', 'p values of the realisation effect on the decomposition share, three cities', '0.50', '0.71',
        s_.p_value, G + '/g2_anova_lb7.csv', 'p_value')
    add(R4S + ' | Discussion', '', 'City models (of 60) in which past PM2.5 has the highest attribution', '59',
        int((sh.leading_input == 'PM2.5').sum()), G + '/shap/g2_shap_lb7.csv', 'leading_input == PM2.5, 60 rows', 'derived')
    st = jsn(G + '/g2_statements_lb7.json')['min_spearman_rho_pollutants_vs_main']
    rng(R4S, '', 'Lowest rank correlation of a model\'s pollutant ranking with the main model, three cities', '0.78', '0.92',
        list(st.values()), G + '/g2_statements_lb7.json')
    pw = txt('analyses/followups/g2_power.txt')
    add(R4S, '', 'Realisation s.d. that the test detects with 80% probability, in units of the model-seed s.d.', '1.32',
        float(re.search(r'80%: realisation s\.d\. = ([\d.]+) x', pw).group(1)),
        'analyses/followups/g2_power.txt')
    # model-seed effect on one decomposition (Supplementary Note S6)
    rows = []
    for c in NAMES:
        x = sh[sh.city == c]
        diffs_c = []
        for dsd, g in x.groupby('decomposition_seed_base'):
            v = g.decomposition_share_pct.to_numpy()
            diffs_c += [abs(v[i] - v[j]) for i in range(len(v)) for j in range(i + 1, len(v))]
        rows.append((c, np.median(diffs_c), max(diffs_c)))
    for (c, med_, mx_), (a, b) in zip(rows, (('4.2', '24.6'), ('5.9', '21.1'), ('4.4', '23.0'))):
        add('Supplementary Note S6', 'tab:s_g2', f'{c}: median change of the share between two model seeds on one decomposition',
            a, med_, G + '/shap/g2_shap_lb7.csv', 'median of |difference| over the 10 model-seed pairs of each of the 4 '
            'decompositions', 'derived')
        add('Supplementary Note S6', 'tab:s_g2', f'{c}: largest such change', b, mx_, G + '/shap/g2_shap_lb7.csv', 'max of the '
            'same differences', 'derived')
    for c, a, b in (('Delhi', '24.0', '32.1'), ('Mumbai', '17.7', '26.9'), ('Bengaluru', '14.5', '19.4')):
        x = sh[(sh.city == c) & (sh.model_seed == 123)].set_index('decomposition_seed_base').decomposition_share_pct
        add('Supplementary Note S6', 'tab:s_g2', f'{c}: share with seed base 123 at model seed 123', a, x[123], G + '/shap/g2_shap_lb7.csv')
        add('Supplementary Note S6', 'tab:s_g2', f'{c}: share with seed base 42 at model seed 123', b, x[42], G + '/shap/g2_shap_lb7.csv')
    cs = csv_(R + '/c5_seed_stability.csv')
    sp = cs.groupby('channel').spread_pct.median()
    mx = cs.groupby('channel').max_diff_pct_of_sd.max()
    rng(R4S, '', 'Median relative period spread by channel (%), component diagnostic', '0.0', '6.3', sp,
        R + '/c5_seed_stability.csv', 'median over cities and dates of spread_pct, per channel', 'derived')
    rng(R4S, '', 'Largest difference of component values, % of the history s.d., by channel', '10.4', '29.6', mx,
        R + '/c5_seed_stability.csv', 'max over cities and dates of max_diff_pct_of_sd, per channel', 'derived')

    # lookback 30 and background
    l30 = csv_(R + '/shap/shap_periods_v2_lb30.csv')
    l30 = l30[l30.period == 'all'].set_index('city')
    for c, a in (('Delhi', '25.3'), ('Mumbai', '15.0'), ('Bengaluru', '10.7')):
        add(R4S, '', f'{c}: decomposition share at a 30-day lookback', a, l30.loc[c, 'non_pollutant_share_pct'],
            R + '/shap/shap_periods_v2_lb30.csv')
    bgd = csv_(BG)
    for c, lo, hi in (('Delhi', '23.1', '24.0'), ('Mumbai', '17.7', '18.7'), ('Bengaluru', '14.2', '14.6')):
        rng(R4S, 'tab:background', f'{c}: decomposition share over three backgrounds', lo, hi,
            bgd[bgd.city == c].decomposition_share_pct, BG, 'original, draw1, draw2')
    add(R4S, 'tab:background', 'Lowest rank correlation of the 17-channel attribution with the original background',
        '0.977', bgd[bgd.background != 'original'].spearman_rho_vs_original.min(), BG,
        'min over cities and the two new backgrounds. The minimum is 0.9779 (Delhi, draw1)', 'derived', bound='atleast')


def span13_() -> float:
    g1 = csv_(G + '/shap/g1_shap18_summary_lb7.csv')
    p = g1[g1.passes_completeness].decomposition_share_pct
    return round(float(p.max() - p.min()), 1)


# --------------------------------------------------------------------------------------------------------------------
def section_leakage_bulletins() -> None:
    acc = csv_(X1 + '/e1_accuracy.csv')
    sh = csv_(X1 + '/e1_shares.csv')
    a = acc.groupby('arm').agg(r2=('test_r2', 'mean'), r2sd=('test_r2', 'std'), rmse=('test_rmse', 'mean'))
    src = X1 + '/e1_accuracy.csv'
    for arm, mean, sd, lab in (('CAUSAL', '0.861', '0.001', 'past-only decomposition'), ('POL', '0.858', '0.005', 'pollutants only'),
                               ('RAW', '0.865', '0.003', 'raw history'), ('LEAKY', '0.943', '0.003', 'whole-record decomposition')):
        msd(R5S + ' | Discussion', 'tab:s_e1', f'Test R2, {lab} (XGBoost, three seeds)', mean, sd, a.loc[arm, 'r2'],
            a.loc[arm, 'r2sd'], src, 'mean and s.d. over seeds 0 to 2', 'derived')
    add(R5S, 'tab:s_e1', 'RMSE, past-only decomposition', '42.0', a.loc['CAUSAL', 'rmse'], src, 'mean over seeds', 'derived')
    add(R5S, 'tab:s_e1', 'RMSE, whole-record decomposition', '26.9', a.loc['LEAKY', 'rmse'], src, 'mean over seeds', 'derived')
    p = sh[sh.IMF1.notna()].copy()
    p['imf14'] = p[['IMF1', 'IMF2', 'IMF3', 'IMF4']].sum(axis=1)
    m = p.groupby('arm')[['imf14', 'Slow']].mean()
    s2 = X1 + '/e1_shares.csv'
    add(ABS + ' | ' + R5S, 'tab:s_e1', 'IMF1 to IMF4 share, past-only decomposition (%)', '3.9', m.loc['CAUSAL', 'imf14'], s2,
        'pooled-city rows (the rows that carry IMF columns), mean over seeds', 'derived')
    add(R5S, 'tab:s_e1', 'IMF1 to IMF4 share, whole-record decomposition (%)', '26.4', m.loc['LEAKY', 'imf14'], s2, '', 'derived')
    add(ABS + ' | ' + R5S + ' | Discussion', 'tab:s_e1', 'Ratio of the two shares', '6.8',
        m.loc['LEAKY', 'imf14'] / m.loc['CAUSAL', 'imf14'], s2, 'whole-record share / past-only share', 'derived')
    add('Supplementary Note S7', 'tab:s_e1', 'Slow channel share, past-only arm (%)', '49.2', m.loc['CAUSAL', 'Slow'], s2,
        'mean over seeds', 'derived')
    cities = sh[sh.arm.isin(['CAUSAL', 'LEAKY']) & sh.osc_share.notna()].groupby(['city', 'arm']).osc_share.mean()
    for c, lo, hi in (('Delhi', '4.8', '33.6'), ('Mumbai', '2.8', '21.8'), ('Bengaluru', '1.9', '12.2')):
        add(R5S + ' | Fig. 4a', 'tab:s_e1', f'{c}: IMF1 to IMF4 share, past-only', lo, cities[(c, 'CAUSAL')], s2,
            'mean over seeds of osc_share', 'derived')
        add(R5S + ' | Fig. 4a', 'tab:s_e1', f'{c}: IMF1 to IMF4 share, whole-record', hi, cities[(c, 'LEAKY')], s2,
            'mean over seeds of osc_share', 'derived')

    # official bulletins
    pool = csv_(X1 + '/e7_d2_pooled.csv')
    ver = txt(X1 + '/e7_d2_verdict.txt')
    add(R6S, '', 'Forecast origins decomposed for the bulletin analysis', '9,229',
        int(re.search(r'of ([\d,]+) origins', txt('analyses/dataset_check/E7_DECISION_RULES.md')).group(1).replace(',', '')),
        'analyses/dataset_check/E7_DECISION_RULES.md', 'the count of origins in the decision-rule document')
    mae = pool.groupby(['h', 'hist', 'year', 'arm']).mae.mean()
    sd = pool.groupby(['h', 'hist', 'year', 'arm']).mae.std()
    yrs = sorted(pool.year.unique())

    def gain(h, hist, base, arm):
        out = []
        for y in yrs:
            g = mae[(h, hist, y, base)] - mae[(h, hist, y, arm)]
            thr = 2 * max(sd[(h, hist, y, base)], sd[(h, hist, y, arm)])
            out.append((g, thr))
        return out
    g1l = gain(1, 'long', 'RAW+MAL', 'RAW+MAL+OSC')
    g7l = gain(7, 'long', 'RAW+MAL', 'RAW+MAL+OSC')
    src = X1 + '/e7_d2_pooled.csv'
    for h, gl in ((1, g1l), (7, g7l)):
        add(R6S, 'tab:s_e7', f'Years (of 7) in which adding the modes passes the rule beyond the 365-day memory, {h} day(s) ahead',
            '0', sum(g > t for g, t in gl), src, 'pooled MAE gain > 2 x larger seed s.d.', 'derived')
    add(R6S, 'tab:s_e7', 'Years (of 7) in which the modes lower the pooled MAE, 1 day ahead, with the 365-day memory', '5',
        sum(g > 0 for g, _ in g1l), src, 'MAE(RAW+MAL) - MAE(RAW+MAL+OSC) > 0', 'derived')
    add(R6S, 'tab:s_e7', 'Largest such reduction (AQI units)', '0.40', max(g for g, _ in g1l), src, '', 'derived')
    add(R6S, 'tab:s_e7', 'Years (of 7) in which the modes raise the pooled MAE, 7 days ahead', '7', sum(g < 0 for g, _ in g7l),
        src, 'MAE(RAW+MAL) - MAE(RAW+MAL+OSC) < 0', 'derived')
    for h in (1, 7):
        gm = gain(h, 'long', 'RAW+MA', 'RAW+MA+OSC')
        add(R6S, 'tab:s_e7', f'Years (of 7) passing the rule without the 365-day memory, {h} day(s) ahead', '0',
            sum(g > t for g, t in gm), src, '', 'derived')
        gc = gain(h, 'clean', 'RAW+MA', 'RAW+MA+OSC')
        add(R6S, 'tab:s_e7', f'Years (of 7) passing the rule on gap-free histories without the memory, {h} day(s) ahead', '2',
            sum(g > t for g, t in gc), src, 'hist == clean', 'derived')
    po = pool[pool['hist'] == 'long'].groupby(['h', 'year', 'arm']).osc_share.mean()
    with_mem = po.xs('RAW+MAL+OSC', level='arm')
    only_dec = po.xs('DEC', level='arm')
    rng(ABS + ' | ' + R6S + ' | Discussion', 'tab:s_e7', 'Share given to IMF1 to IMF4 with the 365-day memory (%)', '9.4', '19.1', with_mem,
        src, 'mean over seeds of osc_share, all years and both horizons, hist == long', 'derived')
    rng(R6S + ' | Discussion', 'tab:s_e7', 'Share given to the modes when only the decomposition channels are given (%)', '16.7',
        '33.3', only_dec, src, 'arm DEC', 'derived')
    mr = re.search(r'h1: P2 False \(halves rho ([\d.]+) \(p ([\d.]+)', ver)
    mr7 = re.search(r'h7: P2 False \(halves rho ([\d.]+) \(p ([\d.]+)', ver)
    add(R6S, 'tab:s_e7', 'Spearman rho of per-city gains between the two halves, 1 day ahead', '0.51', float(mr.group(1)),
        X1 + '/e7_d2_verdict.txt')
    add(R6S, 'tab:s_e7', 'p value, 1 day ahead', '0.06', float(mr.group(2)), X1 + '/e7_d2_verdict.txt')
    add(R6S, 'tab:s_e7', 'Spearman rho, 7 days ahead', '0.47', float(mr7.group(1)), X1 + '/e7_d2_verdict.txt')
    add(R6S, 'tab:s_e7', 'p value, 7 days ahead', '0.09', float(mr7.group(2)), X1 + '/e7_d2_verdict.txt')
    d0 = csv_(DC + '/e7_d0_comparability.csv')
    add('Supplementary Note S2 | ' + R6S, '', 'Median Pearson r of bulletin against dataset AQI over 26 cities', '0.937',
        d0.r.median(), DC + '/e7_d0_comparability.csv', 'median of r', 'derived')
    add('Supplementary Note S2 | ' + R6S + ' | Discussion', '', 'Cities with r below 0.8', '5',
        int((d0.r < 0.8).sum()), DC + '/e7_d0_comparability.csv', 'r < 0.8', 'derived')
    add('Supplementary Note S2', '', 'Lowest r (Ahmedabad)', '0.540', d0.r.min(), DC + '/e7_d0_comparability.csv')


# --------------------------------------------------------------------------------------------------------------------
def section_weather() -> None:
    v = jsn(T6 + '/c2x_verdict.json')
    pri, sec = v['primary'], v['secondary']
    f = T6 + '/c2x_verdict.json'
    S = R7S + ' | Supplementary Note S8'
    add(S, 'tab:s_c2', 'H1: MAE lower than the controls (%)', '4.9', pri['H1']['pct'], f)
    rng(S, 'tab:s_c2', 'H1: 90% interval (%)', '3.6', '6.2', [pri['H1']['pct_lo'], pri['H1']['pct_hi']], f)
    add(S, 'tab:s_c2', 'P H1: weather known at the forecast origin, MAE lower (%)', '3.4', sec['P_H1']['pct'], f)
    rng(S, 'tab:s_c2', 'P H1: 90% interval (%)', '1.4', '5.3', [sec['P_H1']['pct_lo'], sec['P_H1']['pct_hi']], f)
    add(S, 'tab:s_c2', 'H2: excess attribution share of the short weather bands (points)', '3.5', pri['H2']['effect'], f)
    rng(S, 'tab:s_c2', 'H2: 90% interval (points)', '3.3', '3.6', [pri['H2']['lo'], pri['H2']['hi']], f)
    add(S, 'tab:s_c2', 'All three rules passed', 'pass, pass, pass', ', '.join(pri[k]['status'] for k in ('H1', 'H2', 'H1b')), f)
    arm = v['descriptive']['arm_means_all']
    base, pp, long_ = arm['BASE']['mae'], arm['MET_PP']['mae'], arm['MET_PP_LONG']['mae']
    add(S, '', 'Forecast-day weather against no weather: MAE lowered by (%)', '4.4', 100 * (base - pp) / base, f,
        '100 x (MAE of BASE - MAE of MET_PP) / MAE of BASE', 'derived')
    add(S, '', 'Same-season weather from other years produces no detectable MAE reduction against no weather', 'True',
        sec['weather_vs_none']['BASE_minus_POOL_PP']['p'] > 0.05, f,
        'one-sided p of BASE minus POOL_PP is above 0.05 (effect -0.122, p 0.87)', 'derived')
    add(S, '', 'Of the gain over no weather, the share in the bands shorter than 31 days (%)', '85.4',
        100 * (long_ - pp) / (base - pp), f,
        '100 x (MAE of MET_PP_LONG - MAE of MET_PP) / (MAE of BASE - MAE of MET_PP): the arm MET_PP_LONG keeps only the '
        'bands of 31 days and longer, so what it loses against MET_PP is what the short bands supply', 'derived')
    add(S, '', 'Share of IMF1 to IMF4 without weather (%)', '3.8', arm['BASE']['dec_osc'], f, 'arm_means_all, BASE', 'derived')
    add(S, '', 'Share of IMF1 to IMF4 with forecast-day weather (%)', '3.3', arm['MET_PP']['dec_osc'], f, 'arm_means_all, MET_PP',
        'derived')
    add(S, '', 'Pre-lockdown effect of weather against the controls (%)', '4.67', v['lockdown_check']['pct'], f, 'lockdown_check')
    bands = v['descriptive']['bands_and_variable_groups']
    exc = {k: bands[k]['real_mean'] - bands[k]['null_mean'] for k in ('met_disp', 'met_temp', 'met_hum', 'met_rain')
           if 'null_mean' in bands[k]}
    if exc:
        top2 = ', '.join(sorted(sorted(exc, key=exc.get, reverse=True)[:2]))
        add(S, '', 'Variable groups with the largest excess attribution share', 'met_disp, met_rain', top2, f,
            'real mean minus null mean of the share, groups dispersion, temperature, humidity, rain', 'derived')
    pc = v['descriptive']['per_city']
    keys = list(next(iter(pc.values())).keys())
    k_pp = [k for k in keys if k.startswith('MET_PP_vs_POOL_PP')][0]
    k_p = [k for k in keys if k.startswith('MET_vs_POOL')][0] if any(k.startswith('MET_vs_POOL') for k in keys) else None
    lo = lambda d: d.get('lo', d.get('lo90', None))
    sample = pc['Delhi'][k_pp]
    if lo(sample) is not None:
        add(S, '', 'Cities where the 90% interval of the weather effect lies above zero, forecast-day weather', '17',
            sum(lo(pc[c][k_pp]) > 0 for c in pc), f, 'lo > 0 per city', 'derived')
        if k_p:
            add(S, '', 'Same for weather up to the origin', '15', sum(lo(pc[c][k_p]) > 0 for c in pc), f, 'lo > 0 per city',
                'derived')
    else:
        CLAIMS.append(dict(where=S, si='', claim='Per-city interval counts (17 of 18, 15 of 18)', printed='17, 15',
                           recomputed=f'keys: {list(sample)}', ok=False, kind='derived', source=f, how='needs the interval key'))
    pro = v['provenance']
    add(R7S + ' | ' + M9, '', 'Arms fitted', '32', pro['arms'], f)
    add(M9, '', 'Seeds per arm', '40', len(v['seeds']), f)
    add(M9 + ' | Supplementary Note S8', '', 'Fits in total', '1,280', sum(pro['fits made on (addendum A2.3)'].values()), f)
    add(R7S, '', 'Threshold for repeating the test with the iTransformer (%)', '13', v['gate']['threshold_pct'], f)
    add(R7S, '', 'Effect compared with the threshold (%)', '4.9', v['gate']['g_pct'], f)
    add(M9, '', 'Marker that the run was reproduced byte for byte: pooled results of the three runs are identical', 'True',
        len({hashlib.sha256((REPO / EV / 'c2_runs' / d / 'c2x_pooled.csv').read_bytes()).hexdigest()
             for d in ('T6', 'T7', 'S1_wsl_i5')}) == 1, EV + '/c2_runs/{T6,T7,S1_wsl_i5}/c2x_pooled.csv',
        'SHA-256 of the three files is identical', 'derived')
    wk = csv_(EV + '/e4_weekly_cycle.csv')
    add('Supplementary Note S8', '', 'Cities with a significant weekly cycle in NO2 (q < 0.05)', '10',
        int((wk[wk['var'] == 'NO2'].q < 0.05).sum()), EV + '/e4_weekly_cycle.csv', 'q < 0.05 among the 18 cities', 'derived')
    add('Supplementary Note S8', '', 'Cities with a significant weekly cycle in AQI', '0', int((wk[wk['var'] == 'AQI'].q < 0.05).sum()),
        EV + '/e4_weekly_cycle.csv', '', 'derived')


# --------------------------------------------------------------------------------------------------------------------
def section_literature() -> None:
    fc = jsn(LC + '/flow_counts.json')
    scr = csv_(LC + '/screening_decisions.csv')
    order = csv_(LC + '/coding_order.csv')
    cs = csv_(LC + '/coding_sheet.csv')
    coded = cs[cs.status == 'CODED']
    S = M10 + ' | Supplementary Note S5'
    f = LC + '/flow_counts.json'
    add(S, 'tab:s_lit_summary', 'Records identified, OpenAlex', '371', fc['identified']['OpenAlex'], f)
    add(S, 'tab:s_lit_summary', 'Records identified, Scopus', '520', fc['identified']['Scopus'], f)
    add(S, 'tab:s_lit_summary', 'Records identified, total', '891', fc['identified']['total'], f)
    add(S, 'tab:s_lit_summary', 'Duplicates removed', '333', fc['duplicates_removed'], f)
    add(S, 'tab:s_lit_summary', 'Unique records screened', '558', len(scr), LC + '/screening_decisions.csv', 'rows', 'derived')
    add(S, 'tab:s_lit_summary', 'Excluded on title and abstract', '169', int((scr.decision == 'exclude').sum()),
        LC + '/screening_decisions.csv', '', 'derived')
    add(S, 'tab:s_lit_summary', 'Eligible after screening', '389', int((scr.decision == 'include').sum()),
        LC + '/screening_decisions.csv', '', 'derived')
    add(S, 'tab:s_lit_summary', 'Eligible with an open-access copy', '161', len(order), LC + '/coding_order.csv', 'rows', 'derived')
    add(S, 'tab:s_lit_summary', 'Records reached in the random order', '70', len(cs), LC + '/coding_sheet.csv', 'rows', 'derived')
    add(S, 'tab:s_lit_summary', 'Studies coded', '60', len(coded), LC + '/coding_sheet.csv', "status == 'CODED'", 'derived')
    add(S, 'tab:s_lit_summary', 'Not coded because the open copy did not open', '6',
        int((cs.status == 'SKIP-NOACCESS').sum()), LC + '/coding_sheet.csv', '', 'derived')
    add(S, 'tab:s_lit_summary', 'Not coded because the full text failed eligibility', '4',
        int(cs.status.str.startswith('SKIP').sum() - (cs.status == 'SKIP-NOACCESS').sum()), LC + '/coding_sheet.csv', '',
        'derived')
    for code, n in (('TOPIC', '86'), ('NONEN', '32'), ('NOFC', '22'), ('DESC', '17'), ('NODEC', '8'), ('DUP', '3'), ('REV', '1')):
        add('Supplementary Note S5', 'tab:s_lit_summary', f'Excluded on title and abstract, reason {code}', n,
            int((scr.code == code).sum()), LC + '/screening_decisions.csv', '', 'derived')
    t = coded.T3_timing.value_counts()
    k = int(t.get('i', 0))
    lo, hi = wilson(k, 60)
    W = R5S + ' | ' + ABS
    add(W + ' | Discussion', 'tab:s_lit_summary', 'Studies whose pipeline lets data after the forecast origin enter', '42', k,
        LC + '/coding_sheet.csv', "T3_timing == 'i'", 'derived')
    add(W + ' | Discussion', 'tab:s_lit_summary', 'Same, as a share of 60 (%)', '70', 100 * k / 60, LC + '/coding_sheet.csv', '', 'derived')
    add(R5S, 'tab:s_lit_summary', 'Wilson 95% interval, lower (%)', '57', 100 * lo, LC + '/coding_sheet.csv', 'Wilson score', 'derived')
    add(R5S, 'tab:s_lit_summary', 'Wilson 95% interval, upper (%)', '80', 100 * hi, LC + '/coding_sheet.csv', 'Wilson score', 'derived')
    add(R5S, 'tab:s_lit_coding', 'Of these, studies that state the order of decomposition and splitting in words', '3',
        int(((coded.T3_timing == 'i') & (coded.T3_explicit == 'yes')).sum()), LC + '/coding_sheet.csv',
        "T3_timing == 'i' and T3_explicit == 'yes'", 'derived')
    add(R5S, 'tab:s_lit_summary', 'Studies that did not state how the decomposition was applied', '13', int(t.get('v', 0)),
        LC + '/coding_sheet.csv', "T3_timing == 'v'", 'derived')
    add(R5S, 'tab:s_lit_summary', 'Same, as a share of 60 (%)', '22', 100 * int(t.get('v', 0)) / 60, LC + '/coding_sheet.csv', '', 'derived')
    add(R5S, 'tab:s_lit_summary', 'Studies that decomposed only data available at each forecast origin', '3', int(t.get('iii', 0)),
        LC + '/coding_sheet.csv', "T3_timing == 'iii'", 'derived')
    add(R5S, 'tab:s_lit_summary', 'Same, as a share of 60 (%)', '5', 100 * int(t.get('iii', 0)) / 60, LC + '/coding_sheet.csv', '', 'derived')
    add(R5S, 'tab:s_lit_summary', 'Studies that reported a non-decomposed version of the same model', '40',
        int((coded.T5_nodec_model == 'yes').sum()), LC + '/coding_sheet.csv', "T5_nodec_model == 'yes'", 'derived')
    add(R5S + ' | Discussion', 'tab:s_lit_summary', 'Studies that reported a persistence forecast', '1',
        int((coded.T6_persistence == 'yes').sum()), LC + '/coding_sheet.csv', "T6_persistence == 'yes'", 'derived')
    add(R5S, 'tab:s_lit_summary', 'Studies that applied an explanation method such as SHAP', '0',
        int((coded.T9_explanation != 'none').sum()), LC + '/coding_sheet.csv', "T9_explanation != 'none'", 'derived')
    lo0, hi0 = wilson(0, 60)
    add(R5S, 'tab:s_lit_summary', 'Wilson 95% interval of that share, upper (%)', '6', 100 * hi0, LC + '/coding_sheet.csv', 'Wilson score', 'derived')
    add(R5S, 'tab:s_lit_summary', 'Studies that read modes as physical drivers', '1', int((coded.T8_interpretation == 'yes').sum()),
        LC + '/coding_sheet.csv', "T8_interpretation == 'yes'", 'derived')
    add('Supplementary Note S5', 'tab:s_lit_summary', 'Leakage-prone studies published 2015 to 2020', '9',
        int(((coded.T3_timing == 'i') & (coded.rid.map(order.set_index('rid').year) <= 2020)).sum()),
        LC + '/coding_sheet.csv', "T3_timing == 'i', year from coding_order.csv", 'derived')
    add('Supplementary Note S5', 'tab:s_lit_summary', 'Studies published 2015 to 2020', '13',
        int((coded.rid.map(order.set_index('rid').year) <= 2020).sum()), LC + '/coding_sheet.csv', '', 'derived')
    add('Supplementary Note S5', 'tab:s_lit_summary', 'Leakage-prone studies published 2021 to 2025', '33',
        int(((coded.T3_timing == 'i') & (coded.rid.map(order.set_index('rid').year) >= 2021)).sum()),
        LC + '/coding_sheet.csv', '', 'derived')
    add('Supplementary Note S5', 'tab:s_lit_summary', 'Studies published 2021 to 2025', '47',
        int((coded.rid.map(order.set_index('rid').year) >= 2021).sum()), LC + '/coding_sheet.csv', '', 'derived')


# --------------------------------------------------------------------------------------------------------------------
def _nb_code(name: str) -> str:
    nb = json.loads((REPO / 'notebooks' / name).read_text(encoding='utf-8'))
    return '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')


def _last(code: str, name: str):
    """Value of the last top-level assignment `name = ...` in the code (a Python literal)."""
    import ast
    hits = re.findall(r'^' + re.escape(name) + r'\s*=\s*(.+?)\s*(?:#.*)?$', code, flags=re.M)
    return ast.literal_eval(hits[-1])


def section_settings() -> None:
    c5 = txt('analyses/tools/c5_helper_cell.py')
    f = 'analyses/tools/c5_helper_cell.py'
    for name, pr, lab in (('C5_W_MAX', '365', 'Longest decomposition history (available days)'),
                          ('C5_AR_MAX_ORDER', '14', 'Largest autoregressive order tried'),
                          ('C5_EXT_DAYS', '30', 'Autoregressive extension length (values)'),
                          ('C5_TRIALS', '100', 'CEEMDAN trials'), ('C5_EPSILON', '0.2', 'CEEMDAN noise amplitude'),
                          ('C5_MAX_IMF', '8', 'CEEMDAN maximum number of modes'),
                          ('C5_SEED_BASE', '123', 'CEEMDAN seed (plus the city position in the alphabetical list of 26)')):
        add(M3, '', lab, pr, _last(c5, name), f, 'constant in the helper cell that the notebooks execute')
    add(M3 + ' | ' + M2, '', 'Minimum available history (observations)', '180',
        _last(txt('analyses/tools/r19_helper_cell.py'), 'R11_MIN_HISTORY_DAYS'), 'analyses/tools/r19_helper_cell.py',
        'constant R11_MIN_HISTORY_DAYS')
    fn = 'notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb'
    nb = _nb_code('02_ceemdan_itransformer_shap_r1_ext.ipynb')
    add(M3, '', 'Extension used for the main results', 'ar', _last(nb, 'C5_MAIN_EXTENSION'), fn, 'constant C5_MAIN_EXTENSION')
    P = _last(nb, 'ITRANSFORMER_V2_PARAMS')
    S = 'Methods: Forecasting model'
    for k, pr, lab in (('n_layers', '6', 'encoder layers'), ('nhead', '8', 'attention heads'), ('d_model', '256', 'width'),
                       ('ff_dim', '1,024', 'feed-forward width'), ('dropout', '0.1', 'dropout')):
        add(S, '', f'Main model: {lab}', pr, P[k], fn, 'ITRANSFORMER_V2_PARAMS, last assignment in the notebook')
    for name, pr, lab in (('LEARNING_RATE_V2', '0.0005', 'learning rate'), ('WEIGHT_DECAY_V2', '0.000001', 'weight decay'),
                          ('BATCH_SIZE_V2', '32', 'batch size'), ('WARMUP_EPOCHS_V2', '10', 'warm-up epochs'),
                          ('EPOCHS_V2', '200', 'maximum epochs'), ('PATIENCE_V2', '20', 'early-stopping patience')):
        add(S, '', f'Main model: {lab}', pr, _last(nb, name), fn, f'{name}, last assignment in the notebook')
    add(S, '', 'Model seeds', '7, 42, 123, 2024, 2025', ', '.join(str(s) for s in sorted(_last(nb, 'SEEDS'))), fn, 'constant SEEDS')
    add(M5, '', 'Plain iTransformer: width 64, four heads, feed-forward 256, two layers', 'True',
        re.search(r"'d_model': 64, 'nhead': 4, 'ff_dim': 256,\s*'n_layers': 2", nb) is not None, fn,
        'parameter dictionary of the plain iTransformer')
    add('Methods: Channel-level KernelSHAP', '', 'Background windows per city', '50', _last(nb, 'SHAP_N_BACKGROUND'), fn,
        'SHAP_N_BACKGROUND')
    add('Methods: Channel-level KernelSHAP', '', 'Explained test windows per city', '100', _last(nb, 'SHAP_MAX_TEST'), fn,
        'SHAP_MAX_TEST')
    r19 = txt('analyses/tools/r19_helper_cell.py')
    for name, pr, lab in (('R19_VAL_START', '2019-04-01', 'First validation target date'),
                          ('R19_TEST_START', '2019-07-01', 'First test target date'),
                          ('R19_DATA_END', '2020-07-01', 'Last test target date (last day of the data)')):
        v = re.search(name + r" = np\.datetime64\('([\d-]+)'\)", r19).group(1)
        add(R1S + ' | ' + M2, '', lab, pr, v, 'analyses/tools/r19_helper_cell.py', f'constant {name}')
    add(R2S + ' | ' + M2, '', 'Date from which the lockdown and Unlock period starts', '2020-03-25',
        re.search(r"LOCKDOWN = np\.datetime64\('([\d-]+)'\)", txt('analyses/baselines/baselines.py')).group(1),
        'analyses/baselines/baselines.py', 'constant LOCKDOWN')
    add(M2, '', 'Lookbacks', '7, 14, 21, 30', ', '.join(str(x) for x in _last(nb, 'LOOKBACK_PERIODS_V2')), fn,
        'LOOKBACK_PERIODS_V2')
    # software versions (Methods: Implementation)
    I = 'Methods: Implementation'
    gs = jsn(G + '/g_sessions.json')[0]
    for key, pr in (('python', '3.13.15'), ('numpy', '2.1.3'), ('pandas', '2.2.3'), ('scipy', '1.16.3'),
                    ('scikit-learn', '1.6.1'), ('EMD-signal', '1.9.0'), ('shap', '0.51.0')):
        add(I, '', f'Colab notebooks: {key}', pr, gs[key], G + '/g_sessions.json', 'versions the run recorded')
    add(I, '', 'Colab notebooks: PyTorch', '2.11.0', gs['torch'].split('+')[0], G + '/g_sessions.json')
    add(I, '', 'Colab notebooks: GPU', 'Tesla T4', gs['gpu'], G + '/g_sessions.json')
    nb1 = json.loads((REPO / 'notebooks' / '01_phase1_baselines_r1.ipynb').read_text(encoding='utf-8'))
    out1 = '\n'.join(''.join(o.get('text', '')) for c in nb1['cells'] for o in c.get('outputs', []))
    for key, pr in (('tensorflow', '2.20.0'), ('xgboost', '3.4.1')):
        add(I, '', f'Baseline notebook: {key}', pr, re.search(key + r': ([\d.]+)', out1).group(1),
            'notebooks/01_phase1_baselines_r1.ipynb', 'version printed in the output of the import cell')
    pv = jsn(T6 + '/c2x_verdict.json')['provenance']
    for key, pr in (('python', '3.13.0'), ('xgboost', '3.2.0'), ('numpy', '2.4.2'), ('pandas', '3.0.1'), ('scipy', '1.17.1')):
        add(I, '', f'Weather diagnostic: {key}', pr, pv[key], T6 + '/c2x_verdict.json', 'provenance of the run')
    req = txt('requirements/analyses_local_cpu.txt')
    for key, pr in (('scikit-learn', '1.8.0'), ('EMD-signal', '1.9.0'), ('matplotlib', '3.10.8')):
        add(I, '', f'Laptop analyses: {key}', pr, re.search(r'^' + re.escape(key) + r'==([\d.]+)', req, flags=re.M).group(1),
            'requirements/analyses_local_cpu.txt', 'the pinned file of that environment')
    # weather, bulletin and literature settings
    add(M9, '', 'Null sets', '10', jsn(T6 + '/c2x_verdict.json')['primary']['H1']['K'], T6 + '/c2x_verdict.json', 'K of H1')
    e5 = txt('analyses/e1_verification/e5_driver_band_precheck.py')
    add(M9, '', 'Band edges of the four weather bands (days)', '7, 31, 91',
        ', '.join(re.search(r'for k in \((\d+), (\d+), (\d+)\)', e5).groups()),
        'analyses/e1_verification/e5_driver_band_precheck.py', 'trailing means over 7, 31 and 91 days')
    add('Supplementary Note S8', '', 'Permutations of the weekly-cycle test', '2,000',
        int(re.search(r'np\.empty\((\d+)\)', txt('analyses/e1_verification/e4_weekly_cycle.py')).group(1)),
        'analyses/e1_verification/e4_weekly_cycle.py', 'size of the surrogate array')
    add(M8, '', 'Origins used: every n-th origin', '5',
        int(re.search(r'SEQ, HORIZONS, ORIGIN_STEP = 7, \(1, 7\), (\d+)', txt('analyses/dataset_check/e7_common.py')).group(1)),
        'analyses/dataset_check/e7_common.py', 'constant ORIGIN_STEP')
    cities = sorted(set(csv_(X1 + '/e7_d2_city.csv').city))
    add(M8, '', 'Cities in the bulletin analysis', '14', len(cities), X1 + '/e7_d2_city.csv', 'distinct cities', 'derived')
    add(M8 + ' | Supplementary Note S7', '', 'Their names',
        'Amaravati, Amritsar, Bengaluru, Chennai, Delhi, Gurugram, Hyderabad, Jaipur, Kolkata, Lucknow, Mumbai, Patna, '
        'Thiruvananthapuram, Visakhapatnam', ', '.join(cities), X1 + '/e7_d2_city.csv', '', 'derived')
    pool = csv_(X1 + '/e7_d2_pooled.csv')
    add(M8, '', 'Yearly folds', '2019 to 2025', f'{pool.year.min()} to {pool.year.max()}', X1 + '/e7_d2_pooled.csv', '', 'derived')
    add(M8, '', 'Seeds', '0, 1, 2', ', '.join(str(s) for s in sorted(pool.seed.unique())), X1 + '/e7_d2_pooled.csv', '', 'derived')
    add(M7, '', 'Seeds of the leakage contrast', '0, 1, 2',
        ', '.join(str(s) for s in sorted(csv_(X1 + '/e1_accuracy.csv').seed.unique())), X1 + '/e1_accuracy.csv', '', 'derived')
    add(M10, '', 'Seed of the random order of the 161 studies', '20261013',
        re.search(r'default_rng\((\d+)\)', txt('analyses/literature_count/lc_sample.py')).group(1),
        'analyses/literature_count/lc_sample.py', 'default_rng seed')
    # digests of the pre-registration documents (Supplementary Note S8)
    for name, pr in (('C2_PREREGISTRATION.md', 'c3b38c294ba09b1f872e414d48e40623adb1f9d1382473099c2cc78494debd50'),
                     ('C2_PREREGISTRATION_ADDENDUM_A1.md', 'c2d32acd5cbe91dede7cd460ee0ceee2deb029755f0d58964e8d39915e134ed7'),
                     ('C2_PREREGISTRATION_ADDENDUM_A2.md', '0f3e15ce2d78ed9dedf2c436f417c4c80e9a81c9e14de38a30c9a2854151348c')):
        b = (REPO / 'analyses' / 'e1_verification' / name).read_bytes().replace(b'\r\n', b'\n')
        add('Supplementary Note S8', '', f'SHA-256 of {name} (published file, LF line endings)', pr, hashlib.sha256(b).hexdigest(),
            'analyses/e1_verification/' + name, 'hashlib.sha256 over the published file; also in C2_FREEZE_SHA256.txt and the '
            'verdict file', 'derived')
    # remaining derived numbers of the attribution notes
    mat = csv_(G + '/shap/g1_shap18_matrix_lb7.csv').set_index('Unnamed: 0')
    for c, pr in (('Talcher', '1.09'), ('Jorapokhar', '1.14')):
        add('Supplementary Note S6', 'tab:s_g1', f'{c}: attribution of PM2.5 divided by that of PM10', pr,
            mat.loc[c, 'PM2.5'] / mat.loc[c, 'PM10'], G + '/shap/g1_shap18_matrix_lb7.csv', 'ratio of the two columns', 'derived')
    lo, hi = wilson(30, 60)
    add('Supplementary Note S5', '', 'Half-width of the Wilson 95% interval for 60 studies at a share of 50% (percentage points)',
        '12', 100 * (hi - lo) / 2, LC + '/coding_sheet.csv', 'widest interval for n = 60', 'derived')


ROWS_STATIC = [
    ('Fig. 1', 'Design schematic', 'no data', 'analyses/manuscript/scripts/make_figures.py'),
    ('Fig. 2', 'Attribution in the 13 interpreted cities', G + '/shap/g1_shap18_matrix_lb7.csv, g1_shap18_summary_lb7.csv', 'make_figures.py'),
    ('Fig. 3a', 'Raw-history ablation and PM2.5 target', R + '/shap/shap_periods_ablation13ch_lb7.csv, shap_v2_pm25_attribution_lb7.csv', 'make_figures.py'),
    ('Fig. 3b', 'Four realisations x five model seeds', G + '/shap/g2_shap_lb7.csv', 'make_figures.py'),
    ('Fig. 4a', 'Leakage contrast', X1 + '/e1_shares.csv', 'make_figures.py'),
    ('Fig. 4b, 4c', 'Official bulletins', X1 + '/e7_d2_pooled.csv', 'make_figures.py'),
    ('Fig. S1', 'All 18 cities, clustered', G + '/shap/g1_shap18_matrix_lb7.csv', 'make_figures.py'),
    ('Table 1 (tab:performance)', 'Forecast accuracy', BL + '/baselines_pooled.csv, ' + B1 + ', ' + R + '/comparison_v2_full.csv, multiseed_summary_lb7.csv', 'make_tables.py'),
    ('Table 2 (tab:conditioning)', 'City conditioning', G + '/g3_conditioning_summary_lb7.csv', 'make_tables.py'),
    ('tab:s_baselines_city', 'Persistence and climatology by city', BL + '/baselines_city.csv', 'make_tables.py'),
    ('tab:s_g1', 'Attribution, all 18 cities', G + '/shap/g1_shap18_summary_lb7.csv', 'make_tables.py'),
    ('tab:s_g2', 'Decomposition realisations', G + '/g2_anova_lb7.csv', 'make_tables.py'),
    ('tab:s_e1', 'Leakage contrast', X1 + '/e1_accuracy.csv, e1_shares.csv', 'make_tables.py'),
    ('tab:s_e7', 'Official bulletins', X1 + '/e7_d2_pooled.csv', 'make_tables.py'),
    ('tab:s_c2', 'Weather diagnostic rules and results', T6 + '/c2x_verdict.json', 'make_tables.py'),
    ('tab:s_lit_summary, tab:s_lit_coding', 'Literature sample', LC + '/coding_sheet.csv, coding_order.csv', 'make_tables.py'),
    ('tab:windows, tab:coverage, tab:missing0, tab:missing1', 'Windows, coverage, missingness', EV + '/data_audit.csv, pollutant_missing.csv', 'rebuild_si_tables.py'),
    ('tab:cityaccuracy, tab:cityperiods, tab:periodperformance', 'City accuracy and periods', R + '/r110_main_city_periods_lb7.csv, comparison_v2_full.csv', 'rebuild_si_tables.py'),
    ('tab:periods0, tab:periods1', 'Scale diagnostics by channel', R + '/table8_channel_periods.csv', 'rebuild_si_tables.py'),
    ('tab:lookback', 'Lookback selection', R + '/r113_lookback_selection.json', 'rebuild_si_tables.py'),
    ('tab:background', 'Attribution backgrounds', BG, 'rebuild_si_tables.py'),
    ('tab:gaps', 'Window constructions', R + '/s2_summary_lb7.csv, r33_s1_filled_lb7.csv', 'rebuild_si_tables.py'),
]


def check_manuscript(d: Path) -> None:
    files = [d / n for n in ('main.tex', 'supplementary.tex') if (d / n).exists()]
    files += sorted((d / 'tables').glob('*.tex')) + sorted((d / 'si_tables').glob('*.tex'))
    text = ''.join(f.read_text(encoding='utf-8') for f in files)
    text = (text.replace('{,}', ',').replace('5\\times10^{-4}', '0.0005').replace('10^{-6}', '0.000001')
            .replace('\\times10^{-5}', 'e-05'))
    flat = re.sub(r'\s+', ' ', text.replace('$', '').replace('\\%', '%').replace('--', '-').replace('\\pm', '+-'))
    miss = []
    for c in CLAIMS:
        p = c['printed']
        if _num(p) is None:
            continue
        cands = {p, p.replace('-', '−'), p.replace('-', '').strip()}
        if not any(x and x in flat for x in cands):
            miss.append((c['claim'], p))
    for claim, p in miss:
        print(f'  NOT FOUND IN THE MANUSCRIPT TEXT: {p}  ({claim})')
    print(f'manuscript text check: {sum(_num(c["printed"]) is not None for c in CLAIMS) - len(miss)} of '
          f'{sum(_num(c["printed"]) is not None for c in CLAIMS)} numeric values found as printed')


def write_outputs() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / 'trace_claims.csv').open('w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['where', 'si', 'claim', 'printed', 'recomputed', 'ok', 'kind', 'source', 'how'])
        w.writeheader()
        w.writerows(CLAIMS)
    (OUT / 'derived_numbers.txt').write_text('\n'.join(DERIVED) + '\n', encoding='utf-8')
    bad = [c for c in CLAIMS if not c['ok']]
    n_d = sum(c['kind'] == 'derived' for c in CLAIMS)
    lines = ['# Traceability of the numbers in the manuscript', '',
             'Every number quoted in the main text and the Supplementary Notes, with the file it comes from, grouped by '
             'manuscript section and keyed by the Supplementary table label (`tab:...`) that also shows it. '
             '`analyses/manuscript/scripts/trace_claims.py` recomputes each value from the files of this repository, '
             'compares it with the printed value and writes `analyses/manuscript/outputs/trace_claims.csv`. **Direct** means that a '
             'result file prints the number. **Derived** means the number is computed from files that do not print it, '
             'and the formula is given.', '',
             f'Status of the last run: {len(CLAIMS)} values, {len(CLAIMS) - len(bad)} reproduced, {len(bad)} differ; '
             f'{n_d} are derived. Differences are listed at the end of this file.', '']
    where = []
    for c in CLAIMS:
        for s in c['where'].split(' | '):
            where.append((s, c))
    order = [ABS, R1S, R2S, R3S, R4S, R5S, R6S, R7S, DIS]
    secs = sorted({s for s, _ in where}, key=lambda s: (order.index(s) if s in order else 10 + (0 if s.startswith('Methods') else 1), s))
    for s in secs:
        lines += [f'## {s}', '', '| Claim | Printed | SI table | File | Kind | Derivation |', '|---|---|---|---|---|---|']
        for sec, c in where:
            if sec == s:
                mark = '' if c['ok'] else ' **(differs: ' + c['recomputed'] + ')**'
                lines.append(f"| {c['claim']} | {c['printed']}{mark} | {c['si'] or ''} | `{c['source']}` | {c['kind']} | {c['how']} |")
        lines.append('')
    lines += ['## Figures and tables', '', '| Item | Content | Result files | Script |', '|---|---|---|---|']
    lines += [f'| {a} | {b} | `{c}` | `{d}` |' for a, b, c, d in ROWS_STATIC]
    lines += ['', '## Not recomputed', '',
              '- Run times (about 18 CPU-hours for a full decomposition run, about 14 minutes of channel-level SHAP per city '
              'on the T4 GPU) are estimates from the runs and are not stored in a result file.',
              '- Citations, licences, download and search dates, the CPCB breakpoints of the AQI definition and the text of '
              'the pre-registration are quoted from their sources. The pre-registration is published unchanged and its '
              'digest is checked above.',
              '- The number of input channels (12 pollutants and 5 decomposition channels) and the window rules are '
              'definitions in the code, listed in the Methods and implemented in `analyses/tools/`.', '']
    if bad:
        lines += ['## Differences', ''] + [f"- {c['where']}: {c['claim']}: printed {c['printed']}, recomputed {c['recomputed']}" for c in bad]
    MD.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--manuscript', type=Path)
    a = ap.parse_args()
    for fn in (section_data, section_accuracy, section_attribution, section_leakage_bulletins, section_weather,
               section_literature, section_settings):
        fn()
    write_outputs()
    bad = [c for c in CLAIMS if not c['ok']]
    print(f'{len(CLAIMS)} claims, {sum(c["kind"] == "derived" for c in CLAIMS)} derived, {len(CLAIMS) - len(bad)} reproduced, {len(bad)} differ')
    for c in bad:
        print(f"  DIFFERS: [{c['where']}] {c['claim']}: printed {c['printed']}, recomputed {c['recomputed']}")
    if a.manuscript:
        check_manuscript(a.manuscript)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
