# WPEC SG52 GLLS adjustment tool

`GLLS_code/` contains the standalone C++ generalized least-squares adjustment
program. It has no dependency on this repository's Exercise 1 data or Python
workflows; prepare your own HDF5 inputs and input card file.

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

`Exercise_1/` is a local, git-ignored workspace for project-specific data and
Python utilities; its contents are not part of the standalone GLLS tool or
tracked in this repository.
