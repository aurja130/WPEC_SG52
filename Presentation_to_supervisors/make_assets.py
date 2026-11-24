"""Build the figures and numbers for the supervisor presentation.

Run from the repository root after the Exercise 1-4 workflows:

    python3 Presentation_to_supervisors/make_assets.py

Inputs (read-only):
- Exercise_<N>/ex<N>_{prior,observations,results}.hdf5 for N = 1..4
- the release 3 JEZEBEL observation file (Exercise 1 stores no E and C)
- the release 4 coordinator comparison plots
  (SG52_materials_release_4/Submissions_against_release_3/)

Outputs (in Presentation_to_supervisors/):
- images/ex<N>_<kind>_<name>.png: copied comparison plots
- images/ex<N>_ce.pdf: prior and linearized-posterior C/E per response
- generated/numbers.tex: one macro per number, read with \\ExVal{<N>}{<key>}
- generated/ex<N>_data.tex, generated/ex<N>_ce_table.tex: table bodies
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import h5py
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
IMAGES = OUT / "images"
GENERATED = OUT / "generated"
COMPARISONS = (
    ROOT.parent
    / "SG52_materials"
    / "SG52_materials_release_4"
    / "Submissions_against_release_3"
)
COMPARISON_DIRS = {
    1: "Ex1_Comparison",
    2: "Ex2_Comparison",
    3: "Ex3_Comparison",
    4: "Ex4_Comparison_with_prior_std",
}
COPIED_PLOTS = {
    "adjustments": ("MT2", "MT4", "MT18", "MT452"),
    "uncertainties": ("MT2", "MT18", "MT452", "MT1518"),
}
EX4_MATRIX_PLOTS = (
    "prior_correlations/XS_reference_prior",
    "prior_correlations/XS_UU_Ex4",
    "correlations/XS_UU_Ex4",
    "correlations/PFNS_UU_Ex4",
)

# (label in tables, label in plots, response-ID test), in released order.
FAMILIES = (
    ("JEZEBEL $k_\\mathrm{eff}$", "JEZ keff", lambda r: r == "PU-MET-FAST-001-001-s"),
    (
        "JEZEBEL reaction-rate ratios",
        "JEZ RRR",
        lambda r: r.startswith("PU-MET-FAST-001-001_"),
    ),
    ("EUCLID $k_\\mathrm{eff}$ (3x2, 1x8)", "EUC keff", lambda r: r.endswith("-crit")),
    (
        "EUCLID neutron-leakage spectrum",
        "EUC NLS",
        lambda r: r.startswith("euclid_NLS"),
    ),
    (
        "EUCLID reaction-rate ratios",
        "EUC RRR",
        lambda r: r.startswith("euclid_rrr"),
    ),
    ("Marini $\\bar\\nu$ (as MT452)", "Marini nubar", lambda r: r.startswith("marini")),
)
TEX_NAMES = {
    "PU-MET-FAST-001-001-s": "JEZEBEL $k_\\mathrm{eff}$",
    "euclid-3x2-crit": "EUCLID 3x2 $k_\\mathrm{eff}$",
    "euclid-8x1-crit": "EUCLID 1x8 $k_\\mathrm{eff}$",
}


def decode(values: np.ndarray) -> list[str]:
    return [v.decode() if isinstance(v, bytes) else str(v) for v in values]


def family_index(response_id: str) -> int:
    for index, (_, _, test) in enumerate(FAMILIES):
        if test(response_id):
            return index
    raise ValueError(f"unclassified response ID: {response_id}")


def load_exercise(n: int) -> dict[str, object]:
    base = ROOT / f"Exercise_{n}"
    with h5py.File(base / f"ex{n}_prior.hdf5") as h:
        mu_i = h["mean/values"][...]
        sigma_i = h["cov/values"][...]
        states = decode(h["mean/row_indices"][...])
    with h5py.File(base / f"ex{n}_observations.hdf5") as h:
        delta = h["delta/values"][...]
        sigma_e = h["cov/values"][...]
        sens = h["sens/values"][...]
        responses = decode(h["delta/row_indices"][...])
        if "responses" in h:
            experimental = h["responses/experimental"][...]
            simulated = h["responses/simulated"][...]
        else:
            experimental, simulated = exercise1_values(responses)
    with h5py.File(base / f"ex{n}_results.hdf5") as h:
        mu_f = h["mean/values"][...]
        sigma_f = h["covariance/values"][...]
    if not np.allclose(experimental - simulated, delta, rtol=0, atol=1e-12):
        raise ValueError(f"Exercise {n}: E - C does not match /delta")
    return {
        "mu_i": mu_i,
        "sigma_i": sigma_i,
        "states": states,
        "delta": delta,
        "sigma_e": sigma_e,
        "sens": sens,
        "responses": responses,
        "E": experimental,
        "C": simulated,
        "mu_f": mu_f,
        "sigma_f": sigma_f,
    }


def exercise1_values(responses: list[str]) -> tuple[np.ndarray, np.ndarray]:
    sys.path.insert(0, str(ROOT / "Exercise_1"))
    import ex1_observations as ex1

    data = ex1.load_observations(ex1.DEFAULT_SOURCE_DIRECTORY / "JEZEBEL_obs.csv")
    rows = [data.response_ids.index(r) for r in responses]
    return data.experimental[rows], data.simulated[rows]


def analyse(n: int, ex: dict[str, object]) -> dict[str, str]:
    mu_i, mu_f = ex["mu_i"], ex["mu_f"]
    sigma_i, sigma_f = ex["sigma_i"], ex["sigma_f"]
    sens, sigma_e = ex["sens"], ex["sigma_e"]
    E, C = ex["E"], ex["C"]
    states, responses = ex["states"], ex["responses"]
    assert isinstance(states, list) and isinstance(responses, list)

    m = len(responses)
    shift = mu_f - mu_i
    c_post = C + sens @ shift
    obs_std = np.sqrt(np.diag(sigma_e))
    inside_prior = np.abs(E - C) <= obs_std
    inside_post = np.abs(E - c_post) <= obs_std

    std_i = np.sqrt(np.clip(np.diag(sigma_i), 0, None))
    std_f = np.sqrt(np.clip(np.diag(sigma_f), 0, None))
    has_std = std_i > 0
    z = np.abs(shift[has_std]) / std_i[has_std]
    ratio = std_f[has_std] / std_i[has_std]

    values = {
        "n": str(len(states)),
        "m": str(m),
        "nTemplate": str(sum(s.split("_")[1] != "00456" for s in states)),
        "withinPrior": str(int(inside_prior.sum())),
        "withinPost": str(int(inside_post.sum())),
        "maxZ": f"{float(z.max()):.2f}",
        "minRatio": f"{float(ratio.min()):.3f}",
        "negative": str(int(np.sum(mu_f < 0))),
        "zeroMean": str(int(np.sum(mu_i == 0))),
    }

    marini = np.array([r.startswith("marini") for r in responses])
    if marini.any():
        block = sigma_e[np.ix_(marini, marini)]
        d = np.sqrt(np.diag(block))
        rho = block / np.outer(d, d)
        off = rho[~np.eye(len(d), dtype=bool)]
        eig = np.linalg.eigvalsh(rho)
        values["mariniN"] = str(len(d))
        values["mariniRhoMean"] = f"{float(off.mean()):.2f}"
        values["mariniTopMode"] = f"{100 * float(eig[-1] / eig.sum()):.0f}"
        values["withinPriorInt"] = str(int(inside_prior[~marini].sum()))
        values["withinPostInt"] = str(int(inside_post[~marini].sum()))
        values["withinPriorMar"] = str(int(inside_prior[marini].sum()))
        values["withinPostMar"] = str(int(inside_post[marini].sum()))

    ce_prior, ce_post = C / E, c_post / E

    write_data_table(n, responses)
    write_ce_table(n, responses, E, ce_prior, ce_post)
    if m > 3:
        plot_ce(n, responses, ce_prior, ce_post, obs_std / E)
    return values


def write_data_table(n: int, responses: list[str]) -> None:
    counts = [0] * len(FAMILIES)
    for r in responses:
        counts[family_index(r)] += 1
    rows = [
        "\\begin{tabular}{@{}lr@{}}",
        "\\toprule",
        "Data set & points \\\\",
        "\\midrule",
    ]
    rows += [
        f"{label} & {count} \\\\"
        for (label, _, _), count in zip(FAMILIES, counts, strict=True)
        if count
    ]
    rows += [
        "\\midrule",
        f"Total $m$ & {len(responses)} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    (GENERATED / f"ex{n}_data.tex").write_text("\n".join(rows) + "\n")


def write_ce_table(
    n: int,
    responses: list[str],
    E: np.ndarray,
    ce_prior: np.ndarray,
    ce_post: np.ndarray,
) -> None:
    rows = [
        "\\begin{tabular}{@{}lccc@{}}",
        "\\toprule",
        "Response & $E$ & C/E prior & C/E posterior \\\\",
        "\\midrule",
    ]
    rows += [
        f"{TEX_NAMES[r]} & {E[k]:.5g} & {ce_prior[k]:.5f} & {ce_post[k]:.5f} \\\\"
        for k, r in enumerate(responses)
        if r in TEX_NAMES
    ]
    rows += ["\\bottomrule", "\\end{tabular}"]
    (GENERATED / f"ex{n}_ce_table.tex").write_text("\n".join(rows) + "\n")


def plot_ce(
    n: int,
    responses: list[str],
    ce_prior: np.ndarray,
    ce_post: np.ndarray,
    rel_obs_std: np.ndarray,
) -> None:
    x = np.arange(len(responses))
    fig, ax = plt.subplots(figsize=(10, 3.6), layout="constrained")
    ax.fill_between(
        x,
        1 - rel_obs_std,
        1 + rel_obs_std,
        step="mid",
        color="0.85",
        label=r"$1 \pm \sigma_\mathrm{obs}/E$",
    )
    ax.axhline(1, color="0.4", lw=0.8)
    ax.plot(x, ce_prior, "o", mfc="none", mec="#971f30", label="prior C/E")
    ax.plot(x, ce_post, "s", ms=4, color="#1f4e97", label="linearized posterior C/E")
    families = [family_index(r) for r in responses]
    starts = [k for k in range(len(responses)) if k == 0 or families[k] != families[k - 1]]
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(responses)
        if start:
            ax.axvline(start - 0.5, color="0.6", lw=0.6, ls="--")
        ax.text(
            (start + end - 1) / 2,
            1.02 + 0.09 * (k % 2),
            FAMILIES[families[start]][1],
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_xlim(-0.6, len(responses) - 0.4)
    ax.set_xlabel("response index (released order)")
    ax.set_ylabel("C/E")
    fig.legend(loc="outside lower center", fontsize=9, ncols=3)
    fig.savefig(IMAGES / f"ex{n}_ce.pdf", metadata={"CreationDate": None})
    plt.close(fig)


def copy_comparisons() -> None:
    if not COMPARISONS.is_dir():
        raise FileNotFoundError(f"Release 4 comparison folder not found: {COMPARISONS}")
    for n, folder in COMPARISON_DIRS.items():
        for kind, names in COPIED_PLOTS.items():
            for name in names:
                source = COMPARISONS / folder / kind / f"{name}.png"
                shutil.copyfile(source, IMAGES / f"ex{n}_{kind}_{name}.png")
    for name in EX4_MATRIX_PLOTS:
        source = COMPARISONS / COMPARISON_DIRS[4] / f"{name}.png"
        target = IMAGES / f"ex4_{name.replace('/', '_')}.png"
        shutil.copyfile(source, target)


def main() -> None:
    IMAGES.mkdir(exist_ok=True)
    GENERATED.mkdir(exist_ok=True)
    copy_comparisons()
    lines = [
        "% Generated by make_assets.py from the Exercise 1-4 HDF5 files; do not edit.",
        "\\providecommand{\\ExVal}[2]{\\csname ex#1#2\\endcsname}",
    ]
    for n in range(1, 5):
        for key, value in analyse(n, load_exercise(n)).items():
            lines.append(f"\\expandafter\\def\\csname ex{n}{key}\\endcsname{{{value}}}")
    (GENERATED / "numbers.tex").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
