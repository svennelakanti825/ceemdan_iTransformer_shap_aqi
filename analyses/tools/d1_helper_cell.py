# Revision 1, reviewer comment R3.3, decision D1 option (b): calendar-based windows.
#
# Each city's series is placed on a continuous daily calendar running from its first to its last
# observed day. A run of at most D1_MAX_FILL_DAYS consecutive missing days is filled by copying the
# last observed day (past values only). Longer runs stay missing. A forecast window is used only if
# every one of its input days is observed or filled AND its target day is observed. Targets are
# never filled, so every evaluated target is a real observation, and a window of length L always
# spans exactly L calendar days followed by the next calendar day as its target.
D1_MAX_FILL_DAYS = 3


def d1_calendar_city(df_c, value_cols, max_fill_days=D1_MAX_FILL_DAYS):
    '''
    Place one city's rows on a daily calendar and forward-fill short gaps.

    df_c        : rows of a single city, one row per observed day, with a 'Date' column.
    value_cols  : columns to carry onto the calendar.
    Returns (frame, observed, available):
      frame     : DataFrame with 'Date' plus value_cols, one row per calendar day. Days in a gap of
                  at most max_fill_days hold an exact copy of the last observed day. Days in longer
                  gaps hold NaN.
      observed  : bool ndarray, True where df_c has a row for that day.
      available : bool ndarray, True where the day is observed or filled.
    '''
    dates = pd.to_datetime(df_c['Date'])
    if dates.duplicated().any():
        raise ValueError('d1_calendar_city: duplicate dates within one city')
    vals = df_c[list(value_cols)].set_index(dates).sort_index()
    calendar = pd.date_range(vals.index[0], vals.index[-1], freq='D')
    frame = vals.reindex(calendar)
    observed = np.asarray(calendar.isin(vals.index), dtype=bool)
    missing = ~observed

    # Length of the missing run each day belongs to. run_id increases at every observed day, so all
    # days of one missing run share the run_id of the observed day that precedes them.
    run_id = np.cumsum(observed)
    run_len = pd.Series(missing.astype(np.int64)).groupby(run_id).transform('sum').to_numpy()
    fill = missing & (run_len <= max_fill_days)

    # Copy the last observed day. The calendar starts on an observed day, so one always exists.
    last_obs = np.maximum.accumulate(np.where(observed, np.arange(len(observed)), -1))
    if fill.any():
        frame.iloc[np.flatnonzero(fill)] = frame.iloc[last_obs[fill]].to_numpy()

    available = observed | fill
    frame = frame.rename_axis('Date').reset_index()
    return frame, observed, available


def d1_window_starts(observed, available, seq_len):
    '''
    Start indices of usable windows on the calendar.

    Window i uses input days i .. i+seq_len-1 and target day i+seq_len. It is usable when every
    input day is available (observed or filled) and the target day is observed.
    '''
    observed = np.asarray(observed, dtype=bool)
    available = np.asarray(available, dtype=bool)
    n = len(observed)
    if n <= seq_len:
        return np.array([], dtype=np.int64)
    csum = np.concatenate([[0], np.cumsum(available.astype(np.int64))])
    starts = np.arange(n - seq_len, dtype=np.int64)
    inputs_ok = (csum[starts + seq_len] - csum[starts]) == seq_len
    target_ok = observed[starts + seq_len]
    return starts[inputs_ok & target_ok]


def d1_train_row_mask(n_rows, train_starts, seq_len, available):
    '''
    Calendar rows used to fit scalers: available days up to and including the target day of the
    last training window. No validation or test day is included.
    '''
    mask = np.zeros(n_rows, dtype=bool)
    if len(train_starts) == 0:
        return mask
    mask[: int(train_starts[-1]) + seq_len + 1] = True
    return mask & np.asarray(available, dtype=bool)
