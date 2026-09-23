from pathlib import Path
from typing import Literal, TypedDict, TypeAlias
import numpy as np
from numpy.typing import NDArray
import h5py
from endf_mf_mt import MT_NUMBERS
from pseudo_pfns_mubar_id import PFNS_PSEUDO_IDS, MUBAR_PSEUDO_IDS

# Constants
N_ENERGY_GROUPS = 51
N_PFNS_GROUPS = len(PFNS_PSEUDO_IDS)
N_MUBAR_GROUPS = len(MUBAR_PSEUDO_IDS)

# Type aliases
FloatArray: TypeAlias = NDArray[np.float64]
IntArray: TypeAlias = NDArray[np.int64]

MeanData: TypeAlias = dict[
    tuple[int, int],
    FloatArray,
]

CovarianceKey: TypeAlias = tuple[
    tuple[int, int],
    tuple[int, int],
]

RelativeCovarianceData: TypeAlias = dict[
    CovarianceKey,
    FloatArray,
]


class MeanFileInfo(TypedDict):
    kind: Literal["mean"]
    zaid: int
    quantity_id: int
    path: Path


class CovarianceFileInfo(TypedDict):
    kind: Literal["relative_covariance"]
    zaid_1: int
    quantity_id_1: int
    zaid_2: int
    quantity_id_2: int
    path: Path


FileInfo = MeanFileInfo | CovarianceFileInfo


def parse_filename(path: Path) -> FileInfo | None:
    parts = path.stem.split("-")

    if len(parts) == 3 and parts[-1] == "xs":
        return {
            "kind": "mean",
            "zaid": int(parts[0]),
            "quantity_id": int(parts[1]),
            "path": path,
        }

    if len(parts) == 5 and parts[-1] == "relcov":
        return {
            "kind": "relative_covariance",
            "zaid_1": int(parts[0]),
            "quantity_id_1": int(parts[1]),
            "zaid_2": int(parts[2]),
            "quantity_id_2": int(parts[3]),
            "path": path,
        }

    return None


def interpret_quantity_id(zaid: int, qid: int) -> dict[str, object]:
    """Return the physical meaning attached to an SG52 quantity ID."""

    if qid in PFNS_PSEUDO_IDS:
        return {
            "family": "pfns",
            "zaid": zaid,
            "mtid": f"{qid:05d}",
            **PFNS_PSEUDO_IDS[qid],
        }

    if qid in MUBAR_PSEUDO_IDS:
        return {
            "family": "mubar",
            "zaid": zaid,
            "mtid": f"{qid:05d}",
            **MUBAR_PSEUDO_IDS[qid],
        }

    if qid in MT_NUMBERS:
        return {
            "family": "ordinary_MT",
            "zaid": zaid,
            "mtid": f"{qid:05d}",
            **MT_NUMBERS[qid],
        }

    return {
        "family": "unknown",
        "zaid": zaid,
        "mtid": f"{qid:05d}",
    }


def quantity_dimension(qid: int) -> int:
    """Return the number of values represented by one SG52 quantity ID.

    Ordinary MT quantities:
        51 values over incident-neutron energy groups.

    PFNS pseudo-IDs:
        51 values over outgoing-neutron energy groups for one fixed
        incident-neutron energy group.

    Mubar pseudo-IDs:
        1 scalar value for one fixed incident-neutron energy group.
    """

    if qid in MUBAR_PSEUDO_IDS:
        return 1

    return N_ENERGY_GROUPS


def read_data_file(info: FileInfo) -> FloatArray:
    data = np.asarray(np.loadtxt(info["path"], dtype=float))

    if info["kind"] == "mean":
        expected_size = quantity_dimension(info["quantity_id"])

        if data.size != expected_size:
            raise ValueError(
                f"{info['path'].name}: "
                f"expected {expected_size} values, got {data.size}"
            )

        # Always store mean data as a 1-D array.
        return data.reshape(expected_size)

    expected_shape = (
        quantity_dimension(info["quantity_id_1"]),
        quantity_dimension(info["quantity_id_2"]),
    )
    expected_size = expected_shape[0] * expected_shape[1]

    if data.size != expected_size:
        raise ValueError(
            f"{info['path'].name}: "
            f"expected shape {expected_shape} "
            f"({expected_size} values), got {data.shape} "
            f"({data.size} values)"
        )

    # This also turns a scalar mubar-mubar covariance into shape (1, 1).
    return data.reshape(expected_shape)


def write_metadata(
    h5: h5py.File,
    h5_material_ids: IntArray,
    h5_energy_bounds: FloatArray,
) -> None:
    # General file metadata
    h5.attrs["schema_version"] = "0.1"
    h5.attrs["source"] = "WPEC SG52"

    # ------------------------------------------------------------------
    # Common 51-group energy structure
    # ------------------------------------------------------------------
    energy_group = h5.create_group("energy_groups")

    energy_group.create_dataset(
        "bounds_eV",
        data=h5_energy_bounds,
    )

    # ------------------------------------------------------------------
    # PFNS incident-energy groups
    # ------------------------------------------------------------------
    pfns_group = h5.create_group("pfns_groups")

    pfns_entries = sorted(
        PFNS_PSEUDO_IDS.items(),
        key=lambda item: int(item[1]["incident_group"]),
    )

    pfns_ids = np.asarray(
        [qid for qid, _ in pfns_entries],
        dtype=np.int64,
    )

    pfns_lower_bounds = np.asarray(
        [
            float(metadata["incident_energy_lower_mev"])
            for _, metadata in pfns_entries
        ],
        dtype=np.float64,
    )

    pfns_upper_bounds = np.asarray(
        [
            float(metadata["incident_energy_upper_mev"])
            for _, metadata in pfns_entries
        ],
        dtype=np.float64,
    )

    pfns_group.create_dataset(
        "pseudo_ids",
        data=pfns_ids,
    )

    pfns_group.create_dataset(
        "lower_bounds_MeV",
        data=pfns_lower_bounds,
    )

    pfns_group.create_dataset(
        "upper_bounds_MeV",
        data=pfns_upper_bounds,
    )

    # ------------------------------------------------------------------
    # Mubar incident-energy groups
    # ------------------------------------------------------------------
    mubar_group = h5.create_group("mubar_groups")

    mubar_entries = sorted(
        MUBAR_PSEUDO_IDS.items(),
        key=lambda item: int(item[1]["incident_group"]),
    )

    mubar_ids = np.asarray(
        [qid for qid, _ in mubar_entries],
        dtype=np.int64,
    )

    mubar_lower_bounds = np.asarray(
        [
            float(metadata["incident_energy_lower_mev"])
            for _, metadata in mubar_entries
        ],
        dtype=np.float64,
    )

    mubar_upper_bounds = np.asarray(
        [
            float(metadata["incident_energy_upper_mev"])
            for _, metadata in mubar_entries
        ],
        dtype=np.float64,
    )

    mubar_group.create_dataset(
        "pseudo_ids",
        data=mubar_ids,
    )

    mubar_group.create_dataset(
        "lower_bounds_MeV",
        data=mubar_lower_bounds,
    )

    mubar_group.create_dataset(
        "upper_bounds_MeV",
        data=mubar_upper_bounds,
    )

    # ------------------------------------------------------------------
    # Materials
    # ------------------------------------------------------------------
    materials_group = h5.create_group("materials")

    materials_group.create_dataset(
        "zaids",
        data=h5_material_ids,
    )


def write_mean_values(
    h5: h5py.File,
    h5_mean_data: MeanData,
) -> None:
    mean_group = h5.create_group("mean_values")

    for (zaid, quantity_id), values in h5_mean_data.items():
        material_group = mean_group.require_group(
            str(zaid)
        )

        quantity_group = material_group.create_group(
            f"{zaid}_{quantity_id:05d}"
        )

        quantity_group.create_dataset(
            "values",
            data=values,
        )

        metadata = interpret_quantity_id(zaid, quantity_id)

        for h5_key, h5_value in metadata.items():
            if h5_value is not None:
                quantity_group.attrs[h5_key] = h5_value


def write_relative_covariances(
    h5: h5py.File,
    h5_relative_covariance_data: RelativeCovarianceData,
) -> None:
    covariance_group = h5.create_group(
        "relative_covariances"
    )

    for h5_key, h5_values in h5_relative_covariance_data.items():
        (zaid_1, quantity_id_1), (
            zaid_2,
            quantity_id_2,
        ) = h5_key

        material_group = covariance_group.require_group(
            str(zaid_1)
        )

        block_name = (
            f"{zaid_1}_{quantity_id_1:05d}"
            f"_vs_"
            f"{zaid_2}_{quantity_id_2:05d}"
        )

        block_group = material_group.create_group(
            block_name
        )

        block_group.create_dataset(
            "values",
            data=h5_values,
        )

        block_group.attrs["zaid_1"] = str(zaid_1)
        block_group.attrs["quantity_id_1"] = f"{quantity_id_1:05d}"
        block_group.attrs["zaid_2"] = str(zaid_2)
        block_group.attrs["quantity_id_2"] = f"{quantity_id_2:05d}"

        if quantity_id_1 in PFNS_PSEUDO_IDS and quantity_id_2 in PFNS_PSEUDO_IDS:
            block_group.attrs["family"] = 'pfns'
        elif quantity_id_1 in MUBAR_PSEUDO_IDS and quantity_id_2 in MUBAR_PSEUDO_IDS:
            block_group.attrs["family"] = 'mubar'
        elif quantity_id_1 in MT_NUMBERS and quantity_id_2 in MT_NUMBERS:
            block_group.attrs["family"] = 'ordinary_MT'
        else:
            block_group.attrs["family"] = 'unknown'


def write_hdf5(
    output_path: Path,
    h5_material_ids: IntArray,
    h5_energy_bounds: FloatArray,
    h5_mean_data: MeanData,
    h5_relative_covariance_data: RelativeCovarianceData,
) -> None:
    with h5py.File(str(output_path), "w") as h5:
        write_metadata(
            h5,
            h5_material_ids,
            h5_energy_bounds,
        )

        write_mean_values(
            h5,
            h5_mean_data,
        )

        write_relative_covariances(
            h5,
            h5_relative_covariance_data,
        )

# Covariance data path
prior_directory = Path(
    "/home/aurja/Programming/OECDNEA_WPEC_SG52/"
    "Auroras_solution/Exercise_1/Prior/"
)

covariance_directory = prior_directory / "Covariances/plaintext/"

ENERGY_GROUP_FILE = covariance_directory / "gs.txt"
energy_bounds = np.asarray(np.loadtxt(ENERGY_GROUP_FILE, dtype=float))

if energy_bounds.size != N_ENERGY_GROUPS + 1:
    raise ValueError(
        f"{ENERGY_GROUP_FILE.name}: "
        f"expected {N_ENERGY_GROUPS + 1} energy boundaries, "
        f"got {energy_bounds.size}"
    )

if N_PFNS_GROUPS != 10:
    raise ValueError(f"Expected 10 PFNS pseudo-IDs, got {N_PFNS_GROUPS}")

if N_MUBAR_GROUPS != 10:
    raise ValueError(f"Expected 10 mubar pseudo-IDs, got {N_MUBAR_GROUPS}")

# Material IDs
MATERIAL_ID_FILE = covariance_directory / "zaid.txt"
material_ids = np.atleast_1d(
    np.loadtxt(MATERIAL_ID_FILE, dtype=int)
)

# Ingest files
mean_data: MeanData = {}

relative_covariance_data: RelativeCovarianceData = {}

for file_path in covariance_directory.glob("*.txt"):
    file_info = parse_filename(file_path)

    if file_info is None:
        continue

    file_data = read_data_file(file_info)

    if file_info["kind"] == "mean":
        key = (
            file_info["zaid"],
            file_info["quantity_id"],
        )
        mean_data[key] = file_data

    elif file_info["kind"] == "relative_covariance":
        key = (
            (file_info["zaid_1"], file_info["quantity_id_1"]),
            (file_info["zaid_2"], file_info["quantity_id_2"]),
        )
        relative_covariance_data[key] = file_data

OUTPUT_FILE = prior_directory / "ex1_prior.hdf5"

write_hdf5(
    OUTPUT_FILE,
    material_ids,
    energy_bounds,
    mean_data,
    relative_covariance_data,
)
