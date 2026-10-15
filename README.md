# How past data representation shapes timescale explanations of air quality forecasts

Implementation of the study. The framework decomposes each city's daily Air Quality Index (AQI) history into temporal
channels with a **past-only CEEMDAN** (each day decomposed from data available up to that day only), forecasts
next-day AQI with one city-conditioned **iTransformer** over 17 inputs (12 pollutant concentrations and 5
decomposition channels), and attributes each forecast across pollutants and decomposition channels with
**KernelSHAP**. It is evaluated on daily CPCB data from 18 Indian cities with a common calendar split, against
persistence and seasonal climatology, and complemented by XGBoost analyses for which exact attributions exist.
"Past-only" is a constraint on the information used, not a claim about environmental causes.

The notebooks contain all code and all printed outputs of the runs that produced the reported results. The
`results/` folder holds every file those runs wrote, apart from trained models. The `analyses/` folder holds the
scripts and results of the analyses that ran outside the notebooks (see `analyses/README.md`).

## Repository layout

```
.
├── notebooks/
│   ├── 01_phase1_baselines_r1.ipynb                # DLinear, NLinear, XGBoost, Keras LSTM
│   ├── 02_ceemdan_itransformer_shap_r1.ipynb       # full pipeline without the boundary extension (sensitivity) + diagnostics
│   ├── 02_ceemdan_itransformer_shap_r1_ext.ipynb   # full pipeline with the boundary extension (main results)
│   ├── 03_shap_background_check_r1_ext.ipynb       # SHAP background-sample check on the main results
│   └── 04_followups_g1_g3_r1_ext.ipynb             # all-city attribution, decomposition realisations, city conditioning
├── analyses/                                       # reference forecasts, leakage contrast, official bulletins,
│                                                   # weather diagnostic, weekly cycle, literature sample
├── data/
│   └── city_day.csv                                # CPCB dataset (see "Data")
├── results/
│   ├── 01_baselines/                               # files written by notebook 01
│   ├── 02_r1/                                      # reports/ and plots/ of notebook 02 _r1
│   ├── 02_r1_ext/                                  # reports/ and plots/ of notebook 02 _r1_ext (main results)
│   ├── 03_bg_check/                                # files written by notebook 03
│   ├── 04_followups/                               # reports/ and plots/ of notebook 04
│   └── models/                                     # main model, scalers, digests of the stored inputs (see README there)
├── requirements/                                   # one pinned file per environment (see "Environments")
└── README.md
```

## Where each result comes from

| Result | Source |
|---|---|
| Table 1, model rows | `results/01_baselines/phase1_colab_comparison_metrics.csv`, `results/02_r1_ext/reports/comparison_v2_full.csv`, `multiseed_summary_lb7.csv` |
| Table 1, persistence and climatology | `analyses/baselines/outputs/` |
| Table 2, city conditioning | `results/04_followups/reports/g3_conditioning_summary_lb7.csv` |
| Fig. 2, attribution in all cities | `results/04_followups/reports/shap/g1_shap18_matrix_lb7.csv`, `g1_shap18_summary_lb7.csv` |
| Fig. 3a, raw-history ablation and PM2.5 target | `results/02_r1_ext/reports/shap/shap_periods_ablation13ch_lb7.csv`, `shap_v2_pm25_attribution_lb7.csv` |
| Fig. 3b, four decomposition realisations × five model seeds | `results/04_followups/reports/shap/g2_shap_lb7.csv`, `results/04_followups/reports/g2_anova_lb7.csv` |
| Component diagnostic (four decomposition seeds, three cities, six dates) | `results/02_r1_ext/reports/c5_seed_stability.csv` |
| Fig. 4a, leakage contrast | `analyses/x1_shap_recheck/outputs/e1_accuracy.csv`, `e1_shares.csv` |
| Fig. 4b-c, official bulletins | `analyses/x1_shap_recheck/outputs/e7_d2_pooled.csv` |
| Weather diagnostic | `analyses/e1_verification/outputs/c2_runs/T6/` |
| Literature sample | `analyses/literature_count/outputs/coding_sheet.csv` |
| Window construction, boundary extension, lookback, background (Supplementary Information) | `results/02_r1/`, `results/02_r1_ext/`, `results/03_bg_check/` |

`analyses/README.md` lists the remaining Supplementary results and the scripts that produced them.
`analyses/TRACEABILITY.md` maps every number of the main text and the Supplementary Notes, section by section and by
Supplementary table label, to the file it comes from. Numbers that no file prints (for example the 85.4% share of
the weather gain in the short bands) are computed by `analyses/manuscript/scripts/trace_claims.py`, which recomputes
all of them from the files of this repository and reports any difference from the printed value.

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
   5. `04_followups_g1_g3_r1_ext`: reads notebook 02 _r1_ext's folder (never writes there) and writes to its
      subfolder `guide_followups/`. Pre-flight checks first confirm that the reused files, decompositions, datasets,
      models and SHAP values reproduce. About 24 hours over two sessions.
3. Notebook 01 writes its two result files to the Colab session. Download them at the end.
4. The analyses outside the notebooks run on a CPU (see `analyses/README.md`).

Compute: each full decomposition of the 18 cities takes about 18 CPU-hours (parallel over the available cores).
Notebook 02 computes up to four of them (AQI, PM2.5 target, observed days only, second seed), and notebook 04 two
more (decomposition seed bases 2024 and 7). KernelSHAP takes about 14 minutes per city at
lookback 7 on a T4.

### Environments

Each environment has one file with exact versions, taken from what the runs recorded.

| Environment | Runs | Pinned file |
|---|---|---|
| Google Colab, Tesla T4 GPU, Python 3.13.15, CUDA 13.0 | notebooks 01 to 04 | `requirements/notebooks_colab_gpu.txt` |
| Windows 11 laptop CPU, Python 3.13.0 | scripts in `analyses/` | `requirements/analyses_local_cpu.txt` |
| Colab CPU runtime under Linux, Python 3.13.0 | weather diagnostic | `analyses/e1_verification/c2_requirements.txt` (frozen with its code) |

On Colab the notebooks install EMD-signal and shap themselves and use the runtime's other packages, so a current
runtime may differ from the recorded one. The first file restores the recorded versions.

**Comments in the notebooks.** Code comments, docstrings and markdown were edited for this repository (internal
document references removed). Code and outputs are exactly as run.
Notebook 02 _r1's header explains how its Sections 18 and 19 were run. The tags in comments and printed output are
explained below.

## Pipeline

- **Data and windows.** Each city's series is placed on a continuous daily calendar. Input gaps of at most 3 days
  are filled from the last observed day, pollutant gaps from the city's own past readings only (no backward fill,
  nothing from other cities), and targets are never filled. A window is kept only if its last input day has at least
  180 available days of history.
- **Split.** One calendar for all cities, by target date: training before 1 Apr 2019, validation 1 Apr to 30 Jun
  2019, test 1 Jul 2019 to 1 Jul 2020. Every accuracy is also reported for pre-lockdown and lockdown/Unlock targets
  (from 25 Mar 2020). 18 cities have training windows under these rules.
- **Past-only decomposition.** For every available day t, CEEMDAN (100 trials, noise amplitude 0.2, at most 8 modes)
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
  patience 20, set in one cell of notebook 02 before training) were taken from an earlier configuration of
  the study and were not tuned on this split. The same settings are used for every seed,
  lookback and both decomposition pipelines.
- **Attribution.** KernelSHAP with one value per channel (all lookback days of a channel replaced together), 100 test
  windows and 50 background windows per city, seeded per city.

## Main results (lookback 7, test year)

Model comparison (single runs, seed 123) and reference forecasts:

| Model | R² | RMSE | MAE |
|---|---|---|---|
| XGBoost (notebook 01) | 0.855 | 42.92 | 23.24 |
| LSTM, Keras (notebook 01) | 0.844 | 44.48 | 24.47 |
| LSTM (notebook 02, Section 7c) | 0.840 | 44.99 | 27.65 |
| CEEMDAN+iTransformer (proposed) | 0.833 | 46.06 | 27.98 |
| DLinear (notebook 01) | 0.833 | 46.07 | 25.91 |
| iTransformer (plain) | 0.829 | 46.51 | 27.43 |
| NLinear (notebook 01) | 0.828 | 46.65 | 26.41 |
| CEEMDAN+LSTM | 0.824 | 47.29 | 26.96 |
| Persistence (AQI of the origin day) | 0.790 | 51.62 | 23.86 |
| Seasonal climatology | 0.212 | 99.94 | 64.92 |

Five model seeds, mean ± s.d.: proposed 0.821 ± 0.014, plain iTransformer 0.819 ± 0.017, 13-channel ablation (lagged
AQI instead of the decomposition) 0.821 ± 0.034. Over four CEEMDAN realisations with five model seeds each the
proposed model gives 0.821 ± 0.017, with no difference between realisations. The decomposition adds no accuracy over
these baselines. Against persistence the proposed model improves the squared error but not the absolute error (MAE
28.71 ± 2.62 against 23.86, lower than persistence in 1 of 18 cities). Only XGBoost has a lower MAE than persistence.
Without the boundary extension (notebook 02 _r1) the proposed model gives 0.791 ± 0.024 on test, with unchanged
validation accuracy (0.787 against 0.789 with the extension, over five seeds).

Attribution (notebook 04, all 18 cities, 13 of which meet the completeness threshold for interpretation): past PM2.5
is the top input in all 13 cities (17 of 18 in all). The decomposition channels take 14.5% to 26.6% of the mean
absolute SHAP value in the 13 cities, most of it on the slow channel (74.7% to 94.7% of the decomposition share).
IMF1 to IMF4 take 1.40% to 4.81%.

Dependence on representation and training: when one raw AQI channel replaces the five decomposition channels, it
takes 53.2%, 41.6% and 35.5% of the attribution in Delhi, Mumbai and Bengaluru (24.0%, 17.7% and 14.5% for the
decomposition). Across 20 models (four CEEMDAN realisations, five model seeds each) the decomposition share spans
7.5% to 32.1% in Delhi, 12.4% to 34.2% in Mumbai and 8.5% to 31.5% in Bengaluru. The model seed accounts for this
spread (s.d. 5.9 to 7.0 percentage points), and differences between realisations stay within it (p 0.50 to 0.71).
Past PM2.5 leads in 59 of the 60 city models.

Background sample (notebook 03, Delhi, Mumbai and Bengaluru): with two new background samples of 50 training windows
each, none shared with the original sample, the decomposition share stays within 23.1% to 24.0% (Delhi), 17.7% to
18.7% (Mumbai) and 14.2% to 14.6% (Bengaluru), the ranking of the 17 channels agrees with the original sample
(Spearman ρ at least 0.978), and past PM2.5 stays the top input.

The XGBoost analyses (leakage contrast, official bulletins, weather diagnostic) are described in `analyses/README.md`.

## Results folders

- `results/01_baselines/`: `phase1_colab_comparison_metrics.csv`, `phase1_colab_comparison_summary.json`.
- `results/02_r1/` and `results/02_r1_ext/`: the `reports/` folder (CSV and JSON results, `shap/` with SHAP tables and
  the cached per-window SHAP values in `shap/shap_cache_r1/`) and the `plots/` folder of each run.
- `results/03_bg_check/`: the background-check caches and `bg_check_summary_lb7.csv`.
- `results/04_followups/`: the `reports/` and `plots/` folders of notebook 04. `reports/inputs_r1_ext/` holds the
  files reused from notebook 02 _r1_ext, copied and checked against their recorded SHA-256. `g_preflight.json`
  records the pre-flight checks and `g_sessions.json` the software of each session.

## Tags in comments and output

Comments and printed output carry short tags that link each part of the code to the design question or check it
addresses. Tags R1.1 to R1.18 and R3.1 to R3.6 name these questions, for example R1.1 past-only decomposition, R1.2
channel comparability across cities, R1.3 attribution robustness, R1.9 calendar periods, R1.10 COVID-19 restrictions,
R1.13 attribution lookback, R1.15 all cities, R1.16 city bias, R3.3 window construction and R3.6 PM2.5 target. A
suffix (R1.1-7, R1.2-4, R1.9-4) is a sub-item.

| Tag | Meaning |
|---|---|
| C5 | Past-only decomposition: each day decomposed from the previous ≤365 available days (at least 180) |
| a1 | Channel grouping: IMF1 to IMF4 in sifting order plus one slow channel |
| D1 | Calendar-based windows: (b) gaps of at most 3 days filled from the past (main), (a) nothing filled |
| D2, G1 | How a decomposition history treats gaps: longer gaps are joined |
| D3, S1, S2 | Window-construction checks: S1 compares windows with and without filled days, S2 retrains three window constructions |
| D4 | Completeness rule behind the manuscript's 13-city interpretation threshold, and the eight-city subset of the first revision round (see "D4 and the 13-city threshold" below) |
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
| G1, G2, G3 (notebook 04) | Attribution in all 18 cities, four decomposition realisations × five model seeds, five seeds per city-conditioning arm |
| P1 to P5 (notebook 04) | Pre-flight checks: reused files, decompositions, datasets, models and SHAP values reproduce |
| step 6c to 6k | Implementation steps |
| run of record | The run of notebook 02 _r1 |

In notebook 04, G1 names the all-city attribution, not the gap rule of the table above.

### D4 and the 13-city threshold

The manuscript's prespecified completeness screen and tag D4 are the same rule. D4 has two steps, implemented by
`d4_completeness` and `d4_shap8_cities` in notebook 04, in the code cell that starts "Revision 1, R3.3 decision D4
(option c)" (cell 36 counting from 0, just before the heading "G1-G3 helper functions").

1. **Completeness screen (the manuscript's 13 cities).** A city passes when at least 80% of its 14-day calendar
   windows are kept under the calendar eligibility rule (`D4_MIN_KEPT_PCT = 80.0`, `D4_LOOKBACK = 14`). It uses the
   14-day lookback whatever lookback is later selected, so it does not depend on the lookback choice. Thirteen of the
   18 modelled cities pass. The five that fail (Ahmedabad, Brajrajnagar, Jorapokhar, Talcher, Visakhapatnam) are
   trained and evaluated and carry a limited-data flag. The cell prints the table with the kept share of every city,
   and the result files carry it as `passes_completeness` (`results/04_followups/reports/shap/g1_shap18_summary_lb7.csv`)
   and as `eligible14_pct` (`analyses/e1_verification/outputs/data_audit.csv`). The manuscript interprets attribution
   in these 13 cities (Methods, Calendar windows and missingness).
2. **Eight-city subset (first revision round only).** From the cities that pass, Delhi, Mumbai and Bengaluru plus the
   five most polluted others by mean AQI (Patna, Gurugram, Lucknow, Kolkata, Jaipur) form the eight-city set. The
   first revision round computed attribution for these eight only, and the column `d4_attribution_set` in the same
   file marks them. Notebook 04 then computed the other ten cities (G1), which gives all 18 cities, and the manuscript
   reports the 13 that pass. It uses the eight only to state that their earlier values were reproduced exactly
   (Supplementary Note S6). The pollution-level step plays no part in which cities are interpreted.

So "eight-city set" in older comments and output names step 2, and the manuscript's 13 cities are step 1. The eight
cities all pass step 1, so they are a subset of the 13.

## Data

Source: the public "Air Quality Data in India" dataset on Kaggle, file `city_day.csv` (daily city-level pollutant
concentrations and AQI from the Central Pollution Control Board (CPCB), India), version 12, CC0:
https://www.kaggle.com/datasets/rohanrao/air-quality-data-in-india?select=city_day.csv

The file used by all notebooks and analyses is included under `data/` so they run without a download. Target:
next-day `AQI`. Inputs: 12 pollutant concentrations (PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene,
Xylene).
