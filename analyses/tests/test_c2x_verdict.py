"""Tests for the C2 verdict module (task C2-T4), on made-up tables only. No real C2 result exists or is read.

Tables are built from binary-exact numbers (multiples of 1/8, seed noise +-0.25 alternating, so every arm mean is
exact). Boundary cases are therefore tested at the exact boundary. Each statistic is checked against an independent
reference: scipy's Welch t-test and a hand computation of the prediction test. The wording is checked word for word
against section 9 of the approved pre-registration.

Run:  python tests/test_c2x_verdict.py
"""
import math
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'e1_verification'))
import c2x_verdict as cv  # noqa: E402
from c2x_features import ADDENDUM_A1, PREREG, arm_names  # noqa: E402

Z = np.array([1.0, -1.0] * 20)                       # seed noise pattern: mean exactly 0
OFF = [-0.5, -0.375, -0.25, -0.125, 0.0, 0.0, 0.125, 0.25, 0.375, 0.5]    # null-set offsets, sum exactly 0
OFF_E5 = [-0.25, -0.125, 0.125, 0.25]
N_PERIOD = {'all': 6171, 'pre': 4502, 'lock': 1669}


def default_means() -> dict[str, dict[str, float]]:
    """Per arm: MAE, short-band share (syn + intra, split evenly), seasonal share, subseasonal share."""
    m = {'BASE': dict(mae=32.0, short=0.0, seas=0.0, subs=0.0),
         'MET': dict(mae=30.0, short=4.0, seas=2.0, subs=1.0),
         'MET_PP': dict(mae=28.0, short=5.0, seas=2.0, subs=1.0),
         'MET_PP_LONG': dict(mae=29.0, short=0.0, seas=2.5, subs=1.5)}
    for j, o in enumerate(OFF):
        m[f'POOL_{j}'] = dict(mae=32.0 + o, short=2.0 + o / 4, seas=2.0 + o / 4, subs=1.0)
        m[f'POOL_PP_{j}'] = dict(mae=32.0 + o, short=2.0 + o / 4, seas=2.0 + o / 4, subs=1.0)
    for k, o in enumerate(OFF_E5, start=1):
        m[f'E5NULL_{k}'] = dict(mae=32.0 + o, short=2.0 + o, seas=2.0 + o, subs=1.0)
        m[f'E5NULL_PP_{k}'] = dict(mae=32.0 + o, short=2.0 + o, seas=2.0 + o, subs=1.0)
    return m


def tables(change: dict | None = None, pre: dict | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Complete pooled and city tables. change: {arm: {measure: mean}}; pre: the same, pre-lockdown period only."""
    means = default_means()
    for arm, d in (change or {}).items():
        means[arm] = {**means[arm], **d}
    rows, crow = [], []
    for arm in arm_names():
        for period in cv.PERIODS:
            mm = {**means[arm], **((pre or {}).get(arm, {}) if period == 'pre' else {})}
            weather = arm != 'BASE'
            for s in cv.SEEDS:
                z = Z[s]
                syn = intra = mm['short'] / 2 + (0.0625 * z if weather else 0.0)
                seas = mm['seas'] + (0.125 * z if weather else 0.0)
                subs = mm['subs']
                met = syn + intra + seas + subs
                row = dict(arm=arm, seed=s, period=period, n=N_PERIOD[period], best_iter=300, mae=mm['mae'] + 0.25 * z,
                           rmse=1.5 * mm['mae'], r2=0.8, pol=40.0, dec_osc=4.0, dec_slow=45.0, city=1.0, met=met,
                           met_syn=syn, met_intra=intra, met_subs=subs, met_seas=seas, met_disp=met / 2,
                           met_temp=met / 4, met_hum=met / 8, met_rain=met / 8)
                rows.append(row)
                if period == 'all':
                    for c in ('Delhi', 'Mumbai'):
                        crow.append(dict(arm=arm, seed=s, city=c, n=300, mae=row['mae'], met=met, met_syn=syn,
                                         met_intra=intra, met_subs=subs, met_seas=seas))
    return pd.DataFrame(rows), pd.DataFrame(crow)


def run(change: dict | None = None, pre: dict | None = None) -> dict:
    return cv.evaluate(*tables(change, pre))


def null_sd(offsets: list[float]) -> float:
    return float(np.std(np.array(offsets), ddof=1))


# ---------------------------------------------------------------- statistics against independent references

def test_welch_matches_scipy() -> None:
    rng = np.random.default_rng(3)
    for _ in range(20):
        a, b = rng.normal(28, 0.4, 40), rng.normal(28.3, 1.1, 40)
        w = cv.welch(b, a)
        r = stats.ttest_ind(b, a, equal_var=False, alternative='greater')
        ci = stats.ttest_ind(b, a, equal_var=False).confidence_interval(confidence_level=0.90)
        assert math.isclose(w['p'], r.pvalue, rel_tol=1e-9) and math.isclose(w['df'], r.df, rel_tol=1e-9)
        assert math.isclose(w['lo'], ci.low, rel_tol=1e-9) and math.isclose(w['hi'], ci.high, rel_tol=1e-9)
    print('    20 random cases: p, df and 90% interval equal scipy ttest_ind (Welch)')


def test_prediction_test_by_hand() -> None:
    real = 29.0 + 0.25 * Z
    nulls = [32.0 + o + 0.25 * Z for o in OFF]
    x = cv.prediction_test(real, nulls, lower_is_better=True)
    sd = null_sd([32.0 + o for o in OFF])
    se = sd * math.sqrt(1 + 1 / 10)
    assert x['effect'] == 3.0 and x['K'] == 10 and x['df'] == 9
    assert math.isclose(x['se'], se, rel_tol=1e-12)
    assert math.isclose(x['p'], stats.t.sf(3.0 / se, 9), rel_tol=1e-12)
    assert math.isclose(x['lo'], 3.0 - 1.8331129326536335 * se, rel_tol=1e-12)
    assert math.isclose(x['pct'], 100 * 3.0 / 32.0, rel_tol=1e-12) and x['below_every_null']
    assert math.isclose(x['rel_se_null_mean'], sd / (math.sqrt(10) * 32.0), rel_tol=1e-12)
    s = cv.prediction_test(5.0 + 0.125 * Z, [2.0 + o / 4 + 0.125 * Z for o in OFF], lower_is_better=False)
    assert s['effect'] == 3.0 and 'pct' not in s and 'below_every_null' not in s
    print(f'    MAE effect 3.0, SE {se:.4f}, df 9, p {x["p"]:.2e}; share direction real - null; t(9, 0.95) = 1.8331')


def test_zero_null_spread() -> None:
    x = cv.prediction_test(30.0 + 0.25 * Z, [32.0 + 0.25 * Z] * 10, lower_is_better=True)
    assert x['se'] == 0 and x['p'] == 0.0 and x['below_every_null']
    y = cv.prediction_test(32.0 + 0.25 * Z, [32.0 + 0.25 * Z] * 10, lower_is_better=True)
    assert y['p'] == 1.0 and not y['below_every_null']
    print('    identical null-set means: p 0 when the real arm is better, 1 when it is not')


# ---------------------------------------------------------------- rules and wording

def test_clear_pass() -> None:
    v = run()
    p = v['primary']
    assert [p[k]['status'] for k in ('H1', 'H2', 'H1b')] == ['pass', 'pass', 'pass']
    assert v['wording']['row'] == 1 and v['lockdown_check'] == {**v['lockdown_check'], 'run': True, 'triggered': False}
    h1 = p['H1']
    want = cv.ROWS[1].replace('X%', f"{cv.one_decimal(h1['pct'])}%").replace(
        'a to b', f"{cv.one_decimal(h1['pct_lo'])} to {cv.one_decimal(h1['pct_hi'])}")
    assert v['wording']['sentences'][0] == want and 'MAE 12.5% lower' in want
    assert v['wording']['sentences'][1].startswith('Weather known at the forecast origin also lowers')
    assert len(v['wording']['sentences']) == 2 and not v['warnings'] and not v['wording']['addendum_A1_applied']
    assert v['gate'] == {'g_pct': 12.5, 'threshold_pct': 13.0, 'plan_option_A': False}
    print(f'    row 1: "{want[:70]}..."; gate 12.5% -> A not run')


def test_clear_fail() -> None:
    v = run({'MET_PP': {'mae': 32.0}})
    p = v['primary']
    assert p['H1']['status'] == 'fail' and p['H2']['status'] == p['H1b']['status'] == cv.NOT_TESTED
    assert 'effect' in p['H2'] and 'lo' in p['H1b']                       # estimates still reported
    assert v['wording']['row'] == 4 and v['wording']['sentences'][0] == 'No weather claim. Reported as found.'
    assert v['lockdown_check'] == {'run': False} and not v['warnings']
    last = v['wording']['sentences'][-1]                                   # P passed: addendum A1, no "also"
    assert v['wording']['addendum_A1_applied'] and last.startswith('Weather known at the forecast origin lowers')
    assert ' also ' not in last and 'MAE 6.3% lower' in last
    print('    row 4; H2 and H1b "not tested in sequence" with estimates; addendum A1 drops "also"')


def test_h1b_fails() -> None:
    v = run({'MET': {'mae': 28.0}})
    assert [v['primary'][k]['status'] for k in ('H1', 'H2', 'H1b')] == ['pass', 'pass', 'fail']
    assert v['wording']['row'] == 2 and v['wording']['sentences'][0].endswith(
        'It adds no detectable skill beyond the weather of the forecast origin.')
    print('    row 2 when MET_PP does not beat MET')


def test_h2_threshold_exact() -> None:
    at = run({'MET_PP': {'short': 4.0}})                                 # excess exactly 2.0 pp
    below = run({'MET_PP': {'short': 3.875}})                            # excess 1.875 pp, p still tiny
    assert at['primary']['H2']['effect'] == 2.0 and at['primary']['H2']['status'] == 'pass'
    assert below['primary']['H2']['effect'] == 1.875 and below['primary']['H2']['p'] < 1e-6
    assert below['primary']['H2']['status'] == 'fail' and below['primary']['H1b']['status'] == cv.NOT_TESTED
    assert below['wording']['row'] == 3
    print('    excess 2.0 pp passes, 1.875 pp fails despite p < 1e-6 (row 3)')


def test_h1_needs_below_every_null() -> None:
    change = {f'POOL_PP_{j}': {'mae': 32.0} for j in range(9)}
    change['POOL_PP_9'] = {'mae': 28.0}
    change['MET_PP'] = {'mae': 28.25}
    h1 = run(change)['primary']['H1']
    assert h1['p'] < 0.05 and not h1['below_every_null'] and h1['status'] == 'fail'
    print(f'    p {h1["p"]:.3f} < 0.05 but one null set (28.0) is below the real arm (28.25): H1 fails')


def test_p_borderline() -> None:
    sd = null_sd([32.0 + o for o in OFF])
    se = sd * math.sqrt(1.1)
    crit = float(stats.t.ppf(0.95, 9))
    out = []
    for factor, want in ((1.01, 'pass'), (0.99, 'fail')):
        real = 32.0 - factor * crit * se
        h1 = run({'MET_PP': {'mae': real}})['primary']['H1']
        assert h1['below_every_null'] and h1['status'] == want, (factor, h1['p'])
        out.append(f'{h1["p"]:.4f} -> {want}')
    print(f'    t at 1.01 and 0.99 x the critical value: p {", ".join(out)}')


def test_lockdown_sentence() -> None:
    v = run(pre={'MET_PP': {'mae': 31.75}})
    assert v['primary']['H1']['status'] == 'pass' and v['lockdown_check']['triggered']
    assert v['wording']['sentences'][1] == cv.LOCKDOWN_SENTENCE
    print(f'    pre-lockdown p {v["lockdown_check"]["p"]:.3f} >= 0.05: lockdown sentence added after the main sentence')


def test_gate_exact_boundary() -> None:
    base = {f'{fam}_{j}': {'mae': 25.0 + o} for fam in ('POOL', 'POOL_PP') for j, o in enumerate(OFF)}
    at = run({**base, 'MET_PP': {'mae': 21.75}})['gate']                 # d 3.25, g exactly 13.0
    below = run({**base, 'MET_PP': {'mae': 21.78125}})['gate']           # g 12.875
    assert at['g_pct'] == 13.0 and at['plan_option_A'] is True
    assert below['g_pct'] == 12.875 and below['plan_option_A'] is False
    print('    g exactly 13.0% -> plan A; 12.875% -> A not run')


def test_operational_sentence() -> None:
    fail = run({'MET': {'mae': 32.0}})
    assert fail['secondary']['P_H1']['status'] == 'fail' and fail['secondary']['P_H2']['status'] == cv.NOT_TESTED
    assert fail['wording']['sentences'][-1] == cv.OPERATIONAL_FAIL
    ok = run()['wording']['sentences'][-1]
    assert ok.startswith('Weather known at the forecast origin also lowers') and 'MAE 6.3% lower' in ok   # 6.25
    assert [cv.one_decimal(x) for x in (6.25, 6.24999, -1.25, 12.0, 0.05)] == ['6.3', '6.2', '-1.3', '12.0', '0.1']
    print('    P fails -> "adds no detectable skill"; P passes -> filled "also lowers" sentence')


def test_e5_verbatim_rules() -> None:
    v = run()['secondary']['E5_sensitivity']['MET_PP']
    assert v['E5_verbatim_H1'] and v['E5_verbatim_H2'] and v['H1_form']['K'] == 4 and v['H1_form']['df'] == 3
    assert v['pre_lockdown_H1_form']['K'] == 4 and 'p' not in v['pre_lockdown_H1_form']
    v2 = run({'MET_PP': {'seas': 3.0}})['secondary']['E5_sensitivity']['MET_PP']
    assert v2['E5_verbatim_H1'] and not v2['E5_verbatim_H2']             # seasonal share outside the null range
    print('    E5 verbatim H1 and H2 pass by default; H2 fails when the seasonal share leaves the null range; K 4, df 3')


def test_descriptive_has_no_p_values() -> None:
    v = run()

    def walk(x: object) -> None:
        if isinstance(x, dict):
            assert 'p' not in x and 't' not in x, list(x)
            for y in x.values():
                walk(y)
    walk(v['descriptive'])
    walk(v['secondary']['H4_seasonal_excess'])
    assert set(v['descriptive']['per_city']) == {'Delhi', 'Mumbai'} and set(v['descriptive']['per_period']) == {'pre', 'lock'}
    assert 'lo' in v['descriptive']['per_period']['pre']['MET_PP_vs_POOL_PP_mae']
    print('    per period, per city, bands/groups and H4: estimates and 90% intervals, no p-values')


def test_weather_vs_none() -> None:
    w = run()['secondary']['weather_vs_none']
    assert w['BASE_minus_MET_PP']['effect'] == 4.0 and w['BASE_minus_MET']['effect'] == 2.0
    pool = w['BASE_minus_POOL_PP']
    se = math.sqrt(np.var(32.0 + 0.25 * Z, ddof=1) / 40 + null_sd([32.0 + o for o in OFF]) ** 2 / 10)
    assert pool['effect'] == 0.0 and pool['df'] == 9 and math.isclose(pool['se'], se, rel_tol=1e-12)
    print('    BASE against real arms (Welch) and against null families (null set as unit, df K-1)')


def test_wording_is_the_preregistered_text() -> None:
    text = PREREG.read_text(encoding='utf-8')
    sec9 = re.sub(r'\s*\n\s*', ' ', text.split('## 9. Wording')[1].split('## 10.')[0])
    quoted = re.findall(r'"([^"]+)"', sec9)
    mine = [cv.ROWS[1], cv.ROWS[2], cv.ROWS[3], cv.LOCKDOWN_SENTENCE, cv.OPERATIONAL_PASS, cv.OPERATIONAL_FAIL]
    assert quoted == mine, [(a, b) for a, b in zip(quoted, mine) if a != b]
    assert '| H1 fails | No weather claim. Reported as found. |' in sec9 and cv.ROWS[4] == 'No weather claim. Reported as found.'
    sec8 = re.sub(r'\s*\n\s*', ' ', text.split('## 8. Rules')[1].split('## 9.')[0])
    sec7 = re.sub(r'\s*\n\s*', ' ', text.split('## 7. Statistical')[1].split('## 8.')[0])
    assert 'e ≥ 2.0 percentage points' in sec8 and cv.H2_MIN_PP == 2.0
    assert 'only if g ≥ 13%' in sec8 and cv.GATE_PCT == 13.0
    assert 'S = 40 seeds' in sec7 and cv.SEEDS == tuple(range(40))
    assert 'one-sided α = 0.05' in sec7 and cv.ALPHA == 0.05 and '90% interval' in sec7 and cv.LEVEL == 0.90
    assert 'at least 150 test windows' in text and cv.MIN_CITY_TEST == 150
    a1 = re.sub(r'\s*\n\s*', ' ', ADDENDUM_A1.read_text(encoding='utf-8')).split('**Change.**')[1]
    assert re.findall(r'"([^"]+)"', a1)[0] == cv.OPERATIONAL_PASS_A1
    assert cv.OPERATIONAL_PASS_A1 == cv.OPERATIONAL_PASS.replace(' also ', ' ')       # A1 removes one word only
    print('    6 sentences equal section 9 and the A1 sentence equals the addendum, word for word; '
          'constants equal sections 6-8')


# ---------------------------------------------------------------- input checks and determinism

def test_incomplete_input_stops() -> None:
    pooled, city = tables()
    cases = {
        'a missing row': (pooled.iloc[1:], city),
        'a missing value': (pooled.assign(mae=pooled.mae.where(pooled.index != 5)), city),
        'a duplicated row': (pd.concat([pooled, pooled.iloc[:1]]), city),
        'an unknown arm': (pooled.assign(arm=pooled.arm.replace('POOL_0', 'POOL_X')), city),
        'a missing column': (pooled.drop(columns='met_rain'), city),
        'BASE with a weather share': (pooled.assign(met=np.where(pooled.arm == 'BASE', 1.0, pooled.met)), city),
        'a city under 150 windows': (pooled, city.assign(n=np.where(city.city == 'Mumbai', 149, city.n))),
        'an incomplete city table': (pooled, city.iloc[1:]),
    }
    for name, (p, c) in cases.items():
        try:
            cv.evaluate(p, c)
        except ValueError:
            continue
        raise AssertionError(f'{name} was accepted')
    print(f'    {len(cases)} kinds of broken input all stop the verdict')


def test_seed_option_and_write() -> None:
    """Default seeds are the pre-registered 0-39; a 2-seed table needs the explicit option and is flagged."""
    import tempfile
    pooled, city = tables()
    p2, c2 = pooled[pooled.seed < 2], city[city.seed < 2]
    try:
        cv.evaluate(p2, c2)
        raise AssertionError('a 2-seed table was accepted as a real result')
    except ValueError:
        pass
    v = cv.evaluate(p2, c2, seeds=(0, 1))
    assert v['seeds'] == [0, 1] and any('dry run' in w for w in v['warnings'])
    assert not run()['warnings'] and run()['seeds'] == list(range(40))
    with tempfile.TemporaryDirectory() as tmp:
        cv.write(v, Path(tmp), prefix='dry')
        raw = Path(tmp, 'dry_verdict.json').read_bytes() + Path(tmp, 'dry_verdict.txt').read_bytes()
        assert b'\r\n' not in raw and Path(tmp, 'dry_verdict.txt').exists()
    print('    default refuses 2 seeds; seeds=(0, 1) accepted and flagged as a dry run; files LF, prefix applied')


def test_rerun_identical() -> None:
    a, b = run(), run()
    assert cv.to_json(a) == cv.to_json(b) and cv.render(a) == cv.render(b)
    print(f'    JSON ({len(cv.to_json(a))} chars) and text identical on a rerun')


def test_climate_and_provenance_rendered() -> None:
    """The runner's climate table and provenance block reach the JSON and the text unchanged."""
    from c2x_features import MCOLS
    climate = pd.DataFrame([dict(city=c, feature=f, real_mean=1.0, pool_mean=0.875, real_sd=1.0, diff_in_sd=-0.125)
                            for c in ('Delhi', 'Mumbai') for f in MCOLS])
    prov = {'platform': 'laptop CPU', 'xgboost': '3.2.0', 'sha256 c2x_verdict.py': 'abc'}
    v = cv.evaluate(*tables(), climate=climate, provenance=prov)
    assert v['provenance'] == prov and len(v['secondary']['climate_check_full']) == 2 * len(MCOLS)
    med = v['secondary']['climate_check_median_diff_in_sd']
    assert set(med) == {'lblh', 'wind', 'lvent', 't2m', 'rh', 'sprecip'} and med['t2m']['seas'] == -0.125
    text = cv.render(v)
    assert 'climate check' in text and 'PROVENANCE' in text and 'platform: laptop CPU' in text
    assert 'ARM MEANS' in text and all(a in text for a in arm_names())
    print('    climate table (median per variable and band) and provenance appear in JSON and text')


TESTS = [test_climate_and_provenance_rendered, test_welch_matches_scipy, test_prediction_test_by_hand, test_zero_null_spread, test_clear_pass,
         test_clear_fail, test_h1b_fails, test_h2_threshold_exact, test_h1_needs_below_every_null, test_p_borderline,
         test_lockdown_sentence, test_gate_exact_boundary, test_operational_sentence, test_e5_verbatim_rules,
         test_descriptive_has_no_p_values, test_weather_vs_none, test_wording_is_the_preregistered_text,
         test_incomplete_input_stops, test_seed_option_and_write, test_rerun_identical]

if __name__ == '__main__':
    t0 = time.time()
    failed = 0
    for t in TESTS:
        try:
            t()
            print(f'PASS {t.__name__}', flush=True)
        except (Exception, SystemExit) as e:
            failed += 1
            print(f'FAIL {t.__name__}: {type(e).__name__}: {e}', flush=True)
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed in {time.time() - t0:.0f} s')
    sys.exit(1 if failed else 0)
