# Interpretable AQI forecasting with causal CEEMDAN, iTransformer and KernelSHAP (Revision 1)

<!-- TODO before release: the revised manuscript title. -->
Supporting implementation for the revised manuscript. The framework decomposes each city's daily Air Quality Index
(AQI) history into temporal channels with a **causal CEEMDAN** (each day decomposed from past data only), forecasts
next-day AQI with one city-conditioned **iTransformer** over 17 inputs (12 pollutant concentrations and 5
decomposition channels), and attributes each forecast across pollutants and decomposition channels with
**KernelSHAP**. It is evaluated on daily CPCB data from 18 Indian cities with a common calendar split.

The notebooks contain all code and all printed outputs of the runs that produced the revised results. The
`results/` folder holds every file those runs wrote, apart from trained models.

## Repository layout

```
.
├── notebooks/
│   ├── 01_phase1_baselines_r1.ipynb                # DLinear, NLinear, XGBoost, Keras LSTM
│   ├── 02_ceemdan_itransformer_shap_r1.ipynb       # full pipeline without the boundary extension (sensitivity) + diagnostics
│   ├── 02_ceemdan_itransformer_shap_r1_ext.ipynb   # full pipeline with the boundary extension (main results)
│   └── 03_shap_background_check_r1_ext.ipynb       # SHAP background-sample check on the main results
├── data/
│   └── city_day.csv                                # CPCB dataset (see "Data")
├── results/
│   ├── 01_baselines/                               # files written by notebook 01
│   ├── 02_r1/                                      # reports/ and plots/ of notebook 02 _r1
│   ├── 02_r1_ext/                                  # reports/ and plots/ of notebook 02 _r1_ext (main results)
│   ├── 03_bg_check/                                # files written by notebook 03
│   └── models/                                     # trained models are not included (see README there)
├── requirements.txt
└── README.md
```

## How to run

The notebooks are written for **Google Colab** with a GPU (a T4 is enough) and Google Drive.

1. Copy `data/city_day.csv` to `MyDrive/city_day.csv` in Google Drive.
2. Run the notebooks in this order, each with Runtime, Run all:
   1. `01_phase1_baselines_r1`: one session.
   2. `02_ceemdan_itransformer_shap_r1`: writes to `MyDrive/phase4_v2_results_r1`. Several sessions: every
      decomposition (per city), training and SHAP city is saved and reused, so after a disconnect Run all continues
      where it stopped.
   3. `02_ceemdan_itransformer_shap_r1_ext`: writes to `MyDrive/phase4_v2_results_r1_ext`. It copies the
      boundary-extended decompositions that Section 19 of notebook 02 _r1 saved, and the saved trainings that never
      use the decomposition (plain iTransformer, plain LSTM, 13-channel ablation), and checks both on loading.
      Without notebook 02 _r1's folder it computes and trains them itself (equal up to floating-point differences).
   4. `03_shap_background_check_r1_ext`: reads notebook 02 _r1_ext's folder and writes only to
      `reports/shap/bg_check/` in it.
3. Notebook 01 writes its two result files to the Colab session. Download them at the end.

Compute: each full decomposition of the 18 cities takes about 18 CPU-hours (parallel over the available cores).
Notebook 02 computes up to four of them (AQI, PM2.5 target, observed days only, second seed). KernelSHAP takes about
14 minutes per city at lookback 7 on a T4.

**Comments in the notebooks.** Code comments, docstrings and markdown were edited for this repository (internal
document references removed, descriptions updated to the revised pipeline). Code and outputs are exactly as run.
Notebook 02 _r1's header explains how its Sections 18 and 19 were run. The decision tags in comments and printed
output are explained below.

## Pipeline (Revision 1)

- **Data and windows.** Each city's series is placed on a continuous daily calendar. Input gaps of at most 3 days
  are filled from the last observed day, pollutant gaps from the city's own past readings only (no backward fill,
  nothing from other cities), and targets are never filled. A window is kept only if its last input day has at least
  180 available days of history.
- **Split.** One calendar for all cities, by target date: training before 1 Apr 2019, validation 1 Apr to 30 Jun
  2019, test 1 Jul 2019 to 1 Jul 2020. Every accuracy is also reported for pre-lockdown and lockdown/Unlock targets
  (from 25 Mar 2020). 18 cities have training windows under these rules.
- **Causal decomposition.** For every available day t, CEEMDAN (100 trials, noise amplitude 0.2, at most 8 modes)
  decomposes the city's AQI over the previous min(365, available) days up to t. Nothing after t is used. Channels:
  IMF1 to IMF4 in sifting order and one slow channel (IMF5 onwards plus the residue), so the five channels add up to
  the AQI history on every day.
- **Boundary extension (main results).** A window reads the most recent values of a decomposition, where CEEMDAN is
  least reliable (end effect). In the main pipeline each history is extended by 30 days with an autoregressive model
  fitted on the history alone (order up to 14, chosen by AIC), decomposed, and cut back. The extension lowered the
  boundary error of IMF1 to IMF4 by 18% on training dates and was adopted under a rule fixed in advance on validation
  accuracy. Notebook 02 _r1 holds the pipeline without the extension as a sensitivity analysis.
- **Model.** An inverted Transformer (one token per input channel) with one learned bias per city. The main lookback
  is chosen by validation R² only (7 days in both pipelines), and the city conditioning under a validation rule fixed
  in advance. The network settings (`d_model` 256, `ff_dim` 1024, 6 layers, 8 heads, dropout 0.1, at most 200 epochs,
  patience 20, set in one cell of notebook 02 before training) were carried over unchanged from the original
  configuration of the study and were not re-tuned on the revised split. The same settings are used for every seed,
  lookback and both decomposition pipelines.
- **Attribution.** KernelSHAP with one value per channel (all lookback days of a channel replaced together), 100 test
  windows and 50 background windows per city, seeded per city.

## Main results (notebook 02 _r1_ext, lookback 7, test year)

Model comparison (single runs, seed 123):

| Model | R² | RMSE | MAE |
|---|---|---|---|
| XGBoost (notebook 01) | 0.855 | 42.92 | 23.24 |
| LSTM (notebook 02, Section 7c) | 0.840 | 44.99 | 27.65 |
| CEEMDAN+iTransformer (proposed) | 0.833 | 46.06 | 27.98 |
| DLinear (notebook 01) | 0.833 | 46.07 | 25.91 |
| iTransformer (plain) | 0.829 | 46.51 | 27.43 |
| NLinear (notebook 01) | 0.828 | 46.65 | 26.41 |
| CEEMDAN+LSTM | 0.824 | 47.29 | 26.96 |

Five model seeds, mean ± s.d.: proposed 0.821 ± 0.014, plain iTransformer 0.819 ± 0.017, 13-channel ablation (lagged
AQI instead of the decomposition) 0.821 ± 0.034. The decomposition adds no accuracy over these baselines. Without the
boundary extension (notebook 02 _r1) the proposed model gives 0.791 ± 0.024 on test, with unchanged validation
accuracy (0.787 against 0.789 with the extension, over five seeds).

Attribution (eight cities): the decomposition channels take 14.5% to 26.6% of the mean absolute SHAP value, most of
it on the slow channel. IMF1 to IMF4 take 1.40% to 4.81%. Past PM2.5 is the top input in every city.

Background sample (notebook 03, Delhi, Mumbai and Bengaluru): with two new background samples of 50 training windows
each, none shared with the original sample, the decomposition share stays within 23.1% to 24.0% (Delhi), 17.7% to
18.7% (Mumbai) and 14.2% to 14.6% (Bengaluru), the ranking of the 17 channels agrees with the original sample
(Spearman ρ at least 0.978), and past PM2.5 stays the top input.

Decomposition seed (notebook 02 _r1_ext, Section 17): the proposed model retrained on a second CEEMDAN seed gives test
R² 0.845 (0.833 with the main seed, model seed 123 in both). In Delhi, Mumbai and Bengaluru the pollutant ranking is
almost unchanged (Spearman ρ 0.958 to 0.993) and past PM2.5 stays the top input, but the decomposition share is higher
(32.1%, 26.9%, 19.4% against 24.0%, 17.7%, 14.5%), mostly on the slow channel. The size of the decomposition share
therefore depends on the CEEMDAN realisation.

## Results folders

- `results/01_baselines/`: `phase1_colab_comparison_metrics.csv`, `phase1_colab_comparison_summary.json`.
- `results/02_r1/` and `results/02_r1_ext/`: the `reports/` folder (CSV and JSON results, `shap/` with SHAP tables and
  the cached per-window SHAP values in `shap/shap_cache_r1/`) and the `plots/` folder of each run.
- `results/03_bg_check/`: the background-check caches and `bg_check_summary_lb7.csv`.

## Decision tags in comments and output

Reviewer comments are numbered in the order of the review: R1.1 to R1.4 are Reviewer 1's numbered points and R1.5 to
R1.18 the points of Reviewer 1's list (for example R1.9 calendar periods, R1.10 COVID-19 restrictions, R1.13
attribution lookback, R1.15 all cities, R1.16 city bias). R3.1 to R3.6 are Reviewer 3's points. A suffix (R1.1-7,
R1.2-4, R1.9-4) is a sub-item of that comment.

| Tag | Meaning |
|---|---|
| C5 | Causal decomposition: each day decomposed from the previous ≤365 available days (at least 180) |
| a1 | Channel grouping: IMF1 to IMF4 in sifting order plus one slow channel |
| D1 | Calendar-based windows: (b) gaps of at most 3 days filled from the past (main), (a) nothing filled |
| D2, G1 | How a decomposition history treats gaps: longer gaps are joined |
| D3, S1, S2 | Window-construction checks: S1 compares windows with and without filled days, S2 retrains three window constructions |
| D4 | Rule that selects the eight-city attribution set from data completeness and pollution level |
| N1, P3 | Pollutant gap filling from the city's own past only |
| N2 | SHAP explains the model on exactly its saved training inputs |
| N4 | CEEMDAN noise amplitude passed under the name the library reads |
| N5 | SHAP sampling seeded per city |
| N6 | Ablation run and compared at the main lookback |
| P4 | Common calendar split for all cities |
| L4 | Main lookback chosen by validation R² only |
| B1, B2 | City-conditioning variants and their per-city diagnostics (R1.16) |
| T2 | PM2.5-target experiment (R3.6) |
| I-4 | Channel naming by sifting index |
| I-5 | Channel periods saved per window |
| I-6 | Decomposition of observed days only, shared by two S2 arms |
| I-8 | Every training saved and reused across sessions after checks of data, settings and code |
| I-9 | Separate Drive folder per run |
| I-11 | Notebook 01 plots displayed (non-interactive plotting backend removed) |
| I-13 | KernelSHAP without the library's default limit of 10 non-zero values, per input and per channel |
| I-14 | Boundary extension of the decomposition and its adoption rule |
| I-15 | The main pipeline on the boundary-extended decomposition (notebook 02 _r1_ext) |
| I-16 | SHAP background-sample check (notebook 03) |
| step 6c to 6k | Implementation steps of the revision |
| run of record | The run of notebook 02 _r1 |

## Data

CPCB India air-quality data (`city_day.csv`), the public "Air Quality Data in India" dataset (Kaggle), included under
`data/`. Target: next-day `AQI`. Inputs: 12 pollutant concentrations (PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3,
Benzene, Toluene, Xylene).
