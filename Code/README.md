# WPEC SG52 utilities

## Exercise 1 Excel export

`python/exercise_1/export_ex1_excel.py` converts the validated 979-state Exercise 1 HDF5 prior/posterior data into:

- `Exercise_1/Submission/Ex1_relative_results.xlsx`: the supplied NEA template populated with relative mean adjustments and posterior relative covariance blocks;
- `Exercise_1/Submission/Ex1_absolute_results.xlsx`: all 979 absolute state values plus complete prior and posterior covariance matrices.

The script performs no GLLS calculation. Its editable path and filename constants are in the configuration section at the top of the file. It requires Python with `h5py`, `numpy`, and `openpyxl`; run it directly without arguments:

```bash
python Code/python/exercise_1/export_ex1_excel.py
```

The exporter validates input dimensions, canonical state coverage, normalization round trips, covariance symmetry, template headers, and saved workbook sheet names. Exact-zero relative denominators are written as the text `NaN`; unused MT251 template rows remain blank.
