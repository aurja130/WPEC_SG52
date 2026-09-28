# GLLS adjustment executable

This directory contains the standalone C++20 GLLS program. It reads user-
provided HDF5 datasets from an input card file, runs the adjustment, and writes
the posterior datasets to the requested HDF5 output path.

## Requirements

- CMake 3.26 or newer
- A C++20 compiler
- Eigen3
- HighFive

Configure and build from the repository root:

```bash
cmake -S GLLS_code -B GLLS_code/build
cmake --build GLLS_code/build
```

Run the executable from the repository root (paths in the input file are
resolved relative to the current working directory):

```bash
GLLS_code/build/nda path/to/input.txt
```

## Input cards

The input file must provide exactly one card of each type:

- `prmean`: prior mean vector, shape (n,)
- `prcov`: prior covariance matrix, shape (n, n)
- `obsdelta`: observation discrepancy vector, shape (m,)
- `obscov`: observation covariance matrix, shape (m, m)
- `sens`: sensitivity matrix, shape (m, n)
- `psmean`: destination dataset for the posterior mean. If not existent, it will be created.
- `pscov`: destination dataset for the posterior covariance. If not existent, it will be created.

Each card has a filepath, an HDF5 dataset path, and an `END` marker. Example:

```text
CARD prmean
filepath prior.hdf5
dataset /mean/values
END

CARD prcov
filepath prior.hdf5
dataset /cov/values
END

CARD obsdelta
filepath observations.hdf5
dataset /delta/values
END

CARD obscov
filepath observations.hdf5
dataset /cov/values
END

CARD sens
filepath observations.hdf5
dataset /sens/values
END

CARD psmean
filepath posterior.hdf5
dataset /mean/values
END

CARD pscov
filepath posterior.hdf5
dataset /covariance/values
END
```

All input numeric datasets must use float64/double. `prmean` and `obsdelta`
must be rank-1 vectors; `prcov`, `obscov`, and `sens` must be rank-2 matrices.
The posterior output datasets are float64. The two output cards may target
different datasets in the same HDF5 file.

No exercise-specific data or prior is bundled with this executable.
