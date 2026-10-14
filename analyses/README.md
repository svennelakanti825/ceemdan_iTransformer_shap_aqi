# Analyses outside the notebooks

Scripts and results of the analyses that run on CPU outside Colab notebooks 01 to 04: reference forecasts, the
leakage contrast, the official-bulletin analysis, the weather diagnostic, the weekly cycle and the literature sample.
The folders keep the layout in which the scripts were run, so their relative imports work unchanged.

## Where each result comes from

| Result | Script | Result file |
|---|---|---|
| Table 1, persistence and climatology rows, skill scores, Supplementary city table | `baselines/baselines.py` (design fixed in `baselines/BASELINES_DESIGN.md`) | `baselines/outputs/baselines_pooled.csv`, `baselines_skill.csv`, `baselines_city.csv` |
| Fig. 4a and the leakage table: past-only against whole-record decomposition | `e1_verification/e1_leakage_contrast.py` run through `x1_shap_recheck/x1_rerun.py E1` | `x1_shap_recheck/outputs/e1_accuracy.csv`, `e1_shares.csv` |
| Fig. 4b-c and the bulletin table: modes on the official bulletins, yearly folds 2019 to 2025 | `dataset_check/e7_decompose.py`, then `dataset_check/e7_d2_models.py` run through `x1_shap_recheck/x1_rerun_e7.py` | `x1_shap_recheck/outputs/e7_d2_pooled.csv`, `e7_d2_city.csv`, `e7_d2_verdict.txt` |
| Bulletin against dataset AQI (median r over 26 cities) | `dataset_check/e7_d0_d1.py` | `dataset_check/outputs/e7_d0_comparability.csv` |
| PM2.5 among the prominent pollutants on test-year bulletin days, 13 cities | `dataset_check/e7_prominent_pm25.py` | `dataset_check/outputs/e7_prominent_pm25_test_year.csv` |
| Weather diagnostic (Supplementary Note S8 and its table) | `e1_verification/c2_xgb_confirm.py`, `c2x_features.py`, `c2x_verdict.py`, run by `c2_colab_run.ipynb` | `e1_verification/outputs/c2_runs/T6/` |
| Weekly cycle of NO2 and AQI | `e1_verification/e4_weekly_cycle.py` | `e1_verification/outputs/e4_weekly_cycle.csv` |
| Literature sample (Supplementary Note S5 and its tables) | `literature_count/lc_*.py` | `literature_count/outputs/coding_sheet.csv`, `coding_order.csv`, `screening_decisions.csv`, `flow_counts.json` |

Fig. 2, Fig. 3b and Table 2 come from notebook 04 (`results/04_followups/`), and the other model results from
notebooks 01 to 03 (see the main README).

## SHAP from the best iteration (`x1_shap_recheck/`)

The XGBoost models stop early. `XGBRegressor.predict` then uses the best iteration, but `Booster.predict` with
`pred_contribs=True` uses every tree unless an iteration range is given. `x1_rerun.py` runs a script unchanged with
one switch, so that every contribution call uses the trees of the best iteration, and checks that the contributions
add up to the prediction. The reported attribution shares of the leakage contrast and the bulletin analysis are the
ones in `x1_shap_recheck/outputs/`. Error columns do not depend on SHAP and reproduce exactly (`x1_run_log.txt`).
After a run the wrapper restores the scripts' default output files with `git checkout`, so those files must be
committed before it runs. `x1_rerun.py` also lists checks (E3, E5, E6, V3, V5) that are not part of the study. Only
E1 and E7 are reported.

## Weather diagnostic: pre-registration and code freeze

The rules, the thresholds and the reported wording were fixed on 10 October 2026, before any result existed, in
`e1_verification/C2_PREREGISTRATION.md` with addenda `C2_PREREGISTRATION_ADDENDUM_A1.md` and `_A2.md`. The code was
then frozen. `e1_verification/C2_FREEZE_SHA256.txt` lists the SHA-256 of the 13 frozen files (the three documents,
the code, its tests in `tests/`, the requirements and the run notebook). These files are published byte for byte as
frozen, so the digests can be recomputed:

```
python -c "import hashlib,sys;b=open(sys.argv[1],'rb').read();print(hashlib.sha256(b.replace(b'\r\n',b'\n')).hexdigest())" FILE
```

(`.py`, `.md`, `.csv`, `.txt` and `.json` after converting CRLF to LF, the notebook `c2_colab_run.ipynb` as raw
bytes, which `.gitattributes` keeps exact). The executed run notebook (`outputs/c2_runs/T6/c2_colab_run_executed.ipynb`)
prints that all frozen files in the run bundle match the freeze list before any model is fitted, and the verdict
(`outputs/c2_runs/T6/c2x_verdict.txt`) records the digests of the pre-registration and both addenda. Because the
frozen files are unchanged, their comments and paths refer to the authors' project layout (for example the location
of `city_day.csv`), in which the run bundle was built by `c2_colab_bundle.py`.

The run was repeated on two further machines (a second Colab session, `T7`, and a laptop under Linux, `S1_wsl_i5`).
The predictions, pooled and city results are byte-identical across the three runs:

| File | SHA-256 (all three runs) |
|---|---|
| `c2x_predictions.npz` (31.6 MB, not included) | `69c54434cff032e01c6eb83c21bde0f69d6054d9807012f65e254fba5def4165` |
| `c2x_pooled.csv` | `6e335e5e146a113dc16548fa350ce9848d2f7e5b09b78f95b6caec85daeba8da` |
| `c2x_city.csv` | `d9db8f03fdbc96b4eac3e5eb7105dd63ce3f6359af423543ae40b3a4b5bdee14` |

The verdict files differ only in their run metadata (time, machine). The reported run is `T6`.

## Changes from the code as run

Comments and docstrings were edited to remove internal document names. The code is as run, except these lines:

| File | Line as run | Here |
|---|---|---|
| `e1_verification/common.py` | absolute path of `city_day.csv` on the authors' machine | `DATA = REV1.parent / 'data' / 'city_day.csv'` |
| `e1_verification/e4_weekly_cycle.py` | the same path, relative to the authors' project | `data/city_day.csv` of this repository |
| `dataset_check/e7_common.py` | the same path, relative to the authors' project | `KAGGLE = HERE.parents[1] / 'data' / 'city_day.csv'` |
| `baselines/baselines.py` | stored main-model predictions in the authors' project | `results/02_r1_ext/reports/r116_test_predictions_lb7.npz` |
| `dataset_check/e7_prominent_pm25.py` | all-city attribution summary in the authors' project | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` |
| `x1_shap_recheck/x1_rerun.py` | `REPO = REV1.parent.parent` | `REPO = REV1.parent` (the root of this repository) |
| `literature_count/lc_search.py` | the authors' e-mail address for the OpenAlex polite pool | `MAILTO = os.environ.get('OPENALEX_MAILTO', '')` |

The frozen weather-diagnostic files and `baselines/BASELINES_DESIGN.md` are not edited at all (their SHA-256 is
recorded in the outputs). The file `dataset_check/E7_DECISION_RULES.md` is an excerpt of the bulletin analysis's
pre-specification. Its rules are verbatim and its header lists the edits.

## Inputs

- **Past-only CEEMDAN decompositions** of the 18 cities (`c5_decompositions_ext_ar/c5_<city>.npz`, about 35 MB, not
  included). Most
  scripts load them through `e1_verification/common.py` from `phase4_v2_results_r1/models/c5_decompositions_ext_ar/`
  in this folder. They are written by Section 19 of notebook 02 _r1 to
  `MyDrive/phase4_v2_results_r1/models/c5_decompositions_ext_ar/`. Copy that folder here. `common.py` checks each
  file against a fingerprint of the rebuilt calendar before use.
- **Official bulletins** (not included). `python dataset_check/data_bulletins/fetch_bulletins.py` downloads the file at a fixed
  commit of the urbanemissions.info repository (GPL-3.0) and checks its SHA-256. `dataset_check/e7_decompose.py` then
  writes the bulletin decompositions to `dataset_check/outputs/decomp/` (several CPU-hours).
- **Weather.** The ERA5 files used are included (`e1_verification/outputs/era5_daily.csv` and `era5_daily_pool.csv`,
  CC BY 4.0, see `ERA5_SOURCE.txt`), because the Open-Meteo service cannot return a fixed snapshot.
- **Literature.** Full texts and abstracts are not redistributed (copyright). `screening_set_no_abstracts.csv` is the
  screening set without its abstract column. The Scopus searches need an Elsevier API key (`ELSEVIER_API_KEY`).
  The search protocol is given in Supplementary Note S5.
- **Whole-record decompositions** for the leakage contrast are included (`e1_verification/outputs/fullrec_<city>.npz`,
  written by `e1_verification/fullrecord_decomp.py`).

## How to run

Python 3.13 with numpy, pandas, scipy, xgboost and EMD-signal 1.9.0 (the weather diagnostic pins its environment in
`e1_verification/c2_requirements.txt`: XGBoost 3.2.0, NumPy 2.4.2, pandas 3.0.1, SciPy 1.17.1). From this folder:

```
python baselines/baselines.py
cd e1_verification && python fullrecord_decomp.py && python e4_weekly_cycle.py && cd ..
python x1_shap_recheck/x1_rerun.py E1
python dataset_check/data_bulletins/fetch_bulletins.py
cd dataset_check && python e7_d0_d1.py && python e7_decompose.py && python ../x1_shap_recheck/x1_rerun_e7.py && python e7_prominent_pm25.py && cd ..
```

The weather diagnostic ran on a Colab CPU runtime under Linux from the bundle described above (two processes, about
two hours). Its tests run with `python -m pytest tests`.
