# Persistence and seasonal-climatology baselines: design (fixed 13 Oct 2026, before any baseline was computed)

Decision S-2 (`exports/paper_draft_v1/revision_1/PAPER_STRENGTHENING_SUGGESTIONS_13Oct2026.md`), chosen by the user on
13 Oct 2026 ("Do baselines + count first"). This file is written before any baseline value is computed. The script
`baselines.py` prints this file's SHA-256 into its outputs, and the record quotes it. Nothing below is changed after the
first run. Any later variant is reported separately and labelled as added after the fact.

## Windows
- Exactly the 6,171 test windows of the run of record (AQI target, lookback 7, 18 cities, targets 1 Jul 2019 to
  1 Jul 2020). Rebuilt with the frozen helper cells (`e1_verification/common.py`, unchanged) from the hash-pinned
  `city_day.csv`.
- Check before scoring: the rebuilt city, target date and observed AQI of every test window equal those stored with the
  main model's predictions (`phase4_v2_results_r1_ext/reports/r116_test_predictions_lb7.npz`). Stop if any differ.

## Baselines
- **Persistence (P).** Forecast for the target day = the AQI of the origin day (the day before the target) on the
  run-of-record calendar. That is the observed value, or for a filled day the copy of the last observed day (gaps of at
  most 3 days, past values only). It is the last value of the AQI history the model receives.
- **Seasonal climatology (C).** Forecast = the city's mean observed AQI over training-period days (observed days dated
  before 1 Apr 2019) whose day of year lies within ±15 days of the target's day of year. Circular over a 365-day year.
  29 February is mapped to 28 February. At least 10 such days are required, otherwise the city's training-period mean
  is used (the number of such forecasts is reported). No test or validation data enter.
- No other baseline, window width or threshold is computed in this step.

## Reference model
- The main model (CEEMDAN+iTransformer with the scalar city bias), its 5 model seeds 123, 42, 2024, 7 and 2025, from the
  stored test predictions (`pred__bias__<seed>`). Their pooled R² must reproduce the reported 0.821 ± 0.014.

## Metrics (all reported whichever way they come out)
- R² (1 − SS_res / SS_tot over the scored windows), RMSE, MAE and MAPE (mean of |error| / observed × 100), with the
  same formulas for every forecast.
- Subsets: all test windows, before the lockdown (target before 25 Mar 2020) and lockdown/Unlock (from 25 Mar 2020).
- Per city: MAE and R² for P, C and the main model (mean over seeds).
- Skill: MAE skill score of the main model against each baseline, SS = 1 − MAE_model / MAE_baseline, per seed, then
  mean ± s.d. over seeds. Per city: the number of cities where the main model's seed-mean MAE is below the baseline's.
- No hypothesis tests and no pass/fail rules. The baselines are descriptive reference points for the forecasting
  results.
