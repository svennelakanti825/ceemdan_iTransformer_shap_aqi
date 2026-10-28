"""Boundary-extension step 0: which causal end-effect correction makes the causal channel values closest to interior ones.

Fixed before any result. Training-period data only, no model, no attribution.
For Delhi, Mumbai and Bengaluru, 20 seeded decomposition days t per city whose reference day r (60 available days
after t) is before the first validation target (1 Apr 2019). On each t:
  - the causal C5 decomposition at t (history: the last 365 available AQI values up to t) with each extension
    e0 'none', e1 'mirror', e2 'ar' (tools/c5_helper_cell.py, extension length 30 days);
  - the reference: the C5 decomposition at r without extension. The last 7 days of t's history lie 60 values before
    the end of r's history, so they are interior points there.
Error per channel: root mean square difference of the a1 channel values on those 7 days, as % of the s.d. of t's
history. Rule: the variant with the lowest mean error over IMF1 to IMF4 is chosen. If neither e1 nor e2 beats e0 by
at least 10%, the end fix is recorded as not helping.

Run from the repository root (about 240 decompositions, in parallel over the CPU cores):
    python analyses/e1_verification/i14_boundary_error.py
Writes outputs/i14_boundary_error.csv (one row per city, day, variant, channel) and prints the summary and the verdict.
"""
import json
import logging
import os
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'analyses' / 'tools'
DATA = ROOT / 'data' / 'city_day.csv'
OUT = Path(__file__).resolve().parent / 'outputs' / 'i14_boundary_error.csv'
logger = logging.getLogger('i14')
R11_MIN_HISTORY_DAYS = 180
for _f in ('d1_helper_cell.py', 'c5_helper_cell.py'):   # the notebook's own helper cells
    exec((TOOLS / _f).read_text(encoding='utf-8'), globals())

FEATURES = ["PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene"]
CITIES = ['Delhi', 'Mumbai', 'Bengaluru']
VARIANTS = ('none', 'mirror', 'ar')
N_DAYS, AHEAD, SEEN, SAMPLE_SEED = 20, 60, 7, 14
VAL_START = np.datetime64('2019-04-01')


def job(args):
    history, seed, extension = args
    return c5_channels(c5_decompose(history, seed, extension=extension))


def main() -> None:
    df = pd.read_csv(DATA).dropna(subset=['AQI'])
    all_cities = sorted(df['City'].unique())
    jobs, keys = [], []
    for c_i, city in enumerate(CITIES):
        df_c = df[df['City'] == city].sort_values('Date').reset_index(drop=True)
        cal, observed, available = d1_calendar_city(df_c, FEATURES + ['AQI'])
        aqi = cal['AQI'].to_numpy(dtype=np.float64)
        dates = pd.to_datetime(cal['Date']).to_numpy().astype('datetime64[D]')
        seed = C5_SEED_BASE + all_cities.index(city)
        avail_idx = np.flatnonzero(available)
        days = c5_days(available)
        pos = np.searchsorted(avail_idx, days)
        eligible = [(t, avail_idx[p + AHEAD]) for t, p in zip(days, pos)
                    if p + AHEAD < len(avail_idx) and dates[avail_idx[p + AHEAD]] < VAL_START]
        rng = np.random.default_rng(SAMPLE_SEED + c_i)
        for k in np.sort(rng.choice(len(eligible), N_DAYS, replace=False)):
            t, r = eligible[k]
            h_t, h_r = c5_history(aqi, available, t), c5_history(aqi, available, r)
            idx_t = np.flatnonzero(available[:t + 1])[-C5_W_MAX:]
            idx_r = np.flatnonzero(available[:r + 1])[-C5_W_MAX:]
            where = np.searchsorted(idx_r, idx_t[-SEEN:])
            assert np.array_equal(idx_r[where], idx_t[-SEEN:]) and len(idx_r) - 1 - where.max() == AHEAD
            keys.append((city, str(dates[t]), str(dates[r]), float(np.std(h_t)), where))
            jobs += [(h_t, seed, v) for v in VARIANTS] + [(h_r, seed, 'none')]
    with Pool(os.cpu_count() or 1) as pool:
        out = pool.map(job, jobs, chunksize=1)
    rows = []
    for i, (city, d_t, d_r, sd, where) in enumerate(keys):
        ref = out[4 * i + 3][:, where]
        for j, v in enumerate(VARIANTS):
            got = out[4 * i + j][:, -SEEN:]
            for ch, name in enumerate(C5_CHANNEL_NAMES):
                rows.append({'city': city, 'date_t': d_t, 'date_reference': d_r, 'variant': v, 'channel': name,
                             'rms_pct_of_history_sd': 100 * float(np.sqrt(np.mean((got[ch] - ref[ch]) ** 2))) / sd})
    res = pd.DataFrame(rows)
    res.to_csv(OUT, index=False, float_format='%.6f')
    table = res.pivot_table(index='variant', columns='channel', values='rms_pct_of_history_sd', aggfunc='mean')
    table = table.loc[list(VARIANTS), C5_CHANNEL_NAMES]
    table['IMF1-4 mean'] = table[C5_CHANNEL_NAMES[:4]].mean(axis=1)
    print(f'Boundary error, % of the history s.d., mean over {len(keys)} days ({N_DAYS} per city):')
    print(table.round(2).to_string())
    by_city = res[res.channel.isin(C5_CHANNEL_NAMES[:4])].pivot_table(index='variant', columns='city',
                                                                       values='rms_pct_of_history_sd', aggfunc='mean')
    print('\nIMF1-4 mean by city:')
    print(by_city.loc[list(VARIANTS), CITIES].round(2).to_string())
    e = table['IMF1-4 mean']
    best = e[['mirror', 'ar']].idxmin()
    gain = 1 - e[best] / e['none']
    print(f'\nRule: best extension {best} ({e[best]:.2f}) against none ({e["none"]:.2f}), reduction {100 * gain:.1f}%')
    print('Verdict:', f'choose {best}' if gain >= 0.10 else 'neither extension beats none by 10%: the end fix does not help')


if __name__ == '__main__':
    main()
