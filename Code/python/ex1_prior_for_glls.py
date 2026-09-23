from pathlib import Path
import h5py
import numpy as np
from numpy.typing import NDArray

class PriorCovariance:
    def __init__(self, zaid_1: str, qid_1: str, 
                zaid_2: str, qid_2: str, family: str,
                covariance_matrix: NDArray[np.float64], 
                energy_groups: NDArray[np.float64]):

        self.zaid_1 = zaid_1
        self.qid_1 = qid_1
        self.zaid_2 = zaid_2
        self.qid_2 = qid_2
        self.family = family
        self.energy_groups = energy_groups
        self.covariance_matrix = covariance_matrix
        if self.family == "mubar":
            self.row_indices, self.col_indices = self.form_mubar_indices()
        else:
            self.row_indices, self.col_indices = self.form_mt_pfns_indices()

    def form_mt_pfns_indices(self):
        row_indices = []
        col_indices = []
        for g in self.energy_groups:
            row_indices.append(f'{self.zaid_1}_{self.qid_1}_{g}')
            col_indices.append(f'{self.zaid_2}_{self.qid_2}_{g}')
        return row_indices, col_indices

    def form_mubar_indices(self):
        row_indices = [f'{self.zaid_1}_{self.qid_1}']
        col_indices = [f'{self.zaid_2}_{self.qid_2}']
        return row_indices, col_indices


class PriorMean:
    def __init__(self, zaid: str, qid: str, family: str,
                mean_values: NDArray[np.float64],
                energy_groups: NDArray[np.float64]):
        self.zaid = zaid
        self.qid = qid
        self.family = family
        self.energy_groups = energy_groups
        self.mean_values = mean_values

        if self.family == "mubar":
            self.row_indices = self.form_mubar_indices()
        else:
            self.row_indices = self.form_mt_pfns_indices()

    def form_mt_pfns_indices(self):
        indices = []
        for g in self.energy_groups:
            indices.append(f'{self.zaid}_{self.qid}_{g}')
        return indices

    def form_mubar_indices(self):
        indices = [f'{self.zaid}_{self.qid}']
        return indices


FloatArray = NDArray[np.float64]

PRIOR_PATH = Path("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Prior/ex1_prior.hdf5")


prior_file = h5py.File(str(PRIOR_PATH), "r")

# MT's or other pseudo IDs
prior_mts = ['00002', '00004', '00016', '00017', '00018', '00037', '00102', '00452', '00456']
prior_pfns_ids = ['01018', '01118', '01218', '01318', '01418', '01518', '01618', '01718', '01818', '01918']
prior_mubar_ids = ['00251', '01251', '02251', '03251', '04251', '05251', '06251', '07251', '08251', '09251']
prior_qids = prior_mts + prior_pfns_ids + prior_mubar_ids

# Energy group bounds and number of groups
prior_energy_groups = np.arange(51)
prior_pfns_groups = np.arange(10)
prior_mubar_groups = np.arange(10)

# Mean values
mean_values_group = prior_file["mean_values/94239"]

if not isinstance(mean_values_group, h5py.Group):
    raise TypeError("'mean_values/94239' must be an HDF5 group")

prior_means = []

for item in mean_values_group.items():
    item_zaid = item[1].attrs['zaid']
    item_qid = item[1].attrs['mtid']
    if item_qid not in prior_qids:
        continue
    item_family = item[1].attrs['family']
    item_mean_vector = np.asarray(item[1]['values'], dtype=np.float64)
    if item_family == 'mubar':
        item_prior_mean = PriorMean(item_zaid, item_qid, item_family,
                                    item_mean_vector, np.array([0]))
    else:
        item_prior_mean = PriorMean(item_zaid, item_qid, item_family,
                                    item_mean_vector, prior_energy_groups)
    prior_means.append(item_prior_mean)

# Relative covariance matrices
relative_covariances_group = prior_file["relative_covariances/94239"]

if not isinstance(relative_covariances_group, h5py.Group):
    raise TypeError("'relative_covariances/94239' must be an HDF5 group")

prior_covariances = []

for item in relative_covariances_group.items():
    item_zaid_1 = item[1].attrs['zaid_1']
    item_qid_1 = item[1].attrs['quantity_id_1']
    if item_qid_1 not in prior_qids:
        continue
    item_zaid_2 = item[1].attrs['zaid_2']
    item_qid_2 = item[1].attrs['quantity_id_2']
    if item_qid_2 not in prior_qids:
        continue
    item_family = item[1].attrs['family']
    item_covariance_matrix = np.asarray(item[1]['values'], dtype=np.float64)

    if item_family == 'mubar':
        item_prior_covariance = PriorCovariance(item_zaid_1, item_qid_1, 
                                                item_zaid_2, item_qid_2, 
                                                item_family, item_covariance_matrix, 
                                                np.array([0]))
    else:
        item_prior_covariance = PriorCovariance(item_zaid_1, item_qid_1, 
                                                item_zaid_2, item_qid_2, 
                                                item_family, item_covariance_matrix, 
                                                prior_energy_groups)
    
    prior_covariances.append(item_prior_covariance)


# Create the row indices for the mean values, and the row and column indices for the covariance matrices
verbose_indices = []
for mt in prior_mts:
    for energy_group in prior_energy_groups:
        index = f'94239_{mt}_{energy_group}'
        verbose_indices.append(index)

for pfns_id in prior_pfns_ids:
    for energy_group in prior_energy_groups:
        index = f'94239_{pfns_id}_{energy_group}'
        verbose_indices.append(index)

for mubar_id in prior_mubar_ids:
    index = f'94239_{mubar_id}'
    verbose_indices.append(index)

mean_vector = np.zeros((len(verbose_indices),))

for verbose_index in verbose_indices:
    for mean_set in prior_means:
        if verbose_index in mean_set.row_indices:
            mean_vector[verbose_indices.index(verbose_index)] = mean_set.mean_values[mean_set.row_indices.index(verbose_index)]

cov_matrix = np.zeros((len(verbose_indices), len(verbose_indices)))

for cov_set in prior_covariances:
    for row in cov_set.row_indices:
        for col in cov_set.col_indices:
            cov_matrix[
                verbose_indices.index(row),
                verbose_indices.index(col)] = cov_set.covariance_matrix[
                            cov_set.row_indices.index(row),
                            cov_set.col_indices.index(col)]

with h5py.File("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Prior/mean.hdf5", "w") as mean_hdf5:
    mean_dset = mean_hdf5.create_dataset("values", data=mean_vector)

with h5py.File("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Prior/covariance.hdf5", "w") as cov_hdf5:
    cov_dset = cov_hdf5.create_dataset("values", data=cov_matrix)
