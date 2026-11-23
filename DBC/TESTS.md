# Tests

Reference set: [CONCEPTS](CONCEPTS.md) · [CODE](CODE.md) ·
[DEFINITIONS](DEFINITIONS.md) · [EXERCISES](EXERCISES.md)

Every test, what it checks and the concept nodes it guards. Run all with
`pytest Exercise_1 Exercise_2 Exercise_3 Exercise_4 Exercise_5` from the repository root. The GLLS
program has no tests yet.

"Needs" says what a test reads: **synthetic** tests write their own inputs;
**release 3** and **release 4** tests read that release's data directly and fail if it is missing.

| Test | Needs | Checks | Concepts |
|---|---|---|---|
| `Exercise_1/test_ex1_prior.py::PriorCovarianceUnitsTest` | synthetic | The prior builder scales diagonal and cross blocks of the relative covariance by both prior means, in state-vector order | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_2/test_ex2_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 2 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_3/test_ex3_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 3 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_2/test_ex2_observations.py::Exercise2ObservationTest` | synthetic | The three criticality responses keep released order; discrepancy is $E - C$; observation covariance is $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$; absolute sensitivities are $C s / \mu$; other nuclides are dropped | `ResponseSelection` `Discrepancy` `CombinedVariance` `AbsoluteSensitivity` |
| `Exercise_3/test_ex3_observations.py::Exercise3ObservationTest` | release 3 | All 29 responses in released order with unique IDs; Pu-239 parameters map to distinct states; stored values and uncertainties match the release; observation covariance is $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$ and no total-uncertainty dataset is written; states without sensitivity get zero columns | `ResponseSelection` `SensitivityAlignment` `AbsoluteSensitivity` `CombinedVariance` |
| `Exercise_4/test_ex4_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 4 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_4/test_ex4_observations.py::ExerciseFourObservationTest` | release 3 | The 29 integral rows of discrepancy, sensitivity and covariance equal Exercise 3's exactly; the 25 Marini points follow as `marini-nubar-00`…`24` with released $E$, $C$ and $\sigma_E = uE$; each Marini sensitivity row has one entry, on MT452, equal to $C/\mu$, and every MT456 column is zero; the Marini covariance block is $D_{\sigma_E}\rho D_{\sigma_E}$ and positive definite, the integral–Marini blocks zero; a non-zero column 51 or a row that is not one-hot is rejected, a point above 20 MeV is dropped, a missing file fails | `DifferentialSelection` `NubarAsTotal` `DifferentialAlignment` `DifferentialCovariance` `IndependentDataSets` `Discrepancy` `AbsoluteSensitivity` |
| `Exercise_5/test_ex5_prior.py::PriorCovarianceUnitsTest` | synthetic | Same as the Exercise 1 prior test, on the Exercise 5 copy | `AbsolutePriorCovariance` `StateVector` |
| `Exercise_5/test_ex5_observations.py::ExerciseFiveObservationTest` | release 4 | Rows 0–53 (discrepancy, sensitivity, responses, covariance) equal Exercise 4's builder output exactly; `marini-pfns-0000`…`1219` and `keegan-pfns-0000`…`1276` follow in released order with released $E$, $C$ and $\sigma_E = uE$; each PFNS sensitivity row has one entry, $C/\mu$, on the state found by looking up its energies in the released limits, and every MT456 column is zero; each PFNS covariance block is $D_{\sigma_E}\rho D_{\sigma_E}$ and all blocks between the four data sets are zero; the 61 Marini PFNS points of the 27.88 MeV block are dropped; a row that is not one-hot is rejected, a missing PFNS file fails | `DifferentialSelection` `DifferentialAlignment` `PfnsObservationModel` `DifferentialCovariance` `IndependentDataSets` `Discrepancy` `AbsoluteSensitivity` |
