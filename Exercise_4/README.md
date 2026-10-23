# SG52 Exercise 4: Pu-239 GLLS adjustment with Marini nu-bar

Exercise 4 adds the 25 Marini et al. (2021) prompt nu-bar differential points to the 29 integral responses of Exercise 3, giving m = 54. The 979-state Pu-239 prior and the 29 integral rows are the same as in Exercise 3.

Release data is read-only: `../SG52_materials/SG52_materials_release_3/`.

## Run

From the repository root (build `GLLS_code/build/nda` first if it is missing: `cmake --build GLLS_code/build`):

```bash
python3 Exercise_4/ex4_prior.py
python3 Exercise_4/ex4_observations.py
GLLS_code/build/nda Exercise_4/ex4_input.txt
python3 Exercise_4/analyze_ex4_results.py
python3 Exercise_4/export_ex4_excel.py
python3 -m pytest Exercise_4 -q
```

## Outputs

- `Exercise_4/ex4_prior.hdf5`: prior means and covariance.
- `Exercise_4/ex4_observations.hdf5`: `/delta`, `/cov`, `/sens`, `/responses/*` for the 54 responses.
- `Exercise_4/ex4_results.hdf5`: GLLS posterior.
- `Exercise_4/ex4_analysis/`: analysis report and plots.
- `Exercise_4/Submission/Ex4_relative_results.xlsx` and `Exercise_4/Submission/Ex4_absolute_results.xlsx`.

## Response set

- Rows 0 to 28: the 29 Exercise 3 integral responses, unchanged.
- Rows 29 to 53: `marini-nubar-00` to `marini-nubar-24`, in release order.

Marini selection: energy at or below 20 MeV and a non-zero sensitivity row. All 25 released points pass; the observation builder prints kept and dropped points.

## Observation model

- Sensitivity (as-MT452 rule, coordinator instruction recorded in `DBC/EXERCISES.md`): for Marini point k and energy group g, S[k, `94239_00452_g`] = C_k · s_rel[k,g] / μ_prior[`94239_00452_g`]. Marini rows have zero MT456 columns.
- Residual: δ_k = E_k − C_k, with values as released (no correction).
- Covariance is block diagonal:
  - integral block: diag(expt² + sim²), as in Exercise 3;
  - Marini block: diag(σ_E) ρ diag(σ_E), with σ_E = u · E (u relative, ρ from the release);
  - integral–Marini blocks: zero.
  The Marini block is checked for symmetry and positive definiteness (Cholesky).
- Marini `/responses`: experimental = E, experimental_uncertainty = σ_E (absolute), simulated = C, simulated_uncertainty = 0.

## Assumptions

- The Marini release has no sensitivity uncertainties (`sensitivities` holds `structure` and `values` only), so none are propagated.
- No calculation uncertainty is added to the Marini data.
- Integral and Marini data are treated as independent.
- MT456 states have no direct sensitivity in any row. Any posterior change arises only through prior cross-covariances; the analysis reports the MT456 shift rather than assuming zero.

## Tests

`test_ex4_prior.py` and `test_ex4_observations.py` read the release data and fail if it is missing. The observation test builds the 54-row file, checks the integral rows against `Exercise_3/ex3_observations.py` (run read-only), and checks the Marini covariance, sensitivity mapping, selection, and input validation.
