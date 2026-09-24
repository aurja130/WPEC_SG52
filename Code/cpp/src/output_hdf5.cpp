// Nuclear Data Adjustment Tool
// Copyright (C) 2026 Aurora Jahan
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.

#include "output_hdf5.hpp"

#include <highfive/highfive.hpp>

#include <limits>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

namespace {
auto replace_dataset(HighFive::File &file, const std::string &dataset_path,
                     const std::vector<std::size_t> &dimensions,
                     const double *values, std::size_t value_count) -> void {
  if (dataset_path.empty()) {
    throw std::invalid_argument(
        "write_dataset: dataset path must not be empty");
  }
  if (dimensions.empty()) {
    throw std::invalid_argument(
        "write_dataset: dataset must have at least one dimension");
  }
  if (value_count == 0) {
    throw std::invalid_argument("write_dataset: dataset must not be empty");
  }

  if (file.exist(dataset_path)) {
    if (file.getObjectType(dataset_path) != HighFive::ObjectType::Dataset) {
      throw std::runtime_error("write_dataset: path '" + dataset_path +
                               "' in file is not a dataset");
    }
    file.unlink(dataset_path);
  }

  auto dataset = file.createDataSet<double>(
      dataset_path, HighFive::DataSpace(dimensions), {}, {}, true);
  dataset.write_raw(values, HighFive::AtomicType<double>());
}

auto write_vector(HighFive::File &file, const std::string &dataset_path,
                  const Eigen::VectorXd &vector) -> void {
  if (vector.size() == 0) {
    throw std::invalid_argument("write_dataset: vector must not be empty");
  }
  const auto size = static_cast<std::size_t>(vector.size());
  replace_dataset(file, dataset_path, {size}, vector.data(), size);
}

auto write_matrix(HighFive::File &file, const std::string &dataset_path,
                  const Eigen::MatrixXd &matrix) -> void {
  if (matrix.rows() == 0 || matrix.cols() == 0) {
    throw std::invalid_argument("write_dataset: matrix must not be empty");
  }

  const auto rows = static_cast<std::size_t>(matrix.rows());
  const auto columns = static_cast<std::size_t>(matrix.cols());
  if (rows > std::numeric_limits<std::size_t>::max() / columns) {
    throw std::overflow_error("write_dataset: matrix is too large");
  }
  const std::size_t value_count = rows * columns;

  std::vector<double> row_major(value_count);
  for (std::size_t row{0}; row < rows; ++row) {
    for (std::size_t column{0}; column < columns; ++column) {
      row_major.at(row * columns + column) = matrix(
          static_cast<Eigen::Index>(row), static_cast<Eigen::Index>(column));
    }
  }
  replace_dataset(file, dataset_path, {rows, columns}, row_major.data(),
                  value_count);
}
} // namespace

auto write_dataset(const std::filesystem::path &file_path,
                   const std::string &dataset_path, const Dataset &data)
    -> void {
  const std::filesystem::path parent_directory = file_path.parent_path();
  if (!parent_directory.empty()) {
    std::filesystem::create_directories(parent_directory);
  }
  HighFive::File file(file_path.string(),
                      HighFive::File::ReadWrite | HighFive::File::Create);
  std::visit(
      [&file, &dataset_path](const auto &value) {
        using Value = std::decay_t<decltype(value)>;
        if constexpr (std::is_same_v<Value, Eigen::VectorXd>) {
          write_vector(file, dataset_path, value);
        } else {
          write_matrix(file, dataset_path, value);
        }
      },
      data);
  file.flush();
}
