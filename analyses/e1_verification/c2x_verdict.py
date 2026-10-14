"""C2 verdict (task C2-T4): the pre-registered rules applied to the run tables (C2_PREREGISTRATION.md sections 7-9).

Pure functions on two tables (pre-registration Appendix B); nothing here reads a file or fits a model.
  pooled  one row per arm x seed x period (all / pre / lock): n, best_iter, mae, rmse, r2, pol, dec_osc, dec_slow,
          city, met, met_syn, met_intra, met_subs, met_seas, met_disp, met_temp, met_hum, met_rain
  city    one row per arm x seed x city (full test year, cities with >= 150 test windows): n, mae, met, met_syn,
          met_intra, met_subs, met_seas
evaluate() checks the tables (stop on anything missing), computes every statistic of section 7, applies the rules of
section 8 in the fixed order H1 -> H2 -> H1b, the lockdown check, the secondary and descriptive results (decision
T4-b: estimates with 90% intervals, no p-values) and the 13% gate, and picks the section 9 wording (decision T4-c:
one decimal; addendum A1 for the operational sentence). The runner passes in the climate table and the provenance block (decision T4-a). render() gives the
readable text; write() saves c2x_verdict.json and c2x_verdict.txt.
"""
from __future__ import annotations

import json
import math
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from c2x_features import ADDENDUM_A1_SHA256, ADDENDUM_A2_SHA256, N_E5, N_POOL, PREREG_SHA256, arm_names

ALPHA = 0.05                  # one-sided level of every test (section 7)
LEVEL = 0.90                  # two-sided interval level matching the one-sided 5% tests (T1-c)
H2_MIN_PP = 2.0               # H2 minimum short-band excess, percentage points (section 8)
GATE_PCT = 13.0               # C2-11 gate on g (section 8)
SEEDS = tuple(range(40))      # section 5
PERIODS = ('all', 'pre', 'lock')
MIN_CITY_TEST = 150           # section 6
POOLED_COLS = ['n', 'best_iter', 'mae', 'rmse', 'r2', 'pol', 'dec_osc', 'dec_slow', 'city', 'met', 'met_syn',
               'met_intra', 'met_subs', 'met_seas', 'met_disp', 'met_temp', 'met_hum', 'met_rain']
CITY_COLS = ['n', 'mae', 'met', 'met_syn', 'met_intra', 'met_subs', 'met_seas']
WEATHER_COLS = ['met', 'met_syn', 'met_intra', 'met_subs', 'met_seas', 'met_disp', 'met_temp', 'met_hum', 'met_rain']
POOL = [f'POOL_{j}' for j in range(N_POOL)]
POOL_PP = [f'POOL_PP_{j}' for j in range(N_POOL)]
E5 = [f'E5NULL_{k}' for k in range(1, N_E5 + 1)]
E5_PP = [f'E5NULL_PP_{k}' for k in range(1, N_E5 + 1)]
NOT_TESTED = 'not tested in sequence'

# Section 9, verbatim. X%, a and b are filled from the verdict with one decimal.
ROWS = {
    1: ("In a diagnostic setting where the forecast day's weather is known, short-timescale weather explains part "
        "of the day-to-day variation in AQI beyond seasonal climatology (MAE X% lower, 90% interval a to b), and it "
        "adds to the weather of the forecast origin."),
    2: ("The forecast day's weather explains part of the variation in AQI beyond seasonal climatology (MAE X% lower, "
        "90% interval a to b). It adds no detectable skill beyond the weather of the forecast origin."),
    3: ("The forecast day's weather lowers the error beyond seasonal climatology (MAE X% lower, 90% interval a to b), "
        "but the effect is not shown to lie at short timescales."),
    4: "No weather claim. Reported as found.",
}
LOCKDOWN_SENTENCE = "The effect is not separately confirmed outside the COVID-19 lockdown period."
OPERATIONAL_PASS = ("Weather known at the forecast origin also lowers the error beyond seasonal climatology (MAE X% "
                    "lower, 90% interval a to b).")
OPERATIONAL_FAIL = "Weather known at the forecast origin adds no detectable skill beyond seasonal climatology."
# Addendum A1 (C2_PREREGISTRATION_ADDENDUM_A1.md, approved 10 Oct 2026): when H1 fails and P's H1 passes, no "also".
OPERATIONAL_PASS_A1 = ("Weather known at the forecast origin lowers the error beyond seasonal climatology (MAE X% "
                       "lower, 90% interval a to b).")


# ---------------------------------------------------------------- checks

def check_tables(pooled: pd.DataFrame, city: pd.DataFrame, seeds: tuple[int, ...] = SEEDS) -> None:
    """Stop unless both tables are complete: 32 arms x the seeds (pre-registered: 0-39) x 3 periods, the Appendix B
    columns, no gaps. Only the T5 dry run passes other seeds."""
    arms = arm_names()
    missing = [c for c in ['arm', 'seed', 'period'] + POOLED_COLS if c not in pooled.columns]
    if missing:
        raise ValueError(f'pooled table lacks columns {missing}')
    keys = pooled[['arm', 'seed', 'period']]
    if keys.duplicated().any():
        raise ValueError('pooled table has duplicate arm x seed x period rows')
    want = pd.MultiIndex.from_product([arms, seeds, PERIODS], names=['arm', 'seed', 'period'])
    got = pd.MultiIndex.from_frame(keys)
    if len(got) != len(want) or not got.isin(want).all():
        raise ValueError(f'pooled table is not exactly {len(arms)} arms x {len(seeds)} seeds x {len(PERIODS)} periods')
    if pooled[POOLED_COLS].isna().any().any() or not np.isfinite(pooled[POOLED_COLS].to_numpy(float)).all():
        raise ValueError('pooled table has missing or non-finite values')
    if (pooled.loc[pooled.arm == 'BASE', WEATHER_COLS] != 0).any().any():
        raise ValueError('BASE has a non-zero weather share')
    missing = [c for c in ['arm', 'seed', 'city'] + CITY_COLS if c not in city.columns]
    if missing:
        raise ValueError(f'city table lacks columns {missing}')
    names = sorted(city['city'].unique())
    want = pd.MultiIndex.from_product([arms, seeds, names], names=['arm', 'seed', 'city'])
    got = pd.MultiIndex.from_frame(city[['arm', 'seed', 'city']])
    if got.duplicated().any() or len(got) != len(want) or not got.isin(want).all():
        raise ValueError('city table is not complete over arms x seeds x cities')
    if city[CITY_COLS].isna().any().any() or (city['n'] < MIN_CITY_TEST).any():
        raise ValueError(f'city table has missing values or a city with fewer than {MIN_CITY_TEST} test windows')


def runs(table: pd.DataFrame, arm: str, col: str, **where: str) -> np.ndarray:
    """The per-seed values of one arm, in seed order (completeness is checked by check_tables)."""
    t = table[table['arm'] == arm]
    for k, v in where.items():
        t = t[t[k] == v]
    t = t.sort_values('seed')
    if not t['seed'].is_unique or len(t) != table['seed'].nunique():
        raise ValueError(f'{arm} {where}: one value per seed expected')
    if col == 'short':
        return (t['met_syn'] + t['met_intra']).to_numpy(float)
    return t[col].to_numpy(float)


# ---------------------------------------------------------------- statistics (section 7)

def prediction_test(real: np.ndarray, nulls: list[np.ndarray], lower_is_better: bool) -> dict:
    """One observation per weather draw: the real arm mean against the K null-set means, df K - 1.

    lower_is_better=True (MAE): effect d = mean of null means - real mean. False (a share): effect e = real - null."""
    xr = float(np.mean(real))
    m = np.array([float(np.mean(n)) for n in nulls])
    k = len(m)
    mbar, sm = float(m.mean()), float(m.std(ddof=1))
    effect = mbar - xr if lower_is_better else xr - mbar
    se = sm * math.sqrt(1 + 1 / k)
    df = k - 1
    if se > 0:
        t = effect / se
        p = float(stats.t.sf(t, df))
    else:                                   # all null-set means identical: the sign decides
        t = math.copysign(math.inf, effect) if effect else 0.0
        p = 0.0 if effect > 0 else 1.0
    q = float(stats.t.ppf(1 - (1 - LEVEL) / 2, df))
    out = {'real_mean': xr, 'null_means': m.tolist(), 'null_mean': mbar, 'null_sd': sm, 'K': k, 'effect': effect,
           'se': se, 'df': df, 't': t, 'p': p, 'lo': effect - q * se, 'hi': effect + q * se}
    if lower_is_better:
        out['below_every_null'] = bool(xr < m.min())
        out.update(pct=100 * effect / mbar, pct_lo=100 * out['lo'] / mbar, pct_hi=100 * out['hi'] / mbar,
                   rel_se_null_mean=sm / (math.sqrt(k) * mbar))
    return out


def welch(a: np.ndarray, b: np.ndarray) -> dict:
    """d = mean(a) - mean(b), Welch-Satterthwaite df, one-sided p for d > 0, 90% interval."""
    na, nb = len(a), len(b)
    va, vb = float(np.var(a, ddof=1)), float(np.var(b, ddof=1))
    d = float(np.mean(a) - np.mean(b))
    se2 = va / na + vb / nb
    if se2 > 0:
        se = math.sqrt(se2)
        df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
        t = d / se
        p = float(stats.t.sf(t, df))
    else:
        se, df = 0.0, float(na + nb - 2)
        t = math.copysign(math.inf, d) if d else 0.0
        p = 0.0 if d > 0 else 1.0
    q = float(stats.t.ppf(1 - (1 - LEVEL) / 2, df))
    return {'mean_a': float(np.mean(a)), 'mean_b': float(np.mean(b)), 'effect': d, 'se': se, 'df': df, 't': t,
            'p': p, 'lo': d - q * se, 'hi': d + q * se}


def base_vs_nulls(base: np.ndarray, nulls: list[np.ndarray]) -> dict:
    """X_BASE - mean of null-set means, the null set as the unit: SE = sqrt(v_BASE/S + s_m^2/K), df K - 1."""
    m = np.array([float(np.mean(n)) for n in nulls])
    k = len(m)
    d = float(np.mean(base)) - float(m.mean())
    se = math.sqrt(float(np.var(base, ddof=1)) / len(base) + float(m.std(ddof=1)) ** 2 / k)
    df = k - 1
    t = d / se if se > 0 else (math.copysign(math.inf, d) if d else 0.0)
    p = float(stats.t.sf(t, df)) if se > 0 else (0.0 if d > 0 else 1.0)
    q = float(stats.t.ppf(1 - (1 - LEVEL) / 2, df))
    return {'effect': d, 'se': se, 'df': df, 't': t, 'p': p, 'lo': d - q * se, 'hi': d + q * se}


def descriptive(x: dict) -> dict:
    """Decision T4-b: descriptive results keep estimates and intervals, never p-values."""
    return {k: v for k, v in x.items() if k not in ('p', 't')}


# ---------------------------------------------------------------- rules (section 8)

def family(table: pd.DataFrame, real: str, nulls: list[str], col: str, lower: bool, **where: str) -> dict:
    return prediction_test(runs(table, real, col, **where), [runs(table, n, col, **where) for n in nulls], lower)


def h1_rule(x: dict) -> bool:
    return x['p'] < ALPHA and x['below_every_null']


def h2_rule(x: dict) -> bool:
    return x['effect'] >= H2_MIN_PP and x['p'] < ALPHA


def one_decimal(x: float) -> str:
    """Decision T4-c: one decimal, halves rounded away from zero as a reader expects (6.25 -> 6.3, not 6.2)."""
    return str(Decimal(repr(float(x))).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP))


def fill(template: str, x: dict) -> str:
    return (template.replace('X%', f"{one_decimal(x['pct'])}%")
            .replace('a to b', f"{one_decimal(x['pct_lo'])} to {one_decimal(x['pct_hi'])}"))


def evaluate(pooled: pd.DataFrame, city: pd.DataFrame, climate: pd.DataFrame | None = None,
             provenance: dict | None = None, seeds: tuple[int, ...] = SEEDS) -> dict:
    check_tables(pooled, city, seeds)
    v: dict = {'pre_registration_sha256': PREREG_SHA256, 'addendum_A1_sha256': ADDENDUM_A1_SHA256,
               'addendum_A2_sha256': ADDENDUM_A2_SHA256,
               'seeds': list(seeds), 'provenance': provenance or {}, 'warnings': []}
    if tuple(seeds) != SEEDS:
        v['warnings'].append(f'not the pre-registered seeds 0-39 ({len(seeds)} seeds): a dry run, not a result')

    # primary, fixed order H1 -> H2 -> H1b
    h1 = family(pooled, 'MET_PP', POOL_PP, 'mae', True, period='all')
    h2 = family(pooled, 'MET_PP', POOL_PP, 'short', False, period='all')
    h1b = welch(runs(pooled, 'MET', 'mae', period='all'), runs(pooled, 'MET_PP', 'mae', period='all'))
    h1['status'] = 'pass' if h1_rule(h1) else 'fail'
    h2['status'] = ('pass' if h2_rule(h2) else 'fail') if h1['status'] == 'pass' else NOT_TESTED
    h1b['status'] = (('pass' if h1b['p'] < ALPHA else 'fail') if h2['status'] == 'pass' else NOT_TESTED)
    v['primary'] = {'H1': h1, 'H2': h2, 'H1b': h1b}

    lock = {'run': h1['status'] == 'pass'}
    if lock['run']:
        pre = family(pooled, 'MET_PP', POOL_PP, 'mae', True, period='pre')
        lock.update(p=pre['p'], effect=pre['effect'], pct=pre['pct'], triggered=pre['p'] >= ALPHA)
    v['lockdown_check'] = lock

    # secondary
    p1 = family(pooled, 'MET', POOL, 'mae', True, period='all')
    p2 = family(pooled, 'MET', POOL, 'short', False, period='all')
    p1['status'] = 'pass' if h1_rule(p1) else 'fail'
    p2['status'] = ('pass' if h2_rule(p2) else 'fail') if p1['status'] == 'pass' else NOT_TESTED
    v['secondary'] = {
        'P_H1': p1, 'P_H2': p2,
        'H4_seasonal_excess': descriptive(family(pooled, 'MET_PP', POOL_PP, 'met_seas', False, period='all')),
        'ablation_long_minus_pp': welch(runs(pooled, 'MET_PP_LONG', 'mae', period='all'),
                                        runs(pooled, 'MET_PP', 'mae', period='all')),
        'E5_sensitivity': e5_sensitivity(pooled),
        'weather_vs_none': weather_vs_none(pooled),
    }
    if climate is not None:
        c = climate.copy()
        c[['var', 'band']] = c['feature'].str.split('|', expand=True)
        v['secondary']['climate_check_median_diff_in_sd'] = (
            c.groupby(['var', 'band'], sort=False)['diff_in_sd'].median().unstack('band').round(6).to_dict('index'))
        v['secondary']['climate_check_full'] = climate.round(6).to_dict('records')

    v['descriptive'] = descriptive_results(pooled, city)

    # gate (point estimate)
    v['gate'] = {'g_pct': h1['pct'], 'threshold_pct': GATE_PCT, 'plan_option_A': h1['pct'] >= GATE_PCT}

    # wording (section 9)
    row = 4 if h1['status'] != 'pass' else 3 if h2['status'] != 'pass' else 2 if h1b['status'] != 'pass' else 1
    sentences = [fill(ROWS[row], h1) if row != 4 else ROWS[4]]
    if lock['run'] and lock['triggered']:
        sentences.append(LOCKDOWN_SENTENCE)
    a1 = row == 4 and p1['status'] == 'pass'                     # addendum A1: "also" would have no referent
    if p1['status'] == 'pass':
        sentences.append(fill(OPERATIONAL_PASS_A1 if a1 else OPERATIONAL_PASS, p1))
    else:
        sentences.append(OPERATIONAL_FAIL)
    v['wording'] = {'row': row, 'sentences': sentences, 'addendum_A1_applied': a1}
    return v


def e5_sensitivity(pooled: pd.DataFrame) -> dict:
    out = {}
    for real, nulls in (('MET_PP', E5_PP), ('MET', E5)):
        mae = family(pooled, real, nulls, 'mae', True, period='all')
        short = family(pooled, real, nulls, 'short', False, period='all')
        seas = family(pooled, real, nulls, 'met_seas', False, period='all')
        mae['status'] = 'pass' if h1_rule(mae) else 'fail'
        short['status'] = 'pass' if h2_rule(short) else 'fail'
        pre = descriptive(family(pooled, real, nulls, 'mae', True, period='pre'))   # the lockdown computation
        verbatim_h1 = mae['real_mean'] < min(mae['null_means'])
        verbatim_h2 = (short['real_mean'] - max(short['null_means']) >= H2_MIN_PP
                       and min(seas['null_means']) <= seas['real_mean'] <= max(seas['null_means']))
        out[real] = {'H1_form': mae, 'H2_form': short, 'H4_form': descriptive(seas), 'pre_lockdown_H1_form': pre,
                     'E5_verbatim_H1': bool(verbatim_h1), 'E5_verbatim_H2': bool(verbatim_h2)}
    return out


def weather_vs_none(pooled: pd.DataFrame) -> dict:
    base = runs(pooled, 'BASE', 'mae', period='all')
    out = {f'BASE_minus_{a}': welch(base, runs(pooled, a, 'mae', period='all')) for a in ('MET', 'MET_PP')}
    for name, nulls in (('POOL', POOL), ('POOL_PP', POOL_PP), ('E5NULL', E5), ('E5NULL_PP', E5_PP)):
        out[f'BASE_minus_{name}'] = base_vs_nulls(base, [runs(pooled, n, 'mae', period='all') for n in nulls])
    return out


def descriptive_results(pooled: pd.DataFrame, city: pd.DataFrame) -> dict:
    """Decision T4-b: per period, per city and per variable group, estimates with 90% intervals, no p-values."""
    out: dict = {'per_period': {}, 'per_city': {}, 'bands_and_variable_groups': {}}
    for period in ('pre', 'lock'):
        out['per_period'][period] = {
            f'{real}_vs_{name}_{col}': descriptive(family(pooled, real, nulls, col, col == 'mae', period=period))
            for real, nulls, name in (('MET_PP', POOL_PP, 'POOL_PP'), ('MET', POOL, 'POOL')) for col in ('mae', 'short')}
    for c in sorted(city['city'].unique()):
        out['per_city'][c] = {
            f'{real}_vs_{name}_{col}': descriptive(family(city, real, nulls, col, col == 'mae', city=c))
            for real, nulls, name in (('MET_PP', POOL_PP, 'POOL_PP'), ('MET', POOL, 'POOL')) for col in ('mae', 'short')}
    for col in ('met', 'met_syn', 'met_intra', 'met_subs', 'met_seas', 'met_disp', 'met_temp', 'met_hum', 'met_rain'):
        out['bands_and_variable_groups'][col] = descriptive(family(pooled, 'MET_PP', POOL_PP, col, False, period='all'))
    means = pooled[pooled.period == 'all'].groupby('arm', sort=False)[POOLED_COLS].mean()
    out['arm_means_all'] = means.reindex(arm_names()).round(6).to_dict('index')
    return out


# ---------------------------------------------------------------- output

def _plain(x):
    if isinstance(x, dict):
        return {str(k): _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    if isinstance(x, (np.bool_, bool)):
        return bool(x)
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        return float(x) if math.isfinite(x) else str(x)
    return x


def to_json(v: dict) -> str:
    return json.dumps(_plain(v), indent=1, ensure_ascii=False) + '\n'


def _line(name: str, x: dict, pct: bool = False) -> str:
    s = f"  {name:34s} effect {x['effect']:+.3f} (90% {x['lo']:+.3f} to {x['hi']:+.3f})"
    if pct:
        s += f" = {x['pct']:+.2f}% ({x['pct_lo']:+.2f} to {x['pct_hi']:+.2f})"
    if 'p' in x:
        s += f"  p {x['p']:.4f}"
    if 'status' in x:
        s += f"  -> {x['status']}"
    return s


def render(v: dict) -> str:
    p, s = v['primary'], v['secondary']
    out = ['C2 verdict (rules of C2_PREREGISTRATION.md sections 7-9)',
           f"pre-registration SHA-256 {v['pre_registration_sha256']}",
           f"addendum A1 SHA-256 {v['addendum_A1_sha256']}",
           f"addendum A2 SHA-256 {v['addendum_A2_sha256']} (platform: Linux x86-64, n_jobs 2)", '',
           'PRIMARY (MET_PP against the 10 POOL_PP sets, full test year; order H1 -> H2 -> H1b, one-sided 5%)',
           _line('H1 MAE (null mean - real)', p['H1'], pct=True)
           + f"  below every null mean: {p['H1']['below_every_null']}",
           f"  {'':34s} real {p['H1']['real_mean']:.3f}, null mean {p['H1']['null_mean']:.3f}, "
           f"null-set s.d. {p['H1']['null_sd']:.3f}, rel. SE of null mean {p['H1']['rel_se_null_mean']:.4f}",
           _line('H2 short-band share excess (pp)', p['H2']),
           _line('H1b MAE (MET - MET_PP), Welch', p['H1b'])]
    lk = v['lockdown_check']
    out.append(f"  lockdown check: {'p ' + format(lk['p'], '.4f') + (' -> sentence added' if lk['triggered'] else ' -> no sentence') if lk['run'] else 'not run (H1 did not pass)'}")
    g = v['gate']
    out += ['', f"GATE: g = {g['g_pct']:.2f}% against {g['threshold_pct']:.0f}% -> "
            + ('plan option A (T8 first recomputes its power)' if g['plan_option_A'] else 'option A not run'),
            '', f"WORDING (section 9, row {v['wording']['row']}"
            + (', addendum A1 applied' if v['wording']['addendum_A1_applied'] else '') + '):'
            ] + [f'  "{t}"' for t in v['wording']['sentences']]
    out += ['', 'SECONDARY', _line('P H1 MAE (MET vs POOL)', s['P_H1'], pct=True), _line('P H2 short excess', s['P_H2']),
            _line('H4 seasonal excess (descriptive)', s['H4_seasonal_excess']),
            _line('ablation MAE (LONG - MET_PP)', s['ablation_long_minus_pp'])]
    for real, e in s['E5_sensitivity'].items():
        out += [_line(f'E5 nulls {real} H1 form', e['H1_form'], pct=True), _line(f'E5 nulls {real} H2 form', e['H2_form']),
                f"  {'E5 verbatim ' + real:34s} H1 {e['E5_verbatim_H1']}, H2 {e['E5_verbatim_H2']}"]
    out += [_line(k, x) for k, x in s['weather_vs_none'].items()]
    if 'climate_check_median_diff_in_sd' in s:
        out += ['', 'climate check: median over cities of (pool mean - real mean) / real s.d.',
                pd.DataFrame(s['climate_check_median_diff_in_sd']).T.round(3).to_string()]
    d = v['descriptive']
    am = pd.DataFrame(d['arm_means_all']).T[['mae', 'rmse', 'r2', 'met', 'met_syn', 'met_intra', 'met_seas']]
    out += ['', 'ARM MEANS, full test year (40 seeds)', am.round(3).to_string()]
    out += ['', 'DESCRIPTIVE (estimates with 90% intervals, no p-values)']
    for period, rows in d['per_period'].items():
        out += [_line(f'{period}: {k}', x, pct='mae' in k) for k, x in rows.items()]
    out += [_line(f'band/group {k}', x) for k, x in d['bands_and_variable_groups'].items()]
    for c, rows in d['per_city'].items():
        out += [_line(f'{c}: {k}', x, pct='mae' in k) for k, x in rows.items()]
    if v['warnings']:
        out += ['', 'WARNINGS'] + [f'  {w}' for w in v['warnings']]
    if v['provenance']:
        out += ['', 'PROVENANCE'] + [f'  {k}: {x}' for k, x in v['provenance'].items()]
    return '\n'.join(out) + '\n'


def write(v: dict, out_dir: Path, prefix: str = 'c2x') -> None:
    """Unix line endings on every platform, so outputs compare byte for byte across Windows and Linux."""
    for name, text in ((f'{prefix}_verdict.json', to_json(v)), (f'{prefix}_verdict.txt', render(v))):
        with open(out_dir / name, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
