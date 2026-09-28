"""Build the Exercise 1 prior directly from the released SG52 text files.

Missing covariance blocks in the SG52 release are defined to be zero. The
resulting covariance therefore starts as a zero matrix and is populated from
all released blocks whose two quantity IDs belong to the Exercise 1 state.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Literal, TypeAlias, cast

import h5py
import numpy as np
from numpy.typing import NDArray

FloatArray: TypeAlias = NDArray[np.float64]
QuantityKey: TypeAlias = tuple[int, int]

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

REPOSITORY_ROOT: Final = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE_DIRECTORY: Final = (
    REPOSITORY_ROOT.parent / "SG52_materials_release_2" / "Covariances" / "plaintext"
)
DEFAULT_OUTPUT_PATH: Final = REPOSITORY_ROOT / "Exercise_1" / "ex1_prior.hdf5"


@dataclass(frozen=True)
class QuantityLayout:
    """Location and labels for one SG52 quantity in the flattened prior."""

    key: QuantityKey
    state_slice: slice
    indices: tuple[str, ...]

    @property
    def size(self) -> int:
        """Return the number of state values represented by the quantity."""
        return len(self.indices)


def quantity_size(quantity_id: int) -> int:
    """Return the flattened size of an Exercise 1 quantity."""
    return 1 if quantity_id in MUBAR_QUANTITY_IDS else ENERGY_GROUP_COUNT


def build_layout() -> tuple[QuantityLayout, ...]:
    """Build the canonical 979-state Exercise 1 ordering."""
    layouts: list[QuantityLayout] = []
    offset = 0

    for quantity_id in QUANTITY_IDS:
        size = quantity_size(quantity_id)
        quantity = f"{quantity_id:05d}"
        indices = (
            (f"{ZAID}_{quantity}",)
            if size == 1
            else tuple(
                f"{ZAID}_{quantity}_{energy_group}"
                for energy_group in range(ENERGY_GROUP_COUNT)
            )
        )
        layouts.append(
            QuantityLayout(
                key=(ZAID, quantity_id),
                state_slice=slice(offset, offset + size),
                indices=indices,
            )
        )
        offset += size

    return tuple(layouts)


def load_text_array(path: Path, *, dimensions: Literal[1, 2]) -> FloatArray:
    """Load one finite float64 vector or matrix from a released text file."""
    if not path.is_file():
        raise FileNotFoundError(f"Required SG52 source file not found: {path}")

    values = np.asarray(
        np.loadtxt(path, dtype=np.float64, ndmin=dimensions),
        dtype=np.float64,
    )
    if values.ndim != dimensions:
        raise ValueError(
            f"{path.name}: expected {dimensions} dimensions, got {values.ndim}"
        )
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path.name}: contains non-finite values")
    return values


def validate_source_inventory(source_directory: Path) -> None:
    """Validate the release index files used to identify the prior data."""
    zaids = load_text_array(source_directory / "zaid.txt", dimensions=1)
    if not np.array_equal(zaids, np.asarray([ZAID], dtype=np.float64)):
        raise ValueError(
            f"zaid.txt: expected the sole ZAID {ZAID}, got {zaids.tolist()}"
        )

    available_quantities = load_text_array(
        source_directory / f"{ZAID}-mt.txt",
        dimensions=1,
    )
    missing = [
        quantity_id
        for quantity_id in QUANTITY_IDS
        if quantity_id not in available_quantities
    ]
    if missing:
        raise ValueError(f"{ZAID}-mt.txt: missing required quantity IDs {missing}")


def load_mean(
    source_directory: Path,
    layouts: tuple[QuantityLayout, ...],
) -> FloatArray:
    """Load and flatten all selected mean-value files in canonical order."""
    mean = np.empty(sum(layout.size for layout in layouts), dtype=np.float64)

    for layout in layouts:
        zaid, quantity_id = layout.key
        path = source_directory / f"{zaid}-{quantity_id:05d}-xs.txt"
        values = load_text_array(path, dimensions=1)
        if values.shape != (layout.size,):
            raise ValueError(
                f"{path.name}: expected shape {(layout.size,)}, got {values.shape}"
            )
        mean[layout.state_slice] = values

    return mean


def parse_covariance_filename(path: Path) -> tuple[QuantityKey, QuantityKey]:
    """Parse one SG52 relative-covariance filename."""
    parts = path.stem.split("-")
    if len(parts) != 5 or parts[-1] != "relcov":
        raise ValueError(f"Unexpected covariance filename: {path.name}")

    try:
        row_key = (int(parts[0]), int(parts[1]))
        column_key = (int(parts[2]), int(parts[3]))
    except ValueError as exc:
        raise ValueError(f"Invalid covariance filename: {path.name}") from exc

    return row_key, column_key


def load_covariance(
    source_directory: Path,
    layouts: tuple[QuantityLayout, ...],
) -> FloatArray:
    """Assemble released relative covariance blocks in canonical order."""
    state_count = sum(layout.size for layout in layouts)
    covariance = np.zeros((state_count, state_count), dtype=np.float64)
    layout_by_key = {layout.key: layout for layout in layouts}
    loaded_blocks: set[tuple[QuantityKey, QuantityKey]] = set()
    covariance_paths = sorted(source_directory.glob("*-relcov.txt"))

    if not covariance_paths:
        raise FileNotFoundError(f"No SG52 covariance files found in {source_directory}")

    for path in covariance_paths:
        row_key, column_key = parse_covariance_filename(path)
        if row_key not in layout_by_key or column_key not in layout_by_key:
            continue

        block_key = (row_key, column_key)
        if block_key in loaded_blocks:
            raise ValueError(f"Duplicate covariance block: {path.name}")

        row_layout = layout_by_key[row_key]
        column_layout = layout_by_key[column_key]
        values = load_text_array(path, dimensions=2)
        expected_shape = (row_layout.size, column_layout.size)
        if values.shape != expected_shape:
            raise ValueError(
                f"{path.name}: expected shape {expected_shape}, got {values.shape}"
            )

        covariance[row_layout.state_slice, column_layout.state_slice] = values
        loaded_blocks.add(block_key)

    if not np.allclose(covariance, covariance.T, rtol=1.0e-12, atol=1.0e-15):
        raise ValueError("Assembled covariance matrix is not symmetric")

    return covariance


def write_string_dataset(
    group: h5py.Group,
    name: str,
    indices: tuple[str, ...],
) -> None:
    """Write one UTF-8 string index dataset."""
    _ = group.create_dataset(
        name,
        data=np.asarray(indices, dtype=object),
        dtype=h5py.string_dtype(encoding="utf-8"),
    )


def write_prior(
    output_path: Path,
    indices: tuple[str, ...],
    mean: FloatArray,
    covariance: FloatArray,
) -> None:
    """Write the prior using only the requested groups and datasets."""
    state_count = len(indices)
    if mean.shape != (state_count,):
        raise ValueError(
            f"Mean shape {mean.shape} does not match {state_count} indices"
        )
    if covariance.shape != (state_count, state_count):
        message = (
            f"Covariance shape {covariance.shape} does not match {state_count} indices"
        )
        raise ValueError(message)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary_path.unlink(missing_ok=True)

    try:
        with h5py.File(str(temporary_path), "w") as h5:
            mean_group = h5.create_group("mean")
            write_string_dataset(mean_group, "row_indices", indices)
            _ = mean_group.create_dataset("values", data=mean, dtype=np.float64)

            covariance_group = h5.create_group("cov")
            write_string_dataset(covariance_group, "row_indices", indices)
            write_string_dataset(covariance_group, "col_indices", indices)
            _ = covariance_group.create_dataset(
                "values",
                data=covariance,
                dtype=np.float64,
            )

        _ = temporary_path.replace(output_path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def parse_arguments() -> tuple[Path, Path]:
    """Parse optional source and output path overrides."""
    parser = argparse.ArgumentParser(description=__doc__)
    _ = parser.add_argument(
        "--source-directory",
        type=Path,
        default=DEFAULT_SOURCE_DIRECTORY,
        help=f"SG52 covariance plaintext directory (default: {DEFAULT_SOURCE_DIRECTORY})",
    )
    _ = parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f"output HDF5 file (default: {DEFAULT_OUTPUT_PATH})",
    )
    arguments = parser.parse_args()
    return cast(Path, arguments.source_directory), cast(Path, arguments.output)


def main() -> None:
    """Build and write the Exercise 1 prior."""
    source_argument, output_argument = parse_arguments()
    source_directory = source_argument.resolve()
    output_path = output_argument.resolve()

    validate_source_inventory(source_directory)
    layouts = build_layout()
    indices = tuple(index for layout in layouts for index in layout.indices)
    mean = load_mean(source_directory, layouts)
    covariance = load_covariance(source_directory, layouts)
    write_prior(output_path, indices, mean, covariance)

    print(f"Wrote: {output_path}")
    print(f"States: {len(indices)}")
    print(f"Mean shape: {mean.shape}")
    print(f"Covariance shape: {covariance.shape}")


if __name__ == "__main__":
    main()
