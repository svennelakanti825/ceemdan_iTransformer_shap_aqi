"""Tests for the C2 runner (task C2-T5): shares, one fit, parts, output files and the real-run guards.

Fits here use only the made-up dry-run target (independent noise), so no real C2 result is produced or seen.

Run:  python tests/test_c2_runner.py
"""
import io
import json
import re
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'e1_verification'))
import c2_xgb_confirm as rn  # noqa: E402
import c2x_features as cx  # noqa: E402
import c2x_verdict as cv  # noqa: E402

_CACHE: dict = {}


def real() -> cx.C2Data:
    if 'real' not in _CACHE:
        _CACHE['real'] = cx.build()
    return _CACHE['real']


def dry() -> cx.C2Data:
    if 'dry' not in _CACHE:
        _CACHE['dry'] = rn.load(True)
    return _CACHE['dry']


def test_shares_against_independent_grouping() -> None:
    """Group shares equal an independent computation that groups the column names with regular expressions."""
    cols = cx.design(real(), 'MET_PP')['cols']
    absc = np.abs(np.random.default_rng(5).normal(size=(300, len(cols)))).astype(np.float32)
    got = rn.shares(absc, rn.group_masks(cols))
    c = pd.Series(absc.mean(axis=0, dtype=np.float64), index=cols)
    rules = {'pol': r'^POL\|', 'dec_osc': r'^DEC\|IMF[1-4]\|', 'dec_slow': r'^DEC\|Slow\|', 'city': r'^CITY\|',
             'met': r'^MET\|', 'met_syn': r'^MET\|.*\|syn$', 'met_intra': r'^MET\|.*\|intra$',
             'met_subs': r'^MET\|.*\|subs$', 'met_seas': r'^MET\|.*\|seas$', 'met_disp': r'^MET\|(lblh|wind|lvent)\|',
             'met_temp': r'^MET\|t2m\|', 'met_hum': r'^MET\|rh\|', 'met_rain': r'^MET\|sprecip\|'}
    want = {k: 100 * c[[bool(re.search(p, x)) for x in cols]].sum() / c.sum() for k, p in rules.items()}
    assert list(got) == rn.SHARE_ORDER == cv.POOLED_COLS[5:]
    assert all(abs(got[k] - want[k]) < 1e-9 for k in rules), {k: (got[k], want[k]) for k in rules}
    assert abs(sum(got[k] for k in ('pol', 'dec_osc', 'dec_slow', 'city', 'met')) - 100) < 1e-9
    assert abs(sum(got[k] for k in ('met_syn', 'met_intra', 'met_subs', 'met_seas')) - got['met']) < 1e-9
    assert abs(sum(got[k] for k in ('met_disp', 'met_temp', 'met_hum', 'met_rain')) - got['met']) < 1e-9
    base = rn.shares(absc[:, :137], rn.group_masks(cols[:137]))
    assert all(base[k] == 0 for k in rn.SHARE_ORDER if k.startswith('met'))
    print('    13 shares equal a regex grouping; groups partition the columns; BASE weather shares are 0')


def test_dry_target_is_independent_noise() -> None:
    d, r = dry(), real()
    want = np.random.default_rng(rn.DRY_SEED).normal(rn.DRY_MEAN, rn.DRY_SD, len(r.meta))
    assert np.array_equal(d.meta['y'].to_numpy(), want)
    corr = float(np.corrcoef(want, r.meta['y'].to_numpy())[0, 1])
    assert abs(corr) < 0.03, corr
    assert np.array_equal(d.base, r.base) and all(np.array_equal(d.blocks[k], r.blocks[k]) for k in r.blocks)
    assert d.meta.drop(columns='y').equals(r.meta.drop(columns='y'))
    z = cx.design(d, 'MET_PP')
    assert np.array_equal(z['y_train'], want[z['rows_train']]) and np.array_equal(z['y_test'], want[z['rows_test']])
    print(f'    made-up target = fixed-seed noise, correlation with real AQI {corr:+.3f}; every input unchanged')


def test_fit_one_on_dry_target() -> None:
    d = dry()
    r = rn.fit_one(d, 'MET_PP', 0, n_jobs=8)
    assert r['gap'] < rn.ADDITIVITY_TOL and r['pred'].dtype == np.float32 and len(r['pred']) == 6171
    per = {p['period']: p for p in r['pooled']}
    assert list(per) == list(cv.PERIODS) and (per['all']['n'], per['pre']['n'], per['lock']['n']) == (6171, 4502, 1669)
    for p in r['pooled']:
        assert abs(sum(p[k] for k in ('pol', 'dec_osc', 'dec_slow', 'city', 'met')) - 100) < 1e-9
        assert list(p) == ['arm', 'seed', 'period'] + cv.POOLED_COLS
    te = d.meta[d.meta.split == 'test']
    counts = te.city.value_counts()
    assert {c['city'] for c in r['city']} == set(counts[counts >= cv.MIN_CITY_TEST].index)
    assert all(c['n'] == counts[c['city']] for c in r['city'])
    assert all(list(c) == ['arm', 'seed', 'city'] + cv.CITY_COLS for c in r['city'])
    again = rn.fit_one(d, 'MET_PP', 0, n_jobs=8)
    assert again['pooled'] == r['pooled'] and np.array_equal(again['pred'], r['pred'])
    print(f'    additivity gap {r["gap"]:.1e}; periods 6171/4502/1669; {len(r["city"])} cities >= 150; '
          'a second fit is identical')


def test_parts_and_files() -> None:
    d = dry()
    r = rn.fit_one(d, 'BASE', 1, n_jobs=8)
    with tempfile.TemporaryDirectory() as tmp:
        parts = Path(tmp)
        assert not rn.done(parts, 'BASE', 1)
        npy, js = rn.part_paths(parts, 'BASE', 1)
        npy.write_bytes(b'')                                       # an npy without its json is not finished
        assert not rn.done(parts, 'BASE', 1)
        key = rn.run_key(True, 8, 'cpu')
        rn.save_part(parts, 'BASE', 1, r, key)
        assert rn.done(parts, 'BASE', 1) and not list(parts.glob('*.tmp'))
        payload = json.loads(js.read_text(encoding='utf-8'))
        assert payload['pooled'] == r['pooled'] and np.array_equal(np.load(npy), r['pred'])
        assert payload['run_key'] == key and payload['machine'] == rn.machine()
        rn.check_parts_key(parts, key)                             # same key: accepted
        good = npy.read_bytes()
        npy.write_bytes(good[:-8])                                 # predictions cut off by an interruption
        assert not rn.done(parts, 'BASE', 1)
        bad = np.load(io.BytesIO(good)).copy()
        bad[0] += 1.0                                              # predictions changed after the fit
        np.save(npy, bad)
        assert not rn.done(parts, 'BASE', 1)
        npy.write_bytes(good)
        assert rn.done(parts, 'BASE', 1)
        keys = {rn.run_key(True, 2, 'cpu'), rn.run_key(False, 8, 'cpu'), rn.run_key(True, 8, 'cuda')}
        assert key not in keys and len(keys) == 3                  # thread count, mode and device change the key
        for other in keys:
            try:
                rn.check_parts_key(parts, other)
                raise AssertionError('a part from another run key was accepted')
            except ValueError:
                pass
        arrays = {'pred': np.ones((2, 3), np.float32), 'arms': np.array(['BASE', 'MET']), 'n': np.arange(4)}
        a, b = parts / 'a.npz', parts / 'b.npz'
        rn.save_npz(a, arrays)
        time.sleep(2.1)                                            # a zip date would change between the writes
        rn.save_npz(b, arrays)
        assert a.read_bytes() == b.read_bytes()
        with zipfile.ZipFile(a) as zf:
            assert all(i.date_time == (1980, 1, 1, 0, 0, 0) and i.create_system == 3 for i in zf.infolist())
        with np.load(a, allow_pickle=False) as loaded:             # closed again (Windows keeps open files locked)
            assert all(np.array_equal(loaded[k], v) for k, v in arrays.items())
        rn.write_csv(pd.DataFrame({'x': [1.5, 2.25]}), parts / 'c.csv')
        assert b'\r\n' not in (parts / 'c.csv').read_bytes()
    print('    parts finish only with their json and matching predictions (cut-off or changed ones are refitted); '
          'other run keys refused; npz bytes identical two seconds apart and readable; CSV LF')


def test_request_guards() -> None:
    arms, seeds, n = cx.arm_names(), cv.SEEDS, rn.xgb_threads(rn.processors())   # n: most threads XGBoost honours
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        rn.check_request(False, False, arms, seeds, 'cpu', out, 4, 2, ('Linux', 'x86_64'))   # a valid real request (A2)
        rn.check_request(True, False, arms, (0, 1), 'cpu', out, 1, n)        # a dry run with every usable thread
        lin = ('Linux', 'x86_64')
        bad = {'2 seeds': (False, False, arms, (0, 1), 'cpu', out, 1, 2, lin),
               '31 arms': (False, False, arms[:-1], seeds, 'cpu', out, 1, 2, lin),
               'GPU real run': (False, False, arms, seeds, 'cuda', out, 1, 2, lin),
               'real run on Windows (A2)': (False, False, arms, seeds, 'cpu', out, 1, 2, ('Windows', 'AMD64')),
               'real run on macOS (A2)': (False, False, arms, seeds, 'cpu', out, 1, 2, ('Darwin', 'arm64')),
               'real run on ARM Linux (A2)': (False, False, arms, seeds, 'cpu', out, 1, 2, ('Linux', 'aarch64')),
               'real run with n_jobs 1 (A2)': (False, False, arms, seeds, 'cpu', out, 1, 1, lin),
               'unknown device': (True, False, arms, seeds, 'tpu', out, 1, 2),
               'dry run into the real folder': (True, False, arms, (0, 1), 'cpu', cx.OUT, 1, 2),
               'timing into the real folder': (False, True, arms, (0, 1), 'cpu', cx.OUT, 1, 2),
               'n_jobs 0 (all processors)': (False, False, arms, seeds, 'cpu', out, 1, 0, lin),
               'n_jobs -1 (all processors)': (True, False, arms, (0, 1), 'cpu', out, 1, -1),
               'processes 0': (False, False, arms, seeds, 'cpu', out, 0, 2, lin),
               'n_jobs above the processors (real)': (False, False, arms, seeds, 'cpu', out, 1, n + 1, lin),
               'n_jobs above the processors (dry)': (True, False, arms, (0, 1), 'cpu', out, 1, n + 1),
               'n_jobs above the processors (timing)': (False, True, arms, (0, 1), 'cpu', out, 1, n + 1)}
        (out / 'c2x_verdict.json').write_text('{}', encoding='utf-8')
        bad['a finished run in the folder'] = (False, False, arms, seeds, 'cpu', out, 1, 2, lin)
        for name, args in bad.items():
            try:
                rn.check_request(*args)
            except ValueError:
                continue
            raise AssertionError(f'{name} was accepted')
        try:
            rn.main(['--arms', 'BASE', '--out', str(out / 'x')])
            raise AssertionError('--arms accepted for a real run')
        except ValueError:
            pass
        if (rn.platform.system(), rn.platform.machine()) != rn.REAL_PLATFORM:   # this machine is not the A2 platform
            try:
                rn.main(['--processes', '1', '--out', str(out / 'y')])
                raise AssertionError(f'a real run was accepted on {rn.platform.system()}')
            except ValueError:
                pass
    print(f'    {len(bad) + 1} kinds of request refused before any fit; a full real request accepted')


def test_thread_count_rule() -> None:
    """xgb_threads follows XGBoost 3.2.0's rule: processors, OMP variables and the cgroup quota lower n_jobs."""
    n = rn.processors()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        assert rn.cgroup_cpus(root) == -1                                    # no cgroup files
        (root / 'cpu.max').write_text('max 100000\n')
        assert rn.cgroup_cpus(root) == -1                                    # v2 without a quota
        for text, want in (('200000 100000\n', 2), ('150000 100000\n', 2), ('50000 100000\n', 1)):
            (root / 'cpu.max').write_text(text)
            assert rn.cgroup_cpus(root) == want, (text, rn.cgroup_cpus(root))   # v2 rounds up
        assert rn.xgb_threads(8, env={}, cgroup_root=root) == min(1, n)     # the quota lowers n_jobs
        (root / 'cpu.max').unlink()
        (root / 'cpu').mkdir()
        (root / 'cpu' / 'cpu.cfs_period_us').write_text('100000\n')
        for quota, want in (('250000', 2), ('-1', -1), ('50000', 1)):
            (root / 'cpu' / 'cpu.cfs_quota_us').write_text(quota + '\n')
            assert rn.cgroup_cpus(root) == want, (quota, rn.cgroup_cpus(root))  # v1 rounds down
    none = Path(tempfile.gettempdir()) / 'no_cgroup_here'
    assert rn.xgb_threads(2, env={}, cgroup_root=none) == min(2, n)
    assert rn.xgb_threads(n + 5, env={}, cgroup_root=none) == n
    assert rn.xgb_threads(8, env={'OMP_NUM_THREADS': '3'}, cgroup_root=none) == min(3, n)
    assert rn.xgb_threads(8, env={'OMP_NUM_THREADS': '4,2'}, cgroup_root=none) == min(4, n)
    assert rn.xgb_threads(8, env={'OMP_THREAD_LIMIT': '2'}, cgroup_root=none) == min(2, n)
    assert rn.xgb_threads(2, env={'OMP_NUM_THREADS': ''}, cgroup_root=none) == min(2, n)
    print(f'    cgroup v1/v2 quotas, OMP_NUM_THREADS, OMP_THREAD_LIMIT and {n} processors lower n_jobs as XGBoost does')


def test_xgboost_caps_threads_silently() -> None:
    """The installed XGBoost really lowers n_jobs above the processors, without a message: n_jobs = processors and
    n_jobs = processors + 8 give the same predictions. Made-up target, fixed 60 trees."""
    import xgboost as xgb
    from e1_leakage_contrast import PARAMS
    z, n = cx.design(dry(), 'MET_PP'), rn.processors()

    def pred(n_jobs: int) -> np.ndarray:
        params = dict(PARAMS, n_estimators=60, early_stopping_rounds=None)
        m = xgb.XGBRegressor(random_state=0, n_jobs=n_jobs, **params).fit(z['X_train'], z['y_train'], verbose=False)
        return m.predict(z['X_val'])

    p_n, p_more, p_2 = pred(n), pred(n + 8), pred(2)
    assert np.array_equal(p_n, p_more), 'n_jobs above the processors was not lowered to the processors'
    print(f'    n_jobs {n + 8} gives the same model as n_jobs {n} ({n} processors); n_jobs 2 differs from n_jobs {n}: '
          f'{not np.array_equal(p_n, p_2)}')


def test_scripts_listed_for_provenance() -> None:
    assert all(p.is_file() for p in rn.SCRIPTS), [p for p in rn.SCRIPTS if not p.is_file()]
    assert {p.name for p in rn.SCRIPTS} >= {'c2_xgb_confirm.py', 'c2x_features.py', 'c2x_verdict.py'}
    print(f'    {len(rn.SCRIPTS)} scripts are hashed into every verdict')


TESTS = [test_scripts_listed_for_provenance, test_shares_against_independent_grouping, test_dry_target_is_independent_noise,
         test_fit_one_on_dry_target, test_parts_and_files, test_request_guards, test_thread_count_rule,
         test_xgboost_caps_threads_silently]

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
