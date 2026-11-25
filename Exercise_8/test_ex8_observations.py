"""Exercise 8 regression: Exercise 6 rows are kept; Dongwi shape rows are added."""

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
from ex8_observations import (
    DEFAULT_DONGWI_PATH,
    DEFAULT_KEEGAN_PFNS_PATH,
    DEFAULT_MARINI_PATH,
    DEFAULT_MARINI_PFNS_PATH,
    DEFAULT_SNYDER_PATH,
    DEFAULT_SOURCE_DIRECTORY,
    DONGWI_POINT_COUNT,
    DONGWI_RESPONSE_PREFIX,
    KEEGAN_PFNS_PREFIX,
    MARINI_GROUP_COUNT,
    MARINI_PFNS_PREFIX,
    PFNS_INCIDENT_BIN_COUNT,
    PFNS_OUTGOING_GROUP_COUNT,
    SHAPE_SENSITIVITY_COLUMNS,
    SNYDER_POINT_COUNT,
    SNYDER_RESPONSE_PREFIX,
    load_marini_nubar,
    load_pfns,
    load_shape,
    parameter_to_prior_index,
    require_positive_definite,
    total_nubar_prior_index,
)
from numpy.typing import NDArray

FloatArray: TypeAlias = NDArray[np.float64]

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[1]
EXERCISE_4_BUILDER: Final = REPOSITORY_ROOT / "Exercise_4" / "ex4_observations.py"
EXERCISE_5_BUILDER: Final = REPOSITORY_ROOT / "Exercise_5" / "ex5_observations.py"
EXERCISE_6_BUILDER: Final = REPOSITORY_ROOT / "Exercise_6" / "ex6_observations.py"
EXERCISE_8_BUILDER: Final = Path(__file__).resolve().with_name("ex8_observations.py")
INTEGRAL_COUNT: Final = 29
MARINI_COUNT: Final = 25
EXERCISE_4_COUNT: Final = INTEGRAL_COUNT + MARINI_COUNT
MARINI_PFNS_KEPT: Final = 1220
MARINI_PFNS_RELEASED: Final = 1281
KEEGAN_PFNS_KEPT: Final = 1277
EXERCISE_5_COUNT: Final = EXERCISE_4_COUNT + MARINI_PFNS_KEPT + KEEGAN_PFNS_KEPT
SNYDER_KEPT: Final = 91
EXERCISE_6_COUNT: Final = EXERCISE_5_COUNT + SNYDER_KEPT
DONGWI_KEPT: Final = 91
TOTAL_COUNT: Final = EXERCISE_6_COUNT + DONGWI_KEPT
PRIOR_COUNT: Final = 979
ENERGY_GROUP_COUNT: Final = 51
MARINI_PFNS_BLOCK: Final = slice(EXERCISE_4_COUNT, EXERCISE_4_COUNT + MARINI_PFNS_KEPT)
KEEGAN_PFNS_BLOCK: Final = slice(EXERCISE_4_COUNT + MARINI_PFNS_KEPT, EXERCISE_5_COUNT)
SNYDER_BLOCK: Final = slice(EXERCISE_5_COUNT, EXERCISE_6_COUNT)
DONGWI_BLOCK: Final = slice(EXERCISE_6_COUNT, TOTAL_COUNT)
MARINI_PFNS_SOURCE: Final = DEFAULT_MARINI_PFNS_PATH
KEEGAN_PFNS_SOURCE: Final = DEFAULT_KEEGAN_PFNS_PATH
SNYDER_NORMALIZATION_UNCERTAINTY: Final = 0.0117
DONGWI_NORMALIZATION_UNCERTAINTY: Final = 0.0134


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


def read_strings(h5: h5py.File, key: str) -> tuple[str, ...]:
    """Return one HDF5 string dataset as a tuple of Python strings."""
    dataset = cast(h5py.Dataset, h5[key])
    return tuple(cast(list[str], dataset.asstr()[()]))


def read_outputs(path: Path) -> Outputs:
    """Read the observation datasets written by an observation builder."""
    with h5py.File(path, "r") as h5:
        return Outputs(
            response_ids=read_strings(h5, "responses/row_indices"),
            prior_ids=read_strings(h5, "sens/col_indices"),
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
    """Return unique prior states covering mapped, MT452, MT456, PFNS, Snyder and Dongwi targets."""
    mapped = [
        parameter_to_prior_index(name)
        for name in release_parameter_ids()
        if name.startswith("Pu239_")
    ]
    required = [
        *mapped,
        *(total_nubar_prior_index(group) for group in range(ENERGY_GROUP_COUNT)),
        *(f"94239_00456_{group}" for group in range(ENERGY_GROUP_COUNT)),
        *load_pfns(MARINI_PFNS_SOURCE, MARINI_PFNS_PREFIX).target_indices,
        *load_pfns(KEEGAN_PFNS_SOURCE, KEEGAN_PFNS_PREFIX).target_indices,
        *load_shape(
            DEFAULT_SNYDER_PATH, "Snyder", SNYDER_RESPONSE_PREFIX, SNYDER_POINT_COUNT
        ).target_indices,
        *load_shape(
            DEFAULT_DONGWI_PATH, "Dongwi", DONGWI_RESPONSE_PREFIX, DONGWI_POINT_COUNT
        ).target_indices,
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


def load_json(path: Path) -> dict[str, Any]:
    """Load one released JSON file, failing loudly if it is missing."""
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")
    with path.open(encoding="utf-8") as file:
        return cast(dict[str, Any], json.load(file))


def write_variant(
    directory: Path,
    source: Path,
    edit: Callable[[dict[str, Any]], None],
) -> Path:
    """Write a copy of one released JSON file after applying one edit."""
    document = load_json(source)
    edit(document)
    path = directory / "variant.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def released_pfns_arrays(
    document: dict[str, Any],
) -> tuple[FloatArray, FloatArray, FloatArray, FloatArray]:
    """Return released values, relative uncertainties, correlations, and evaluated values."""
    values = np.asarray(document["data"]["values"], dtype=np.float64)
    relative = np.asarray(document["data"]["uncertainties"], dtype=np.float64)
    correlation = np.asarray(document["data"]["correlations"], dtype=np.float64)
    evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)
    count = values.size
    return values, relative, correlation.reshape(count, count), evaluated


PFNS_BLOCK_COUNT: Final = 20
PFNS_NORMALIZATION_SIGMA: Final = 1.0  # 100 % per-block normalization (Captain 2026-11-25)


def pfns_normalization_term(document: dict[str, Any], kept: slice) -> FloatArray:
    """Return sigma_N**2 * sum_b outer(E_b, E_b) over the released incident-energy blocks."""
    values = np.asarray(document["data"]["values"], dtype=np.float64)[kept]
    energies = np.asarray(document["data"]["structure"][0]["limits"], dtype=np.float64)[kept]
    term = np.zeros((values.size, values.size), dtype=np.float64)
    for energy in np.unique(energies):
        block = np.where(energies == energy, values, 0.0)
        term += np.outer(block, block)
    return PFNS_NORMALIZATION_SIGMA**2 * term


def first_appearance_labels(energies: FloatArray) -> tuple[int, ...]:
    """Label each point by its energy block, numbered in order of first appearance."""
    labels: dict[float, int] = {}
    return tuple(labels.setdefault(energy, len(labels)) for energy in energies.tolist())


class ExerciseEightObservationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        directory = tempfile.TemporaryDirectory()
        cls.addClassCleanup(directory.cleanup)
        root = Path(directory.name)
        prior = root / "prior.hdf5"
        write_synthetic_prior(prior, synthetic_prior_indices())
        run_builder(EXERCISE_4_BUILDER, prior, root / "ex4.hdf5")
        run_builder(EXERCISE_5_BUILDER, prior, root / "ex5.hdf5")
        run_builder(EXERCISE_6_BUILDER, prior, root / "ex6.hdf5")
        run_builder(EXERCISE_8_BUILDER, prior, root / "ex8.hdf5")
        cls.ex4 = read_outputs(root / "ex4.hdf5")
        cls.ex5 = read_outputs(root / "ex5.hdf5")
        cls.ex6 = read_outputs(root / "ex6.hdf5")
        cls.ex8 = read_outputs(root / "ex8.hdf5")
        cls.marini_pfns_document = load_json(MARINI_PFNS_SOURCE)
        cls.keegan_pfns_document = load_json(KEEGAN_PFNS_SOURCE)
        cls.snyder_document = load_json(DEFAULT_SNYDER_PATH)
        cls.dongwi_document = load_json(DEFAULT_DONGWI_PATH)
        cls.marini_pfns = load_pfns(MARINI_PFNS_SOURCE, MARINI_PFNS_PREFIX)
        cls.keegan_pfns = load_pfns(KEEGAN_PFNS_SOURCE, KEEGAN_PFNS_PREFIX)
        cls.snyder = load_shape(
            DEFAULT_SNYDER_PATH, "Snyder", SNYDER_RESPONSE_PREFIX, SNYDER_POINT_COUNT
        )
        cls.dongwi = load_shape(
            DEFAULT_DONGWI_PATH, "Dongwi", DONGWI_RESPONSE_PREFIX, DONGWI_POINT_COUNT
        )

    def test_release_integral_inventory_is_the_29_response_order(self) -> None:
        ids = release_response_ids()
        self.assertEqual(len(ids), INTEGRAL_COUNT)
        self.assertEqual(len(set(ids)), INTEGRAL_COUNT)
        self.assertEqual(ids[0], "PU-MET-FAST-001-001-s")
        self.assertEqual(ids[3], "PU-MET-FAST-001-001_Pu239/U235")
        self.assertEqual(ids[4:6], ["euclid-3x2-crit", "euclid-8x1-crit"])

    def test_response_inventory_appends_marini_pfns_keegan_snyder_then_dongwi(self) -> None:
        marini_ids = [f"marini-nubar-{index:02d}" for index in range(MARINI_COUNT)]
        marini_pfns_ids = [
            f"{MARINI_PFNS_PREFIX}{index:04d}" for index in range(MARINI_PFNS_KEPT)
        ]
        keegan_pfns_ids = [
            f"{KEEGAN_PFNS_PREFIX}{index:04d}" for index in range(KEEGAN_PFNS_KEPT)
        ]
        snyder_ids = [f"snyder-{index:02d}" for index in range(SNYDER_KEPT)]
        dongwi_ids = [f"dongwi-{index:02d}" for index in range(DONGWI_KEPT)]
        self.assertEqual(
            list(self.ex8.response_ids),
            [
                *release_response_ids(),
                *marini_ids,
                *marini_pfns_ids,
                *keegan_pfns_ids,
                *snyder_ids,
                *dongwi_ids,
            ],
        )
        self.assertEqual(self.ex8.delta.shape, (TOTAL_COUNT,))
        self.assertEqual(self.ex8.covariance.shape, (TOTAL_COUNT, TOTAL_COUNT))
        self.assertEqual(self.ex8.sensitivity.shape, (TOTAL_COUNT, PRIOR_COUNT))
        self.assertEqual(self.ex8.response_ids[SNYDER_BLOCK][0], "snyder-00")
        self.assertEqual(self.ex8.response_ids[SNYDER_BLOCK][-1], "snyder-90")
        self.assertEqual(self.ex8.response_ids[DONGWI_BLOCK][0], "dongwi-00")
        self.assertEqual(self.ex8.response_ids[DONGWI_BLOCK][-1], "dongwi-90")

    def test_rows_0_to_53_match_exercise_4_exactly(self) -> None:
        head = slice(0, EXERCISE_4_COUNT)
        self.assertEqual(self.ex8.prior_ids, self.ex4.prior_ids)
        self.assertEqual(self.ex8.response_ids[head], self.ex4.response_ids)
        np.testing.assert_array_equal(self.ex8.delta[head], self.ex4.delta)
        np.testing.assert_array_equal(
            self.ex8.covariance[head, head], self.ex4.covariance
        )
        np.testing.assert_array_equal(self.ex8.sensitivity[head], self.ex4.sensitivity)
        np.testing.assert_array_equal(self.ex8.experimental[head], self.ex4.experimental)
        np.testing.assert_array_equal(self.ex8.simulated[head], self.ex4.simulated)
        np.testing.assert_array_equal(
            self.ex8.experimental_uncertainty[head], self.ex4.experimental_uncertainty
        )
        np.testing.assert_array_equal(
            self.ex8.simulated_uncertainty[head], self.ex4.simulated_uncertainty
        )

    def test_rows_0_to_2641_match_exercise_6_exactly(self) -> None:
        head = slice(0, EXERCISE_6_COUNT)
        self.assertEqual(self.ex8.prior_ids, self.ex6.prior_ids)
        self.assertEqual(self.ex8.response_ids[head], self.ex6.response_ids)
        np.testing.assert_array_equal(self.ex8.delta[head], self.ex6.delta)
        np.testing.assert_array_equal(
            self.ex8.covariance[head, head], self.ex6.covariance
        )
        np.testing.assert_array_equal(self.ex8.sensitivity[head], self.ex6.sensitivity)
        np.testing.assert_array_equal(self.ex8.experimental[head], self.ex6.experimental)
        np.testing.assert_array_equal(self.ex8.simulated[head], self.ex6.simulated)
        np.testing.assert_array_equal(
            self.ex8.experimental_uncertainty[head], self.ex6.experimental_uncertainty
        )
        np.testing.assert_array_equal(
            self.ex8.simulated_uncertainty[head], self.ex6.simulated_uncertainty
        )

    def test_rows_0_to_2550_match_exercise_5_exactly(self) -> None:
        head = slice(0, EXERCISE_5_COUNT)
        self.assertEqual(self.ex8.prior_ids, self.ex5.prior_ids)
        self.assertEqual(self.ex8.response_ids[head], self.ex5.response_ids)
        np.testing.assert_array_equal(self.ex8.delta[head], self.ex5.delta)
        np.testing.assert_array_equal(
            self.ex8.covariance[head, head], self.ex5.covariance
        )
        np.testing.assert_array_equal(self.ex8.sensitivity[head], self.ex5.sensitivity)
        np.testing.assert_array_equal(self.ex8.experimental[head], self.ex5.experimental)
        np.testing.assert_array_equal(self.ex8.simulated[head], self.ex5.simulated)
        np.testing.assert_array_equal(
            self.ex8.experimental_uncertainty[head], self.ex5.experimental_uncertainty
        )
        np.testing.assert_array_equal(
            self.ex8.simulated_uncertainty[head], self.ex5.simulated_uncertainty
        )

    def test_blocks_are_mutually_uncorrelated(self) -> None:
        blocks = (
            slice(0, INTEGRAL_COUNT),
            slice(INTEGRAL_COUNT, EXERCISE_4_COUNT),
            MARINI_PFNS_BLOCK,
            KEEGAN_PFNS_BLOCK,
            SNYDER_BLOCK,
            DONGWI_BLOCK,
        )
        covariance = self.ex8.covariance
        for a, first in enumerate(blocks):
            for b, second in enumerate(blocks):
                if a != b:
                    np.testing.assert_array_equal(covariance[first, second], 0.0)

    def test_marini_pfns_values_and_covariance_use_released_data(self) -> None:
        values, relative, correlation, evaluated = released_pfns_arrays(
            self.marini_pfns_document
        )
        kept = slice(0, MARINI_PFNS_KEPT)
        sigma = relative[kept] * values[kept]
        block = slice(MARINI_PFNS_BLOCK.start, MARINI_PFNS_BLOCK.stop)
        np.testing.assert_allclose(self.ex8.experimental[block], values[kept], rtol=1e-12)
        np.testing.assert_allclose(self.ex8.simulated[block], evaluated[kept], rtol=1e-12)
        np.testing.assert_allclose(
            self.ex8.experimental_uncertainty[block], sigma, rtol=1e-12
        )
        np.testing.assert_array_equal(self.ex8.simulated_uncertainty[block], 0.0)
        np.testing.assert_allclose(
            self.ex8.delta[block], values[kept] - evaluated[kept], rtol=1e-12
        )
        scale = np.diag(sigma)
        expected = (
            scale @ correlation[kept, kept] @ scale
            + pfns_normalization_term(self.marini_pfns_document, kept)
        )
        np.testing.assert_allclose(
            self.ex8.covariance[block, block], expected, rtol=1e-12, atol=1e-30
        )
        require_positive_definite(self.ex8.covariance[block, block], "Marini PFNS block")

    def test_keegan_pfns_values_and_covariance_use_released_data(self) -> None:
        values, relative, correlation, evaluated = released_pfns_arrays(
            self.keegan_pfns_document
        )
        self.assertEqual(KEEGAN_PFNS_KEPT, values.size)
        sigma = relative * values
        np.testing.assert_allclose(
            self.ex8.experimental[KEEGAN_PFNS_BLOCK], values, rtol=1e-12
        )
        np.testing.assert_allclose(
            self.ex8.simulated[KEEGAN_PFNS_BLOCK], evaluated, rtol=1e-12
        )
        np.testing.assert_allclose(
            self.ex8.experimental_uncertainty[KEEGAN_PFNS_BLOCK], sigma, rtol=1e-12
        )
        scale = np.diag(sigma)
        expected = scale @ correlation @ scale + pfns_normalization_term(
            self.keegan_pfns_document, slice(None)
        )
        np.testing.assert_allclose(
            self.ex8.covariance[KEEGAN_PFNS_BLOCK, KEEGAN_PFNS_BLOCK],
            expected,
            rtol=1e-12,
            atol=1e-30,
        )
        require_positive_definite(
            self.ex8.covariance[KEEGAN_PFNS_BLOCK, KEEGAN_PFNS_BLOCK], "Keegan PFNS block"
        )

    def test_pfns_blocks_are_twenty_incident_energy_groups(self) -> None:
        for points, document in (
            (self.marini_pfns, self.marini_pfns_document),
            (self.keegan_pfns, self.keegan_pfns_document),
        ):
            energies = np.asarray(document["data"]["structure"][0]["limits"], dtype=np.float64)
            kept_energies = energies[np.asarray(points.released_indices)]
            self.assertEqual(np.unique(kept_energies).size, PFNS_BLOCK_COUNT)
            self.assertEqual(points.block_ids, first_appearance_labels(kept_energies))

    def test_pfns_covariance_between_blocks_is_plain_d_rho_d(self) -> None:
        for block, points, document in (
            (MARINI_PFNS_BLOCK, self.marini_pfns, self.marini_pfns_document),
            (KEEGAN_PFNS_BLOCK, self.keegan_pfns, self.keegan_pfns_document),
        ):
            values, relative, correlation, _ = released_pfns_arrays(document)
            released = np.asarray(points.released_indices)
            first, last = 0, released.size - 1
            self.assertNotEqual(points.block_ids[first], points.block_ids[last])
            sigma = relative[released] * values[released]
            np.testing.assert_allclose(
                self.ex8.experimental_uncertainty[block], sigma, rtol=1e-12
            )
            expected = sigma[first] * correlation[released[first], released[last]] * sigma[last]
            np.testing.assert_allclose(
                self.ex8.covariance[block.start + first, block.start + last],
                expected,
                rtol=1e-12,
                atol=1e-30,
            )

    def test_pfns_sensitivities_land_on_one_prior_state_as_c_over_mu(self) -> None:
        means = synthetic_means(PRIOR_COUNT)
        for block, points, document in (
            (MARINI_PFNS_BLOCK, self.marini_pfns, self.marini_pfns_document),
            (KEEGAN_PFNS_BLOCK, self.keegan_pfns, self.keegan_pfns_document),
        ):
            _, _, _, evaluated = released_pfns_arrays(document)
            sensitivity = self.ex8.sensitivity[block]
            energies_in = np.asarray(document["data"]["structure"][0]["limits"], dtype=np.float64)
            energies_out = np.asarray(document["data"]["structure"][1]["limits"], dtype=np.float64)
            edges_in = np.asarray(document["sensitivities"]["structure"][0]["limits"], dtype=np.float64)
            edges_out = np.asarray(document["sensitivities"]["structure"][1]["limits"], dtype=np.float64)
            mt = cast(list[int], document["sensitivities"]["structure"][0]["mt"])
            for row, released in enumerate(points.released_indices):
                incident = int(np.searchsorted(edges_in, energies_in[released], side="right")) - 1
                group = int(np.searchsorted(edges_out, energies_out[released], side="right")) - 1
                column = self.ex8.prior_ids.index(f"94239_{mt[incident]:05d}_{group}")
                expected = np.zeros(PRIOR_COUNT, dtype=np.float64)
                expected[column] = evaluated[released] / means[column]
                np.testing.assert_allclose(sensitivity[row], expected, rtol=1e-12, atol=0.0)
        mt456 = [
            index
            for index, name in enumerate(self.ex8.prior_ids)
            if name.startswith("94239_00456_")
        ]
        np.testing.assert_array_equal(self.ex8.sensitivity[:, mt456], 0.0)

    def test_snyder_values_and_covariance_use_released_data(self) -> None:
        document = self.snyder_document
        kept = slice(0, SNYDER_KEPT)
        energies = np.asarray(document["experimental data"]["values"], dtype=np.float64)[kept]
        relative = np.asarray(document["experimental data"]["uncertainties"], dtype=np.float64)[kept]
        correlation = np.asarray(
            document["experimental data"]["correlations"], dtype=np.float64
        ).reshape(SNYDER_POINT_COUNT, SNYDER_POINT_COUNT)[kept, kept]
        evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)[kept]
        sigma = relative * energies
        np.testing.assert_allclose(self.ex8.experimental[SNYDER_BLOCK], energies, rtol=1e-12)
        np.testing.assert_allclose(self.ex8.simulated[SNYDER_BLOCK], evaluated, rtol=1e-12)
        np.testing.assert_allclose(
            self.ex8.experimental_uncertainty[SNYDER_BLOCK], sigma, rtol=1e-12
        )
        np.testing.assert_array_equal(self.ex8.simulated_uncertainty[SNYDER_BLOCK], 0.0)
        np.testing.assert_allclose(
            self.ex8.delta[SNYDER_BLOCK], energies - evaluated, rtol=1e-12
        )
        scale = np.diag(sigma)
        expected = scale @ correlation @ scale + 0.0117**2 * np.outer(energies, energies)
        np.testing.assert_allclose(
            self.ex8.covariance[SNYDER_BLOCK, SNYDER_BLOCK], expected, rtol=1e-12, atol=1e-30
        )
        require_positive_definite(self.ex8.covariance[SNYDER_BLOCK, SNYDER_BLOCK], "Snyder block")

    def test_snyder_sensitivity_lands_on_one_mt18_state_as_c_over_mu(self) -> None:
        means = synthetic_means(PRIOR_COUNT)
        document = self.snyder_document
        energies_in = np.asarray(document["experimental data"]["structure"]["limits"], dtype=np.float64)
        edges = np.asarray(document["sensitivities"]["structure"]["limits"], dtype=np.float64)
        evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)
        sensitivity = self.ex8.sensitivity[SNYDER_BLOCK]
        for row, released in enumerate(self.snyder.released_indices):
            group = int(np.searchsorted(edges, energies_in[released], side="right")) - 1
            column = self.ex8.prior_ids.index(f"94239_00018_{group}")
            expected = np.zeros(PRIOR_COUNT, dtype=np.float64)
            expected[column] = evaluated[released] / means[column]
            np.testing.assert_allclose(sensitivity[row], expected, rtol=1e-12, atol=0.0)

    def test_snyder_drops_the_20_54_mev_point(self) -> None:
        self.assertEqual(self.snyder.released_indices, tuple(range(SNYDER_KEPT)))
        self.assertEqual(self.snyder.dropped_indices, (SNYDER_POINT_COUNT - 1,))

    def test_snyder_variant_with_two_hot_row_is_rejected(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["sensitivities"]["values"][0] = [1.0, 1.0] + [0.0] * (
                SHAPE_SENSITIVITY_COLUMNS - 2
            )

        with tempfile.TemporaryDirectory() as directory:
            path = write_variant(Path(directory), DEFAULT_SNYDER_PATH, edit)
            with self.assertRaisesRegex(ValueError, "one-hot"):
                _ = load_shape(path, "Snyder", SNYDER_RESPONSE_PREFIX, SNYDER_POINT_COUNT)

    def test_missing_snyder_file_fails_loudly(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            _ = load_shape(
                Path(directory) / "absent.json",
                "Snyder",
                SNYDER_RESPONSE_PREFIX,
                SNYDER_POINT_COUNT,
            )

    def test_dongwi_values_and_covariance_use_released_data(self) -> None:
        document = self.dongwi_document
        kept = slice(0, DONGWI_KEPT)
        energies = np.asarray(document["experimental data"]["values"], dtype=np.float64)[kept]
        relative = np.asarray(document["experimental data"]["uncertainties"], dtype=np.float64)[kept]
        correlation = np.asarray(
            document["experimental data"]["correlations"], dtype=np.float64
        ).reshape(DONGWI_POINT_COUNT, DONGWI_POINT_COUNT)[kept, kept]
        evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)[kept]
        sigma = relative * energies
        np.testing.assert_allclose(self.ex8.experimental[DONGWI_BLOCK], energies, rtol=1e-12)
        np.testing.assert_allclose(self.ex8.simulated[DONGWI_BLOCK], evaluated, rtol=1e-12)
        np.testing.assert_allclose(
            self.ex8.experimental_uncertainty[DONGWI_BLOCK], sigma, rtol=1e-12
        )
        np.testing.assert_array_equal(self.ex8.simulated_uncertainty[DONGWI_BLOCK], 0.0)
        np.testing.assert_allclose(
            self.ex8.delta[DONGWI_BLOCK], energies - evaluated, rtol=1e-12
        )
        scale = np.diag(sigma)
        expected = scale @ correlation @ scale + 0.0134**2 * np.outer(energies, energies)
        np.testing.assert_allclose(
            self.ex8.covariance[DONGWI_BLOCK, DONGWI_BLOCK], expected, rtol=1e-12, atol=1e-30
        )
        require_positive_definite(self.ex8.covariance[DONGWI_BLOCK, DONGWI_BLOCK], "Dongwi block")

    def test_dongwi_sensitivity_lands_on_one_mt18_state_as_c_over_mu(self) -> None:
        means = synthetic_means(PRIOR_COUNT)
        document = self.dongwi_document
        energies_in = np.asarray(document["experimental data"]["structure"]["limits"], dtype=np.float64)
        edges = np.asarray(document["sensitivities"]["structure"]["limits"], dtype=np.float64)
        evaluated = np.asarray(document["evaluated data"]["values"], dtype=np.float64)
        sensitivity = self.ex8.sensitivity[DONGWI_BLOCK]
        for row, released in enumerate(self.dongwi.released_indices):
            group = int(np.searchsorted(edges, energies_in[released], side="right")) - 1
            column = self.ex8.prior_ids.index(f"94239_00018_{group}")
            expected = np.zeros(PRIOR_COUNT, dtype=np.float64)
            expected[column] = evaluated[released] / means[column]
            np.testing.assert_allclose(sensitivity[row], expected, rtol=1e-12, atol=0.0)

    def test_dongwi_drops_the_20_54_mev_point(self) -> None:
        self.assertEqual(self.dongwi.released_indices, tuple(range(DONGWI_KEPT)))
        self.assertEqual(self.dongwi.dropped_indices, (DONGWI_POINT_COUNT - 1,))

    def test_dongwi_variant_with_two_hot_row_is_rejected(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["sensitivities"]["values"][0] = [1.0, 1.0] + [0.0] * (
                SHAPE_SENSITIVITY_COLUMNS - 2
            )

        with tempfile.TemporaryDirectory() as directory:
            path = write_variant(Path(directory), DEFAULT_DONGWI_PATH, edit)
            with self.assertRaisesRegex(ValueError, "one-hot"):
                _ = load_shape(path, "Dongwi", DONGWI_RESPONSE_PREFIX, DONGWI_POINT_COUNT)

    def test_missing_dongwi_file_fails_loudly(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            _ = load_shape(
                Path(directory) / "absent.json",
                "Dongwi",
                DONGWI_RESPONSE_PREFIX,
                DONGWI_POINT_COUNT,
            )

    def test_marini_pfns_drops_the_27_88_mev_block(self) -> None:
        self.assertEqual(
            self.marini_pfns.dropped_indices, tuple(range(MARINI_PFNS_KEPT, MARINI_PFNS_RELEASED))
        )
        self.assertEqual(self.marini_pfns.released_indices, tuple(range(MARINI_PFNS_KEPT)))
        self.assertEqual(self.keegan_pfns.dropped_indices, ())

    def test_marini_nubar_still_passes_all_points(self) -> None:
        points = load_marini_nubar(DEFAULT_MARINI_PATH)
        self.assertEqual(points.released_indices, tuple(range(MARINI_COUNT)))
        self.assertEqual(points.dropped_indices, ())
        self.assertEqual(points.sensitivity.shape, (MARINI_COUNT, MARINI_GROUP_COUNT))

    def test_pfns_selection_variant_with_non_one_hot_row_is_rejected(self) -> None:
        def edit(document: dict[str, Any]) -> None:
            document["sensitivities"]["values"][0] = [
                [0.5] + [0.0] * (PFNS_OUTGOING_GROUP_COUNT - 1)
            ] + [[0.0] * PFNS_OUTGOING_GROUP_COUNT] * (PFNS_INCIDENT_BIN_COUNT - 1)

        with tempfile.TemporaryDirectory() as directory:
            path = write_variant(Path(directory), MARINI_PFNS_SOURCE, edit)
            with self.assertRaisesRegex(ValueError, "one-hot"):
                _ = load_pfns(path, MARINI_PFNS_PREFIX)

    def test_missing_pfns_file_fails_loudly(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            self.assertRaises(FileNotFoundError),
        ):
            _ = load_pfns(Path(directory) / "absent.json", MARINI_PFNS_PREFIX)


if __name__ == "__main__":
    unittest.main()
