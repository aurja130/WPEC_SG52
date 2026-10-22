# Exercises

Reference set: [CONCEPTS](CONCEPTS.md) · [CODE](CODE.md) ·
[DEFINITIONS](DEFINITIONS.md) · [TESTS](TESTS.md)

One section per SG52 exercise from the specification. Each section is the
contract for its workflow: data used, assumptions, acceptance checks, the
result today, the concept nodes it exercises, and comments. Comments are dated
and signed; any agent may add one.

Acceptance checks shared by every exercise, from the method rules:

- Release 3 data, the experimental and calculation uncertainties (never
  `total_uncert`), and absolute GLLS.
- Relative mean adjustment and posterior relative covariance normalized on the
  prior mean.
- The release 3 output template, including the prior and questions sheets, in
  scientific format with 11 significant digits.
- The analysis report states PFNS normalization and positivity flags, and every
  assumption.
- The workflow reruns from the repository root and the exercise's tests pass.

## Exercise 1 · JEZEBEL criticality

**Data:** Prior from the release covariances. One integral response: JEZEBEL
$k_\text{eff}$ (`PU-MET-FAST-001-001-s`). Workflow in
[`Exercise_1/`](../Exercise_1/README.md).

**Assumptions:** None beyond the method.

**Acceptance:** The shared checks.

**Result today:** Release 2 data. Prior C/E 1.00044, linearized posterior C/E
1.0000055. Largest PFNS normalization deviation $1.1 \times 10^{-6}$ (flagged);
no negative states. Observation variance from `total_uncert`; posterior
relative covariance normalized on the posterior mean; release 2 template.
Submitted to the NEA; resubmission requested (feedback 2026-09-30).

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `AbsolutePriorCovariance` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance`

**Comments:** —

## Exercise 2 · JEZEBEL and EUCLID criticality

**Data:** Prior as Exercise 1. Three integral responses: JEZEBEL
$k_\text{eff}$, EUCLID 3x2 and 1x8 $k_\text{eff}$ (`euclid-3x2-crit`,
`euclid-8x1-crit`). Workflow in [`Exercise_2/`](../Exercise_2/README.md).

**Assumptions:** No covariance between the three responses (diagonal
observation covariance).

**Acceptance:** The shared checks.

**Result today:** Release 2 data. Linearized posterior $k_\text{eff}$: JEZEBEL
1.000085 (measured 1, prior 1.00044); EUCLID 3x2 1.000444 (measured 1.00029,
prior 1.00012); EUCLID 1x8 0.999397 (measured 1.00038, prior 0.99838). Largest
PFNS normalization deviation $1.6 \times 10^{-4}$ (flagged); no negative states.
Same three method-rule gaps as Exercise 1. Submitted; resubmission requested.

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `UncorrelatedResponses` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance`

**Comments:** —

## Exercise 3 · All integral responses

**Data:** Prior as Exercise 1. All 29 integral responses in released order:
JEZEBEL $k_\text{eff}$ and three reaction-rate ratios; EUCLID two
$k_\text{eff}$, 15 neutron-leakage-spectrum points and eight reaction-rate
ratios. Workflow in [`Exercise_3/`](../Exercise_3/README.md).

**Assumptions:** No covariance between responses, including between
neutron-leakage-spectrum points.

**Acceptance:** The shared checks.

**Result today:** Release 2 data. Largest PFNS normalization deviation
$1.57 \times 10^{-3}$ (flagged); no negative states. The uncertainty audit
finds all 15 EUCLID leakage-spectrum `total_uncert` values differ from the
quadrature of their components; they are still used. Same three method-rule
gaps as Exercise 1. Submitted; resubmission requested.

**Concepts:** `ResponseSelection` `Discrepancy` `SensitivityAlignment` `AbsoluteSensitivity` `ObservationCovariance` `UncorrelatedResponses` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `UncertaintyAudit` `PfnsChecks` `RelativePosteriorCovariance`

**Comments:** —

## Exercise 4 · Add Marini nu-bar

**Data:** Exercise 3's integral responses plus Marini nu-bar (EXFOR
14799002) with its differential sensitivities.

**Assumptions:** To be fixed before work starts.

**Acceptance:** The shared checks; to be extended before work starts.

**Result today:** Not started.

**Concepts:** `DifferentialSet` `DifferentialSensitivities` `DifferentialObservations`

**Comments:** —

## Exercise 5 · Add Marini and Keegan PFNS

**Data:** Exercise 4's data plus Marini PFNS (EXFOR 14684002) and Keegan PFNS.

**Assumptions:** To be fixed before work starts.

**Acceptance:** The shared checks; to be extended before work starts.

**Result today:** Not started.

**Concepts:** `DifferentialSet` `DifferentialSensitivities` `DifferentialObservations` `PfnsChecks`

**Comments:** —

## Exercise 6 · Add Snyder, compare with ENDF/B-VIII.1

**Data:** Exercise 5's data plus the Snyder fission ratio (EXFOR 14721002).
ENDF/B-VIII.1 Pu-239 for comparison.

**Assumptions:** To be fixed before work starts.

**Acceptance:** The shared checks, plus a comparison with ENDF/B-VIII.1 (the
specification expects them to be consistent); to be extended before work
starts.

**Result today:** Not started.

**Concepts:** `DifferentialObservations` `EndfComparison`

**Comments:** —

## Exercise 7 · SNEAK-7A/B validation

**Data:** SNEAK-7A/B $k_\text{eff}$ and spectral indices (IRPHE
SNEAK-LMFR-EXP-001) with the release's models, and the posterior of the
preceding adjustment.

**Assumptions:** To be fixed before work starts. **Open:** transport
calculation with an adjusted library, or a linear estimate from SNEAK
sensitivities.

**Acceptance:** C/E of every SNEAK response with prior and adjusted data;
to be extended before work starts.

**Result today:** Not started.

**Concepts:** `ValidationSet` `AdjustedLibrary` `SneakCalculation` `SneakComparison`

**Comments:** —

## Exercise 8 · Add Dongwi

**Data:** Exercise 6's data plus the Dongwi fission ratio (EXFOR 14851002).

**Assumptions:** To be fixed before work starts.

**Acceptance:** The shared checks; to be extended before work starts.

**Result today:** Not started.

**Concepts:** `DifferentialSet` `DifferentialObservations`

**Comments:** —
