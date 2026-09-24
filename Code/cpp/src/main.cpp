// Nuclear Data Adjustment Tool
// Copyright (C) 2026 Aurora Jahan
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 3 as
// published by the Free Software Foundation.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include <exception>
#include <iostream>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>

#include "glls.hpp"
#include "input_parser.hpp"
#include "output_hdf5.hpp"

namespace {
auto require_vector(const Dataset &data, std::string_view card_name)
    -> const Eigen::VectorXd & {
  if (!std::holds_alternative<Eigen::VectorXd>(data)) {
    throw std::runtime_error(std::string{card_name} +
                             " dataset must be a vector");
  }
  return std::get<Eigen::VectorXd>(data);
}

auto require_matrix(const Dataset &data, std::string_view card_name)
    -> const Eigen::MatrixXd & {
  if (!std::holds_alternative<Eigen::MatrixXd>(data)) {
    throw std::runtime_error(std::string{card_name} +
                             " dataset must be a matrix");
  }
  return std::get<Eigen::MatrixXd>(data);
}
auto print_dataset_info(std::string_view label, const std::string &file_path,
                        const std::string &dataset_path, Eigen::Index rows,
                        Eigen::Index columns) -> void {
  std::cout << label << '\n'
            << "     file = " << file_path << '\n'
            << "     dataset = " << dataset_path << '\n'
            << "     dimensions = " << rows << " x " << columns << "\n\n";
}
} // namespace

auto main(int argc, char *argv[]) -> int {
  const std::span<char *const> arguments(argv, static_cast<std::size_t>(argc));
  if (arguments.size() != 2) {
    const char *executable = arguments.empty() ? "nda" : arguments.front();
    std::cerr << "Usage: " << executable << " <input-file>\n";
    return 2;
  }

  try {
    const InputPaths paths = parse_input(arguments.back());
    const Dataset prior_mean_data =
        read_dataset(paths.prmean_filepath, paths.prmean_dataset);
    const Dataset prior_covariance_data =
        read_dataset(paths.prcov_filepath, paths.prcov_dataset);
    const Dataset observation_delta_data =
        read_dataset(paths.obsdelta_filepath, paths.obsdelta_dataset);
    const Dataset observation_covariance_data =
        read_dataset(paths.obscov_filepath, paths.obscov_dataset);
    const Dataset sensitivity_data =
        read_dataset(paths.sens_filepath, paths.sens_dataset);

    const auto &prior_mean = require_vector(prior_mean_data, "prmean");
    const auto &prior_covariance =
        require_matrix(prior_covariance_data, "prcov");
    const auto &observation_delta =
        require_vector(observation_delta_data, "obsdelta");
    const auto &observation_covariance =
        require_matrix(observation_covariance_data, "obscov");
    const auto &sensitivity = require_matrix(sensitivity_data, "sens");

    print_dataset_info("Prior mean", paths.prmean_filepath,
                       paths.prmean_dataset, prior_mean.size(), 1);
    print_dataset_info("Prior covariance", paths.prcov_filepath,
                       paths.prcov_dataset, prior_covariance.rows(),
                       prior_covariance.cols());
    print_dataset_info("Observation delta", paths.obsdelta_filepath,
                       paths.obsdelta_dataset, observation_delta.size(), 1);
    print_dataset_info("Observation covariance", paths.obscov_filepath,
                       paths.obscov_dataset, observation_covariance.rows(),
                       observation_covariance.cols());
    print_dataset_info("Sensitivity", paths.sens_filepath, paths.sens_dataset,
                       sensitivity.rows(), sensitivity.cols());

    std::cout << "Running GLLS update...\n\n";
    const GLLSResult posterior =
        glls(prior_mean, prior_covariance, sensitivity, observation_delta,
             observation_covariance);
    const Dataset posterior_mean{posterior.mu_x_f};
    const Dataset posterior_covariance{posterior.Sigma_x_f};
    std::cout << '\n';

    write_dataset(paths.psmean_filepath, paths.psmean_dataset, posterior_mean);
    print_dataset_info("Posterior mean", paths.psmean_filepath,
                       paths.psmean_dataset, posterior.mu_x_f.size(), 1);
    write_dataset(paths.pscov_filepath, paths.pscov_dataset,
                  posterior_covariance);
    print_dataset_info("Posterior covariance", paths.pscov_filepath,
                       paths.pscov_dataset, posterior.Sigma_x_f.rows(),
                       posterior.Sigma_x_f.cols());
  } catch (const std::exception &error) {
    std::cerr << error.what() << '\n';
    return 1;
  }

  return 0;
}