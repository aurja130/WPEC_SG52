# SG52 Exercise 8: Pu-239 GLLS adjustment with Snyder and Dongwi fission cross sections

Exercise 8 adds the Dongwi fission cross section shape data set (EXFOR 14851002, release 4) to the data of Exercise 6, giving m = 2733 = 2642 + 91 Dongwi points. The 2642 Exercise 6 responses are unchanged: 29 integral + 25 Marini nu-bar + 1220 Marini PFNS + 1277 Keegan PFNS + 91 Snyder. The 979-state Pu-239 prior is the same as in Exercises 3 to 6.

Exercise 8 has no ENDF/B-VIII.1 comparison: the specification asks for it only in Exercise 6.

Release data is read-only: `../SG52_materials/SG52_materials_release_4/`.

## Run

From the repository root (build `GLLS_code/build/nda` first if it is missing: `cmake --build GLLS_code/build`):

```bash
python3 Exercise_8/ex8_prior.py
python3 Exercise_8/ex8_observations.py
GLLS_code/build/nda Exercise_8/ex8_input.txt
python3 Exercise_8/analyze_ex8_results.py
python3 Exercise_8/export_ex8_excel.py
python3 -m pytest Exercise_8 -q
```

## Outputs

- `Exercise_8/ex8_prior.hdf5`: prior means and covariance.
- `Exercise_8/ex8_observations.hdf5`: `/delta`, `/cov`, `/sens`, `/responses/*` for the 2733 responses.
- `Exercise_8/ex8_results.hdf5`: GLLS posterior.
- `Exercise_8/ex8_analysis/`: analysis report, plots and CSV summaries.
- `Exercise_8/Submission/Ex8_relative_results.xlsx` (release 4 output template) and `Exercise_8/Submission/Ex8_absolute_results.xlsx`.

## Response set

- Rows 0 to 28: the 29 integral responses, unchanged.
- Rows 29 to 53: `marini-nubar-00` to `marini-nubar-24`, in release order.
- Rows 54 to 1273: `marini-pfns-0000` to `marini-pfns-1219`, in released order.
- Rows 1274 to 2550: `keegan-pfns-0000` to `keegan-pfns-1276`, in released order.
- Rows 2551 to 2641: `snyder-00` to `snyder-90`, in released index order.
- Rows 2642 to 2732: `dongwi-00` to `dongwi-90`, in released index order.

Snyder and Dongwi selection: incident energy at or below 20 MeV and a non-zero sensitivity row. The 92nd point of each shape file (20.54 MeV) has a zero sensitivity row and is dropped. The highest kept Dongwi incident energy is 19.395 MeV.

## Observation model

- Nu-bar and PFNS: as in Exercise 6 (as-MT452 rule for Marini nu-bar; PFNS one-hot rows with S = C_k / μ_prior; no block-normalization term in the sensitivity; one floating normalization factor per PFNS block with σ_N = 1.0 (100 %) in the covariance).
- Snyder: each point is its own observation with residual δ_k = E_k − C_k, where C_k is the released ENDF/B-VIII.0 MT18 value. Its sensitivity is the released one-hot row: a single non-zero entry on `94239_00018_<group>`, the group holding E_in, with S = C_k / μ_prior.
- Dongwi: treated as Snyder, with the same residual, one-hot MT18 sensitivity and S = C_k / μ_prior, over its 91 kept points.
- Covariance is block diagonal over the six data sets (integral, Marini nu-bar, Marini PFNS, Keegan PFNS, Snyder, Dongwi):
  - integral block: diag(expt² + sim²), as in Exercise 3;
  - Marini nu-bar, Marini PFNS, Keegan PFNS: diag(σ_E) ρ diag(σ_E), with σ_E = u · E (u relative, ρ from the release); Marini PFNS and Keegan PFNS additionally σ_N² Σ_b E_b E_bᵀ (σ_N = 1.0, one floating normalization factor per block);
  - Snyder: diag(σ_E) ρ diag(σ_E) + s_N² E Eᵀ, with σ_E = u · E and s_N = 1.17 %;
  - Dongwi: diag(σ_E) ρ diag(σ_E) + s_N² E Eᵀ, with σ_E = u · E and s_N = 1.34 %;
  - all blocks between data sets, including Snyder–Dongwi: zero.
  Each differential block is checked for symmetry and positive definiteness (Cholesky).
- Differential `/responses`: experimental = E, experimental_uncertainty = σ_E (absolute), simulated = C, simulated_uncertainty = 0.

## Assumptions

- Exercise 6's assumptions carry over, except the ENDF/B-VIII.1 comparison.
- Dongwi shape normalization: a free normalization factor with prior uncertainty s_N = 1.34 % (the normalization error removed from the shape file, release 4 Differential README), marginalized into the Dongwi covariance as D_σ ρ D_σ + s_N² E Eᵀ; no renormalization on the prior.
- Snyder shape normalization as in Exercise 6: s_N = 1.17 %.
- Snyder and Dongwi are independent: the release declares the two data sets correlated (`CorrelatedData`) but gives no covariance between them; this is an approximation, so none is applied.

## Tests

`test_ex8_prior.py` checks that the relative-to-absolute prior conversion scales diagonal and cross blocks by the prior means, on a synthetic covariance.

`test_ex8_observations.py` builds the observation file on a synthetic prior and checks: the 29-response integral inventory; the response order (Marini nu-bar, Marini PFNS, Keegan PFNS, Snyder, then Dongwi); that rows 0 to 53 match Exercise 4 exactly; that rows 0 to 2550 match Exercise 5 exactly; that rows 0 to 2641 match Exercise 6 exactly; that the differential blocks are mutually uncorrelated; the Marini PFNS, Keegan PFNS, Snyder and Dongwi values and covariance against the released data; that each PFNS, Snyder and Dongwi sensitivity lands on one prior state as C / μ; that the Snyder and Dongwi 20.54 MeV points are dropped; that Snyder and Dongwi selections with a two-hot row are rejected; that missing Snyder, Dongwi and PFNS files fail loudly; that the 27.88 MeV Marini PFNS block is dropped; that all Marini nu-bar points still pass; and that a PFNS selection with a non-one-hot row is rejected.
