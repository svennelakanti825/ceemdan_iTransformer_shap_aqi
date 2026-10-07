# Trained models and decompositions

Trained models, scalers, saved training datasets and the per-city causal decompositions are large and are **not**
stored in this repository. The notebooks write them to Google Drive (`MyDrive/phase4_v2_results_r1/models/` and
`MyDrive/phase4_v2_results_r1_ext/models/`). They are available from the authors on request.

Running the notebooks regenerates them from `data/city_day.csv`. Every result file the runs wrote is under
`results/`, including the per-window SHAP values (`reports/shap/shap_cache_r1/`) and the saved test predictions of the
city-conditioning runs (`reports/r116_test_predictions_lb7.npz`).
