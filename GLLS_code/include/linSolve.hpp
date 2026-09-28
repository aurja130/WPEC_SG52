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
#include <Eigen/Cholesky>
#include <Eigen/Core>
#include <stdexcept>

class SPDSolver {
public:
  explicit SPDSolver(const Eigen::MatrixXd &coefficient_matrix);

  [[nodiscard]]
  Eigen::VectorXd solve(const Eigen::VectorXd &rhs) const;

  [[nodiscard]]
  Eigen::MatrixXd solve(const Eigen::MatrixXd &RHS) const;

private:
  Eigen::LLT<Eigen::MatrixXd> llt;
};