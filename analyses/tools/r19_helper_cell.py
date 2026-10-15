# ── Revision 1, R1.9/R1.10 (decision P4 on common dates) with the R1.1 minimum history (C5): windows, split, cities ──
# Replaces the per-city 70/10/20 split and the per-builder city thresholds (300 + L rows, L + 10 rows, none).
# Every builder takes a city's windows from r19_city_windows:
#   1. D1 windows (d1_window_starts).
#   2. R1.1 minimum history: a window is kept only if its last input day has at least R11_MIN_HISTORY_DAYS
#      available days up to and including it, counted from the start of the record (gaps joined, G1).
#   3. Split by the target date, the same dates for every city: training targets before R19_VAL_START,
#      validation targets before R19_TEST_START, test targets up to R19_DATA_END.
# A city is modelled only if it has at least one training window. r19_check_cities then makes every builder
# call of a run model the same cities, in the same order, per target (R3.6: the PM2.5 check has its own cities).
R19_VAL_START = np.datetime64('2019-04-01')    # first validation target date
R19_TEST_START = np.datetime64('2019-07-01')   # first test target date
R19_DATA_END = np.datetime64('2020-07-01')     # last day of the data set, last test target date
R11_MIN_HISTORY_DAYS = 180                     # R1.1 decision C5


def r19_city_windows(dates, observed, available, seq_len, min_history=R11_MIN_HISTORY_DAYS):
    '''Usable windows of one city and its split by target date.

    dates, observed, available: the daily calendar from d1_calendar_city.
    Returns (starts, (n_train, n_train + n_val, n_windows)). starts are in date order, so the first n_train
    windows are training windows, the next n_val validation windows and the rest test windows.
    '''
    available = np.asarray(available, dtype=bool)
    starts = d1_window_starts(observed, available, seq_len)
    history = np.cumsum(available)                      # available days up to and including each day
    starts = starts[history[starts + seq_len - 1] >= min_history]
    target = pd.to_datetime(pd.Series(dates)).to_numpy(dtype='datetime64[D]')[starts + seq_len]
    if len(target) and (np.any(np.diff(target) <= np.timedelta64(0, 'D')) or target[-1] > R19_DATA_END):
        raise ValueError('R1.9: window targets must be increasing and end by R19_DATA_END')
    n_train = int(np.searchsorted(target, R19_VAL_START, side='left'))
    n_train_val = int(np.searchsorted(target, R19_TEST_START, side='left'))
    return starts, (n_train, n_train_val, len(starts))


_r19_cities_in_run = {}


def r19_check_cities(valid_cities, builder, target='AQI'):
    '''Every builder call of a run for the same target must model the same cities in the same order (decision
    R1.9/R1.10).

    The first call per target records the list. A later call with a different list raises. Re-running this cell
    resets it. Revision 1, R3.6 (T2): the PM2.5 check models the cities with a PM2.5 training window, so the lists
    are kept per target. Every builder except the main model's is AQI-only and uses the default.
    '''
    cities = tuple(valid_cities)
    if not cities:
        raise ValueError(f'R1.9: {builder} has no city with a training window ({target})')
    first = _r19_cities_in_run.setdefault(target, (cities, builder))
    if cities != first[0]:
        raise ValueError(f'R1.9: {builder} models {list(cities)} for {target}, but {first[1]} modelled {list(first[0])}')
