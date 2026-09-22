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

# include "glls.hpp"

GLLSResult glls(
    const Eigen::VectorXd& mu_x_i,
    const Eigen::MatrixXd& Sigma_x_i,
    const Eigen::MatrixXd& S,
    const Eigen::VectorXd& Delta_E_i,
    const Eigen::MatrixXd& Sigma_E
) {
    // Validate input dimensions
    const Eigen::Index n = mu_x_i.size();
    const Eigen::Index m = Delta_E_i.size();

    if (n == 0 || m == 0) {
        throw std::invalid_argument(
            "glls: input dimensions must be non-zero."
        );
    }
    else if (Sigma_x_i.rows() != n || Sigma_x_i.cols() != n) {
        throw std::invalid_argument(
            "glls: prior covariance matrix must have dimensions n x n."
        );
    }
    else if (S.rows() != m || S.cols() != n) {
        throw std::invalid_argument(
            "glls: sensitivity matrix must have dimensions m x n."
        );
    }
    else if (Sigma_E.rows() != m || Sigma_E.cols() != m) {
        throw std::invalid_argument(
            "glls: observation covariance matrix must have dimensions m x m."
        );
    }
    else {
        std::cout << "glls: input dimensions are valid." << std::endl;
    }

    // Construct V
    Eigen::MatrixXd V = S * Sigma_x_i * S.transpose() + Sigma_E;

    // Factorize V
    SPDSolver solver(V);

    // Solve for a and b
    Eigen::VectorXd a = solver.solve(Delta_E_i);
    Eigen::MatrixXd b = solver.solve((S * Sigma_x_i).eval());

    // Compute mu_x_f and Sigma_x_f
    Eigen::VectorXd mu_x_f = mu_x_i + Sigma_x_i * S.transpose() * a;
    Eigen::MatrixXd Sigma_x_f = Sigma_x_i - Sigma_x_i * S.transpose() * b;

    // Return the results
    return {mu_x_f, Sigma_x_f};
}