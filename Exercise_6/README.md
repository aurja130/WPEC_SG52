# SG52 Exercise 6: Pu-239 GLLS adjustment with Snyder fission cross section and an ENDF/B-VIII.1 comparison

Exercise 6 adds the Snyder fission cross section shape data set (EXFOR 14721002, release 4) to the data of Exercise 5, giving m = 2642 = 2551 + 91 Snyder points. The 2551 Exercise 5 responses are unchanged: 29 integral + 25 Marini nu-bar + 1220 Marini PFNS + 1277 Keegan PFNS. The 979-state Pu-239 prior is the same as in Exercises 3 to 5.

Exercise 6 also compares the posterior with the ENDF/B-VIII.1 Pu-239 evaluation, processed with NJOY2016 next to ENDF/B-VIII.0.

Release data is read-only: `../SG52_materials/SG52_materials_release_4/`.

## Run

From the repository root (build `GLLS_code/build/nda` first if it is missing: `cmake --build GLLS_code/build`):

```bash
python3 Exercise_6/ex6_prior.py
python3 Exercise_6/ex6_observations.py
GLLS_code/build/nda Exercise_6/ex6_input.txt
python3 Exercise_6/ex6_endf_reference.py
python3 Exercise_6/analyze_ex6_results.py
python3 Exercise_6/export_ex6_excel.py
python3 -m pytest Exercise_6 -q
```

`ex6_endf_reference.py` runs NJOY twice (ENDF/B-VIII.0 and ENDF/B-VIII.1); it takes about 5 minutes.

`python3 Exercise_6/ex6_endf_reference.py --skip-njoy` reuses the existing NJOY work dirs in `Exercise_6/ex6_njoy/` instead of rerunning NJOY.

## Requirements for the reference step

- `njoy` (NJOY2016, BSD-3-Clause license, https://github.com/njoy/NJOY2016) on `PATH`.
- The two ENDF files in `Resources/` (git-ignored), with their NNDC sources and sha256:
  - `Resources/ENDF-B-VIII.0/n-094_Pu_239.endf`, sha256 `eae697df932ab4635d742123fc476b110271f92689083c0133527f429a48e684`, from https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip;
  - `Resources/ENDF-B-VIII.1/n-094_Pu_239.endf`, sha256 `7e298d9edc2fd2e956f1ef4bd9f20d7c0d8185294e7fb7016872bed249cda127`, from https://www.nndc.bnl.gov/endf-releases/releases/B-VIII.1/neutrons/neutrons-version.VIII.1.tar.gz.

## Outputs

- `Exercise_6/ex6_prior.hdf5`: prior means and covariance.
- `Exercise_6/ex6_observations.hdf5`: `/delta`, `/cov`, `/sens`, `/responses/*` for the 2642 responses.
- `Exercise_6/ex6_results.hdf5`: GLLS posterior.
- `Exercise_6/ex6_endf_reference.hdf5`: ENDF/B-VIII.0 and ENDF/B-VIII.1 reference group values, per-QID reproduction error and gate flag.
- `Exercise_6/ex6_njoy/`: NJOY work directories for the two libraries.
- `Exercise_6/ex6_analysis/`: analysis report, plots, `data_set_summary.csv`, `pfns_block_summary.csv`, `endf_comparison_states.csv` (per-state values), `endf_comparison_qids.csv` (per-QID reproduction and gate), `target_vs_adjustment.png`.
- `Exercise_6/Submission/Ex6_relative_results.xlsx` (release 4 output template) and `Exercise_6/Submission/Ex6_absolute_results.xlsx`.

## Response set

- Rows 0 to 28: the 29 integral responses, unchanged.
- Rows 29 to 53: `marini-nubar-00` to `marini-nubar-24`, in release order.
- Rows 54 to 1273: `marini-pfns-0000` to `marini-pfns-1219`, in released order.
- Rows 1274 to 2550: `keegan-pfns-0000` to `keegan-pfns-1276`, in released order.
- Rows 2551 to 2641: `snyder-00` to `snyder-90`, in released index order.

Snyder selection: incident energy at or below 20 MeV and a non-zero sensitivity row. The 92nd point (20.54 MeV) has a zero sensitivity row and is dropped.

## Observation model

- Nu-bar and PFNS: as in Exercise 5 (as-MT452 rule for Marini nu-bar; PFNS one-hot rows with S = C_k / μ_prior; no block-normalization term in the sensitivity; one floating normalization factor per PFNS block with σ_N = 1.0 (100 %) in the covariance).
- Snyder: each point is its own observation with residual δ_k = E_k − C_k, where C_k is the released ENDF/B-VIII.0 MT18 value. Its sensitivity is the released one-hot row: a single non-zero entry on `94239_00018_<group>`, the group holding E_in, with S = C_k / μ_prior.
- Covariance is block diagonal over the five data sets (integral, Marini nu-bar, Marini PFNS, Keegan PFNS, Snyder):
  - integral block: diag(expt² + sim²), as in Exercise 3;
  - Marini nu-bar, Marini PFNS, Keegan PFNS: diag(σ_E) ρ diag(σ_E), with σ_E = u · E (u relative, ρ from the release); Marini PFNS and Keegan PFNS additionally σ_N² Σ_b E_b E_bᵀ (σ_N = 1.0, one floating normalization factor per block);
  - Snyder: diag(σ_E) ρ diag(σ_E) + s_N² E Eᵀ, with σ_E = u · E and s_N = 1.17 %;
  - all blocks between data sets: zero.
  Each differential block is checked for symmetry and positive definiteness (Cholesky).
- Differential `/responses`: experimental = E, experimental_uncertainty = σ_E (absolute), simulated = C, simulated_uncertainty = 0.

## ENDF/B-VIII.1 comparison

- Reference group values: GENDF (GROUPR) MF3 for cross sections and nu-bar; ERRORR MF34 output for mubar; ERRORR MF35 output spectra for PFNS, each PFNS slice being the trapezoid average over the input's `efmean` incident energies inside the slice's range (bounds included). The same procedure is applied to ENDF/B-VIII.1.
- Reproduction gate: a QID enters the comparison only if the ENDF/B-VIII.0 reference group values reproduce the released prior means of that QID to 10⁻⁶ of the QID's largest value. QIDs that fail the gate are listed with their reproduction error and not compared; the PFNS slices 01318, 01518 and 01618 are excluded by the gate.
- Target adjustment: t = (x⁽¹⁾ − μ_i) / μ_i per state, the relative change from the prior to the ENDF/B-VIII.1 reference group values.
- Relative adjustment: r = (μ_f − μ_i) / μ_i per state, the relative change from the prior to the posterior.
- Consistency pull: z = (x⁽¹⁾ − μ_f) / σ_f per state, how many posterior standard deviations the ENDF/B-VIII.1 value lies from the posterior mean.
- Moved toward ENDF/B-VIII.1: |μ_f − x⁽¹⁾| < |μ_i − x⁽¹⁾|. Reported per compared QID and in total as the number of states moved toward, out of the states where ENDF/B-VIII.1 differs from the prior (x⁽¹⁾ ≠ μ_i) and the update changed the mean (μ_f ≠ μ_i), with the number of differing states alongside; together with the number of states with |z| ≤ 1 and |z| ≤ 2. The report flags when the posterior is less consistent with VIII.1 than the prior and when fewer than half the changed states moved toward VIII.1.

## Assumptions

- Exercise 5's assumptions carry over.
- PFNS: one floating normalization factor per block (kept points sharing one released incident energy), σ_N = 1.0 (100 %), marginalized into the covariance as σ_N² Σ_b E_b E_bᵀ. Captain decision 2026-11-25, after the 2026-11-24 coordinator feedback (`feedback_on_v4_submission.pdf`): PFNS are shape data.
- Snyder shape normalization: a free normalization factor with prior uncertainty s_N = 1.17 % (the normalization error removed from the shape file, release 4 Differential README), marginalized into the Snyder covariance as D_σ ρ D_σ + s_N² E Eᵀ; no renormalization on the prior.
- Snyder is independent of every other data set; Dongwi is not used.
- Reference group values as above; the same procedure is applied to ENDF/B-VIII.1 although its PFNS incident grid differs from ENDF/B-VIII.0's.
- Reproduction gate as above: every cross-section, nu-bar and mubar QID reproduces exactly; the PFNS slices 01318, 01518 and 01618 are excluded by the gate and listed as not compared.
- ENDF/B-VIII.1's ERRORR cross-section output has no MT17 or MT37; the GENDF tape is the source for cross sections.

## Tests

`test_ex6_prior.py` checks that the relative-to-absolute prior conversion scales diagonal and cross blocks by the prior means, on a synthetic covariance.

`test_ex6_observations.py` builds the observation file on a synthetic prior and checks: the 29-response integral inventory; the response order (Marini nu-bar, Marini PFNS, Keegan PFNS, then Snyder); that rows 0 to 53 match Exercise 4 exactly; that rows 0 to 2550 match Exercise 5 exactly; that the differential blocks are mutually uncorrelated; the Marini PFNS, Keegan PFNS and Snyder values and covariance against the released data; that each PFNS and Snyder sensitivity lands on one prior state as C / μ; that the Snyder 20.54 MeV point is dropped; that a Snyder selection with a two-hot row is rejected; that the 27.88 MeV block is dropped; that all Marini nu-bar points still pass; that a PFNS selection with a non-one-hot row is rejected; and that missing PFNS and Snyder files fail loudly.

`test_ex6_endf_reference.py` checks the ENDF parsing (`fnum` exponent forms), the selection of the Legendre-0, first-sigma-zero data for each group, the ERRORR MF3 and MF5 readers, the single-spectrum and trapezoid-average slice rules (including unequal spacing, bounds included and outside points excluded), the failure on an empty slice, the reproduction gate at its tolerance, the loud failure when a QID that passed on ENDF/B-VIII.0 no longer reproduces, the reporting of an expected unreproduced quantity without raising, and the output shapes and flags.
