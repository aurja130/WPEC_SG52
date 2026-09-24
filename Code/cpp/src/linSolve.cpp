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

#include "linSolve.hpp"

SPDSolver::SPDSolver(const Eigen::MatrixXd &coefficient_matrix) {
  if (coefficient_matrix.rows() != coefficient_matrix.cols()) {
    throw std::invalid_argument(
        "SPDSolver: coefficient matrix must be square.");
  }

  llt.compute(coefficient_matrix);

  if (llt.info() != Eigen::Success) {
    throw std::runtime_error(
        "SPDSolver: Cholesky factorization failed. "
        "Coefficient matrix may not be positive definite.");
  }
}

// Vector RHS
Eigen::VectorXd SPDSolver::solve(const Eigen::VectorXd &rhs) const {
  if (llt.rows() != rhs.rows()) {
    throw std::invalid_argument("SPDSolver: incompatible vector dimensions.");
  }

  return llt.solve(rhs);
}

// Matrix RHS
Eigen::MatrixXd SPDSolver::solve(const Eigen::MatrixXd &RHS) const {
  if (llt.rows() != RHS.rows()) {
    throw std::invalid_argument("SPDSolver: incompatible matrix dimensions.");
  }

  return llt.solve(RHS);
}