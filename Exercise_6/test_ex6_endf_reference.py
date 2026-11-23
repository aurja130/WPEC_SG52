"""Synthetic checks for the ENDF/B reference parsers, slice averaging and gate."""

import unittest

import h5py
import numpy as np
from ex6_endf_reference import (
    EXPECTED_UNREPRODUCED,
    OUTPUT_PATH,
    PFNS_QUANTITY_IDS,
    QUANTITY_IDS,
    enforce_gate,
    errorr_mf3,
    errorr_mf5,
    fnum,
    gendf_mf3,
    is_reproduced,
    slice_average,
)


def endf_line(data: str, mf: int, mt: int) -> str:
    """Build one 80-column ENDF record with the given data in columns 1-66."""
    return f"{data:<66}{1:4d}{mf:2d}{mt:3d}{1:5d}"


def cont_fields(nw: int, ig: int) -> str:
    """Return the 66-column data of a GENDF CONT record."""
    return f"{0:11d}{0:11d}{0:11d}{0:11d}{nw:11d}{ig:11d}"


def value_fields(values: list[str]) -> str:
    """Return up to six right-justified 11-column ENDF fields."""
    return "".join(f"{value:>11}" for value in values)


class EndfFieldTest(unittest.TestCase):
    def test_fnum_parses_exponent_forms_and_plain_floats(self) -> None:
        self.assertAlmostEqual(fnum(" 3.818431+3") or 0.0, 3818.431)
        self.assertAlmostEqual(fnum("-1.2-10") or 0.0, -1.2e-10)
        self.assertAlmostEqual(fnum("0.86287049") or 0.0, 0.86287049)
        self.assertIsNone(fnum("           "))


class GendfMf3Test(unittest.TestCase):
    def test_selects_legendre0_first_sigma_zero_for_each_group(self) -> None:
        head = endf_line(f"{0:22}{1:11d}{1:11d}", 3, 102)
        lines = [
            head,
            endf_line(cont_fields(2, 1), 3, 102),
            endf_line(value_fields(["1.5+0", "2.5-1"]), 3, 102),
            endf_line(cont_fields(2, 2), 3, 102),
            endf_line(value_fields(["0.86287049", "-1.2-10"]), 3, 102),
        ]
        vals = gendf_mf3(lines, ng=2)
        np.testing.assert_allclose(vals, [0.25, -1.2e-10])


class ErrorrParserTest(unittest.TestCase):
    def test_errorr_mf3_reads_values_after_head(self) -> None:
        lines = [
            endf_line(" " * 66, 3, 251),
            endf_line(value_fields(["-1.2-10", "0.86287049", "3.818431+3"]), 3, 251),
        ]
        np.testing.assert_allclose(errorr_mf3(lines), [-1.2e-10, 0.86287049, 3818.431])

    def test_errorr_mf5_reads_efmean_and_chi(self) -> None:
        head = endf_line(" " * 11 + " 1.667+7" + " " * 44, 5, 18)
        lines = [
            head,
            endf_line(value_fields(["0.5", "-2.5-3", "1.0+0"]), 5, 18),
        ]
        efmean, chi = errorr_mf5(lines)
        self.assertAlmostEqual(efmean, 1.667e7)
        np.testing.assert_allclose(chi, [0.5, -2.5e-3, 1.0])


class SliceAverageTest(unittest.TestCase):
    def test_single_spectrum_in_slice_is_used_directly(self) -> None:
        efmeans = np.array([1.0e6, 2.0e7])
        chis = np.array([[0.1, 0.9], [0.4, 0.6]])
        np.testing.assert_allclose(
            slice_average(efmeans, chis, 9.0e5, 1.1e6), [0.1, 0.9]
        )

    def test_trapezoid_average_with_unequal_spacing(self) -> None:
        efmeans = np.array([1.0, 2.0, 4.0])
        chis = np.array([[1.0, 0.0], [3.0, 2.0], [5.0, 4.0]])
        # Trapezoid weights for the hat functions are (0.5, 1.5, 1.0), total 3.
        expected = np.array([10.0 / 3.0, 7.0 / 3.0])
        np.testing.assert_allclose(slice_average(efmeans, chis, 1.0, 4.0), expected)

    def test_bounds_are_included_and_outside_points_excluded(self) -> None:
        efmeans = np.array([1.0, 2.0, 4.0])
        chis = np.array([[1.0, 0.0], [3.0, 2.0], [5.0, 4.0]])
        np.testing.assert_allclose(slice_average(efmeans, chis, 2.0, 4.0), [4.0, 3.0])

    def test_empty_slice_raises(self) -> None:
        with self.assertRaises(ValueError):
            _ = slice_average(np.array([1.0]), np.array([[1.0]]), 2.0, 3.0)


class ReproductionGateTest(unittest.TestCase):
    def test_gate_flags_error_above_tolerance_and_passes_below(self) -> None:
        self.assertFalse(is_reproduced(2.0e-6))
        self.assertTrue(is_reproduced(5.0e-7))

    def test_regression_outside_expected_set_raises(self) -> None:
        with self.assertRaises(ValueError):
            _ = enforce_gate({"00018": 2.0e-6})

    def test_expected_unreproduced_quantity_is_reported_without_raising(self) -> None:
        flags = enforce_gate({EXPECTED_UNREPRODUCED[0]: 2.0e-6, "00018": 5.0e-7})
        self.assertEqual(flags, {EXPECTED_UNREPRODUCED[0]: False, "00018": True})


class OutputFileTest(unittest.TestCase):
    def test_output_shapes_and_reproduction_flags(self) -> None:
        if not OUTPUT_PATH.is_file():
            self.skipTest(
                f"{OUTPUT_PATH.name} is generated output; run the script first"
            )
        qid_count = len(QUANTITY_IDS)
        self.assertEqual(qid_count, 29)
        self.assertEqual(len(PFNS_QUANTITY_IDS), 10)
        with h5py.File(OUTPUT_PATH, "r") as h5:
            state_count = h5["row_indices"].shape[0]
            self.assertEqual(state_count, 979)
            self.assertEqual(h5["viii0/values"].shape, (state_count,))
            self.assertEqual(h5["viii1/values"].shape, (state_count,))
            self.assertEqual(h5["qid/ids"].shape, (qid_count,))
            self.assertEqual(h5["qid/reproduction_error"].shape, (qid_count,))
            self.assertEqual(h5["state/reproduced"].shape, (state_count,))
            ids = [value.decode("utf-8") for value in h5["qid/ids"][:]]
            reproduced = dict(zip(ids, h5["qid/reproduced"][:], strict=True))
        for qid, flag in reproduced.items():
            if qid not in EXPECTED_UNREPRODUCED:
                self.assertTrue(flag, f"QID {qid} is not reproduced")


if __name__ == "__main__":
    _ = unittest.main()
