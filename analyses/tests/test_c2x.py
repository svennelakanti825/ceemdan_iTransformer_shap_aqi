"""Leakage and correctness tests for the C2 feature builder (task C2-T3; C2_PREREGISTRATION.md section 10).

Every test changes an input in memory on purpose and checks that only what may change does change. No file is
modified. No test-year prediction is made, so no C2 result is produced.

Coverage of the pre-registered checks:
  no look-ahead (t, t+1)            test_lookahead, test_day_t_plus_1_reaches_only_met_pp
  no AQI / pollutant info in weather test_no_aqi_or_pollutant_in_weather
  real and pool files kept apart    test_files_kept_apart
  no test data in fitting           test_test_targets_cannot_reach_fit, test_late_pollutants_cannot_reach_train_val
                                    (test-period AQI also enters the causal CEEMDAN channels of test windows only;
                                    that causality is tested in tests/test_c5_helper.py, rerun with this file)
  null rules                        test_pool_rule_worked_cases (+ the checks inside c2x_features.run_checks)
  alignment                         test_alignment_of_consecutive_windows
  bands                             test_bands_add_up
  window identity, splits, periods  test_windows_splits_periods
  arms and design                   test_arms_and_design
  hash rule, pinned inputs          test_hash_rule_and_inputs
  ERA5 days are IST days            test_era5_days_are_ist

Run:  python tests/test_c2x.py
"""
import hashlib
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'e1_verification'))
import c2x_features as cx  # noqa: E402
from common import FEATURES, load_df  # noqa: E402
from e1_leakage_contrast import PARAMS  # noqa: E402

VARS = ['blh', 'wind', 'vent', 't2m', 'rh', 'precip']
CUT = pd.Timestamp('2019-12-15')              # a test-year date for the look-ahead tests
LATE = pd.Timestamp('2019-06-30')             # the last validation target; validation inputs end the day before
_CACHE: dict = {}


def reference() -> cx.C2Data:
    if 'data' not in _CACHE:
        _CACHE['data'] = cx.build()
    return _CACHE['data']


def banks() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if 'banks' not in _CACHE:
        real, pool = cx.read_era5('era5_daily.csv'), cx.read_era5('era5_daily_pool.csv')
        _CACHE['banks'] = (real, pool, cx.bank_from(real), cx.bank_from(pool))
    return _CACHE['banks']


def scaled(met: pd.DataFrame, rows: np.ndarray) -> pd.DataFrame:
    """A copy with the 6 weather variables changed on the given rows (positive values stay positive)."""
    out = met.copy()
    out.loc[rows, VARS] = out.loc[rows, VARS] * 1.37 + 0.5
    return out


def same(a: np.ndarray, b: np.ndarray) -> bool:
    return a.shape == b.shape and np.array_equal(a, b)


def rows_all_differ(a: np.ndarray, b: np.ndarray) -> bool:
    return bool((a != b).any(axis=1).all())


def test_lookahead() -> None:
    """Changing all real ERA5 after day D leaves MET_PP for targets <= D and MET for origins <= D unchanged."""
    d = reference()
    real, _, _, pool_b = banks()
    blocks, _, _ = cx.weather_blocks(d.meta, cx.bank_from(scaled(real, (real.Date > CUT).to_numpy())), pool_b)
    tgt_ok, org_ok = (d.meta.target <= CUT).to_numpy(), (d.meta.origin <= CUT).to_numpy()
    assert same(blocks['MET_PP'][tgt_ok], d.blocks['MET_PP'][tgt_ok])
    assert same(blocks['MET_PP_LONG'][tgt_ok], d.blocks['MET_PP_LONG'][tgt_ok])
    assert same(blocks['MET'][org_ok], d.blocks['MET'][org_ok])
    assert rows_all_differ(blocks['MET_PP'][~tgt_ok], d.blocks['MET_PP'][~tgt_ok])      # the change did arrive
    assert rows_all_differ(blocks['MET'][~org_ok], d.blocks['MET'][~org_ok])
    print(f'    {tgt_ok.sum()} MET_PP rows and {org_ok.sum()} MET rows unchanged; every later row changed')


def test_day_t_plus_1_reaches_only_met_pp() -> None:
    """Changing ERA5 on day D only: the windows with target D change in MET_PP, not in MET (their origin is D-1)."""
    d = reference()
    real, _, _, pool_b = banks()
    blocks, _, _ = cx.weather_blocks(d.meta, cx.bank_from(scaled(real, (real.Date == CUT).to_numpy())), pool_b)
    on = (d.meta.target == CUT).to_numpy()
    assert on.sum() >= 10, on.sum()
    assert rows_all_differ(blocks['MET_PP'][on], d.blocks['MET_PP'][on])
    assert same(blocks['MET'][on], d.blocks['MET'][on])
    before = (d.meta.origin < CUT).to_numpy()
    assert same(blocks['MET'][before], d.blocks['MET'][before])
    assert same(blocks['MET_PP'][(d.meta.target < CUT).to_numpy()], d.blocks['MET_PP'][(d.meta.target < CUT).to_numpy()])
    print(f'    {on.sum()} windows with target {CUT.date()}: MET_PP changed, MET unchanged')


def test_no_aqi_or_pollutant_in_weather() -> None:
    """Weather blocks do not move when y or every pollutant reading changes; BASE does (sanity)."""
    d = reference()
    _, _, real_b, pool_b = banks()
    meta = d.meta.copy()
    meta['y'] = np.random.default_rng(1).uniform(0, 500, len(meta))
    blocks, _, _ = cx.weather_blocks(meta, real_b, pool_b)
    assert all(same(blocks[k], d.blocks[k]) for k in d.blocks)
    df = load_df()
    df.loc[:, FEATURES] = df[FEATURES] * 1.37 + 0.5               # NaN pattern unchanged, so calendars unchanged
    d2 = cx.build(df=df)
    assert all(same(d2.blocks[k], d.blocks[k]) for k in d.blocks), 'a weather block moved with the pollutants'
    pol = np.array([c.startswith('POL|') for c in d.base_cols])
    assert not same(d2.base[:, pol], d.base[:, pol]) and same(d2.base[:, ~pol], d.base[:, ~pol])
    print(f'    all {len(d.blocks)} weather blocks identical; only the pollutant columns of BASE changed')


def test_files_kept_apart() -> None:
    """Real-year ERA5 never reaches a pool null; pool ERA5 never reaches a real or E5 block."""
    d = reference()
    real, pool, real_b, pool_b = banks()
    b1, _, _ = cx.weather_blocks(d.meta, cx.bank_from(scaled(real, np.ones(len(real), bool))), pool_b)
    pools = [k for k in d.blocks if k.startswith('POOL')]
    others = [k for k in d.blocks if not k.startswith('POOL')]
    assert all(same(b1[k], d.blocks[k]) for k in pools)
    assert all(not same(b1[k], d.blocks[k]) for k in others)
    b2, _, _ = cx.weather_blocks(d.meta, real_b, cx.bank_from(scaled(pool, np.ones(len(pool), bool))))
    assert all(same(b2[k], d.blocks[k]) for k in others)
    assert all(not same(b2[k], d.blocks[k]) for k in pools)
    print(f'    {len(pools)} pool blocks depend only on the pool file; {len(others)} other blocks only on the real file')


def test_test_targets_cannot_reach_fit() -> None:
    """Changing every test target leaves the training and validation arrays of every arm, and a real fit, identical."""
    d = reference()
    meta2 = d.meta.copy()
    test = (meta2.split == 'test').to_numpy()
    meta2.loc[test, 'y'] = meta2.loc[test, 'y'] * 3 + 100
    d2 = cx.C2Data(meta2, d.base, d.base_cols, d.blocks, d.block_cols, d.lookups, [])
    for arm in cx.arm_names():
        a, b = cx.design(d, arm), cx.design(d2, arm)
        for k in ('X_train', 'y_train', 'X_val', 'y_val', 'X_test'):
            assert same(a[k], b[k]), (arm, k)
        assert not same(a['y_test'], b['y_test'])
    boosters = []
    for data in (d, d2):
        z = cx.design(data, 'MET_PP')
        m = xgb.XGBRegressor(random_state=0, **PARAMS)
        m.fit(z['X_train'], z['y_train'], eval_set=[(z['X_val'], z['y_val'])], verbose=False)
        boosters.append(bytes(m.get_booster().save_raw('ubj')))          # no test prediction is made
    assert boosters[0] == boosters[1], 'the fitted model changed with the test targets'
    print(f'    {len(cx.arm_names())} arms: train/val arrays identical; MET_PP seed-0 booster byte-identical '
          f'({len(boosters[0])} bytes)')


def test_late_pollutants_cannot_reach_train_val() -> None:
    """Changing every pollutant reading from 2019-06-30 on leaves all training and validation inputs identical.

    Catches a fill constant or calendar step that reads later data (N1, D1)."""
    d = reference()
    df = load_df()
    late = pd.to_datetime(df['Date']) >= LATE
    df.loc[late, FEATURES] = df.loc[late, FEATURES] * 1.37 + 0.5
    d2 = cx.build(df=df)
    assert same(d2.meta[['city', 'split', 'origin', 'target']].to_numpy(),
                d.meta[['city', 'split', 'origin', 'target']].to_numpy())
    a, b = cx.design(d, 'MET_PP'), cx.design(d2, 'MET_PP')
    for k in ('X_train', 'y_train', 'X_val', 'y_val'):
        assert same(a[k], b[k]), k
    moved = (d.meta.origin >= LATE).to_numpy() & (d.meta.split == 'test').to_numpy()
    assert rows_all_differ(d2.base[moved], d.base[moved])
    print(f'    train and val inputs identical; all {moved.sum()} test windows with origin >= {LATE.date()} changed')


def test_pool_rule_worked_cases() -> None:
    cases = [('2016-02-29', 0, '2006-02-28'), ('2019-12-31', 3, '2012-12-31'), ('2020-01-01', 9, '2009-01-01'),
             ('2015-07-01', 0, '2005-07-01'), ('2020-07-01', 5, '2005-07-01')]
    for own, j, want in cases:
        got = cx.pool_dates(pd.DatetimeIndex([own]), j)[0]
        assert got == pd.Timestamp(want), (own, j, got)
    own = pd.DatetimeIndex([f'{y}-06-15' for y in range(2015, 2021)])
    seen = {y: set() for y in range(2015, 2021)}
    for j in range(cx.N_POOL):
        py = cx.pool_dates(own, j).year
        assert len(set(py)) == 6 and all(2005 <= p <= 2014 for p in py), (j, list(py))
        for y, p in zip(range(2015, 2021), py):
            seen[y].add(p)
    assert all(v == set(range(2005, 2015)) for v in seen.values())
    print(f'    {len(cases)} worked cases; each set maps the 6 own years to 6 pool years; each own year meets all 10')


def test_alignment_of_consecutive_windows() -> None:
    """Where a city's next window starts the day after, its t-block equals this window's t+1-block."""
    d = reference()
    m = d.meta
    nxt = ((m.city.to_numpy()[1:] == m.city.to_numpy()[:-1])
           & (m.origin.to_numpy()[1:] == m.target.to_numpy()[:-1]))
    i = np.flatnonzero(nxt)
    assert len(i) > 15000, len(i)
    assert same(d.blocks['MET_PP'][i], d.blocks['MET'][i + 1])
    for j in range(cx.N_POOL):
        assert same(d.blocks[f'POOL_PP_{j}'][i], d.blocks[f'POOL_{j}'][i + 1]), j
    for k in range(1, cx.N_E5 + 1):
        assert same(d.blocks[f'E5NULL_PP_{k}'][i], d.blocks[f'E5NULL_{k}'][i + 1]), k
    print(f'    {len(i)} consecutive pairs aligned in MET, all 10 pool sets and all 4 E5 sets')


def test_bands_add_up() -> None:
    """For 50 random windows, the four bands of each variable sum to that variable on the lookup date."""
    d = reference()
    real, pool, _, _ = banks()
    rng = np.random.default_rng(7)
    tf = {'lblh': lambda t: np.log(t.blh), 'wind': lambda t: t.wind, 'lvent': lambda t: np.log(t.vent),
          't2m': lambda t: t.t2m, 'rh': lambda t: t.rh, 'sprecip': lambda t: np.sqrt(t.precip)}
    cols = d.block_cols['MET_PP']
    n = 0
    for r in rng.choice(len(d.meta), 50, replace=False):
        c, tgt = d.meta.city[r], d.meta.target[r]
        j = int(rng.integers(cx.N_POOL))
        for block, table, date in (('MET_PP', real, tgt), (f'POOL_PP_{j}', pool, cx.pool_dates(pd.DatetimeIndex([tgt]), j)[0])):
            row = table[(table.City == c) & (table.Date == date)].iloc[0]
            for v, f in tf.items():
                s = sum(d.blocks[block][r, cols.index(f'MET|{v}|{b}')] for b in cx.BANDS)
                assert abs(s - f(row)) <= 1e-9 * max(1.0, abs(f(row))), (block, c, date, v, s, f(row))
                n += 1
    print(f'    {n} band sums checked (real and pool)')


def test_windows_splits_periods() -> None:
    d = reference()
    m = d.meta
    assert m.city.nunique() == cx.N_CITIES and m.split.value_counts().to_dict() == cx.EXPECTED_WINDOWS
    tr, va, te = (m[m.split == s] for s in cx.SPLITS)
    assert tr.target.max() < pd.Timestamp('2019-04-01')
    assert va.target.min() >= pd.Timestamp('2019-04-01') and va.target.max() <= pd.Timestamp('2019-06-30')
    assert te.target.min() >= pd.Timestamp('2019-07-01') and te.target.max() <= pd.Timestamp('2020-07-01')
    assert set(m.period[m.split != 'test']) == {'na'}
    assert ((te.period == 'pre') == (te.target < cx.LOCKDOWN_START)).all() and set(te.period) == {'pre', 'lock'}
    for c, g in m.groupby('city', sort=False):                # within a city, train < val < test in time
        order = g.split.map({'train': 0, 'val': 1, 'test': 2}).to_numpy()
        assert (np.diff(order) >= 0).all() and g.target.is_monotonic_increasing, c
    print(f'    splits by target date as pre-registered; periods {te.period.value_counts().to_dict()}')


def test_arms_and_design() -> None:
    d = reference()
    arms = cx.arm_names()
    assert len(arms) == len(set(arms)) == 32 and arms[0] == 'BASE'
    assert set(arms) - {'BASE'} == set(d.blocks)
    widths = {}
    for arm in arms:
        z = cx.design(d, arm)
        rows = np.concatenate([z[f'rows_{s}'] for s in cx.SPLITS])
        assert np.array_equal(np.sort(rows), np.arange(len(d.meta))), arm          # disjoint and complete
        assert len(z['cols']) == z['X_train'].shape[1] == z['X_test'].shape[1], arm
        widths[len(z['cols'])] = widths.get(len(z['cols']), 0) + 1
    assert widths == {137: 1, 161: 30, 149: 1}, widths
    try:
        cx.design(d, 'NOT_AN_ARM')
        raise AssertionError('unknown arm accepted')
    except KeyError:
        pass
    print(f'    32 arms; widths {widths}; splits disjoint and complete for every arm')


def test_hash_rule_and_inputs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lf, crlf, binary = Path(tmp, 'a.csv'), Path(tmp, 'b.csv'), Path(tmp, 'c.npz')
        lf.write_bytes(b'x,y\n1,2\n')
        crlf.write_bytes(b'x,y\r\n1,2\r\n')
        binary.write_bytes(b'x,y\r\n1,2\r\n')
        assert cx.sha256_rule(lf) == cx.sha256_rule(crlf) == hashlib.sha256(b'x,y\n1,2\n').hexdigest()
        assert cx.sha256_rule(binary) == hashlib.sha256(b'x,y\r\n1,2\r\n').hexdigest()
    line = cx.verify_inputs()[0]
    assert '30 pinned files and 2 raw ERA5 hashes match' in line, line
    assert 'pre-registration and addenda A1 and A2 hashes are the approved ones' in line, line
    print('    CRLF and LF text hash the same; binary hashed as bytes; all pinned inputs verified')


def test_era5_days_are_ist() -> None:
    """Both ERA5 files come from the same request, in Asia/Kolkata days; the pool download changed only the dates."""
    import fetch_era5 as fe
    import fetch_era5_pool as fp
    assert 'timezone=Asia%2FKolkata' in fe.URL and 'models=era5' in fe.URL and 'wind_speed_unit=ms' in fe.URL
    assert fe.URL.count(fp.ORIGINAL_RANGE) == 1
    pool_url = fe.URL.replace(fp.ORIGINAL_RANGE, fp.POOL_RANGE)
    assert pool_url.replace(fp.POOL_RANGE, '') == fe.URL.replace(fp.ORIGINAL_RANGE, '')
    print('    request uses Asia/Kolkata days, model era5, m/s; the pool request differs only in its dates')


TESTS = [test_windows_splits_periods, test_arms_and_design, test_hash_rule_and_inputs, test_pool_rule_worked_cases,
         test_lookahead, test_day_t_plus_1_reaches_only_met_pp, test_no_aqi_or_pollutant_in_weather,
         test_files_kept_apart, test_alignment_of_consecutive_windows, test_bands_add_up,
         test_test_targets_cannot_reach_fit, test_late_pollutants_cannot_reach_train_val, test_era5_days_are_ist]

if __name__ == '__main__':
    t0 = time.time()
    failed = 0
    for t in TESTS:
        t1 = time.time()
        try:
            t()
            print(f'PASS {t.__name__} ({time.time() - t1:.0f} s)', flush=True)
        except (Exception, SystemExit) as e:                  # report every failure (a STOP too), exit non-zero
            failed += 1
            print(f'FAIL {t.__name__}: {type(e).__name__}: {e}', flush=True)
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed in {time.time() - t0:.0f} s')
    sys.exit(1 if failed else 0)
