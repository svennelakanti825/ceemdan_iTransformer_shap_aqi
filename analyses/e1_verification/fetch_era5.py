"""ERA5 hourly meteorology for the 18 modelled cities, from the Open-Meteo historical archive (models=era5).

Daily aggregates in local time (Asia/Kolkata): mean boundary-layer height, mean 10 m wind speed, ventilation
coefficient (daily mean of hourly BLH x wind speed), mean temperature and relative humidity, precipitation sum.
Coordinates are approximate city centres. ERA5 is a 0.25 degree grid, so Delhi and Gurugram fall in
neighbouring cells and their meteorology is strongly shared.
Source: Hersbach et al. (2020), doi:10.1002/qj.3803, served by https://open-meteo.com (CC BY 4.0).
"""
from __future__ import annotations

import json
import time
import urllib.request

import pandas as pd

from common import OUT

CITY_COORDS: dict[str, tuple[float, float]] = {
    'Ahmedabad': (23.03, 72.58), 'Amaravati': (16.51, 80.52), 'Amritsar': (31.63, 74.87),
    'Bengaluru': (12.97, 77.59), 'Brajrajnagar': (21.82, 83.92), 'Chennai': (13.08, 80.27),
    'Delhi': (28.61, 77.21), 'Gurugram': (28.46, 77.03), 'Hyderabad': (17.39, 78.49),
    'Jaipur': (26.91, 75.79), 'Jorapokhar': (23.71, 86.41), 'Kolkata': (22.57, 88.36),
    'Lucknow': (26.85, 80.95), 'Mumbai': (19.08, 72.88), 'Patna': (25.59, 85.14),
    'Talcher': (20.95, 85.23), 'Thiruvananthapuram': (8.52, 76.94), 'Visakhapatnam': (17.69, 83.22),
}
HOURLY = 'boundary_layer_height,wind_speed_10m,temperature_2m,relative_humidity_2m,precipitation'
URL = ('https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}'
       '&start_date=2015-01-01&end_date=2020-07-01&hourly={h}&models=era5&timezone=Asia%2FKolkata'
       '&wind_speed_unit=ms')


def fetch(city: str, lat: float, lon: float) -> pd.DataFrame:
    for attempt in range(5):
        try:
            with urllib.request.urlopen(URL.format(lat=lat, lon=lon, h=HOURLY), timeout=180) as r:
                js = json.load(r)
            break
        except Exception as e:  # rate limit or transient error
            print(city, 'retry', attempt, e, flush=True)
            time.sleep(30 * (attempt + 1))
    else:
        raise RuntimeError(city)
    h = pd.DataFrame(js['hourly'])
    h['time'] = pd.to_datetime(h['time'])
    h['vent'] = h['boundary_layer_height'] * h['wind_speed_10m']
    d = h.set_index('time').resample('D').agg({
        'boundary_layer_height': 'mean', 'wind_speed_10m': 'mean', 'vent': 'mean',
        'temperature_2m': 'mean', 'relative_humidity_2m': 'mean', 'precipitation': 'sum'})
    d.columns = ['blh', 'wind', 'vent', 't2m', 'rh', 'precip']
    d['City'] = city
    d['grid_lat'], d['grid_lon'] = js['latitude'], js['longitude']
    return d.reset_index().rename(columns={'time': 'Date'})


if __name__ == '__main__':
    frames = []
    for c, (lat, lon) in CITY_COORDS.items():
        frames.append(fetch(c, lat, lon))
        print(c, len(frames[-1]), frames[-1][['grid_lat', 'grid_lon']].iloc[0].tolist(), flush=True)
        time.sleep(3)
    pd.concat(frames).to_csv(OUT / 'era5_daily.csv', index=False)
    print('saved', flush=True)
