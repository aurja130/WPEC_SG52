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

Questions sheet answers, shared by Exercises 1–3 (Captain, 2026-10-22):

1. Input covariances: yes, the released covariances are relative; each entry
   is multiplied by both prior means to give the absolute prior covariance.
2. GLLS form: absolute.
3. Normalization in relative GLLS: not applicable. Every GLLS term is
   absolute: discrepancy $E - C$, observation covariance
   $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$, prior covariance; relative
   sensitivities are made absolute with $C$ and the prior mean.
4. Posterior covariance normalized on the prior mean: yes.
5. Sensitivity uncertainties: no, they are not propagated (assumption).

## Exercise 1 · JEZEBEL criticality

**Data:** Prior from the release covariances. One integral response: JEZEBEL
$k_\text{eff}$ (`PU-MET-FAST-001-001-s`). Workflow in
[`Exercise_1/`](../Exercise_1/README.md).

**Assumptions:** Sensitivity uncertainties are not propagated.

**Acceptance:** The shared checks.

**Result today:** Release 3 data and template, all method rules met
(2026-10-22). C/E prior 1.00044, linearized posterior 1.00000554. Largest
PFNS normalization deviation $1.10 \times 10^{-6}$ (flagged); no negative
states. Same posterior as the release 2 run within $4 \times 10^{-11}$ in
relative adjustment (`total_uncert` was the component quadrature here); only
the reporting changed. Packaged as `UU_Erik_Aurora_SG52_v3`; the release 2
submission is kept as `_v2`. `_v3` received by the coordinators
(Andry Monlon, 2026-10-23).

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `AbsolutePriorCovariance` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** —

## Exercise 2 · JEZEBEL and EUCLID criticality

**Data:** Prior as Exercise 1. Three integral responses: JEZEBEL
$k_\text{eff}$, EUCLID 3x2 and 1x8 $k_\text{eff}$ (`euclid-3x2-crit`,
`euclid-8x1-crit`). Workflow in [`Exercise_2/`](../Exercise_2/README.md).

**Assumptions:** No covariance between the three responses (diagonal
observation covariance). Sensitivity uncertainties are not propagated.

**Acceptance:** The shared checks.

**Result today:** Release 3 data and template, all method rules met
(2026-10-22). C/E prior → linearized posterior: JEZEBEL 1.00044 → 1.0000854;
EUCLID 3x2 0.99983 → 1.0001537; EUCLID 1x8 0.99800 → 0.9990169. Largest PFNS
normalization deviation $1.61 \times 10^{-4}$ (flagged); no negative states.
Same posterior as the release 2 run within $2 \times 10^{-9}$ in relative
adjustment; only the reporting changed. Packaged as `_v3`; received by the
coordinators 2026-10-23.

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** —

## Exercise 3 · All integral responses

**Data:** Prior as Exercise 1. All 29 integral responses in released order:
JEZEBEL $k_\text{eff}$ and three reaction-rate ratios; EUCLID two
$k_\text{eff}$, 15 neutron-leakage-spectrum points and eight reaction-rate
ratios. Workflow in [`Exercise_3/`](../Exercise_3/README.md).

**Assumptions:** No covariance between responses, including between
neutron-leakage-spectrum points. Sensitivity uncertainties are not propagated.

**Acceptance:** The shared checks.

**Result today:** Release 3 data and template, all method rules met
(2026-10-22). C/E prior → linearized posterior: JEZEBEL $k_\text{eff}$
1.00044 → 1.00018; EUCLID 3x2 0.99983 → 1.00043; EUCLID 1x8 0.99800 →
0.99953. 23 of 29 posterior residuals within one observation standard
deviation (20 before). Largest PFNS normalization deviation
$1.38 \times 10^{-3}$ (flagged); no negative states; largest mean shift 0.75
prior standard deviations. The posterior changed against the release 2 run:
the 15 leakage-spectrum uncertainties are now 2.4–3.2 times smaller than the
release 2 `total_uncert`. Relative adjustments moved by up to 0.078 and
posterior standard deviations by up to 22 % (one-off comparison of the
posterior with the `_v2` absolute workbook and the release 2 observation file,
2026-10-22, the same comparison as for Exercises 1 and 2). Packaged as `_v3`;
received by the coordinators 2026-10-23.

**Concepts:** `ResponseSelection` `Discrepancy` `SensitivityAlignment` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `UncertaintyAudit` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** —

## Exercise 4 · Add Marini nu-bar

**Data:** Prior as Exercise 1. Exercise 3's 29 integral responses in the same
order, then the 25 Marini nu-bar points (0.973–19.9 MeV) in released order,
$m = 54$. Marini fields in
`Adjustement set/Differential/Marini nubar/nubar_Marini2021.json`: $E$ =
`experimental data.values` (n/f), $u$ = `experimental data.uncertainties`
(relative), $\rho$ = `experimental data.correlations` (25 × 25, row-major),
point energies = `experimental data.structure.limits` (MeV), $C$ =
`evaluated data.values` (ENDF/B-VIII.0 MT456), $s^\text{rel}$ =
`sensitivities.values` (25 × 52). Response IDs `marini-nubar-00` to
`marini-nubar-24`. The specification cites EXFOR 14799002; the file says
private communication. Observation HDF5 keeps Exercise 3's layout (`/delta`,
`/cov`, `/sens`, `/responses/*`) with $\sigma_C = 0$ for the Marini rows.
Workflow in `Exercise_4/`.

**Assumptions:** The as-MT452 rule (coordinator instruction, 2026-10-23):
Marini sensitivity rows land on MT452; $E$ and $C$ are used as released (both
prompt), so the discrepancy carries no delayed-nu-bar offset; MT456 stays at
the prior. No calculation uncertainty for the Marini points. Independent data
sets (no covariance between the integral block and the Marini block). No
covariance between integral responses, as in Exercise 3. Sensitivity
uncertainties are not propagated.

**Acceptance:** The shared checks, plus:

- The first 29 rows of `/delta` and `/sens` and the integral block of `/cov`
  equal Exercise 3's observation file exactly.
- Every Marini `/sens` row has one non-zero entry, on the MT452 state of the
  point's group (groups 31–50), equal to $C_k / \mu_{i,(452,g)}$; every MT456
  column is zero in all 54 rows.
- The Marini covariance block is $D_{\sigma_E} \rho D_{\sigma_E}$ with
  $\sigma_E = u E$, symmetric and positive definite; the integral–Marini
  blocks are zero.
- `nda` runs on the 54 × 54 correlated $\Sigma_E$, and the analysis reproduces
  its posterior from the inputs.
- The analysis report gives prior and linearized-posterior C/E for all 54
  observations and states the as-MT452 rule, the unadjusted MT456 and every
  assumption.
- The questions sheet's answer 3 describes the block-diagonal $\Sigma_E$
  (integral diagonal, Marini full correlation); the comment sheet states the
  as-MT452 rule.

**Result today:** Contract fixed 2026-10-23; not built.

**Concepts:** `ResponseSelection` `DifferentialSet` `DifferentialSensitivities` `DifferentialObservations` `DifferentialSelection` `NubarAsTotal` `DifferentialAlignment` `Discrepancy` `SensitivityAlignment` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `DifferentialCovariance` `IndependentDataSets` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** 2026-10-23, orchestrator: Marini measured prompt nu-bar (JSON
`reaction = "nubar-prompt"`; its `evaluated data` matches ENDF/B-VIII.0 MF1
MT456 within $1.4 \times 10^{-5}$, MT452 only within $2.1 \times 10^{-3}$),
while the specification, the integral sensitivities and the template use
MT452, and ENDF/B-VIII.0 MF31 has no MT452–MT456 covariance. **Resolved** the
same day by Andry Monlon (`Update_email.pdf`): use the Marini data as if they
were MT452, as agreed before we joined. Corrected total nu-bar data derived
from Marini may be released later; Exercise 4 would then need a rerun.

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
