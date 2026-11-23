# SG52 Exercise 5: Pu-239 GLLS adjustment with Marini and Keegan PFNS

Exercise 5 adds two PFNS differential data sets, Marini PFNS (CEA, EXFOR 14684002) and Keegan PFNS (Chi-Nu, K.J. Kelly et al.; "Keegan" is the release's folder name), to the 29 integral responses and the 25 Marini nu-bar points of Exercise 4, giving m = 2551 = 29 integral + 25 Marini nu-bar + 1220 Marini PFNS + 1277 Keegan PFNS. The 979-state Pu-239 prior is the same as in Exercises 3 and 4.

Release data is read-only: `../SG52_materials/SG52_materials_release_4/`.

## Run

From the repository root (build `GLLS_code/build/nda` first if it is missing: `cmake --build GLLS_code/build`):

```bash
python3 Exercise_5/ex5_prior.py
python3 Exercise_5/ex5_observations.py
GLLS_code/build/nda Exercise_5/ex5_input.txt
python3 Exercise_5/analyze_ex5_results.py
python3 Exercise_5/export_ex5_excel.py
python3 -m pytest Exercise_5 -q
```

## Outputs

- `Exercise_5/ex5_prior.hdf5`: prior means and covariance.
- `Exercise_5/ex5_observations.hdf5`: `/delta`, `/cov`, `/sens`, `/responses/*` for the 2551 responses.
- `Exercise_5/ex5_results.hdf5`: GLLS posterior.
- `Exercise_5/ex5_analysis/`: analysis report, plots, `data_set_summary.csv` (per data set) and `pfns_block_summary.csv` (per PFNS block).
- `Exercise_5/Submission/Ex5_relative_results.xlsx` (release 4 output template) and `Exercise_5/Submission/Ex5_absolute_results.xlsx`.

## Response set

- Rows 0 to 28: the 29 integral responses, unchanged.
- Rows 29 to 53: `marini-nubar-00` to `marini-nubar-24`, in release order, as in Exercise 4.
- Rows 54 to 1273: `marini-pfns-0000` to `marini-pfns-1219`, in released order.
- Rows 1274 to 2550: `keegan-pfns-0000` to `keegan-pfns-1276`, in released order.

Marini PFNS selection: incident energy at or below 20 MeV, a non-zero sensitivity row and a calculated value. The 61 points of the 27.88 MeV block have no calculated value and zero sensitivity rows, so they are dropped; the observation builder prints kept and dropped points.

## Observation model

- Nu-bar (as Exercise 4): for Marini nu-bar point k and energy group g, S[k, `94239_00452_g`] = C_k · s_rel[k,g] / μ_prior[`94239_00452_g`]; residual δ_k = E_k − C_k, with values as released.
- PFNS: each point is its own observation with residual δ_k = E_k − C_k, where C_k is the released block-normalized value. Its sensitivity is the released one-hot row: a single non-zero entry on state `94239_<slice MT>_<outgoing group>`, the state of the PFNS slice holding E_in and the outgoing group holding E_out, with S = C_k / μ_prior. There is no block-normalization term and no free normalization factor.
- Covariance is block diagonal over the four data sets (integral, Marini nu-bar, Marini PFNS, Keegan PFNS):
  - integral block: diag(expt² + sim²), as in Exercise 3;
  - each differential block: diag(σ_E) ρ diag(σ_E), with σ_E = u · E (u relative, ρ from the release);
  - all blocks between data sets: zero.
  Each differential block is checked for symmetry and positive definiteness (Cholesky).
- Differential `/responses`: experimental = E, experimental_uncertainty = σ_E (absolute), simulated = C, simulated_uncertainty = 0.

## Assumptions

- PFNS calculated values are the released block-normalized values, used as released: no free normalization factor and no renormalization on the prior.
- PFNS sensitivities are the released one-hot rows, with no term for the block normalization, as released.
- Each PFNS set's covariance is diag(σ_E) ρ diag(σ_E) with σ_E = u · E, as for Marini nu-bar; no Peelle's Pertinent Puzzle correction.
- Independent data sets: zero covariance between the integral block, Marini nu-bar, Marini PFNS and Keegan PFNS, even though the two PFNS files share an EXFOR number.
- Exercise 4's assumptions carry over: the as-MT452 rule for Marini nu-bar (its sensitivity rows land on MT452, E and C used as released), no covariance between integral responses, sensitivity uncertainties not propagated, no calculation uncertainty for differential points.

## Tests

`test_ex5_prior.py` checks that the relative-to-absolute prior conversion scales diagonal and cross blocks by the prior means, on a synthetic covariance.

`test_ex5_observations.py` builds the observation file on a synthetic prior and checks: the 29-response integral inventory; the response order (Marini nu-bar, then Marini PFNS, then Keegan PFNS); that rows 0 to 53 match Exercise 4 exactly; that the differential blocks are mutually uncorrelated; the Marini PFNS and Keegan PFNS values and covariance against the released data; that each PFNS sensitivity lands on one prior state as C / μ; that the 27.88 MeV block is dropped; that all Marini nu-bar points still pass; that a PFNS selection with a non-one-hot row is rejected; and that a missing PFNS file fails loudly.
