"""Convert the SG52 JEZEBEL observation CSV files to one validated HDF5 file.

The sensitivity CSV files are stored by SG52 as:

    response x nuclear-data parameter

This converter transposes them before writing, so the HDF5 representation is:

    nuclear-data parameter x response

The original parameter and response labels are preserved verbatim.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import h5py
import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]

OBSERVATION_COLUMNS: Final[tuple[str, ...]] = (
    "expt",
    "expt_uncert",
    "sim",
    "sim_uncert",
    "total_uncert",
    "bias",
)


@dataclass(frozen=True)
class ObservationData:
    response_ids: tuple[str, ...]
    experimental: FloatArray
    experimental_uncertainty: FloatArray
    simulated: FloatArray
    simulated_uncertainty: FloatArray
    total_uncertainty: FloatArray
    bias: FloatArray


@dataclass(frozen=True)
class SensitivityData:
    response_ids: tuple[str, ...]
    parameter_ids: tuple[str, ...]
    values: FloatArray


def _read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file)

        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{path.name}: file is empty") from exc

        rows = [row for row in reader if row]

    if not rows:
        raise ValueError(f"{path.name}: file contains a header but no data rows")

    return header, rows


def load_observations(path: Path) -> ObservationData:
    header, rows = _read_csv_rows(path)

    expected_header = ("", *OBSERVATION_COLUMNS)

    if tuple(header) != expected_header:
        raise ValueError(
            f"{path.name}: unexpected header.\n"
            f"Expected: {expected_header}\n"
            f"Got:      {tuple(header)}"
        )

    expected_columns = len(expected_header)

    for row_number, row in enumerate(rows, start=2):
        if len(row) != expected_columns:
            raise ValueError(
                f"{path.name}, row {row_number}: "
                f"expected {expected_columns} columns, got {len(row)}"
            )

    response_ids = tuple(row[0] for row in rows)

    if len(set(response_ids)) != len(response_ids):
        raise ValueError(f"{path.name}: duplicate response IDs found")

    numeric = np.asarray(
        [[float(value) for value in row[1:]] for row in rows],
        dtype=np.float64,
    )

    observations = ObservationData(
        response_ids=response_ids,
        experimental=numeric[:, 0].copy(),
        experimental_uncertainty=numeric[:, 1].copy(),
        simulated=numeric[:, 2].copy(),
        simulated_uncertainty=numeric[:, 3].copy(),
        total_uncertainty=numeric[:, 4].copy(),
        bias=numeric[:, 5].copy(),
    )

    _validate_observation_derived_columns(path, observations)

    return observations


def _validate_observation_derived_columns(
    path: Path,
    observations: ObservationData,
) -> None:
    calculated_total_uncertainty = np.hypot(
        observations.experimental_uncertainty,
        observations.simulated_uncertainty,
    )

    if not np.allclose(
        observations.total_uncertainty,
        calculated_total_uncertainty,
        rtol=1.0e-6,
        atol=1.0e-12,
    ):
        raise ValueError(
            f"{path.name}: total_uncert does not match "
            "sqrt(expt_uncert^2 + sim_uncert^2)"
        )

    if np.any(observations.total_uncertainty <= 0.0):
        raise ValueError(f"{path.name}: total uncertainty must be positive")

    calculated_bias = (
        np.abs(observations.simulated - observations.experimental)
        / observations.total_uncertainty
    )

    if not np.allclose(
        observations.bias,
        calculated_bias,
        rtol=1.0e-6,
        atol=1.0e-10,
    ):
        raise ValueError(
            f"{path.name}: bias does not match "
            "abs(sim - expt) / total_uncert"
        )


def load_sensitivities(path: Path) -> SensitivityData:
    header, rows = _read_csv_rows(path)

    if not header or header[0] != "":
        raise ValueError(
            f"{path.name}: expected an empty first header cell "
            "for the response-ID column"
        )

    parameter_ids = tuple(header[1:])

    if not parameter_ids:
        raise ValueError(f"{path.name}: no sensitivity parameters found")

    if len(set(parameter_ids)) != len(parameter_ids):
        raise ValueError(f"{path.name}: duplicate parameter IDs found")

    expected_columns = len(header)
    response_ids: list[str] = []
    raw_values: list[list[float]] = []

    for row_number, row in enumerate(rows, start=2):
        if len(row) != expected_columns:
            raise ValueError(
                f"{path.name}, row {row_number}: "
                f"expected {expected_columns} columns, got {len(row)}"
            )

        response_ids.append(row[0])
        raw_values.append([float(value) for value in row[1:]])

    response_id_tuple = tuple(response_ids)

    if len(set(response_id_tuple)) != len(response_id_tuple):
        raise ValueError(f"{path.name}: duplicate response IDs found")

    response_by_parameter = np.asarray(
        raw_values,
        dtype=np.float64,
    )

    # SG52 CSV orientation:
    #     response x parameter
    #
    # Internal/HDF5 orientation:
    #     parameter x response
    parameter_by_response = response_by_parameter.T.copy()

    return SensitivityData(
        response_ids=response_id_tuple,
        parameter_ids=parameter_ids,
        values=parameter_by_response,
    )


def validate_alignment(
    observations: ObservationData,
    sensitivities: SensitivityData,
    sensitivity_uncertainties: SensitivityData,
) -> None:
    if sensitivities.response_ids != sensitivity_uncertainties.response_ids:
        raise ValueError(
            "Sensitivity values and sensitivity uncertainties "
            "do not have identical response IDs in identical order"
        )

    if sensitivities.parameter_ids != sensitivity_uncertainties.parameter_ids:
        raise ValueError(
            "Sensitivity values and sensitivity uncertainties "
            "do not have identical parameter IDs in identical order"
        )

    if observations.response_ids != sensitivities.response_ids:
        raise ValueError(
            "Observation and sensitivity response IDs "
            "do not match in identical order"
        )

    if sensitivities.values.shape != sensitivity_uncertainties.values.shape:
        raise ValueError(
            "Sensitivity values and sensitivity uncertainties "
            "have different matrix shapes"
        )


def _write_string_dataset(
    group: h5py.Group,
    name: str,
    values: tuple[str, ...],
) -> None:
    string_dtype = h5py.string_dtype(encoding="utf-8")
    group.create_dataset(
        name,
        data=np.asarray(values, dtype=object),
        dtype=string_dtype,
    )


def write_hdf5(
    output_path: Path,
    observations: ObservationData,
    sensitivities: SensitivityData,
    sensitivity_uncertainties: SensitivityData,
    observation_source: Path,
    sensitivity_source: Path,
    sensitivity_uncertainty_source: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with h5py.File(str(output_path), "w") as h5:
        h5.attrs["format"] = "WPEC SG52 JEZEBEL observation data"
        h5.attrs["schema_version"] = "0.1"
        h5.attrs["sensitivity_orientation"] = "parameter x response"

        observation_group = h5.create_group("observations")
        observation_group.attrs["source_file"] = observation_source.name

        _write_string_dataset(
            observation_group,
            "response_ids",
            observations.response_ids,
        )

        observation_group.create_dataset(
            "experimental",
            data=observations.experimental,
        )
        observation_group.create_dataset(
            "experimental_uncertainty",
            data=observations.experimental_uncertainty,
        )
        observation_group.create_dataset(
            "simulated",
            data=observations.simulated,
        )
        observation_group.create_dataset(
            "simulated_uncertainty",
            data=observations.simulated_uncertainty,
        )
        observation_group.create_dataset(
            "total_uncertainty",
            data=observations.total_uncertainty,
        )
        observation_group.create_dataset(
            "bias",
            data=observations.bias,
        )

        sensitivity_group = h5.create_group("sensitivities")
        sensitivity_group.attrs["relative_source_file"] = sensitivity_source.name
        sensitivity_group.attrs["relative_uncertainty_source_file"] = (
            sensitivity_uncertainty_source.name
        )
        sensitivity_group.attrs["orientation"] = "parameter x response"

        _write_string_dataset(
            sensitivity_group,
            "parameter_ids",
            sensitivities.parameter_ids,
        )
        _write_string_dataset(
            sensitivity_group,
            "response_ids",
            sensitivities.response_ids,
        )

        sensitivity_group.create_dataset(
            "relative",
            data=sensitivities.values,
            compression="gzip",
            shuffle=True,
        )
        sensitivity_group.create_dataset(
            "relative_uncertainty",
            data=sensitivity_uncertainties.values,
            compression="gzip",
            shuffle=True,
        )


def main() -> None:
    directory = Path(
        "/home/aurja/Programming/OECDNEA_WPEC_SG52/"
        "Auroras_solution/Exercise_1/Observations/"
    )

    observation_file = directory / "JEZEBEL" / "JEZEBEL_obs.csv"
    sensitivity_file = directory / "JEZEBEL" / "JEZEBEL_sens_rel.csv"
    sensitivity_uncertainty_file = directory / "JEZEBEL" / "JEZEBEL_sens_unc_rel.csv"

    output_file = directory / "exercise_1_observations.hdf5"

    observations = load_observations(observation_file)
    sensitivities = load_sensitivities(sensitivity_file)
    sensitivity_uncertainties = load_sensitivities(
        sensitivity_uncertainty_file
    )

    validate_alignment(
        observations,
        sensitivities,
        sensitivity_uncertainties,
    )

    write_hdf5(
        output_path=output_file,
        observations=observations,
        sensitivities=sensitivities,
        sensitivity_uncertainties=sensitivity_uncertainties,
        observation_source=observation_file,
        sensitivity_source=sensitivity_file,
        sensitivity_uncertainty_source=sensitivity_uncertainty_file,
    )

    print(f"Wrote: {output_file}")
    print(f"Responses: {len(observations.response_ids)}")
    print(f"Parameters: {len(sensitivities.parameter_ids)}")
    print(
        "Sensitivity matrix shape "
        f"(parameter x response): {sensitivities.values.shape}"
    )


if __name__ == "__main__":
    main()
