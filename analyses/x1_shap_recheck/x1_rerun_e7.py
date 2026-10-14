"""X1 extension (13 Oct 2026): E7 D2 (dataset_check/e7_d2_models.py) with SHAP from the best iteration.

X1 (10 Oct) left E7 out because E7's rules use errors only. Its reported attribution share ("IMF1-4 receive 21-35%
while adding no skill") was computed the old way, on every tree. This reuses x1_rerun.run() unchanged: the original
outputs are restored from git, the new ones go to outputs/, and the error columns must reproduce exactly.

Usage (from analyses/dataset_check): python ../x1_shap_recheck/x1_rerun_e7.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import x1_rerun as x  # noqa: E402
import xgboost as xgb  # noqa: E402

x.EXPS['E7'] = (x.REV1 / 'dataset_check', 'e7_d2_models', lambda m: m.main(),
                ['outputs/e7_d2_pooled.csv', 'outputs/e7_d2_city.csv', 'outputs/e7_d2_verdict.txt'],
                {'e7_d2_pooled.csv': ['h', 'year', 'hist', 'arm', 'seed', 'n', 'mae'],
                 'e7_d2_city.csv': ['h', 'year', 'hist', 'arm', 'seed', 'city', 'n', 'mae']})

if __name__ == '__main__':
    x.OUT.mkdir(parents=True, exist_ok=True)
    xgb.Booster.predict = x._best_iteration_contribs
    x.self_test()
    print(f'xgboost {xgb.__version__}: self-test passed', flush=True)
    x.run('E7')
