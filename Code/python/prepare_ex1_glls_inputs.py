from pathlib import Path
import h5py
import numpy as np
from numpy.typing import NDArray


FloatArray = NDArray[np.float64]

PRIOR_PATH = Path("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Prior/exercise_1_prior.hdf5")


prior_file = h5py.File(str(PRIOR_PATH), "r")

prior_energy_groups = np.asarray(prior_file["energy_groups/bounds_eV"], dtype=np.float64)

mean_values_group = prior_file["mean_values/94239"]

if not isinstance(mean_values_group, h5py.Group):
    raise TypeError("'mean_values/94239' must be an HDF5 group")

prior_mts = ['00002', '00004', '00016', '00017', '00018', '00037', '00102', '00452', '00456']
prior_pfns_ids = ['01018', '01118', '01218', '01318', '01418', '01518', '01618', '01718', '01818', '01918']
prior_mubar_ids = ['00251', '01251', '02251', '03251', '04251', '05251', '06251', '07251', '08251', '09251']

prior_mt_mean_values = np.hstack([np.asarray(mean_values_group[f'{mt}/values'], dtype=np.float64) for mt in prior_mts]).reshape(-1, 1)
prior_pfns_mean_values = np.hstack([np.asarray(mean_values_group[f'{id}/values'], dtype=np.float64) for id in prior_pfns_ids]).reshape(-1, 1)
prior_mubar_mean_values = np.hstack([np.asarray(mean_values_group[f'{id}/values'], dtype=np.float64) for id in prior_mubar_ids]).reshape(-1, 1)

print(prior_mt_mean_values.shape)
print(prior_pfns_mean_values.shape)
print(prior_mubar_mean_values.shape)

exit()

prior_mubar_groups = np.asarray(prior_file["mubar_groups"], dtype=np.float64)
prior_pfns_groups = np.asarray(prior_file["pfns_groups"], dtype=np.float64)
prior_relative_covariances = np.asarray(prior_file["relative_covariances"], dtype=np.float64)
