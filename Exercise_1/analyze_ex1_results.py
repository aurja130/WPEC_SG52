#!/usr/bin/env python3
"""
Comprehensive diagnostics for WPEC SG52 Exercise 1 (JEZEBEL k_eff GLLS).

Expected input files
--------------------
ex1_prior.hdf5
    /mean/values            shape (979,)
    /cov/values             shape (979, 979)

ex1_observations.hdf5
    /delta/values           shape (1,)
    /sens/values            shape (1, 979)
    /cov/values             shape (1, 1)

ex1_results.hdf5
    /mean/values            shape (979,)
    /covariance/values      shape (979, 979)

The script reconstructs the canonical SG52 Exercise-1 Pu-239 state ordering:

  9 ordinary quantities x 51 groups = 459
  10 PFNS incident-energy slices x 51 outgoing groups = 510
  10 mubar incident-energy slices x 1 value = 10
  ---------------------------------------------------------
  total = 979

It performs:
  * shape, finiteness, symmetry and PSD diagnostics
  * direct reproduction of the GLLS posterior from the inputs
  * response-space diagnostics and the exact scalar residual identity
  * prior/posterior uncertainty comparisons
  * absolute, relative, and prior-sigma-normalized mean adjustments
  * response-variance decomposition by family and QID
  * PFNS normalization and positivity checks
  * CSV exports and diagnostic plots

The raw relative mean adjustment

    (mu_f - mu_i) / mu_i

is retained, but should not be used as the primary ranking statistic when
mu_i is tiny.  The preferred mean-adjustment diagnostic is

    (mu_f - mu_i) / sigma_i.

Usage
Run from the repository root with the Exercise 1 data files in this directory:

    python Exercise_1/analyze_ex1_results.py

Paths can also be overridden with `--prior`, `--observations`, and
`--posterior`. The default output directory is `Exercise_1/ex1_analysis`.

For SG52 Exercise 1 the experimental JEZEBEL k_eff is 1.0.  This is used
only to display C/E-like quantities; all GLLS consistency checks use the
matrices/vectors themselves.
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, TypedDict, cast

import h5py
import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.intp]
BoolArray = NDArray[np.bool_]
StringArray = NDArray[np.str_]


def float_at(values: FloatArray, index: int) -> float:
    return float(cast(np.float64, values[index]))


def float_at_2d(values: FloatArray, row: int, column: int) -> float:
    return float(cast(np.float64, values[row, column]))


def int_at(values: IntArray, index: int) -> int:
    return int(cast(np.intp, values[index]))


def bool_at(values: BoolArray, index: int) -> bool:
    return bool(cast(np.bool_, values[index]))


def string_at(values: StringArray, index: int) -> str:
    return str(cast(np.str_, values[index]))


class PlotFigure(Protocol):
    def tight_layout(self) -> None: ...

    def savefig(self, fname: Path, *, dpi: int) -> None: ...


class PlotAxes(Protocol):
    def plot(self, *args: object, **kwargs: object) -> object: ...

    def bar(self, *args: object, **kwargs: object) -> object: ...

    def axhline(self, y: float, **kwargs: object) -> object: ...

    def set_xlabel(self, label: str) -> object: ...

    def set_ylabel(self, label: str) -> object: ...

    def set_title(self, label: str) -> object: ...

    def set_xticks(self, ticks: object) -> object: ...

    def set_xticklabels(self, labels: object, *, rotation: int) -> object: ...

    def legend(self) -> object: ...


class PlotModule(Protocol):
    def subplots(
        self, *, figsize: tuple[float, float] | None = None
    ) -> tuple[PlotFigure, PlotAxes]: ...

    def close(self, figure: PlotFigure) -> None: ...


def as_plot_module(module: object) -> PlotModule:
    return cast(PlotModule, module)


@dataclass
class AnalysisArgs(argparse.Namespace):
    prior: Path = field(init=False)
    observations: Path = field(init=False)
    posterior: Path = field(init=False)
    output_dir: Path = field(init=False)
    top: int = field(init=False)
    e_obs: float = field(init=False)
    relative_denominator_sigma_ratio: float = field(init=False)
    variance_tolerance: float = field(init=False)
    reproduction_tolerance: float = field(init=False)
    residual_identity_tolerance: float = field(init=False)
    response_uncertainty_ratio_flag: float = field(init=False)
    pfns_normalization_tolerance: float = field(init=False)


class PfnsRow(TypedDict):
    qid: str
    incident_group: int
    prior_sum: float
    posterior_sum: float
    sum_change: float
    prior_negative_bins: int
    posterior_negative_bins: int
    prior_min: float
    posterior_min: float
    prior_sum_variance: float
    posterior_sum_variance: float


class StateRow(TypedDict):
    index: int
    label: str
    family: str
    qid: str
    group: int | str
    incident_group: int | str
    outgoing_group: int | str
    mu_i: float
    mu_f: float
    delta_mu: float
    relative_adjustment: float
    prior_std: float
    posterior_std: float
    standardized_shift_prior_sigma: float
    posterior_prior_std_ratio: float
    posterior_prior_variance_ratio: float
    abs_mu_i_over_prior_std: float
    relative_denominator_fragile: bool
    sensitivity: float
    response_variance_contribution: float
    prior_negative: bool
    posterior_negative: bool


class SummaryRow(TypedDict):
    family: str
    n_parameters: int
    n_nonzero_sensitivity: int
    max_abs_standardized_shift: float
    max_abs_relative_adjustment_stable_denominator: float
    min_posterior_prior_std_ratio: float
    n_reduced_variance: int
    n_increased_variance: int
    n_posterior_negative: int
    response_variance_contribution: float


class QidSummaryRow(SummaryRow):
    qid: str


EXERCISE_DIRECTORY = Path(__file__).resolve().parent
# Canonical SG52 Exercise-1 Pu-239 state ordering
# ---------------------------------------------------------------------------

ZAID = "94239"

PRIOR_MTS = [
    "00002",  # elastic
    "00004",  # inelastic
    "00016",  # (n,2n)
    "00017",  # (n,3n)
    "00018",  # fission
    "00037",  # (n,4n)
    "00102",  # capture
    "00452",  # total nubar
    "00456",  # prompt nubar
]

PRIOR_PFNS_IDS = [
    "01018",
    "01118",
    "01218",
    "01318",
    "01418",
    "01518",
    "01618",
    "01718",
    "01818",
    "01918",
]

PRIOR_MUBAR_IDS = [
    "00251",
    "01251",
    "02251",
    "03251",
    "04251",
    "05251",
    "06251",
    "07251",
    "08251",
    "09251",
]

N_GROUPS = 51
EXPECTED_STATE_SIZE = 979


@dataclass(frozen=True)
class StateMeta:
    index: int
    label: str
    family: str
    qid: str
    group: int | None
    incident_group: int | None
    outgoing_group: int | None


def build_state_metadata() -> list[StateMeta]:
    metadata: list[StateMeta] = []
    i = 0

    for qid in PRIOR_MTS:
        for group in range(N_GROUPS):
            metadata.append(
                StateMeta(
                    index=i,
                    label=f"{ZAID}_{qid}_{group}",
                    family="mt",
                    qid=qid,
                    group=group,
                    incident_group=None,
                    outgoing_group=None,
                )
            )
            i += 1

    for incident_group, qid in enumerate(PRIOR_PFNS_IDS):
        for outgoing_group in range(N_GROUPS):
            metadata.append(
                StateMeta(
                    index=i,
                    label=f"{ZAID}_{qid}_{outgoing_group}",
                    family="pfns",
                    qid=qid,
                    group=outgoing_group,
                    incident_group=incident_group,
                    outgoing_group=outgoing_group,
                )
            )
            i += 1

    for incident_group, qid in enumerate(PRIOR_MUBAR_IDS):
        metadata.append(
            StateMeta(
                index=i,
                label=f"{ZAID}_{qid}",
                family="mubar",
                qid=qid,
                group=None,
                incident_group=incident_group,
                outgoing_group=None,
            )
        )
        i += 1

    if len(metadata) != EXPECTED_STATE_SIZE:
        raise RuntimeError(
            f"Internal state metadata has size {len(metadata)}, "
            + f"expected {EXPECTED_STATE_SIZE}."
        )

    return metadata


# ---------------------------------------------------------------------------
# HDF5 readers
# ---------------------------------------------------------------------------


def read_dataset(path: Path, dataset: str) -> FloatArray:
    with h5py.File(str(path), "r") as h5:
        if dataset not in h5:
            raise KeyError(f"{path}: dataset {dataset!r} not found")
        hdf5_dataset = cast(h5py.Dataset, h5[dataset])
        return np.asarray(hdf5_dataset[()], dtype=np.float64)


def read_inputs(
    args: AnalysisArgs,
) -> tuple[
    FloatArray, FloatArray, FloatArray, FloatArray, FloatArray, FloatArray, FloatArray
]:
    mu_i = read_dataset(args.prior, "mean/values")
    Sigma_i = read_dataset(args.prior, "cov/values")
    Delta_E_i = read_dataset(args.observations, "delta/values")
    S = read_dataset(args.observations, "sens/values")
    Sigma_E = read_dataset(args.observations, "cov/values")

    mu_f = read_dataset(args.posterior, "mean/values")
    Sigma_f = read_dataset(args.posterior, "covariance/values")

    return mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------


def safe_std_from_cov(cov: FloatArray) -> FloatArray:
    diag: FloatArray = np.diag(cov)
    largest_diagonal = float(cast(np.float64, np.max(np.abs(diag))))
    tiny_negative = (diag < 0.0) & (diag > -1e-14 * max(1.0, largest_diagonal))
    diag = diag.copy()
    diag[tiny_negative] = 0.0

    if np.any(diag < 0.0):
        bad: IntArray = cast(IntArray, np.flatnonzero(diag < 0.0))
        bad_indices = [int_at(bad, index) for index in range(min(20, bad.size))]
        raise ValueError(
            "Covariance has materially negative diagonal entries at indices "
            + f"{bad_indices}"
        )
    return cast(FloatArray, np.sqrt(diag))


def matrix_symmetry_error(matrix: FloatArray) -> float:
    difference: FloatArray = cast(FloatArray, np.abs(matrix - matrix.T))
    return float(np.max(difference))


class EigenDiagnostics(TypedDict):
    min_eigenvalue: float
    max_eigenvalue: float
    psd_tolerance: float
    psd_within_tolerance: bool


def eig_diagnostics(matrix: FloatArray) -> EigenDiagnostics:
    sym: FloatArray = 0.5 * (matrix + matrix.T)
    eigvals: FloatArray = cast(FloatArray, np.linalg.eigvalsh(sym))

    min_eig = float_at(eigvals, 0)
    max_eig = float_at(eigvals, eigvals.size - 1)
    scale = max(1.0, abs(max_eig))
    tolerance = 1e-10 * scale

    return {
        "min_eigenvalue": min_eig,
        "max_eigenvalue": max_eig,
        "psd_tolerance": tolerance,
        "psd_within_tolerance": bool(min_eig >= -tolerance),
    }


def fmt(x: float) -> str:
    return f"{x:.12g}"


def max_abs_difference(a: FloatArray, b: FloatArray) -> float:
    difference: FloatArray = cast(FloatArray, np.abs(a - b))
    return float(np.max(difference))


def relative_frobenius_difference(a: FloatArray, b: FloatArray) -> float:
    denom = float(cast(np.float64, np.linalg.norm(a)))
    if denom == 0.0:
        return float(cast(np.float64, np.linalg.norm(a - b)))
    return float(cast(np.float64, np.linalg.norm(a - b))) / denom


def top_indices(values: FloatArray, n: int) -> list[int]:
    finite: FloatArray = cast(
        FloatArray, np.where(np.isfinite(values), np.abs(values), -np.inf)
    )
    ordered: IntArray = np.argsort(finite)[::-1][:n]
    return [int_at(ordered, index) for index in range(ordered.size)]


def grouped_indices(
    metadata: list[StateMeta], attribute: Literal["family", "qid"]
) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}
    for meta in metadata:
        key = meta.family if attribute == "family" else meta.qid
        groups.setdefault(key, []).append(meta.index)
    return groups


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------


def write_csv(
    path: Path, fieldnames: list[str], rows: Iterable[Mapping[str, object]]
) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Plot helpers
# ---------------------------------------------------------------------------


def make_plots(
    output_dir: Path,
    metadata: list[StateMeta],
    standardized_shift: FloatArray,
    std_ratio: FloatArray,
    qid_rows: list[QidSummaryRow],
    pfns_rows: list[PfnsRow],
) -> list[str]:
    try:
        from matplotlib import pyplot
    except ImportError:
        return ["matplotlib not installed; plots skipped"]

    plt = as_plot_module(pyplot)
    messages: list[str] = []
    x = np.arange(len(metadata))

    # Plot 1: mean adjustment in prior-sigma units
    fig, ax = plt.subplots()
    _ = ax.plot(x, standardized_shift)
    _ = ax.axhline(0.0, linewidth=0.8)
    _ = ax.set_xlabel("Canonical state index")
    _ = ax.set_ylabel(r"$(\mu_f-\mu_i)/\sigma_i$")
    _ = ax.set_title("Exercise 1 mean adjustment in prior-sigma units")
    fig.tight_layout()
    fig.savefig(output_dir / "mean_adjustment_prior_sigma.png", dpi=180)
    plt.close(fig)

    # Plot 2: posterior/prior standard deviation ratio
    fig, ax = plt.subplots()
    _ = ax.plot(x, std_ratio)
    _ = ax.axhline(1.0, linewidth=0.8)
    _ = ax.set_xlabel("Canonical state index")
    _ = ax.set_ylabel(r"$\sigma_f/\sigma_i$")
    _ = ax.set_title("Exercise 1 posterior/prior standard deviation")
    fig.tight_layout()
    fig.savefig(output_dir / "posterior_prior_std_ratio.png", dpi=180)
    plt.close(fig)

    # Plot 3: response variance contribution by QID
    qid_labels = [str(row["qid"]) for row in qid_rows]
    qid_contrib = [float(row["response_variance_contribution"]) for row in qid_rows]

    fig, ax = plt.subplots(figsize=(max(8.0, 0.35 * len(qid_labels)), 5.0))
    _ = ax.bar(np.arange(len(qid_labels)), qid_contrib)
    _ = ax.axhline(0.0, linewidth=0.8)
    _ = ax.set_xticks(np.arange(len(qid_labels)))
    _ = ax.set_xticklabels(qid_labels, rotation=90)
    _ = ax.set_ylabel(r"Contribution to $S\Sigma_iS^T$")
    _ = ax.set_title("Exercise 1 response-variance contribution by QID")
    fig.tight_layout()
    fig.savefig(output_dir / "response_variance_contribution_by_qid.png", dpi=180)
    plt.close(fig)

    # Plot 4: PFNS normalization before/after
    if pfns_rows:
        pfns_labels = [str(row["qid"]) for row in pfns_rows]
        prior_sums = [float(row["prior_sum"]) for row in pfns_rows]
        posterior_sums = [float(row["posterior_sum"]) for row in pfns_rows]
        positions = np.arange(len(pfns_labels))

        fig, ax = plt.subplots()
        _ = ax.plot(positions, prior_sums, marker="o", label="Prior")
        _ = ax.plot(positions, posterior_sums, marker="o", label="Posterior")
        _ = ax.axhline(1.0, linewidth=0.8)
        _ = ax.set_xticks(positions)
        _ = ax.set_xticklabels(pfns_labels, rotation=45)
        _ = ax.set_ylabel("Sum over 51 outgoing groups")
        _ = ax.set_title("PFNS normalization diagnostic")
        _ = ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "pfns_normalization.png", dpi=180)
        plt.close(fig)

    messages.append("plots written")
    return messages


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------


def analyze(args: AnalysisArgs) -> str:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = build_state_metadata()
    labels: StringArray = np.asarray([m.label for m in metadata], dtype=np.str_)
    families: StringArray = np.asarray([m.family for m in metadata], dtype=np.str_)
    qids: StringArray = np.asarray([m.qid for m in metadata], dtype=np.str_)

    mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f = read_inputs(args)

    # ----------------------
    # Basic shape validation
    # ----------------------
    n = EXPECTED_STATE_SIZE

    expected_shapes: dict[str, tuple[int, ...]] = {
        "mu_x_i": (n,),
        "Sigma_x_i": (n, n),
        "Delta_E_i": (1,),
        "S": (1, n),
        "Sigma_E": (1, 1),
        "mu_x_f": (n,),
        "Sigma_x_f": (n, n),
    }

    actual_shapes: dict[str, tuple[int, ...]] = {
        "mu_x_i": mu_i.shape,
        "Sigma_x_i": Sigma_i.shape,
        "Delta_E_i": Delta_E_i.shape,
        "S": S.shape,
        "Sigma_E": Sigma_E.shape,
        "mu_x_f": mu_f.shape,
        "Sigma_x_f": Sigma_f.shape,
    }

    for name, expected in expected_shapes.items():
        actual = actual_shapes[name]
        if actual != expected:
            raise ValueError(f"{name}: shape {actual}, expected {expected}")

    arrays: dict[str, FloatArray] = {
        "mu_x_i": mu_i,
        "Sigma_x_i": Sigma_i,
        "Delta_E_i": Delta_E_i,
        "S": S,
        "Sigma_E": Sigma_E,
        "mu_x_f": mu_f,
        "Sigma_x_f": Sigma_f,
    }
    for name, array in arrays.items():
        if not np.all(np.isfinite(array)):
            bad: IntArray = np.argwhere(~np.isfinite(array))
            bad_rows: list[list[int]] = cast(list[list[int]], bad[:20].tolist())
            raise ValueError(f"{name} contains non-finite values at " + f"{bad_rows}")

    # ----------------------
    # Reproduce GLLS update
    # ----------------------
    A = Sigma_i @ S.T
    V = S @ A + Sigma_E

    # K = Sigma_i S^T V^{-1}, formed via solves rather than explicit inverse.
    K = np.linalg.solve(V, A.T).T

    expected_delta_mu = K @ Delta_E_i
    expected_mu_f = mu_i + expected_delta_mu
    expected_Sigma_f = Sigma_i - K @ (S @ Sigma_i)

    mean_update_max_abs_error = max_abs_difference(mu_f, expected_mu_f)
    mean_update_rel_error = relative_frobenius_difference(expected_mu_f, mu_f)

    covariance_update_max_abs_error = max_abs_difference(Sigma_f, expected_Sigma_f)
    covariance_update_rel_error = relative_frobenius_difference(
        expected_Sigma_f, Sigma_f
    )

    # ----------------------
    # State-space diagnostics
    # ----------------------
    delta_mu = mu_f - mu_i

    prior_std = safe_std_from_cov(Sigma_i)
    posterior_std = safe_std_from_cov(Sigma_f)

    relative_adjustment: FloatArray = np.full(n, np.nan, dtype=np.float64)
    nonzero_prior_mean: BoolArray = cast(BoolArray, mu_i != 0.0)
    _ = np.divide(delta_mu, mu_i, out=relative_adjustment, where=nonzero_prior_mean)

    standardized_shift: FloatArray = np.zeros(n, dtype=np.float64)
    nonzero_prior_std: BoolArray = cast(BoolArray, prior_std != 0.0)
    _ = np.divide(delta_mu, prior_std, out=standardized_shift, where=nonzero_prior_std)

    std_ratio: FloatArray = np.ones(n, dtype=np.float64)
    _ = np.divide(posterior_std, prior_std, out=std_ratio, where=nonzero_prior_std)

    variance_ratio: FloatArray = np.ones(n, dtype=np.float64)
    prior_var: FloatArray = prior_std**2
    posterior_var: FloatArray = posterior_std**2
    nonzero_prior_variance: BoolArray = cast(BoolArray, prior_var != 0.0)
    _ = np.divide(
        posterior_var,
        prior_var,
        out=variance_ratio,
        where=nonzero_prior_variance,
    )

    mean_to_prior_std: FloatArray = np.full(n, np.inf, dtype=np.float64)
    _ = np.divide(
        np.abs(mu_i),
        prior_std,
        out=mean_to_prior_std,
        where=nonzero_prior_std,
    )

    # Raw relative adjustments become numerically/interpretively fragile when
    # the prior mean is essentially zero compared with its own prior std.
    relative_denominator_fragile: BoolArray = cast(
        BoolArray,
        (mu_i == 0.0)
        | (
            nonzero_prior_std
            & (mean_to_prior_std < args.relative_denominator_sigma_ratio)
        ),
    )

    covariance_reduction = Sigma_i - Sigma_f

    prior_cov_diag = eig_diagnostics(Sigma_i)
    posterior_cov_diag = eig_diagnostics(Sigma_f)
    reduction_cov_diag = eig_diagnostics(covariance_reduction)

    prior_sym_error = matrix_symmetry_error(Sigma_i)
    posterior_sym_error = matrix_symmetry_error(Sigma_f)

    variance_tolerance = args.variance_tolerance * max(
        1.0,
        float(np.max(prior_var)),
    )

    reduced_uncertainty_exact: BoolArray = posterior_var < prior_var
    increased_uncertainty_exact: BoolArray = posterior_var > prior_var

    reduced_uncertainty: BoolArray = posterior_var < (prior_var - variance_tolerance)
    increased_uncertainty: BoolArray = posterior_var > (prior_var + variance_tolerance)

    # ----------------------
    # Response-space diagnostics
    # ----------------------
    response_shift: FloatArray = S @ delta_mu
    posterior_residual: FloatArray = Delta_E_i - response_shift

    nd_response_cov: FloatArray = S @ Sigma_i @ S.T
    posterior_nd_response_cov: FloatArray = S @ Sigma_f @ S.T

    prior_nd_response_std = float(
        cast(np.float64, np.sqrt(max(float_at_2d(nd_response_cov, 0, 0), 0.0)))
    )
    posterior_nd_response_std = float(
        cast(
            np.float64,
            np.sqrt(max(float_at_2d(posterior_nd_response_cov, 0, 0), 0.0)),
        )
    )
    observation_std = float(
        cast(np.float64, np.sqrt(max(float_at_2d(Sigma_E, 0, 0), 0.0)))
    )
    innovation_std = float(cast(np.float64, np.sqrt(max(float_at_2d(V, 0, 0), 0.0))))

    response_variance_ratio_to_observation = (
        prior_nd_response_std / observation_std if observation_std != 0.0 else np.inf
    )

    residual_fraction_actual = (
        float_at(posterior_residual, 0) / float_at(Delta_E_i, 0)
        if float_at(Delta_E_i, 0) != 0.0
        else np.nan
    )

    residual_fraction_expected = (
        float_at_2d(Sigma_E, 0, 0) / float_at_2d(V, 0, 0)
        if float_at_2d(V, 0, 0) != 0.0
        else np.nan
    )

    residual_identity_error = (
        abs(residual_fraction_actual - residual_fraction_expected)
        if np.isfinite(residual_fraction_actual)
        and np.isfinite(residual_fraction_expected)
        else np.nan
    )

    # Optional JEZEBEL-specific presentation of calculated k_eff / C/E.
    e_obs = float(args.e_obs)
    e_calc_i = e_obs - float_at(Delta_E_i, 0)
    e_calc_f = e_calc_i + float_at(response_shift, 0)

    c_over_e_i = e_calc_i / e_obs if e_obs != 0.0 else np.nan
    c_over_e_f = e_calc_f / e_obs if e_obs != 0.0 else np.nan

    # ----------------------
    # Response variance decomposition
    # ----------------------
    # For one response:
    #   S Sigma S^T = sum_i S_i (Sigma S^T)_i
    #
    # Individual contributions may be negative because of covariance
    # cross-terms, but they sum exactly to the total propagated variance.
    sensitivity: FloatArray = S[0, :]
    sigma_s: FloatArray = Sigma_i @ sensitivity
    component_response_variance_contribution: FloatArray = sensitivity * sigma_s

    component_contribution_sum = float(np.sum(component_response_variance_contribution))
    component_contribution_error = abs(
        component_contribution_sum - float_at_2d(nd_response_cov, 0, 0)
    )

    # ----------------------
    # PFNS normalization/positivity diagnostics
    # ----------------------
    pfns_rows: list[PfnsRow] = []

    for qid in PRIOR_PFNS_IDS:
        matches: BoolArray = cast(BoolArray, qids == qid)
        pfns_indices: IntArray = np.flatnonzero(matches)
        prior_block: FloatArray = Sigma_i[np.ix_(pfns_indices, pfns_indices)]
        posterior_block: FloatArray = Sigma_f[np.ix_(pfns_indices, pfns_indices)]
        ones: FloatArray = np.ones(len(pfns_indices), dtype=np.float64)

        pfns_rows.append(
            {
                "qid": qid,
                "incident_group": int(PRIOR_PFNS_IDS.index(qid)),
                "prior_sum": float(np.sum(mu_i[pfns_indices])),
                "posterior_sum": float(np.sum(mu_f[pfns_indices])),
                "sum_change": float(
                    np.sum(mu_f[pfns_indices]) - np.sum(mu_i[pfns_indices])
                ),
                "prior_negative_bins": int(np.sum(mu_i[pfns_indices] < 0.0)),
                "posterior_negative_bins": int(np.sum(mu_f[pfns_indices] < 0.0)),
                "prior_min": float(np.min(mu_i[pfns_indices])),
                "posterior_min": float(np.min(mu_f[pfns_indices])),
                "prior_sum_variance": float(ones @ prior_block @ ones),
                "posterior_sum_variance": float(ones @ posterior_block @ ones),
            }
        )

    write_csv(
        output_dir / "pfns_normalization.csv",
        list(pfns_rows[0].keys()),
        pfns_rows,
    )

    # ----------------------
    # Full per-state CSV
    # ----------------------
    state_rows: list[StateRow] = []

    for meta in metadata:
        i = meta.index
        state_rows.append(
            {
                "index": i,
                "label": meta.label,
                "family": meta.family,
                "qid": meta.qid,
                "group": "" if meta.group is None else meta.group,
                "incident_group": (
                    "" if meta.incident_group is None else meta.incident_group
                ),
                "outgoing_group": (
                    "" if meta.outgoing_group is None else meta.outgoing_group
                ),
                "mu_i": float_at(mu_i, i),
                "mu_f": float_at(mu_f, i),
                "delta_mu": float_at(delta_mu, i),
                "relative_adjustment": float_at(relative_adjustment, i),
                "prior_std": float_at(prior_std, i),
                "posterior_std": float_at(posterior_std, i),
                "standardized_shift_prior_sigma": float_at(standardized_shift, i),
                "posterior_prior_std_ratio": float_at(std_ratio, i),
                "posterior_prior_variance_ratio": float_at(variance_ratio, i),
                "abs_mu_i_over_prior_std": float_at(mean_to_prior_std, i),
                "relative_denominator_fragile": bool_at(
                    relative_denominator_fragile, i
                ),
                "sensitivity": float_at_2d(S, 0, i),
                "response_variance_contribution": float_at(
                    component_response_variance_contribution, i
                ),
                "prior_negative": float_at(mu_i, i) < 0.0,
                "posterior_negative": float_at(mu_f, i) < 0.0,
            }
        )

    state_fieldnames = list(state_rows[0].keys())
    write_csv(output_dir / "state_summary.csv", state_fieldnames, state_rows)

    # ----------------------
    # Group summaries
    # ----------------------
    family_groups = grouped_indices(metadata, "family")
    qid_groups = grouped_indices(metadata, "qid")

    family_rows: list[SummaryRow] = []
    for family, idx_list in family_groups.items():
        family_indices: IntArray = np.asarray(idx_list, dtype=np.intp)
        stable = family_indices[~relative_denominator_fragile[family_indices]]
        stable_rel_max = (
            float(cast(np.float64, np.nanmax(np.abs(relative_adjustment[stable]))))
            if stable.size
            else np.nan
        )

        family_rows.append(
            {
                "family": family,
                "n_parameters": int(family_indices.size),
                "n_nonzero_sensitivity": int(
                    np.count_nonzero(sensitivity[family_indices])
                ),
                "max_abs_standardized_shift": float(
                    cast(np.float64, np.max(np.abs(standardized_shift[family_indices])))
                ),
                "max_abs_relative_adjustment_stable_denominator": stable_rel_max,
                "min_posterior_prior_std_ratio": float(
                    np.min(std_ratio[family_indices])
                ),
                "n_reduced_variance": int(np.sum(reduced_uncertainty[family_indices])),
                "n_increased_variance": int(
                    np.sum(increased_uncertainty[family_indices])
                ),
                "n_posterior_negative": int(np.sum(mu_f[family_indices] < 0.0)),
                "response_variance_contribution": float(
                    np.sum(component_response_variance_contribution[family_indices])
                ),
            }
        )
    write_csv(
        output_dir / "family_summary.csv",
        list(family_rows[0].keys()),
        family_rows,
    )

    qid_rows: list[QidSummaryRow] = []
    for qid, idx_list in qid_groups.items():
        qid_indices: IntArray = np.asarray(idx_list, dtype=np.intp)
        stable = qid_indices[~relative_denominator_fragile[qid_indices]]
        stable_rel_max = (
            float(cast(np.float64, np.nanmax(np.abs(relative_adjustment[stable]))))
            if stable.size
            else np.nan
        )

        qid_rows.append(
            {
                "qid": qid,
                "family": string_at(families, int_at(qid_indices, 0)),
                "n_parameters": int(qid_indices.size),
                "n_nonzero_sensitivity": int(
                    np.count_nonzero(sensitivity[qid_indices])
                ),
                "max_abs_standardized_shift": float(
                    cast(np.float64, np.max(np.abs(standardized_shift[qid_indices])))
                ),
                "max_abs_relative_adjustment_stable_denominator": stable_rel_max,
                "min_posterior_prior_std_ratio": float(np.min(std_ratio[qid_indices])),
                "n_reduced_variance": int(np.sum(reduced_uncertainty[qid_indices])),
                "n_increased_variance": int(np.sum(increased_uncertainty[qid_indices])),
                "n_posterior_negative": int(np.sum(mu_f[qid_indices] < 0.0)),
                "response_variance_contribution": float(
                    np.sum(component_response_variance_contribution[qid_indices])
                ),
            }
        )

    # Put largest absolute variance contributors first in this summary.
    qid_rows.sort(
        key=lambda row: abs(float(row["response_variance_contribution"])),
        reverse=True,
    )

    write_csv(
        output_dir / "qid_summary.csv",
        list(qid_rows[0].keys()),
        qid_rows,
    )

    # ----------------------
    # Human-readable report
    # ----------------------
    top_n = args.top
    lines: list[str] = []

    def add(text: str = "") -> None:
        lines.append(text)

    add("=" * 78)
    add("WPEC SG52 EXERCISE 1 — GLLS RESULT DIAGNOSTICS")
    add("=" * 78)
    add()

    add("INPUT DIMENSIONS")
    add("-" * 78)
    for name, shape in actual_shapes.items():
        add(f"{name:16s}: {shape}")
    add()

    add("COVARIANCE NUMERICS")
    add("-" * 78)
    add(f"Prior symmetry max |A-A^T|      : {fmt(prior_sym_error)}")
    add(f"Posterior symmetry max |A-A^T|  : {fmt(posterior_sym_error)}")
    add(
        "Prior min/max eigenvalue         : "
        + f"{fmt(float(prior_cov_diag['min_eigenvalue']))} / "
        + f"{fmt(float(prior_cov_diag['max_eigenvalue']))}"
    )
    add(
        "Posterior min/max eigenvalue     : "
        + f"{fmt(float(posterior_cov_diag['min_eigenvalue']))} / "
        + f"{fmt(float(posterior_cov_diag['max_eigenvalue']))}"
    )
    add(
        "Covariance reduction min/max eig : "
        + f"{fmt(float(reduction_cov_diag['min_eigenvalue']))} / "
        + f"{fmt(float(reduction_cov_diag['max_eigenvalue']))}"
    )
    add(f"Prior PSD within tolerance        : {prior_cov_diag['psd_within_tolerance']}")
    add(
        "Posterior PSD within tolerance    : "
        + f"{posterior_cov_diag['psd_within_tolerance']}"
    )
    add(
        "Reduction PSD within tolerance    : "
        + f"{reduction_cov_diag['psd_within_tolerance']}"
    )
    add()

    add("DIRECT GLLS REPRODUCTION")
    add("-" * 78)
    add(f"Mean max absolute mismatch       : {fmt(mean_update_max_abs_error)}")
    add(f"Mean relative norm mismatch      : {fmt(mean_update_rel_error)}")
    add(f"Covariance max absolute mismatch : {fmt(covariance_update_max_abs_error)}")
    add(f"Covariance relative norm mismatch: {fmt(covariance_update_rel_error)}")
    add()

    add("JEZEBEL RESPONSE CHECK")
    add("-" * 78)
    add(f"E_obs                              : {fmt(e_obs)}")
    add(f"E_calc,i                           : {fmt(e_calc_i)}")
    add(f"Delta_E_i = E_obs - E_calc,i      : {fmt(float_at(Delta_E_i, 0))}")
    add(f"S (mu_f - mu_i)                   : {fmt(float_at(response_shift, 0))}")
    add(f"E_calc,f (linear reconstruction)  : {fmt(e_calc_f)}")
    add(
        "Posterior residual E_obs-E_calc,f : "
        + f"{fmt(float_at(posterior_residual, 0))}"
    )
    add(f"Prior C/E                         : {fmt(c_over_e_i)}")
    add(f"Posterior C/E                     : {fmt(c_over_e_f)}")
    add()
    add(f"sqrt(S Sigma_i S^T)               : {fmt(prior_nd_response_std)}")
    add(f"sqrt(S Sigma_f S^T)               : {fmt(posterior_nd_response_std)}")
    add(f"sqrt(Sigma_E)                     : {fmt(observation_std)}")
    add(f"sqrt(V)                           : {fmt(innovation_std)}")
    add(
        "Prior ND response std / obs std   : "
        + f"{fmt(response_variance_ratio_to_observation)}"
    )
    add()
    add(f"Actual residual fraction          : {fmt(residual_fraction_actual)}")
    add(f"Expected scalar residual fraction : {fmt(residual_fraction_expected)}")
    add(f"Absolute identity mismatch        : {fmt(residual_identity_error)}")
    add()

    add("MEAN ADJUSTMENT SUMMARY")
    add("-" * 78)
    max_abs_standardized_shift: np.float64 = cast(
        np.float64, np.max(np.abs(standardized_shift))
    )
    add(
        "Max |delta_mu / prior_std|        : "
        + f"{fmt(float(max_abs_standardized_shift))}"
    )
    add(f"Posterior negative state values   : {int(np.sum(mu_f < 0.0))} / {n}")
    add(
        "Fragile relative denominators     : "
        + f"{int(np.sum(relative_denominator_fragile))} / {n}"
    )
    add(
        "  criterion: |mu_i|/sigma_i < "
        + f"{args.relative_denominator_sigma_ratio:g} "
        + "(plus exact zero means)"
    )
    add()

    add(f"TOP {top_n} MEAN SHIFTS IN PRIOR-SIGMA UNITS (PRIMARY RANKING)")
    add("-" * 78)
    for i in top_indices(standardized_shift, top_n):
        add(
            f"{string_at(labels, i):20s} "
            + f"z={fmt(float_at(standardized_shift, i)):>15s} "
            + f"delta={fmt(float_at(delta_mu, i)):>15s} "
            + f"mu_i={fmt(float_at(mu_i, i)):>15s} "
            + f"sigma_i={fmt(float_at(prior_std, i)):>15s}"
        )
    add()

    stable_relative = relative_adjustment.copy()
    stable_relative[relative_denominator_fragile] = np.nan

    add(f"TOP {top_n} RELATIVE MEAN SHIFTS WITH NON-FRAGILE DENOMINATORS")
    add("-" * 78)
    for i in top_indices(stable_relative, top_n):
        if not np.isfinite(float_at(stable_relative, i)):
            continue
        add(
            f"{string_at(labels, i):20s} "
            + f"rel={fmt(float_at(stable_relative, i)):>15s} "
            + f"delta={fmt(float_at(delta_mu, i)):>15s} "
            + f"mu_i={fmt(float_at(mu_i, i)):>15s}"
        )
    add()

    add(f"TOP {top_n} RAW RELATIVE MEAN SHIFTS (TINY-DENOMINATOR WARNING)")
    add("-" * 78)
    for i in top_indices(relative_adjustment, top_n):
        add(
            f"{string_at(labels, i):20s} "
            + f"rel={fmt(float_at(relative_adjustment, i)):>15s} "
            + f"mu_i={fmt(float_at(mu_i, i)):>15s} "
            + f"delta={fmt(float_at(delta_mu, i)):>15s} "
            + f"fragile={bool_at(relative_denominator_fragile, i)}"
        )
    add()

    add("UNCERTAINTY UPDATE SUMMARY")
    add("-" * 78)
    add(
        f"Components with lower variance     : {int(np.sum(reduced_uncertainty_exact))}"
    )
    add(
        f"Components with higher variance    : {int(np.sum(increased_uncertainty_exact))}"
    )
    add(f"Materially reduced beyond tol      : {int(np.sum(reduced_uncertainty))}")
    add(f"Materially increased beyond tol    : {int(np.sum(increased_uncertainty))}")
    add(
        f"Unchanged within configured tol    : {n - int(np.sum(reduced_uncertainty)) - int(np.sum(increased_uncertainty))}"
    )
    add(f"Minimum sigma_f/sigma_i           : {fmt(float(np.min(std_ratio)))}")
    add()

    add(f"TOP {top_n} STANDARD-DEVIATION REDUCTIONS")
    add("-" * 78)
    ordered_std_ratio: IntArray = np.argsort(std_ratio)[:top_n]
    for position in range(ordered_std_ratio.size):
        i = int_at(ordered_std_ratio, position)
        add(
            f"{string_at(labels, i):20s} "
            + f"sigma_f/sigma_i={fmt(float_at(std_ratio, i)):>15s} "
            + f"sigma_i={fmt(float_at(prior_std, i)):>15s} "
            + f"sigma_f={fmt(float_at(posterior_std, i)):>15s}"
        )
    add()

    add("RESPONSE-VARIANCE DECOMPOSITION")
    add("-" * 78)
    add(f"Sum of component contributions   : {fmt(component_contribution_sum)}")
    add(f"Direct S Sigma_i S^T             : {fmt(float_at_2d(nd_response_cov, 0, 0))}")
    add(f"Decomposition absolute mismatch  : {fmt(component_contribution_error)}")
    add()

    add("BY FAMILY")
    for row in family_rows:
        add(
            f"{row['family']!s:8s} "
            + f"n={int(row['n_parameters']):4d} "
            + f"nonzero_S={int(row['n_nonzero_sensitivity']):4d} "
            + f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            + f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            + "response-var contribution="
            + f"{fmt(float(row['response_variance_contribution'])):>15s}"
        )
    add()

    add("BY QID — SORTED BY |RESPONSE-VARIANCE CONTRIBUTION|")
    for row in qid_rows:
        add(
            f"{row['qid']!s:>5s} "
            + f"{row['family']!s:6s} "
            + f"nonzero_S={int(row['n_nonzero_sensitivity']):3d} "
            + f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            + f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            + "response-var contribution="
            + f"{fmt(float(row['response_variance_contribution'])):>15s}"
        )
    add()

    add("PFNS NORMALIZATION / POSITIVITY")
    add("-" * 78)
    for row in pfns_rows:
        add(
            f"{row['qid']} "
            + f"sum: {fmt(float(row['prior_sum']))} -> "
            + f"{fmt(float(row['posterior_sum']))}; "
            + f"negative bins: {int(row['prior_negative_bins'])} -> "
            + f"{int(row['posterior_negative_bins'])}; "
            + f"min posterior={fmt(float(row['posterior_min']))}; "
            + "Var(sum) prior/post="
            + f"{fmt(float(row['prior_sum_variance']))}/"
            + f"{fmt(float(row['posterior_sum_variance']))}"
        )
    add()

    add("AUTOMATIC FLAGS")
    add("-" * 78)
    flags: list[str] = []

    if mean_update_max_abs_error > args.reproduction_tolerance:
        flags.append(
            "Posterior mean does not reproduce the GLLS mean update within "
            + f"{args.reproduction_tolerance:g}."
        )

    if covariance_update_max_abs_error > args.reproduction_tolerance:
        flags.append(
            "Posterior covariance does not reproduce the GLLS covariance "
            + f"update within {args.reproduction_tolerance:g}."
        )

    if np.any(increased_uncertainty):
        flags.append(
            "At least one posterior diagonal variance increased beyond the "
            + "configured tolerance."
        )

    if not bool(prior_cov_diag["psd_within_tolerance"]):
        flags.append("Prior covariance is not PSD within the numerical tolerance.")

    if not bool(posterior_cov_diag["psd_within_tolerance"]):
        flags.append("Posterior covariance is not PSD within the numerical tolerance.")

    if not bool(reduction_cov_diag["psd_within_tolerance"]):
        flags.append("Sigma_i - Sigma_f is not PSD within the numerical tolerance.")

    if (
        abs(float_at(posterior_residual, 0))
        > abs(float_at(Delta_E_i, 0)) + args.reproduction_tolerance
    ):
        flags.append(
            "The posterior linearized JEZEBEL residual is farther from zero "
            + "than the prior residual."
        )

    if (
        np.isfinite(residual_identity_error)
        and residual_identity_error > args.residual_identity_tolerance
    ):
        flags.append(
            "The scalar residual identity is not satisfied within "
            + f"{args.residual_identity_tolerance:g}."
        )

    if response_variance_ratio_to_observation > args.response_uncertainty_ratio_flag:
        flags.append(
            "Prior nuclear-data propagated response std is "
            + f"{response_variance_ratio_to_observation:.3g} times the "
            + "observation std. This is mathematically allowed, but a very "
            + "large ratio is worth checking for covariance/sensitivity scaling."
        )

    total_pfns_negative = sum(int(row["posterior_negative_bins"]) for row in pfns_rows)
    if total_pfns_negative > 0:
        flags.append(
            f"Posterior PFNS contains {total_pfns_negative} negative group values. "
            + "Linear GLLS does not enforce positivity."
        )

    max_pfns_norm_error = max(
        abs(float(row["posterior_sum"]) - 1.0) for row in pfns_rows
    )
    if max_pfns_norm_error > args.pfns_normalization_tolerance:
        flags.append(
            "At least one posterior PFNS slice differs from unit normalization "
            + f"by more than {args.pfns_normalization_tolerance:g}; maximum "
            + f"|sum-1| = {max_pfns_norm_error:.6g}."
        )

    if not flags:
        add("No automatic flags.")
    else:
        for number, flag in enumerate(flags, start=1):
            add(f"{number}. {flag}")

    add()
    add("FILES WRITTEN")
    add("-" * 78)
    add("state_summary.csv")
    add("family_summary.csv")
    add("qid_summary.csv")
    add("pfns_normalization.csv")
    add("analysis_summary.txt")
    add("mean_adjustment_prior_sigma.png")
    add("posterior_prior_std_ratio.png")
    add("response_variance_contribution_by_qid.png")
    add("pfns_normalization.png")

    plot_messages = make_plots(
        output_dir=output_dir,
        metadata=metadata,
        standardized_shift=standardized_shift,
        std_ratio=std_ratio,
        qid_rows=qid_rows,
        pfns_rows=pfns_rows,
    )
    if plot_messages and plot_messages[0] != "plots written":
        add()
        add("PLOT NOTE")
        add("-" * 78)
        for message in plot_messages:
            add(message)

    report = "\n".join(lines)
    _ = (output_dir / "analysis_summary.txt").write_text(report, encoding="utf-8")
    return report


def parse_args() -> AnalysisArgs:
    parser = argparse.ArgumentParser(
        description="Analyze WPEC SG52 Exercise-1 GLLS results."
    )

    _ = parser.add_argument(
        "--prior",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex1_prior.hdf5",
    )
    _ = parser.add_argument(
        "--observations",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex1_observations.hdf5",
    )
    _ = parser.add_argument(
        "--posterior",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex1_results.hdf5",
    )
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex1_analysis",
    )
    _ = parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top-ranked state entries shown in the text report.",
    )
    _ = parser.add_argument(
        "--e-obs",
        type=float,
        default=1.0,
        help=(
            "Experimental response value used only to display reconstructed "
            + "C/E quantities. SG52 JEZEBEL Exercise 1 uses 1.0."
        ),
    )
    _ = parser.add_argument(
        "--relative-denominator-sigma-ratio",
        type=float,
        default=1e-6,
        help=(
            "Flag a raw relative adjustment as denominator-fragile when "
            + "|mu_i| / sigma_i falls below this value."
        ),
    )
    _ = parser.add_argument(
        "--variance-tolerance",
        type=float,
        default=1e-12,
        help=(
            "Relative numerical tolerance when classifying diagonal variances "
            + "as increased/reduced."
        ),
    )
    _ = parser.add_argument(
        "--reproduction-tolerance",
        type=float,
        default=1e-10,
        help="Absolute tolerance for direct GLLS posterior reproduction.",
    )
    _ = parser.add_argument(
        "--residual-identity-tolerance",
        type=float,
        default=1e-10,
        help="Tolerance for the one-response exact residual-fraction identity.",
    )
    _ = parser.add_argument(
        "--response-uncertainty-ratio-flag",
        type=float,
        default=100.0,
        help=("Flag if sqrt(S Sigma_i S^T) / sqrt(Sigma_E) exceeds this value."),
    )
    _ = parser.add_argument(
        "--pfns-normalization-tolerance",
        type=float,
        default=1e-6,
        help="Flag posterior PFNS slices whose sum differs from 1 by more than this.",
    )

    args = AnalysisArgs()
    _ = parser.parse_args(namespace=args)
    return args


def main() -> None:
    args = parse_args()
    report = analyze(args)
    print(report)


if __name__ == "__main__":
    main()
