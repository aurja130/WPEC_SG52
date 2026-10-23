"""Exercise 4 regression: integral rows match Exercise 3; Marini nu-bar rows are added."""

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, TypeAlias, cast

import h5py
import numpy as np
from ex4_observations import (
    DEFAULT_MARINI_PATH,
    DEFAULT_SOURCE_DIRECTORY,
    MARINI_GROUP_COUNT,
    load_marini_nubar,
    parameter_to_prior_index,
    require_positive_definite,
    total_nubar_prior_index,
)
from numpy.typing import NDArray

FloatArray: TypeAlias = NDArray[np.float64]

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
EXERCISE_3_BUILDER: Final = REPOSITORY_ROOT / "Exercise_3" / "ex3_observations.py"
EXERCISE_4_BUILDER: Final = Path(__file__).resolve().with_name("ex4_observations.py")
INTEGRAL_COUNT: Final = 29
MARINI_COUNT: Final = 25
PRIOR_COUNT: Final = 979
ENERGY_GROUP_COUNT: Final = 51


def synthetic_means(count: int) -> np.ndarray:
    """Distinct positive prior means, so a wrong target state shows in C / mu."""
    return 1.0 + 1.0e-3 * np.arange(count, dtype=np.float64)


@dataclass(frozen=True)
class Outputs:
    """One GLLS observation file read back into memory."""

    response_ids: tuple[str, ...]
    prior_ids: tuple[str, ...]
    delta: FloatArray
    covariance: FloatArray
    sensitivity: FloatArray
    experimental: FloatArray
    simulated: FloatArray
    experimental_uncertainty: FloatArray
    simulated_uncertainty: FloatArray


def read_outputs(path: Path) -> Outputs:
    """Read the observation datasets written by an observation builder."""
    with h5py.File(path, "r") as h5:
        return Outputs(
            response_ids=tuple(h5["responses/row_indices"].asstr()[()]),
            prior_ids=tuple(h5["sens/col_indices"].asstr()[()]),
            delta=np.asarray(h5["delta/values"], dtype=np.float64),
            covariance=np.asarray(h5["cov/values"], dtype=np.float64),
            sensitivity=np.asarray(h5["sens/values"], dtype=np.float64),
            experimental=np.asarray(h5["responses/experimental"], dtype=np.float64),
            simulated=np.asarray(h5["responses/simulated"], dtype=np.float64),
            experimental_uncertainty=np.asarray(
                h5["responses/experimental_uncertainty"], dtype=np.float64
            ),
            simulated_uncertainty=np.asarray(
                h5["responses/simulated_uncertainty"], dtype=np.float64
            ),
        )


def release_response_ids() -> list[str]:
    """Return the 29 released integral response IDs in source order."""
    ids: list[str] = []
    for family in ("JEZEBEL", "EUCLID"):
        path = DEFAULT_SOURCE_DIRECTORY / family / f"{family}_obs.csv"
        with path.open(newline="", encoding="utf-8") as file:
            rows = [row for row in csv.reader(file) if row]
        ids.extend(row[0] for row in rows[1:])
    return ids


def release_parameter_ids() -> tuple[str, ...]:
    """Return the released sensitivity parameter header without the index column."""
    path = DEFAULT_SOURCE_DIRECTORY / "JEZEBEL" / "JEZEBEL_sens_rel.csv"
    with path.open(newline="", encoding="utf-8") as file:
        header = next(csv.reader(file))
    return tuple(header[1:])


def synthetic_prior_indices() -> list[str]:
    """Return 979 unique prior states covering all mapped, MT452, and MT456 states."""
    mapped = [
        parameter_to_prior_index(name)
        for name in release_parameter_ids()
        if name.startswith("Pu239_")
    ]
    required = [
        *mapped,
        *(total_nubar_prior_index(group) for group in range(ENERGY_GROUP_COUNT)),
        *(f"94239_00456_{group}" for group in range(ENERGY_GROUP_COUNT)),
    ]
    states = list(dict.fromkeys(required))
    if len(states) > PRIOR_COUNT:
        raise ValueError(f"{len(states)} required prior states exceed {PRIOR_COUNT}")
    states.extend(f"unused_{index}" for index in range(PRIOR_COUNT - len(states)))
    return states


def write_synthetic_prior(path: Path, indices: list[str]) -> None:
    """Write a prior with the combined HDF5 layout and distinct positive means."""
    with h5py.File(path, "w") as h5:
        group = h5.create_group("mean")
        _ = group.create_dataset(
            "row_indices",
            data=np.asarray(indices, dtype=object),
            dtype=h5py.string_dtype(encoding="utf-8"),
        )
        _ = group.create_dataset(
            "values", data=synthetic_means(len(indices)), dtype=np.float64
        )


def run_builder(script: Path, prior: Path, output: Path) -> None:
    """Run one observation builder on the synthetic prior; fail with its stderr."""
    result = subprocess.run(
        [sys.executable, str(script), "--prior", str(prior), "--output", str(output)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script.name} failed:\n{result.stderr}")


def load_document() -> dict[str, Any]:
    """Load the released Marini nu-bar JSON, failing loudly if it is missing."""
    if not DEFAULT_MARINI_PATH.is_file():
        raise FileNotFoundError(
            f"Required Marini nu-bar file not found: {DEFAULT_MARINI_PATH}"
        )
    with DEFAULT_MARINI_PATH.open(encoding="utf-8") as file:
        return cast(dict[str, Any], json.load(file))


def write_variant(directory: Path, edit: Callable[[dict[str, Any]], None]) -> Path:
    """Write a copy of the released Marini JSON after applying one edit."""
    document = load_document()
    edit(document)
    path = directory / "nubar_variant.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def released_marini_arrays(
    document: dict[str, Any],
) -> tuple[FloatArray, FloatArray, FloatArray]:
    """Return released n/f values, relative uncertainties, and evaluated values."""
    experimental = np.asarray(document["experimental data"]["values"], dtype=np.float64)
    relative = np.asarray(document["experimental data"]["uncertainties"], dtype=np.float64)
    evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)
    return experimental, relative, evaluated


class ExerciseFourObservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        root = Path(directory.name)
        prior = root / "prior.hdf5"
        write_synthetic_prior(prior, synthetic_prior_indices())
        run_builder(EXERCISE_4_BUILDER, prior, root / "ex4.hdf5")
        run_builder(EXERCISE_3_BUILDER, prior, root / "ex3.hdf5")
        cls.ex4 = read_outputs(root / "ex4.hdf5")
        cls.ex3 = read_outputs(root / "ex3.hdf5")
        cls.document = load_document()

    def test_release_integral_inventory_is_the_29_response_order(self) -> None:
        ids = release_response_ids()
        self.assertEqual(len(ids), INTEGRAL_COUNT)
        self.assertEqual(len(set(ids)), INTEGRAL_COUNT)
        self.assertEqual(ids[0], "PU-MET-FAST-001-001-s")
        self.assertEqual(ids[3], "PU-MET-FAST-001-001_Pu239/U235")
        self.assertEqual(ids[4:6], ["euclid-3x2-crit", "euclid-8x1-crit"])
        self.assertTrue(all(name.startswith("euclid_NLS_") for name in ids[6:21]))
        self.assertTrue(all(name.startswith("euclid_rrr_") for name in ids[21:]))

    def test_response_inventory_appends_marini_points_in_order(self) -> None:
        marini_ids = [f"marini-nubar-{index:02d}" for index in range(MARINI_COUNT)]
        self.assertEqual(
            list(self.ex4.response_ids), [*release_response_ids(), *marini_ids]
        )
        self.assertEqual(self.ex4.delta.shape, (INTEGRAL_COUNT + MARINI_COUNT,))
        self.assertEqual(self.ex4.covariance.shape, (54, 54))
        self.assertEqual(self.ex4.sensitivity.shape, (54, PRIOR_COUNT))

    def test_integral_rows_match_exercise_3_exactly(self) -> None:
        integral = slice(0, INTEGRAL_COUNT)
        self.assertEqual(self.ex4.prior_ids, self.ex3.prior_ids)
        self.assertEqual(self.ex4.response_ids[integral], self.ex3.response_ids)
        np.testing.assert_array_equal(self.ex4.delta[integral], self.ex3.delta)
        np.testing.assert_array_equal(
            self.ex4.covariance[integral, integral], self.ex3.covariance
        )
        np.testing.assert_array_equal(
            self.ex4.sensitivity[integral], self.ex3.sensitivity
        )
        np.testing.assert_array_equal(
            self.ex4.experimental[integral], self.ex3.experimental
        )
        np.testing.assert_array_equal(
            self.ex4.simulated[integral], self.ex3.simulated
        )
        np.testing.assert_array_equal(
            self.ex4.experimental_uncertainty[integral],
            self.ex3.experimental_uncertainty,
        )
        np.testing.assert_array_equal(
            self.ex4.simulated_uncertainty[integral], self.ex3.simulated_uncertainty
        )

    def test_integral_and_marini_covariance_blocks_are_uncorrelated(self) -> None:
        covariance = self.ex4.covariance
        np.testing.assert_array_equal(covariance[:INTEGRAL_COUNT, INTEGRAL_COUNT:], 0.0)
        np.testing.assert_array_equal(covariance[INTEGRAL_COUNT:, :INTEGRAL_COUNT], 0.0)

    def test_marini_responses_and_delta_use_released_values(self) -> None:
        experimental, relative, evaluated = released_marini_arrays(self.document)
        sigma = relative * experimental
        marini = slice(INTEGRAL_COUNT, None)
        np.testing.assert_allclose(self.ex4.experimental[marini], experimental, rtol=1e-12)
        np.testing.assert_allclose(self.ex4.simulated[marini], evaluated, rtol=1e-12)
        np.testing.assert_allclose(
            self.ex4.experimental_uncertainty[marini], sigma, rtol=1e-12
        )
        np.testing.assert_array_equal(self.ex4.simulated_uncertainty[marini], 0.0)
        np.testing.assert_allclose(
            self.ex4.delta[marini], experimental - evaluated, rtol=1e-12
        )

    def test_marini_covariance_is_scaled_correlation_and_positive_definite(self) -> None:
        experimental, relative, _ = released_marini_arrays(self.document)
        correlation = np.asarray(
            self.document["experimental data"]["correlations"], dtype=np.float64
        ).reshape(MARINI_COUNT, MARINI_COUNT)
        scale = np.diag(relative * experimental)
        expected = scale @ correlation @ scale
        block = self.ex4.covariance[INTEGRAL_COUNT:, INTEGRAL_COUNT:]
        np.testing.assert_allclose(block, expected, rtol=1e-12, atol=1e-30)
        require_positive_definite(block, "Marini nu-bar block")

    def test_marini_sensitivities_land_on_mt452_states_without_mt456(self) -> None:
        _, _, evaluated = released_marini_arrays(self.document)
        energies = np.asarray(
            self.document["experimental data"]["structure"]["limits"], dtype=np.float64
        )
        edges = np.asarray(
            self.document["sensitivities"]["structure"]["limits"], dtype=np.float64
        )
        released = np.asarray(self.document["sensitivities"]["values"], dtype=np.float64)
        groups = np.searchsorted(edges, energies, side="right") - 1
        np.testing.assert_array_equal(
            np.argmax(released[:, :MARINI_GROUP_COUNT], axis=1), groups
        )

        sensitivity = self.ex4.sensitivity[INTEGRAL_COUNT:]
        means = synthetic_means(PRIOR_COUNT)
        for row, group in enumerate(groups):
            column = self.ex4.prior_ids.index(total_nubar_prior_index(int(group)))
            expected = np.zeros(PRIOR_COUNT, dtype=np.float64)
            expected[column] = evaluated[row] / means[column]
            np.testing.assert_allclose(sensitivity[row], expected, rtol=1e-12, atol=0.0)
        mt456 = [
            index
            for index, name in enumerate(self.ex4.prior_ids)
            if name.startswith("94239_00456_")
        ]
        np.testing.assert_array_equal(self.ex4.sensitivity[:, mt456], 0.0)

    def test_release_marini_points_all_pass_the_selection_rules(self) -> None:
        points = load_marini_nubar(DEFAULT_MARINI_PATH)
        self.assertEqual(points.released_indices, tuple(range(MARINI_COUNT)))
        self.assertEqual(points.dropped_indices, ())
        self.assertEqual(points.sensitivity.shape, (MARINI_COUNT, MARINI_GROUP_COUNT))
        np.testing.assert_array_equal(points.sensitivity.sum(axis=1), 1.0)

    def test_column_51_sensitivity_is_rejected(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["sensitivities"]["values"][0][MARINI_GROUP_COUNT] = 1.0

        with tempfile.TemporaryDirectory() as directory:
            path = write_variant(Path(directory), edit)
            with self.assertRaisesRegex(ValueError, "column 51"):
                _ = load_marini_nubar(path)

    def test_point_above_20_mev_is_dropped(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["experimental data"]["structure"]["limits"][MARINI_COUNT - 1] = 20.5

        with tempfile.TemporaryDirectory() as directory:
            points = load_marini_nubar(write_variant(Path(directory), edit))
        self.assertEqual(points.dropped_indices, (MARINI_COUNT - 1,))
        self.assertEqual(points.released_indices, tuple(range(MARINI_COUNT - 1)))

    def test_non_one_hot_sensitivity_row_is_rejected(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["sensitivities"]["values"][0] = [0.5] + [0.0] * MARINI_GROUP_COUNT

        with tempfile.TemporaryDirectory() as directory:
            path = write_variant(Path(directory), edit)
            with self.assertRaisesRegex(ValueError, "one-hot"):
                _ = load_marini_nubar(path)

    def test_missing_marini_file_fails_loudly(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            _ = load_marini_nubar(Path(directory) / "absent.json")

    def test_require_positive_definite_rejects_indefinite_and_asymmetric_blocks(
        self,
    ) -> None:
        with self.assertRaisesRegex(ValueError, "positive definite"):
            require_positive_definite(np.array([[1.0, 2.0], [2.0, 1.0]]), "test block")
        with self.assertRaisesRegex(ValueError, "symmetric"):
            require_positive_definite(np.array([[1.0, 0.5], [0.0, 1.0]]), "test block")


if __name__ == "__main__":
    unittest.main()
