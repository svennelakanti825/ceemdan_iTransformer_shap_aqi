"""Leaky contrast arm: ONE CEEMDAN per city over its entire available AQI record (gaps joined, as C5 joins them).

Same CEEMDAN settings and city seeds as the causal run of record (100 trials, epsilon 0.2, max_imf 8,
seed 123 + city index), no boundary extension. Channel values on a day therefore depend on observations after
that day, including test-period observations: this is the design Reviewer 1 (R1.1) identified as leakage.
Output: outputs/fullrec_<city>.npz with the 5 sifting-order channels on every available calendar day.
"""
from __future__ import annotations

import sys
import time
from multiprocessing import Pool

import numpy as np

from common import NS, OUT, city_calendars, load_df


def job(args: tuple) -> str:
    city, y_avail, avail_idx, seed = args
    t0 = time.time()
    comps = NS['c5_decompose'](y_avail, seed)          # sifting order, residue last; reconstruction checked
    ch = NS['c5_channels'](comps)                        # (5, n_available)
    np.savez_compressed(OUT / f'fullrec_{city}.npz', channels=ch, avail_idx=avail_idx,
                        n_components=len(comps), seed=seed)
    return f'{city}: {len(y_avail)} samples, {len(comps)} components, {time.time() - t0:.0f}s'


if __name__ == '__main__':
    cities = city_calendars(load_df())
    jobs = []
    for c, info in cities.items():
        idx = np.flatnonzero(info['available'])
        if (OUT / f'fullrec_{c}.npz').exists():
            continue
        jobs.append((c, info['y'][idx], idx, info['seed']))
    jobs.sort(key=lambda j: -len(j[1]))
    with Pool(8) as p:
        for msg in p.imap_unordered(job, jobs):
            print(msg, flush=True)
    print('done', flush=True)
    sys.exit(0)
