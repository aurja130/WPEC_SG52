#!/usr/bin/env python3
"""
Diagnostics for the three-response WPEC SG52 Exercise 2 Pu-239 GLLS update.

Inputs: ex2_prior.hdf5 (979-state absolute covariance),
ex2_observations.hdf5 (three criticality responses, observation covariance and
sensitivities), and ex2_results.hdf5 (posterior mean and covariance).
The indexed responses are JEZEBEL PMF-001, EUCLID 3x2 and EUCLID 8x1.
Results include direct posterior reproduction, per-response reconstructed k_eff
and uncertainty, state/group response-variance decompositions, PFNS diagnostics,
CSV tables and plots. Run: python Exercise_2/analyze_ex2_results.py
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
    # Experimental and simulated k_eff are read from the indexed HDF5 input.
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
    sensitivity_0: float
    sensitivity_1: float
    sensitivity_2: float
    response_variance_contribution_0: float
    response_variance_contribution_1: float
    response_variance_contribution_2: float
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
    response_variance_contribution_0: float
    response_variance_contribution_1: float
    response_variance_contribution_2: float


class QidSummaryRow(SummaryRow):
    qid: str


EXERCISE_DIRECTORY = Path(__file__).resolve().parent
# Canonical SG52 Pu-239 state ordering
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

RESPONSE_IDS = (
    "PU-MET-FAST-001-001-s",
    "euclid-3x2-crit",
    "euclid-8x1-crit",
)
N_RESPONSES = len(RESPONSE_IDS)


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


def read_response_metadata(path: Path) -> tuple[tuple[str, ...], FloatArray, FloatArray]:
    with h5py.File(str(path), "r") as h5:
        dataset = cast(h5py.Dataset, h5["responses/row_indices"])
        response_ids = tuple(str(value) for value in dataset.asstr()[()])
        experimental = np.asarray(
            cast(h5py.Dataset, h5["responses/experimental"])[()], dtype=np.float64
        )
        simulated = np.asarray(
            cast(h5py.Dataset, h5["responses/simulated"])[()], dtype=np.float64
        )
    return response_ids, experimental, simulated


def read_inputs(
    args: AnalysisArgs,
) -> tuple[
    FloatArray, FloatArray, FloatArray, FloatArray, FloatArray, FloatArray,
    FloatArray, tuple[str, ...], FloatArray, FloatArray,
]:
    mu_i = read_dataset(args.prior, "mean/values")
    Sigma_i = read_dataset(args.prior, "cov/values")
    Delta_E_i = read_dataset(args.observations, "delta/values")
    S = read_dataset(args.observations, "sens/values")
    Sigma_E = read_dataset(args.observations, "cov/values")

    mu_f = read_dataset(args.posterior, "mean/values")
    Sigma_f = read_dataset(args.posterior, "covariance/values")

    response_ids, experimental, simulated = read_response_metadata(args.observations)
    return mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f, response_ids, experimental, simulated


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
    _ = ax.set_title("Exercise 2 mean adjustment in prior-sigma units")
    fig.tight_layout()
    fig.savefig(output_dir / "mean_adjustment_prior_sigma.png", dpi=180)
    plt.close(fig)

    # Plot 2: posterior/prior standard deviation ratio
    fig, ax = plt.subplots()
    _ = ax.plot(x, std_ratio)
    _ = ax.axhline(1.0, linewidth=0.8)
    _ = ax.set_xlabel("Canonical state index")
    _ = ax.set_ylabel(r"$\sigma_f/\sigma_i$")
    _ = ax.set_title("Exercise 2 posterior/prior standard deviation")
    fig.tight_layout()
    fig.savefig(output_dir / "posterior_prior_std_ratio.png", dpi=180)
    plt.close(fig)

    # Each response has its own variance decomposition, including signed
    # covariance cross-terms allocated to individual state components.
    qid_labels = [str(row["qid"]) for row in qid_rows]
    for response_index, response_id in enumerate(RESPONSE_IDS):
        column = f"response_variance_contribution_{response_index}"
        qid_contrib = [float(row[column]) for row in qid_rows]
        fig, ax = plt.subplots(figsize=(max(8.0, 0.35 * len(qid_labels)), 5.0))
        _ = ax.bar(np.arange(len(qid_labels)), qid_contrib)
        _ = ax.axhline(0.0, linewidth=0.8)
        _ = ax.set_xticks(np.arange(len(qid_labels)))
        _ = ax.set_xticklabels(qid_labels, rotation=90)
        _ = ax.set_ylabel(r"Contribution to $(S\Sigma_iS^T)_{rr}$")
        _ = ax.set_title(f"Exercise 2 response variance by QID: {response_id}")
        fig.tight_layout()
        fig.savefig(
            output_dir / f"response_variance_contribution_by_qid_{response_index}.png",
            dpi=180,
        )
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

    (
        mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f,
        response_ids, experimental, simulated,
    ) = read_inputs(args)

    # ----------------------
    # Basic shape validation
    # ----------------------
    n = EXPECTED_STATE_SIZE

    expected_shapes: dict[str, tuple[int, ...]] = {
        "mu_x_i": (n,),
        "Sigma_x_i": (n, n),
        "Delta_E_i": (N_RESPONSES,),
        "S": (N_RESPONSES, n),
        "Sigma_E": (N_RESPONSES, N_RESPONSES),
        "mu_x_f": (n,),
        "Sigma_x_f": (n, n),
        "experimental": (N_RESPONSES,),
        "simulated": (N_RESPONSES,),
    }

    actual_shapes: dict[str, tuple[int, ...]] = {
        "mu_x_i": mu_i.shape,
        "Sigma_x_i": Sigma_i.shape,
        "Delta_E_i": Delta_E_i.shape,
        "S": S.shape,
        "Sigma_E": Sigma_E.shape,
        "mu_x_f": mu_f.shape,
        "Sigma_x_f": Sigma_f.shape,
        "experimental": experimental.shape,
        "simulated": simulated.shape,
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
        "experimental": experimental,
        "simulated": simulated,
    }
    for name, array in arrays.items():
        if not np.all(np.isfinite(array)):
            bad: IntArray = np.argwhere(~np.isfinite(array))
            bad_rows: list[list[int]] = cast(list[list[int]], bad[:20].tolist())
            raise ValueError(f"{name} contains non-finite values at " + f"{bad_rows}")

    if response_ids != RESPONSE_IDS:
        raise ValueError(f"Response order {response_ids!r}, expected {RESPONSE_IDS!r}")
    if not np.allclose(
        Delta_E_i, experimental - simulated, rtol=1e-10, atol=1e-12
    ):
        raise ValueError("Observation delta does not match experimental - simulated")

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

    prior_nd_response_std = safe_std_from_cov(nd_response_cov)
    posterior_nd_response_std = safe_std_from_cov(posterior_nd_response_cov)
    observation_std = safe_std_from_cov(Sigma_E)
    innovation_std = safe_std_from_cov(V)
    response_variance_ratio_to_observation = np.divide(
        prior_nd_response_std, observation_std,
        out=np.full(N_RESPONSES, np.inf),
        where=observation_std != 0.0,
    )

    # Coupled residual identity; independent scalar variance ratios are invalid.
    expected_residual = Sigma_E @ np.linalg.solve(V, Delta_E_i)
    residual_identity_error = np.abs(posterior_residual - expected_residual)
    e_calc_f = simulated + response_shift
    c_over_e_i = np.divide(
        simulated, experimental, out=np.full(N_RESPONSES, np.nan),
        where=experimental != 0.0,
    )
    c_over_e_f = np.divide(
        e_calc_f, experimental, out=np.full(N_RESPONSES, np.nan),
        where=experimental != 0.0,
    )

    # Each response r: sum_i S[r,i] (Sigma_i S[r,:]^T)[i] =
    # (S Sigma_i S^T)[r,r]. Terms may be signed from cross-covariance.
    component_response_variance_contribution = S * A.T
    component_contribution_sum = np.sum(
        component_response_variance_contribution, axis=1
    )
    component_contribution_error = np.abs(
        component_contribution_sum - np.diag(nd_response_cov)
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
                "sensitivity_0": float_at_2d(S, 0, i),
                "sensitivity_1": float_at_2d(S, 1, i),
                "sensitivity_2": float_at_2d(S, 2, i),
                "response_variance_contribution_0": float_at_2d(
                    component_response_variance_contribution, 0, i
                ),
                "response_variance_contribution_1": float_at_2d(
                    component_response_variance_contribution, 1, i
                ),
                "response_variance_contribution_2": float_at_2d(
                    component_response_variance_contribution, 2, i
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
                    np.count_nonzero(np.any(S[:, family_indices] != 0.0, axis=0))
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
                "response_variance_contribution_0": float(
                    np.sum(component_response_variance_contribution[0, family_indices])
                ),
                "response_variance_contribution_1": float(
                    np.sum(component_response_variance_contribution[1, family_indices])
                ),
                "response_variance_contribution_2": float(
                    np.sum(component_response_variance_contribution[2, family_indices])
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
                    np.count_nonzero(np.any(S[:, qid_indices] != 0.0, axis=0))
                ),
                "max_abs_standardized_shift": float(
                    cast(np.float64, np.max(np.abs(standardized_shift[qid_indices])))
                ),
                "max_abs_relative_adjustment_stable_denominator": stable_rel_max,
                "min_posterior_prior_std_ratio": float(np.min(std_ratio[qid_indices])),
                "n_reduced_variance": int(np.sum(reduced_uncertainty[qid_indices])),
                "n_increased_variance": int(np.sum(increased_uncertainty[qid_indices])),
                "n_posterior_negative": int(np.sum(mu_f[qid_indices] < 0.0)),
                "response_variance_contribution_0": float(
                    np.sum(component_response_variance_contribution[0, qid_indices])
                ),
                "response_variance_contribution_1": float(
                    np.sum(component_response_variance_contribution[1, qid_indices])
                ),
                "response_variance_contribution_2": float(
                    np.sum(component_response_variance_contribution[2, qid_indices])
                ),
            }
        )

    # Rank by total absolute contribution across all three response variances.
    qid_rows.sort(
        key=lambda row: sum(
            abs(float(row[f"response_variance_contribution_{r}"]))
            for r in range(N_RESPONSES)
        ),
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
    add("WPEC SG52 EXERCISE 2 — THREE-RESPONSE GLLS RESULT DIAGNOSTICS")
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

    add("THREE CRITICALITY RESPONSES (INDEXED HDF5 ORDER)")
    add("-" * 78)
    response_rows: list[dict[str, object]] = []
    for r, response_id in enumerate(response_ids):
        add(f"[{r}] {response_id}")
        add(f"  Observed k_eff                   : {fmt(float_at(experimental, r))}")
        add(f"  Prior simulated k_eff            : {fmt(float_at(simulated, r))}")
        add(f"  Prior residual (observed - sim)  : {fmt(float_at(Delta_E_i, r))}")
        add(f"  Posterior linearized k_eff       : {fmt(float_at(e_calc_f, r))}")
        add(f"  Response shift S(delta_mu)       : {fmt(float_at(response_shift, r))}")
        add(f"  Posterior residual               : {fmt(float_at(posterior_residual, r))}")
        add(f"  Vector-identity residual         : {fmt(float_at(expected_residual, r))}")
        add(f"  Residual identity mismatch       : {fmt(float_at(residual_identity_error, r))}")
        add(f"  Prior / posterior C/E            : {fmt(float_at(c_over_e_i, r))} / {fmt(float_at(c_over_e_f, r))}")
        add(f"  Observational std                : {fmt(float_at(observation_std, r))}")
        add(f"  Propagated ND std prior/post     : {fmt(float_at(prior_nd_response_std, r))} / {fmt(float_at(posterior_nd_response_std, r))}")
        add(f"  Innovation std                   : {fmt(float_at(innovation_std, r))}")
        add(f"  Prior ND std / observation std   : {fmt(float_at(response_variance_ratio_to_observation, r))}")
        add()
        response_rows.append({
            "response_index": r,
            "response_id": response_id,
            "experimental_k_eff": float_at(experimental, r),
            "prior_simulated_k_eff": float_at(simulated, r),
            "posterior_linearized_k_eff": float_at(e_calc_f, r),
            "prior_residual": float_at(Delta_E_i, r),
            "posterior_residual": float_at(posterior_residual, r),
            "expected_posterior_residual": float_at(expected_residual, r),
            "residual_identity_error": float_at(residual_identity_error, r),
            "prior_ce": float_at(c_over_e_i, r),
            "posterior_ce": float_at(c_over_e_f, r),
            "observation_std": float_at(observation_std, r),
            "prior_propagated_std": float_at(prior_nd_response_std, r),
            "posterior_propagated_std": float_at(posterior_nd_response_std, r),
            "innovation_std": float_at(innovation_std, r),
        })
    write_csv(output_dir / "response_summary.csv", list(response_rows[0]), response_rows)
    add("Response covariance matrices (rows/columns in indexed response order):")
    for name, matrix in (
        ("Observation Sigma_E", Sigma_E),
        ("Prior propagated S Sigma_i S^T", nd_response_cov),
        ("Posterior propagated S Sigma_f S^T", posterior_nd_response_cov),
    ):
        add(f"  {name}:")
        for row in matrix:
            add("    " + "  ".join(fmt(float(value)) for value in row))
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
    for r, response_id in enumerate(response_ids):
        add(
            f"[{r}] {response_id}: components={fmt(float_at(component_contribution_sum, r))}, "
            + f"direct prior variance={fmt(float_at_2d(nd_response_cov, r, r))}, "
            + f"absolute mismatch={fmt(float_at(component_contribution_error, r))}"
        )
    add("Signed contributions include cross-covariances; columns 0/1/2 match response IDs above.")
    add()

    add("BY FAMILY (variance contributions in response order 0 / 1 / 2)")
    for row in family_rows:
        contributions = " / ".join(
            fmt(float(row[f"response_variance_contribution_{r}"]))
            for r in range(N_RESPONSES)
        )
        add(
            f"{row['family']!s:8s} "
            + f"n={int(row['n_parameters']):4d} "
            + f"nonzero_S(any)={int(row['n_nonzero_sensitivity']):4d} "
            + f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            + f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            + f"response variances={contributions}"
        )
    add()

    add("BY QID — SORTED BY SUM OF ABSOLUTE RESPONSE-VARIANCE CONTRIBUTIONS")
    for row in qid_rows:
        contributions = " / ".join(
            fmt(float(row[f"response_variance_contribution_{r}"]))
            for r in range(N_RESPONSES)
        )
        add(
            f"{row['qid']!s:>5s} "
            + f"{row['family']!s:6s} "
            + f"nonzero_S(any)={int(row['n_nonzero_sensitivity']):3d} "
            + f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            + f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            + f"response variances={contributions}"
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

    for r, response_id in enumerate(response_ids):
        if float_at(residual_identity_error, r) > args.residual_identity_tolerance:
            flags.append(
                f"{response_id}: coupled vector residual identity mismatch exceeds "
                + f"{args.residual_identity_tolerance:g}."
            )
        ratio = float_at(response_variance_ratio_to_observation, r)
        if ratio > args.response_uncertainty_ratio_flag:
            flags.append(
                f"{response_id}: prior propagated ND response std is "
                + f"{ratio:.3g} times observational std; check covariance/sensitivity scaling."
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
    add("response_summary.csv")
    add("family_summary.csv")
    add("qid_summary.csv")
    add("pfns_normalization.csv")
    add("analysis_summary.txt")
    add("mean_adjustment_prior_sigma.png")
    add("posterior_prior_std_ratio.png")
    for r in range(N_RESPONSES):
        add(f"response_variance_contribution_by_qid_{r}.png")
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
        description="Analyze WPEC SG52 Exercise-2 three-response GLLS results."
    )

    _ = parser.add_argument(
        "--prior",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex2_prior.hdf5",
    )
    _ = parser.add_argument(
        "--observations",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex2_observations.hdf5",
    )
    _ = parser.add_argument(
        "--posterior",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex2_results.hdf5",
    )
    _ = parser.add_argument(
        "--output-dir",
        type=Path,
        default=EXERCISE_DIRECTORY / "ex2_analysis",
    )
    _ = parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top-ranked state entries shown in the text report.",
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
        help="Absolute tolerance for the coupled vector residual identity.",
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
