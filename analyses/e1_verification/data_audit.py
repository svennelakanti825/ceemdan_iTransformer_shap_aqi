"""Data audit of city_day.csv on the calendar rules of the main run, and the prefix audit of input availability.

Per city: record dates, missing AQI, longest gap, training, validation and test windows at lookback 7, test windows
whose last input day is filled, test windows whose 365-sample decomposition history spans more calendar days than
samples (compressed history), and the share of 14-day calendar windows kept by the eligibility rule (the
completeness screen for attribution interpretation, threshold 80%). Pollutant missingness per city.

Prefix audit: for every retained origin t, availability is recomputed from the calendar prefix ending at t (an open
trailing gap counted by its elapsed length) and compared with the full-record availability mask up to t.

Usage: python data_audit.py
Outputs (outputs/): data_audit.csv, pollutant_missing.csv, prefix_audit.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import DATA, FEATURES, NS, OUT

SEQ = 7


def main() -> None:
    raw = pd.read_csv(DATA, parse_dates=['Date'])
    rows, pr = [], []
    counts = {'train': 0, 'validation': 0, 'test': 0}
    bad, filled = dict.fromkeys(counts, 0), dict.fromkeys(counts, 0)
    for city, g in raw.groupby('City'):
        valid = g.dropna(subset=['AQI']).sort_values('Date')
        if not len(valid):
            continue
        cal, obs, av = NS['d1_calendar_city'](valid, FEATURES + ['AQI'])
        starts, split = NS['r19_city_windows'](cal.Date, obs, av, SEQ)
        miss = ~obs
        runs = pd.Series(miss.astype(int)).groupby(np.cumsum(obs)).sum()
        ends = starts[split[1]:] + SEQ - 1
        compressed, max_span = 0, 0
        for t in ends:
            ix = np.flatnonzero(av[:t + 1])[-365:]
            span = ix[-1] - ix[0] + 1
            compressed += span > len(ix)
            max_span = max(max_span, span)
        rows.append(dict(
            city=city, raw_start=g.Date.min().date(), raw_end=g.Date.max().date(), raw_rows=len(g),
            valid_aqi=len(valid), first_valid=valid.Date.min().date(), last_valid=valid.Date.max().date(),
            calendar_days=len(cal), missing_aqi_pct=100 * miss.mean(), longest_gap=int(runs.max()),
            train=split[0], validation=split[1] - split[0], test=split[2] - split[1],
            test_filled_origin=int((~obs[ends]).sum()), test_history_compressed=int(compressed),
            max_test_history_span=max_span,
            eligible14_pct=(100 * len(NS['d1_window_starts'](obs, av, 14)) / (len(cal) - 14)
                            if len(cal) > 14 else 0)))
        pr += [dict(city=city, pollutant=f, missing_pct=100 * g[f].isna().mean()) for f in FEATURES]

        if len(valid) < 2 or split[0] == 0:
            continue
        for i, start in enumerate(starts):
            t = start + SEQ - 1
            part = 'train' if i < split[0] else 'validation' if i < split[1] else 'test'
            o = obs[:t + 1]
            m = ~o
            run_len = pd.Series(m.astype(int)).groupby(np.cumsum(o)).transform('sum').to_numpy()
            prefix = o | (m & (run_len <= NS['D1_MAX_FILL_DAYS']))
            counts[part] += 1
            bad[part] += int(not np.array_equal(prefix, av[:t + 1]))
            filled[part] += int(not obs[t])

    a = pd.DataFrame(rows)
    a.to_csv(OUT / 'data_audit.csv', index=False)
    pd.DataFrame(pr).to_csv(OUT / 'pollutant_missing.csv', index=False)
    res = {'origins_checked': counts, 'mask_mismatches': bad, 'filled_origins': filled}
    (OUT / 'prefix_audit.json').write_text(json.dumps(res, indent=2), encoding='utf-8')
    m = a[a.train > 0]
    tot = m[['train', 'validation', 'test', 'test_filled_origin', 'test_history_compressed']].sum()
    print(f'{len(m)} modelled cities; windows {tot.to_dict()}; '
          f'compressed test histories {100 * tot.test_history_compressed / tot.test:.1f}%; '
          f'cities passing the 80% completeness screen: {int((m.eligible14_pct >= 80).sum())}')
    print(f'prefix audit: {res}')


if __name__ == '__main__':
    main()
