# WPEC SG52 utilities

## Exercise 1 prior builder

`python/exercise_1/ex1_prior.py` converts the released SG52 Pu-239 plaintext
means and relative covariance blocks directly into `Exercise_1/ex1_prior.hdf5`.
By default it reads `SG52_materials_release_2/Covariances/plaintext` from the
repository's sibling directory; `--source-directory` and `--output` override
these paths.

Run it with Python containing `h5py` and `numpy`:

```bash
python Code/python/exercise_1/ex1_prior.py
```

The output contains the canonical 979-state ordering in
`/mean/row_indices`, `/cov/row_indices`, and `/cov/col_indices`; the rank-1
prior mean is in `/mean/values`, and the relative covariance matrix is in
`/cov/values`. Missing covariance blocks in the SG52 release are stored as
zeros.

## Exercise 1 observation builder

`python/exercise_1/ex1_observations.py` converts the released JEZEBEL
observation and relative-sensitivity CSV data directly into
`Exercise_1/ex1_observations.hdf5`. It reads the prior means and canonical
state ordering from `Exercise_1/ex1_prior.hdf5`; `--source-directory`,
`--prior`, and `--output` override the defaults.

Run the prior builder first, then:

```bash
python Code/python/exercise_1/ex1_observations.py
```

Exercise 1 uses the `PU-MET-FAST-001-001-s` criticality response specified by
the SG52 exercise document. Its response ID indexes `/delta/values` and both
axes of `/cov/values`. It is also the row index of `/sens/values`; the
sensitivity column indices are the prior's 979 state indices. Released
relative sensitivities are converted to absolute response derivatives using
the simulated response and prior means.

## Exercise 1 Excel export

`python/exercise_1/export_ex1_excel.py` converts the validated 979-state Exercise 1 HDF5 prior/posterior data into:

- `Exercise_1/Submission/Ex1_relative_results.xlsx`: the supplied NEA template populated with relative mean adjustments and posterior relative covariance blocks;
- `Exercise_1/Submission/Ex1_absolute_results.xlsx`: all 979 absolute state values plus complete prior and posterior covariance matrices.

The script performs no GLLS calculation. Its editable path and filename constants are in the configuration section at the top of the file. It requires Python with `h5py`, `numpy`, and `openpyxl`; run it directly without arguments:

```bash
python Code/python/exercise_1/export_ex1_excel.py
```

The exporter validates input dimensions, canonical state coverage, normalization round trips, covariance symmetry, template headers, and saved workbook sheet names. Exact-zero relative denominators are written as the text `NaN`; unused MT251 template rows remain blank.
