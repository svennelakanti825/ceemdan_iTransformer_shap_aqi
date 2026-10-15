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
| Windows, missingness, filled and compressed histories, completeness screen (Supplementary Note S1 and its tables) | `e1_verification/data_audit.py` | `e1_verification/outputs/data_audit.csv`, `pollutant_missing.csv` |
| Prefix audit: availability recomputed from each origin's calendar prefix (19,250 origins, 0 mismatches, 59 filled test windows) | `e1_verification/data_audit.py` | `e1_verification/outputs/prefix_audit.json` |
| Ahmedabad CO equal to NO on 1,317 days, and the XGBoost proxy check (MAE of the other 17 cities 9.9% lower without Ahmedabad, Welch p 6.5e-05) | `dataset_check/gd_ahmedabad_check.py`, then `dataset_check/ahmedabad_co_no.py` | `dataset_check/outputs/gd_ahmedabad_check/`, `dataset_check/outputs/ahmedabad_co_no.txt` |
| Detectable realisation effect of the G2 test (1.32 times the model-seed s.d. with 80% probability) | `followups/g2_power.py` | `followups/g2_power.txt` |
| Exploratory test-year weather analysis disclosed in Methods, and the power planning of the weather diagnostic (both cited by the pre-registration) | `e1_verification/e3_met_forecast.py`, `e1_verification/c2_t1_design_check.py` | `e1_verification/outputs/e3_met_forecast.csv`, `c2_t1_design_check.txt` (reads `e5_pooled.csv`) |
| Boundary error of IMF1 to IMF4 with and without the autoregressive extension (18% lower), the step that chose the extension | `e1_verification/i14_boundary_error.py` (rerun on the laptop: byte-identical output) | `e1_verification/outputs/i14_boundary_error.csv` |
| Every number of the main text and the Supplementary Notes, with the printed and the recomputed value (derived numbers such as the 85.4% short-band share are listed with their formula) | `manuscript/scripts/trace_claims.py` | `TRACEABILITY.md`, `manuscript/outputs/trace_claims.csv`, `manuscript/outputs/derived_numbers.txt` |
| Weekly cycle of NO2 and AQI | `e1_verification/e4_weekly_cycle.py` | `e1_verification/outputs/e4_weekly_cycle.csv` |
| Literature sample (Supplementary Note S5 and its tables) | `literature_count/lc_*.py` | `literature_count/outputs/coding_sheet.csv`, `coding_order.csv`, `screening_decisions.csv`, `flow_counts.json` |

## Figures and tables of the manuscript (`manuscript/`)

- `manuscript/scripts/make_figures.py` draws Figs 1 to 4 and Supplementary Fig. S1 (including the average-linkage
  clustering that orders the cities in Fig. S1) into `manuscript/figures/`.
- `manuscript/scripts/make_tables.py` writes Tables 1 and 2 to `manuscript/tables/` and the supplementary tables
  `tableS_*` to `manuscript/si_tables/`, including the Wilson 95% intervals of the literature shares.
- `manuscript/scripts/rebuild_si_tables.py` computes the twelve supplementary tables `si_tables/ch_*.tex` (windows,
  coverage, missingness, background, city accuracy and periods, channel periods, lookback, gap sensitivity) into
  `manuscript/si_rebuild/tables/` under their names without the `ch_` prefix. The numbers in every table body are
  identical to `si_tables/ch_*.tex`, whose captions and notes were then edited for wording. The script also writes
  tables and figures of an earlier draft that are not used.

The tables regenerate byte for byte. The figures regenerate with identical plotted values. Their glyphs depend on the
installed fonts (Liberation Sans or Arial).

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

The pre-registration also refers to `C2_TASK_TRACKER.md`, the authors' internal project log, which is not
distributed. The digests it recorded are those in `C2_FREEZE_SHA256.txt` and in the verdict file.

The run was repeated on two further machines (a second Colab session, `T7`, and a laptop under Linux, `S1_wsl_i5`).
The predictions, pooled and city results are byte-identical across the three runs:

| File | SHA-256 (all three runs) |
|---|---|
| `c2x_predictions.npz` (31.6 MB, not included) | `69c54434cff032e01c6eb83c21bde0f69d6054d9807012f65e254fba5def4165` |
| `c2x_pooled.csv` | `6e335e5e146a113dc16548fa350ce9848d2f7e5b09b78f95b6caec85daeba8da` |
| `c2x_city.csv` | `d9db8f03fdbc96b4eac3e5eb7105dd63ce3f6359af423543ae40b3a4b5bdee14` |

The verdict files differ only in their run metadata (time, machine). The reported run is `T6`.

### Pinned inputs

Appendix A of the pre-registration pins the SHA-256 of the data, the ERA5 files, the decompositions and nine code
files the diagnostic imports. Eight of the code files are published exactly as pinned and verify with the command
above. The ninth, `e1_verification/common.py`, differs in one statement, the location of `city_day.csv`, as
section 2 of the pre-registration states for packaging. As run, the statement held an absolute path on the authors'
machine, which is left out below. It named the same pinned file as Appendix A (row 1). Here it points to
`data/city_day.csv` of this repository. All other lines are as run.

| `e1_verification/common.py` | SHA-256 |
|---|---|
| as run (pinned in Appendix A, and printed by the run in `outputs/c2_runs/T6/c2x_verdict.txt`) | `dd1a9716406d6521d9f418b9046a5ec96438a344e7a37cbd96a5efd2a3d1ade3` |
| published here | `99bcd56be703e80e52668d97b943e0113cfb3c4c8c0248eefa00310b37d8e257` |

```diff
--- common.py (as run, pinned)
+++ common.py (published)
@@ -21,2 +21 @@
-DATA = Path(r'<absolute path on the authors' machine, part 1>'
-            r'<part 2>/city_day.csv')
+DATA = REV1.parent / 'data' / 'city_day.csv'
```

The statement did not affect the diagnostic. The frozen `c2x_features.py` checks the AQI file against its pinned
digest and then sets `common.DATA` to that file (line 209) before anything is read.

## Changes from the code as run

Comments and docstrings were edited to remove internal document names. The code is as run, except these lines:

| File | Line as run | Here |
|---|---|---|
| `e1_verification/common.py` | absolute path of `city_day.csv` on the authors' machine (exact lines and both digests under Pinned inputs) | `DATA = REV1.parent / 'data' / 'city_day.csv'` |
| `e1_verification/e4_weekly_cycle.py` | the same path, relative to the authors' project | `data/city_day.csv` of this repository |
| `dataset_check/e7_common.py` | the same path, relative to the authors' project | `KAGGLE = HERE.parents[1] / 'data' / 'city_day.csv'` |
| `baselines/baselines.py` | stored main-model predictions in the authors' project | `results/02_r1_ext/reports/r116_test_predictions_lb7.npz` |
| `dataset_check/e7_prominent_pm25.py` | all-city attribution summary in the authors' project | `results/04_followups/reports/shap/g1_shap18_summary_lb7.csv` |
| `x1_shap_recheck/x1_rerun.py` | `REPO = REV1.parent.parent` | `REPO = REV1.parent` (the root of this repository) |
| `manuscript/scripts/make_tables.py`, `make_figures.py` | result paths in the authors' project | the `results/` and `analyses/` folders of this repository |
| `manuscript/scripts/rebuild_si_tables.py` | a flat copy of the result files and the data audit in a working folder | a lookup in `results/02_r1_ext/reports`, `results/01_baselines`, `results/03_bg_check` and `e1_verification/outputs`, writing to `manuscript/si_rebuild/` |
| `e1_verification/i14_boundary_error.py` | repository, data and output locations in the authors' project | `ROOT` is the root of this repository, `DATA = ROOT / 'data' / 'city_day.csv'`, output to `outputs/` |
| `literature_count/lc_search.py` | the authors' e-mail address for the OpenAlex polite pool | `MAILTO = os.environ.get('OPENALEX_MAILTO', '')` |

The frozen weather-diagnostic files and `baselines/BASELINES_DESIGN.md` are not edited at all (their SHA-256 is
recorded in the outputs). The file `dataset_check/E7_DECISION_RULES.md` is an excerpt of the bulletin analysis's
pre-specification. Its rules are verbatim and its header lists the edits.

## Inputs

- **Past-only CEEMDAN decompositions** of the 18 cities (`c5_decompositions_ext_ar/c5_<city>.npz`, 31 MB,
  included). Most scripts load them through `e1_verification/common.py` from
  `phase4_v2_results_r1/models/c5_decompositions_ext_ar/` in this folder, where they are stored. They were written by
  Section 19 of notebook 02 _r1 and match the digests in Appendix A of the pre-registration (also listed in
  `results/models/SHA256SUMS.txt`). `common.py` checks each file against a fingerprint of the rebuilt calendar before
  use.
- **Official bulletins** (not included). `python dataset_check/data_bulletins/fetch_bulletins.py` downloads the file at a fixed
  commit of the urbanemissions.info repository (GPL-3.0) and checks its SHA-256. `dataset_check/e7_decompose.py` then
  writes the bulletin decompositions to `dataset_check/outputs/decomp/` (several CPU-hours).
- **Weather.** The ERA5 files used are included (`e1_verification/outputs/era5_daily.csv` and `era5_daily_pool.csv`,
  CC BY 4.0, see `ERA5_SOURCE.txt`), because the Open-Meteo service cannot return a fixed snapshot.
- **Literature.** Full texts and abstracts are not redistributed (copyright). The search exports
  (`outputs/search/openalex_records_no_abstracts.csv`, `scopus_records_no_abstracts.csv`, with `search_log.json` giving
  the queries, dates and counts) and `screening_set_no_abstracts.csv` are given without their abstract column. The Scopus searches need an Elsevier API key (`ELSEVIER_API_KEY`).
  The protocol, fixed before the searches ran, is `literature_count/LITERATURE_COUNT_PROTOCOL_13Oct2026.md`,
  published unchanged so that its SHA-256 in `PROTOCOL_SHA256.txt` can be recomputed (CRLF converted to LF). As it
  states, title and abstract screening and the first full-text coding were done with AI assistance (Claude,
  Anthropic). The first author then checked all 60 codings against the source papers. `outputs/coding_sheet.csv`
  is the coding reported in the paper.
- **Whole-record decompositions** for the leakage contrast are included (`e1_verification/outputs/fullrec_<city>.npz`,
  written by `e1_verification/fullrecord_decomp.py`).

## How to run

Python 3.13.0 with the versions pinned in `../requirements/analyses_local_cpu.txt`
(`python -m pip install -r ../requirements/analyses_local_cpu.txt`). The weather diagnostic pins its runner in
`e1_verification/c2_requirements.txt`, frozen with its code, at the same versions. From this folder:

```
python baselines/baselines.py
cd e1_verification && python fullrecord_decomp.py && python e4_weekly_cycle.py && cd ..
python x1_shap_recheck/x1_rerun.py E1
python dataset_check/data_bulletins/fetch_bulletins.py
cd dataset_check && python e7_d0_d1.py && python e7_decompose.py && python ../x1_shap_recheck/x1_rerun_e7.py && python e7_prominent_pm25.py && cd ..
```

The weather diagnostic ran on a Colab CPU runtime under Linux from the bundle described above (two processes, about
two hours). Its tests run with `python -m pytest tests`.
