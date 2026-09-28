"""Build the Exercise 1 observation inputs from the released JEZEBEL data.

Exercise 1 uses the PMF-001 criticality response. Relative sensitivities from
SG52 are aligned to the prior state indices and converted to absolute response
derivatives before being written for the GLLS calculation.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypeAlias, cast

import h5py
import numpy as np
from numpy.typing import NDArray

FloatArray: TypeAlias = NDArray[np.float64]

OBSERVATION_COLUMNS: Final = (
    "expt",
    "expt_uncert",
    "sim",
    "sim_uncert",
    "total_uncert",
    "bias",
)
EXERCISE_1_RESPONSE_IDS: Final = ("PU-MET-FAST-001-001-s",)
REACTION_QUANTITY_IDS: Final = {
    "elastic": 2,
    "inelastic": 4,
    "z,2n": 16,
    "z,3n": 17,
    "fission": 18,
    "z,4n": 37,
    "capture": 102,
}

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
EXERCISE_DIRECTORY: Final = Path(__file__).resolve().parent
DEFAULT_SOURCE_DIRECTORY: Final = (
    REPOSITORY_ROOT.parent
    / "SG52_materials_release_2"
    / "Adjustement set"
    / "Integral"
    / "JEZEBEL"
)
DEFAULT_PRIOR_PATH: Final = EXERCISE_DIRECTORY / "ex1_prior.hdf5"
DEFAULT_OUTPUT_PATH: Final = EXERCISE_DIRECTORY / "ex1_observations.hdf5"


@dataclass(frozen=True)
class ObservationData:
    """Values and uncertainties indexed by integral response ID."""

    response_ids: tuple[str, ...]
    experimental: FloatArray
    simulated: FloatArray
    total_uncertainty: FloatArray


@dataclass(frozen=True)
class SensitivityData:
    """Relative sensitivities in source response-by-parameter orientation."""

    response_ids: tuple[str, ...]
    parameter_ids: tuple[str, ...]
    values: FloatArray


@dataclass(frozen=True)
class PriorData:
    """Prior means and canonical state indices used for alignment."""

    indices: tuple[str, ...]
    mean: FloatArray


@dataclass(frozen=True)
class ObservationInputs:
    """Final arrays and indices consumed by the GLLS executable."""

    response_indices: tuple[str, ...]
    prior_indices: tuple[str, ...]
    delta: FloatArray
    covariance: FloatArray
    sensitivity: FloatArray


def read_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    """Read one non-empty rectangular CSV file."""
    if not path.is_file():
        raise FileNotFoundError(f"Required SG52 source file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{path.name}: file is empty") from exc
        rows = [row for row in reader if row]

    if not rows:
        raise ValueError(f"{path.name}: file contains a header but no data rows")

    expected_columns = len(header)
    for row_number, row in enumerate(rows, start=2):
        if len(row) != expected_columns:
            message = (
                f"{path.name}, row {row_number}: expected {expected_columns} "
                f"columns, got {len(row)}"
            )
            raise ValueError(message)

    return header, rows


def parse_float_rows(path: Path, rows: list[list[str]]) -> FloatArray:
    """Parse all non-index CSV cells as finite float64 values."""
    try:
        values = np.asarray(
            [[float(value) for value in row[1:]] for row in rows],
            dtype=np.float64,
        )
    except ValueError as exc:
        raise ValueError(f"{path.name}: contains a non-numeric value") from exc

    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path.name}: contains non-finite values")
    return values


def load_observations(path: Path) -> ObservationData:
    """Load and validate released JEZEBEL observation values."""
    header, rows = read_csv(path)
    expected_header = ("", *OBSERVATION_COLUMNS)
    if tuple(header) != expected_header:
        raise ValueError(
            f"{path.name}: expected header {expected_header}, got {tuple(header)}"
        )

    response_ids = tuple(row[0] for row in rows)
    if len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{path.name}: duplicate response IDs found")

    numeric = parse_float_rows(path, rows)
    experimental = numeric[:, 0].copy()
    experimental_uncertainty = numeric[:, 1]
    simulated = numeric[:, 2].copy()
    simulated_uncertainty = numeric[:, 3]
    total_uncertainty = numeric[:, 4].copy()
    bias = numeric[:, 5]

    calculated_uncertainty = np.hypot(
        experimental_uncertainty,
        simulated_uncertainty,
    )
    if not np.allclose(
        total_uncertainty,
        calculated_uncertainty,
        rtol=1.0e-6,
        atol=1.0e-12,
    ):
        raise ValueError(
            f"{path.name}: total_uncert does not match the component uncertainties"
        )
    if np.any(total_uncertainty <= 0.0):
        raise ValueError(f"{path.name}: total uncertainty must be positive")

    calculated_bias = np.abs(simulated - experimental) / total_uncertainty
    if not np.allclose(bias, calculated_bias, rtol=1.0e-6, atol=1.0e-10):
        raise ValueError(
            f"{path.name}: bias does not match abs(sim - expt) / total_uncert"
        )

    return ObservationData(
        response_ids=response_ids,
        experimental=experimental,
        simulated=simulated,
        total_uncertainty=total_uncertainty,
    )


def load_sensitivities(path: Path) -> SensitivityData:
    """Load relative sensitivities in their released row orientation."""
    header, rows = read_csv(path)
    if not header or header[0] != "":
        raise ValueError(
            f"{path.name}: expected an empty first header cell for response IDs"
        )

    parameter_ids = tuple(header[1:])
    if not parameter_ids:
        raise ValueError(f"{path.name}: no sensitivity parameters found")
    if len(set(parameter_ids)) != len(parameter_ids):
        raise ValueError(f"{path.name}: duplicate sensitivity parameters found")

    response_ids = tuple(row[0] for row in rows)
    if len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{path.name}: duplicate response IDs found")

    return SensitivityData(
        response_ids=response_ids,
        parameter_ids=parameter_ids,
        values=parse_float_rows(path, rows),
    )


def load_prior(path: Path) -> PriorData:
    """Load the canonical state indices and means from the combined prior."""
    if not path.is_file():
        raise FileNotFoundError(f"Required prior file not found: {path}")

    with h5py.File(str(path), "r") as h5:
        index_dataset = h5.get("mean/row_indices")
        mean_dataset = h5.get("mean/values")
        if not isinstance(index_dataset, h5py.Dataset):
            raise TypeError(f"{path}: /mean/row_indices is not a dataset")
        if not isinstance(mean_dataset, h5py.Dataset):
            raise TypeError(f"{path}: /mean/values is not a dataset")

        raw_indices = np.asarray(index_dataset.asstr()[()], dtype=np.str_)
        indices = tuple(map(str, raw_indices))
        mean = np.asarray(mean_dataset, dtype=np.float64)

    if not indices or len(set(indices)) != len(indices):
        raise ValueError(f"{path}: prior indices must be non-empty and unique")
    if mean.shape != (len(indices),):
        message = (
            f"{path}: prior mean shape {mean.shape} does not match "
            f"{len(indices)} indices"
        )
        raise ValueError(message)
    if not np.all(np.isfinite(mean)):
        raise ValueError(f"{path}: prior mean contains non-finite values")

    return PriorData(indices=indices, mean=mean)


def parameter_to_prior_index(parameter_id: str) -> str:
    """Map one released Pu-239 sensitivity parameter to a prior state ID."""
    parts = parameter_id.split("_")
    if len(parts) < 4 or parts[0] != "Pu239":
        raise ValueError(f"Unsupported Pu-239 sensitivity parameter: {parameter_id}")

    family, reaction = parts[1], parts[2]
    if family == "crossSection" and reaction in REACTION_QUANTITY_IDS:
        if len(parts) != 4:
            raise ValueError(f"Malformed sensitivity parameter: {parameter_id}")
        quantity_id = REACTION_QUANTITY_IDS[reaction]
        return f"94239_{quantity_id:05d}_{int(parts[3])}"

    if family == "multiplicity" and reaction == "total nu":
        if len(parts) != 4:
            raise ValueError(f"Malformed sensitivity parameter: {parameter_id}")
        return f"94239_00452_{int(parts[3])}"

    if family == "spectrum" and reaction == "prompt nu":
        if len(parts) != 5:
            raise ValueError(f"Malformed sensitivity parameter: {parameter_id}")
        incident_group = int(parts[3])
        quantity_id = 1018 + 100 * incident_group
        return f"94239_{quantity_id:05d}_{int(parts[4])}"

    if family == "crossSection" and reaction == "mubar":
        if len(parts) != 4:
            raise ValueError(f"Malformed sensitivity parameter: {parameter_id}")
        quantity_id = 251 + 1000 * int(parts[3])
        return f"94239_{quantity_id:05d}"

    raise ValueError(f"Unsupported Pu-239 sensitivity parameter: {parameter_id}")


def select_response_positions(response_ids: tuple[str, ...]) -> tuple[int, ...]:
    """Locate all Exercise 1 responses in released row order."""
    positions: list[int] = []
    for response_id in EXERCISE_1_RESPONSE_IDS:
        try:
            positions.append(response_ids.index(response_id))
        except ValueError as exc:
            raise ValueError(
                f"Required Exercise 1 response not found: {response_id}"
            ) from exc
    return tuple(positions)


def build_inputs(
    observations: ObservationData,
    sensitivities: SensitivityData,
    prior: PriorData,
) -> ObservationInputs:
    """Align released data and form absolute GLLS observation inputs."""
    if observations.response_ids != sensitivities.response_ids:
        raise ValueError(
            "Observation and sensitivity response IDs differ or are out of order"
        )

    positions = select_response_positions(observations.response_ids)
    response_indices = tuple(observations.response_ids[index] for index in positions)
    position_array = np.asarray(positions, dtype=np.int64)
    experimental = observations.experimental[position_array]
    simulated = observations.simulated[position_array]
    uncertainty = observations.total_uncertainty[position_array]
    delta = experimental - simulated
    covariance = np.diag(np.square(uncertainty)).astype(np.float64, copy=False)

    prior_position = {index: position for position, index in enumerate(prior.indices)}
    sensitivity = np.zeros(
        (len(response_indices), len(prior.indices)),
        dtype=np.float64,
    )
    populated_prior_indices: set[str] = set()

    for source_column, parameter_id in enumerate(sensitivities.parameter_ids):
        if not parameter_id.startswith("Pu239_"):
            continue

        target_index = parameter_to_prior_index(parameter_id)
        if target_index in populated_prior_indices:
            raise ValueError(
                f"Multiple sensitivity parameters map to prior index {target_index}"
            )
        try:
            target_column = prior_position[target_index]
        except KeyError as exc:
            message = (
                f"Sensitivity parameter {parameter_id} maps to absent prior "
                f"index {target_index}"
            )
            raise ValueError(message) from exc

        relative: FloatArray = np.asarray(
            sensitivities.values.take(position_array, axis=0)[
                :,
                source_column : source_column + 1,
            ],
            dtype=np.float64,
        ).reshape(-1)
        prior_mean = prior.mean[target_column : target_column + 1]
        if np.count_nonzero(prior_mean) == 0:
            if np.count_nonzero(relative) != 0:
                raise ValueError(
                    f"Cannot convert nonzero sensitivity for zero prior {target_index}"
                )
        else:
            sensitivity[:, target_column] = simulated * relative / prior_mean
        populated_prior_indices.add(target_index)

    if not np.all(np.isfinite(delta)):
        raise ValueError("Observation delta contains non-finite values")
    if not np.all(np.isfinite(covariance)):
        raise ValueError("Observation covariance contains non-finite values")
    if not np.all(np.isfinite(sensitivity)):
        raise ValueError("Sensitivity matrix contains non-finite values")

    return ObservationInputs(
        response_indices=response_indices,
        prior_indices=prior.indices,
        delta=delta,
        covariance=covariance,
        sensitivity=sensitivity,
    )


def write_string_dataset(
    group: h5py.Group,
    name: str,
    indices: tuple[str, ...],
) -> None:
    """Write one UTF-8 index dataset."""
    _ = group.create_dataset(
        name,
        data=np.asarray(indices, dtype=object),
        dtype=h5py.string_dtype(encoding="utf-8"),
    )


def write_observations(output_path: Path, inputs: ObservationInputs) -> None:
    """Write only the indexed datasets consumed by the GLLS executable."""
    response_count = len(inputs.response_indices)
    prior_count = len(inputs.prior_indices)
    if inputs.delta.shape != (response_count,):
        raise ValueError("Observation delta shape does not match its row indices")
    if inputs.covariance.shape != (response_count, response_count):
        raise ValueError("Observation covariance shape does not match its indices")
    if inputs.sensitivity.shape != (response_count, prior_count):
        raise ValueError("Sensitivity shape does not match its row and column indices")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.unlink(missing_ok=True)

    try:
        with h5py.File(str(temporary_path), "w") as h5:
            delta_group = h5.create_group("delta")
            write_string_dataset(
                delta_group,
                "row_indices",
                inputs.response_indices,
            )
            _ = delta_group.create_dataset(
                "values",
                data=inputs.delta,
                dtype=np.float64,
            )

            covariance_group = h5.create_group("cov")
            write_string_dataset(
                covariance_group,
                "row_indices",
                inputs.response_indices,
            )
            write_string_dataset(
                covariance_group,
                "col_indices",
                inputs.response_indices,
            )
            _ = covariance_group.create_dataset(
                "values",
                data=inputs.covariance,
                dtype=np.float64,
            )

            sensitivity_group = h5.create_group("sens")
            write_string_dataset(
                sensitivity_group,
                "row_indices",
                inputs.response_indices,
            )
            write_string_dataset(
                sensitivity_group,
                "col_indices",
                inputs.prior_indices,
            )
            _ = sensitivity_group.create_dataset(
                "values",
                data=inputs.sensitivity,
                dtype=np.float64,
            )

        _ = temporary_path.replace(output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def parse_arguments() -> tuple[Path, Path, Path]:
    """Parse optional source, prior, and output path overrides."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--source-directory",
        type=Path,
        default=DEFAULT_SOURCE_DIRECTORY,
        help=f"JEZEBEL source directory (default: {DEFAULT_SOURCE_DIRECTORY})",
    )
    _ = parser.add_argument(
        "--prior",
        type=Path,
        default=DEFAULT_PRIOR_PATH,
        help=f"combined prior HDF5 file (default: {DEFAULT_PRIOR_PATH})",
    )
    _ = parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"output HDF5 file (default: {DEFAULT_OUTPUT_PATH})",
    )
    arguments = parser.parse_args()
    return (
        cast(Path, arguments.source_directory),
        cast(Path, arguments.prior),
        cast(Path, arguments.output),
    )


def main() -> None:
    """Build and write the Exercise 1 observation inputs."""
    source_argument, prior_argument, output_argument = parse_arguments()
    source_directory = source_argument.resolve()
    prior_path = prior_argument.resolve()
    output_path = output_argument.resolve()

    observations = load_observations(source_directory / "JEZEBEL_obs.csv")
    sensitivities = load_sensitivities(source_directory / "JEZEBEL_sens_rel.csv")
    prior = load_prior(prior_path)
    inputs = build_inputs(observations, sensitivities, prior)
    write_observations(output_path, inputs)

    print(f"Wrote: {output_path}")
    print(f"Responses: {len(inputs.response_indices)}")
    print(f"Prior states: {len(inputs.prior_indices)}")
    print(f"Delta shape: {inputs.delta.shape}")
    print(f"Covariance shape: {inputs.covariance.shape}")
    print(f"Sensitivity shape: {inputs.sensitivity.shape}")


if __name__ == "__main__":
    main()
