# C2 pre-registration: weather and timescale, confirmatory test on the test year (XGBoost)

**Status: APPROVED by the user on 10 Oct 2026 (the DRAFT 1 text, with only this line changed). Written before any C2 model was fitted.**
- On approval, the file's SHA-256 is recorded in `exports/paper_draft_v1/revision_1/C2_TASK_TRACKER.md` and the file
  is committed before the full run (C2-T6). Any later change is a dated addendum, and the original text stays.
- Design record: `C2_IMPLEMENTATION_PLAN_08Oct2026.md` (sections 13-16) and the tracker (C2-T1: decisions T1-a,
  T1-b, T1-c, R-a, R-b, R-c).

## 0. What was known before this file was written
- **Development years (targets before 2019-04-01).** E5 (pre-registered 8 Oct) ran the same features with
  in-period year-swapped nulls on two folds:
  - forecast-day weather (MET_PP) passed E5's H1 and H2 in both folds;
  - origin-day weather (MET) failed;
  - city-specific effects failed.
- **Test year, already seen (disclosure A4).** E1 and E3 (8 Oct, 3 seeds) used the same windows and model. E3 found
  that raw forecast-day weather (6 variables, no bands, no null) gave a test MAE of 21.56:
  - 22.83 with no weather (5.6% lower);
  - 22.57 with a seasonal clock (4.5% lower).
  E3's per-arm seed s.d. (0.25-1.28 MAE) was used to plan the power of this test (`c2_t1_design_check.py`, Part 3).
  BASE seeds 0-2 were fitted in E1 and E3 (Q9).
- **Not seen on the test year:** banded weather, any null arm, the pool years, and any SHAP share of weather. No
  `c2x_*` output exists.

## 1. Question and scope
**Question.** On the test year, does the observed weather of the forecast day explain part of the day-to-day
variation in AQI beyond seasonal climatology? Does that part lie at short timescales (under 31 days)?

**Role.** A diagnostic that answers reviewer comments R1.4 and R3.2. It is not a forecasting result and never
enters Table 2. The main arm uses the weather of the target day ("perfect prognosis"), which a forecaster would
only have as a weather forecast. The arm with weather up to the forecast origin is the operational counterpart.

**What C2 cannot show:**
- (a) forecasting skill (no weather forecasts are used);
- (b) that the iTransformer or its CEEMDAN channel attributions reflect weather. C2 tests the data with a
  low-noise model on the same windows;
- (c) city-specific effects;
- (d) causation. Results are associations in a reanalysis.

## 2. Pinned inputs
- **Hash rule.** SHA-256. Text files (.py .md .csv .txt .json) are hashed after converting CRLF to LF. Binary files
  are hashed as they are. The hashes are therefore the same on every operating system. All hashes are in Appendix A.
- **AQI data.** `exports/paper_draft_v1/revision_1/Revised_Overleaf/audit_inputs/city_day.csv`, as read by
  `common.py`.
- **Weather, real years.** `Implementation/revision_1/e1_verification/outputs/era5_daily.csv`: 18 cities, 2015-01-01
  to 2020-07-01.
- **Weather, pool years.** `.../outputs/era5_daily_pool.csv`: the same 18 cities, grid cells and processing,
  2004-09-01 to 2014-12-31.
- **Weather source.** Both files are ERA5 via Open-Meteo (CC BY 4.0, Hersbach et al. 2020) and are tracked in git
  with `-text` (`ERA5_SOURCE.txt`).
- **Causal CEEMDAN cache.** `Implementation/revision_1/phase4_v2_results_r1/models/c5_decompositions_ext_ar/`,
  18 files. Each is also matched to its input by fingerprint on loading (`common.load_causal`).
- **Imported code** (used unchanged): `common.py`, `e1_leakage_contrast.py` (PARAMS), `e5_driver_band_precheck.py`
  (`met_bank`, `swap_dates`, `MV`, `BANDS`), and the helper cells `d1`, `r19`, `c5`, `n1` in `tools/`.
  - At reviewer-repository packaging (C2-T10), `common.py` gets a relative data path. That changes its hash, not
    its logic, and C2-T10 checks that the outputs stay identical.
- **Window identity.** 18 cities:
  - Ahmedabad, Amaravati, Amritsar, Bengaluru, Brajrajnagar, Chennai, Delhi, Gurugram, Hyderabad, Jaipur,
    Jorapokhar, Kolkata, Lucknow, Mumbai, Patna, Talcher, Thiruvananthapuram, Visakhapatnam;
  - 11,569 training, 1,510 validation and 6,171 test windows.
- **Software and hardware.** Python 3.13.0, xgboost 3.2.0, numpy 2.4.2, pandas 3.0.1, scipy 1.17.1, on the laptop
  CPU (Intel i5-1135G7, 4 cores, 16 GB). The XGBoost thread count is fixed before the run (C2-T5) and recorded in
  the verdict.

## 3. Windows, splits and periods
- **Windows.** LB7 windows as built by `common.build_lb7` (run of record: D1 calendar, R1.9 split, N1 fill).
  - Input days t-6 to t; the origin day is t.
  - The target is the AQI of day t+1.
- **Splits by target date:**
  - training: before 2019-04-01;
  - validation: 2019-04-01 to 2019-06-30, used only for early stopping;
  - test: 2019-07-01 to 2020-07-01, used only for evaluation and SHAP.
- **Periods by target date:**
  - pre-lockdown: 2019-07-01 to 2020-03-24;
  - lockdown/Unlock: 2020-03-25 to 2020-07-01 (`LOCKDOWN_START` in r1_ext).

## 4. Features and arms
**BASE (137 features).** As E1/E3 CAUSAL and E5 BASE:
- 12 pollutants × 7 days (N1-filled);
- 5 causal CEEMDAN channels (IMF1-4, Slow) × 7 days;
- city one-hot (18).

**Weather bank (24 features).** Built by `met_bank`, imported unchanged.
- **Variables:** log boundary-layer height, wind speed, log ventilation, 2 m temperature, relative humidity,
  √precipitation.
- **Bands for day d,** where Mk(d) is the mean over days d-k+1 to d:
  - synoptic = v(d) - M7(d);
  - intraseasonal = M7(d) - M31(d);
  - subseasonal = M31(d) - M91(d);
  - seasonal = M91(d).

  The four bands sum to v(d).
- The bank is computed on each weather file's own chronology, then looked up by date.

**Arms.** Each arm appends one weather block to BASE.

| Arm | Weather block | Role |
|---|---|---|
| BASE | none | reference |
| MET | real bank at origin day t | operational counterpart |
| MET_PP | real bank at target day t+1 | main diagnostic |
| MET_PP_LONG | MET_PP with only the subseasonal and seasonal bands (12 features) | short-band ablation (R-c) |
| POOL_j, j = 0..9 | bank at t, from pool year P_j | primary nulls for MET |
| POOL_PP_j, j = 0..9 | bank at t+1, from pool year P_j | primary nulls for MET_PP |
| E5NULL_k, k = 1..4 | bank at t, from `swap_dates(·, k)` (E5 rule) | secondary sensitivity |
| E5NULL_PP_k, k = 1..4 | bank at t+1, from `swap_dates(·, k)` | secondary sensitivity |

**Pool rule (R-a).**
- For a lookup date with calendar year y, null set j uses the same month and day in pool year
  P_j(y) = 2005 + ((y - 2015 + j) mod 10). 29 February maps to 28 February.
- All pool years (2005-2014) lie outside the AQI record, so a null never uses the own year or the test period.
- Within a set, different own years get different pool years. Across the 10 sets, every own year meets every pool
  year once.

**Totals.** 32 arms × 40 seeds = 1,280 fits.

## 5. Model and fitting
- **Model.** `xgboost.XGBRegressor(random_state=s, **PARAMS)` with the E1 PARAMS:
  n_estimators 3000, learning_rate 0.03, max_depth 6, subsample 0.8, colsample_bytree 0.8, min_child_weight 5,
  reg_lambda 1.0, tree_method hist, early_stopping_rounds 100.
- **Seeds:** s = 0, 1, …, 39 for every arm.
- **Fitting.** Fit on training windows, with `eval_set` = validation windows. Predictions use the best iteration.
- **SHAP.** Exact TreeSHAP: `pred_contribs=True` with `iteration_range=(0, best_iteration + 1)`, on the test
  windows.
  - This is the same model that made the predictions. E1, E3 and E5 used all trees (best iteration + 100). That is
    corrected here.
  - Additivity is checked for every fit: |sum of contributions + bias - prediction| < 0.01 AQI units on every test
    window. Using all trees gives gaps of about 0.2 in a synthetic test, so this catches the wrong model.

## 6. Measures
Computed for each arm × seed on the test windows, for the full test year and for each period.
- **Errors:** MAE, RMSE, R².
- **Shares.** For a set of windows W, c_f = mean over W of |φ_f|, where φ_f is feature f's SHAP value. The share of
  a group G = 100 × Σ_{f∈G} c_f / Σ_f c_f.
- **Feature groups:**
  - pollutants;
  - oscillatory channels (IMF1-4);
  - slow channel;
  - city;
  - weather, all;
  - weather by band: synoptic, intraseasonal, subseasonal, seasonal;
  - weather by variable group: dispersion (log BLH, wind, log ventilation), temperature, humidity, rain.
- **Short-band share** = synoptic share + intraseasonal share.
- **Per city** (descriptive): cities with at least 150 test windows.

## 7. Statistical procedures (fixed)
**Notation.**
- S = 40 seeds. X_{A,s} is a per-run measure (MAE or a share) of arm A at seed s, and X̄_A is its mean over seeds.
- For a real arm R, the primary null family is the K = 10 pool sets N_j (POOL_PP_j for MET_PP, POOL_j for MET).
- m_j = X̄_{N_j}, m̄ = mean_j m_j, and s_m = the standard deviation of the m_j (ddof 1).

**Prediction test (decision T1-b).** One observation per weather draw. Under the null hypothesis, the real weather
is one more same-season draw, so its arm mean varies like a new null-set mean.
- **Effect:**
  - for MAE, d = m̄ - X̄_R (positive means real weather lowers the error);
  - for a share, e = X̄_R - m̄.
- **Test.** SE = s_m × √(1 + 1/K). t = effect / SE. One-sided p = P(T_{K-1} ≥ t).
- **90% interval (decision T1-c):** effect ± t_{K-1, 0.95} × SE, with t_{9, 0.95} = 1.8331.
- **Percentage for MAE:** g = 100 × d / m̄. The interval is the MAE interval × 100 / m̄. The relative standard
  error of m̄, s_m / (√K × m̄), is printed.

**Welch test** (real against real arms; only training randomness differs):
- d_W = X̄_A - X̄_B and SE = √(v_A/S + v_B/S), with Welch–Satterthwaite degrees of freedom;
- one-sided p, and a 90% interval d_W ± t_{df, 0.95} × SE.

**Multiplicity.**
- The primary rules are tested in a fixed order (H1, then H2, then H1b), each at one-sided α = 0.05.
- A rule is tested only if all earlier rules passed. Otherwise its estimate and interval are reported as "not
  tested in sequence".
- This keeps the chance of any false primary claim at 5%. Secondary and descriptive results carry no claim.

## 8. Rules (fixed)
**Primary** (R = MET_PP against the 10 POOL_PP sets, full test year):
- **H1** (weather of the forecast day beyond seasonal climatology), measure MAE:
  - passes if the prediction-test p < 0.05 **and** X̄_R is below every m_j.
- **H2** (the effect lies at short timescales), measure short-band share:
  - passes if e ≥ 2.0 percentage points (the convention carried over from E5) **and** the prediction-test
    p < 0.05.
- **H1b** (the forecast day adds to the forecast origin), measure MAE, Welch, MET_PP against MET:
  - d_W = X̄_MET - X̄_MET_PP;
  - passes if p < 0.05.
- **Lockdown check (R-b).** If H1 passes, the H1 prediction test is repeated on the pre-lockdown test targets. If
  that p ≥ 0.05, the lockdown sentence of section 9 is added to the wording.

**Secondary** (reported with the same statistics, no primary claim):
- **P** (operational counterpart): H1 and H2 computed for R = MET against the 10 POOL sets, in their own fixed order.
- **H4** (seasonal band, descriptive): the seasonal-share excess of MET_PP over the POOL_PP sets, with its 90%
  interval.
- **Short-band ablation (R-c):** X̄_MET_PP_LONG - X̄_MET_PP in MAE, with a Welch 90% interval and one-sided p.
  Positive means the short bands lower the error.
- **E5 sensitivity:**
  - all primary computations repeated against the 4 E5 null sets (K = 4, t_{3, 0.95} = 2.3534);
  - E5's verbatim rules. H1: X̄_R below every null mean. H2: short share minus the largest null short share
    ≥ 2 pp, and the seasonal share within the null range.
- **Weather against no weather:**
  - X̄_BASE - X̄_A for A = MET and MET_PP: Welch 90% intervals;
  - X̄_BASE - m̄ for each null family, with the null set as the unit: SE = √(v_BASE/S + s_m²/K), K - 1 degrees of
    freedom.
- **Climate check:** for each variable and band, the mean of the bank over the pool years against the real years,
  per city.

**Descriptive only** (no p-values): per period, per city and per variable group.

**Gate for the iTransformer (C2-11).**
- g as in section 7, for MET_PP against the POOL_PP sets, on the full test year (point estimate).
- The iTransformer test (option A) is planned only if g ≥ 13%.
- If it is, C2-T8 first recomputes option A's power including the spread between null sets, and A gets its own
  pre-registration addendum before it runs.
- If g < 13%, A is not run, and the paper states why.

## 9. Wording (paper prose, fixed; numbers come from the verdict)

| Result | Wording |
|---|---|
| H1, H2 and H1b pass | "In a diagnostic setting where the forecast day's weather is known, short-timescale weather explains part of the day-to-day variation in AQI beyond seasonal climatology (MAE X% lower, 90% interval a to b), and it adds to the weather of the forecast origin." |
| H1 and H2 pass, H1b fails | "The forecast day's weather explains part of the variation in AQI beyond seasonal climatology (MAE X% lower, 90% interval a to b). It adds no detectable skill beyond the weather of the forecast origin." |
| H1 passes, H2 fails | "The forecast day's weather lowers the error beyond seasonal climatology (MAE X% lower, 90% interval a to b), but the effect is not shown to lie at short timescales." |
| H1 fails | No weather claim. Reported as found. |

**Added sentences:**
- **Lockdown sentence** (R-b, when triggered): "The effect is not separately confirmed outside the COVID-19
  lockdown period."
- **Operational counterpart:**
  - if P's H1 passes: "Weather known at the forecast origin also lowers the error beyond seasonal climatology (MAE X%
    lower, 90% interval a to b)."
  - otherwise: "Weather known at the forecast origin adds no detectable skill beyond seasonal climatology."
- **Always reported:** H4, the ablation, the E5 sensitivity, the per-period, per-city and variable-group results,
  and the limitations in section 11.

## 10. Integrity checks (implemented in C2-T3 tests, the C2-T5 runner and the C2-T7 audit)
- **No look-ahead:**
  - changing ERA5 values after day t+1 leaves MET_PP unchanged, and after day t leaves MET unchanged;
  - changing day t+1 changes MET_PP but not MET.
- **No AQI or pollutant information in any weather feature.** Weather is built only from the two pinned ERA5 files.
- **No test data in fitting.** Changing test-period AQI leaves every fitted model unchanged.
- **Null rules:**
  - pool lookups always fall in 2005-2014, on the same month and day (or 28 February);
  - within a set, different own years map to different pool years;
  - E5 nulls never use the own year;
  - every lookup is finite.
- **Alignment.** Dates are joined by calendar date. ERA5 days are Indian Standard Time days.
- **Window identity.** 18 fingerprints and 11,569 / 1,510 / 6,171 windows.
- **SHAP.** Computed on the best iteration, with the additivity check of section 5.
- **Reproducibility.**
  - A full rerun on the same machine, library versions and thread count must give byte-identical outputs.
  - An independent audit recomputes the metrics from saved predictions and recomputes the verdict and the gate.
- **Freeze.** The verdict file records the SHA-256 of this file, every script and every input.
- **Stop on failure.** Any failed check (hash, window identity, finite features, additivity) stops the run. No
  verdict is written from a run with a failed check, and the failure is logged and reported.

## 11. Limitations (stated with the results)
- The test is conditional on one test year and these 18 cities. The pooled MAE is dominated by high-AQI cities.
- Each city is represented by one 0.25° ERA5 grid cell, with Open-Meteo's land cell selection and elevation
  downscaling.
- **Reanalysis, not observations.** ERA5 assimilates no surface air-quality data (that is the separate CAMS
  reanalysis), and its aerosols are not the observed ones. Feedback from pollution to weather is therefore not
  represented, and the analysis is associational.
- **Perfect prognosis.** The main arm is not a forecast. Archived weather forecasts (for example TIGGE) are future
  work.
- **Attribution.** Path-dependent TreeSHAP shares credit among correlated inputs. H2 is an attribution result, which
  the ablation complements.
- **Climate shift.** The pool years (2005-2014) are earlier than the real years. Each arm is trained and tested
  within itself, and the climate check reports the shift.
- **Confirmation after exploration.** The test year was partly seen by E3 (section 0).

## 12. Deviations from E5

| Item | E5 | C2 |
|---|---|---|
| Data | development folds F1, F2 (targets before 2019-04-01) | run-of-record split, test year |
| Seeds | 3 | 40 |
| Nulls | 4 in-period year swaps | 10 pool years outside the AQI record (primary). E5's 4 kept as secondary |
| H1 | real mean below every null mean | prediction test p < 0.05 and below every null mean |
| H2 | short share - largest null share ≥ 2 pp, and seasonal share within the null range | short-share excess over the null mean ≥ 2 pp and prediction test p < 0.05. Seasonal part moved to H4 (descriptive) |
| H1b, ablation, lockdown check, gate | none | added |
| H3 (city-specific) | tested | not tested (one period). Per-city results descriptive |
| SHAP | all trees | best iteration, additivity checked |
| N1 fill constant | stated departure | none (it is the run-of-record constant on this split) |
| Intervals | none | 90%, matching the one-sided 5% tests |

## 13. Reporting commitment
- All results are reported whichever way they come out.
- If anything changes after the first full run, the first run is still reported, and the change is a new, labelled
  run.

## Appendix A. SHA-256 of pinned inputs (hash rule of section 2; computed 10 Oct 2026)

| SHA-256 | File |
|---|---|
| 0d84b21c3e4878bbad8df362f2ab05f61ad959538dddf5918e714077ed3c1847 | exports/paper_draft_v1/revision_1/Revised_Overleaf/audit_inputs/city_day.csv |
| c757a0875981429d3fbd4049fecb6e4dda92a06470a45a7f712929a408c69c99 | Implementation/revision_1/e1_verification/outputs/era5_daily.csv (raw bytes: 1e2886f34e3e56f779e07a244f2447f2a03bfb700abbfd2b7fe2af2b5b2bae65) |
| c8d72b276b28e3c5e5c15c86807f67eb7a9233f838d3ba5feee63af3237de5d1 | Implementation/revision_1/e1_verification/outputs/era5_daily_pool.csv (raw bytes: a45a76ee31ae917ad73519f98b4d4e30034285c293f3ef632d9e55aa28e8c8cc) |
| dd1a9716406d6521d9f418b9046a5ec96438a344e7a37cbd96a5efd2a3d1ade3 | Implementation/revision_1/e1_verification/common.py |
| ee0bef59ac6228b23dea9182f0e3581eee6ec220f7bd2a9ba33a1366a158b8f2 | Implementation/revision_1/e1_verification/e1_leakage_contrast.py |
| c4075fdbfaffbbc7aac1b41b26a49eb277c89d8f2047fcb24ccff2a9d280563a | Implementation/revision_1/e1_verification/e5_driver_band_precheck.py |
| 1e491c819f49ac7ded2aefa1a7e4dffc7e0dc187f2b089a5922519f66332e333 | Implementation/revision_1/e1_verification/fetch_era5.py |
| b1164c742948c415d7e72a8d3fb34982088a27b0d05986f2e6fcca05bc80ac08 | Implementation/revision_1/e1_verification/fetch_era5_pool.py |
| db5d76348a619cbad3b8e9148230155decdeb129b9ec536c266194dfb02e5c57 | Implementation/revision_1/tools/d1_helper_cell.py |
| e56b88b99f17f8dd94d871c567e41dd4ad35bbc88ca8e134e21ffe45f5a75630 | Implementation/revision_1/tools/r19_helper_cell.py |
| 7fe091af1bba71fd3c633dbf33eaab02bc72e3ea2c5f62fd2bcfe0c0f950f34f | Implementation/revision_1/tools/c5_helper_cell.py |
| 8dd39cff622a1598ad59ba64871e54d7f8f8877cc36ba024aabd4d557c6cd787 | Implementation/revision_1/tools/n1_helper_cell.py |
| 6ffabbbba15913d044e1e5b9f13c1927661deaf13da7ae96f6f2bc832602da3c | .../c5_Ahmedabad.npz |
| 1a1aef39aba673b77140290fb755cc45478427d86077f176996f0f9b97a7e645 | .../c5_Amaravati.npz |
| ba1f5a8384122281ebb1d36d74097fd4ed02902b8edb470362a98b5a17969f01 | .../c5_Amritsar.npz |
| 487630402b20a4eaf51b39db348703e6186392cee9aa8c93e0d6b64be5c700ea | .../c5_Bengaluru.npz |
| 02ff8e921636b3720ab92361b003667dfedece878c6f1e4cac9d0b825eb5b81d | .../c5_Brajrajnagar.npz |
| 3083adf00665d90e44e828e1a6a9bfb20d4ae4bf2835fd96c2a786a7ad07ed87 | .../c5_Chennai.npz |
| 992ca9b7ff6d35292a103ee146dfc54032427e77c849ebd1643db41d72aad014 | .../c5_Delhi.npz |
| 4663945ea4db644545c01b0ef1546d7af2f195ceec951b0b8813fc0217ca08c2 | .../c5_Gurugram.npz |
| d894b77811d54cad05a5e39a62beb52b054f6688bae0e588650100f1a9554c2e | .../c5_Hyderabad.npz |
| 3dc57cce9c5030d134ad9465528e316631484d17289e6e58c8dc6e4b3b525f02 | .../c5_Jaipur.npz |
| bb70a9662428cc3a176f64320b54a4a85c267d78568b0c5304f807f60bd95ae9 | .../c5_Jorapokhar.npz |
| 5564caf3b06861ad1e5eb2c73cedcffbf097a4cbeff58b71f197fb571b06a5ec | .../c5_Kolkata.npz |
| 20e911925e50b1102cb6f027967f544cbb5d09b3dce5093c2b257f7e1e416e04 | .../c5_Lucknow.npz |
| d18b262378860e8bf16a9f3314055198bfb9aa8cc6fe70b7e662bf8c02a71413 | .../c5_Mumbai.npz |
| 37facd6334a6ba0fc1700d5cac65ba9199d9a347b5e70089ec0a2345608d5b88 | .../c5_Patna.npz |
| 2eecd97334cc1b92a6b93e003d434877ba1afa030f5640e3fb2eea1907f7d8fd | .../c5_Talcher.npz |
| e42d910e239448ad367e1331dfec36a97b2917c6708e6549d0ffe1015f0216f9 | .../c5_Thiruvananthapuram.npz |
| 41bc2e554cec78872b46ff24ff2475a80e4b9b05d62199731944ff42fb7c3745 | .../c5_Visakhapatnam.npz |

`.../` stands for `Implementation/revision_1/phase4_v2_results_r1/models/c5_decompositions_ext_ar/`.

## Appendix B. Planned outputs and where each rule reads its numbers

**Outputs** (folder `Implementation/revision_1/e1_verification/outputs/`):
- **`c2x_pooled.csv`.** One row per arm × seed × period (all, pre, lock).
  - Columns: n, best_iter, mae, rmse, r2, pol, dec_osc, dec_slow, city, met, met_syn, met_intra, met_subs,
    met_seas, met_disp, met_temp, met_hum, met_rain.
- **`c2x_city.csv`.** One row per arm × seed × city, full test year, cities with ≥ 150 test windows.
  - Columns: n, mae, met, met_syn, met_intra, met_subs, met_seas.
- **`c2x_predictions.npz`.** Test predictions (float32) per arm × seed, for the audit. Git-ignored, with its hash in
  the verdict.
- **`c2x_verdict.txt` and `c2x_verdict.json`.** Every rule, estimate, interval, p-value, the gate, and all hashes.

| Rule | Arms | Column(s) | Period |
|---|---|---|---|
| H1, gate g | MET_PP, POOL_PP_0..9 | mae | all |
| Lockdown check | MET_PP, POOL_PP_0..9 | mae | pre |
| H2 | MET_PP, POOL_PP_0..9 | met_syn + met_intra | all |
| H1b | MET_PP, MET | mae | all |
| P (H1, H2) | MET, POOL_0..9 | mae, met_syn + met_intra | all |
| H4 | MET_PP, POOL_PP_0..9 | met_seas | all |
| Ablation | MET_PP_LONG, MET_PP | mae | all |
| E5 sensitivity | MET_PP or MET, E5NULL(_PP)_1..4 | mae, met_syn + met_intra, met_seas | all |
| Weather against none | BASE, MET, MET_PP, null sets | mae | all |
| Descriptive | all arms | all columns | all, pre, lock, and per city |
| Climate check | none (computed from the two ERA5 files) | bank means by variable and band | not applicable |
