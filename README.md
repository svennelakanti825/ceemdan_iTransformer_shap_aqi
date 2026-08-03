# Interpretable AQI forecasting with CEEMDAN + iTransformer + KernelSHAP

Supporting implementation for the paper *"Timescale decomposition of air-quality predictions identifies operational horizons for urban intervention"* The framework decomposes each city's daily Air
Quality Index (AQI) into intrinsic temporal modes with **CEEMDAN**, forecasts with a single
city-conditioned **iTransformer** over an 18-channel input (12 pollutants + 6 energy-ranked
IMFs), and attributes each forecast jointly across pollutants and temporal modes with
**KernelSHAP**. It is evaluated on five and a half years of daily observations from 20 Indian
CPCB cities.

The two notebooks are self-contained and reproduce every number, table, and figure in the paper.

## Repository layout

```
.
├── notebooks/
│   ├── 01_phase1_baselines.ipynb          # DLinear, NLinear, XGBoost (+ a Keras LSTM baseline)
│   └── 02_ceemdan_itransformer_shap.ipynb # proposed model + neural baselines + SHAP + ablation + multi-seed
├── data/
│   └── city_day.csv                       # CPCB dataset (see "Data" below)
├── results/
│   ├── metrics/                           # metric tables produced by the notebooks
│   ├── figures/                           # figures used in the paper
│   └── models/                            # placeholder — large trained artifacts provided separately
├── requirements.txt
└── README.md
```

## Notebook → paper mapping

| Notebook | Produces | Paper element |
|---|---|---|
| **01_phase1_baselines** | DLinear, NLinear, XGBoost at lookback 7/14/30 | **Table 2** (DLinear, NLinear, XGBoost rows) |
| **02_ceemdan_itransformer_shap** — §6 | Proposed CEEMDAN+iTransformer at lookback 7/14/21/30 | **Table 2** (proposed row), **Table 4** (lookback sensitivity) |
| **02** — §7a/7b/7c | Plain iTransformer, CEEMDAN+LSTM, LSTM baselines | **Table 2** (iTransformer, CEEMDAN+LSTM, LSTM rows) |
| **02** — §9 | KernelSHAP attribution for Delhi / Mumbai / Bengaluru (lookback 14) | **Table 5**, **Fig. 2** (per-city bars), **Fig. 3** (cross-city heatmap) |
| **02** — §11 | KernelSHAP at lookback 7 (robustness) | **Table 7** |
| **02** — §12 | 13-channel autoregressive ablation | Discussion (ablation), **Table 3** ablation row |
| **02** — §13 | Multi-seed reruns (5 seeds) + CEEMDAN period stability | **Table 3** (multi-seed) |
| **02** — §14 | 8-city SHAP generalisation | **Fig. 4** |
| **02** — §4 | Per-city CEEMDAN characteristic periods | **Table 8** |
| Architecture diagram | — | **Fig. 1** (`results/figures/architecture_v2_feature_aug.png`) |

Each result section inside the notebooks carries a **📄 Maps to manuscript** tag, and the top
of notebook 02 has a full bidirectional cross-reference index.

## Headline results (Table 2, lookback = 7, 20-city test set)

| Model | R² | RMSE | MAE | MAPE (%) |
|---|---|---|---|---|
| CEEMDAN+LSTM | 0.768 | 53.93 | 29.06 | 23.55 |
| DLinear | 0.795 | 50.63 | 26.11 | 19.75 |
| NLinear | 0.807 | 49.20 | 25.68 | 18.79 |
| LSTM | 0.818 | 47.68 | 29.67 | 29.63 |
| iTransformer | 0.835 | 45.51 | 25.00 | 23.03 |
| **XGBoost** | **0.864** | **41.29** | **21.77** | **18.32** |
| **CEEMDAN+iTransformer (proposed)** | 0.828 | 47.06 | 29.66 | 27.92 |

The proposed framework is competitive with the strongest baselines (best lookback: R² = 0.870
at 30 days). Its contribution is **interpretability** — resolving where a forecast's predictive
signal sits in time — rather than top predictive accuracy; a same-architecture 13-channel
ablation confirms the decomposition trades a small amount of accuracy for temporal resolution
(see notebook 02, §12, and Table 3).

## How to run

The notebooks are written for **Google Colab** (free GPU) and are the recommended way to
reproduce the results. Upload the notebook, attach `data/city_day.csv`, and run top to bottom.

To run locally:

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
jupyter notebook
```

Point each notebook's data path at `data/city_day.csv`. A CUDA GPU is recommended for
notebook 02 (CEEMDAN decomposition + Transformer training + KernelSHAP are compute-heavy);
CPU works but is slow.

## Results

- `results/metrics/` — the metric tables the notebooks emit:
  - `phase1_comparison_metrics.csv`, `phase1_comparison_summary.json` — DLinear/NLinear/XGBoost/LSTM.
  - `ceemdan_itransformer_lookback_metrics.csv` — proposed model at lookback 7/14/21/30.
  - `shap_attribution_3city_lb14.csv` — per-channel mean |SHAP| for Delhi/Mumbai/Bengaluru.
  - `shap_attribution_8city_lb14.csv` — clustered 8-city attribution matrix.
- `results/figures/` — the six figures used in the paper.
- `results/models/` — trained model checkpoints and the full KernelSHAP artifacts for
  notebook 02 are large and are provided separately (see `results/models/README.md`). The
  metrics and figures above are the distilled outputs and are sufficient to check every
  reported number.

## Data

CPCB India air-quality data (`city_day.csv`), the public "Air Quality Data in India" dataset
(Kaggle). It is included here under `data/` for convenience so the notebooks run out of the
box. Target variable: `AQI`. Features: 12 pollutant concentrations
(PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3, Benzene, Toluene, Xylene).

## Method summary

- **CEEMDAN** runs per city on the AQI series; the six highest-energy intrinsic mode
  functions (IMFs) are retained and concatenated with the 12 pollutant channels (18 channels).
- **iTransformer** applies channel-wise self-attention over the 18 channels (inverted
  tokenisation), with a learnable per-city scalar bias for cross-city baseline differences.
- **KernelSHAP** attributes each prediction across all 18 channels, separating temporal-scale
  (IMF) and pollutant-source contributions.
- **Evaluation protocol:** per-city chronological 70/10/20 train/validation/test split;
  scalers fit on the training split only; XGBoost uses strictly lagged pollutant features.
