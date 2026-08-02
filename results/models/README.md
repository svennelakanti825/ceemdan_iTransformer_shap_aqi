# Trained model artifacts

The trained model checkpoints and the full KernelSHAP artifacts produced by
`notebooks/02_ceemdan_itransformer_shap.ipynb` are large and are **not** stored in this
repository. They are available separately from the authors on request.

This includes, per lookback window and per city where applicable:

- CEEMDAN+iTransformer checkpoints (proposed model, lookback 7/14/21/30)
- Plain iTransformer, CEEMDAN+LSTM, and LSTM baseline checkpoints
- 13-channel ablation checkpoint
- Cached per-city CEEMDAN decompositions
- Raw KernelSHAP value arrays for the 3-city and 8-city analyses

The distilled outputs needed to verify every number and figure in the paper are already
included in this repository under `results/metrics/` and `results/figures/`. Running the
notebooks top to bottom regenerates the artifacts above from `data/city_day.csv`.
