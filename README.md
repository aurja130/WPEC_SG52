# WPEC SG52 nuclear data adjustment exercises

This repository demonstrates the work done by researchers at Uppsala University 
related to the OECD-NEA WPEC SG52 nuclear data adjustment exercises.

## GLLS adjustment tool

`GLLS_code/` contains the standalone C++ generalized least-squares adjustment
program. It has no dependency on the data or Python
workflows for WPEC SG52 exercises; prepare your own HDF5 inputs and input card file.

Build from the repository root:

```bash
cmake -S GLLS_code -B GLLS_code/build
cmake --build GLLS_code/build
```

Run it with an input file:

```bash
GLLS_code/build/nda path/to/input.txt
```

See [`GLLS_code/README.md`](GLLS_code/README.md) for build requirements, input
cards, and HDF5 dataset expectations.

## Exercise workflows

Run each workflow from the repository root with the sibling
`SG52_materials_release_2/` data directory available:

- [Exercise 1 — JEZEBEL criticality](Exercise_1/README.md)
- [Exercise 2 — JEZEBEL and EUCLID criticalities](Exercise_2/README.md)
- [Exercise 3 — all JEZEBEL and EUCLID integral responses](Exercise_3/README.md)
