"""Check criticality-response selection, ordering, and absolute sensitivities."""

import csv
import tempfile
import unittest
from pathlib import Path

import numpy as np

from ex2_observations import (
    EUCLID_RESPONSE_IDS,
    JEZEBEL_RESPONSE_IDS,
    PriorData,
    build_inputs,
    load_observations,
    load_sensitivities,
)


class Exercise2ObservationTest(unittest.TestCase):
    def test_three_responses_keep_source_order_and_absolute_derivatives(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            observation_header = [
                "", "expt", "expt_uncert", "sim", "sim_uncert", "total_uncert", "bias"
            ]
            parameters = (
                "Pu239_crossSection_elastic_0",
                "Pu239_crossSection_fission_1",
                "U238_crossSection_elastic_0",
            )
            records = {
                "JEZEBEL": (
                    [(JEZEBEL_RESPONSE_IDS[0], 1.0, 0.1, 1.1, 0, 0.1, 1.0)],
                    [(JEZEBEL_RESPONSE_IDS[0], 0.2, -0.4, 100.0)],
                ),
                "EUCLID": (
                    [
                        (EUCLID_RESPONSE_IDS[1], 1.2, 0.3, 1.1, 0, 0.3, -1 / 3),
                        ("unused-leakage", 0, 0, 0, 0, 0, 0),
                        (EUCLID_RESPONSE_IDS[0], 0.9, 0.2, 0.8, 0, 0.2, -0.5),
                    ],
                    [
                        (EUCLID_RESPONSE_IDS[1], -0.5, 0.4, 100.0),
                        ("unused-leakage", "invalid", "invalid", "invalid"),
                        (EUCLID_RESPONSE_IDS[0], 0.1, 0.3, 100.0),
                    ],
                ),
            }
            loaded_observations = []
            loaded_sensitivities = []
            for source_name, (response_rows, sensitivity_rows) in records.items():
                obs_path = root / f"{source_name}_obs.csv"
                sens_path = root / f"{source_name}_sens_rel.csv"
                for path, header, rows in (
                    (obs_path, observation_header, response_rows),
                    (sens_path, ["", *parameters], sensitivity_rows),
                ):
                    with path.open("w", newline="", encoding="utf-8") as handle:
                        writer = csv.writer(handle)
                        writer.writerow(header)
                        writer.writerows(rows)
                required = (
                    JEZEBEL_RESPONSE_IDS if source_name == "JEZEBEL" else EUCLID_RESPONSE_IDS
                )
                loaded_observations.append(
                    load_observations(
                        obs_path, required, signed_bias=source_name == "EUCLID"
                    )
                )
                loaded_sensitivities.append(load_sensitivities(sens_path, required))

            prior = PriorData(
                indices=("94239_00002_0", "94239_00018_1"),
                mean=np.asarray([2.0, 4.0]),
            )
            inputs = build_inputs(
                tuple(loaded_observations), tuple(loaded_sensitivities), prior
            )
            self.assertEqual(
                inputs.response_indices,
                (*JEZEBEL_RESPONSE_IDS, *EUCLID_RESPONSE_IDS),
            )
            np.testing.assert_allclose(inputs.experimental, [1.0, 0.9, 1.2])
            np.testing.assert_allclose(inputs.simulated, [1.1, 0.8, 1.1])
            np.testing.assert_allclose(inputs.delta, [-0.1, 0.1, 0.1])
            np.testing.assert_allclose(inputs.covariance, np.diag([0.01, 0.04, 0.09]))
            np.testing.assert_allclose(
                inputs.sensitivity,
                [[0.11, -0.11], [0.04, 0.06], [-0.275, 0.11]],
            )


if __name__ == "__main__":
    unittest.main()
