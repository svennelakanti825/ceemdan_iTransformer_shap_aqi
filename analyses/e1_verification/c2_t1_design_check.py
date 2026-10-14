"""C2-T1 design check: which unit of inference keeps the real-vs-null weather tests at their stated 5% level.

Reads only E5 development-fold results (targets before 2019-04-01, already pre-registered and reported). No test-year
data and no C2 result is used. The simulation draws synthetic MAE values only.

Part 1 estimates, from E5, the seed s.d. within an arm and the s.d. between the 4 null weather sets (tau).
Part 2 simulates the H1 rule under three tests, with 20 seeds per arm and 4 null sets:
  planned    : Welch one-sided, MET_PP runs vs the 80 pooled null runs (plan 13.2)
  set_welch  : Welch one-sided, MET_PP runs vs the 4 null-set means
  prediction : t = (mean of null-set means - MET_PP mean) / (s_sets * sqrt(1 + 1/4)), df 3
Each is combined with E5's "below every null mean". Under H0 the real weather is one more same-season draw.
Part 3 (added after the journal-reviewer review, 10 Oct) uses the test-year seed s.d. that E3 already reported
(3 seeds per arm, disclosed as A4) and gives the power of the prediction test for 4 or 10 null sets and 20 or 40
seeds, with and without "below every null mean".
Output: outputs/c2_t1_design_check.txt
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parent / 'outputs'
S, K, R = 20, 4, 20000
SIGMAS = (0.25, 0.40)
TAUS = (0.0, 0.15, 0.26, 0.40)
DELTAS = (0.0, 0.5, 1.0, 1.4)


def variance_components(res: pd.DataFrame) -> list[str]:
    res = res.assign(short=res['met_syn'] + res['met_intra'])
    lines = ['Part 1. E5 development folds, 3 seeds per arm: seed s.d. within an arm, s.d. of the 4 null-set means, '
             'and tau = sqrt(var(set means) - within var / 3)']
    for fold in ('F1', 'F2'):
        for pp in ('', '_PP'):
            d = res[(res['fold'] == fold) & res['arm'].isin([f'NULL{pp}_{k}' for k in range(1, K + 1)])]
            for col in ('mae', 'short', 'met_seas'):
                within2 = (d.groupby('arm')[col].std(ddof=1) ** 2).mean()
                means = d.groupby('arm')[col].mean()
                tau = np.sqrt(max(means.var(ddof=1) - within2 / 3, 0.0))
                lines.append(f'  {fold} MET{pp:3s} {col:8s} within s.d. {np.sqrt(within2):.3f}  '
                             f's.d. of set means {means.std(ddof=1):.3f}  tau {tau:.3f}')
    return lines


def welch_p(m1: np.ndarray, v1: np.ndarray, n1: int, m0: np.ndarray, v0: np.ndarray, n0: int) -> np.ndarray:
    se2 = v1 / n1 + v0 / n0
    df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v0 / n0) ** 2 / (n0 - 1))
    return stats.t.sf((m0 - m1) / np.sqrt(se2), df)


def simulate(rng: np.random.Generator, sigma: float, tau: float, delta: float) -> dict[str, float]:
    shift = rng.normal(0.0, tau, (R, K + 1))
    pp = shift[:, :1] - delta + rng.normal(0.0, sigma, (R, S))
    nu = shift[:, 1:, None] + rng.normal(0.0, sigma, (R, K, S))
    m1, v1, sm = pp.mean(1), pp.var(1, ddof=1), nu.mean(2)
    below = m1 < sm.min(1)
    pool = nu.reshape(R, -1)
    p_planned = welch_p(m1, v1, S, pool.mean(1), pool.var(1, ddof=1), K * S)
    p_set = welch_p(m1, v1, S, sm.mean(1), sm.var(1, ddof=1), K)
    t_pred = (sm.mean(1) - m1) / (sm.std(1, ddof=1) * np.sqrt(1 + 1 / K))
    p_pred = stats.t.sf(t_pred, K - 1)
    return {'planned': float((below & (p_planned < 0.05)).mean()),
            'set_welch': float((below & (p_set < 0.05)).mean()),
            'prediction': float((below & (p_pred < 0.05)).mean()),
            'prediction_2.5%': float((below & (p_pred < 0.025)).mean())}


def simulate_pred(rng: np.random.Generator, sigma: float, tau: float, delta: float, k: int, s: int
                  ) -> tuple[float, float]:
    shift = rng.normal(0.0, tau, (R, k + 1))
    real = shift[:, 0] - delta + rng.normal(0.0, sigma, (R, s)).mean(1)
    sm = shift[:, 1:] + rng.normal(0.0, sigma, (R, k, s)).mean(2)
    p = stats.t.sf((sm.mean(1) - real) / (sm.std(1, ddof=1) * np.sqrt(1 + 1 / k)), k - 1)
    return float((p < 0.05).mean()), float(((p < 0.05) & (real < sm.min(1))).mean())


def test_year_noise() -> list[str]:
    e3 = pd.read_csv(OUT / 'e3_met_forecast.csv')
    sd = e3.groupby('arm')['test_mae'].std(ddof=1)
    return ['', 'Part 3a. Test-year seed s.d. of MAE in E3 (3 seeds per arm; already reported 8 Oct, disclosure A4)'] + [
        f'  {a:24s} {v:.3f}' for a, v in sd.items()]


def main() -> None:
    lines = variance_components(pd.read_csv(OUT / 'e5_pooled.csv'))
    lines += ['', f'Part 2. Pass rate of the H1 rule ({R} simulations, {S} seeds per arm, {K} null sets). '
              'delta = 0 is the false-pass rate (should be 0.05); delta > 0 is the power. MAE units.',
              f'  {"sigma":>5} {"tau":>5} {"delta":>5} | {"planned":>8} {"set_welch":>9} {"prediction":>10} '
              f'{"pred_2.5%":>9}']
    rng = np.random.default_rng(20261010)
    for sigma in SIGMAS:
        for tau in TAUS:
            for delta in DELTAS:
                r = simulate(rng, sigma, tau, delta)
                lines.append(f'  {sigma:5.2f} {tau:5.2f} {delta:5.1f} | {r["planned"]:8.3f} {r["set_welch"]:9.3f} '
                             f'{r["prediction"]:10.3f} {r["prediction_2.5%"]:9.3f}')
    lines += test_year_noise()
    lines += ['', 'Part 3b. Prediction test, power at test-year seed noise. Cells: pass rate of the test alone / '
              'test + below every null mean, for K null sets and S seeds per arm.',
              f'  {"sigma":>5} {"tau":>5} {"delta":>5} | ' + ' | '.join(f'K={k:<2d} S={s:<2d}  ' for k in (4, 10)
                                                                   for s in (20, 40))]
    for sigma in (0.4, 0.8, 1.3):
        for tau in (0.15, 0.26, 0.40):
            for delta in DELTAS:
                cells = [simulate_pred(rng, sigma, tau, delta, k, s) for k in (4, 10) for s in (20, 40)]
                lines.append(f'  {sigma:5.2f} {tau:5.2f} {delta:5.1f} | '
                             + ' | '.join(f'{a:.3f}/{b:.3f}' for a, b in cells))
    txt = '\n'.join(lines)
    print(txt)
    (OUT / 'c2_t1_design_check.txt').write_text(txt + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
