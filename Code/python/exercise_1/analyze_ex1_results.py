#!/usr/bin/env python3
"""
Comprehensive diagnostics for WPEC SG52 Exercise 1 (JEZEBEL k_eff GLLS).

Expected input files
--------------------
mu_x_i.hdf5
    /values                 shape (979,)

Sigma_x_i.hdf5
    /values                 shape (979, 979)

Delta_E_i.hdf5
    /values                 shape (1,)

S.hdf5
    /values                 shape (1, 979)

Sigma_E.hdf5
    /values                 shape (1, 1)

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
-----
Run in the directory containing the six HDF5 files:

    python analyze_ex1_results.py

or specify paths explicitly:

    python analyze_ex1_results.py \
        --prior-mean mu_x_i.hdf5 \
        --prior-cov Sigma_x_i.hdf5 \
        --delta-e Delta_E_i.hdf5 \
        --sensitivity S.hdf5 \
        --response-cov Sigma_E.hdf5 \
        --posterior ex1_results.hdf5

Outputs are written to ./ex1_analysis by default.

For SG52 Exercise 1 the experimental JEZEBEL k_eff is 1.0.  This is used
only to display C/E-like quantities; all GLLS consistency checks use the
matrices/vectors themselves.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np


# ---------------------------------------------------------------------------
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
            f"expected {EXPECTED_STATE_SIZE}."
        )

    return metadata


# ---------------------------------------------------------------------------
# HDF5 readers
# ---------------------------------------------------------------------------

def read_dataset(path: Path, dataset: str) -> np.ndarray:
    with h5py.File(path, "r") as h5:
        if dataset not in h5:
            raise KeyError(f"{path}: dataset {dataset!r} not found")
        return np.asarray(h5[dataset], dtype=np.float64)


def read_inputs(args: argparse.Namespace):
    mu_i = read_dataset(args.prior_mean, "values")
    Sigma_i = read_dataset(args.prior_cov, "values")
    Delta_E_i = read_dataset(args.delta_e, "values")
    S = read_dataset(args.sensitivity, "values")
    Sigma_E = read_dataset(args.response_cov, "values")

    mu_f = read_dataset(args.posterior, "mean/values")
    Sigma_f = read_dataset(args.posterior, "covariance/values")

    return mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f


# ---------------------------------------------------------------------------
# Numerical helpers
# ---------------------------------------------------------------------------

def safe_std_from_cov(cov: np.ndarray) -> np.ndarray:
    diag = np.diag(cov)
    tiny_negative = (diag < 0.0) & (diag > -1e-14 * max(1.0, np.max(np.abs(diag))))
    diag = diag.copy()
    diag[tiny_negative] = 0.0

    if np.any(diag < 0.0):
        bad = np.where(diag < 0.0)[0]
        raise ValueError(
            "Covariance has materially negative diagonal entries at indices "
            f"{bad[:20].tolist()}"
        )
    return np.sqrt(diag)


def matrix_symmetry_error(matrix: np.ndarray) -> float:
    return float(np.max(np.abs(matrix - matrix.T)))


def eig_diagnostics(matrix: np.ndarray) -> dict[str, float | bool]:
    sym = 0.5 * (matrix + matrix.T)
    eigvals = np.linalg.eigvalsh(sym)

    min_eig = float(eigvals[0])
    max_eig = float(eigvals[-1])
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


def max_abs_difference(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.max(np.abs(a - b)))


def relative_frobenius_difference(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a)
    if denom == 0.0:
        return float(np.linalg.norm(a - b))
    return float(np.linalg.norm(a - b) / denom)


def top_indices(values: np.ndarray, n: int) -> np.ndarray:
    finite = np.where(np.isfinite(values), np.abs(values), -np.inf)
    return np.argsort(finite)[::-1][:n]


def grouped_indices(metadata: list[StateMeta], attribute: str) -> dict[str, list[int]]:
    groups: dict[str, list[int]] = {}
    for meta in metadata:
        key = str(getattr(meta, attribute))
        groups.setdefault(key, []).append(meta.index)
    return groups


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict]) -> None:
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
    standardized_shift: np.ndarray,
    std_ratio: np.ndarray,
    qid_rows: list[dict],
    pfns_rows: list[dict],
) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return ["matplotlib not installed; plots skipped"]

    messages: list[str] = []
    x = np.arange(len(metadata))

    # Plot 1: mean adjustment in prior-sigma units
    fig, ax = plt.subplots()
    ax.plot(x, standardized_shift)
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xlabel("Canonical state index")
    ax.set_ylabel(r"$(\mu_f-\mu_i)/\sigma_i$")
    ax.set_title("Exercise 1 mean adjustment in prior-sigma units")
    fig.tight_layout()
    fig.savefig(output_dir / "mean_adjustment_prior_sigma.png", dpi=180)
    plt.close(fig)

    # Plot 2: posterior/prior standard deviation ratio
    fig, ax = plt.subplots()
    ax.plot(x, std_ratio)
    ax.axhline(1.0, linewidth=0.8)
    ax.set_xlabel("Canonical state index")
    ax.set_ylabel(r"$\sigma_f/\sigma_i$")
    ax.set_title("Exercise 1 posterior/prior standard deviation")
    fig.tight_layout()
    fig.savefig(output_dir / "posterior_prior_std_ratio.png", dpi=180)
    plt.close(fig)

    # Plot 3: response variance contribution by QID
    qid_labels = [str(row["qid"]) for row in qid_rows]
    qid_contrib = [float(row["response_variance_contribution"]) for row in qid_rows]

    fig, ax = plt.subplots(figsize=(max(8.0, 0.35 * len(qid_labels)), 5.0))
    ax.bar(np.arange(len(qid_labels)), qid_contrib)
    ax.axhline(0.0, linewidth=0.8)
    ax.set_xticks(np.arange(len(qid_labels)))
    ax.set_xticklabels(qid_labels, rotation=90)
    ax.set_ylabel(r"Contribution to $S\Sigma_iS^T$")
    ax.set_title("Exercise 1 response-variance contribution by QID")
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
        ax.plot(positions, prior_sums, marker="o", label="Prior")
        ax.plot(positions, posterior_sums, marker="o", label="Posterior")
        ax.axhline(1.0, linewidth=0.8)
        ax.set_xticks(positions)
        ax.set_xticklabels(pfns_labels, rotation=45)
        ax.set_ylabel("Sum over 51 outgoing groups")
        ax.set_title("PFNS normalization diagnostic")
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir / "pfns_normalization.png", dpi=180)
        plt.close(fig)

    messages.append("plots written")
    return messages


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze(args: argparse.Namespace) -> str:
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    metadata = build_state_metadata()
    labels = np.array([m.label for m in metadata], dtype=object)
    families = np.array([m.family for m in metadata], dtype=object)
    qids = np.array([m.qid for m in metadata], dtype=object)

    mu_i, Sigma_i, Delta_E_i, S, Sigma_E, mu_f, Sigma_f = read_inputs(args)

    # ----------------------
    # Basic shape validation
    # ----------------------
    n = EXPECTED_STATE_SIZE

    expected_shapes = {
        "mu_x_i": (n,),
        "Sigma_x_i": (n, n),
        "Delta_E_i": (1,),
        "S": (1, n),
        "Sigma_E": (1, 1),
        "mu_x_f": (n,),
        "Sigma_x_f": (n, n),
    }

    actual_shapes = {
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

    arrays = {
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
            bad = np.argwhere(~np.isfinite(array))
            raise ValueError(f"{name} contains non-finite values at {bad[:20].tolist()}")

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
    covariance_update_rel_error = relative_frobenius_difference(expected_Sigma_f, Sigma_f)

    # ----------------------
    # State-space diagnostics
    # ----------------------
    delta_mu = mu_f - mu_i

    prior_std = safe_std_from_cov(Sigma_i)
    posterior_std = safe_std_from_cov(Sigma_f)

    relative_adjustment = np.full(n, np.nan, dtype=np.float64)
    np.divide(delta_mu, mu_i, out=relative_adjustment, where=(mu_i != 0.0))

    standardized_shift = np.zeros(n, dtype=np.float64)
    np.divide(delta_mu, prior_std, out=standardized_shift, where=(prior_std != 0.0))

    std_ratio = np.ones(n, dtype=np.float64)
    np.divide(posterior_std, prior_std, out=std_ratio, where=(prior_std != 0.0))

    variance_ratio = np.ones(n, dtype=np.float64)
    prior_var = prior_std**2
    posterior_var = posterior_std**2
    np.divide(posterior_var, prior_var, out=variance_ratio, where=(prior_var != 0.0))

    mean_to_prior_std = np.full(n, np.inf, dtype=np.float64)
    np.divide(
        np.abs(mu_i),
        prior_std,
        out=mean_to_prior_std,
        where=(prior_std != 0.0),
    )

    # Raw relative adjustments become numerically/interpretively fragile when
    # the prior mean is essentially zero compared with its own prior std.
    relative_denominator_fragile = (
        (mu_i == 0.0)
        | (
            (prior_std != 0.0)
            & (mean_to_prior_std < args.relative_denominator_sigma_ratio)
        )
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

    reduced_uncertainty_exact = posterior_var < prior_var
    increased_uncertainty_exact = posterior_var > prior_var

    reduced_uncertainty = posterior_var < (prior_var - variance_tolerance)
    increased_uncertainty = posterior_var > (prior_var + variance_tolerance)

    # ----------------------
    # Response-space diagnostics
    # ----------------------
    response_shift = S @ delta_mu
    posterior_residual = Delta_E_i - response_shift

    nd_response_cov = S @ Sigma_i @ S.T
    posterior_nd_response_cov = S @ Sigma_f @ S.T

    prior_nd_response_std = float(np.sqrt(max(nd_response_cov[0, 0], 0.0)))
    posterior_nd_response_std = float(
        np.sqrt(max(posterior_nd_response_cov[0, 0], 0.0))
    )
    observation_std = float(np.sqrt(max(Sigma_E[0, 0], 0.0)))
    innovation_std = float(np.sqrt(max(V[0, 0], 0.0)))

    response_variance_ratio_to_observation = (
        prior_nd_response_std / observation_std
        if observation_std != 0.0
        else np.inf
    )

    residual_fraction_actual = (
        float(posterior_residual[0] / Delta_E_i[0])
        if Delta_E_i[0] != 0.0
        else np.nan
    )

    residual_fraction_expected = (
        float(Sigma_E[0, 0] / V[0, 0])
        if V[0, 0] != 0.0
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
    e_calc_i = e_obs - float(Delta_E_i[0])
    e_calc_f = e_calc_i + float(response_shift[0])

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
    sigma_s = Sigma_i @ S[0, :]
    component_response_variance_contribution = S[0, :] * sigma_s

    component_contribution_sum = float(
        np.sum(component_response_variance_contribution)
    )
    component_contribution_error = abs(
        component_contribution_sum - float(nd_response_cov[0, 0])
    )

    # ----------------------
    # PFNS normalization/positivity diagnostics
    # ----------------------
    pfns_rows: list[dict] = []

    for qid in PRIOR_PFNS_IDS:
        idx = np.where(qids == qid)[0]
        prior_block = Sigma_i[np.ix_(idx, idx)]
        posterior_block = Sigma_f[np.ix_(idx, idx)]
        ones = np.ones(len(idx), dtype=np.float64)

        pfns_rows.append(
            {
                "qid": qid,
                "incident_group": int(PRIOR_PFNS_IDS.index(qid)),
                "prior_sum": float(np.sum(mu_i[idx])),
                "posterior_sum": float(np.sum(mu_f[idx])),
                "sum_change": float(np.sum(mu_f[idx]) - np.sum(mu_i[idx])),
                "prior_negative_bins": int(np.sum(mu_i[idx] < 0.0)),
                "posterior_negative_bins": int(np.sum(mu_f[idx] < 0.0)),
                "prior_min": float(np.min(mu_i[idx])),
                "posterior_min": float(np.min(mu_f[idx])),
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
    state_rows: list[dict] = []

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
                "mu_i": float(mu_i[i]),
                "mu_f": float(mu_f[i]),
                "delta_mu": float(delta_mu[i]),
                "relative_adjustment": float(relative_adjustment[i]),
                "prior_std": float(prior_std[i]),
                "posterior_std": float(posterior_std[i]),
                "standardized_shift_prior_sigma": float(standardized_shift[i]),
                "posterior_prior_std_ratio": float(std_ratio[i]),
                "posterior_prior_variance_ratio": float(variance_ratio[i]),
                "abs_mu_i_over_prior_std": float(mean_to_prior_std[i]),
                "relative_denominator_fragile": bool(
                    relative_denominator_fragile[i]
                ),
                "sensitivity": float(S[0, i]),
                "response_variance_contribution": float(
                    component_response_variance_contribution[i]
                ),
                "prior_negative": bool(mu_i[i] < 0.0),
                "posterior_negative": bool(mu_f[i] < 0.0),
            }
        )

    state_fieldnames = list(state_rows[0].keys())
    write_csv(output_dir / "state_summary.csv", state_fieldnames, state_rows)

    # ----------------------
    # Group summaries
    # ----------------------
    family_groups = grouped_indices(metadata, "family")
    qid_groups = grouped_indices(metadata, "qid")

    family_rows: list[dict] = []
    for family, idx_list in family_groups.items():
        idx = np.asarray(idx_list, dtype=int)
        stable = idx[~relative_denominator_fragile[idx]]
        stable_rel_max = (
            float(np.nanmax(np.abs(relative_adjustment[stable])))
            if stable.size
            else np.nan
        )

        family_rows.append(
            {
                "family": family,
                "n_parameters": int(idx.size),
                "n_nonzero_sensitivity": int(np.count_nonzero(S[0, idx])),
                "max_abs_standardized_shift": float(
                    np.max(np.abs(standardized_shift[idx]))
                ),
                "max_abs_relative_adjustment_stable_denominator": stable_rel_max,
                "min_posterior_prior_std_ratio": float(np.min(std_ratio[idx])),
                "n_reduced_variance": int(np.sum(reduced_uncertainty[idx])),
                "n_increased_variance": int(np.sum(increased_uncertainty[idx])),
                "n_posterior_negative": int(np.sum(mu_f[idx] < 0.0)),
                "response_variance_contribution": float(
                    np.sum(component_response_variance_contribution[idx])
                ),
            }
        )

    write_csv(
        output_dir / "family_summary.csv",
        list(family_rows[0].keys()),
        family_rows,
    )

    qid_rows: list[dict] = []
    for qid, idx_list in qid_groups.items():
        idx = np.asarray(idx_list, dtype=int)
        stable = idx[~relative_denominator_fragile[idx]]
        stable_rel_max = (
            float(np.nanmax(np.abs(relative_adjustment[stable])))
            if stable.size
            else np.nan
        )

        qid_rows.append(
            {
                "qid": qid,
                "family": str(families[idx[0]]),
                "n_parameters": int(idx.size),
                "n_nonzero_sensitivity": int(np.count_nonzero(S[0, idx])),
                "max_abs_standardized_shift": float(
                    np.max(np.abs(standardized_shift[idx]))
                ),
                "max_abs_relative_adjustment_stable_denominator": stable_rel_max,
                "min_posterior_prior_std_ratio": float(np.min(std_ratio[idx])),
                "n_reduced_variance": int(np.sum(reduced_uncertainty[idx])),
                "n_increased_variance": int(np.sum(increased_uncertainty[idx])),
                "n_posterior_negative": int(np.sum(mu_f[idx] < 0.0)),
                "response_variance_contribution": float(
                    np.sum(component_response_variance_contribution[idx])
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
        f"{fmt(float(prior_cov_diag['min_eigenvalue']))} / "
        f"{fmt(float(prior_cov_diag['max_eigenvalue']))}"
    )
    add(
        "Posterior min/max eigenvalue     : "
        f"{fmt(float(posterior_cov_diag['min_eigenvalue']))} / "
        f"{fmt(float(posterior_cov_diag['max_eigenvalue']))}"
    )
    add(
        "Covariance reduction min/max eig : "
        f"{fmt(float(reduction_cov_diag['min_eigenvalue']))} / "
        f"{fmt(float(reduction_cov_diag['max_eigenvalue']))}"
    )
    add(
        "Prior PSD within tolerance        : "
        f"{prior_cov_diag['psd_within_tolerance']}"
    )
    add(
        "Posterior PSD within tolerance    : "
        f"{posterior_cov_diag['psd_within_tolerance']}"
    )
    add(
        "Reduction PSD within tolerance    : "
        f"{reduction_cov_diag['psd_within_tolerance']}"
    )
    add()

    add("DIRECT GLLS REPRODUCTION")
    add("-" * 78)
    add(f"Mean max absolute mismatch       : {fmt(mean_update_max_abs_error)}")
    add(f"Mean relative norm mismatch      : {fmt(mean_update_rel_error)}")
    add(
        f"Covariance max absolute mismatch : "
        f"{fmt(covariance_update_max_abs_error)}"
    )
    add(
        f"Covariance relative norm mismatch: "
        f"{fmt(covariance_update_rel_error)}"
    )
    add()

    add("JEZEBEL RESPONSE CHECK")
    add("-" * 78)
    add(f"E_obs                              : {fmt(e_obs)}")
    add(f"E_calc,i                           : {fmt(e_calc_i)}")
    add(f"Delta_E_i = E_obs - E_calc,i      : {fmt(float(Delta_E_i[0]))}")
    add(f"S (mu_f - mu_i)                   : {fmt(float(response_shift[0]))}")
    add(f"E_calc,f (linear reconstruction)  : {fmt(e_calc_f)}")
    add(f"Posterior residual E_obs-E_calc,f : {fmt(float(posterior_residual[0]))}")
    add(f"Prior C/E                         : {fmt(c_over_e_i)}")
    add(f"Posterior C/E                     : {fmt(c_over_e_f)}")
    add()
    add(f"sqrt(S Sigma_i S^T)               : {fmt(prior_nd_response_std)}")
    add(f"sqrt(S Sigma_f S^T)               : {fmt(posterior_nd_response_std)}")
    add(f"sqrt(Sigma_E)                     : {fmt(observation_std)}")
    add(f"sqrt(V)                           : {fmt(innovation_std)}")
    add(
        "Prior ND response std / obs std   : "
        f"{fmt(response_variance_ratio_to_observation)}"
    )
    add()
    add(f"Actual residual fraction          : {fmt(residual_fraction_actual)}")
    add(f"Expected scalar residual fraction : {fmt(residual_fraction_expected)}")
    add(f"Absolute identity mismatch        : {fmt(residual_identity_error)}")
    add()

    add("MEAN ADJUSTMENT SUMMARY")
    add("-" * 78)
    add(
        f"Max |delta_mu / prior_std|        : "
        f"{fmt(float(np.max(np.abs(standardized_shift))))}"
    )
    add(
        f"Posterior negative state values   : "
        f"{int(np.sum(mu_f < 0.0))} / {n}"
    )
    add(
        "Fragile relative denominators     : "
        f"{int(np.sum(relative_denominator_fragile))} / {n}"
    )
    add(
        "  criterion: |mu_i|/sigma_i < "
        f"{args.relative_denominator_sigma_ratio:g} "
        "(plus exact zero means)"
    )
    add()

    add(f"TOP {top_n} MEAN SHIFTS IN PRIOR-SIGMA UNITS (PRIMARY RANKING)")
    add("-" * 78)
    for i in top_indices(standardized_shift, top_n):
        add(
            f"{labels[i]:20s} "
            f"z={fmt(float(standardized_shift[i])):>15s} "
            f"delta={fmt(float(delta_mu[i])):>15s} "
            f"mu_i={fmt(float(mu_i[i])):>15s} "
            f"sigma_i={fmt(float(prior_std[i])):>15s}"
        )
    add()

    stable_relative = relative_adjustment.copy()
    stable_relative[relative_denominator_fragile] = np.nan

    add(f"TOP {top_n} RELATIVE MEAN SHIFTS WITH NON-FRAGILE DENOMINATORS")
    add("-" * 78)
    for i in top_indices(stable_relative, top_n):
        if not np.isfinite(stable_relative[i]):
            continue
        add(
            f"{labels[i]:20s} "
            f"rel={fmt(float(stable_relative[i])):>15s} "
            f"delta={fmt(float(delta_mu[i])):>15s} "
            f"mu_i={fmt(float(mu_i[i])):>15s}"
        )
    add()

    add(f"TOP {top_n} RAW RELATIVE MEAN SHIFTS (TINY-DENOMINATOR WARNING)")
    add("-" * 78)
    for i in top_indices(relative_adjustment, top_n):
        add(
            f"{labels[i]:20s} "
            f"rel={fmt(float(relative_adjustment[i])):>15s} "
            f"mu_i={fmt(float(mu_i[i])):>15s} "
            f"delta={fmt(float(delta_mu[i])):>15s} "
            f"fragile={bool(relative_denominator_fragile[i])}"
        )
    add()

    add("UNCERTAINTY UPDATE SUMMARY")
    add("-" * 78)
    add(f"Components with lower variance     : {int(np.sum(reduced_uncertainty_exact))}")
    add(f"Components with higher variance    : {int(np.sum(increased_uncertainty_exact))}")
    add(f"Materially reduced beyond tol      : {int(np.sum(reduced_uncertainty))}")
    add(f"Materially increased beyond tol    : {int(np.sum(increased_uncertainty))}")
    add(f"Unchanged within configured tol    : {n - int(np.sum(reduced_uncertainty)) - int(np.sum(increased_uncertainty))}")
    add(f"Minimum sigma_f/sigma_i           : {fmt(float(np.min(std_ratio)))}")
    add()

    add(f"TOP {top_n} STANDARD-DEVIATION REDUCTIONS")
    add("-" * 78)
    for i in np.argsort(std_ratio)[:top_n]:
        add(
            f"{labels[i]:20s} "
            f"sigma_f/sigma_i={fmt(float(std_ratio[i])):>15s} "
            f"sigma_i={fmt(float(prior_std[i])):>15s} "
            f"sigma_f={fmt(float(posterior_std[i])):>15s}"
        )
    add()

    add("RESPONSE-VARIANCE DECOMPOSITION")
    add("-" * 78)
    add(
        "Sum of component contributions   : "
        f"{fmt(component_contribution_sum)}"
    )
    add(
        "Direct S Sigma_i S^T             : "
        f"{fmt(float(nd_response_cov[0, 0]))}"
    )
    add(
        "Decomposition absolute mismatch  : "
        f"{fmt(component_contribution_error)}"
    )
    add()

    add("BY FAMILY")
    for row in family_rows:
        add(
            f"{str(row['family']):8s} "
            f"n={int(row['n_parameters']):4d} "
            f"nonzero_S={int(row['n_nonzero_sensitivity']):4d} "
            f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            f"response-var contribution="
            f"{fmt(float(row['response_variance_contribution'])):>15s}"
        )
    add()

    add("BY QID — SORTED BY |RESPONSE-VARIANCE CONTRIBUTION|")
    for row in qid_rows:
        add(
            f"{str(row['qid']):>5s} "
            f"{str(row['family']):6s} "
            f"nonzero_S={int(row['n_nonzero_sensitivity']):3d} "
            f"max|z|={fmt(float(row['max_abs_standardized_shift'])):>12s} "
            f"min sigma ratio={fmt(float(row['min_posterior_prior_std_ratio'])):>12s} "
            f"response-var contribution="
            f"{fmt(float(row['response_variance_contribution'])):>15s}"
        )
    add()

    add("PFNS NORMALIZATION / POSITIVITY")
    add("-" * 78)
    for row in pfns_rows:
        add(
            f"{row['qid']} "
            f"sum: {fmt(float(row['prior_sum']))} -> "
            f"{fmt(float(row['posterior_sum']))}; "
            f"negative bins: {int(row['prior_negative_bins'])} -> "
            f"{int(row['posterior_negative_bins'])}; "
            f"min posterior={fmt(float(row['posterior_min']))}; "
            f"Var(sum) prior/post="
            f"{fmt(float(row['prior_sum_variance']))}/"
            f"{fmt(float(row['posterior_sum_variance']))}"
        )
    add()

    add("AUTOMATIC FLAGS")
    add("-" * 78)
    flags: list[str] = []

    if mean_update_max_abs_error > args.reproduction_tolerance:
        flags.append(
            "Posterior mean does not reproduce the GLLS mean update within "
            f"{args.reproduction_tolerance:g}."
        )

    if covariance_update_max_abs_error > args.reproduction_tolerance:
        flags.append(
            "Posterior covariance does not reproduce the GLLS covariance "
            f"update within {args.reproduction_tolerance:g}."
        )

    if np.any(increased_uncertainty):
        flags.append(
            "At least one posterior diagonal variance increased beyond the "
            "configured tolerance."
        )

    if not bool(prior_cov_diag["psd_within_tolerance"]):
        flags.append("Prior covariance is not PSD within the numerical tolerance.")

    if not bool(posterior_cov_diag["psd_within_tolerance"]):
        flags.append(
            "Posterior covariance is not PSD within the numerical tolerance."
        )

    if not bool(reduction_cov_diag["psd_within_tolerance"]):
        flags.append(
            "Sigma_i - Sigma_f is not PSD within the numerical tolerance."
        )

    if (
        abs(float(posterior_residual[0]))
        > abs(float(Delta_E_i[0])) + args.reproduction_tolerance
    ):
        flags.append(
            "The posterior linearized JEZEBEL residual is farther from zero "
            "than the prior residual."
        )

    if (
        np.isfinite(residual_identity_error)
        and residual_identity_error > args.residual_identity_tolerance
    ):
        flags.append(
            "The scalar residual identity is not satisfied within "
            f"{args.residual_identity_tolerance:g}."
        )

    if response_variance_ratio_to_observation > args.response_uncertainty_ratio_flag:
        flags.append(
            "Prior nuclear-data propagated response std is "
            f"{response_variance_ratio_to_observation:.3g} times the "
            "observation std. This is mathematically allowed, but a very "
            "large ratio is worth checking for covariance/sensitivity scaling."
        )

    total_pfns_negative = sum(int(row["posterior_negative_bins"]) for row in pfns_rows)
    if total_pfns_negative > 0:
        flags.append(
            f"Posterior PFNS contains {total_pfns_negative} negative group values. "
            "Linear GLLS does not enforce positivity."
        )

    max_pfns_norm_error = max(
        abs(float(row["posterior_sum"]) - 1.0)
        for row in pfns_rows
    )
    if max_pfns_norm_error > args.pfns_normalization_tolerance:
        flags.append(
            "At least one posterior PFNS slice differs from unit normalization "
            f"by more than {args.pfns_normalization_tolerance:g}; maximum "
            f"|sum-1| = {max_pfns_norm_error:.6g}."
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
    (output_dir / "analysis_summary.txt").write_text(report, encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze WPEC SG52 Exercise-1 GLLS results."
    )

    parser.add_argument(
        "--prior-mean",
        type=Path,
        default=Path("mu_x_i.hdf5"),
    )
    parser.add_argument(
        "--prior-cov",
        type=Path,
        default=Path("Sigma_x_i.hdf5"),
    )
    parser.add_argument(
        "--delta-e",
        type=Path,
        default=Path("Delta_E_i.hdf5"),
    )
    parser.add_argument(
        "--sensitivity",
        type=Path,
        default=Path("S.hdf5"),
    )
    parser.add_argument(
        "--response-cov",
        type=Path,
        default=Path("Sigma_E.hdf5"),
    )
    parser.add_argument(
        "--posterior",
        type=Path,
        default=Path("ex1_results.hdf5"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ex1_analysis"),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=15,
        help="Number of top-ranked state entries shown in the text report.",
    )
    parser.add_argument(
        "--e-obs",
        type=float,
        default=1.0,
        help=(
            "Experimental response value used only to display reconstructed "
            "C/E quantities. SG52 JEZEBEL Exercise 1 uses 1.0."
        ),
    )
    parser.add_argument(
        "--relative-denominator-sigma-ratio",
        type=float,
        default=1e-6,
        help=(
            "Flag a raw relative adjustment as denominator-fragile when "
            "|mu_i| / sigma_i falls below this value."
        ),
    )
    parser.add_argument(
        "--variance-tolerance",
        type=float,
        default=1e-12,
        help=(
            "Relative numerical tolerance when classifying diagonal variances "
            "as increased/reduced."
        ),
    )
    parser.add_argument(
        "--reproduction-tolerance",
        type=float,
        default=1e-10,
        help="Absolute tolerance for direct GLLS posterior reproduction.",
    )
    parser.add_argument(
        "--residual-identity-tolerance",
        type=float,
        default=1e-10,
        help="Tolerance for the one-response exact residual-fraction identity.",
    )
    parser.add_argument(
        "--response-uncertainty-ratio-flag",
        type=float,
        default=100.0,
        help=(
            "Flag if sqrt(S Sigma_i S^T) / sqrt(Sigma_E) exceeds this value."
        ),
    )
    parser.add_argument(
        "--pfns-normalization-tolerance",
        type=float,
        default=1e-6,
        help="Flag posterior PFNS slices whose sum differs from 1 by more than this.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = analyze(args)
    print(report)


if __name__ == "__main__":
    main()
