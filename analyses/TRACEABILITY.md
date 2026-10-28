# Traceability of the numbers in the manuscript

Every number quoted in the main text and the Supplementary Notes, with the file it comes from, grouped by manuscript section and keyed by the Supplementary table label (`tab:...`) that also shows it. `analyses/manuscript/scripts/trace_claims.py` recomputes each value from the files of this repository, compares it with the printed value and writes `analyses/manuscript/outputs/trace_claims.csv`. **Direct** means that a result file prints the number. **Derived** means the number is computed from files that do not print it, and the formula is given.

Status of the last run: 370 values, 370 reproduced, 0 differ; 190 are derived. Differences are listed at the end of this file.

## Abstract

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Share of attribution to the five decomposition channels, 13 cities (lowest) | 14.5 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | min and max over the 13 interpreted cities |
| Share of attribution to the five decomposition channels, 13 cities (highest) | 26.6 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | min and max over the 13 interpreted cities |
| Decomposition share across the 20 models, lowest and highest over the three cities (lowest) | 7.5 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | min of min and max of max over cities |
| Decomposition share across the 20 models, lowest and highest over the three cities (highest) | 34.2 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | min of min and max of max over cities |
| IMF1 to IMF4 share, past-only decomposition (%) | 3.9 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | pooled-city rows (the rows that carry IMF columns), mean over seeds |
| Ratio of the two shares | 6.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | whole-record share / past-only share |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (lowest) | 9.4 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (highest) | 19.1 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Studies whose pipeline lets data after the forecast origin enter | 42 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'i' |
| Same, as a share of 60 (%) | 70 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |

## Results: A leakage-free evaluation on common dates

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Cities in the source file | 26 | tab:coverage | `analyses/e1_verification/outputs/data_audit.csv` | direct | rows of the audit |
| Cities meeting the submitted-analysis minimum-history criterion (307 observed AQI days) | 20 | tab:coverage | `analyses/e1_verification/outputs/data_audit.csv` | derived | valid_aqi >= 307 |
| Modelled cities (at least one eligible training window) | 18 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | train > 0 |
| Cities kept in the coverage audit without an eligible training window | Coimbatore, Guwahati | tab:coverage | `analyses/e1_verification/outputs/data_audit.csv` | derived | valid_aqi >= 307 and train == 0 |
| Windows, training (lookback 7) | 11,569 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of train over the 18 modelled cities |
| Windows, validation (lookback 7) | 1,510 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of validation over the 18 modelled cities |
| Windows, test (lookback 7) | 6,171 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of test over the 18 modelled cities |
| Retained forecast origins (training + validation + test) | 19,250 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | 11,569 + 1,510 + 6,171 |
| Origins whose availability mask differs when recomputed from the calendar prefix | 0 |  | `analyses/e1_verification/outputs/prefix_audit.json` | derived | sum over train, validation, test |
| Test windows whose final input day uses a short-gap-filled AQI value | 59 |  | `analyses/e1_verification/outputs/prefix_audit.json` | direct |  |
| Same count from the data audit | 59 |  | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of test_filled_origin over the 18 modelled cities |
| Median zero-crossing scale of IMF1 across the 18 cities (lowest) | 3.2 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF1 across the 18 cities (highest) | 3.7 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF2 across the 18 cities (lowest) | 6.7 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF2 across the 18 cities (highest) | 7.7 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF3 across the 18 cities (lowest) | 14.6 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF3 across the 18 cities (highest) | 18.2 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF4 across the 18 cities (lowest) | 33.1 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| Median zero-crossing scale of IMF4 across the 18 cities (highest) | 42.8 | tab:periods0 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | min and max over cities of median_d |
| The 5th to 95th percentile range of one channel never overlaps the next, in any city | True | tab:periods1 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | p95_d of channel k < p5_d of channel k+1, all cities and channels |
| Cities where the slow channel reaches the 364-step limit at its 95th percentile | 13 | tab:periods1 | `results/02_r1_ext/reports/table8_channel_periods.csv` | derived | p95_d >= 364 |
| First validation target date | 2019-04-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_VAL_START |
| First test target date | 2019-07-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_TEST_START |
| Last test target date (last day of the data) | 2020-07-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_DATA_END |

## Results: Decomposition adds no accuracy and persistence is a strong reference

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Augmented model, seed 123, test R2 | 0.833 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| Augmented model, seed 123, RMSE | 46.06 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| Augmented model, seed 123, MAE | 27.98 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| XGBoost test R2 | 0.855 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Keras LSTM test R2 | 0.844 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| PyTorch LSTM test R2 | 0.840 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| DLinear test R2 | 0.833 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Five-seed test R2, augmented model (mean) | 0.821 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, augmented model (s.d.) | 0.014 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, plain iTransformer (mean) | 0.819 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, plain iTransformer (s.d.) | 0.017 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, raw-history ablation (mean) | 0.821 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, raw-history ablation (s.d.) | 0.034 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Test R2 over four CEEMDAN realisations x five model seeds (20 models), mean | 0.821 | tab:s_g2 | `results/04_followups/reports/g2_models_lb7.csv` | derived | mean over the 20 models |
| Same, the number after the plus-minus sign: the within-realisation (model-seed) s.d. | 0.017 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | sd_within of the pooled test_r2 row. The s.d. over all 20 models is 0.016 (sd_all) |
| F test of the realisation effect on test R2, F(3,16) | 0.24 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct |  |
| p value of that test | 0.866 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct |  |
| Persistence test R2 | 0.790 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Persistence MAE | 23.86 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| RMSE skill of the augmented model against persistence (mean) | 0.078 |  | `analyses/baselines/outputs/baselines_pooled.csv` | derived | 1 - RMSE(model seed) / RMSE(persistence), over the five seeds. The skill file lists MAE skill only |
| RMSE skill of the augmented model against persistence (s.d.) | 0.036 |  | `analyses/baselines/outputs/baselines_pooled.csv` | derived | 1 - RMSE(model seed) / RMSE(persistence), over the five seeds. The skill file lists MAE skill only |
| Five-seed MAE of the augmented model (mean) | 28.71 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed MAE of the augmented model (s.d.) | 2.62 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE skill against persistence over five seeds (mean) | -0.203 |  | `analyses/baselines/outputs/baselines_skill.csv` | derived | mean and s.d. of skill over the five seeds |
| MAE skill against persistence over five seeds (s.d.) | 0.110 |  | `analyses/baselines/outputs/baselines_skill.csv` | derived | mean and s.d. of skill over the five seeds |
| Cities where the five-seed mean MAE is below persistence | 1 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | count of model_mae_mean < persistence_mae |
| That city | Delhi | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived |  |
| MAE skill before 25 March 2020 (mean) | -0.048 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | subset pre-lockdown |
| MAE skill before 25 March 2020 (s.d.) | 0.076 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | subset pre-lockdown |
| MAE skill before 25 March 2020, over seeds (lowest) | -0.121 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | min and max over seeds |
| MAE skill before 25 March 2020, over seeds (highest) | 0.067 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | min and max over seeds |
| MAE after 25 March 2020 (augmented model, five seeds) (mean) | 27.32 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE after 25 March 2020 (augmented model, five seeds) (s.d.) | 4.07 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE after 25 March 2020 (persistence) | 12.98 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Seasonal climatology test R2 | 0.212 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| XGBoost MAE (the only model with a lower MAE than persistence) | 23.24 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Every model in Table 1 has a higher R2 than persistence | True | tab:performance | `Table 1 sources` | derived | R2 of each single-run row > 0.790 |
| Only XGBoost has a lower MAE than persistence | XGBoost | tab:performance | `Table 1 sources` | derived | single-run rows with MAE < 23.86 |
| Validation R2 at lookback 7 | 0.8036 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 14 | 0.7794 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 21 | 0.7716 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 30 | 0.7817 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Test R2 without the city term (mean) | 0.837 | tab:conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` | direct |  |
| Test R2 without the city term (s.d.) | 0.020 | tab:conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` | direct |  |
| Test R2 with the scalar bias (mean) | 0.821 | tab:conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` | direct |  |
| Test R2 with the scalar bias (s.d.) | 0.014 | tab:conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` | direct |  |
| Cities where the no-city-term model has the lower mean MAE | 15 | tab:conditioning | `results/04_followups/reports/g3_city_wins_lb7.csv` | direct |  |
| Mean forecast error after 25 March 2020, scalar-bias model (AQI units) | 18.1 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | mean of (forecast - observed) over the 1,669 windows from 25 March 2020, averaged over the five seeds. Table 2 prints it (column Mean error after, from make_tables.py), the same predictions reproduce its MAE-after column |
| Mean forecast error after 25 March 2020, no-city-term model (AQI units) | 9.0 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | same for the no-city-term arm |
| Mean forecast error after 25 March 2020, city scale and bias (AQI units) (mean) | 17.0 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | same for this arm |
| Mean forecast error after 25 March 2020, city scale and bias (AQI units) (s.d.) | 6.8 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | same for this arm |
| Mean forecast error after 25 March 2020, city vector and bias (AQI units) (mean) | 15.0 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | same for this arm |
| Mean forecast error after 25 March 2020, city vector and bias (AQI units) (s.d.) | 10.0 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | same for this arm |
| Mean forecast error after 25 March 2020, scalar-bias model (s.d. over seeds) | 6.4 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | Table 2, column Mean error after |
| Mean forecast error after 25 March 2020, no-city-term model (s.d. over seeds) | 4.1 | tab:conditioning | `results/04_followups/reports/g3_test_predictions_lb7.npz` | derived | Table 2, column Mean error after |
| Shared test targets of the three window constructions | 5,828 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, calendar days with short-gap filling (shared targets) (mean) | 0.828 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, calendar days with short-gap filling (shared targets) (s.d.) | 0.015 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, calendar days without filling (mean) | 0.813 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, calendar days without filling (s.d.) | 0.029 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, consecutive observations (shared targets) (mean) | 0.824 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2, consecutive observations (shared targets) (s.d.) | 0.011 | tab:gaps | `results/02_r1_ext/reports/s2_summary_lb7.csv` | direct |  |
| Test R2 without the boundary extension (mean) | 0.791 | tab:gaps | `results/02_r1/reports/multiseed_summary_lb7.csv` | direct | results/02_r1 is the run without the extension |
| Test R2 without the boundary extension (s.d.) | 0.024 | tab:gaps | `results/02_r1/reports/multiseed_summary_lb7.csv` | direct | results/02_r1 is the run without the extension |
| Mean validation R2 without the boundary extension | 0.787 |  | `results/02_r1/reports/r116_conditioning_runs_lb7.csv` | derived | mean over five seeds |
| Mean validation R2 with the boundary extension | 0.789 |  | `results/02_r1_ext/reports/r116_conditioning_runs_lb7.csv` | derived | mean over five seeds |
| Date from which the lockdown and Unlock period starts | 2020-03-25 |  | `analyses/baselines/baselines.py` | direct | constant LOCKDOWN |

## Results: Past PM2.5 dominates AQI attribution

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Test R2 in Chennai | 0.378 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Test R2 in Amaravati | 0.404 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Test R2 in Bengaluru | 0.496 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Interpreted cities in which past PM2.5 has the highest attribution | 13 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | leading_input == PM2.5 among the 13 |
| Modelled cities in which PM2.5 leads | 17 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | leading_input == PM2.5 among the 18 |
| The city where it does not | Ahmedabad | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived |  |
| Share of attribution to the five decomposition channels, 13 cities (lowest) | 14.5 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | min and max over the 13 interpreted cities |
| Share of attribution to the five decomposition channels, 13 cities (highest) | 26.6 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | min and max over the 13 interpreted cities |
| Share to IMF1 to IMF4, 13 cities (lowest) | 1.40 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived |  |
| Share to IMF1 to IMF4, 13 cities (highest) | 4.81 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived |  |
| Slow channel share of the decomposition share, 13 cities (lowest) | 74.7 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived |  |
| Slow channel share of the decomposition share, 13 cities (highest) | 94.7 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived |  |
| Test-year bulletin days naming PM2.5 among the prominent pollutants (%) (lowest) | 11.0 |  | `analyses/dataset_check/outputs/e7_prominent_pm25_test_year.csv` | direct |  |
| Test-year bulletin days naming PM2.5 among the prominent pollutants (%) (highest) | 97.0 |  | `analyses/dataset_check/outputs/e7_prominent_pm25_test_year.csv` | direct |  |
| Cities with PM2.5 named on fewer than half of the days | Amaravati, Amritsar, Jaipur, Mumbai, Thiruvananthapuram |  | `analyses/dataset_check/outputs/e7_prominent_pm25_test_year.csv` | derived | pm25_named_pct < 50 |
| Ahmedabad days with CO equal to NO, 1 January 2015 to 9 April 2020 | 1,317 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Change in the MAE of the other 17 cities without Ahmedabad (%) | -9.9 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Welch p value of that check across ten seeds | 6.5e-05 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Difference of the decomposition share between the two parts of the test year (points) (lowest) | -3.3 |  | `results/04_followups/reports/shap/g1_shap18_periods_lb7.csv` | derived | lockdown_unlock minus pre_lockdown, per city, 13 cities |
| Difference of the decomposition share between the two parts of the test year (points) (highest) | 5.1 |  | `results/04_followups/reports/shap/g1_shap18_periods_lb7.csv` | derived | lockdown_unlock minus pre_lockdown, per city, 13 cities |
| Median of those differences (points) | 1.1 |  | `results/04_followups/reports/shap/g1_shap18_periods_lb7.csv` | derived |  |
| Cities where past PM2.5 leads in both periods | 13 |  | `results/04_followups/reports/shap/g1_shap18_periods_lb7.csv` | derived | idxmax of the 17 channels is PM2.5 in both rows |

## Results: Attribution to past AQI depends on representation and training

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Span of the decomposition share across the 13 cities at one model seed (points) | 12.1 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | max - min of decomposition_share_pct over the 13 cities |
| Delhi: share to the five decomposition channels | 24.0 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Mumbai: share to the five decomposition channels | 17.7 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Bengaluru: share to the five decomposition channels | 14.5 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Delhi: share to the one raw AQI channel | 53.2 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Mumbai: share to the one raw AQI channel | 41.6 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Bengaluru: share to the one raw AQI channel | 35.5 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Spearman correlation of the pollutant ranking, raw channel against decomposition, each city | 0.972 |  | `results/02_r1_ext/reports/shap/ablation13ch_vs_proposed_pollutant_ranking.csv` | direct | the three values are equal at 0.972 |
| Delhi: PM2.5 history share when PM2.5 is the target | 95.7 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Mumbai: PM2.5 history share when PM2.5 is the target | 94.4 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Bengaluru: PM2.5 history share when PM2.5 is the target | 94.9 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Delhi: IMF1 to IMF4 share when PM2.5 is the target | 31.7 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |
| Mumbai: IMF1 to IMF4 share when PM2.5 is the target | 21.2 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |
| Bengaluru: IMF1 to IMF4 share when PM2.5 is the target | 36.4 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |
| Test R2 of the PM2.5-target model over five seeds (17 cities) (mean) | 0.775 |  | `results/02_r1_ext/reports/multiseed_pm25_lb7.csv` | derived | mean and s.d. of r2 over five seeds |
| Test R2 of the PM2.5-target model over five seeds (17 cities) (s.d.) | 0.010 |  | `results/02_r1_ext/reports/multiseed_pm25_lb7.csv` | derived | mean and s.d. of r2 over five seeds |
| Decomposition share across the 20 models, lowest and highest over the three cities (lowest) | 7.5 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | min of min and max of max over cities |
| Decomposition share across the 20 models, lowest and highest over the three cities (highest) | 34.2 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | min of min and max of max over cities |
| Delhi: decomposition share across 20 models (lowest) | 7.5 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Delhi: decomposition share across 20 models (highest) | 32.1 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Mumbai: decomposition share across 20 models (lowest) | 12.4 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Mumbai: decomposition share across 20 models (highest) | 34.2 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Bengaluru: decomposition share across 20 models (lowest) | 8.5 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Bengaluru: decomposition share across 20 models (highest) | 31.5 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct | rows with period all |
| Delhi: span of the decomposition share across the 20 models (points) | 24.6 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | max - min |
| Ratio of that span to the 12.1-point span across cities (about twice) | 2.0 |  | `results/04_followups/reports/g2_anova_lb7.csv` | derived | 24.6 / 12.1 |
| Model-seed s.d. of the decomposition share (points), three cities (lowest) | 5.9 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | sd_within |
| Model-seed s.d. of the decomposition share (points), three cities (highest) | 7.0 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | sd_within |
| p values of the realisation effect on the decomposition share, three cities (lowest) | 0.50 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | p_value |
| p values of the realisation effect on the decomposition share, three cities (highest) | 0.71 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | p_value |
| City models (of 60) in which past PM2.5 has the highest attribution | 59 |  | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | leading_input == PM2.5, 60 rows |
| Lowest rank correlation of a model's pollutant ranking with the main model, three cities (lowest) | 0.78 |  | `results/04_followups/reports/g2_statements_lb7.json` | direct |  |
| Lowest rank correlation of a model's pollutant ranking with the main model, three cities (highest) | 0.92 |  | `results/04_followups/reports/g2_statements_lb7.json` | direct |  |
| Realisation s.d. that the test detects with 80% probability, in units of the model-seed s.d. | 1.32 |  | `analyses/followups/g2_power.txt` | direct |  |
| Median relative period spread by channel (%), component diagnostic (lowest) | 0.0 |  | `results/02_r1_ext/reports/c5_seed_stability.csv` | derived | median over cities and dates of spread_pct, per channel |
| Median relative period spread by channel (%), component diagnostic (highest) | 6.3 |  | `results/02_r1_ext/reports/c5_seed_stability.csv` | derived | median over cities and dates of spread_pct, per channel |
| Largest difference of component values, % of the history s.d., by channel (lowest) | 10.4 |  | `results/02_r1_ext/reports/c5_seed_stability.csv` | derived | max over cities and dates of max_diff_pct_of_sd, per channel |
| Largest difference of component values, % of the history s.d., by channel (highest) | 29.6 |  | `results/02_r1_ext/reports/c5_seed_stability.csv` | derived | max over cities and dates of max_diff_pct_of_sd, per channel |
| Delhi: decomposition share at a 30-day lookback | 25.3 |  | `results/02_r1_ext/reports/shap/shap_periods_v2_lb30.csv` | direct |  |
| Mumbai: decomposition share at a 30-day lookback | 15.0 |  | `results/02_r1_ext/reports/shap/shap_periods_v2_lb30.csv` | direct |  |
| Bengaluru: decomposition share at a 30-day lookback | 10.7 |  | `results/02_r1_ext/reports/shap/shap_periods_v2_lb30.csv` | direct |  |
| Delhi: decomposition share over three backgrounds (lowest) | 23.1 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Delhi: decomposition share over three backgrounds (highest) | 24.0 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Mumbai: decomposition share over three backgrounds (lowest) | 17.7 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Mumbai: decomposition share over three backgrounds (highest) | 18.7 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Bengaluru: decomposition share over three backgrounds (lowest) | 14.2 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Bengaluru: decomposition share over three backgrounds (highest) | 14.6 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | direct | original, draw1, draw2 |
| Lowest rank correlation of the 17-channel attribution with the original background | 0.977 | tab:background | `results/03_bg_check/bg_check_summary_lb7.csv` | derived | min over cities and the two new backgrounds. The minimum is 0.9779 (Delhi, draw1) |

## Results: Whole-record decomposition inflates timescale attribution

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Test R2, past-only decomposition (XGBoost, three seeds) (mean) | 0.861 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, past-only decomposition (XGBoost, three seeds) (s.d.) | 0.001 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, pollutants only (XGBoost, three seeds) (mean) | 0.858 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, pollutants only (XGBoost, three seeds) (s.d.) | 0.005 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, raw history (XGBoost, three seeds) (mean) | 0.865 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, raw history (XGBoost, three seeds) (s.d.) | 0.003 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, whole-record decomposition (XGBoost, three seeds) (mean) | 0.943 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, whole-record decomposition (XGBoost, three seeds) (s.d.) | 0.003 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| RMSE, past-only decomposition | 42.0 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean over seeds |
| RMSE, whole-record decomposition | 26.9 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean over seeds |
| IMF1 to IMF4 share, past-only decomposition (%) | 3.9 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | pooled-city rows (the rows that carry IMF columns), mean over seeds |
| IMF1 to IMF4 share, whole-record decomposition (%) | 26.4 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived |  |
| Ratio of the two shares | 6.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | whole-record share / past-only share |
| Delhi: IMF1 to IMF4 share, past-only | 4.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Delhi: IMF1 to IMF4 share, whole-record | 33.6 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Mumbai: IMF1 to IMF4 share, past-only | 2.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Mumbai: IMF1 to IMF4 share, whole-record | 21.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Bengaluru: IMF1 to IMF4 share, past-only | 1.9 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Bengaluru: IMF1 to IMF4 share, whole-record | 12.2 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Studies whose pipeline lets data after the forecast origin enter | 42 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'i' |
| Same, as a share of 60 (%) | 70 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Wilson 95% interval, lower (%) | 57 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | Wilson score |
| Wilson 95% interval, upper (%) | 80 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | Wilson score |
| Of these, studies that state the order of decomposition and splitting in words | 3 | tab:s_lit_coding | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'i' and T3_explicit == 'yes' |
| Studies that did not state how the decomposition was applied | 13 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'v' |
| Same, as a share of 60 (%) | 22 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Studies that decomposed only data available at each forecast origin | 3 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'iii' |
| Same, as a share of 60 (%) | 5 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Studies that reported a non-decomposed version of the same model | 40 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T5_nodec_model == 'yes' |
| Studies that reported a persistence forecast | 1 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T6_persistence == 'yes' |
| Studies that applied an explanation method such as SHAP | 0 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T9_explanation != 'none' |
| Wilson 95% interval of that share, upper (%) | 6 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | Wilson score |
| Studies that read modes as physical drivers | 1 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T8_interpretation == 'yes' |

## Results: Modes can receive attribution without passing a skill test

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Forecast origins decomposed for the bulletin analysis | 9,229 |  | `analyses/dataset_check/E7_DECISION_RULES.md` | direct | the count of origins in the decision-rule document |
| Years (of 7) in which adding the modes passes the rule beyond the 365-day memory, 1 day(s) ahead | 0 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | pooled MAE gain > 2 x larger seed s.d. |
| Years (of 7) in which adding the modes passes the rule beyond the 365-day memory, 7 day(s) ahead | 0 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | pooled MAE gain > 2 x larger seed s.d. |
| Years (of 7) in which the modes lower the pooled MAE, 1 day ahead, with the 365-day memory | 5 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | MAE(RAW+MAL) - MAE(RAW+MAL+OSC) > 0 |
| Largest such reduction (AQI units) | 0.40 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived |  |
| Years (of 7) in which the modes raise the pooled MAE, 7 days ahead | 7 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | MAE(RAW+MAL) - MAE(RAW+MAL+OSC) < 0 |
| Years (of 7) passing the rule without the 365-day memory, 1 day(s) ahead | 0 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived |  |
| Years (of 7) passing the rule on gap-free histories without the memory, 1 day(s) ahead | 2 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | hist == clean |
| Years (of 7) passing the rule without the 365-day memory, 7 day(s) ahead | 0 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived |  |
| Years (of 7) passing the rule on gap-free histories without the memory, 7 day(s) ahead | 2 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | hist == clean |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (lowest) | 9.4 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (highest) | 19.1 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Share given to the modes when only the decomposition channels are given (%) (lowest) | 16.7 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | arm DEC |
| Share given to the modes when only the decomposition channels are given (%) (highest) | 33.3 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | arm DEC |
| Spearman rho of per-city gains between the two halves, 1 day ahead | 0.51 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_verdict.txt` | direct |  |
| p value, 1 day ahead | 0.06 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_verdict.txt` | direct |  |
| Spearman rho, 7 days ahead | 0.47 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_verdict.txt` | direct |  |
| p value, 7 days ahead | 0.09 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_verdict.txt` | direct |  |
| Median Pearson r of bulletin against dataset AQI over 26 cities | 0.937 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | derived | median of r |
| Cities with r below 0.8 | 5 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | derived | r < 0.8 |

## Results: Observed weather improves a diagnostic of short-timescale AQI variation

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| H1: MAE lower than the controls (%) | 4.9 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H1: 90% interval (%) (lowest) | 3.6 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H1: 90% interval (%) (highest) | 6.2 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: weather known at the forecast origin, MAE lower (%) | 3.4 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: 90% interval (%) (lowest) | 1.4 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: 90% interval (%) (highest) | 5.3 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: excess attribution share of the short weather bands (points) | 3.5 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: 90% interval (points) (lowest) | 3.3 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: 90% interval (points) (highest) | 3.6 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| All three rules passed | pass, pass, pass | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Forecast-day weather against no weather: MAE lowered by (%) | 4.4 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | 100 x (MAE of BASE - MAE of MET_PP) / MAE of BASE |
| Same-season weather from other years produces no detectable MAE reduction against no weather | True |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | one-sided p of BASE minus POOL_PP is above 0.05 (effect -0.122, p 0.87) |
| Of the gain over no weather, the share in the bands shorter than 31 days (%) | 85.4 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | 100 x (MAE of MET_PP_LONG - MAE of MET_PP) / (MAE of BASE - MAE of MET_PP): the arm MET_PP_LONG keeps only the bands of 31 days and longer, so what it loses against MET_PP is what the short bands supply |
| Share of IMF1 to IMF4 without weather (%) | 3.8 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | arm_means_all, BASE |
| Share of IMF1 to IMF4 with forecast-day weather (%) | 3.3 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | arm_means_all, MET_PP |
| Pre-lockdown effect of weather against the controls (%) | 4.67 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | lockdown_check |
| Variable groups with the largest excess attribution share | met_disp, met_rain |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | real mean minus null mean of the share, groups dispersion, temperature, humidity, rain |
| Cities where the 90% interval of the weather effect lies above zero, forecast-day weather | 17 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | lo > 0 per city |
| Same for weather up to the origin | 15 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | lo > 0 per city |
| Arms fitted | 32 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Threshold for repeating the test with the iTransformer (%) | 13 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Effect compared with the threshold (%) | 4.9 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |

## Discussion

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Fewest components returned on a day | 5 |  | `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/*.npz` | derived | min of n_components |
| Most components returned on a day | 9 |  | `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/*.npz` | derived | max of n_components |
| Test windows with a compressed decomposition history (count) | 2,427 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum over the 18 modelled cities |
| Share of the 6,171 test windows with a compressed history (%) | 39.3 |  | `analyses/e1_verification/outputs/data_audit.csv` | derived | 2,427 / 6,171 |
| Persistence test R2 | 0.790 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Persistence MAE | 23.86 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Cities where the five-seed mean MAE is below persistence | 1 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | count of model_mae_mean < persistence_mae |
| Seasonal climatology test R2 | 0.212 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Every model in Table 1 has a higher R2 than persistence | True | tab:performance | `Table 1 sources` | derived | R2 of each single-run row > 0.790 |
| IMF1 to IMF4 receive less than 5% in every interpreted city | 5 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | largest share over the 13 cities |
| Delhi: span of the decomposition share across the 20 models (points) | 24.6 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | derived | max - min |
| City models (of 60) in which past PM2.5 has the highest attribution | 59 |  | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | leading_input == PM2.5, 60 rows |
| Test R2, past-only decomposition (XGBoost, three seeds) (mean) | 0.861 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, past-only decomposition (XGBoost, three seeds) (s.d.) | 0.001 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, pollutants only (XGBoost, three seeds) (mean) | 0.858 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, pollutants only (XGBoost, three seeds) (s.d.) | 0.005 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, raw history (XGBoost, three seeds) (mean) | 0.865 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, raw history (XGBoost, three seeds) (s.d.) | 0.003 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, whole-record decomposition (XGBoost, three seeds) (mean) | 0.943 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Test R2, whole-record decomposition (XGBoost, three seeds) (s.d.) | 0.003 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived | mean and s.d. over seeds 0 to 2 |
| Ratio of the two shares | 6.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | whole-record share / past-only share |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (lowest) | 9.4 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Share given to IMF1 to IMF4 with the 365-day memory (%) (highest) | 19.1 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | mean over seeds of osc_share, all years and both horizons, hist == long |
| Share given to the modes when only the decomposition channels are given (%) (lowest) | 16.7 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | arm DEC |
| Share given to the modes when only the decomposition channels are given (%) (highest) | 33.3 | tab:s_e7 | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived | arm DEC |
| Cities with r below 0.8 | 5 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | derived | r < 0.8 |
| Studies whose pipeline lets data after the forecast origin enter | 42 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'i' |
| Same, as a share of 60 (%) | 70 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Studies that reported a persistence forecast | 1 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T6_persistence == 'yes' |

## Methods: Calendar windows and missingness

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Windows, training (lookback 7) | 11,569 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of train over the 18 modelled cities |
| Windows, validation (lookback 7) | 1,510 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of validation over the 18 modelled cities |
| Windows, test (lookback 7) | 6,171 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of test over the 18 modelled cities |
| Origins whose availability mask differs when recomputed from the calendar prefix | 0 |  | `analyses/e1_verification/outputs/prefix_audit.json` | derived | sum over train, validation, test |
| Modelled cities with at least 80% of 14-day windows retained | 13 | tab:coverage | `analyses/e1_verification/outputs/data_audit.csv` | derived | eligible14_pct >= 80 |
| Same screen as used for the 13 interpreted cities | 13 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | sum of passes_completeness |
| Minimum available history (observations) | 180 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R11_MIN_HISTORY_DAYS |
| First validation target date | 2019-04-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_VAL_START |
| First test target date | 2019-07-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_TEST_START |
| Last test target date (last day of the data) | 2020-07-01 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R19_DATA_END |
| Date from which the lockdown and Unlock period starts | 2020-03-25 |  | `analyses/baselines/baselines.py` | direct | constant LOCKDOWN |
| Lookbacks | 7, 14, 21, 30 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | LOOKBACK_PERIODS_V2 |

## Methods: Channel-level KernelSHAP

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Background windows per city | 50 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | SHAP_N_BACKGROUND |
| Explained test windows per city | 100 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | SHAP_MAX_TEST |

## Methods: Comparators and reference forecasts

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Plain iTransformer: width 64, four heads, feed-forward 256, two layers | True |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | parameter dictionary of the plain iTransformer |

## Methods: Data and target

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Rows of city_day.csv | 29,531 |  | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum of raw_rows over 26 cities |

## Methods: Forecasting model

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Main model: encoder layers | 6 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | ITRANSFORMER_V2_PARAMS, last assignment in the notebook |
| Main model: attention heads | 8 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | ITRANSFORMER_V2_PARAMS, last assignment in the notebook |
| Main model: width | 256 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | ITRANSFORMER_V2_PARAMS, last assignment in the notebook |
| Main model: feed-forward width | 1,024 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | ITRANSFORMER_V2_PARAMS, last assignment in the notebook |
| Main model: dropout | 0.1 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | ITRANSFORMER_V2_PARAMS, last assignment in the notebook |
| Main model: learning rate | 0.0005 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | LEARNING_RATE_V2, last assignment in the notebook |
| Main model: weight decay | 0.000001 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | WEIGHT_DECAY_V2, last assignment in the notebook |
| Main model: batch size | 32 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | BATCH_SIZE_V2, last assignment in the notebook |
| Main model: warm-up epochs | 10 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | WARMUP_EPOCHS_V2, last assignment in the notebook |
| Main model: maximum epochs | 200 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | EPOCHS_V2, last assignment in the notebook |
| Main model: early-stopping patience | 20 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | PATIENCE_V2, last assignment in the notebook |
| Model seeds | 7, 42, 123, 2024, 2025 |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | constant SEEDS |

## Methods: Implementation

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Colab notebooks: python | 3.13.15 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: numpy | 2.1.3 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: pandas | 2.2.3 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: scipy | 1.16.3 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: scikit-learn | 1.6.1 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: EMD-signal | 1.9.0 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: shap | 0.51.0 |  | `results/04_followups/reports/g_sessions.json` | direct | versions the run recorded |
| Colab notebooks: PyTorch | 2.11.0 |  | `results/04_followups/reports/g_sessions.json` | direct |  |
| Colab notebooks: GPU | Tesla T4 |  | `results/04_followups/reports/g_sessions.json` | direct |  |
| Baseline notebook: tensorflow | 2.20.0 |  | `notebooks/01_phase1_baselines_r1.ipynb` | direct | version printed in the output of the import cell |
| Baseline notebook: xgboost | 3.4.1 |  | `notebooks/01_phase1_baselines_r1.ipynb` | direct | version printed in the output of the import cell |
| Weather diagnostic: python | 3.13.0 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | provenance of the run |
| Weather diagnostic: xgboost | 3.2.0 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | provenance of the run |
| Weather diagnostic: numpy | 2.4.2 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | provenance of the run |
| Weather diagnostic: pandas | 3.0.1 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | provenance of the run |
| Weather diagnostic: scipy | 1.17.1 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | provenance of the run |
| Laptop analyses: scikit-learn | 1.8.0 |  | `requirements/analyses_local_cpu.txt` | direct | the pinned file of that environment |
| Laptop analyses: EMD-signal | 1.9.0 |  | `requirements/analyses_local_cpu.txt` | direct | the pinned file of that environment |
| Laptop analyses: matplotlib | 3.10.8 |  | `requirements/analyses_local_cpu.txt` | direct | the pinned file of that environment |

## Methods: Leakage contrast

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Seeds of the leakage contrast | 0, 1, 2 |  | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv` | derived |  |

## Methods: Literature sample

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Records identified, OpenAlex | 371 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Records identified, Scopus | 520 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Records identified, total | 891 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Duplicates removed | 333 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Unique records screened | 558 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived | rows |
| Excluded on title and abstract | 169 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Eligible after screening | 389 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Eligible with an open-access copy | 161 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_order.csv` | derived | rows |
| Records reached in the random order | 70 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | rows |
| Studies coded | 60 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | status == 'CODED' |
| Not coded because the open copy did not open | 6 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Not coded because the full text failed eligibility | 4 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Seed of the random order of the 161 studies | 20261013 |  | `analyses/literature_count/lc_sample.py` | direct | default_rng seed |

## Methods: Official bulletin analysis

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Origins used: every n-th origin | 5 |  | `analyses/dataset_check/e7_common.py` | direct | constant ORIGIN_STEP |
| Cities in the bulletin analysis | 14 |  | `analyses/x1_shap_recheck/outputs/e7_d2_city.csv` | derived | distinct cities |
| Their names | Amaravati, Amritsar, Bengaluru, Chennai, Delhi, Gurugram, Hyderabad, Jaipur, Kolkata, Lucknow, Mumbai, Patna, Thiruvananthapuram, Visakhapatnam |  | `analyses/x1_shap_recheck/outputs/e7_d2_city.csv` | derived |  |
| Yearly folds | 2019 to 2025 |  | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived |  |
| Seeds | 0, 1, 2 |  | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | derived |  |

## Methods: Past-only decomposition

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Retained forecast origins (training + validation + test) | 19,250 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | 11,569 + 1,510 + 6,171 |
| Decomposed city-days | 20,070 |  | `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/*.npz` | derived | sum of len(days) over 18 files |
| Fewest components returned on a day | 5 |  | `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/*.npz` | derived | min of n_components |
| Most components returned on a day | 9 |  | `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/*.npz` | derived | max of n_components |
| Boundary error of IMF1 to IMF4 on training dates, reduction by the autoregressive extension (%) | 18 |  | `analyses/e1_verification/outputs/i14_boundary_error.csv` | derived | 100 x (1 - mean error with the extension / mean error without), mean over IMF1 to IMF4, 3 cities x 20 dates. Produced by e1_verification/i14_boundary_error.py |
| Rule for adopting the extension: boundary-error reduction of at least (%) | 10 |  | `analyses/e1_verification/outputs/i14_boundary_error.csv` | derived | the reduction exceeds the 10% threshold fixed before the run |
| Longest decomposition history (available days) | 365 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| Largest autoregressive order tried | 14 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| Autoregressive extension length (values) | 30 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| CEEMDAN trials | 100 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| CEEMDAN noise amplitude | 0.2 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| CEEMDAN maximum number of modes | 8 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| CEEMDAN seed (plus the city position in the alphabetical list of 26) | 123 |  | `analyses/tools/c5_helper_cell.py` | direct | constant in the helper cell that the notebooks execute |
| Minimum available history (observations) | 180 |  | `analyses/tools/r19_helper_cell.py` | direct | constant R11_MIN_HISTORY_DAYS |
| Extension used for the main results | ar |  | `notebooks/02_ceemdan_itransformer_shap_r1_ext.ipynb` | direct | constant C5_MAIN_EXTENSION |

## Methods: Weather diagnostic

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Arms fitted | 32 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Seeds per arm | 40 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Fits in total | 1,280 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Marker that the run was reproduced byte for byte: pooled results of the three runs are identical | True |  | `analyses/e1_verification/outputs/c2_runs/{T6,T7,S1_wsl_i5}/c2x_pooled.csv` | derived | SHA-256 of the three files is identical |
| Null sets | 10 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | K of H1 |
| Band edges of the four weather bands (days) | 7, 31, 91 |  | `analyses/e1_verification/e5_driver_band_precheck.py` | direct | trailing means over 7, 31 and 91 days |

## Fig. 3a

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Delhi: share to the five decomposition channels | 24.0 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Mumbai: share to the five decomposition channels | 17.7 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Bengaluru: share to the five decomposition channels | 14.5 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| Delhi: share to the one raw AQI channel | 53.2 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Mumbai: share to the one raw AQI channel | 41.6 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Bengaluru: share to the one raw AQI channel | 35.5 |  | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv` | direct | non_pollutant_share_pct of the all-windows row |
| Delhi: PM2.5 history share when PM2.5 is the target | 95.7 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Mumbai: PM2.5 history share when PM2.5 is the target | 94.4 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Bengaluru: PM2.5 history share when PM2.5 is the target | 94.9 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_vs_aqi_lb7.csv` | direct |  |
| Delhi: IMF1 to IMF4 share when PM2.5 is the target | 31.7 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |
| Mumbai: IMF1 to IMF4 share when PM2.5 is the target | 21.2 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |
| Bengaluru: IMF1 to IMF4 share when PM2.5 is the target | 36.4 |  | `results/02_r1_ext/reports/shap/shap_v2_pm25_attribution_lb7.csv` | derived | sum of IMF1..IMF4 over the sum of all channels |

## Fig. 4a

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Delhi: IMF1 to IMF4 share, past-only | 4.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Delhi: IMF1 to IMF4 share, whole-record | 33.6 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Mumbai: IMF1 to IMF4 share, past-only | 2.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Mumbai: IMF1 to IMF4 share, whole-record | 21.8 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Bengaluru: IMF1 to IMF4 share, past-only | 1.9 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |
| Bengaluru: IMF1 to IMF4 share, whole-record | 12.2 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds of osc_share |

## Results 3

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Same screen as used for the 13 interpreted cities | 13 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | sum of passes_completeness |

## Results: Decomposition adds no accuracy

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| City-level test R2, lowest (Thiruvananthapuram) | 0.082 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| City-level test R2, highest (Delhi) | 0.917 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| City-level test R2, median over 18 cities | 0.634 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | median of test_r2 |
| Cities with test R2 below 0.5 | Amaravati, Bengaluru, Chennai, Thiruvananthapuram | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | test_r2 < 0.5 |
| Pooled standard deviation of observed AQI, pre-lockdown | 125.8 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | derived | RMSE / sqrt(1 - R2) of the persistence row (the evaluated subset's own s.d.) |
| Pooled standard deviation of observed AQI, lockdown/Unlock | 39.7 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | derived | RMSE / sqrt(1 - R2) of the persistence row (the evaluated subset's own s.d.) |
| Augmented model R2 after 25 March 2020, five seeds (mean) | -0.151 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Augmented model R2 after 25 March 2020, five seeds (s.d.) | 0.259 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |

## Supplementary Note S1

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Test windows whose final input day uses a short-gap-filled AQI value | 59 |  | `analyses/e1_verification/outputs/prefix_audit.json` | direct |  |
| Test windows with a compressed decomposition history (count) | 2,427 | tab:windows | `analyses/e1_verification/outputs/data_audit.csv` | derived | sum over the 18 modelled cities |
| Share of the 6,171 test windows with a compressed history (%) | 39.3 |  | `analyses/e1_verification/outputs/data_audit.csv` | derived | 2,427 / 6,171 |
| Longest decomposition history in calendar days | 532 |  | `analyses/e1_verification/outputs/data_audit.csv` | direct | max of max_test_history_span |
| Modelled cities with at least 80% of 14-day windows retained | 13 | tab:coverage | `analyses/e1_verification/outputs/data_audit.csv` | derived | eligible14_pct >= 80 |
| Cities that fail the screen | Ahmedabad, Brajrajnagar, Jorapokhar, Talcher, Visakhapatnam |  | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | passes_completeness is False |

## Supplementary Note S2

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| SHA-256 of city_day.csv after converting line endings to LF | 0d84b21c3e4878bbad8df362f2ab05f61ad959538dddf5918e714077ed3c1847 |  | `data/city_day.csv` | derived | hashlib.sha256 over the LF-converted bytes |
| Ahmedabad days with CO equal to NO, 1 January 2015 to 9 April 2020 | 1,317 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Change in the MAE of the other 17 cities without Ahmedabad (%) | -9.9 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Welch p value of that check across ten seeds | 6.5e-05 |  | `analyses/dataset_check/outputs/ahmedabad_co_no.txt` | direct |  |
| Median Pearson r of bulletin against dataset AQI over 26 cities | 0.937 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | derived | median of r |
| Cities with r below 0.8 | 5 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | derived | r < 0.8 |
| Lowest r (Ahmedabad) | 0.540 |  | `analyses/dataset_check/outputs/e7_d0_comparability.csv` | direct |  |

## Supplementary Note S3

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Climatology forecasts that fall back to the city training mean | 138 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | sum of clim_fallback |
| Cities with such fallbacks | 5 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | count of clim_fallback > 0 |
| Origins that are short-gap fills (persistence copies the value) | 59 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | sum of origin_filled |

## Supplementary Note S5

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Records identified, OpenAlex | 371 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Records identified, Scopus | 520 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Records identified, total | 891 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Duplicates removed | 333 | tab:s_lit_summary | `analyses/literature_count/outputs/flow_counts.json` | direct |  |
| Unique records screened | 558 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived | rows |
| Excluded on title and abstract | 169 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Eligible after screening | 389 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Eligible with an open-access copy | 161 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_order.csv` | derived | rows |
| Records reached in the random order | 70 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | rows |
| Studies coded | 60 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | status == 'CODED' |
| Not coded because the open copy did not open | 6 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Not coded because the full text failed eligibility | 4 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Excluded on title and abstract, reason TOPIC | 86 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason NONEN | 32 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason NOFC | 22 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason DESC | 17 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason NODEC | 8 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason DUP | 3 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Excluded on title and abstract, reason REV | 1 | tab:s_lit_summary | `analyses/literature_count/outputs/screening_decisions.csv` | derived |  |
| Leakage-prone studies published 2015 to 2020 | 9 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived | T3_timing == 'i', year from coding_order.csv |
| Studies published 2015 to 2020 | 13 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Leakage-prone studies published 2021 to 2025 | 33 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Studies published 2021 to 2025 | 47 | tab:s_lit_summary | `analyses/literature_count/outputs/coding_sheet.csv` | derived |  |
| Half-width of the Wilson 95% interval for 60 studies at a share of 50% (percentage points) | 12 |  | `analyses/literature_count/outputs/coding_sheet.csv` | derived | widest interval for n = 60 |

## Supplementary Note S6

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Cities of the first-round eight-city subset (tag D4, step 2) | Bengaluru, Delhi, Gurugram, Jaipur, Kolkata, Lucknow, Mumbai, Patna | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | d4_attribution_set is True |
| All eight pass the completeness screen, so they are a subset of the 13 | True | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | passes_completeness over those eight |
| Delhi: median change of the share between two model seeds on one decomposition | 4.2 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | median of |difference| over the 10 model-seed pairs of each of the 4 decompositions |
| Delhi: largest such change | 24.6 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | max of the same differences |
| Mumbai: median change of the share between two model seeds on one decomposition | 5.9 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | median of |difference| over the 10 model-seed pairs of each of the 4 decompositions |
| Mumbai: largest such change | 21.1 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | max of the same differences |
| Bengaluru: median change of the share between two model seeds on one decomposition | 4.4 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | median of |difference| over the 10 model-seed pairs of each of the 4 decompositions |
| Bengaluru: largest such change | 23.0 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | derived | max of the same differences |
| Delhi: share with seed base 123 at model seed 123 | 24.0 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Delhi: share with seed base 42 at model seed 123 | 32.1 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Mumbai: share with seed base 123 at model seed 123 | 17.7 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Mumbai: share with seed base 42 at model seed 123 | 26.9 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Bengaluru: share with seed base 123 at model seed 123 | 14.5 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Bengaluru: share with seed base 42 at model seed 123 | 19.4 | tab:s_g2 | `results/04_followups/reports/shap/g2_shap_lb7.csv` | direct |  |
| Talcher: attribution of PM2.5 divided by that of PM10 | 1.09 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_matrix_lb7.csv` | derived | ratio of the two columns |
| Jorapokhar: attribution of PM2.5 divided by that of PM10 | 1.14 | tab:s_g1 | `results/04_followups/reports/shap/g1_shap18_matrix_lb7.csv` | derived | ratio of the two columns |

## Supplementary Note S7

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Slow channel share, past-only arm (%) | 49.2 | tab:s_e1 | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | derived | mean over seeds |
| Their names | Amaravati, Amritsar, Bengaluru, Chennai, Delhi, Gurugram, Hyderabad, Jaipur, Kolkata, Lucknow, Mumbai, Patna, Thiruvananthapuram, Visakhapatnam |  | `analyses/x1_shap_recheck/outputs/e7_d2_city.csv` | derived |  |

## Supplementary Note S8

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| H1: MAE lower than the controls (%) | 4.9 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H1: 90% interval (%) (lowest) | 3.6 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H1: 90% interval (%) (highest) | 6.2 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: weather known at the forecast origin, MAE lower (%) | 3.4 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: 90% interval (%) (lowest) | 1.4 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| P H1: 90% interval (%) (highest) | 5.3 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: excess attribution share of the short weather bands (points) | 3.5 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: 90% interval (points) (lowest) | 3.3 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| H2: 90% interval (points) (highest) | 3.6 | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| All three rules passed | pass, pass, pass | tab:s_c2 | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Forecast-day weather against no weather: MAE lowered by (%) | 4.4 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | 100 x (MAE of BASE - MAE of MET_PP) / MAE of BASE |
| Same-season weather from other years produces no detectable MAE reduction against no weather | True |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | one-sided p of BASE minus POOL_PP is above 0.05 (effect -0.122, p 0.87) |
| Of the gain over no weather, the share in the bands shorter than 31 days (%) | 85.4 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | 100 x (MAE of MET_PP_LONG - MAE of MET_PP) / (MAE of BASE - MAE of MET_PP): the arm MET_PP_LONG keeps only the bands of 31 days and longer, so what it loses against MET_PP is what the short bands supply |
| Share of IMF1 to IMF4 without weather (%) | 3.8 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | arm_means_all, BASE |
| Share of IMF1 to IMF4 with forecast-day weather (%) | 3.3 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | arm_means_all, MET_PP |
| Pre-lockdown effect of weather against the controls (%) | 4.67 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct | lockdown_check |
| Variable groups with the largest excess attribution share | met_disp, met_rain |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | real mean minus null mean of the share, groups dispersion, temperature, humidity, rain |
| Cities where the 90% interval of the weather effect lies above zero, forecast-day weather | 17 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | lo > 0 per city |
| Same for weather up to the origin | 15 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | derived | lo > 0 per city |
| Fits in total | 1,280 |  | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | direct |  |
| Cities with a significant weekly cycle in NO2 (q < 0.05) | 10 |  | `analyses/e1_verification/outputs/e4_weekly_cycle.csv` | derived | q < 0.05 among the 18 cities |
| Cities with a significant weekly cycle in AQI | 0 |  | `analyses/e1_verification/outputs/e4_weekly_cycle.csv` | derived |  |
| Permutations of the weekly-cycle test | 2,000 |  | `analyses/e1_verification/e4_weekly_cycle.py` | direct | size of the surrogate array |
| SHA-256 of C2_PREREGISTRATION.md (published file, LF line endings) | c3b38c294ba09b1f872e414d48e40623adb1f9d1382473099c2cc78494debd50 |  | `analyses/e1_verification/C2_PREREGISTRATION.md` | derived | hashlib.sha256 over the published file; also in C2_FREEZE_SHA256.txt and the verdict file |
| SHA-256 of C2_PREREGISTRATION_ADDENDUM_A1.md (published file, LF line endings) | c2d32acd5cbe91dede7cd460ee0ceee2deb029755f0d58964e8d39915e134ed7 |  | `analyses/e1_verification/C2_PREREGISTRATION_ADDENDUM_A1.md` | derived | hashlib.sha256 over the published file; also in C2_FREEZE_SHA256.txt and the verdict file |
| SHA-256 of C2_PREREGISTRATION_ADDENDUM_A2.md (published file, LF line endings) | 0f3e15ce2d78ed9dedf2c436f417c4c80e9a81c9e14de38a30c9a2854151348c |  | `analyses/e1_verification/C2_PREREGISTRATION_ADDENDUM_A2.md` | derived | hashlib.sha256 over the published file; also in C2_FREEZE_SHA256.txt and the verdict file |

## Supplementary Note S9

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Test R2 without the boundary extension (mean) | 0.791 | tab:gaps | `results/02_r1/reports/multiseed_summary_lb7.csv` | direct | results/02_r1 is the run without the extension |
| Test R2 without the boundary extension (s.d.) | 0.024 | tab:gaps | `results/02_r1/reports/multiseed_summary_lb7.csv` | direct | results/02_r1 is the run without the extension |
| Mean validation R2 without the boundary extension | 0.787 |  | `results/02_r1/reports/r116_conditioning_runs_lb7.csv` | derived | mean over five seeds |
| Mean validation R2 with the boundary extension | 0.789 |  | `results/02_r1_ext/reports/r116_conditioning_runs_lb7.csv` | derived | mean over five seeds |
| Test R2 of windows without filled AQI input days | 0.840 | tab:gaps | `results/02_r1_ext/reports/r33_s1_filled_lb7.csv` | direct |  |
| Test R2 of windows with filled AQI input days | 0.767 | tab:gaps | `results/02_r1_ext/reports/r33_s1_filled_lb7.csv` | direct |  |
| Windows with filled AQI input days | 343 | tab:gaps | `results/02_r1_ext/reports/r33_s1_filled_lb7.csv` | direct |  |
| Test R2 of windows without filled days, cities with both kinds | 0.812 | tab:gaps | `results/02_r1_ext/reports/r33_s1_filled_lb7.csv` | direct |  |
| Windows without filled days, cities with both kinds | 2,525 | tab:gaps | `results/02_r1_ext/reports/r33_s1_filled_lb7.csv` | direct |  |

## Table 1

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| Augmented model, seed 123, test R2 | 0.833 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| Augmented model, seed 123, RMSE | 46.06 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| Augmented model, seed 123, MAE | 27.98 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| XGBoost test R2 | 0.855 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Keras LSTM test R2 | 0.844 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| PyTorch LSTM test R2 | 0.840 | tab:performance | `results/02_r1_ext/reports/comparison_v2_full.csv` | direct |  |
| DLinear test R2 | 0.833 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Five-seed test R2, augmented model (mean) | 0.821 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, augmented model (s.d.) | 0.014 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, plain iTransformer (mean) | 0.819 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, plain iTransformer (s.d.) | 0.017 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, raw-history ablation (mean) | 0.821 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed test R2, raw-history ablation (s.d.) | 0.034 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Test R2 over four CEEMDAN realisations x five model seeds (20 models), mean | 0.821 | tab:s_g2 | `results/04_followups/reports/g2_models_lb7.csv` | derived | mean over the 20 models |
| Same, the number after the plus-minus sign: the within-realisation (model-seed) s.d. | 0.017 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct | sd_within of the pooled test_r2 row. The s.d. over all 20 models is 0.016 (sd_all) |
| F test of the realisation effect on test R2, F(3,16) | 0.24 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct |  |
| p value of that test | 0.866 | tab:s_g2 | `results/04_followups/reports/g2_anova_lb7.csv` | direct |  |
| Persistence test R2 | 0.790 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Persistence MAE | 23.86 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| RMSE skill of the augmented model against persistence (mean) | 0.078 |  | `analyses/baselines/outputs/baselines_pooled.csv` | derived | 1 - RMSE(model seed) / RMSE(persistence), over the five seeds. The skill file lists MAE skill only |
| RMSE skill of the augmented model against persistence (s.d.) | 0.036 |  | `analyses/baselines/outputs/baselines_pooled.csv` | derived | 1 - RMSE(model seed) / RMSE(persistence), over the five seeds. The skill file lists MAE skill only |
| Five-seed MAE of the augmented model (mean) | 28.71 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Five-seed MAE of the augmented model (s.d.) | 2.62 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE skill against persistence over five seeds (mean) | -0.203 |  | `analyses/baselines/outputs/baselines_skill.csv` | derived | mean and s.d. of skill over the five seeds |
| MAE skill against persistence over five seeds (s.d.) | 0.110 |  | `analyses/baselines/outputs/baselines_skill.csv` | derived | mean and s.d. of skill over the five seeds |
| Cities where the five-seed mean MAE is below persistence | 1 | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived | count of model_mae_mean < persistence_mae |
| That city | Delhi | tab:s_baselines_city | `analyses/baselines/outputs/baselines_city.csv` | derived |  |
| MAE skill before 25 March 2020 (mean) | -0.048 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | subset pre-lockdown |
| MAE skill before 25 March 2020 (s.d.) | 0.076 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | subset pre-lockdown |
| MAE skill before 25 March 2020, over seeds (lowest) | -0.121 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | min and max over seeds |
| MAE skill before 25 March 2020, over seeds (highest) | 0.067 | tab:periodperformance | `analyses/baselines/outputs/baselines_skill.csv` | derived | min and max over seeds |
| MAE after 25 March 2020 (augmented model, five seeds) (mean) | 27.32 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE after 25 March 2020 (augmented model, five seeds) (s.d.) | 4.07 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| MAE after 25 March 2020 (persistence) | 12.98 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| Seasonal climatology test R2 | 0.212 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | direct |  |
| XGBoost MAE (the only model with a lower MAE than persistence) | 23.24 | tab:performance | `results/01_baselines/phase1_colab_comparison_metrics.csv` | direct |  |
| Every model in Table 1 has a higher R2 than persistence | True | tab:performance | `Table 1 sources` | derived | R2 of each single-run row > 0.790 |
| Only XGBoost has a lower MAE than persistence | XGBoost | tab:performance | `Table 1 sources` | derived | single-run rows with MAE < 23.86 |
| Validation R2 at lookback 7 | 0.8036 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 14 | 0.7794 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 21 | 0.7716 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |
| Validation R2 at lookback 30 | 0.7817 | tab:lookback | `results/02_r1_ext/reports/r113_lookback_selection.json` | direct |  |

## tab:cityaccuracy

| Claim | Printed | SI table | File | Kind | Derivation |
|---|---|---|---|---|---|
| City-level test R2, lowest (Thiruvananthapuram) | 0.082 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| City-level test R2, highest (Delhi) | 0.917 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | direct |  |
| City-level test R2, median over 18 cities | 0.634 | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | median of test_r2 |
| Cities with test R2 below 0.5 | Amaravati, Bengaluru, Chennai, Thiruvananthapuram | tab:cityaccuracy | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | derived | test_r2 < 0.5 |
| Pooled standard deviation of observed AQI, pre-lockdown | 125.8 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | derived | RMSE / sqrt(1 - R2) of the persistence row (the evaluated subset's own s.d.) |
| Pooled standard deviation of observed AQI, lockdown/Unlock | 39.7 | tab:performance | `analyses/baselines/outputs/baselines_pooled.csv` | derived | RMSE / sqrt(1 - R2) of the persistence row (the evaluated subset's own s.d.) |
| Augmented model R2 after 25 March 2020, five seeds (mean) | -0.151 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |
| Augmented model R2 after 25 March 2020, five seeds (s.d.) | 0.259 | tab:performance | `results/02_r1_ext/reports/multiseed_summary_lb7.csv` | direct |  |

## Figures and tables

| Item | Content | Result files | Script |
|---|---|---|---|
| Fig. 1 | Design schematic | `no data` | `analyses/manuscript/scripts/make_figures.py` |
| Fig. 2 | Attribution in the 13 interpreted cities | `results/04_followups/reports/shap/g1_shap18_matrix_lb7.csv, g1_shap18_summary_lb7.csv` | `make_figures.py` |
| Fig. 3a | Raw-history ablation and PM2.5 target | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv, shap_v2_pm25_attribution_lb7.csv` | `make_figures.py` |
| Fig. 3b | Four realisations x five model seeds | `results/04_followups/reports/shap/g2_shap_lb7.csv` | `make_figures.py` |
| Fig. 4a | Leakage contrast | `analyses/x1_shap_recheck/outputs/e1_shares.csv` | `make_figures.py` |
| Fig. 4b, 4c | Official bulletins | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | `make_figures.py` |
| Fig. S1 | All 18 cities, clustered | `results/04_followups/reports/shap/g1_shap18_matrix_lb7.csv` | `make_figures.py` |
| Table 1 (tab:performance) | Forecast accuracy | `analyses/baselines/outputs/baselines_pooled.csv, results/01_baselines/phase1_colab_comparison_metrics.csv, results/02_r1_ext/reports/comparison_v2_full.csv, multiseed_summary_lb7.csv` | `make_tables.py` |
| Table 2 (tab:conditioning) | City conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` | `make_tables.py` |
| tab:s_baselines_city | Persistence and climatology by city | `analyses/baselines/outputs/baselines_city.csv` | `make_tables.py` |
| tab:s_g1 | Attribution, all 18 cities | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` | `make_tables.py` |
| tab:s_g2 | Decomposition realisations | `results/04_followups/reports/g2_anova_lb7.csv` | `make_tables.py` |
| tab:s_e1 | Leakage contrast | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv, e1_shares.csv` | `make_tables.py` |
| tab:s_e7 | Official bulletins | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` | `make_tables.py` |
| tab:s_c2 | Weather diagnostic rules and results | `analyses/e1_verification/outputs/c2_runs/T6/c2x_verdict.json` | `make_tables.py` |
| tab:s_lit_summary, tab:s_lit_coding | Literature sample | `analyses/literature_count/outputs/coding_sheet.csv, coding_order.csv` | `make_tables.py` |
| tab:windows, tab:coverage, tab:missing0, tab:missing1 | Windows, coverage, missingness | `analyses/e1_verification/outputs/data_audit.csv, pollutant_missing.csv` | `rebuild_si_tables.py` |
| tab:cityaccuracy, tab:cityperiods, tab:periodperformance | City accuracy and periods | `results/02_r1_ext/reports/r110_main_city_periods_lb7.csv, comparison_v2_full.csv` | `rebuild_si_tables.py` |
| tab:periods0, tab:periods1 | Scale diagnostics by channel | `results/02_r1_ext/reports/table8_channel_periods.csv` | `rebuild_si_tables.py` |
| tab:lookback | Lookback selection | `results/02_r1_ext/reports/r113_lookback_selection.json` | `rebuild_si_tables.py` |
| tab:background | Attribution backgrounds | `results/03_bg_check/bg_check_summary_lb7.csv` | `rebuild_si_tables.py` |
| tab:gaps | Window constructions | `results/02_r1_ext/reports/s2_summary_lb7.csv, r33_s1_filled_lb7.csv` | `rebuild_si_tables.py` |

## Not recomputed

- Run times (about 18 CPU-hours for a full decomposition run, about 14 minutes of channel-level SHAP per city on the T4 GPU) are estimates from the runs and are not stored in a result file.
- Citations, licences, download and search dates, the CPCB breakpoints of the AQI definition and the text of the pre-registration are quoted from their sources. The pre-registration is published unchanged and its digest is checked above.
- The number of input channels (12 pollutants and 5 decomposition channels) and the window rules are definitions in the code, listed in the Methods and implemented in `analyses/tools/`.

