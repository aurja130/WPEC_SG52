# Code

Reference set: [CONCEPTS](CONCEPTS.md) · [DEFINITIONS](DEFINITIONS.md) ·
[EXERCISES](EXERCISES.md) · [TESTS](TESTS.md)

Where each implemented or partial concept node lives. Paths are relative to the
repository root; symbols follow the path they belong to.

The exercise workflows are per-exercise copies of the same scripts.
`Exercise_4/` is the most general version (integral responses plus Marini
nu-bar); `Exercise_1/` to `Exercise_3/` differ in which responses they select.

## Release data

| Node | Code | Notes |
|---|---|---|
| `PriorCovariances` | `Exercise_3/ex3_prior.py` `DEFAULT_SOURCE_DIRECTORY` `validate_source_inventory` `load_mean` `load_covariance` `parse_covariance_filename` | Same in `ex1_prior.py` and `ex2_prior.py`. Points at release 3 |
| `IntegralSet` | `Exercise_3/ex3_observations.py` `OBSERVATION_COLUMNS` `read_csv` `load_observations` | Reads the release 3 columns `expt`, `expt_uncert`, `sim`, `sim_uncert` |
| `IntegralSensitivities` | `Exercise_3/ex3_observations.py` `load_sensitivities` | |
| `DifferentialSet` | `Exercise_6/ex6_observations.py` `DEFAULT_MARINI_PATH` `DEFAULT_MARINI_PFNS_PATH` `DEFAULT_KEEGAN_PFNS_PATH` `DEFAULT_SNYDER_PATH` `load_marini_nubar` `load_pfns` `load_snyder` `nullable_float_array_at` | Marini nu-bar, Marini and Keegan PFNS, Snyder shape; earlier exercises read subsets |
| `DifferentialSensitivities` | `Exercise_6/ex6_observations.py` `load_marini_nubar` `load_pfns` `load_snyder` `MARINI_SENSITIVITY_COLUMNS` `SNYDER_SENSITIVITY_COLUMNS` `PFNS_INCIDENT_BIN_COUNT` `PFNS_OUTGOING_GROUP_COUNT` | Nu-bar and Snyder 52 columns; PFNS $10 \times 51$ |
| `OutputTemplate` | `Exercise_3/export_ex3_excel.py` `TEMPLATE_PATH` `locate_mean_table` `locate_covariance_axes` `question_row` | Release 4 template, same in all four export scripts; data stay release 3 |

## Prior

| Node | Code | Notes |
|---|---|---|
| `StateVector` | `Exercise_3/ex3_prior.py` `QUANTITY_IDS` `QuantityLayout` `build_layout` | Rebuilt independently by `build_state_metadata` in each analysis and export script |
| `PriorMean` | `Exercise_3/ex3_prior.py` `load_mean` `write_prior` | |
| `AbsolutePriorCovariance` | `Exercise_3/ex3_prior.py` `load_covariance` | $\Sigma_i = D_{\mu_i} R_i D_{\mu_i}$ |

## Observations

| Node | Code | Notes |
|---|---|---|
| `ResponseSelection` | `Exercise_1/ex1_observations.py` `select_response_positions` `Exercise_2/ex2_observations.py` `select_response_positions` `Exercise_3/ex3_observations.py` `JEZEBEL_CRITICALITY_ID` `load_observations` | Exercise 3 takes every released response |
| `Discrepancy` | `Exercise_3/ex3_observations.py` `build_inputs` | `delta = experimental - simulated` |
| `SensitivityAlignment` | `Exercise_3/ex3_observations.py` `parameter_to_prior_index` `build_inputs` | |
| `AbsoluteSensitivity` | `Exercise_3/ex3_observations.py` `build_inputs` | $S = D_C\, s\, D_{\mu_i}^{-1}$ |
| `ObservationCovariance` | `Exercise_3/ex3_observations.py` `build_inputs` `write_observations` `Exercise_4/ex4_observations.py` `build_marini_inputs` `combine_inputs` `require_positive_definite` | Integral block $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$, checked against the components by the analysis; Marini block $D_{\sigma_E}\rho D_{\sigma_E}$ |
| `DifferentialObservations` | `Exercise_6/ex6_observations.py` `load_marini_nubar` `build_marini_inputs` `load_pfns` `build_pfns_inputs` `load_snyder` `build_snyder_inputs` `combine_inputs` | Rows after the 29 integral rows: Marini nu-bar, Marini PFNS, Keegan PFNS, Snyder. Exercises 4 and 5 hold the earlier subsets |
| `DifferentialSelection` | `Exercise_6/ex6_observations.py` `load_marini_nubar` `load_pfns` `load_snyder` `MARINI_ENERGY_LIMIT_MEV` `PFNS_ENERGY_LIMIT_MEV` `SNYDER_ENERGY_LIMIT_MEV` `MARINI_PFNS_PREFIX` `KEEGAN_PFNS_PREFIX` `SNYDER_RESPONSE_PREFIX` | Drops points above 20 MeV, with a zero sensitivity row or (PFNS) a `null` calculated value |
| `NubarAsTotal` | `Exercise_6/ex6_observations.py` `total_nubar_prior_index` | Same in Exercises 4 and 5 |
| `DifferentialAlignment` | `Exercise_6/ex6_observations.py` `load_marini_nubar` `build_marini_inputs` `load_pfns` `build_pfns_inputs` `load_snyder` `build_snyder_inputs` | Rejects rows that are not one-hot; nu-bar and Snyder reject a non-zero column 51; PFNS and Snyder check the one-hot state against an energy lookup |
| `PfnsObservationModel` | `Exercise_6/ex6_observations.py` `load_pfns` `build_pfns_inputs` `PfnsPoints` | Released block-normalized $C$; one-hot row on `94239_<slice MT>_<group>`, $S = C/\mu_i$; same in Exercise 5 |
| `CrossSectionShapeModel` | `Exercise_6/ex6_observations.py` `load_snyder` `build_snyder_inputs` `SNYDER_NORMALIZATION_UNCERTAINTY` | Snyder only; block $D_{\sigma_E}\rho D_{\sigma_E} + s_N^2 E E^\top$, `/responses/experimental_uncertainty` keeps the shape-only $\sigma_E$ |
| `DifferentialCovariance` | `Exercise_6/ex6_observations.py` `build_marini_inputs` `build_pfns_inputs` `build_snyder_inputs` `require_positive_definite` | One block per data set |
| `IndependentDataSets` | `Exercise_6/ex6_observations.py` `combine_inputs` | Block-diagonal over any number of data sets |

## GLLS update

| Node | Code | Notes |
|---|---|---|
| `InputCards` | `GLLS_code/src/input_parser.cpp` `parse_input` `read_dataset` `GLLS_code/src/main.cpp` `require_vector` `require_matrix` | |
| `ResponseCovariance` | `GLLS_code/src/glls.cpp` `glls` | |
| `CholeskySolve` | `GLLS_code/src/linSolve.cpp` `SPDSolver` | Eigen LLT |
| `PosteriorMean` | `GLLS_code/src/glls.cpp` `glls` | |
| `PosteriorCovariance` | `GLLS_code/src/glls.cpp` `glls` | |
| `PosteriorOutput` | `GLLS_code/src/output_hdf5.cpp` `write_dataset` `replace_dataset` | |

## Diagnostics

| Node | Code | Notes |
|---|---|---|
| `GllsReproduction` | `Exercise_3/analyze_ex3_results.py` `analyze` `relative_frobenius_difference` `max_abs_difference` | Report section "Direct GLLS reproduction" |
| `LinearizedResponses` | `Exercise_3/analyze_ex3_results.py` `analyze` `read_response_metadata` `Exercise_5/analyze_ex5_results.py` `chi2_per_point` `row_data_set_names` | Report section "All released responses"; Exercise 5 adds "Data set summary" (`data_set_summary.csv`) and "PFNS blocks" (`pfns_block_summary.csv`) and lists PFNS rows only in `response_summary.csv` |
| `UncertaintyReduction` | `Exercise_3/analyze_ex3_results.py` `analyze` `safe_std_from_cov` `grouped_indices` `make_plots` | Report sections "Uncertainty update summary" and "Response-variance decomposition" |
| `CovarianceHealth` | `Exercise_3/analyze_ex3_results.py` `matrix_symmetry_error` `eig_diagnostics` | |
| `PfnsChecks` | `Exercise_3/analyze_ex3_results.py` `PfnsRow` `analyze` | Report section "PFNS normalization / positivity" |
| `UncertaintyAudit` | `Exercise_3/analyze_ex3_results.py` `analyze` | Only in the Exercise 3 analysis; report section "Observation uncertainty" |
| `EndfComparison` | `Exercise_6/ex6_endf_reference.py` `main` `write_output` | Reference values and gate built; the comparison metrics in the analysis are planned |
| `ReferenceGroupValues` | `Exercise_6/ex6_endf_reference.py` `run_njoy` `read_njoy_input` `gendf_mf3` `errorr_mf3` `errorr_mf5` `slice_average` `build_library_values` `verify_endf_file` | NJOY work dirs `Exercise_6/ex6_njoy/`; output `Exercise_6/ex6_endf_reference.hdf5` |
| `ReproductionGate` | `Exercise_6/ex6_endf_reference.py` `reproduction_error` `is_reproduced` `enforce_gate` `REPRODUCTION_TOLERANCE` `EXPECTED_UNREPRODUCED` | Fails loudly if a QID outside the expected three stops reproducing |

## Submission

| Node | Code | Notes |
|---|---|---|
| `TemplateSelection` | `Exercise_3/export_ex3_excel.py` `template_cells` `build_template_selection` `TemplateSelection` | One 928-state selection in template axis order; the 51 omitted states must be exactly MT456 |
| `RelativeMeanAdjustment` | `Exercise_3/export_ex3_excel.py` `calculate_relative_outputs` | |
| `RelativePosteriorCovariance` | `Exercise_3/export_ex3_excel.py` `calculate_relative_outputs` `relative_covariance_block` `validate_relative_outputs` | Prior and posterior covariances both divided by the prior mean $\mu_i$ |
| `AbsoluteWorkbook` | `Exercise_3/export_ex3_excel.py` `populate_absolute_workbook` `add_state_values_sheet` `add_absolute_covariance_sheet` | |
| `UpdatedTemplate` | `Exercise_3/export_ex3_excel.py` `populate_relative_workbook` `populate_mean_sheet` `populate_covariance_sheet` `populate_questions_sheet` `append_relative_comment` `SCIENTIFIC_FORMAT` | Fills `prior_abs`, `prior_cov_rel_to_prior`, `posterior_rel_adjust`, `posterior_cov_rel_to_prior` and `Questions` |
