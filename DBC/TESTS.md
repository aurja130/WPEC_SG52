# Tests

Reference set: [CONCEPTS](CONCEPTS.md) · [CODE](CODE.md) ·
[DEFINITIONS](DEFINITIONS.md) · [EXERCISES](EXERCISES.md)

Every test, what it checks and the concept nodes it guards. Run all with
`pytest Exercise_1 Exercise_2 Exercise_3` from the repository root. The GLLS
program has no tests yet.

"Needs" says what a test reads: **synthetic** tests write their own inputs;
**release 3** tests read the release data directly and fail if it is missing.

| Test | Needs | Checks | Concepts |
|---|---|---|---|
| `Exercise_1/test_ex1_prior.py::PriorCovarianceUnitsTest` | synthetic | The prior builder scales diagonal and cross blocks of the relative covariance by both prior means, in state-vector order | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_2/test_ex2_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 2 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_3/test_ex3_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 3 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_2/test_ex2_observations.py::Exercise2ObservationTest` | synthetic | The three criticality responses keep released order; discrepancy is $E - C$; observation covariance is $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$; absolute sensitivities are $C s / \mu$; other nuclides are dropped | `ResponseSelection` `Discrepancy` `CombinedVariance` `AbsoluteSensitivity` |
| `Exercise_3/test_ex3_observations.py::Exercise3ObservationTest` | release 3 | All 29 responses in released order with unique IDs; Pu-239 parameters map to distinct states; stored values and uncertainties match the release; observation covariance is $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$ and no total-uncertainty dataset is written; states without sensitivity get zero columns | `ResponseSelection` `SensitivityAlignment` `AbsoluteSensitivity` `CombinedVariance` |
