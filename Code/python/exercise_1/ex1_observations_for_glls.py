import h5py
import numpy as np

OBSERVATION_PATH = "/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Observations/ex1_groupwise_observations_data.hdf5"

observation_file = h5py.File(str(OBSERVATION_PATH), "r")

# READ OBS MEAN AND COV DATA
mean_cov_group = observation_file["observations"]
obs_response_ids = mean_cov_group.get("response_ids").asstr()[...].tolist()
CRITICALITY_RESPONSE_ID = "PU-MET-FAST-001-001-s"
desired_obs_response_index = obs_response_ids.index(CRITICALITY_RESPONSE_ID)
obs_experimental = np.asarray(mean_cov_group["experimental"])
obs_simulated = np.asarray(mean_cov_group["simulated"])
obs_total_uncertainty_std = np.asarray(mean_cov_group["total_uncertainty"])

# CREATE OBS MEAN AND COV matrices
Delta_E_i = np.array([
    obs_experimental[desired_obs_response_index]
    - obs_simulated[desired_obs_response_index]
])

Sigma_E = np.array([[
    obs_total_uncertainty_std[desired_obs_response_index] ** 2
]])

# READ SENSITIVITY DATA
sens_group = observation_file["sensitivities"]
sens_response_ids = sens_group.get("response_ids").asstr()[...].tolist()
desired_sens_response_index = sens_response_ids.index(CRITICALITY_RESPONSE_ID)
sens_parameter_ids = sens_group.get("parameter_ids").asstr()[...].tolist()
rel_sens_values = np.asarray(sens_group["relative"])

# MATCH AVAILABLE SENSITIVITY DATA TO PRIOR DATA
raw_we_want = []

for parameter_id in sens_parameter_ids:
    if parameter_id.startswith('Pu239'):
        raw_we_want.append(sens_parameter_ids.index(parameter_id))
    else:
        continue

raw_desired_rel_sens_values = rel_sens_values[raw_we_want, desired_sens_response_index]

prior_mts = ['00002', '00004', '00016', '00017', '00018', '00037', '00102', '00452', '00456']
prior_pfns_ids = ['01018', '01118', '01218', '01318', '01418', '01518', '01618', '01718', '01818', '01918']
prior_mubar_ids = ['00251', '01251', '02251', '03251', '04251', '05251', '06251', '07251', '08251', '09251']
prior_energy_groups = np.arange(51)

prior_verbose_indices = []
for mt in prior_mts:
    for energy_group in prior_energy_groups:
        index = f'94239_{mt}_{energy_group}'
        prior_verbose_indices.append(index)

for pfns_id in prior_pfns_ids:
    for energy_group in prior_energy_groups:
        index = f'94239_{pfns_id}_{energy_group}'
        prior_verbose_indices.append(index)

for mubar_id in prior_mubar_ids:
    index = f'94239_{mubar_id}'
    prior_verbose_indices.append(index)

prior_index_map = {
    verbose_index: i
    for i, verbose_index in enumerate(prior_verbose_indices)
}

sens_verbose_indices = []

for i in raw_we_want:
    splitted_parameter_id = sens_parameter_ids[i].split('_')
    if splitted_parameter_id[2] == 'elastic':
        QID = '00002'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'inelastic':
        QID = '00004'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'z,2n':
        QID = '00016'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'z,3n':
        QID = '00017'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'fission':
        QID = '00018'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'z,4n':
        QID = '00037'
        energy_group = splitted_parameter_id[3]
    elif splitted_parameter_id[2] == 'capture':
        QID = '00102'
        energy_group = splitted_parameter_id[3]
    elif (splitted_parameter_id[1] == "multiplicity"
        and splitted_parameter_id[2] == "total nu"):
        QID = "00452"
        energy_group = splitted_parameter_id[3]
    elif (splitted_parameter_id[1] == "spectrum"
        and splitted_parameter_id[2] == "prompt nu"):
        incident_group = int(splitted_parameter_id[3])
        energy_group = splitted_parameter_id[4]
        QID = f"{1018 + 100 * incident_group:05d}"
    elif (splitted_parameter_id[1] == "crossSection"
        and splitted_parameter_id[2] == "mubar"):
        incident_group = int(splitted_parameter_id[3])
        QID = f"{251 + 1000 * incident_group:05d}"
    else:
        raise ValueError(f"{sens_parameter_ids[i]} corresponds to no considered QID")

    if QID.endswith('251'):
        SENS_VERBOSE_INDEX = f'94239_{QID}'
    else:
        SENS_VERBOSE_INDEX = f'94239_{QID}_{energy_group}'

    sens_verbose_indices.append(SENS_VERBOSE_INDEX)

# CREATE SENSITIVITY MATRIX
ordered_desired_rel_sens_values = np.zeros((len(prior_verbose_indices),), dtype=np.float64)

for i, sens_verbose_index in enumerate(sens_verbose_indices):
    prior_index = prior_index_map[sens_verbose_index]

    ordered_desired_rel_sens_values[prior_index] = (
        raw_desired_rel_sens_values[i]
    )

# READ THE PRIOR DATA TO NORMALIZE THE SENSITIVITIES
PRIOR_MEAN_PATH = "/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Prior/mu_x_i.hdf5"
prior_mean_file = h5py.File(PRIOR_MEAN_PATH, "r")
mean_vector = np.asarray(prior_mean_file['values'])

# NORMALIZE THE SENSITIVITIES
E_calc_mu_x_i = obs_simulated[desired_obs_response_index]

valid_conversion = (
    (mean_vector != 0.0)
    & (ordered_desired_rel_sens_values != 0.0)
)

abs_sens_values = np.zeros_like(ordered_desired_rel_sens_values, dtype=np.float64)

_ = np.divide(E_calc_mu_x_i * ordered_desired_rel_sens_values, mean_vector,
            out=abs_sens_values, where=valid_conversion)

# BUILD THE SENSITIVITY MATRIX
S = abs_sens_values.reshape(1, -1)

# OUTPUT HDF5
with h5py.File("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Observations/Delta_E_i.hdf5", "w") as mean_hdf5:
    mean_dset = mean_hdf5.create_dataset("values", data=Delta_E_i)
with h5py.File("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Observations/Sigma_E.hdf5", "w") as mean_hdf5:
    mean_dset = mean_hdf5.create_dataset("values", data=Sigma_E)
with h5py.File("/home/aurja/Programming/OECDNEA_WPEC_SG52/Auroras_solution/Exercise_1/Observations/S.hdf5", "w") as mean_hdf5:
    mean_dset = mean_hdf5.create_dataset("values", data=S)
