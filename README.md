# Explainable Crack-Risk Estimation in IN939 LPBF

Working repository for a paper on explainable crack-risk estimation in IN939 laser powder bed fusion (LPBF). It combines three streams of evidence:

1. **Stream 1, sensor analysis** (`src/sensor_analysis/`): physics-based proxy classification of acoustic-emission recordings, with thermal data treated descriptively.
2. **Stream 2, literature mining** (`src/literature_pipeline/`): LLM-assisted extraction of process parameters and crack outcomes from ten published IN939 LPBF studies.
3. **Stream 3, model** (`src/modelling/`): Random Forest with stratified 5-fold cross-validation and SHAP.

## Layout

    paper/     LaTeX source, figures, fonts and the compiled PDF
    src/       code for the three streams
    data/      literature-derived datasets (CSV)
    dashboard/ results dashboard (HTML)

## Data

`data/clean_dataset_125.csv` holds the 129-sample cleaned literature dataset. The raw acoustic-emission and thermal recordings are not included because they have not been cleared for public release. The source papers are not included for copyright reasons.

## Known issues (not yet fixed)

- `requirements.txt` has a merged line (`python-dotenvscikit-learn`).
- `src/modelling/stream3_model.py` uses hardcoded `/home/claude/...` paths.
- The filename `clean_dataset_125.csv` does not match its 129 rows.
