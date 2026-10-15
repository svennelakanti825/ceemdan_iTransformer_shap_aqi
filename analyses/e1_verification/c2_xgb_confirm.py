"""C2 runner (task C2-T5): the pre-registered C2 experiment end to end.

Rules: C2_PREREGISTRATION.md (sections 4-6 and 10) and addenda A1 (wording) and A2 (platform). Inputs come from
c2x_features, the verdict from c2x_verdict.

  Real run (T6):  python c2_xgb_confirm.py --processes P --out <new folder>    (Linux x86-64, n_jobs 2: addendum A2)
                  -> outputs/c2x_pooled.csv, c2x_city.csv, c2x_predictions.npz, c2x_verdict.json, c2x_verdict.txt
  Dry run (T5):   python c2_xgb_confirm.py --dry-run --seeds 0 1 --out outputs/dryrun/A
  Timing (T5):    python c2_xgb_confirm.py --timing --processes P --n-jobs J

Per fit (arm x seed):
- XGBRegressor(random_state=seed, n_jobs=J, **E1 PARAMS) is fitted on the training rows, with early stopping on the
  validation rows.
- Test predictions use the best iteration.
- Exact TreeSHAP uses the same best iteration.
- Additivity is checked, and the run stops above 0.01 AQI units.
- MAE, RMSE, R2 and the group shares are computed for the full test year, pre-lockdown and lockdown/Unlock, and per
  city (cities with at least 150 test windows).

Resuming:
- Each finished fit is saved as a part: a .npy and then a .json, written last and atomically. The json records the
  run key, the SHA-256 of the predictions and the machine that made the fit (addendum A2.3).
- A restart skips finished fits whose predictions match their recorded SHA-256, so a part damaged by an interruption
  is refitted. Parts made under another run key (other code, inputs, versions, mode, thread count or device) are
  never mixed in: the run stops instead.
- The final files are always assembled from the parts in fixed arm x seed order, so an interrupted run gives the
  same bytes as an uninterrupted one.

Outputs carry no timestamps and use LF line endings, and the .npz is written with a fixed zip date. Timing goes to
run_log.log, which is git-ignored.

Dry run: before anything is fitted, a made-up target replaces AQI: independent normal noise with a fixed seed, built
from no AQI, feature or date. It therefore cannot carry information about the real weather effect.

Timing mode also writes fingerprints_<device>_p<P>_t<J>.json: the SHA-256 of each timed model's full 400-tree test
predictions and 300-tree SHAP values (made-up target). Two machines with equal fingerprints build identical
full-size models. The dry run cannot show this, because early stopping on noise keeps only a few trees.

Thread count: XGBoost silently lowers n_jobs to the processors this process may use (and to OMP_NUM_THREADS,
OMP_THREAD_LIMIT and a Linux cgroup CPU quota). The thread count changes the results (T5 dry run), so a request that
XGBoost would not honour is refused, and the recorded n_jobs is always the number of threads used.

Guards (every mode): n_jobs and processes fixed and >= 1, and n_jobs honoured by XGBoost on this machine.
Real-run guards: all 32 arms, seeds 0-39, CPU, Linux x86-64, n_jobs 2 (addendum A2), and an output folder without
a finished verdict.
Worker processes are always started with 'spawn' (the Windows default), so Linux runs the same way.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import multiprocessing
import os
import platform
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import xgboost as xgb

import c2x_features as cx
import c2x_verdict as cv
from e1_leakage_contrast import PARAMS

HERE = cx.HERE
TESTS = cx.REPO / 'Implementation' / 'revision_1' / 'tests'
SCRIPTS = [HERE / 'c2_xgb_confirm.py', HERE / 'c2x_features.py', HERE / 'c2x_verdict.py',
           TESTS / 'test_c2x.py', TESTS / 'test_c2x_verdict.py', TESTS / 'test_c2_runner.py']
DRY_SEED, DRY_MEAN, DRY_SD = 20261010, 100.0, 30.0
ADDITIVITY_TOL = 0.01
TIMING_TREES, TIMING_SHAP_TREES = 400, 300            # about E5's trained trees (best 129-352, + 100 rounds)
TIMING_ARMS = ['BASE', 'MET', 'MET_PP', 'MET_PP_LONG', 'POOL_PP_0', 'POOL_0', 'E5NULL_PP_1', 'E5NULL_1']
REAL_N_JOBS = 2                                        # addendum A2.1
REAL_PLATFORM = ('Linux', 'x86_64')                   # addendum A2.1: (platform.system(), platform.machine())
SHARE_ORDER = ['pol', 'dec_osc', 'dec_slow', 'city', 'met', 'met_syn', 'met_intra', 'met_subs', 'met_seas',
               'met_disp', 'met_temp', 'met_hum', 'met_rain']
assert SHARE_ORDER == cv.POOLED_COLS[5:]

_DATA: cx.C2Data | None = None                         # one build per process
SPAWN = multiprocessing.get_context('spawn')


# ---------------------------------------------------------------- machine

def cgroup_cpus(root: Path = Path('/sys/fs/cgroup')) -> int:
    """XGBoost 3.2.0 GetCfsCPUCount: the Linux cgroup CPU quota in whole CPUs, or -1 if there is none.
    cgroup v2 cpu.max 'quota period' rounds up. 'max period' means no quota. cgroup v1 quota / period rounds down."""
    try:
        v2 = root / 'cpu.max'
        if v2.is_file():
            a, b = (v2.read_text().split() + ['', ''])[:2]
            return max(-(-int(a) // int(b)), 1) if a.isdigit() and b.isdigit() and int(a) > 0 and int(b) > 0 else -1
        q, p = root / 'cpu' / 'cpu.cfs_quota_us', root / 'cpu' / 'cpu.cfs_period_us'
        if q.is_file() and p.is_file():
            quota, period = int(q.read_text().split()[0]), int(p.read_text().split()[0])
            return max(quota // period, 1) if quota > 0 and period > 0 else -1
    except (OSError, ValueError, IndexError):
        return -1
    return -1


def processors() -> int:
    """Logical processors this process may use (the affinity mask where Python can read it)."""
    return (getattr(os, 'process_cpu_count', None) or os.cpu_count)() or 1


def xgb_threads(n_jobs: int, env: dict | None = None, cgroup_root: Path = Path('/sys/fs/cgroup')) -> int:
    """Threads XGBoost 3.2.0 uses for a fixed n_jobs >= 1 (src/common/threading_utils.cc OmpGetNumThreads and
    src/context.cc Context::Threads): n_jobs, lowered to the processors, OMP_NUM_THREADS, OMP_THREAD_LIMIT and the
    cgroup CPU quota."""
    env = os.environ if env is None else env
    caps = [n_jobs, processors()]
    for var in ('OMP_NUM_THREADS', 'OMP_THREAD_LIMIT'):
        first = env.get(var, '').split(',')[0].strip()
        if first.isdigit() and int(first) > 0:
            caps.append(int(first))
    quota = cgroup_cpus(cgroup_root)
    if quota > 0:
        caps.append(quota)
    return max(min(caps), 1)


def cpu_model() -> str:
    """The processor's marketing name, for the provenance block."""
    try:
        if sys.platform.startswith('linux'):
            for line in Path('/proc/cpuinfo').read_text().splitlines():
                if line.startswith('model name'):
                    return line.split(':', 1)[1].strip()
        if sys.platform == 'win32':
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k:
                return str(winreg.QueryValueEx(k, 'ProcessorNameString')[0]).strip()
    except OSError:
        pass
    return platform.processor() or 'unknown'


def machine() -> str:
    """The machine that makes a fit, recorded in its part (addendum A2.3)."""
    return f'{cpu_model()} | {platform.system()} {platform.machine()} | {processors()} processors'


def run_key(dry: bool, n_jobs: int, device: str) -> str:
    """SHA-256 of everything that determines a fit: mode, thread count, device, operating system, library versions,
    the approved documents, every script and every input. Parts made under another key are never mixed."""
    key = {'mode': 'dry' if dry else 'real', 'n_jobs': n_jobs, 'device': device,
           'system': [platform.system(), platform.machine()],
           'versions': [platform.python_version(), np.__version__, pd.__version__, scipy.__version__, xgb.__version__],
           'documents': [cx.PREREG_SHA256, cx.ADDENDUM_A1_SHA256, cx.ADDENDUM_A2_SHA256],
           'scripts': {s.name: cx.sha256_rule(s) for s in SCRIPTS},
           'inputs': [want for want, _, _ in cx.appendix_a()]}
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------- inputs

def dry_target(n: int) -> np.ndarray:
    """The made-up dry-run target: independent normal noise. No AQI, feature or date is used."""
    return np.random.default_rng(DRY_SEED).normal(DRY_MEAN, DRY_SD, n)


def load(dry: bool) -> cx.C2Data:
    data = cx.build()
    if dry:
        meta = data.meta.copy()
        meta['y'] = dry_target(len(meta))
        data = dataclasses.replace(data, meta=meta)
    return data


def _init(dry: bool) -> None:
    global _DATA
    _DATA = load(dry)


# ---------------------------------------------------------------- one fit

def group_masks(cols: list[str]) -> dict[str, np.ndarray]:
    """Feature groups of pre-registration section 6, from the column names of c2x_features."""
    parts = [c.split('|') for c in cols]
    fam = np.array([p[0] for p in parts])
    name = np.array([p[1] for p in parts])
    band = np.array([p[2] if p[0] == 'MET' else '' for p in parts])
    met = fam == 'MET'
    m = {'pol': fam == 'POL', 'dec_osc': (fam == 'DEC') & np.isin(name, ['IMF1', 'IMF2', 'IMF3', 'IMF4']),
         'dec_slow': (fam == 'DEC') & (name == 'Slow'), 'city': fam == 'CITY', 'met': met,
         'met_syn': met & (band == 'syn'), 'met_intra': met & (band == 'intra'), 'met_subs': met & (band == 'subs'),
         'met_seas': met & (band == 'seas'), 'met_disp': met & np.isin(name, ['lblh', 'wind', 'lvent']),
         'met_temp': met & (name == 't2m'), 'met_hum': met & (name == 'rh'), 'met_rain': met & (name == 'sprecip')}
    top = sum(m[k].astype(int) for k in ('pol', 'dec_osc', 'dec_slow', 'city', 'met'))
    assert (top == 1).all(), 'feature groups must partition the columns'
    for parts_of_met in (('met_syn', 'met_intra', 'met_subs', 'met_seas'), ('met_disp', 'met_temp', 'met_hum', 'met_rain')):
        assert (sum(m[k].astype(int) for k in parts_of_met) == met.astype(int)).all()
    return {k: m[k] for k in SHARE_ORDER}


def shares(abs_contrib: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    """Section 6: c_f = mean over the windows of |phi_f|; share of a group = 100 x its c_f sum / the total."""
    c = abs_contrib.mean(axis=0, dtype=np.float64)
    tot = c.sum()
    return {k: float(100.0 * c[m].sum() / tot) for k, m in masks.items()}


def metrics(y: np.ndarray, p: np.ndarray) -> dict[str, float]:
    e = y.astype(np.float64) - p.astype(np.float64)
    return {'mae': float(np.mean(np.abs(e))), 'rmse': float(np.sqrt(np.mean(e ** 2))),
            'r2': float(1.0 - np.sum(e ** 2) / np.sum((y - y.mean()) ** 2))}


def model_for(seed: int, n_jobs: int, device: str, timing: bool = False) -> xgb.XGBRegressor:
    params = dict(PARAMS)
    if timing:                                         # fixed size, timing mode only; never used for outputs
        params.update(n_estimators=TIMING_TREES, early_stopping_rounds=None)
    if device == 'cuda':
        params['device'] = 'cuda'
    return xgb.XGBRegressor(random_state=seed, n_jobs=n_jobs, **params)


def fit_one(data: cx.C2Data, arm: str, seed: int, n_jobs: int, device: str = 'cpu') -> dict:
    z = cx.design(data, arm)
    model = model_for(seed, n_jobs, device)
    model.fit(z['X_train'], z['y_train'], eval_set=[(z['X_val'], z['y_val'])], verbose=False)
    best = int(model.best_iteration)
    pred = model.predict(z['X_test']).astype(np.float32)          # best iteration (xgboost sklearn API)
    contrib = model.get_booster().predict(xgb.DMatrix(z['X_test']), pred_contribs=True,
                                          iteration_range=(0, best + 1))
    gap = float(np.abs(contrib.sum(axis=1, dtype=np.float64) - pred).max())
    if not gap < ADDITIVITY_TOL:
        raise RuntimeError(f'STOP: {arm} seed {seed}: SHAP does not add up to the prediction (gap {gap})')
    absc = np.abs(contrib[:, :-1])
    masks = group_masks(z['cols'])
    meta_te = data.meta.iloc[z['rows_test']]
    y_te, period, city = z['y_test'], meta_te['period'].to_numpy(), meta_te['city'].to_numpy()
    pooled = []
    for per in cv.PERIODS:
        m = np.ones(len(y_te), bool) if per == 'all' else period == per
        pooled.append({'arm': arm, 'seed': seed, 'period': per, 'n': int(m.sum()), 'best_iter': best,
                       **metrics(y_te[m], pred[m]), **shares(absc[m], masks)})
    city_rows = []
    for c in sorted(set(city)):
        m = city == c
        if m.sum() < cv.MIN_CITY_TEST:
            continue
        sh = shares(absc[m], masks)
        city_rows.append({'arm': arm, 'seed': seed, 'city': c, 'n': int(m.sum()), 'mae': metrics(y_te[m], pred[m])['mae'],
                          **{k: sh[k] for k in ('met', 'met_syn', 'met_intra', 'met_subs', 'met_seas')}})
    return {'pooled': pooled, 'city': city_rows, 'pred': pred, 'best_iter': best, 'gap': gap}


# ---------------------------------------------------------------- parts (resume)

def part_paths(parts: Path, arm: str, seed: int) -> tuple[Path, Path]:
    stem = parts / f'{arm}__s{seed:02d}'
    return stem.with_suffix('.npy'), stem.with_suffix('.json')


def save_part(parts: Path, arm: str, seed: int, r: dict, key: str) -> None:
    npy, js = part_paths(parts, arm, seed)
    tmp = npy.with_name(npy.name + '.tmp')
    with open(tmp, 'wb') as f:
        np.lib.format.write_array(f, r['pred'], allow_pickle=False)
    os.replace(tmp, npy)
    payload = {'arm': arm, 'seed': seed, 'run_key': key, 'pred_sha256': array_sha256(r['pred']), 'machine': machine(),
               'best_iter': r['best_iter'], 'additivity_gap': r['gap'], 'pooled': r['pooled'], 'city': r['city']}
    tmp = js.with_name(js.name + '.tmp')
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(payload, f)
    os.replace(tmp, js)                                    # the json last: its presence marks a finished fit


def read_part(parts: Path, arm: str, seed: int) -> tuple[dict, np.ndarray] | None:
    """A finished part (its json and predictions), or None if it is missing, unreadable, or its predictions do not
    match their recorded SHA-256 (for example, cut off by an interruption)."""
    npy, js = part_paths(parts, arm, seed)
    try:
        payload = json.loads(js.read_text(encoding='utf-8'))
        pred = np.load(npy, allow_pickle=False)
    except (OSError, ValueError, EOFError):
        return None
    if (payload.get('arm'), payload.get('seed')) != (arm, seed) or payload.get('pred_sha256') != array_sha256(pred):
        return None
    return payload, pred


def done(parts: Path, arm: str, seed: int) -> bool:
    return read_part(parts, arm, seed) is not None


def check_parts_key(parts: Path, key: str) -> None:
    """Stop if the folder holds a part made under another run key (A2.3: no mixing of code, inputs or settings)."""
    other = []
    for js in sorted(parts.glob('*.json')):
        try:
            k = json.loads(js.read_text(encoding='utf-8')).get('run_key')
        except (OSError, ValueError):
            continue                                       # unreadable: refitted, never mixed
        if k != key:
            other.append(js.name)
    if other:
        raise ValueError(f'{parts} holds {len(other)} parts made under another run key (other code, inputs, versions, '
                         f'mode, thread count or device), e.g. {other[0]}. Use a new --out')


def _work(task: tuple) -> tuple[str, int, float, int, float]:
    arm, seed, parts, n_jobs, device, key = task
    t0 = time.time()
    r = fit_one(_DATA, arm, seed, n_jobs, device)
    save_part(parts, arm, seed, r, key)
    return arm, seed, time.time() - t0, r['best_iter'], r['gap']


def _timing_work(task: tuple) -> tuple[float, float, str, str, str]:
    """(start, end) wall-clock times of one fixed-size fit + SHAP (input building is outside the window), then the
    arm and the SHA-256 of the full-size test predictions and SHAP values (computed after the window)."""
    arm, seed, n_jobs, device = task
    z = cx.design(_DATA, arm)
    t0 = time.time()
    model = model_for(seed, n_jobs, device, timing=True)
    model.fit(z['X_train'], z['y_train'], verbose=False)
    contrib = model.get_booster().predict(xgb.DMatrix(z['X_test']), pred_contribs=True,
                                          iteration_range=(0, TIMING_SHAP_TREES))
    t1 = time.time()
    pred = model.predict(z['X_test']).astype(np.float32)          # all TIMING_TREES trees (no early stopping)
    return t0, t1, arm, array_sha256(pred), array_sha256(contrib.astype(np.float32))


def array_sha256(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


# ---------------------------------------------------------------- outputs

def save_npz(path: Path, arrays: dict[str, np.ndarray]) -> None:
    """A standard .npz (np.load reads it) with a fixed zip date and host, so equal arrays give equal bytes."""
    tmp = path.with_name(path.name + '.tmp')
    with zipfile.ZipFile(tmp, 'w', compression=zipfile.ZIP_STORED) as zf:
        for name, arr in arrays.items():
            info = zipfile.ZipInfo(f'{name}.npy', date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type, info.create_system, info.external_attr = zipfile.ZIP_STORED, 3, 0o644 << 16
            with zf.open(info, 'w', force_zip64=True) as f:
                np.lib.format.write_array(f, np.ascontiguousarray(arr), allow_pickle=False)
    os.replace(tmp, path)


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, lineterminator='\n')


def provenance(dry: bool, arms: list[str], seeds: tuple[int, ...], processes: int, n_jobs: int, device: str,
               max_gap: float, out_hashes: dict[str, str], key: str, fits_by_machine: dict[str, int]) -> dict:
    p = {'mode': (f'DRY RUN: made-up target, normal({DRY_MEAN:g}, {DRY_SD:g}), seed {DRY_SEED}; not a result'
                  if dry else 'REAL RUN'),
         'arms': len(arms), 'seeds': f'{seeds[0]}-{seeds[-1]} ({len(seeds)})', 'device': device,
         'processes': processes, 'xgboost n_jobs per fit': n_jobs,
         'xgboost threads used per fit': xgb_threads(n_jobs), 'python': platform.python_version(),
         'numpy': np.__version__, 'pandas': pd.__version__, 'scipy': scipy.__version__, 'xgboost': xgb.__version__,
         'platform': platform.platform(), 'machine': platform.machine(), 'processor': platform.processor() or 'unknown',
         'cpu': cpu_model(), 'logical processors available': processors(),
         'fits made on (addendum A2.3)': fits_by_machine, 'run key': key,
         'max additivity gap': max_gap, 'sha256 C2_PREREGISTRATION.md': cx.PREREG_SHA256,
         'sha256 C2_PREREGISTRATION_ADDENDUM_A1.md': cx.ADDENDUM_A1_SHA256,
         'sha256 C2_PREREGISTRATION_ADDENDUM_A2.md': cx.ADDENDUM_A2_SHA256}
    p.update({f'sha256 {s.name}': cx.sha256_rule(s) for s in SCRIPTS})
    p.update({f'sha256 input {path.relative_to(cx.REPO).as_posix()}': want for want, path, _ in cx.appendix_a()})
    p.update({f'sha256 output {k}': v for k, v in out_hashes.items()})
    return p


def assemble(out: Path, parts: Path, prefix: str, arms: list[str], seeds: tuple[int, ...], dry: bool,
             processes: int, n_jobs: int, device: str, key: str) -> None:
    data = load(dry)
    pooled_rows, city_rows, preds, bests, gaps, machines = [], [], [], [], [], {}
    for a in arms:
        for s in seeds:
            part = read_part(parts, a, s)
            if part is None or part[0]['run_key'] != key:
                raise RuntimeError(f'STOP: part {a} seed {s} is missing, damaged or from another run key')
            payload, pred = part
            pooled_rows += payload['pooled']
            city_rows += payload['city']
            preds.append(pred)
            bests.append(payload['best_iter'])
            gaps.append(payload['additivity_gap'])
            machines[payload['machine']] = machines.get(payload['machine'], 0) + 1
    pooled = pd.DataFrame(pooled_rows)[['arm', 'seed', 'period'] + cv.POOLED_COLS]
    city = pd.DataFrame(city_rows)[['arm', 'seed', 'city'] + cv.CITY_COLS]
    files = {'pooled': out / f'{prefix}_pooled.csv', 'city': out / f'{prefix}_city.csv',
             'predictions': out / f'{prefix}_predictions.npz'}
    write_csv(pooled, files['pooled'])
    write_csv(city, files['city'])
    test_rows = np.flatnonzero((data.meta['split'] == 'test').to_numpy())
    save_npz(files['predictions'], {
        'pred': np.stack(preds).reshape(len(arms), len(seeds), -1).astype(np.float32),
        'best_iter': np.array(bests, dtype=np.int32).reshape(len(arms), len(seeds)),
        'arms': np.array(arms), 'seeds': np.array(seeds, dtype=np.int32), 'test_rows': test_rows.astype(np.int64)})
    if list(arms) != cx.arm_names():
        print('subset of arms: tables written, no verdict', flush=True)
        return
    climate = cx.climate_check(cx.load_bank('era5_daily.csv'), cx.load_bank('era5_daily_pool.csv'))
    prov = provenance(dry, arms, seeds, processes, n_jobs, device, max(gaps),
                      {k: cx.sha256_rule(f) for k, f in files.items()}, key, dict(sorted(machines.items())))
    v = cv.evaluate(pooled, city, climate, prov, seeds=seeds)
    cv.write(v, out, prefix)


# ---------------------------------------------------------------- main

def check_request(dry: bool, timing: bool, arms: list[str], seeds: tuple[int, ...], device: str, out: Path,
                  processes: int, n_jobs: int, system: tuple[str, str] | None = None) -> None:
    """Guards for every mode, then the real-run guards (pre-registration sections 2, 4, 5, 13 and addendum A2).
    Raises ValueError; nothing is fitted before. system defaults to (platform.system(), platform.machine())."""
    if device not in ('cpu', 'cuda'):
        raise ValueError(f'unknown device {device}')
    if processes < 1 or n_jobs < 1:
        raise ValueError('processes and n_jobs must be fixed counts >= 1 (n_jobs 0 or -1 would mean "all processors", '
                         'which differs between machines and changes the results)')
    if xgb_threads(n_jobs) != n_jobs:
        raise ValueError(f'XGBoost would use only {xgb_threads(n_jobs)} threads here, not n_jobs {n_jobs} '
                         f'({processors()} processors available), so the recorded thread count would be false')
    if dry or timing:
        if out.resolve() == cx.OUT.resolve():
            raise ValueError('dry-run and timing outputs never go to the real outputs folder')
        return
    if list(arms) != cx.arm_names() or tuple(seeds) != cv.SEEDS:
        raise ValueError('a real run needs all 32 arms and seeds 0-39 (pre-registration sections 4-5)')
    if device != 'cpu':
        raise ValueError('a real run is on the CPU (pre-registration section 2)')
    here = system or (platform.system(), platform.machine())
    if tuple(here) != REAL_PLATFORM:
        raise ValueError(f'a real run is on {" ".join(REAL_PLATFORM)} (addendum A2.1), not on {" ".join(here)}. '
                         'Dry runs and timing work anywhere')
    if n_jobs != REAL_N_JOBS:
        raise ValueError(f'a real run uses n_jobs {REAL_N_JOBS} (addendum A2.1), not {n_jobs}')
    if (out / 'c2x_verdict.json').exists():
        raise ValueError(f'{out} already holds a finished run; the first run is kept (section 13). Use a new --out')


def run_fits(todo: list[tuple[str, int]], parts: Path, dry: bool, processes: int, n_jobs: int, device: str,
             log: Path) -> None:
    def record(arm: str, seed: int, sec: float, best: int, gap: float) -> None:
        line = f'{arm:14s} seed {seed:2d}  best_iter {best:4d}  {sec:6.1f} s  additivity gap {gap:.1e}'
        print(line, flush=True)
        with open(log, 'a', encoding='utf-8', newline='\n') as f:
            f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + line + '\n')
    key = run_key(dry, n_jobs, device)
    tasks = [(a, s, parts, n_jobs, device, key) for a, s in todo]
    if processes == 1:
        _init(dry)
        for t in tasks:
            record(*_work(t))
        return
    with ProcessPoolExecutor(max_workers=processes, mp_context=SPAWN, initializer=_init, initargs=(dry,)) as ex:
        for fut in as_completed([ex.submit(_work, t) for t in tasks]):
            record(*fut.result())


def fingerprint_path(out: Path, device: str, processes: int, n_jobs: int) -> Path:
    return out / f'fingerprints_{device}_p{processes}_t{n_jobs}.json'


def run_timing(dry: bool, processes: int, n_jobs: int, device: str, log: Path) -> None:
    tasks = [(a, 0, n_jobs, device) for a in TIMING_ARMS]
    if processes == 1:
        _init(True)
        res = [_timing_work(t) for t in tasks]
    else:
        with ProcessPoolExecutor(max_workers=processes, mp_context=SPAWN, initializer=_init, initargs=(True,)) as ex:
            res = list(ex.map(_timing_work, tasks))
    wall = max(r[1] for r in res) - min(r[0] for r in res)        # first fit start to last fit end
    per_fit = np.mean([r[1] - r[0] for r in res])
    est = wall / len(tasks) * 1280 / 3600
    line = (f'TIMING {device} processes {processes} x n_jobs {n_jobs}: {len(tasks)} fits of {TIMING_TREES} trees + '
            f'SHAP on {TIMING_SHAP_TREES}: wall {wall:.1f} s (one fit takes {per_fit:.1f} s); '
            f'estimated 1,280 fits: {est:.2f} h')
    print(line, flush=True)
    with open(log, 'a', encoding='utf-8', newline='\n') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M:%S ') + line + '\n')
    fp = {'made-up target': f'normal({DRY_MEAN:g}, {DRY_SD:g}), seed {DRY_SEED}', 'device': device,
          'xgboost threads per fit': n_jobs, 'trees': TIMING_TREES, 'shap trees': TIMING_SHAP_TREES,
          'arms': {arm: {'pred_sha256': p, 'shap_sha256': s} for _, _, arm, p, s in res}}
    with open(fingerprint_path(log.parent, device, processes, n_jobs), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(fp, f, indent=1)
        f.write('\n')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--dry-run', action='store_true', help='made-up target; outputs prefixed dry_, never a result')
    ap.add_argument('--timing', action='store_true', help='time fixed-size fits on the made-up target; no outputs')
    ap.add_argument('--seeds', type=int, nargs='+')
    ap.add_argument('--arms', nargs='+', help='dry run only: a subset of arms (tables only, no verdict)')
    ap.add_argument('--processes', type=int, default=1)
    ap.add_argument('--n-jobs', type=int, default=REAL_N_JOBS)
    ap.add_argument('--device', default='cpu')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--stop-after', type=int, help='stop after this many new fits (resume test)')
    a = ap.parse_args(argv)
    dry = a.dry_run or a.timing
    arms = a.arms or cx.arm_names()
    if a.arms and not a.dry_run:
        raise ValueError('--arms is for dry runs only')
    seeds = tuple(a.seeds) if a.seeds else ((0, 1) if dry else cv.SEEDS)
    out = a.out or (cx.OUT / ('dryrun' if dry else ''))
    check_request(a.dry_run, a.timing, arms, seeds, a.device, out, a.processes, a.n_jobs)
    out.mkdir(parents=True, exist_ok=True)
    log = out / 'run_log.log'
    if a.timing:
        run_timing(True, a.processes, a.n_jobs, a.device, log)
        return 0
    parts = out / ('parts' if a.dry_run else 'c2x_parts')
    parts.mkdir(exist_ok=True)
    key = run_key(a.dry_run, a.n_jobs, a.device)
    check_parts_key(parts, key)
    todo = [(arm, s) for arm in arms for s in seeds if not done(parts, arm, s)]
    stopped = a.stop_after is not None and a.stop_after < len(todo)
    if stopped:
        todo = todo[:a.stop_after]
    print(f'{len(arms) * len(seeds)} fits requested, {len(todo)} to run now, '
          f'processes {a.processes} x n_jobs {a.n_jobs}, device {a.device}', flush=True)
    run_fits(todo, parts, a.dry_run, a.processes, a.n_jobs, a.device, log)
    if stopped:
        print(f'stopped after {a.stop_after} fits as asked; run again to resume', flush=True)
        return 3
    assemble(out, parts, 'dry' if a.dry_run else 'c2x', arms, seeds, a.dry_run, a.processes, a.n_jobs, a.device,
             key)
    print(f'done: outputs in {out}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
