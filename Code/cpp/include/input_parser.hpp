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

#pragma once

#include <Eigen/Core>
#include <filesystem>
#include <string>
#include <variant>

struct InputPaths {
  std::string prmean_filepath;
  std::string prmean_dataset;
  std::string prcov_filepath;
  std::string prcov_dataset;
  std::string obsdelta_filepath;
  std::string obsdelta_dataset;
  std::string obscov_filepath;
  std::string obscov_dataset;
  std::string sens_filepath;
  std::string sens_dataset;
};

using Dataset = std::variant<Eigen::MatrixXd, Eigen::VectorXd>;

auto read_dataset(const std::filesystem::path &file_path,
                  const std::string &dataset_path) -> Dataset;

auto parse_input(const std::filesystem::path &input_file) -> InputPaths;
