# ── Revision 1, R1.1 (decision C5) and R1.2 (decision a1): causal CEEMDAN with sifting-order channels ──
# Replaces the full-record, energy-ranked decomposition (extract_city_imf_features).
# For every available day t of a city with at least C5_MIN_HISTORY available days so far, CEEMDAN runs on the
# last min(C5_W_MAX, available days so far) available AQI values up to and including t, joined across longer
# gaps (D2 = G1). Nothing after t enters. A window whose last input day is t takes all its channel values from
# the decomposition at t (its last L values).
# Each decomposition uses a fresh CEEMDAN instance seeded with the city's seed, so a result does not depend on
# which other days were decomposed, in which order, or on how many processes ran.
# Channels (a1): IMF1 to IMF4 in sifting order, plus one slow channel = IMF5 onwards + the residue.
# Saved per city and day: the last C5_KEEP values of every component (a1 channels and CEEMDAN+LSTM groups are
# derived from them), the number of components, the history length and each channel's zero-crossing period
# over the history (I-5). The noise amplitude is passed as `epsilon`, the argument PyEMD reads. The submitted
# code passed `noise_std`, which PyEMD ignores, so the submitted runs used PyEMD's default of 0.005.
# Revision 1, I-14 (step 6i): optional end-effect correction. With extension 'mirror' or 'ar' the history is extended
# by ext_days values computed from the history alone, decomposed, and the components are cut back to the history.
# The default 'none' is C5 as run of record (its saved settings, and so every existing cache, are unchanged).
import hashlib
import os

C5_W_MAX = 365                      # history cap, available days
C5_MIN_HISTORY = R11_MIN_HISTORY_DAYS   # 180, from the R1.9 helper cell
C5_TRIALS = 100
C5_EPSILON = 0.2                    # noise amplitude, as stated in Methods
C5_MAX_IMF = 8                      # PyEMD max_imf: at most max_imf + 1 IMFs plus the residue
C5_SEED_BASE = 123                  # city seed = C5_SEED_BASE + index of the city among all cities in the data
C5_KEEP = 30                        # values kept per decomposition: the longest lookback
C5_N_CHANNELS = 5
C5_MAX_COMPONENTS = C5_MAX_IMF + 2
C5_CHANNEL_NAMES = ['IMF1', 'IMF2', 'IMF3', 'IMF4', 'IMF5+ (slow)']
C5_EXTENSIONS = ('none', 'mirror', 'ar')   # I-14
C5_EXT_DAYS = 30                    # I-14: extension length, the longest lookback
C5_AR_MAX_ORDER = 14                # I-14: largest AR order tried for the 'ar' extension


def c5_params(trials=C5_TRIALS, epsilon=C5_EPSILON, max_imf=C5_MAX_IMF, w_max=C5_W_MAX,
              min_history=C5_MIN_HISTORY, keep=C5_KEEP, extension='none', ext_days=C5_EXT_DAYS):
    '''Every setting that determines a saved decomposition. A saved file must match these exactly.
    I-14: the extension settings are recorded only when an extension is used, so 'none' keeps the C5 record.'''
    import PyEMD
    if extension not in C5_EXTENSIONS:
        raise ValueError(f'C5: unknown extension {extension!r}')
    p = {'trials': int(trials), 'epsilon': float(epsilon), 'max_imf': int(max_imf), 'w_max': int(w_max),
         'min_history': int(min_history), 'keep': int(keep), 'pyemd': str(PyEMD.__version__)}
    if extension != 'none':
        p.update({'extension': str(extension), 'ext_days': int(ext_days), 'ar_max_order': C5_AR_MAX_ORDER})
    return p


def c5_ar_forecast(x, n_ahead, max_order=C5_AR_MAX_ORDER):
    '''I-14: n_ahead values continuing x by an AR(p) model with intercept, fitted by least squares on x only.
    p in 1..max_order minimises AIC, every order fitted on the same targets x[max_order:]. Forecast recursively.'''
    x = np.asarray(x, dtype=np.float64)
    n = len(x) - max_order
    if n <= 2 * max_order + 2:
        raise ValueError(f'C5: history of {len(x)} values is too short for an AR({max_order}) extension')
    y = x[max_order:]
    best = None
    for p in range(1, max_order + 1):
        X = np.column_stack([np.ones(n)] + [x[max_order - k:len(x) - k] for k in range(1, p + 1)])
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        rss = float(np.sum((y - X @ coef) ** 2))
        aic = n * np.log(max(rss, 1e-300) / n) + 2 * (p + 1)
        if best is None or aic < best[0]:
            best = (aic, p, coef)
    _, p, coef = best
    buf = list(x[-p:])
    out = np.empty(n_ahead)
    for i in range(n_ahead):
        out[i] = coef[0] + sum(coef[k] * buf[-k] for k in range(1, p + 1))
        buf.append(out[i])
    return out


def c5_extend(x, extension='none', ext_days=C5_EXT_DAYS):
    '''I-14: the history x followed by ext_days values computed from x alone ('none': x unchanged).
    'mirror': x[n-2], x[n-3], ..., x[n-1-ext_days] (even symmetry about the last day). 'ar': c5_ar_forecast.'''
    x = np.asarray(x, dtype=np.float64)
    if extension == 'none':
        return x
    if extension == 'mirror':
        if len(x) < ext_days + 2:
            raise ValueError(f'C5: history of {len(x)} values is too short for a {ext_days}-day mirror')
        return np.concatenate([x, x[-2:-ext_days - 2:-1]])
    if extension == 'ar':
        return np.concatenate([x, c5_ar_forecast(x, ext_days)])
    raise ValueError(f'C5: unknown extension {extension!r}')


def c5_decompose(history, seed, trials=C5_TRIALS, epsilon=C5_EPSILON, max_imf=C5_MAX_IMF, extension='none',
                 ext_days=C5_EXT_DAYS):
    '''CEEMDAN components of one history, in sifting order (last row = residue). No fallback: errors raise.
    I-14: with an extension, the extended history is decomposed and the components are cut back to the history.

    Fewer than C5_N_CHANNELS components is allowed here and recorded, so a long run is never lost. Such a day
    cannot give a1 channels: c5_channels raises when a window needs it (decision for the authors).
    '''
    from PyEMD import CEEMDAN
    x = np.asarray(history, dtype=np.float64)
    comps = CEEMDAN(trials=trials, epsilon=epsilon, max_imf=max_imf, seed=seed, parallel=False)(
        c5_extend(x, extension, ext_days))[:, :len(x)]
    if not np.allclose(comps.sum(axis=0), x, rtol=0, atol=1e-6 * max(1.0, float(np.abs(x).max()))):
        raise ValueError('C5: CEEMDAN components do not reconstruct the history')
    if len(comps) > C5_MAX_COMPONENTS:
        raise ValueError(f'C5: {len(comps)} components, more than the {C5_MAX_COMPONENTS} that max_imf allows')
    return comps


def c5_channels(comps):
    '''a1 channels (5, n) from components (K, n): IMF1..IMF4, and the sum of IMF5 onwards and the residue.'''
    comps = np.asarray(comps, dtype=np.float64)
    if len(comps) < C5_N_CHANNELS:
        raise ValueError(f'C5: {len(comps)} components, a1 needs at least {C5_N_CHANNELS}')
    return np.vstack([comps[:C5_N_CHANNELS - 1], comps[C5_N_CHANNELS - 1:].sum(axis=0, keepdims=True)])


def c5_period(x):
    '''Zero-crossing period in days (as period_zero_crossing in the submitted notebook). NaN below 2 crossings.'''
    x = np.asarray(x, dtype=np.float64) - np.mean(x)
    s = np.sign(x)
    s[s == 0] = 1
    n = int(np.sum(s[:-1] != s[1:]))
    return 2.0 * (len(x) - 1) / n if n >= 2 else np.nan


def c5_days(available, min_history=C5_MIN_HISTORY):
    '''Calendar days decomposed: available days with at least min_history available days up to and including them.'''
    available = np.asarray(available, dtype=bool)
    return np.flatnonzero(available & (np.cumsum(available) >= min_history))


def c5_history(aqi, available, t, w_max=C5_W_MAX):
    '''The last min(w_max, available days so far) available AQI values up to and including day t (gaps joined).'''
    idx = np.flatnonzero(np.asarray(available, dtype=bool)[:t + 1])[-w_max:]
    return np.asarray(aqi, dtype=np.float64)[idx]


def _c5_job(args):
    '''One decomposition. Top-level so that worker processes can run it.'''
    history, seed, trials, epsilon, max_imf, keep = args[:6]
    extension, ext_days = args[6:8] if len(args) > 6 else ('none', C5_EXT_DAYS)   # I-14
    comps = c5_decompose(history, seed, trials, epsilon, max_imf, extension, ext_days)
    tail = np.full((C5_MAX_COMPONENTS, keep), np.nan)
    tail[:len(comps)] = comps[:, -keep:]
    periods = (np.array([c5_period(ch) for ch in c5_channels(comps)]) if len(comps) >= C5_N_CHANNELS
               else np.full(C5_N_CHANNELS, np.nan))
    return tail, len(comps), periods


def c5_decompose_city(aqi, available, seed, n_jobs=1, trials=C5_TRIALS, epsilon=C5_EPSILON,
                      max_imf=C5_MAX_IMF, w_max=C5_W_MAX, min_history=C5_MIN_HISTORY, keep=C5_KEEP,
                      extension='none', ext_days=C5_EXT_DAYS):
    '''Causal decompositions of one city on its D1 calendar (aqi, available from d1_calendar_city).

    Returns {'days', 'tail' (n, C5_MAX_COMPONENTS, keep), 'n_components', 'periods' (n, 5), 'history_len'}.
    '''
    days = c5_days(available, min_history)
    jobs = [(c5_history(aqi, available, t, w_max), seed, trials, epsilon, max_imf, keep, extension, ext_days)
            for t in days]
    if n_jobs > 1:
        from multiprocessing import Pool
        with Pool(n_jobs) as pool:
            out = pool.map(_c5_job, jobs, chunksize=max(1, len(jobs) // (8 * n_jobs)))
    else:
        out = [_c5_job(j) for j in jobs]
    return {'days': days.astype(np.int64),
            'tail': np.stack([o[0] for o in out]) if out else np.empty((0, C5_MAX_COMPONENTS, keep)),
            'n_components': np.array([o[1] for o in out], dtype=np.int64),
            'periods': np.stack([o[2] for o in out]) if out else np.empty((0, C5_N_CHANNELS)),
            'history_len': np.array([len(j[0]) for j in jobs], dtype=np.int64)}


def c5_fingerprint(dates, aqi, available, seed):
    '''Identifies the input of a city's decompositions: calendar, available days, AQI on them, seed.'''
    available = np.asarray(available, dtype=bool)
    h = hashlib.sha256()
    h.update(pd.to_datetime(pd.Series(dates)).dt.strftime('%Y-%m-%d').str.cat(sep=',').encode())
    h.update(available.tobytes())
    h.update(np.asarray(aqi, dtype=np.float64)[available].tobytes())
    h.update(str(int(seed)).encode())
    return h.hexdigest()


def c5_load_or_compute(city, dates, aqi, available, seed, cache_dir, n_jobs=None, **params):
    '''Decompositions of one city, from cache_dir/c5_<city>.npz if it was made with the same settings and input,
    otherwise computed and saved. A file made with other settings or other input raises instead of being reused
    or silently overwritten: delete it to recompute.'''
    expected = c5_params(**params)
    fp = c5_fingerprint(dates, aqi, available, seed)
    path = Path(cache_dir) / f'c5_{city}.npz'
    if path.exists():
        saved = np.load(path, allow_pickle=False)
        meta = json.loads(str(saved['meta']))
        if meta['params'] != expected or meta['fingerprint'] != fp:
            raise ValueError(f'C5: {path} was made with other settings or input ({meta["params"]}); delete it to recompute')
        return {k: saved[k] for k in ('days', 'tail', 'n_components', 'periods', 'history_len')}
    n_jobs = n_jobs or os.cpu_count() or 1
    dec = c5_decompose_city(aqi, available, seed, n_jobs=n_jobs, **params)
    short = int((dec['n_components'] < C5_N_CHANNELS).sum())
    if short:
        logger.warning(f'C5: {city}: {short} of {len(dec["days"])} days have fewer than {C5_N_CHANNELS} components; '
                       f'windows ending on them cannot be built (decision needed)')
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + '.partial.npz')
    np.savez_compressed(tmp, meta=json.dumps({'city': city, 'params': expected, 'fingerprint': fp}), **dec)
    os.replace(tmp, path)
    return dec


def c5_spot_check(dec, aqi, available, seed, n_check=3, rng_seed=0, **params):
    '''Recompute n_check saved days one at a time and require exact equality (checks a parallel run).'''
    p = c5_params(**params)
    rng = np.random.default_rng(rng_seed)
    for r in rng.choice(len(dec['days']), size=min(n_check, len(dec['days'])), replace=False):
        h = c5_history(aqi, available, int(dec['days'][r]), p['w_max'])
        tail, n_comp, periods = _c5_job((h, seed, p['trials'], p['epsilon'], p['max_imf'], p['keep'],
                                         p.get('extension', 'none'), p.get('ext_days', C5_EXT_DAYS)))
        if not (n_comp == dec['n_components'][r] and np.array_equal(tail, dec['tail'][r], equal_nan=True)
                and np.array_equal(periods, dec['periods'][r], equal_nan=True)):
            raise ValueError(f'C5: saved decomposition of day {int(dec["days"][r])} is not reproduced')


def c5_rows(dec, days):
    '''Row of each calendar day in dec. Raises if a day was not decomposed.'''
    days = np.asarray(days, dtype=np.int64)
    rows = np.searchsorted(dec['days'], days)
    if len(days) and (rows.max() >= len(dec['days']) or not np.array_equal(dec['days'][rows], days)):
        raise ValueError('C5: a requested day has no decomposition (history shorter than the minimum?)')
    return rows


def c5_window_channels(dec, starts, seq_len):
    '''a1 channel values of each window, from the decomposition at its last input day: (n, seq_len, 5).'''
    out = np.empty((len(starts), seq_len, C5_N_CHANNELS))
    for i, r in enumerate(c5_rows(dec, np.asarray(starts) + seq_len - 1)):
        k = int(dec['n_components'][r])
        if k < C5_N_CHANNELS:
            raise ValueError(f'C5: the decomposition of day {int(dec["days"][r])} has {k} components, '
                             f'a1 needs {C5_N_CHANNELS} (decision needed)')
        out[i] = c5_channels(dec['tail'][r, :k, -seq_len:]).T
    return out
