# Trained models and decompositions

This repository holds the inputs that the analyses and the attribution need and that are slow to regenerate.
`SHA256SUMS.txt` in this folder lists the SHA-256 of each of them (raw bytes).

| Path | What it is |
|---|---|
| `analyses/phase4_v2_results_r1/models/c5_decompositions_ext_ar/c5_<city>.npz` (18 files, 31 MB) | Past-only CEEMDAN decompositions of the 18 cities (seed 123 plus the city index, histories extended by 30 days with an autoregressive model). Written by Section 19 of notebook `02_ceemdan_itransformer_shap_r1`, about 18 CPU-hours. Every script in `analyses/` reads them from this folder, and they match the digests pinned in Appendix A of `analyses/e1_verification/C2_PREREGISTRATION.md`. |
| `results/models/02_r1_ext/ceemdan_it_v2_lb7.pt` | Main CEEMDAN+iTransformer model, lookback 7, model seed 123 (PyTorch state, torch 2.11.0). |
| `results/models/02_r1_ext/ceemdan_it_v2_lb7_scalers.pkl` | Its input, channel and target scalers and the city index (pickle, scikit-learn 1.6.1). |
| `results/models/02_r1_ext/ceemdan_it_v2_lb7_scalers.json` | The same scaler parameters and city index as plain JSON, for readers who prefer not to load a pickle. |
| `results/models/02_r1_ext/ceemdan_it_v2_lb7_dataset.npz` | The training, validation and test windows of the model with their dates and the test predictions. |

The model's SHA-256, `2184fa3ef205a8e0fc172aaed5534219e59aa7edb1a9df63c6cbe3c8ba46555e`, is the `model_sha256` stored
in every KernelSHAP cache file of the main model in `results/02_r1_ext/reports/shap/shap_cache_r1/`, so these are the
weights behind the reported attributions.

To use them in Google Colab, copy `c5_decompositions_ext_ar/` to `MyDrive/phase4_v2_results_r1/models/`, from where
notebook `02_ceemdan_itransformer_shap_r1_ext` reuses it, and the three `ceemdan_it_v2_lb7*` files other than the
`.json` to `MyDrive/phase4_v2_results_r1_ext/models/`, where its KernelSHAP sections load them.

The other trained models (lookbacks 14 to 30, baselines, multi-seed and sensitivity runs) are not stored. Running the
notebooks regenerates them from `data/city_day.csv`. Every result file the runs wrote is under `results/`, including
the per-window SHAP values (`reports/shap/shap_cache_r1/`) and the saved test predictions of the city-conditioning runs
(`reports/r116_test_predictions_lb7.npz`).
