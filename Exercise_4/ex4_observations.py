"""Build Exercise 4 observation inputs from released integral and Marini nu-bar responses.

JEZEBEL and EUCLID relative sensitivities are aligned to the Pu-239 prior
state indices and converted to absolute response derivatives for GLLS. The
Marini prompt nu-bar points follow the as-MT452 rule and are appended with a
block-diagonal covariance, so integral and Marini blocks are uncorrelated.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections.abc import Mapping
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
)
JEZEBEL_CRITICALITY_ID: Final = "PU-MET-FAST-001-001-s"
EUCLID_CRITICALITY_IDS: Final = ("euclid-3x2-crit", "euclid-8x1-crit")
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
    / "SG52_materials"
    / "SG52_materials_release_3"
    / "Adjustement set"
    / "Integral"
)
DEFAULT_PRIOR_PATH: Final = EXERCISE_DIRECTORY / "ex4_prior.hdf5"
DEFAULT_OUTPUT_PATH: Final = EXERCISE_DIRECTORY / "ex4_observations.hdf5"
DEFAULT_MARINI_PATH: Final = (
    REPOSITORY_ROOT.parent
    / "SG52_materials"
    / "SG52_materials_release_3"
    / "Adjustement set"
    / "Differential"
    / "Marini nubar"
    / "nubar_Marini2021.json"
)
MARINI_RESPONSE_PREFIX: Final = "marini-nubar-"
MARINI_POINT_COUNT: Final = 25
MARINI_SENSITIVITY_COLUMNS: Final = 52
MARINI_GROUP_COUNT: Final = 51
MARINI_ENERGY_LIMIT_MEV: Final = 20.0


@dataclass(frozen=True)
class ObservationData:
    """Values and uncertainties indexed by integral response ID."""

    response_ids: tuple[str, ...]
    experimental: FloatArray
    experimental_uncertainty: FloatArray
    simulated: FloatArray
    simulated_uncertainty: FloatArray


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
    experimental: FloatArray
    simulated: FloatArray
    experimental_uncertainty: FloatArray
    simulated_uncertainty: FloatArray


@dataclass(frozen=True)
class MariniPoints:
    """Released Marini nu-bar points kept by the Exercise 4 selection rules."""

    released_indices: tuple[int, ...]
    dropped_indices: tuple[int, ...]
    experimental: FloatArray
    relative_uncertainty: FloatArray
    correlation: FloatArray
    evaluated: FloatArray
    sensitivity: FloatArray  # relative, 51 energy groups, one-hot rows


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


def load_observations(path: Path, source: str) -> ObservationData:
    """Load every released response in source order and validate the inventory."""
    header, rows = read_csv(path)
    expected_header = ("", *OBSERVATION_COLUMNS)
    if tuple(header) != expected_header:
        raise ValueError(
            f"{path.name}: expected header {expected_header}, got {tuple(header)}"
        )

    response_ids = tuple(row[0] for row in rows)
    if not all(response_ids) or len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{path.name}: response IDs must be non-empty and unique")
    if source == "JEZEBEL":
        valid_inventory = (
            len(response_ids) == 4
            and response_ids[0] == JEZEBEL_CRITICALITY_ID
            and all(
                response_id.startswith("PU-MET-FAST-001-001_")
                for response_id in response_ids[1:]
            )
        )
    elif source == "EUCLID":
        valid_inventory = (
            len(response_ids) == 25
            and response_ids[:2] == EUCLID_CRITICALITY_IDS
            and all(response_id.startswith("euclid_NLS_") for response_id in response_ids[2:17])
            and all(response_id.startswith("euclid_rrr_") for response_id in response_ids[17:])
        )
    else:
        raise ValueError(f"Unknown integral response source: {source}")
    if not valid_inventory:
        raise ValueError(f"{path.name}: unexpected {source} response inventory or order")

    numeric = parse_float_rows(path, rows)
    experimental = numeric[:, 0].copy()
    experimental_uncertainty = numeric[:, 1].copy()
    simulated = numeric[:, 2].copy()
    simulated_uncertainty = numeric[:, 3].copy()

    if np.any(experimental_uncertainty < 0.0) or np.any(simulated_uncertainty < 0.0):
        raise ValueError(f"{path.name}: component uncertainties must be nonnegative")
    if np.any(experimental_uncertainty**2 + simulated_uncertainty**2 <= 0.0):
        raise ValueError(f"{path.name}: expt_uncert^2 + sim_uncert^2 must be positive")

    return ObservationData(
        response_ids=response_ids,
        experimental=experimental,
        experimental_uncertainty=experimental_uncertainty,
        simulated=simulated,
        simulated_uncertainty=simulated_uncertainty,
    )


def load_sensitivities(path: Path, required_ids: tuple[str, ...]) -> SensitivityData:
    """Load all relative sensitivity rows in observation source order."""
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
    if response_ids != required_ids:
        raise ValueError(f"{path.name}: sensitivity response IDs differ from observations")
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


def build_inputs(
    observations: tuple[ObservationData, ObservationData],
    sensitivities: tuple[SensitivityData, SensitivityData],
    prior: PriorData,
) -> ObservationInputs:
    """Align both integral sources and form the 29 absolute GLLS integral rows."""
    for observation, relative in zip(observations, sensitivities, strict=True):
        if observation.response_ids != relative.response_ids:
            raise ValueError("Observation and sensitivity response IDs differ")
    if len({*observations[0].response_ids, *observations[1].response_ids}) != 29:
        raise ValueError("JEZEBEL and EUCLID response IDs must be distinct")
    if sensitivities[0].parameter_ids != sensitivities[1].parameter_ids:
        raise ValueError("JEZEBEL and EUCLID sensitivity parameter headers differ")

    response_indices = (*observations[0].response_ids, *observations[1].response_ids)
    experimental = np.concatenate([data.experimental for data in observations])
    experimental_uncertainty = np.concatenate(
        [data.experimental_uncertainty for data in observations]
    )
    simulated = np.concatenate([data.simulated for data in observations])
    simulated_uncertainty = np.concatenate(
        [data.simulated_uncertainty for data in observations]
    )
    relative_values = np.concatenate([data.values for data in sensitivities], axis=0)
    delta = experimental - simulated
    variance = experimental_uncertainty**2 + simulated_uncertainty**2
    covariance = np.diag(variance).astype(np.float64, copy=False)

    prior_position = {index: position for position, index in enumerate(prior.indices)}
    sensitivity = np.zeros(
        (len(response_indices), len(prior.indices)),
        dtype=np.float64,
    )
    populated_prior_indices: set[str] = set()

    for source_column, parameter_id in enumerate(sensitivities[0].parameter_ids):
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

        relative = relative_values[:, source_column]
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
        experimental=experimental,
        simulated=simulated,
        experimental_uncertainty=experimental_uncertainty,
        simulated_uncertainty=simulated_uncertainty,
    )


def float_array_at(
    document: Mapping[str, object],
    keys: tuple[str, ...],
    shape: tuple[int, ...],
) -> FloatArray:
    """Return one finite float64 JSON array at a nested key path, checking its shape."""
    label = "/".join(keys)
    node: object = document
    for key in keys:
        if not isinstance(node, Mapping) or key not in node:
            raise ValueError(f"Marini nu-bar JSON lacks {label}")
        node = node[key]
    array = np.asarray(node, dtype=np.float64)
    if array.shape != shape:
        raise ValueError(f"{label}: expected shape {shape}, found {array.shape}")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label}: contains non-finite values")
    return array


def require_positive_definite(matrix: FloatArray, name: str) -> None:
    """Raise unless the matrix is symmetric and admits a Cholesky factorization."""
    asymmetry = np.max(np.abs(matrix - matrix.T))
    if asymmetry > 1e-12 * np.max(np.abs(matrix)):
        raise ValueError(f"{name} must be symmetric")
    try:
        _ = np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"{name} must be positive definite") from exc


def total_nubar_prior_index(group: int) -> str:
    """Return the prior state carrying total nu-bar (MT452) in one energy group."""
    return f"94239_00452_{group}"


def load_marini_nubar(path: Path) -> MariniPoints:
    """Load the released Marini nu-bar points and apply the Exercise 4 selection rules."""
    if not path.is_file():
        raise FileNotFoundError(f"Required Marini nu-bar file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        document = cast(dict[str, object], json.load(file))

    count = MARINI_POINT_COUNT
    energies = float_array_at(
        document, ("experimental data", "structure", "limits"), (count,)
    )
    experimental = float_array_at(document, ("experimental data", "values"), (count,))
    relative_uncertainty = float_array_at(
        document, ("experimental data", "uncertainties"), (count,)
    )
    correlation = float_array_at(
        document, ("experimental data", "correlations"), (count * count,)
    ).reshape(count, count)
    evaluated = float_array_at(document, ("evaluated data", "values"), (count,))
    sensitivity = float_array_at(
        document, ("sensitivities", "values"), (count, MARINI_SENSITIVITY_COLUMNS)
    )

    if np.any(sensitivity[:, MARINI_GROUP_COUNT:] != 0.0):
        raise ValueError(
            f"{path.name}: sensitivity column {MARINI_GROUP_COUNT} "
            "(above 20 MeV) must be zero"
        )
    groups = sensitivity[:, :MARINI_GROUP_COUNT]
    for position, row in enumerate(groups):
        nonzero = row[row != 0.0]
        if nonzero.size > 1 or (nonzero.size == 1 and nonzero[0] != 1.0):
            raise ValueError(
                f"{path.name}: sensitivity row {position} must be one-hot "
                "(single 1.0) or all zero"
            )

    kept = tuple(
        position
        for position in range(count)
        if energies[position] <= MARINI_ENERGY_LIMIT_MEV
        and np.any(groups[position] != 0.0)
    )
    if not kept:
        raise ValueError(f"{path.name}: no Marini nu-bar point passes the rules")
    dropped = tuple(position for position in range(count) if position not in kept)
    selected = np.asarray(kept, dtype=np.intp)
    return MariniPoints(
        released_indices=kept,
        dropped_indices=dropped,
        experimental=experimental[selected],
        relative_uncertainty=relative_uncertainty[selected],
        correlation=correlation[np.ix_(selected, selected)],
        evaluated=evaluated[selected],
        sensitivity=groups[selected],
    )


def build_marini_inputs(points: MariniPoints, prior: PriorData) -> ObservationInputs:
    """Form the Marini nu-bar GLLS rows; sensitivities land on MT452 prior states."""
    prior_position = {index: position for position, index in enumerate(prior.indices)}
    response_indices = tuple(
        f"{MARINI_RESPONSE_PREFIX}{index:02d}" for index in points.released_indices
    )
    sigma = points.relative_uncertainty * points.experimental
    covariance = np.diag(sigma) @ points.correlation @ np.diag(sigma)
    require_positive_definite(covariance, "Marini nu-bar covariance block")

    sensitivity = np.zeros((len(response_indices), len(prior.indices)), dtype=np.float64)
    for row, relative_row in enumerate(points.sensitivity):
        for group in np.flatnonzero(relative_row):
            target_index = total_nubar_prior_index(int(group))
            try:
                target_column = prior_position[target_index]
            except KeyError as exc:
                raise ValueError(
                    f"Marini nu-bar maps to absent prior index {target_index}"
                ) from exc
            prior_mean = float(prior.mean[target_column])
            if prior_mean == 0.0:
                raise ValueError(
                    f"Cannot convert nonzero Marini sensitivity for zero prior "
                    f"{target_index}"
                )
            sensitivity[row, target_column] = (
                points.evaluated[row] * relative_row[group] / prior_mean
            )

    return ObservationInputs(
        response_indices=response_indices,
        prior_indices=prior.indices,
        delta=points.experimental - points.evaluated,
        covariance=covariance,
        sensitivity=sensitivity,
        experimental=points.experimental,
        simulated=points.evaluated,
        experimental_uncertainty=sigma,
        simulated_uncertainty=np.zeros_like(sigma),
    )


def combine_inputs(
    integral: ObservationInputs, marini: ObservationInputs
) -> ObservationInputs:
    """Stack integral and Marini rows; integral-Marini covariance blocks are zero."""
    if integral.prior_indices != marini.prior_indices:
        raise ValueError("Integral and Marini inputs use different prior indices")
    response_indices = (*integral.response_indices, *marini.response_indices)
    if len(set(response_indices)) != len(response_indices):
        raise ValueError("Combined observation response IDs must be distinct")
    integral_count = len(integral.response_indices)
    covariance = np.zeros(
        (len(response_indices), len(response_indices)), dtype=np.float64
    )
    covariance[:integral_count, :integral_count] = integral.covariance
    covariance[integral_count:, integral_count:] = marini.covariance
    return ObservationInputs(
        response_indices=response_indices,
        prior_indices=integral.prior_indices,
        delta=np.concatenate([integral.delta, marini.delta]),
        covariance=covariance,
        sensitivity=np.vstack([integral.sensitivity, marini.sensitivity]),
        experimental=np.concatenate([integral.experimental, marini.experimental]),
        simulated=np.concatenate([integral.simulated, marini.simulated]),
        experimental_uncertainty=np.concatenate(
            [integral.experimental_uncertainty, marini.experimental_uncertainty]
        ),
        simulated_uncertainty=np.concatenate(
            [integral.simulated_uncertainty, marini.simulated_uncertainty]
        ),
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
    """Write indexed GLLS inputs and the released response values."""
    response_count = len(inputs.response_indices)
    prior_count = len(inputs.prior_indices)
    if inputs.delta.shape != (response_count,):
        raise ValueError("Observation delta shape does not match its row indices")
    if inputs.covariance.shape != (response_count, response_count):
        raise ValueError("Observation covariance shape does not match its indices")
    if inputs.sensitivity.shape != (response_count, prior_count):
        raise ValueError("Sensitivity shape does not match its row and column indices")
    if inputs.experimental.shape != (response_count,):
        raise ValueError("Experimental response shape does not match its indices")
    if inputs.simulated.shape != (response_count,):
        raise ValueError("Simulated response shape does not match its indices")
    for name, values in (
        ("Experimental uncertainty", inputs.experimental_uncertainty),
        ("Simulated uncertainty", inputs.simulated_uncertainty),
    ):
        if values.shape != (response_count,):
            raise ValueError(f"{name} shape does not match its indices")

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

            responses_group = h5.create_group("responses")
            write_string_dataset(responses_group, "row_indices", inputs.response_indices)
            _ = responses_group.create_dataset(
                "experimental", data=inputs.experimental, dtype=np.float64
            )
            _ = responses_group.create_dataset(
                "simulated", data=inputs.simulated, dtype=np.float64
            )
            _ = responses_group.create_dataset(
                "experimental_uncertainty",
                data=inputs.experimental_uncertainty,
                dtype=np.float64,
            )
            _ = responses_group.create_dataset(
                "simulated_uncertainty",
                data=inputs.simulated_uncertainty,
                dtype=np.float64,
            )

        _ = temporary_path.replace(output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def parse_arguments() -> tuple[Path, Path, Path, Path]:
    """Parse optional source, Marini, prior, and output path overrides."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--source-directory",
        type=Path,
        default=DEFAULT_SOURCE_DIRECTORY,
        help=f"integral source directory (default: {DEFAULT_SOURCE_DIRECTORY})",
    )
    _ = parser.add_argument(
        "--marini",
        type=Path,
        default=DEFAULT_MARINI_PATH,
        help=f"Marini nu-bar JSON file (default: {DEFAULT_MARINI_PATH})",
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
        cast(Path, arguments.marini),
        cast(Path, arguments.prior),
        cast(Path, arguments.output),
    )


def main() -> None:
    """Build and write the Exercise 4 observation inputs."""
    source_argument, marini_argument, prior_argument, output_argument = parse_arguments()
    source_directory = source_argument.resolve()
    marini_path = marini_argument.resolve()
    prior_path = prior_argument.resolve()
    output_path = output_argument.resolve()

    observations = (
        load_observations(
            source_directory / "JEZEBEL" / "JEZEBEL_obs.csv", "JEZEBEL"
        ),
        load_observations(
            source_directory / "EUCLID" / "EUCLID_obs.csv", "EUCLID"
        ),
    )
    sensitivities = (
        load_sensitivities(
            source_directory / "JEZEBEL" / "JEZEBEL_sens_rel.csv",
            observations[0].response_ids,
        ),
        load_sensitivities(
            source_directory / "EUCLID" / "EUCLID_sens_rel.csv",
            observations[1].response_ids,
        ),
    )
    prior = load_prior(prior_path)
    integral_inputs = build_inputs(observations, sensitivities, prior)
    marini = load_marini_nubar(marini_path)
    inputs = combine_inputs(integral_inputs, build_marini_inputs(marini, prior))
    write_observations(output_path, inputs)

    print(f"Wrote: {output_path}")
    print(f"Responses: {len(inputs.response_indices)}")
    print(f"Marini nu-bar points kept: {len(marini.released_indices)}")
    print(f"Marini nu-bar dropped points: {list(marini.dropped_indices)}")
    print(f"Prior states: {len(inputs.prior_indices)}")
    print(f"Delta shape: {inputs.delta.shape}")
    print(f"Covariance shape: {inputs.covariance.shape}")
    print(f"Sensitivity shape: {inputs.sensitivity.shape}")


if __name__ == "__main__":
    main()
