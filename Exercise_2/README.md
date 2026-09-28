# SG52 Exercise 2

Adjust Pu-239 with three criticality responses: JEZEBEL PMF-001, EUCLID 3x2,
and EUCLID 8x1 (the release's name for the 1x8 configuration). Other JEZEBEL
and EUCLID responses are reserved for later exercises.

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
The released integral files provide individual response uncertainties, but no
between-response covariance; the observation covariance is diagonal. Treating
these responses as uncorrelated is an assumption of this workflow.

Outputs: `ex2_results.hdf5`, diagnostics in `ex2_analysis/`, and the NEA
relative-template and full-state absolute workbooks in `Submission/`. Check
the analysis report for PFNS normalization and positivity; linear GLLS does
not enforce either constraint.
