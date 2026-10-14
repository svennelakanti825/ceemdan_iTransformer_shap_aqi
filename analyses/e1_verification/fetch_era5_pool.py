"""ERA5 for the C2 null-year pool (decision R-a, 10 Oct 2026): the 18 cities, 2004-09-01 to 2014-12-31.

Uses fetch_era5.fetch unchanged (same coordinates, variables, Open-Meteo model, timezone, units and daily
aggregation); only the date range of the request differs. 2004-09-01 gives the 91-day history needed for the trailing
bands from 2005-01-01. The pool years 2005-2014 lie outside the AQI record (2015-2020), so no null can use the own
year or the test period. Output: outputs/era5_daily_pool.csv
"""
from __future__ import annotations

import time

import pandas as pd

import fetch_era5 as fe
from common import OUT

ORIGINAL_RANGE = 'start_date=2015-01-01&end_date=2020-07-01'
POOL_RANGE = 'start_date=2004-09-01&end_date=2014-12-31'
PAUSE_S = 15                     # longer than fetch_era5.py: a 10-year request weighs more against the rate limit


if __name__ == '__main__':
    assert fe.URL.count(ORIGINAL_RANGE) == 1
    fe.URL = fe.URL.replace(ORIGINAL_RANGE, POOL_RANGE)
    frames = []
    for c, (lat, lon) in fe.CITY_COORDS.items():
        frames.append(fe.fetch(c, lat, lon))
        print(c, len(frames[-1]), frames[-1][['grid_lat', 'grid_lon']].iloc[0].tolist(), flush=True)
        time.sleep(PAUSE_S)
    pd.concat(frames).to_csv(OUT / 'era5_daily_pool.csv', index=False)
    print('saved', flush=True)
