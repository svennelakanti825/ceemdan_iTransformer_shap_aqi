"""X1: rerun earlier XGBoost checks with SHAP taken from the model that made the predictions (10 Oct 2026).

With early stopping, XGBRegressor.predict uses the best iteration, but
Booster.predict(pred_contribs=True) without an iteration_range uses every tree (best iteration + 100). E1, E3, E5, E6
and the novelty checks v3 and v5 computed SHAP shares that way.

This wrapper runs each original script UNCHANGED, with one switch: a pred_contribs call without an iteration_range
gets iteration_range=(0, best_iteration + 1). Every switched call is checked for additivity (contributions sum to the
best-iteration margin within 0.01). The scripts write to their usual tracked output files. Afterwards the new files
are copied to x1_shap_recheck/outputs/ and the originals are restored from git (also if the run fails).
Error columns (MAE, R2, ...) do not depend on SHAP, so they must reproduce exactly. That is checked, as proof that
the rerun is the same experiment.

Usage: python x1_rerun.py E1 E5 E3 E6 V3 V5     (any subset, run in the given order)
"""
from __future__ import annotations

import importlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

HERE = Path(__file__).resolve().parent
REV1 = HERE.parent
REPO = REV1.parent
OUT = HERE / 'outputs'
E1V, NOV = REV1 / 'e1_verification', REV1 / 'novelty_checks'

# name: (script folder, module, how to call main, output files, columns that must reproduce exactly per file;
#        None = the whole file must be identical)
EXPS: dict[str, tuple] = {
    'E1': (E1V, 'e1_leakage_contrast', lambda m: m.main(['POL', 'RAW', 'CAUSAL', 'LEAKY']),
           ['outputs/e1_accuracy.csv', 'outputs/e1_shares.csv'], {'e1_accuracy.csv': None}),
    'E3': (E1V, 'e3_met_forecast', lambda m: m.main(), ['outputs/e3_met_forecast.csv'],
           {'e3_met_forecast.csv': ['arm', 'seed', 'val_r2', 'test_r2', 'test_mae']}),
    'E5': (E1V, 'e5_driver_band_precheck', lambda m: m.main(),
           ['outputs/e5_pooled.csv', 'outputs/e5_city.csv', 'outputs/e5_verdict.txt'],
           {'e5_pooled.csv': ['fold', 'arm', 'seed', 'n_eval', 'best_iter', 'mae', 'rmse', 'r2'],
            'e5_city.csv': ['fold', 'arm', 'seed', 'city', 'n', 'mae']}),
    'E6': (E1V, 'e6_horizon_lookback_osc', lambda m: m.main(),
           ['outputs/e6_pooled.csv', 'outputs/e6_city.csv', 'outputs/e6_verdict.txt'],
           {'e6_pooled.csv': ['L', 'h', 'fold', 'arm', 'seed', 'n_eval', 'best_iter', 'mae', 'r2'],
            'e6_city.csv': ['L', 'h', 'fold', 'arm', 'seed', 'city', 'n', 'mae']}),
    'V3': (NOV, 'v3_controlled_compare', lambda m: m.main(), ['v3_accuracy.csv', 'v3_shares.csv'],
           {'v3_accuracy.csv': None}),
    'V5': (NOV, 'v5_moving_average', lambda m: m.main(), ['v5_moving_average.csv'],
           {'v5_moving_average.csv': ['arm', 'seed', 'r2', 'mae']}),
}

_ORIG_PREDICT = xgb.Booster.predict
CALLS: list[tuple[int, int, float]] = []          # (trees used, trees kept, additivity gap) per switched call


def _best_iteration_contribs(self: xgb.Booster, data: xgb.DMatrix, *args, **kw):
    if kw.get('pred_contribs') and tuple(kw.get('iteration_range', (0, 0))) == (0, 0):
        bi = self.attr('best_iteration')
        assert bi is not None, 'pred_contribs on a model without early stopping: nothing to switch'
        ir = (0, int(bi) + 1)
        kw['iteration_range'] = ir
        out = _ORIG_PREDICT(self, data, *args, **kw)
        margin = _ORIG_PREDICT(self, data, output_margin=True, iteration_range=ir)
        gap = float(np.abs(out.sum(axis=1) - margin).max())
        assert gap < 0.01, f'additivity gap {gap}'
        CALLS.append((ir[1], self.num_boosted_rounds(), gap))
        return out
    return _ORIG_PREDICT(self, data, *args, **kw)


def self_test() -> None:
    """The switch must make SHAP add up to XGBRegressor.predict on an early-stopped model (synthetic data)."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=(2000, 10))
    y = 3 * x[:, 0] + np.sin(2 * x[:, 1]) + rng.normal(size=2000)
    m = xgb.XGBRegressor(n_estimators=2000, learning_rate=0.03, max_depth=4, early_stopping_rounds=50,
                         random_state=0).fit(x[:1500], y[:1500], eval_set=[(x[1500:], y[1500:])], verbose=False)
    c = m.get_booster().predict(xgb.DMatrix(x[1500:]), pred_contribs=True)
    gap = np.abs(c.sum(1) - m.predict(x[1500:])).max()
    assert gap < 1e-3 and m.get_booster().num_boosted_rounds() > m.best_iteration + 1, gap
    CALLS.clear()


def git(*args: str) -> str:
    return subprocess.run(['git', *args], cwd=REPO, capture_output=True, text=True, check=True).stdout


def compare(name: str, old: Path, new: Path, cols: list[str] | None) -> str:
    if cols is None:
        same = old.read_bytes().replace(b'\r\n', b'\n') == new.read_bytes().replace(b'\r\n', b'\n')
        return f'  {name}: whole file identical: {same}'
    a, b = pd.read_csv(old, dtype=str, keep_default_na=False), pd.read_csv(new, dtype=str, keep_default_na=False)
    same = a.shape == b.shape and a[cols].equals(b[cols])
    return f'  {name}: {len(a)} rows, error columns {cols} identical: {same}'


def run(exp: str) -> None:
    folder, module, call, outputs, exact = EXPS[exp]
    paths = [folder / o for o in outputs]
    rel = [p.relative_to(REPO).as_posix() for p in paths]
    assert git('status', '--porcelain', '--', *rel) == '', f'{exp}: original outputs have local changes'
    sys.path.insert(0, str(folder))
    t0 = time.time()
    CALLS.clear()
    try:
        call(importlib.import_module(module))
        for p in paths:
            (OUT / p.name).write_bytes(p.read_bytes())
    finally:
        git('checkout', '--', *rel)                       # restore the original outputs whatever happened
        sys.path.remove(str(folder))
    assert git('status', '--porcelain', '--', *rel) == '', f'{exp}: originals not restored'
    used, kept = np.array([c[0] for c in CALLS]), np.array([c[1] for c in CALLS])
    lines = [f'{exp} ({module}), {time.time() - t0:.0f} s. SHAP calls switched: {len(CALLS)}; trees used '
             f'{used.min()}-{used.max()} of {kept.min()}-{kept.max()} kept; largest additivity gap '
             f'{max(c[2] for c in CALLS):.2e}. Originals restored from git.']
    lines += [compare(n, folder / o, OUT / n, cols) for o in outputs for n in [Path(o).name] if n in exact
              for cols in [exact[n]]]
    txt = '\n'.join(lines)
    print(txt, flush=True)
    with open(OUT / 'x1_run_log.txt', 'a', encoding='utf-8') as f:
        f.write(time.strftime('%Y-%m-%d %H:%M ') + txt + '\n')


if __name__ == '__main__':
    OUT.mkdir(parents=True, exist_ok=True)
    xgb.Booster.predict = _best_iteration_contribs
    self_test()
    print(f'xgboost {xgb.__version__}: self-test passed (switched SHAP adds up to the early-stopped predictions)',
          flush=True)
    for e in sys.argv[1:]:
        run(e)
