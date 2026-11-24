# Exercises

Reference set: [CONCEPTS](CONCEPTS.md) · [CODE](CODE.md) ·
[DEFINITIONS](DEFINITIONS.md) · [TESTS](TESTS.md)

One section per SG52 exercise from the specification. Each section is the
contract for its workflow: data used, the matrix layout, the data treatment,
assumptions, acceptance checks, the result today, the concept nodes it
exercises, and comments. Comments are dated and signed; any agent may add one.
The matrix layout and the data treatment of each section refer to the shared
tables in [Matrix layout and data treatment](#matrix-layout-and-data-treatment).

Acceptance checks shared by every exercise, from the method rules:

- Release data, the experimental and calculation uncertainties (never
  `total_uncert`), and absolute GLLS. Exercises 1–4 use release 3 data;
  Exercise 5 on uses release 4, whose prior and integral files are identical.
- Relative mean adjustment and posterior relative covariance normalized on the
  prior mean.
- The newest output template, including the prior and questions sheets, in
  scientific format with 11 significant digits: release 4 since 2026-11-23
  (release 3 before).
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

Questions sheet answers 6–11, added by the release 4 template (orchestrator
draft, 2026-11-23; wording accepted by the Captain the same day, pending
coordinator feedback on submission). Exercises 1–3: all six not applicable,
integral responses only.
Exercise 4:

6. Pointwise inclusion: yes; each Marini point has its own residual
   $E_k - C_k$ with $C_k$ the released evaluated value; the as-MT452 rule
   applies.
7. One-hot sensitivity: yes, the released rows, made absolute with $C$ and
   the prior mean on MT452.
8. Peelle's Pertinent Puzzle: no correction; $\sigma_E = uE$.
9. Shape data sets (Marini/Keegan PFNS, Snyder, Dongwi): not applicable, not
   used.
10. Their normalization: not applicable.
11. Snyder–Dongwi correlation: not applicable, not used.

Exercise 5:

6. Pointwise inclusion: yes, for Marini nu-bar and both PFNS sets; the
   Marini PFNS points at 27.88 MeV have no evaluated value and are not used.
7. One-hot sensitivity: yes, the released rows; nu-bar on MT452, PFNS on
   (slice holding $E_\text{in}$, outgoing group holding $E_\text{out}$).
8. Peelle's Pertinent Puzzle: no correction; $\sigma_E = uE$ for every
   differential set.
9. Shape data sets: yes for both PFNS sets ("Clean ratio shape"); Snyder and
   Dongwi not used. This is a judgment: the level comes from the released
   block-normalized $C$, and no normalization parameter is fitted.
10. Their normalization: the released block-normalized $C$ as is; no free
    normalization factor, no renormalization on the prior.
11. Snyder–Dongwi correlation: not applicable, not used.

### Matrix layout and data treatment

Shared by every exercise; notation as in [CONCEPTS](CONCEPTS.md#notation).
Indices are zero-based. Ranges are inclusive. Counts and index ranges were read
from the generated HDF5 files on 2026-11-24.

#### Matrices

| Matrix | Dataset | Shape | Rows | Columns |
|---|---|---|---|---|
| $\mu_i$ | `ex<N>_prior.hdf5:/mean/values` | $n$ | states (`/mean/row_indices`) | — |
| $\Sigma_i$ | `ex<N>_prior.hdf5:/cov/values` | $n \times n$ | states | states |
| $\Delta$ | `ex<N>_observations.hdf5:/delta/values` | $m$ | responses (`/delta/row_indices`) | — |
| $\Sigma_E$ | `ex<N>_observations.hdf5:/cov/values` | $m \times m$ | responses | responses |
| $S$ | `ex<N>_observations.hdf5:/sens/values` | $m \times n$ | responses | states (`/sens/col_indices`, prior order) |
| $E$, $\sigma_E$, $C$, $\sigma_C$ | `ex<N>_observations.hdf5:/responses/{experimental, experimental_uncertainty, simulated, simulated_uncertainty}` (Exercise 2 on) | $m$ each | responses (`/responses/row_indices`) | — |
| $\mu_f$ | `ex<N>_results.hdf5:/mean/values` | $n$ | states, prior order (no index dataset) | — |
| $\Sigma_f$ | `ex<N>_results.hdf5:/covariance/values` | $n \times n$ | states, prior order | states |

$n = 979$ in every exercise. Every index dataset of one exercise lists the same
states in the same order.

#### State index (rows of $\mu$ and $\Sigma$, columns of $S$)

Label `94239_<QID>_<g>` for 51-group quantities, `94239_<QID>` for mubar.
Within a 51-group QID, state = first index + $g$, energy group $g = 0$
(1e-5–2.97e-3 eV) … 50 (17–20 MeV), ascending (`gs.txt`, eV).

| States | QID | Quantity |
|---|---|---|
| 0–50 | 00002 | elastic |
| 51–101 | 00004 | inelastic |
| 102–152 | 00016 | (n,2n) |
| 153–203 | 00017 | (n,3n) |
| 204–254 | 00018 | fission |
| 255–305 | 00037 | (n,4n) |
| 306–356 | 00102 | capture |
| 357–407 | 00452 | total nu-bar |
| 408–458 | 00456 | prompt nu-bar |
| $459 + 51k + g$, $k = 0…9$ (459–968) | $1018 + 100k$ | PFNS slice $k$, outgoing group $g$ |
| $969 + k$, $k = 0…9$ (969–978) | $251 + 1000k$ | mubar, incident range $k$ |

PFNS slice and mubar incident ranges (`pfns_incident_energies.txt`,
`mubar_incident_energies.txt`; the mubar bounds read 1.353 and 5.3526 MeV
where PFNS reads 1.35 and 5.35):

| $k$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| PFNS QID | 1018 | 1118 | 1218 | 1318 | 1418 | 1518 | 1618 | 1718 | 1818 | 1918 |
| States | 459–509 | 510–560 | 561–611 | 612–662 | 663–713 | 714–764 | 765–815 | 816–866 | 867–917 | 918–968 |
| Incident (MeV) | 1e-11–6.41e-7 | 6.41e-7–0.5 | 0.5–1.35 | 1.35–5.35 | 5.35–6.07 | 6.07–10 | 10–13 | 13–14 | 14–15 | 15–20 |

#### Observation rows (rows of $\Delta$, $\Sigma_E$, $S$)

From Exercise 3 on, every exercise keeps the rows of the one before it and
appends its new data set; Exercises 1 and 2 pick single integral rows (see
their sections).

| Rows | Data set | Response IDs | Count |
|---|---|---|---|
| 0 | JEZEBEL $k_\text{eff}$ | `PU-MET-FAST-001-001-s` | 1 |
| 1–3 | JEZEBEL reaction-rate ratios | `PU-MET-FAST-001-001_{U238, Np237, Pu239}/U235` | 3 |
| 4–5 | EUCLID $k_\text{eff}$ | `euclid-3x2-crit`, `euclid-8x1-crit` | 2 |
| 6–20 | EUCLID leakage spectrum | `euclid_NLS_<config>_<E>`: configs `3x2x45` (6–10), `3x2x55` (11–15), `8x1x90` (16–20), each $E$ = 2.4, 3.2, 4, 4.8, 5.6 | 15 |
| 21–28 | EUCLID reaction-rate ratios | `euclid_rrr_<config>_<reaction>/U235(fission)`: `8x1x130` (21–24), `3x2x65` (25–28), each Pu239(fission), U238(n,2n), U238(capture), U238(fission) | 8 |
| 29–53 | Marini nu-bar | `marini-nubar-00` … `-24` | 25 |
| 54–1273 | Marini PFNS | `marini-pfns-0000` … `-1219` | 1220 |
| 1274–2550 | Keegan PFNS | `keegan-pfns-0000` … `-1276` | 1277 |
| 2551–2641 | Snyder | `snyder-00` … `-90` | 91 |
| 2642–2732 | Dongwi | `dongwi-00` … `-90` | 91 |

$\Sigma_E$ is block-diagonal over these data sets (integral rows 0–28 count as
one block); every entry between two data sets is zero (independent data sets).

#### Data treatment by source

**Prior (`Covariances/plaintext`).** $\mu_i$: `94239-<QID>-xs.txt`, in state
order. $R_i$: `94239-<QID1>-94239-<QID2>-relcov.txt` (51 × 51, mubar 1 × 1)
placed at the two QIDs' state ranges; missing files are zero blocks (release
README). Made absolute, $\Sigma_i = D_{\mu_i} R_i D_{\mu_i}$. Blocks between
QIDs are non-zero among the seven cross sections (MT2, 4, 16, 17, 18, 37, 102,
states 0–356), among PFNS slices 1018–1318, between 1418 and 1518, and among
1718–1918; MT452, MT456, slice 1618 and the mubar states have no covariance
with other QIDs. 196 states have $\mu_i = 0$ (MT4 groups 0–23, MT16 0–37,
MT17 0–43, MT37 0–49, PFNS slices 1218–1918 groups 0–4); 215 have zero prior
variance (these plus slice 1018 groups 0–17 and mubar 00251), so GLLS cannot
move them.

**Integral (`Integral/{JEZEBEL,EUCLID}`).** From `*_obs.csv` (columns `expt`,
`expt_uncert`, `sim`, `sim_uncert`; JEZEBEL file rows 0–3, EUCLID file
rows 4–28): $\Delta_k = E_k - C_k$, and the diagonal entry
$(\Sigma_E)_{kk} = \sigma_{E,k}^2 + \sigma_{C,k}^2$, absolute as released. From
`*_sens_rel.csv` (3836 parameter columns): the 596 `Pu239_*` columns map to
states (elastic → 00002, inelastic → 00004, z,2n → 00016, z,3n → 00017,
fission → 00018, z,4n → 00037, capture → 00102, multiplicity total nu →
00452, spectrum prompt nu $k$, $g$ → PFNS slice $k$ group $g$, mubar $k$ →
$251 + 1000k$) and are made absolute, $S_{kj} = C_k s_{kj} / \mu_{i,j}$; the
3240 columns of other nuclides are dropped (not adjusted); `*_sens_unc_rel.csv`
is not read. Non-zero $S$ columns in rows 0–28: 595 — MT2, MT18, MT102, MT452
all groups; MT4 groups 25–50 (states 76–101); MT16 38–50 (140–152); MT17
45–50 (198–203); MT37 50 (305); PFNS slices 1018–1318 groups 18–50, 1418–1918
groups 17–50; mubar 01251–09251 (970–978). Always zero: MT456 (408–458) and
mubar 00251 (969).

**Marini nu-bar (`Marini nubar/nubar-Marini2021.json`; release 3:
`nubar_Marini2021.json`).** $E$ = `experimental data.values`, $u$ =
`.uncertainties`, $\rho$ = `.correlations`, $C$ = `evaluated data.values`
(prompt, MT456). Kept: points with energy ≤ 20 MeV and a non-zero row (all 25).
$\Delta = E - C$ into rows 29–53; $\sigma_E = uE$, $\sigma_C = 0$; $\Sigma_E$
block $D_{\sigma_E} \rho D_{\sigma_E}$ at rows/columns 29–53. One-hot row on
group $g$ moved to MT452 (as-MT452 rule): $S_{k,\,357+g} = C_k / \mu_{i,357+g}$,
groups 31–50 (states 388–407), 18 distinct states.

**Marini PFNS (`Marini PFNS/PFNS_CEAcor.json`) and Keegan PFNS (`Keegan
PFNS/PFNS_ChiNuPu9_Oct2020.json`).** $E$ = `data.values`, $u$ =
`data.uncertainties`, $\rho$ = `data.correlations`, $C$ = `evaluated
data.values` (block-normalized, used as released). Kept: $E_\text{in} \le 20$
MeV, non-zero row, finite $C$ (Marini 1220 of 1281, Keegan 1277 of 1277).
$\Delta = E - C$; $\sigma_E = uE$, $\sigma_C = 0$; $\Sigma_E$ block
$D_{\sigma_E} \rho D_{\sigma_E}$ per data set (Marini rows/columns 54–1273,
Keegan 1274–2550). One-hot row on (slice $k$ holding $E_\text{in}$, group $g$
holding $E_\text{out}$), checked against an energy lookup:
$S_{r,\,459+51k+g} = C_r / \mu_{i,459+51k+g}$. Marini: slices 1218–1918,
groups 28–43, 128 distinct states; Keegan: slices 1318–1918, groups 25–42,
126 distinct states.

**Snyder (`Snyder/nfcs_Snyder2021_shape.json`) and Dongwi
(`Dongwi/nfcs_Dongwi2025_shape.json`).** $E$ = `experimental data.values`,
$u$, $\rho$ as for Marini nu-bar, $C$ = `evaluated data.values` (MT18). Kept:
energy ≤ 20 MeV and a non-zero row (91 of 92 each). $\Delta = E - C$;
$\sigma_E = uE$, $\sigma_C = 0$; $\Sigma_E$ block
$D_{\sigma_E} \rho D_{\sigma_E} + s_N^2 E E^\top$ with $s_N$ = 0.0117 Snyder
(rows/columns 2551–2641), 0.0134 Dongwi (2642–2732). One-hot row on MT18 group
$g$, checked against an energy lookup: $S_{k,\,204+g} = C_k / \mu_{i,204+g}$,
groups 27–50 (states 231–254), 22 distinct states.

**Posterior and outputs.** `nda` writes $\mu_f$ and $\Sigma_f$ (absolute GLLS,
[CONCEPTS](CONCEPTS.md#notation)) in prior state order. The analysis forms
linearized responses $C_f = C + S(\mu_f - \mu_i)$ for every row. The relative
workbook holds the 928 template states (all but MT456) in template order: MT2,
4, 16, 17, 18, 37, 102 (states 0–356), mubar (969–978), MT452 (357–407), PFNS
slices 1018–1918 (459–968). `posterior_rel_adjust` and `prior_abs` are 51
group rows × 19 QID columns (mubar column: rows 0–9); the two
`*_cov_rel_to_prior` sheets are 928 × 928. Relative values are normalized on
the prior: $r = D_{\mu_i}^{-1}(\mu_f - \mu_i)$,
$R_f = D_{\mu_i}^{-1} \Sigma_f D_{\mu_i}^{-1}$; cells with $\mu_i = 0$ are
written `NaN`. The absolute workbook holds all 979 states in state order
(`State_values_absolute`: $\mu_i$, $\mu_f$, prior and posterior standard
deviation) and both 979 × 979 absolute covariances.

**ENDF/B-VIII.0 and VIII.1 reference (Exercise 6 only).**
`ex6_endf_reference.hdf5` holds each library's reference group values on the
979 states (`/row_indices`, prior order) and the per-QID reproduction gate
(29 QIDs). It enters no GLLS matrix; the analysis compares it with $\mu_i$,
$\mu_f$ and $\Sigma_f$ state by state.

## Exercise 1 · JEZEBEL criticality

**Data:** Prior from the release covariances. One integral response: JEZEBEL
$k_\text{eff}$ (`PU-MET-FAST-001-001-s`). Workflow in
[`Exercise_1/`](../Exercise_1/README.md).

**Matrices:** $n = 979$, $m = 1$. $\mu_i$, $\mu_f$ (979) and $\Sigma_i$,
$\Sigma_f$ (979 × 979) over states 0–978 as in the shared state index table.
$\Delta$ (1), $\Sigma_E$ (1 × 1) and $S$ (1 × 979, 447 non-zero columns) have
one row: row 0 JEZEBEL $k_\text{eff}$. No `/responses` group (added in
Exercise 2).

**Data treatment:** Prior as in the shared section, into all of $\mu_i$ and
$\Sigma_i$. Integral: JEZEBEL file row 0 only, into row 0 of $\Delta$,
$\Sigma_E$ and $S$; $\Sigma_E = \sigma_E^2 + \sigma_C^2$.

**Assumptions:** Sensitivity uncertainties are not propagated.

**Acceptance:** The shared checks.

**Result today:** Release 3 data and template, all method rules met
(2026-10-22). C/E prior 1.00044, linearized posterior 1.00000554. Largest
PFNS normalization deviation $1.10 \times 10^{-6}$ (flagged); no negative
states. Same posterior as the release 2 run within $4 \times 10^{-11}$ in
relative adjustment (`total_uncert` was the component quadrature here); only
the reporting changed. Packaged as `UU_Erik_Aurora_SG52_v3`; the release 2
submission is kept as `_v2`. `_v3` received by the coordinators
(Andry Monlon, 2026-10-23). Re-exported 2026-11-23 into the release 4
template: only the questions sheet changed (answers 6–11); every other sheet
and the absolute workbook are cell-identical to the previous export.
Packaged as `UU_Erik_Aurora_SG52_v4` for the Captain to send.

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `AbsolutePriorCovariance` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** —

## Exercise 2 · JEZEBEL and EUCLID criticality

**Data:** Prior as Exercise 1. Three integral responses: JEZEBEL
$k_\text{eff}$, EUCLID 3x2 and 1x8 $k_\text{eff}$ (`euclid-3x2-crit`,
`euclid-8x1-crit`). Workflow in [`Exercise_2/`](../Exercise_2/README.md).

**Matrices:** $n = 979$, $m = 3$. Prior and posterior as Exercise 1. Rows of
$\Delta$, $\Sigma_E$ (3 × 3, diagonal), $S$ (3 × 979, 538 non-zero columns)
and `/responses/*`: 0 `PU-MET-FAST-001-001-s`, 1 `euclid-3x2-crit`, 2
`euclid-8x1-crit`. This order differs from the shared row table (EUCLID
$k_\text{eff}$ at rows 1–2, not 4–5).

**Data treatment:** Prior as in the shared section. Integral: JEZEBEL file
row 0 into row 0, EUCLID file rows 0–1 into rows 1–2; diagonal $\Sigma_E$.

**Assumptions:** No covariance between the three responses (diagonal
observation covariance). Sensitivity uncertainties are not propagated.

**Acceptance:** The shared checks.

**Result today:** Release 3 data and template, all method rules met
(2026-10-22). C/E prior → linearized posterior: JEZEBEL 1.00044 → 1.0000854;
EUCLID 3x2 0.99983 → 1.0001537; EUCLID 1x8 0.99800 → 0.9990169. Largest PFNS
normalization deviation $1.61 \times 10^{-4}$ (flagged); no negative states.
Same posterior as the release 2 run within $2 \times 10^{-9}$ in relative
adjustment; only the reporting changed. Packaged as `_v3`; received by the
coordinators 2026-10-23. Re-exported 2026-11-23 into the release 4 template:
only the questions sheet changed; every other sheet and the absolute workbook
are cell-identical to the previous export. Packaged as `_v4`.

**Concepts:** `ResponseSelection` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** —

## Exercise 3 · All integral responses

**Data:** Prior as Exercise 1. All 29 integral responses in released order:
JEZEBEL $k_\text{eff}$ and three reaction-rate ratios; EUCLID two
$k_\text{eff}$, 15 neutron-leakage-spectrum points and eight reaction-rate
ratios. Workflow in [`Exercise_3/`](../Exercise_3/README.md).

**Matrices:** $n = 979$, $m = 29$. Prior and posterior as Exercise 1. Rows
0–28 as in the shared row table: 0–3 JEZEBEL, 4–28 EUCLID. $\Sigma_E$
29 × 29 diagonal; $S$ 29 × 979, 595 non-zero columns.

**Data treatment:** Prior and Integral as in the shared section: the whole
JEZEBEL and EUCLID files, rows 0–28 of $\Delta$, $\Sigma_E$ and $S$.

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
received by the coordinators 2026-10-23. Re-exported 2026-11-23 into the
release 4 template: only the questions sheet changed; every other sheet and
the absolute workbook are cell-identical to the previous export. Packaged as
`_v4`.

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

**Matrices:** $n = 979$, $m = 54$. Prior and posterior as Exercise 1. Rows:
0–28 integral, 29–53 Marini nu-bar. $\Sigma_E$ 54 × 54: diagonal on 0–28, full
block on 29–53, zero between. $S$ 54 × 979; rows 29–53 hit only MT452 states
388–407; MT456 columns 408–458 are zero in every row.

**Data treatment:** Prior and Integral as Exercise 3 (release 3 files). Marini
nu-bar as in the shared section (release 3 file name), into rows/columns
29–53 of $\Delta$, $\Sigma_E$ and rows 29–53 of $S$.

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

**Result today:** Built 2026-10-23 on release 3; all acceptance checks pass
(14 tests; an independent numpy GLLS reproduces the `nda` posterior; reruns
give identical HDF5 datasets). C/E prior → linearized posterior: JEZEBEL
$k_\text{eff}$ 1.00044 → 1.00012; EUCLID 3x2 0.99983 → 1.00049; EUCLID 1x8
0.99800 → 0.99952; Marini 0.9909–1.0121 → 0.9815–0.9962. Within one
observation standard deviation: 41 of 54 before, 35 after (integral 20 → 24,
Marini 21 → 11). MT452 lowered in every group, by at most 1.84 % (group 50);
MT456 unchanged. Largest PFNS normalization deviation
$1.40 \times 10^{-3}$ (flagged; $1.38 \times 10^{-3}$ in Exercise 3); no
negative states. Completion review passed after one fix. Added 2026-10-26 to
`UU_Erik_Aurora_SG52_v3` (`Ex4/`; Ex1–3 unchanged, archives rebuilt) for the
Captain to send; coordinator comments go into the next round. Re-exported
2026-11-23 into the release 4 template: only the questions sheet changed
(answers 6–11); every other sheet and the absolute workbook are
cell-identical to the previous export. Packaged as `_v4`.

**Concepts:** `ResponseSelection` `DifferentialSet` `DifferentialSensitivities` `DifferentialObservations` `DifferentialSelection` `NubarAsTotal` `DifferentialAlignment` `Discrepancy` `SensitivityAlignment` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `DifferentialCovariance` `IndependentDataSets` `PosteriorMean` `PosteriorCovariance` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** 2026-10-23, orchestrator: Marini measured prompt nu-bar (JSON
`reaction = "nubar-prompt"`; its `evaluated data` matches ENDF/B-VIII.0 MF1
MT456 within $1.4 \times 10^{-5}$, MT452 only within $2.1 \times 10^{-3}$),
while the specification, the integral sensitivities and the template use
MT452, and ENDF/B-VIII.0 MF31 has no MT452–MT456 covariance. **Resolved** the
same day by Andry Monlon (`Update_email.pdf`): use the Marini data as if they
were MT452, as agreed before we joined. Corrected total nu-bar data derived
from Marini may be released later; Exercise 4 would then need a rerun.
2026-10-23, orchestrator: **Marini lies off the posterior.** All 25 posterior
C/E are below 1 (0.9815–0.9962), outside the measured scatter. The rule and
the integral data are not the cause: Marini alone gives the same (0.9834–0.9977),
as does building $\sigma_E$ on $C$ instead of $E$ (0.9845–0.9985); dropping the
correlations gives 0.9906–1.0081. The released correlations are strong (mean
off-diagonal 0.81; one mode carries 82 % of the variance), and the prior
disagrees with Marini's shape ($\chi^2/m = 2.34$ for Marini alone before the
update), so GLLS fits the shape and moves the common level. Seven groups hold
two points that one group value cannot both follow: fitting one value per pair
leaves residuals of 0.1–3.3σ, three pairs above 2σ (largest group 43,
`marini-nubar-16`/`17`; corrected 2026-10-23 after the completion review, first
recorded as "up to 2.6σ"). Keeping one point per group still gives
0.9851–1.0009. Reported, not corrected.
2026-10-23, orchestrator: completion review (one round): one blocker, fixed —
questions-sheet answer 5 and the README now name the unpropagated integral
sensitivity uncertainties and the uncorrelated integral responses. Nits fixed:
the sensitivity test uses distinct prior means and checks MT456 in all 54 rows;
the report states that the Marini $\sigma_E$ is built on $E$.
2026-11-23, orchestrator: release 4 renames the Marini file to
`nubar-Marini2021.json`. Against release 3, `experimental data`,
`evaluated data` and `sensitivities.values` (still 25 × 52) are identical;
only 22 of the 52 `sensitivities.structure.limits` are rounded (largest
change 0.005 MeV), and the README now says 25 × 51. The workflow still reads
release 3; moving it to release 4 is a separate task.

## Exercise 5 · Add Marini and Keegan PFNS

**Data:** Release 4 throughout. Its prior covariances and integral files are
byte-identical to release 3, and its Marini nu-bar values to release 3's, so
Exercise 4's 54 rows carry over unchanged (Marini nu-bar now from
`Marini nubar/nubar-Marini2021.json`). Then two PFNS data sets, each a list of
(incident, outgoing energy) pairs in released order:
Marini PFNS (`Marini PFNS/PFNS_CEAcor.json`, EXFOR 14684002, 1281 points,
21 PFNS blocks) and Keegan PFNS (`Keegan PFNS/PFNS_ChiNuPu9_Oct2020.json`,
Chi-Nu, K.J. Kelly, 1277 points, 20 PFNS blocks). Fields per file: $E$ =
`data.values`, $u$ = `data.uncertainties` (relative), $\rho$ =
`data.correlations` ($N \times N$, row-major), incident and outgoing
energies = `data.structure[0].limits` and `data.structure[1].limits` (MeV),
$C$ = `evaluated data.values` (`null` above 20 MeV), $s^\text{rel}$ =
`sensitivities.values` ($N \times 10 \times 51$: PFNS slice
`sensitivities.structure[0].mt` × outgoing group). Kept: the 1220 Marini
points with $E_\text{in} \le 20$ MeV (the 61 points of the 27.88 MeV block
have $C$ `null` and zero rows) and all 1277 Keegan points, so
$m = 54 + 1220 + 1277 = 2551$. Response IDs `marini-pfns-0000` …
`marini-pfns-1219` and `keegan-pfns-0000` … `keegan-pfns-1276` (released
index). Row order: Exercise 4's 54 rows, Marini PFNS, Keegan PFNS.
Observation HDF5 keeps Exercise 4's layout (`/delta`, `/cov`, `/sens`,
`/responses/*`) with $\sigma_C = 0$ for every differential row. Workflow in
`Exercise_5/`.

**Matrices:** $n = 979$, $m = 2551$. Prior and posterior as Exercise 1. Rows:
0–53 as Exercise 4, 54–1273 Marini PFNS, 1274–2550 Keegan PFNS. $\Sigma_E$
2551 × 2551 with four diagonal blocks (0–28 diagonal, 29–53, 54–1273,
1274–2550 full). $S$: PFNS rows hit only PFNS states (Marini slices
1218–1918 groups 28–43, Keegan slices 1318–1918 groups 25–42).

**Data treatment:** Prior, Integral and Marini nu-bar as Exercise 4 (release 4
files). Marini PFNS and Keegan PFNS as in the shared section, into rows 54–1273
and 1274–2550 of $\Delta$, $S$ and the matching diagonal blocks of $\Sigma_E$.

**Assumptions:**
- Exercise 4's assumptions carry over: the as-MT452 rule for Marini nu-bar, no
  covariance between integral responses, sensitivity uncertainties not
  propagated, no calculation uncertainty for differential points.
- PFNS calculated values are the released block-normalized values, used as
  released: no free normalization factor, no renormalization on the prior.
  This is how the PFNS shape data are handled. It also makes Marini's
  multiplicity-weighted convention harmless, because each block's $C$ is
  scaled to its own data.
- PFNS sensitivities are the released one-hot rows (value 1 on the PFNS slice
  holding $E_\text{in}$ and the outgoing group holding $E_\text{out}$), with
  no term for the block normalization, as released.
- Each PFNS set's covariance is $D_{\sigma_E} \rho D_{\sigma_E}$ with
  $\sigma_E = uE$, as for Marini nu-bar; no Peelle's Pertinent Puzzle
  correction.
- Independent data sets: no covariance between the integral block, Marini
  nu-bar, Marini PFNS and Keegan PFNS. The two PFNS files share an EXFOR
  number but are independent experiments (release README).

**Acceptance:** The shared checks, plus:

- The first 54 rows of `/delta`, `/sens`, `/responses/*` and the leading
  54 × 54 block of `/cov` equal Exercise 4's observation file exactly.
- Every PFNS `/sens` row has one non-zero entry, on the state of the PFNS
  slice holding $E_\text{in}$ and the outgoing group holding $E_\text{out}$,
  equal to $C_k / \mu_{i,j}$; that state agrees with a lookup of both
  energies in the released `sensitivities.structure` limits; every other
  entry is zero.
- Each PFNS block of `/cov` is $D_{\sigma_E} \rho D_{\sigma_E}$ with
  $\sigma_E = uE$, symmetric and positive definite; every block between
  data sets is zero.
- `nda` runs on the 2551 × 2551 $\Sigma_E$, and the analysis reproduces its
  posterior from the inputs.
- The analysis report gives, per data set (integral, Marini nu-bar, Marini
  PFNS, Keegan PFNS): count, prior and linearized-posterior $\chi^2/m$, C/E
  range and the number within one observation standard deviation. It writes
  every response's row to a CSV, gives PFNS normalization and positivity
  flags, and names every assumption.
- The questions sheet answers 6–11 for the PFNS data; the comment sheet
  states the as-MT452 rule and the PFNS rules.

**Result today:** Built 2026-11-23 on release 4, m = 2551. Gate green: 31
tests across Exercises 1–5, the full workflow rerun from a clean state, a
second run giving identical HDF5 datasets, `nda` reproduced by the analysis to
$5 \times 10^{-13}$, rows 0–53 equal to Exercise 4's. $\chi^2/m$ prior →
posterior (each set's own $\Sigma_E$ block; Exercise 4's comment used $V$,
which gives 2.34 for Marini nu-bar): integral 1.25 → 1.16; Marini nu-bar
7.55 → 1.42; Marini PFNS 0.64 → 0.31; Keegan PFNS 1.82 → 0.89. Within one
observation standard deviation, prior → posterior: integral 20 → 22, Marini
nu-bar 21 → 12, Marini PFNS 743 → 931, Keegan PFNS 716 → 586. C/E prior →
linearized posterior: JEZEBEL $k_\text{eff}$ 1.00044 → 1.00038; EUCLID 3x2
0.99983 → 1.00218; EUCLID 1x8 0.99800 → 1.00124; Marini nu-bar
0.9909–1.0121 → 0.9822–0.9967. PFNS block mean C/E: Marini 0.936–1.075 →
0.914–1.032, Keegan 0.891–2.964 → 0.863–2.512. PFNS normalization: every
slice's sum rises except 01618; largest deviation $2.40 \times 10^{-3}$
(slice 01418; Exercise 4 had $1.40 \times 10^{-3}$), flagged. No negative
states; MT456 unchanged; largest mean shift 2.72 prior standard deviations
(PFNS states with means near $10^{-8}$). Completion review passed with no
blockers (2026-11-23). Added 2026-11-23 to `UU_Erik_Aurora_SG52_v4` (`Ex5/`;
Ex1–4 unchanged, archives rebuilt) for the Captain to send.

**Concepts:** `DifferentialSet` `DifferentialSensitivities` `DifferentialSelection` `NubarAsTotal` `PfnsObservationModel` `DifferentialAlignment` `Discrepancy` `AbsoluteSensitivity` `ObservationCovariance` `CombinedVariance` `UncorrelatedResponses` `DifferentialCovariance` `IndependentDataSets` `PosteriorMean` `PosteriorCovariance` `GllsReproduction` `LinearizedResponses` `PfnsChecks` `RelativePosteriorCovariance` `UpdatedTemplate`

**Comments:** 2026-11-23, orchestrator: release 4 adds `evaluated data` and
one-hot `sensitivities` to both PFNS files (release 3 had neither), which is
what makes Exercise 5 possible. Checked before work: the one-hot state of
every kept point matches a lookup of its energies in the released limits;
no kept point lands on a zero prior mean; both kept correlation matrices are
positive definite (smallest eigenvalue 0.79 Marini, 0.097 Keegan). Keegan
has 45 points with relative uncertainty above 1 (up to 346), so they carry
almost no weight. Each block's released $C$ integrates to 0.952–0.956
(Marini) and 0.985–0.998 (Keegan) of the data's integral over the block's
measured outgoing range, because the prior spectrum is normalized over all
outgoing energies. Taken as released, the PFNS discrepancies therefore carry
a positive block-level offset (about 4.5 % for Marini). The PFNS
normalization flags will show whether the update turns that offset into
slice mass.
2026-11-23, orchestrator: completion review (one round): no blockers;
reviewer independently confirmed rows 0–53, selection, alignment, $S = C/\mu$,
covariance blocks and every "Result today" number. Nits fixed: the questions
sheet's normalization answer and the block-normalized definition now say that
$C$ integrates to less than the data over the measured range; the comment
sheets carry the script-computed posterior PFNS slice sums instead of
pointing to the analysis report, which the NEA does not receive; report
assumption (viii) reads its kept/released counts and dropped energies from
the JSON; (i) names release 3's `Update_email.pdf`. Open proposal:
`state_summary.csv` is 21 MB because it carries 2 × 2551 per-response
columns.

## Exercise 6 · Add Snyder, compare with ENDF/B-VIII.1

**Data:** Release 4. Exercise 5's 2551 rows unchanged, then the Snyder
fission cross section, shape version (`Snyder/nfcs_Snyder2021_shape.json`,
EXFOR 14721002, 92 points, `MeasurementType` "Shape clean ratio"). Fields:
$E$ = `experimental data.values` (b), $u$ = `experimental data.uncertainties`
(relative), $\rho$ = `experimental data.correlations` (92 × 92), incident
energy = `experimental data.structure.limits` (MeV), $C$ =
`evaluated data.values` (ENDF/B-VIII.0 MT18), $s^\text{rel}$ =
`sensitivities.values` (92 × 52, one-hot, column 51 zero). Kept: the 91
points up to 19.4 MeV; the 20.54 MeV point has a zero sensitivity row.
Response IDs `snyder-00` … `snyder-90` (released index); $m = 2642$.
Sensitivities land on `94239_00018_<group>` (groups 27–50), $S = C/\mu$.
Normalization uncertainty $s_N = 1.17\,\%$ from the release 4 Differential
README (release 3's absolute file gives 1.1727 %: its covariance equals the
shape covariance plus $(0.011727)^2 E E^\top$ exactly).
Reference libraries for the comparison: ENDF/B-VIII.0 and ENDF/B-VIII.1
Pu-239 from the NNDC (`Resources/ENDF-B-VIII.0/n-094_Pu_239.endf`, sha256
`eae697df…a48e684`, from `endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip`;
`Resources/ENDF-B-VIII.1/n-094_Pu_239.endf`, sha256 `7e298d9e…49cda127`,
from `releases/B-VIII.1/neutrons/neutrons-version.VIII.1.tar.gz`), both
processed with NJOY 2016.78 and the ERRORR part of the release's
`Covariances/NJOY_input` (from the second `moder`). Workflow in
`Exercise_6/`.

**Matrices:** $n = 979$, $m = 2642$. Prior and posterior as Exercise 1. Rows:
0–2550 as Exercise 5, 2551–2641 Snyder. $\Sigma_E$ adds the full block
2551–2641. $S$: Snyder rows hit only MT18 states 231–254.

**Data treatment:** Everything of Exercise 5 unchanged. Snyder as in the
shared section ($s_N = 0.0117$), into rows 2551–2641 of $\Delta$, $S$ and the
block 2551–2641 of $\Sigma_E$. ENDF/B-VIII.0 and VIII.1 reference as in the
shared section; outside the GLLS matrices.

**Assumptions:**
- Exercise 5's assumptions carry over.
- Snyder shape normalization: a free normalization factor with prior
  uncertainty equal to the removed normalization (systematic) error, $s_N =
  1.17\,\%$, marginalized into the observation covariance, as on the
  coordinators' Exercise 6 slide (2026-09-01 meeting): $\Sigma_E^{(S)} =
  D_{\sigma_E} \rho D_{\sigma_E} + s_N^2 E E^\top$, $\sigma_E = uE$
  (Captain, 2026-11-23).
- Snyder is independent of every other data set (Dongwi is not used).
- Reference group values: GENDF (GROUPR) MF3 for MT 2, 4, 16, 17, 18, 37,
  102, 452, 456; ERRORR MF34 output for the ten mubar values; ERRORR MF35
  output spectra at the input's 31 `efmean` values for PFNS, each PFNS
  slice being the trapezoid average over the `efmean` values inside its
  incident range (bounds included). The same procedure is applied to
  VIII.1, although its PFNS incident grid differs from VIII.0's.
- Reproduction gate: a QID is compared with VIII.1 only if the VIII.0 run
  reproduces the released prior means of that QID to $10^{-6}$ of the QID's
  largest value. Found before work: every cross-section, nu-bar and mubar
  QID reproduces exactly, and seven PFNS slices reproduce to $10^{-10}$;
  slices 01318, 01518 and 01618 do not (up to $2.8 \times 10^{-3}$) and are
  listed as not compared.

**Acceptance:** The shared checks, plus:

- Rows 0–2550 of `/delta`, `/sens`, `/responses/*` and the leading
  2551 × 2551 block of `/cov` equal Exercise 5's exactly.
- Snyder rows: released $E$, $C$, $\sigma_E = uE$; one non-zero
  sensitivity per row, $C/\mu$ on the MT18 state of the group holding
  $E_\text{in}$ (checked against an energy lookup); the Snyder block equals
  $D_{\sigma_E}\rho D_{\sigma_E} + s_N^2 E E^\top$, is positive definite and
  uncorrelated with every other block.
- The reference step writes both libraries' 979-state group values, the
  per-QID VIII.0 reproduction error and the gate flag; a VIII.0 run that no
  longer reproduces a QID that passed before fails loudly.
- The analysis gives Exercise 5's sections for five data sets and an
  "ENDF/B-VIII.1 comparison" section: per compared QID, the target
  adjustment $t$ against the relative mean adjustment $r$, the number of
  states moved toward VIII.1, and the number with $|z_f| \le 1$ and
  $\le 2$; per-state values in a CSV; the excluded QIDs with their
  reproduction error.
- The questions sheet answers the shape questions for Snyder (shape data
  set, normalization factor with 1.17 % prior uncertainty); the comment sheet
  states the Snyder rule.

**Result today:** Built 2026-11-23 on release 4, m = 2642. Gate green: 61
tests across Exercises 1–6; full workflow including both NJOY runs rerun from
a clean state with identical HDF5 datasets and attributes; `nda` reproduced
by the analysis to $9 \times 10^{-13}$; rows 0–2550 equal to Exercise 5's.
$\chi^2/m$ prior → posterior: integral 1.25 → 1.18; Marini nu-bar 7.55 →
1.42; Marini PFNS 0.64 → 0.31; Keegan PFNS 1.82 → 0.89; Snyder 1.37 → 1.22
(within one observation standard deviation 60 → 84 of 91). C/E prior →
linearized posterior: JEZEBEL $k_\text{eff}$ 1.00044 → 1.00038; EUCLID 3x2
0.99983 → 1.00204; EUCLID 1x8 0.99800 → 1.00108. PFNS normalization largest
deviation $2.39 \times 10^{-3}$ (slice 01418), flagged; no negative states;
largest mean shift 2.72 prior standard deviations.
ENDF/B-VIII.1 comparison over the 826 states of the 26 QIDs that pass the
gate: VIII.1 differs from the prior on 644 states, the update changed 541 of
them and moved 186 toward VIII.1; states within two standard deviations of
VIII.1 fell from 568 (prior) to 324 (posterior), of 626 with finite posterior
standard deviation. Both are automatic flags in the report: the posterior is
less consistent with VIII.1 than the prior. MT18 in groups 27–50 (22 of the
24 groups carry Snyder points): target adjustment within ±0.9 %, relative
adjustment +0.3 to +1.4 %, 7 of 24 states moved toward VIII.1, 16 of 24
within two posterior standard deviations (24 of 24 before). Not compared:
PFNS slices 01318, 01518, 01618 (reproduction error $1.5$–$2.8 \times
10^{-3}$). Completion review passed with no blockers (2026-11-23). Added
2026-11-23 to `UU_Erik_Aurora_SG52_v4` (`Ex6/`; Ex1–5 unchanged, archives
rebuilt) for the Captain to send.

**Concepts:** `DifferentialSelection` `DifferentialAlignment` `CrossSectionShapeModel` `DifferentialCovariance` `IndependentDataSets` `EndfComparison` `ReferenceGroupValues` `ReproductionGate` `TargetAdjustment` `PosteriorConsistency` `LinearizedResponses` `PfnsChecks` `UpdatedTemplate`

**Comments:** 2026-11-23, orchestrator: the specification asks only to
"compare with the ENDF/B-VIII.1 file"; nobody instructed us to process
VIII.1 ourselves. The Captain chose to process it with the released NJOY
input behind the reproduction gate. Found before work: VIII.1's ERRORR
cross-section output has no MT17 or MT37 (no MF33 covariance for them), so
the GENDF tape is the source for cross sections. VIII.1 changes are large in
the groups above 0.3 MeV: MT17 −13 to −93 %, MT37 −40 %, MT102 −51 to
+18 %, MT4 −6 to +20 %, MT16 −10 to +2 %, MT18 within ±0.9 %; PFNS slices
up to 25 % in groups holding more than $10^{-3}$ of the slice maximum.
2026-11-23, orchestrator: completion review (one round): no blockers; the
reviewer independently confirmed rows 0–2550, the Snyder rows and block,
the GENDF/ERRORR values, the gate (no subset or plain mean of nearby
`efmean` spectra reproduces the three excluded slices better than
$2.9 \times 10^{-4}$), the metrics and every "Result today" number. Fixed:
consistency and "moved toward" flags in the report, the changed-state
denominator, a `group` column, the comment sheets' Snyder exception, no
fallback to Exercise 5's prior, a repository-relative NJOY input path,
README run and gate details. Noted, not acted on: NJOY RECONR on VIII.1
prints "Error in quantum numbers for Group Number 2 and Channel Number 2"
for its second resolved range (5–30 keV, LRF = 7, SAMMY); no effect on the
values was found, and these groups lie below the fast range.
2026-11-23, orchestrator: **why the posterior moves away from VIII.1**
(one-off numpy diagnostics on the Exercise 6 files; the GLLS rerun
reproduces `nda` to $9 \times 10^{-13}$). Of the 247 states that leave the
two-standard-deviation band, 230 are PFNS; 178 leave only because
$\sigma_f$ shrank (median $\sigma_f/\sigma_i$ 0.19) with the posterior mean
still within two prior standard deviations of VIII.1, and 211 moved away.
Updating with one data set group at a time: integral only keeps 510 of 626
in the band, integral + nu-bar + Snyder 502, PFNS only 323, so the PFNS
data alone produce the loss. Rescaling each PFNS block's $C$ to the data
integral (or a free 10 % block normalization) recovers only 324 → 347.
Building every differential $\sigma_E$ on $C$ instead of $E$ (a PPP-style
variant, as in the coordinators' own Exercise 6 slide; left aside for
submissions by the 2026-10-26 meeting) gives 375 in the band and 283 of 541
changed states moved toward VIII.1 (186 as submitted).
Under our observation model the data prefer the posterior to VIII.1:
linearized $\chi^2/m$ (posterior vs VIII.1) integral 1.18 vs 22.4, Marini
nu-bar 1.42 vs 9.51, Marini PFNS 0.31 vs 0.47, Keegan PFNS 0.89 vs 1.00,
Snyder 1.22 vs 1.25. The 15 leakage-spectrum responses give 74 % of VIII.1's
integral $\chi^2$ (the EUCLID 3x2 U238 capture ratio alone another 17 %), and
PFNS slice 01118 (incident 0.64 eV–0.5 MeV, no differential data) gives
83–91 % of their linear change: VIII.1 raises its 0.03–0.5 MeV outgoing mass
by 5–8 %, and with the released sensitivities (about −0.8 to −1.0 per group)
this lowers the EUCLID leakage C/E at 2.4 MeV by 10–22 % (linearized; VIII.0
for every other nuclide). Caveats:
linearization of changes this large, other nuclides held at VIII.0, and the
VIII.1 PFNS slices averaged on VIII.0's incident energies.

## Exercise 7 · SNEAK-7A/B validation

**Data:** SNEAK-7A/B $k_\text{eff}$ and spectral indices (IRPHE
SNEAK-LMFR-EXP-001) with the release's models, and the posterior of the
preceding adjustment.

**Matrices:** Not built.

**Data treatment:** Not built.

**Assumptions:** To be fixed before work starts. **Open:** transport
calculation with an adjusted library, or a linear estimate from SNEAK
sensitivities.

**Acceptance:** C/E of every SNEAK response with prior and adjusted data;
to be extended before work starts.

**Result today:** Not started. Ignored by decision of the 2026-10-26 meeting
(`SG52_materials_release_4/email_for_v4.pdf`, Andry Monlon, 2026-11-06); the
release 4 template's folder example has no `Ex7/`.

**Concepts:** `ValidationSet` `AdjustedLibrary` `SneakCalculation` `SneakComparison`

**Comments:** —

## Exercise 8 · Add Dongwi

**Data:** Release 4. Exercise 6's 2642 rows unchanged, then the Dongwi
fission cross section, shape version (`Dongwi/nfcs_Dongwi2025_shape.json`,
EXFOR 14851002, 92 points, same incident bins as Snyder within 0.005 MeV).
Fields as for Snyder: $E$ = `experimental data.values` (b), $u$ =
`experimental data.uncertainties`, $\rho$ = `experimental data.correlations`
(92 × 92), incident energy = `experimental data.structure.limits`, $C$ =
`evaluated data.values` (ENDF/B-VIII.0 MT18), $s^\text{rel}$ =
`sensitivities.values` (92 × 52, one-hot, column 51 zero). Kept: 91 points;
the 20.54 MeV point has a zero sensitivity row. Response IDs `dongwi-00` …
`dongwi-90`; $m = 2733$. Sensitivities on `94239_00018_<group>`, $S =
C/\mu$. Normalization uncertainty $s_N = 1.34\,\%$ from the release 4
Differential README (release 3's absolute file gives 1.3426 %: absolute
covariance = shape covariance + $(0.013426)^2 E E^\top$ exactly). No
ENDF/B-VIII.1 comparison: the specification asks for it only in Exercise 6
(Captain, 2026-11-23). Workflow in `Exercise_8/`.

**Matrices:** $n = 979$, $m = 2733$. Prior and posterior as Exercise 1. Rows:
0–2641 as Exercise 6, 2642–2732 Dongwi. $\Sigma_E$ adds the full block
2642–2732 (zero against Snyder). $S$: Dongwi rows hit the same MT18 states
231–254 as Snyder.

**Data treatment:** Everything of Exercise 6's GLLS input unchanged (no
ENDF/B-VIII.1 reference). Dongwi as in the shared section ($s_N = 0.0134$),
into rows 2642–2732 of $\Delta$, $S$ and the block 2642–2732 of $\Sigma_E$.

**Assumptions:**
- Exercise 6's assumptions carry over, except the ENDF/B-VIII.1 comparison.
- Dongwi shape normalization as for Snyder: a factor with prior uncertainty
  $s_N = 1.34\,\%$, marginalized: $\Sigma_E^{(D)} = D_{\sigma_E}\rho
  D_{\sigma_E} + s_N^2 E E^\top$, $\sigma_E = uE$.
- Snyder and Dongwi are independent: no cross-covariance. The release
  declares them correlated (`CorrelatedData`) but gives no covariance
  between them, so independence is an approximation; the questions sheet
  answers "No" and says why (Captain, 2026-11-23).

**Acceptance:** The shared checks, plus:

- Rows 0–2641 of `/delta`, `/sens`, `/responses/*` and the leading
  2642 × 2642 block of `/cov` equal Exercise 6's exactly.
- Dongwi rows: released $E$, $C$, $\sigma_E = uE$; one non-zero sensitivity
  per row, $C/\mu$ on the MT18 state found by an energy lookup; the block
  equals $D_{\sigma_E}\rho D_{\sigma_E} + 0.0134^2 E E^\top$, is positive
  definite, and every block between data sets (Snyder–Dongwi included) is
  zero.
- The analysis gives Exercise 6's sections for six data sets, without the
  ENDF/B-VIII.1 comparison.
- The questions sheet answers the shape and Snyder–Dongwi questions; the
  comment sheet states the Dongwi rule.

**Result today:** Built 2026-11-23 on release 4, m = 2733. Gate green: 85
tests across Exercises 1–6 and 8; full workflow rerun from a clean state with
identical HDF5 datasets; `nda` reproduced by the analysis to
$9 \times 10^{-13}$; rows 0–2641 equal to Exercise 6's. $\chi^2/m$ prior →
posterior: integral 1.25 → 1.19; Marini nu-bar 7.55 → 1.41; Marini PFNS
0.64 → 0.31; Keegan PFNS 1.82 → 0.89; Snyder 1.37 → 1.19; Dongwi 1.47 →
1.30 (within one observation standard deviation 43 → 76 of 91). C/E prior →
linearized posterior: JEZEBEL $k_\text{eff}$ 1.00044 → 1.00037; EUCLID 3x2
0.99983 → 1.00196; EUCLID 1x8 0.99800 → 1.00094. PFNS normalization largest
deviation $2.38 \times 10^{-3}$ (slice 01418), flagged; no negative states;
largest mean shift 2.72 prior standard deviations. Adding Dongwi lowers the
smallest MT18 relative adjustment in groups 27–50 from +0.31 % (Exercise 6)
to +0.04 %; the largest stays about +1.34 %. Completion review passed with no
blockers (2026-11-23). Added 2026-11-23 to `UU_Erik_Aurora_SG52_v4` (`Ex8/`;
Ex1–6 unchanged, archives rebuilt) for the Captain to send.

**Concepts:** `DifferentialSelection` `DifferentialAlignment` `CrossSectionShapeModel` `DifferentialCovariance` `IndependentDataSets` `LinearizedResponses` `PfnsChecks` `UpdatedTemplate`

**Comments:** 2026-11-23, orchestrator: completion review (one round): no
blockers; the reviewer independently confirmed rows 0–2641, the shared
shape loader (Snyder rows unchanged), the Dongwi rows, sensitivities and
block, the zero Snyder–Dongwi block and every "Result today" number. Fixed:
the Snyder–Dongwi wording (the release declares them correlated, no
covariance given), the point-measurement answer and a docstring. Size of the
independence approximation (reviewer's one-off check): with fully
correlated normalization terms ($0.0117 \cdot 0.0134\, E_S E_D^\top$) the
MT18 relative adjustment changes by at most $3.9 \times 10^{-4}$ and its
posterior standard deviation grows by at most 1.4 %.
