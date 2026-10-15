"""Detectable effect of the realisation test in notebook 04 (G2).

One-way random-effects ANOVA with k decomposition realisations and n model seeds each, tested at 5%. For a
detection probability P, the smallest between-realisation s.d. that the F test detects, as a multiple of the
model-seed s.d., is r = sqrt((F_crit / F_{1-P}(k-1, k(n-1)) - 1) / n), where under the alternative the F statistic
is (1 + n r^2) times an F(k-1, k(n-1)) variable.

Usage: python g2_power.py
Output: g2_power.txt
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
G2 = HERE.parents[1] / 'results' / '04_followups' / 'reports' / 'shap' / 'g2_shap_lb7.csv'
ALPHA = 0.05


def main() -> None:
    g2 = pd.read_csv(G2)
    k, n = g2.decomposition_seed_base.nunique(), g2.model_seed.nunique()
    df1, df2 = k - 1, k * (n - 1)
    fcrit = stats.f.ppf(1 - ALPHA, df1, df2)
    lines = [f'{k} realisations x {n} model seeds, F({df1}, {df2}), critical value {fcrit:.3f} at {ALPHA:.0%}']
    for power in (0.5, 0.8):
        r = float(np.sqrt((fcrit / stats.f.ppf(1 - power, df1, df2) - 1) / n))
        lines.append(f'detected with probability {power:.0%}: realisation s.d. = {r:.2f} x model-seed s.d.')
    (HERE / 'g2_power.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
