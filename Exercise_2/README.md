# SG52 Exercise 2

Adjust Pu-239 with three criticality responses: JEZEBEL PMF-001, EUCLID 3x2,
and EUCLID 8x1 (the release's name for the 1x8 configuration). Other JEZEBEL
and EUCLID responses are reserved for later exercises. The input data come
from `../SG52_materials/SG52_materials_release_3/`.

From the repository root, with `GLLS_code/build/nda` built and Python packages
`numpy`, `h5py`, `matplotlib`, and `openpyxl` available:

```bash
python Exercise_2/ex2_prior.py
python Exercise_2/ex2_observations.py
GLLS_code/build/nda Exercise_2/ex2_input.txt
python Exercise_2/analyze_ex2_results.py
python Exercise_2/export_ex2_excel.py
```

`ex2_prior.py` uses the same 979-state ENDF/B-VIII.0 prior as Exercise 1. It
scales each released relative covariance entry by both prior means before
writing absolute HDF5 covariance. `ex2_observations.py` aligns the selected
responses and relative sensitivities to that state, converts sensitivities to
absolute derivatives, and stores observed/simulated responses for diagnostics.
Each response's observation variance is `expt_uncert² + sim_uncert²`.

Assumptions: the release gives no covariance between responses, so the
observation covariance is diagonal; the released sensitivity uncertainties
(`sens_unc_rel.csv`) are not propagated.

Outputs: `ex2_results.hdf5`, diagnostics in `ex2_analysis/`, and in
`Submission/` the release 3 template (relative results normalized on the prior
mean, 11 significant digits) plus the full-state absolute workbook. Check the
analysis report for PFNS normalization and positivity; linear GLLS does not
enforce either constraint.
