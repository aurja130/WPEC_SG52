# SG52 Exercise 3

Adjust the 979-state Pu-239 prior using **all 29 released integral responses** in
source order: JEZEBEL's criticality and three reaction-rate ratios, followed by
EUCLID's two criticalities, 15 neutron-leakage spectrum points, and eight
reaction-rate ratios. The release calls the 1x8 EUCLID configuration `8x1`.
The input data come from the sibling `SG52_materials_release_3/` directory.

From the repository root, with `GLLS_code/build/nda` built and Python packages
`numpy`, `h5py`, `matplotlib`, and `openpyxl` installed:

```bash
python Exercise_3/ex3_prior.py
python Exercise_3/ex3_observations.py
GLLS_code/build/nda Exercise_3/ex3_input.txt
python Exercise_3/analyze_ex3_results.py
python Exercise_3/export_ex3_excel.py
```

`ex3_prior.py` converts the released *relative* covariance blocks to absolute
covariance by multiplying each entry by its two prior state means. It writes
`ex3_prior.hdf5`. `ex3_observations.py` aligns the JEZEBEL and EUCLID sensitivity
columns to that prior and converts relative sensitivities to absolute response
derivatives. It writes `ex3_observations.hdf5`, including response IDs and both
experimental and simulated values/uncertainties. Only Pu-239 parameters are
adjusted; sensitivities for other nuclides are outside this state vector.

Each response's observation variance is `expt_uncert² + sim_uncert²` (release
3 dropped the earlier `total_uncert` column, which overstated the 15 EUCLID
leakage-spectrum uncertainties). Assumptions: the release
supplies no between-response covariance, so off-diagonal entries are zero,
including between leakage-spectrum points; the released sensitivity
uncertainties (`sens_unc_rel.csv`) are not propagated.

`ex3_results.hdf5` contains the GLLS posterior mean and covariance. The
`ex3_analysis/` directory contains a text report, response/state/family/QID
CSVs, PFNS normalization data, and four plots. The report reproduces the
multivariate GLLS update and its coupled residual identity. Its adjusted
responses are *linearized predictions*, not new transport simulations.

`Submission/Ex3_relative_results.xlsx` fills the release 3 output template
(928 states): questions, absolute prior mean, prior and posterior relative
covariances normalized on the prior mean, and relative mean adjustments, in
scientific format with 11 significant digits. `Submission/Ex3_absolute_results.xlsx`
contains the full 979-state means and prior/posterior absolute covariances,
including the 51 MT456 values omitted from the template. Inspect the report's
PFNS normalization and positivity flags: linear GLLS imposes neither
constraint, so do not interpret the posterior as exactly normalized.
