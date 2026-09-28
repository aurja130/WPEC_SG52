# SG52 Exercise 3

Adjust the 979-state Pu-239 prior using **all 29 released integral responses** in
source order: JEZEBEL's criticality and three reaction-rate ratios, followed by
EUCLID's two criticalities, 15 neutron-leakage spectrum points, and eight
reaction-rate ratios. The release calls the 1x8 EUCLID configuration `8x1`.

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

The observation covariance uses the release-provided `total_uncert` for each
response without recomputing it from other columns. The release supplies no
between-response covariance, so using zero off-diagonal entries—including
between leakage-spectrum points—is an assumption of this workflow.

`ex3_results.hdf5` contains the GLLS posterior mean and covariance. The
`ex3_analysis/` directory contains a text report, response/state/family/QID
CSVs, PFNS normalization data, and four plots. The report reproduces the
multivariate GLLS update and its coupled residual identity. Its adjusted
responses are *linearized predictions*, not new transport simulations.

`Submission/Ex3_relative_results.xlsx` fills the official relative template
(928 representable states). `Submission/Ex3_absolute_results.xlsx` contains the
full 979-state means and prior/posterior absolute covariances, including the 51
MT456 values omitted from that template. Inspect the report's PFNS normalization
and positivity flags: linear GLLS imposes neither constraint. In the released
29-response run, the largest posterior PFNS slice normalization error is about
0.001565; do not interpret the posterior as exactly normalized.
