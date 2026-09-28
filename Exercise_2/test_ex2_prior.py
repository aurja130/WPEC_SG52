"""Regression check for converting SG52 relative covariance into GLLS units."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from ex2_prior import MUBAR_QUANTITY_IDS, QUANTITY_IDS, ZAID


class PriorCovarianceUnitsTest(unittest.TestCase):
    def test_builder_scales_diagonal_and_cross_blocks_by_prior_means(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "plaintext"
            source.mkdir()
            np.savetxt(source / "zaid.txt", [ZAID], fmt="%d")
            np.savetxt(source / f"{ZAID}-mt.txt", QUANTITY_IDS, fmt="%d")

            for quantity_id in QUANTITY_IDS:
                count = 1 if quantity_id in MUBAR_QUANTITY_IDS else 51
                values = np.ones(count)
                if quantity_id == 2:
                    values[:2] = [2.0, 4.0]
                elif quantity_id == 4:
                    values[0] = -3.0
                np.savetxt(
                    source / f"{ZAID}-{quantity_id:05d}-xs.txt", values, fmt="%.17g"
                )

            diagonal = np.zeros((51, 51))
            diagonal[0, 0] = 0.25
            diagonal[1, 1] = 0.5
            diagonal[0, 1] = diagonal[1, 0] = -0.05
            cross = np.zeros((51, 51))
            cross[0, 0] = 0.1
            np.savetxt(source / f"{ZAID}-00002-{ZAID}-00002-relcov.txt", diagonal)
            np.savetxt(source / f"{ZAID}-00002-{ZAID}-00004-relcov.txt", cross)
            np.savetxt(source / f"{ZAID}-00004-{ZAID}-00002-relcov.txt", cross.T)

            output = root / "prior.hdf5"
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).with_name("ex2_prior.py")),
                    "--source-directory",
                    str(source),
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            with h5py.File(output, "r") as prior:
                mean = prior["mean/values"][:]
                covariance = prior["cov/values"][:]

            np.testing.assert_array_equal(mean[[0, 1, 51]], [2.0, 4.0, -3.0])
            np.testing.assert_allclose(
                covariance[[0, 0, 1, 0, 51, 2], [0, 1, 1, 51, 0, 52]],
                [1.0, -0.4, 8.0, -0.6, -0.6, 0.0],
                atol=1e-14,
            )
            self.assertEqual(covariance.shape, (979, 979))


if __name__ == "__main__":
    unittest.main()
