"""Exercise 3 release-order, uncertainty, and sensitivity regression."""

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from ex3_observations import DEFAULT_SOURCE_DIRECTORY, parameter_to_prior_index


class Exercise3ObservationTest(unittest.TestCase):
    def test_all_released_responses_and_published_uncertainties(self) -> None:
        source = DEFAULT_SOURCE_DIRECTORY
        observation_rows = []
        sensitivity_rows = []
        parameter_header = None
        for family in ("JEZEBEL", "EUCLID"):
            with (source / family / f"{family}_obs.csv").open(newline="", encoding="utf-8") as file:
                rows = list(csv.reader(file))
                observation_rows.extend(rows[1:])
            with (source / family / f"{family}_sens_rel.csv").open(newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                header = next(reader)
                if parameter_header is None:
                    parameter_header = header
                else:
                    self.assertEqual(header, parameter_header)
                sensitivity_rows.extend(reader)

        assert parameter_header is not None
        ids = [row[0] for row in observation_rows]
        self.assertEqual(len(ids), 29)
        self.assertEqual(len(set(ids)), 29)
        self.assertEqual(ids[0], "PU-MET-FAST-001-001-s")
        self.assertEqual(ids[3], "PU-MET-FAST-001-001_Pu239/U235")
        self.assertEqual(ids[4:6], ["euclid-3x2-crit", "euclid-8x1-crit"])
        self.assertTrue(all(name.startswith("euclid_NLS_") for name in ids[6:21]))
        self.assertTrue(all(name.startswith("euclid_rrr_") for name in ids[21:]))
        self.assertEqual([row[0] for row in sensitivity_rows], ids)

        parameters = parameter_header[1:]
        pu_positions = [i for i, name in enumerate(parameters) if name.startswith("Pu239_")]
        mapped = [parameter_to_prior_index(parameters[i]) for i in pu_positions]
        self.assertEqual(len(set(mapped)), len(mapped))
        # Unobserved prior coordinates must remain zero in the absolute sensitivity.
        indices = mapped + [f"unused_{i}" for i in range(979 - len(mapped))]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prior_path = root / "prior.hdf5"
            output_path = root / "observations.hdf5"
            with h5py.File(prior_path, "w") as prior:
                mean = prior.create_group("mean")
                mean.create_dataset("row_indices", data=indices, dtype=h5py.string_dtype())
                mean.create_dataset("values", data=np.full(979, 2.0))
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("ex3_observations.py")),
                    "--source-directory", str(source),
                    "--prior", str(prior_path),
                    "--output", str(output_path),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("WARNING: 15 released total_uncert", result.stdout)
            self.assertIn("Sensitivity shape: (29, 979)", result.stdout)

            numeric = np.array([[float(cell) for cell in row[1:]] for row in observation_rows])
            published_total = numeric[:, 4]
            component_total = np.hypot(numeric[:, 1], numeric[:, 3])
            discrepancies = ~np.isclose(published_total, component_total, rtol=1e-6, atol=1e-12)
            self.assertEqual(np.flatnonzero(discrepancies).tolist(), list(range(6, 21)))
            with h5py.File(output_path, "r") as output:
                self.assertEqual(output["responses/row_indices"].asstr()[:].tolist(), ids)
                self.assertEqual(output["sens/col_indices"].asstr()[:].tolist(), indices)
                np.testing.assert_allclose(output["delta/values"][:], numeric[:, 0] - numeric[:, 2])
                np.testing.assert_allclose(output["responses/experimental"][:], numeric[:, 0])
                np.testing.assert_allclose(output["responses/simulated"][:], numeric[:, 2])
                np.testing.assert_allclose(output["responses/experimental_uncertainty"][:], numeric[:, 1])
                np.testing.assert_allclose(output["responses/simulated_uncertainty"][:], numeric[:, 3])
                np.testing.assert_allclose(output["responses/total_uncertainty"][:], published_total)
                np.testing.assert_allclose(
                    output["responses/total_to_component_uncertainty_ratio"][:],
                    published_total / component_total,
                )
                np.testing.assert_allclose(output["cov/values"][:], np.diag(published_total**2))
                self.assertEqual(output["sens/values"].shape, (29, 979))
                relative = np.array([[float(cell) for cell in row[1:]] for row in sensitivity_rows])
                np.testing.assert_allclose(
                    output["sens/values"][:, :len(mapped)],
                    numeric[:, 2, None] * relative[:, pu_positions] / 2.0,
                )
                np.testing.assert_array_equal(output["sens/values"][:, len(mapped):], 0)


if __name__ == "__main__":
    unittest.main()
