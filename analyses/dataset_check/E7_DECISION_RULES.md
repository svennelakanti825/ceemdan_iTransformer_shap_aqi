# E7 decision rules: official CPCB bulletins over a longer record (written 8 Oct 2026, before any E7 model was fitted)

This is the authors' pre-specification of the bulletin analysis, published as an excerpt. The data, the analyses and
every rule below are reproduced verbatim. Edits: the opening paragraph on the motivation is replaced by one sentence,
file paths are given as they are in this repository, a pointer to an internal planning note is removed, and the
source of the addendum is described in general terms.

## Question
Does a three times longer record of official daily AQI make city timescale signatures and the forecasting contribution
of past-only decomposition modes stable and city-specific?

## Data (fixed)
- **Larger dataset.** CPCB daily AQI bulletins (official city-average AQI, AQI category, prominent pollutant), as
  scraped and processed by urbanemissions.info.
  - File: `data_bulletins/AllIndiaBulletinsMaster2025_openrefined.csv` from github.com/urbanemissionsinfo/AQI_bulletins
    (data/Processed, main branch, GPL-3.0). SHA-256 in `data_bulletins/SHA256SUMS.txt`.
  - Coverage: 297 cities, 2015-05-01 to 2025-12-31. AQI only, no pollutant concentrations.
- **Reference dataset.** The Kaggle `city_day.csv` used by the paper (`data/city_day.csv`).

## D0. Comparability (descriptive, no rule)
- Per Kaggle city, on overlapping dates:
  - Pearson r of daily AQI, bulletin against Kaggle;
  - median difference.
- Cities with r < 0.8 are flagged.

## D1. Do city timescale signatures become stable with a longer record? (bulletin data, descriptive)
- **Eligible cities.** At least 80% of days present in each of at least 8 of the 10 calendar years 2016-2025.
- **City-years.** A city-year enters only if that year has at least 80% coverage.
- **Bands.** As E2, on log AQI over each city's calendar, from centred moving averages (minimum 60% of the window):
  - B1 <7 d
  - B2 7-31 d
  - B3 31-91 d
  - B4 >91 d

  Each band's variance share is taken within each city-year, over days where all bands are finite.
  Descriptive only, nothing is forecast.
- **Statistics, per band:**
  - ICC(1) across city-years;
  - Spearman ρ of city means, 2016-2020 against 2021-2025 (5-year halves);
  - the same for 2-year means, 2016-2017 against 2018-2019 (Kaggle-length analogue);
  - Spearman-Brown projected reliability for 1, 2, 5 and 10 years.
- **Rule D1.** City signatures are stable with the longer record if the 5-year-halves ρ is at least 0.7 with
  p < 0.05 for both B1 and B2.
- **Submitted contrasts, tested year by year (pass = at least 8 of the years both cities have):**
  - (i) Gurugram B1 share > Delhi B1 share (Gurugram "short-term dynamics")
  - (ii) Delhi B2 share > Gurugram B2 share (Delhi "fortnightly")

## D2. Do causal temporal modes carry stable, city-specific forecast information over a longer record? (bulletin data)
- **Cities (fixed rule).** The Kaggle-modelled cities whose bulletin record spans at least 8 years with at least
  85% coverage. That gives 14: Amaravati, Amritsar, Bengaluru, Chennai, Delhi, Gurugram, Hyderabad, Jaipur,
  Kolkata, Lucknow, Mumbai, Patna, Thiruvananthapuram, Visakhapatnam.
- **Pipeline.** As r1_ext, reused from the helper cells:
  - D1 calendar, forward fill of at most 3 days;
  - causal CEEMDAN on the last 365 available days, at least 180 days of history;
  - 100 trials, epsilon 0.2, max_imf 8, AR end extension of 30 days;
  - seed 123 + index of the city in the sorted list of the 14.
- **Origins (compute budget).** Last input days whose calendar index is divisible by 5.
- **Windows.**
  - Lookback L = 7: all 7 input days available.
  - Horizons h = 1 and h = 7: target observed at origin + h.
- **Arms** (all include a city one-hot):
  - RAW: the 7 AQI values
  - RAW+MA: RAW + trailing means of available AQI at the origin (3, 7, 14, 31 d)
  - RAW+MA+OSC: RAW+MA + IMF1-4 × 7
  - DEC: the 5 causal channels × 7, the paper design without pollutants
- **Folds.** Evaluation years 2019-2025 by target date. The fit uses all earlier targets. Early stopping on the
  last 10% of the fit period. XGBoost (E1 PARAMS), seeds 0, 1, 2. Exact TreeSHAP.
- **Learning curve.** For evaluation years 2023, 2024 and 2025, also fit on the 3 preceding years only ("short").
- **Gain.** gain_osc = (MAE[RAW+MA] − MAE[RAW+MA+OSC]) / MAE[RAW+MA] × 100, pooled and per city.
- **Rules (each applied per horizon):**
  - **P1, shared signal beyond smoothing.** Pooled MAE gain > 2 × the larger seed s.d., in at least 5 of 7 folds.
  - **P2, city-specific and stable.** Spearman ρ of per-city mean gain_osc, folds 2019-2021 against 2022-2025,
    at least 0.6 with p < 0.05 (n = 14). ICC over the 7 folds is also reported.
  - **P3, more data helps.** The long-history pooled MAE gain exceeds the short-history gain by more than 2 ×
    the larger seed s.d., in at least 2 of 3 years.

## Overall verdict (fixed)
- **D1 and P1 and P2 pass:** a longer dataset brings the city-specific claim back in leakage-free form.
  Recommend the dataset extension.
- **D1 passes, P2 fails:** the longer data support a descriptive city typology of AQI variability, but not
  city-specific predictive temporal drivers.
- **D1 fails:** dataset size does not bring the city-specific claim back.

All results are reported whichever way they come out. The bulletin data hold no pollutants, so E7 cannot test
pollutant-against-mode attribution shares, only the timescale part.

## Addendum 1 (8 Oct 2026, written after D0/D1 and before any D2 model was fitted)
Prompted by an internal review of the design, which found:
- decomposition histories join available values across long gaps;
- the raw-history comparison has a shorter information horizon than the decomposition.

Two dataset-side levers are added.

- **D2b, matched-history control.**
  - New arms:
    - RAW+MAL: RAW + trailing calendar means of available AQI at the origin over 3, 7, 14, 31, 91, 182 and
      365 days, matching the decomposition's 365-sample memory;
    - RAW+MAL+OSC.
  - **P1b:** P1's rule applied to MAE[RAW+MAL] − MAE[RAW+MAL+OSC]. If P1 holds and P1b fails, the modes add
    longer memory, not timescale structure.
- **D2c, gap-free histories (calendar-aware eligibility).**
  - Only windows whose 365-sample decomposition history spans exactly its own length in calendar days, i.e.
    contains no unavailable day. This is 6,610 of 9,229 origins.
  - Fit and evaluation use only those windows. Arms RAW+MA and RAW+MA+OSC, long history.
  - P1 and P2 are applied unchanged. If P2 passes here but not on all windows, gap compression was hiding
    city-specific structure.
- **Overall verdict extension.** A longer, cleaner dataset brings the city-specific claim back only if D1 passes
  and P2 passes, either on all windows or on gap-free windows, with P1b also passing.

**Status at the time of writing.** D1 failed its rule (B2 halves ρ 0.61 < 0.7). The D1 station-count check was
post hoc. Contrast (i) passed and contrast (ii) failed.
