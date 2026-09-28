# SG52 Exercise 1

Adjust the 979-state Pu-239 prior using the JEZEBEL PMF-001 criticality
response (`PU-MET-FAST-001-001-s`). The input data come from the sibling
`SG52_materials_release_2/` directory.

From the repository root, with `GLLS_code/build/nda` built and Python packages
`numpy`, `h5py`, `matplotlib`, and `openpyxl` available:

```bash
python Exercise_1/ex1_prior.py
python Exercise_1/ex1_observations.py
GLLS_code/build/nda Exercise_1/ex1_input.txt
python Exercise_1/analyze_ex1_results.py
python Exercise_1/export_ex1_excel.py
```

`ex1_prior.py` reads the released Pu-239 means and relative covariance blocks,
scales each covariance entry by both prior means to obtain an absolute
covariance, and writes `ex1_prior.hdf5`. The state vector contains 459 ordinary
quantity values, 510 PFNS values, and 10 mubar values. `ex1_observations.py`
selects the JEZEBEL criticality row and its relative sensitivities, maps the
Pu-239 columns to the prior ordering, converts them to absolute response
derivatives, and writes `ex1_observations.hdf5`. Its observation variance is
the square of the release-provided `total_uncert`.

The GLLS executable writes the posterior mean and covariance to
`ex1_results.hdf5`. `ex1_analysis/` contains the report, state/family/QID CSVs,
PFNS normalization checks, and plots. The adjusted criticality value reported
there is a linearized prediction, not a new transport calculation.

`Submission/Ex1_relative_results.xlsx` fills the official relative output
template, which represents 928 states. `Submission/Ex1_absolute_results.xlsx`
retains all 979 states and the full prior/posterior absolute covariances,
including the 51 MT456 values absent from that template. Linear GLLS does not
enforce PFNS normalization or positivity; inspect the analysis report before
using the posterior as physical data.
