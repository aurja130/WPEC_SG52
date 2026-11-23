"""Compute ENDF/B-VIII.0 and VIII.1 Pu-239 reference group values with NJOY.

Runs NJOY with the released SG52 input on both ENDF/B Pu-239 files, parses the
GENDF, MF46 and PFNS tapes into the 979-state Exercise 5 ordering, and checks
ENDF/B-VIII.0 against the released prior means quantity by quantity.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias, cast

import h5py
import numpy as np
from numpy.typing import NDArray

FloatArray: TypeAlias = NDArray[np.float64]

ZAID: Final = 94239
ENERGY_GROUP_COUNT: Final = 51
ORDINARY_QUANTITY_IDS: Final = (2, 4, 16, 17, 18, 37, 102, 452, 456)
PFNS_QUANTITY_IDS: Final = tuple(range(1018, 1919, 100))
MUBAR_QUANTITY_IDS: Final = tuple(range(251, 9252, 1000))
QUANTITY_IDS: Final = (
    *ORDINARY_QUANTITY_IDS,
    *PFNS_QUANTITY_IDS,
    *MUBAR_QUANTITY_IDS,
)
PFNS_TAPE_RANGE: Final = range(100, 131)
REPRODUCTION_TOLERANCE: Final = 1.0e-6
EXPECTED_UNREPRODUCED: Final = ("01318", "01518", "01618")

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
EXERCISE_DIRECTORY: Final = Path(__file__).resolve().parent
RELEASE_DIRECTORY: Final = (
    REPOSITORY_ROOT.parent / "SG52_materials" / "SG52_materials_release_4"
)
COVARIANCE_DIRECTORY: Final = RELEASE_DIRECTORY / "Covariances"
PLAINTEXT_DIRECTORY: Final = COVARIANCE_DIRECTORY / "plaintext"
NJOY_INPUT_PATH: Final = COVARIANCE_DIRECTORY / "NJOY_input"
PFNS_ENERGY_PATH: Final = PLAINTEXT_DIRECTORY / "pfns_incident_energies.txt"
PRIOR_PATH: Final = EXERCISE_DIRECTORY / "ex6_prior.hdf5"
FALLBACK_PRIOR_PATH: Final = REPOSITORY_ROOT / "Exercise_5" / "ex5_prior.hdf5"
NJOY_ROOT: Final = EXERCISE_DIRECTORY / "ex6_njoy"
OUTPUT_PATH: Final = EXERCISE_DIRECTORY / "ex6_endf_reference.hdf5"


@dataclass(frozen=True)
class Library:
    """One ENDF/B library: name, file location, pinned checksum and source."""

    name: str
    endf_path: Path
    sha256: str
    source: str


LIBRARIES: Final = (
    Library(
        name="viii0",
        endf_path=REPOSITORY_ROOT / "Resources" / "ENDF-B-VIII.0" / "n-094_Pu_239.endf",
        sha256="eae697df932ab4635d742123fc476b110271f92689083c0133527f429a48e684",
        source="https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip",
    ),
    Library(
        name="viii1",
        endf_path=REPOSITORY_ROOT / "Resources" / "ENDF-B-VIII.1" / "n-094_Pu_239.endf",
        sha256="7e298d9edc2fd2e956f1ef4bd9f20d7c0d8185294e7fb7016872bed249cda127",
        source=(
            "https://www.nndc.bnl.gov/endf-releases/releases/B-VIII.1/neutrons/"
            "neutrons-version.VIII.1.tar.gz"
        ),
    ),
)

_ENDF_FLOAT_RE: Final = re.compile(r"^([+-]?[\d.]+)([+-]\d+)$")


def fnum(field: str) -> float | None:
    """Parse one ENDF 11-character float field; blank fields return None."""
    text = field.strip()
    if not text:
        return None
    match = _ENDF_FLOAT_RE.match(text)
    if match is not None:
        return float(f"{match.group(1)}e{match.group(2)}")
    return float(text)


def sha256_of(path: Path) -> str:
    """Return the hex SHA-256 digest of a file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_endf_file(library: Library) -> None:
    """Fail loudly if a reference ENDF file is missing or has a different checksum."""
    if not library.endf_path.is_file():
        raise FileNotFoundError(
            f"ENDF/{library.name} file not found: {library.endf_path}\n"
            f"Download from {library.source}"
        )
    digest = sha256_of(library.endf_path)
    if digest != library.sha256:
        raise ValueError(
            f"{library.endf_path}: sha256 {digest} does not match {library.sha256}\n"
            f"Source: {library.source}"
        )


def find_njoy() -> Path:
    """Locate the NJOY executable on PATH."""
    executable = shutil.which("njoy")
    if executable is None:
        raise FileNotFoundError("njoy executable not found on PATH")
    return Path(executable)


def read_njoy_input() -> str:
    """Return the NJOY input for the second (post-ACER) MODER block to end of file."""
    text = NJOY_INPUT_PATH.read_text(encoding="utf-8")
    start = text.index("moder", text.index("acer"))
    return text[start:]


def run_njoy(library: Library, *, skip_njoy: bool) -> tuple[Path, str]:
    """Run NJOY in a fresh work directory and return it with the NJOY version line."""
    work_directory = NJOY_ROOT / library.name
    log_path = work_directory / "njoy.log"
    input_path = work_directory / "input.txt"

    if skip_njoy:
        if not log_path.is_file():
            raise FileNotFoundError(f"--skip-njoy requested but {log_path} is missing")
    else:
        shutil.rmtree(work_directory, ignore_errors=True)
        work_directory.mkdir(parents=True)
        shutil.copyfile(library.endf_path, work_directory / "tape20")
        _ = input_path.write_text(read_njoy_input(), encoding="utf-8")
        executable = find_njoy()
        with input_path.open("rb") as stdin, log_path.open("wb") as log:
            _ = subprocess.run(
                [str(executable)],
                stdin=stdin,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=work_directory,
                check=True,
            )

    first_line = next(
        line
        for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip()
    )
    version = " ".join(first_line.split()[:3])
    return work_directory, version


def read_tape_lines(path: Path) -> dict[tuple[int, int], list[str]]:
    """Group the 80-column ENDF records of a tape by (MF, MT), skipping MF0/MT0."""
    groups: dict[tuple[int, int], list[str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.ljust(80)
        mf = int(line[70:72])
        mt = int(line[72:75])
        if mf == 0 or mt == 0:
            continue
        groups.setdefault((mf, mt), []).append(line)
    return groups


def fields(line: str) -> list[float]:
    """Return all non-blank float fields from the data portion of an ENDF record."""
    return [v for j in range(0, 66, 11) if (v := fnum(line[j : j + 11])) is not None]


def gendf_mf3(lines: list[str], ng: int = ENERGY_GROUP_COUNT) -> FloatArray:
    """Return the Legendre-0 group cross sections of one GENDF MF3 section."""
    head = lines[0]
    nl = int(head[22:33])
    nz = int(head[33:44])
    vals = np.zeros(ng)
    i = 1
    while i < len(lines):
        c = lines[i]
        nw = int(c[44:55])
        ig = int(c[55:66])
        i += 1
        nrec = (nw + 5) // 6
        data = [
            x
            for ln in lines[i : i + nrec]
            for x in (fnum(ln[j : j + 11]) for j in range(0, 66, 11))
            if x is not None
        ][:nw]
        i += nrec
        if ig == 0 or ig > ng:
            break
        vals[ig - 1] = data[nl * nz]
    return vals


def errorr_mf3(lines: list[str]) -> FloatArray:
    """Return the values of one ERRORR MF3 section (HEAD record first)."""
    return np.array([v for ln in lines[1:] for v in fields(ln)])


def errorr_mf5(lines: list[str]) -> tuple[float, FloatArray]:
    """Return (efmean in eV, chi values) of one ERRORR MF5 section."""
    efmean = fnum(lines[0][11:22])
    if efmean is None:
        raise ValueError("MF5 HEAD record has no efmean field")
    vals = [v for ln in lines[1:] for v in fields(ln)]
    return efmean, np.array(vals)


def load_released_means(quantity_id: int) -> FloatArray:
    """Load one released prior mean vector (1 value for mubar quantities)."""
    path = PLAINTEXT_DIRECTORY / f"{ZAID}-{quantity_id:05d}-xs.txt"
    values = np.asarray(np.loadtxt(path, dtype=np.float64, ndmin=1), dtype=np.float64)
    expected = 1 if quantity_id in MUBAR_QUANTITY_IDS else ENERGY_GROUP_COUNT
    if values.shape != (expected,):
        raise ValueError(f"{path.name}: expected {expected} values, got {values.shape}")
    return values


def load_pfns_slices() -> dict[int, tuple[float, float]]:
    """Load the PFNS incident-energy slice bounds in eV keyed by QID."""
    slices: dict[int, tuple[float, float]] = {}
    for raw in PFNS_ENERGY_PATH.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        qid_text, lo_text, hi_text = raw.split()
        slices[int(qid_text)] = (float(lo_text), float(hi_text))
    missing = [qid for qid in PFNS_QUANTITY_IDS if qid not in slices]
    if missing:
        raise ValueError(f"{PFNS_ENERGY_PATH.name}: missing slices {missing}")
    return slices


def slice_average(
    efmeans: FloatArray,
    chis: FloatArray,
    lo: float,
    hi: float,
) -> FloatArray:
    """Average the PFNS spectra whose efmean lies in [lo, hi] (eV).

    A single matching spectrum is used directly; several are combined with a
    trapezoid-weighted average over incident energy.
    """
    selected = (efmeans >= lo * (1.0 - 1.0e-9)) & (efmeans <= hi * (1.0 + 1.0e-9))
    if not np.any(selected):
        raise ValueError(f"No PFNS efmean in slice [{lo}, {hi}] eV")
    order = np.argsort(efmeans[selected])
    e_sorted = efmeans[selected][order]
    chi_sorted = chis[selected][order]
    if e_sorted.size == 1:
        return chi_sorted[0].copy()
    weights = np.trapezoid(np.eye(e_sorted.size), e_sorted)
    return np.asarray((weights @ chi_sorted) / weights.sum(), dtype=np.float64)


def load_pfns_spectra(tape_directory: Path) -> tuple[FloatArray, FloatArray]:
    """Return (efmeans, chis) from every PFNS tape in PFNS_TAPE_RANGE."""
    efmeans: list[float] = []
    chis: list[FloatArray] = []
    for number in PFNS_TAPE_RANGE:
        path = tape_directory / f"tape{number}"
        if not path.is_file():
            raise FileNotFoundError(f"NJOY did not produce {path}")
        groups = read_tape_lines(path)
        section = groups.get((5, 18))
        if section is None:
            raise ValueError(f"{path.name}: no MF5 MT18 section")
        efmean, chi = errorr_mf5(section)
        efmeans.append(efmean)
        chis.append(chi)
    return np.asarray(efmeans, dtype=np.float64), np.asarray(chis, dtype=np.float64)


def build_library_values(
    tape_directory: Path,
    state_ids: tuple[str, ...],
) -> FloatArray:
    """Build the 979-state vector for one library in the prior's state order."""
    gendf = read_tape_lines(tape_directory / "tape91")
    mubar_tape = read_tape_lines(tape_directory / "tape46")
    mubar_section = mubar_tape.get((3, 251))
    if mubar_section is None:
        raise ValueError("tape46: no MF3 MT251 section")
    mubar_values = errorr_mf3(mubar_section)
    if mubar_values.size != len(MUBAR_QUANTITY_IDS):
        raise ValueError(f"tape46 MT251 has {mubar_values.size} values, expected 10")
    efmeans, chis = load_pfns_spectra(tape_directory)
    pfns_slices = load_pfns_slices()

    by_qid: dict[str, FloatArray] = {}
    for mt in ORDINARY_QUANTITY_IDS:
        section = gendf.get((3, mt))
        if section is None:
            raise ValueError(f"tape91: no MF3 MT{mt} section")
        by_qid[f"{mt:05d}"] = gendf_mf3(section)
    for quantity_id, value in zip(MUBAR_QUANTITY_IDS, mubar_values, strict=True):
        by_qid[f"{quantity_id:05d}"] = np.array([value])
    for quantity_id in PFNS_QUANTITY_IDS:
        lo, hi = pfns_slices[quantity_id]
        by_qid[f"{quantity_id:05d}"] = slice_average(efmeans, chis, lo, hi)

    values = np.empty(len(state_ids), dtype=np.float64)
    for index, state_id in enumerate(state_ids):
        qid, position = state_position(state_id)
        values[index] = by_qid[qid][position]
    return values


def state_position(state_id: str) -> tuple[str, int]:
    """Split a state ID into (QID, position within the QID)."""
    parts = state_id.split("_")
    if len(parts) not in (2, 3) or parts[0] != str(ZAID):
        raise ValueError(f"state id must be 94239_<qid>[_<group>]: {state_id}")
    position = int(parts[2]) if len(parts) == 3 else 0
    return parts[1], position


def load_state_ids() -> tuple[str, ...]:
    """Return the 979 state IDs in the prior's order."""
    path = PRIOR_PATH if PRIOR_PATH.is_file() else FALLBACK_PRIOR_PATH
    with h5py.File(path, "r") as h5:
        dataset = cast(h5py.Dataset, h5["mean/row_indices"])
        raw = cast(list[bytes | str], np.asarray(dataset[()]).tolist())
    return tuple(v.decode("utf-8") if isinstance(v, bytes) else v for v in raw)


def reproduction_error(values: FloatArray, released: FloatArray) -> float:
    """Return max |x - mu| / max |mu| over one quantity's states."""
    scale = float(np.max(np.abs(released)))
    if scale == 0.0:
        raise ValueError("Released means are all zero; relative error undefined")
    return float(np.max(np.abs(values - released)) / scale)


def is_reproduced(error: float) -> bool:
    """Return True when a relative reproduction error passes the gate."""
    return error <= REPRODUCTION_TOLERANCE


def enforce_gate(errors: dict[str, float]) -> dict[str, bool]:
    """Apply the reproduction gate; raise on regressions outside the expected set."""
    flags = {qid: is_reproduced(error) for qid, error in errors.items()}
    regressions = [
        qid for qid, ok in flags.items() if not ok and qid not in EXPECTED_UNREPRODUCED
    ]
    if regressions:
        raise ValueError(f"Reproduction gate failed for QIDs {regressions}")
    for qid in EXPECTED_UNREPRODUCED:
        if flags.get(qid):
            print(f"Note: QID {qid} now reproduces; update EXPECTED_UNREPRODUCED")
    return flags


def write_string_dataset(group: h5py.Group, name: str, values: tuple[str, ...]) -> None:
    """Write one UTF-8 string dataset."""
    _ = group.create_dataset(
        name,
        data=np.asarray(values, dtype=object),
        dtype=h5py.string_dtype(encoding="utf-8"),
    )


def write_output(
    output_path: Path,
    state_ids: tuple[str, ...],
    values: dict[str, FloatArray],
    qids: tuple[str, ...],
    errors: dict[str, float],
    flags: dict[str, bool],
    attributes: dict[str, str],
) -> None:
    """Write the reference values and gate results."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.unlink(missing_ok=True)
    state_flags = np.array(
        [flags[state_position(state_id)[0]] for state_id in state_ids],
        dtype=bool,
    )

    try:
        with h5py.File(temporary_path, "w") as h5:
            for key, value in attributes.items():
                h5.attrs[key] = value
            write_string_dataset(h5, "row_indices", state_ids)
            for name in ("viii0", "viii1"):
                group = h5.create_group(name)
                _ = group.create_dataset("values", data=values[name], dtype=np.float64)
            qid_group = h5.create_group("qid")
            write_string_dataset(qid_group, "ids", qids)
            _ = qid_group.create_dataset(
                "reproduction_error",
                data=np.array([errors[q] for q in qids], dtype=np.float64),
            )
            _ = qid_group.create_dataset(
                "reproduced",
                data=np.array([flags[q] for q in qids], dtype=bool),
            )
            state_group = h5.create_group("state")
            _ = state_group.create_dataset("reproduced", data=state_flags, dtype=bool)
        _ = temporary_path.replace(output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def parse_arguments() -> bool:
    """Parse the NJOY reuse flag."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--skip-njoy",
        action="store_true",
        help="reuse existing NJOY work directories instead of running NJOY",
    )
    return bool(parser.parse_args().skip_njoy)


def main() -> None:
    """Run NJOY for both libraries, apply the gate and write the HDF5 output."""
    skip_njoy = parse_arguments()
    for library in LIBRARIES:
        verify_endf_file(library)

    state_ids = load_state_ids()
    qids = tuple(f"{q:05d}" for q in QUANTITY_IDS)
    released = {q: load_released_means(int(q)) for q in qids}

    values: dict[str, FloatArray] = {}
    versions: dict[str, str] = {}
    for library in LIBRARIES:
        work_directory, version = run_njoy(library, skip_njoy=skip_njoy)
        versions[library.name] = version
        values[library.name] = build_library_values(work_directory, state_ids)

    errors: dict[str, float] = {}
    for qid in qids:
        mask = np.array([state_position(s)[0] == qid for s in state_ids])
        errors[qid] = reproduction_error(values["viii0"][mask], released[qid])
    flags = enforce_gate(errors)

    attributes = {
        "njoy_version": versions["viii0"],
        "njoy_input_source": str(NJOY_INPUT_PATH),
        "viii0_endf_sha256": LIBRARIES[0].sha256,
        "viii1_endf_sha256": LIBRARIES[1].sha256,
    }
    write_output(OUTPUT_PATH, state_ids, values, qids, errors, flags, attributes)

    print(f"Wrote: {OUTPUT_PATH}")
    print(f"States: {len(state_ids)}")
    for qid in qids:
        status = "ok" if flags[qid] else "not reproduced"
        print(f"QID {qid}: error {errors[qid]:.3e} {status}")


if __name__ == "__main__":
    main()
