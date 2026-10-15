"""Share of test-year bulletin days that name PM2.5 among the prominent pollutants, per interpreted city.

Test year: targets 1 Jul 2019 to 1 Jul 2020 (the common calendar split). Interpreted cities: the 13 modelled cities that
pass the completeness screen (passes_completeness in the all-city attribution summary). A day counts when the
bulletin's prominent_pollutant field lists PM2.5. Days without a bulletin value for the city are not counted.

Usage: python e7_prominent_pm25.py [g1_summary_csv]
Output: outputs/e7_prominent_pm25_test_year.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BULLETIN = HERE / 'data_bulletins' / 'AllIndiaBulletinsMaster2025_openrefined.csv'
G1 = (Path(sys.argv[1]) if len(sys.argv) > 1 else
      HERE.parents[1] / 'results' / '04_followups' / 'reports' / 'shap' / 'g1_shap18_summary_lb7.csv')
OUT = HERE / 'outputs' / 'e7_prominent_pm25_test_year.csv'
TEST_START, TEST_END = pd.Timestamp('2019-07-01'), pd.Timestamp('2020-07-01')
ALIASES = {'Bengaluru': ['Bengaluru', 'Bangalore']}


def main() -> None:
    cities = pd.read_csv(G1).query('passes_completeness').city.tolist()
    b = pd.read_csv(BULLETIN, parse_dates=['date'])
    b = b[(b.date >= TEST_START) & (b.date <= TEST_END)]
    rows = []
    for c in cities:
        d = b[b.city.isin(ALIASES.get(c, [c]))].drop_duplicates('date')
        named = d.prominent_pollutant.fillna('').str.contains('PM2.5', regex=False)
        rows.append(dict(city=c, bulletin_days=len(d), pm25_named_days=int(named.sum()),
                         pm25_named_pct=round(100 * named.mean(), 1) if len(d) else float('nan')))
    t = pd.DataFrame(rows).sort_values('pm25_named_pct')
    t.to_csv(OUT, index=False)
    print(t.to_string(index=False))
    print(f'range {t.pm25_named_pct.min():.1f} to {t.pm25_named_pct.max():.1f}% over {len(t)} cities; '
          f'below 50%: {", ".join(t[t.pm25_named_pct < 50].city)}')


if __name__ == '__main__':
    main()
