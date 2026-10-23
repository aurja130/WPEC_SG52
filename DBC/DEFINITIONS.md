# Definitions

Reference set: [CONCEPTS](CONCEPTS.md) · [CODE](CODE.md) ·
[EXERCISES](EXERCISES.md) · [TESTS](TESTS.md)

Project-specific terms, and generic terms in the sense this project uses them.
Symbols follow the notation table in [CONCEPTS](CONCEPTS.md#notation). Source
names where a term comes from: **spec** (the exercise specification in the
newest release), **feedback** (coordinator feedback: the 2026-09-30 email, and
Andry Monlon's 2026-10-23 reply in `Update_email.pdf`), **release** (a release
data README), **Captain** (a decision recorded here). **Open:** marks an
unresolved question.

## Method

| Term | Meaning | Source |
|---|---|---|
| adjustment | Updating prior nuclear data with measurements so calculated responses move toward measured ones, with a posterior covariance | spec |
| GLLS (generalized linear least squares) | The linear Bayesian update $\mu_f = \mu_i + \Sigma_i S^\top V^{-1}\Delta$, $\Sigma_f = \Sigma_i - \Sigma_i S^\top V^{-1} S \Sigma_i$, in absolute form | spec, feedback |
| prior | ENDF/B-VIII.0 Pu-239 means $\mu_i$ and covariance $\Sigma_i$ before adjustment | spec |
| posterior | Mean $\mu_f$ and covariance $\Sigma_f$ after the GLLS update | spec |
| state vector, state | The 979 adjusted Pu-239 quantities in canonical order: 9 ordinary QIDs × 51 groups, 10 PFNS slices × 51 outgoing groups, 10 mubar values. A state is one entry | Captain |
| QID (quantity ID) | Release identifier of one quantity: an ENDF MT number for ordinary quantities, or a pseudo-MT for PFNS and mubar | release |
| pseudo-MT | Release-specific QID that is not an ENDF MT: 1018–1918 in steps of 100 for the ten PFNS incident-energy groups, 251–9251 in steps of 1000 for the ten mubar ranges | release |
| energy group | One bin of the 51-group structure (1e-11 to 20 MeV); PFNS incident energies use a separate 10-group structure | spec |
| MT452 | Total nu-bar (prompt plus delayed). The specification's adjusted nu-bar and the template's nu-bar column; integral sensitivities (`total nu`) land here, and so do nu-bar data under the as-MT452 rule | spec, release |
| MT456 | Prompt nu-bar. In the state vector (51 states) but absent from the relative output template. No data set has a sensitivity to it, and the released prior has no MT452–MT456 covariance (ENDF/B-VIII.0 MF31 has none), so it stays at the prior | release |
| as-MT452 rule | Marini nu-bar is used as if it measured MT452: its sensitivity rows land on MT452, and its measured and calculated values (both prompt) are used as released. Not optimal; corrected total nu-bar data derived from Marini may be released later | feedback |
| absolute covariance | Covariance in the units of the quantities themselves, e.g. $\Sigma_i$, $\Sigma_f$ | Captain |
| relative covariance | Covariance divided by the product of two means: $R = D_\mu^{-1} \Sigma D_\mu^{-1}$. Meaningless without naming which mean | Captain |
| normalized on prior | Relative results divided by the prior mean $\mu_i$, never the posterior mean; applies to the relative mean adjustment and the posterior relative covariance | feedback |
| relative sensitivity | $s_{kj} = (\partial C_k / C_k) / (\partial x_j / x_j)$, as released | release |
| absolute sensitivity | $S_{kj} = \partial C_k / \partial x_j = C_k s_{kj} / \mu_{i,j}$, the form GLLS uses | Captain |
| discrepancy | $\Delta_k = E_k - C_k$, measured minus calculated. The release's bias is $(C - E)/\sqrt{\sigma_E^2 + \sigma_C^2}$, a normalized discrepancy with the opposite sign | release |
| experimental uncertainty | Released absolute uncertainty $\sigma_E$ of a measured value (`expt_uncert`) | release |
| calculation uncertainty | Released absolute uncertainty $\sigma_C$ of a calculated value (`sim_uncert`) | release |
| sensitivity uncertainty | Released relative uncertainty of each relative sensitivity (`sens_unc_rel.csv`). Not propagated in Exercises 1–4: an assumption, answered as such in the questions sheet. The differential sets release none | release, Captain |
| `total_uncert` | Release 2 column of total response uncertainty. Not equal to the quadrature of its components for the 15 EUCLID leakage points; removed in release 3; must not be used | feedback |
| observation covariance | $\Sigma_E$, covariance of the discrepancies: block-diagonal over data sets, $\operatorname{diag}(\sigma_E^2 + \sigma_C^2)$ for the integral responses under the method rule and the differential covariance for each differential set | feedback, Captain |
| differential covariance | $D_{\sigma_E}\, \rho\, D_{\sigma_E}$ for one differential data set, with $\sigma_E = u E$ from the released relative uncertainties $u$ and correlation matrix $\rho$. No calculation uncertainty: the release gives none (assumption) | release, Captain |
| independent data sets | Assumption: zero covariance between the integral responses and each differential data set, and between differential data sets | Captain |
| differential sensitivity | A released 52-column sensitivity row of a differential point: column $g \le 50$ is the relative sensitivity to energy group $g$, column 51 is always zero. Rows for the cross-section and nu-bar sets are one-hot | release |
| PFNS observation model | How the pointwise, shape-only PFNS points (Marini, Keegan), released without sensitivities or calculated values, are predicted from the PFNS slices of the state vector. **Open:** design not fixed | Captain |
| response covariance | $V = S \Sigma_i S^\top + \Sigma_E$, the covariance of the discrepancies including prior nuclear-data uncertainty | Captain |
| linearized prediction | A response recomputed to first order, $C + S(\mu_f - \mu_i)$; not a transport calculation | Captain |
| residual identity | $E - C_f = \Sigma_E V^{-1} \Delta$: the posterior residuals follow from the update alone. Individual residuals need not shrink | Captain |
| C/E | Calculated over measured value of a response | spec |
| uncertainty reduction | Posterior over prior standard deviation, per state, QID or response | Captain |
| PFNS normalization | Each PFNS slice sums to one over its 51 outgoing groups. GLLS does not enforce it; deviations above $10^{-6}$ are flagged | Captain |
| positivity | Every posterior state is non-negative. GLLS does not enforce it; negative states are flagged | Captain |
| method rule | A rule on how to compute results, set by the coordinators: absolute GLLS with consistent normalization in any relative form; normalized on prior; experimental and calculation uncertainties instead of `total_uncert`; the release 3 template with 11 significant digits | feedback |
| assumption | A modelling choice the specification does not make, named in the exercise README, the analysis report and [EXERCISES](EXERCISES.md); e.g. zero covariance between integral responses | Captain |
| input card | One `CARD … END` block naming an HDF5 file and dataset for the GLLS program | Captain |

## Data

| Term | Meaning | Source |
|---|---|---|
| release, release data | One coordinator input package. Release 3 (2026-09-30) replaces release 2; release 2 is kept only to reproduce earlier submissions | feedback |
| observation | One measured quantity used in the update, with its calculated value, uncertainties and sensitivities | Captain |
| integral response, response | A benchmark quantity: $k_\text{eff}$, reaction-rate ratio or neutron-leakage-spectrum point of JEZEBEL or EUCLID | spec |
| response ID | Release identifier of an integral response, e.g. `PU-MET-FAST-001-001-s`, `euclid-3x2-crit`; for a differential point, the data set name and its zero-based index in released order, e.g. `marini-nubar-00` | release, Captain |
| JEZEBEL | ICSBEP PU-MET-FAST-001 bare Pu sphere: $k_\text{eff}$ and three reaction-rate ratios | spec |
| EUCLID | Experiments in two configurations, 3x2 and 1x8 (called `8x1` in the release): two $k_\text{eff}$, 15 neutron-leakage-spectrum points, eight reaction-rate ratios | spec |
| differential measurement | A measured Pu-239 quantity at given energies: Marini nu-bar and PFNS, Keegan PFNS, Snyder and Dongwi fission ratios, SACS-Cf. **Open:** the specification lists SACS-Cf but assigns it to no exercise | spec |
| differential point | One measured value of a differential data set, at one incident energy (and one outgoing energy for PFNS) | Captain |
| Marini nu-bar | Marini et al. prompt nu-bar, 25 points from 0.973 to 19.9 MeV (`nubar_Marini2021.json`). The specification cites EXFOR 14799002; the file says private communication, no EXFOR entry yet. Calculated values are ENDF/B-VIII.0 MT456 | spec, release |
| EXFOR | The nuclear reaction data library; differential data sets are cited by EXFOR entry | spec |
| validation benchmark | A benchmark kept out of the adjustment to test the result: SNEAK-7A/B | spec |
| SNEAK | IRPHE SNEAK-LMFR-EXP-001 fast critical assemblies 7A and 7B: $k_\text{eff}$ and spectral indices | spec |
| ENDF/B-VIII.0 | Evaluated library providing the prior | spec |
| ENDF/B-VIII.1 | Evaluated library the adjustment aims to approach; used for comparison | spec |
| adjusted library | Pu-239 nuclear data carrying the posterior in a format a transport code reads. **Open:** format and whether it is needed | spec |

## Submission

| Term | Meaning | Source |
|---|---|---|
| output template | The NEA results workbook. Release 3 adds sheets for the prior and the questions and allows the full covariance | feedback |
| questions sheet | The release 3 template sheet of five method questions every participant answers; the shared answers are in [EXERCISES](EXERCISES.md) | feedback |
| prior sheets | The release 3 template sheets `prior_abs` (absolute prior mean as ingested) and `prior_cov_rel_to_prior` (prior covariance normalized on prior) | feedback |
| submission | The filled output template for one exercise, sent to the NEA | spec |
| template state selection | The 928 states the release 3 template holds, in its axis order: MT2, 4, 16, 17, 18, 37, 102 (51 groups each), ten mubar, MT452, ten PFNS slices; all states except MT456. Before 2026-10-22, split into 418 cross-section and mubar plus 510 PFNS states for the release 2 template | Captain |
| relative mean adjustment | $(\mu_f - \mu_i)/\mu_i$ per state | spec |
| absolute workbook | Our own workbook with all 979 states, prior and posterior means and full absolute covariances | Captain |

## Working terms

| Term | Meaning | Source |
|---|---|---|
| DBC (Driven by Concepts) | Working method: the Captain leads through the concept set in this folder, which must match the code | Captain |
| concept node | One box in a [CONCEPTS](CONCEPTS.md) diagram, with a stable CamelCase ID | Captain |
| exercise | One of the eight SG52 adjustment tasks, each with its own data selection and submission | spec |
| acceptance check | An observable condition an exercise must meet before its results go to the NEA | Captain |
| result today | The numbers the current workflow produces for an exercise, as recorded in [EXERCISES](EXERCISES.md) | Captain |
