# ── Revision 1, N1 / R1.11 (decision P3, gaps after the forward fill by option (c)): pollutant gaps filled from the city's own past ──
# Replaces groupby('City').ffill().bfill() + full-dataset mean fill in the loaders. Each window builder,
# on the daily calendar from d1_calendar_city:
#   1. n1_pollutant_calendar: a pollutant value is the last real reading within N1_MAX_FILL_DAYS
#      calendar days. A gap still open after the city's first reading of that pollutant gets the median
#      of the city's own readings in the previous N1_HISTORY_DAYS available days (the history of the
#      causal decomposition, R1.1 C5), or of all its earlier readings if there are none in that span.
#      No backward fill, nothing from another city, nothing from a later date.
#   2. n1_fill_constant: days before the city's first reading of a pollutant (or every day, if never
#      measured) get one constant per pollutant, the same for every city and date: the median of all
#      cities' real readings on training rows (the D1 scaler rows, d1_train_row_mask). Each builder
#      keeps the readings from n1_readings for this, since filled values cannot be told apart later.
N1_MAX_FILL_DAYS = 3     # same limit as D1_MAX_FILL_DAYS
N1_HISTORY_DAYS = 365    # same history cap as the causal decomposition (R1.1, C5)


def n1_readings(values, observed):
    '''Real pollutant readings on the daily calendar: values on observed days, NaN elsewhere.

    values: (n_days, n_pollutants) from d1_calendar_city, whose rows on non-observed days are D1 copies.
    '''
    return np.where(np.asarray(observed, dtype=bool)[:, None], values, np.nan)


def n1_pollutant_calendar(values, observed, available, max_fill_days=N1_MAX_FILL_DAYS,
                          history_days=N1_HISTORY_DAYS):
    '''Pollutant array on the daily calendar, filled from the city's own past readings only.

    values: (n_days, n_pollutants) from d1_calendar_city. Only rows of observed days are real readings,
    so the rows D1 copied into short AQI gaps are discarded and rebuilt by the same rule. Unavailable
    days stay NaN. Available days before the city's first reading of a pollutant stay NaN, for
    n1_fill_constant.
    '''
    available = np.asarray(available, dtype=bool)
    real = n1_readings(values, observed)
    out = pd.DataFrame(real).ffill(limit=max_fill_days).to_numpy(dtype=np.float64, copy=True)
    out[~available] = np.nan

    # Longer gaps after the first reading: median of the readings in the history_days available days
    # before day t. Unavailable days are skipped, as gaps are joined in the decomposition history (G1).
    avail_days = np.flatnonzero(available)
    avail_rank = np.cumsum(available) - 1
    days = np.arange(len(out))
    for j in range(out.shape[1]):
        read = np.isfinite(real[:, j])
        if not read.any():
            continue
        first = int(np.argmax(read))
        for t in np.flatnonzero(available & np.isnan(out[:, j]) & (days > first)):
            start = avail_days[max(int(avail_rank[t]) - history_days, 0)]
            past = real[start:t, j]
            past = past[np.isfinite(past)]
            if past.size == 0:                       # no reading in that span: all earlier readings
                past = real[:t, j][read[:t]]
            out[t, j] = np.median(past)
    return out


def n1_fill_constant(city_raw, key, city_splits, seq_len):
    '''Fill the days before each city's first reading of a pollutant with one pooled constant per pollutant.

    city_raw[c][key]: (n_days, n_pollutants) from n1_pollutant_calendar, filled in place. city_raw[c]
    also holds 'n', 'available', 'starts' and 'n1_readings' (from n1_readings). city_splits[c][0] is the
    number of training windows. The constant is the median of all cities' real readings on training rows.
    Returns the constant per pollutant.
    '''
    readings = []
    for c in city_raw:
        d = city_raw[c]
        rows = d1_train_row_mask(d['n'], d['starts'][:city_splits[c][0]], seq_len, d['available'])
        readings.append(d['n1_readings'][rows])
    readings = np.vstack(readings)
    if not np.isfinite(readings).any(axis=0).all():
        raise ValueError("N1: a pollutant has no training reading in any city")
    constant = np.nanmedian(readings, axis=0)
    for c in city_raw:
        x = city_raw[c][key]
        gap = np.isnan(x) & np.asarray(city_raw[c]['available'], dtype=bool)[:, None]
        x[gap] = np.broadcast_to(constant, x.shape)[gap]
    return constant
