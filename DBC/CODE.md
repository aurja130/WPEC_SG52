# Code

Reference set: [CONCEPTS](CONCEPTS.md) · [DEFINITIONS](DEFINITIONS.md) ·
[EXERCISES](EXERCISES.md) · [TESTS](TESTS.md)

Where each implemented or partial concept node lives. Paths are relative to the
repository root; symbols follow the path they belong to.

The exercise workflows are per-exercise copies of the same scripts.
`Exercise_3/` is the most general version; `Exercise_1/` and `Exercise_2/`
differ in which responses they select.

## Release data

| Node | Code | Notes |
|---|---|---|
| `PriorCovariances` | `Exercise_3/ex3_prior.py` `DEFAULT_SOURCE_DIRECTORY` `validate_source_inventory` `load_mean` `load_covariance` `parse_covariance_filename` | Same in `ex1_prior.py` and `ex2_prior.py`. Points at release 3 |
| `IntegralSet` | `Exercise_3/ex3_observations.py` `OBSERVATION_COLUMNS` `read_csv` `load_observations` | Reads the release 3 columns `expt`, `expt_uncert`, `sim`, `sim_uncert` |
| `IntegralSensitivities` | `Exercise_3/ex3_observations.py` `load_sensitivities` | |
| `OutputTemplate` | `Exercise_3/export_ex3_excel.py` `TEMPLATE_PATH` `locate_mean_table` `locate_covariance_axes` `question_row` | Release 3 template |

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
| `ObservationCovariance` | `Exercise_3/ex3_observations.py` `build_inputs` `write_observations` | $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$; the Exercise 3 analysis checks it against the components |

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
| `LinearizedResponses` | `Exercise_3/analyze_ex3_results.py` `analyze` `read_response_metadata` | Report section "All released responses" |
| `UncertaintyReduction` | `Exercise_3/analyze_ex3_results.py` `analyze` `safe_std_from_cov` `grouped_indices` `make_plots` | Report sections "Uncertainty update summary" and "Response-variance decomposition" |
| `CovarianceHealth` | `Exercise_3/analyze_ex3_results.py` `matrix_symmetry_error` `eig_diagnostics` | |
| `PfnsChecks` | `Exercise_3/analyze_ex3_results.py` `PfnsRow` `analyze` | Report section "PFNS normalization / positivity" |
| `UncertaintyAudit` | `Exercise_3/analyze_ex3_results.py` `analyze` | Only in the Exercise 3 analysis; report section "Observation uncertainty" |

## Submission

| Node | Code | Notes |
|---|---|---|
| `TemplateSelection` | `Exercise_3/export_ex3_excel.py` `template_cells` `build_template_selection` `TemplateSelection` | One 928-state selection in template axis order; the 51 omitted states must be exactly MT456 |
| `RelativeMeanAdjustment` | `Exercise_3/export_ex3_excel.py` `calculate_relative_outputs` | |
| `RelativePosteriorCovariance` | `Exercise_3/export_ex3_excel.py` `calculate_relative_outputs` `relative_covariance_block` `validate_relative_outputs` | Prior and posterior covariances both divided by the prior mean $\mu_i$ |
| `AbsoluteWorkbook` | `Exercise_3/export_ex3_excel.py` `populate_absolute_workbook` `add_state_values_sheet` `add_absolute_covariance_sheet` | |
| `UpdatedTemplate` | `Exercise_3/export_ex3_excel.py` `populate_relative_workbook` `populate_mean_sheet` `populate_covariance_sheet` `populate_questions_sheet` `append_relative_comment` `SCIENTIFIC_FORMAT` | Fills `prior_abs`, `prior_cov_rel_to_prior`, `posterior_rel_adjust`, `posterior_cov_rel_to_prior` and `Questions` |
