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

# pragma once
# include <iostream>
# include "linSolve.hpp"

struct GLLSResult
{
    Eigen::VectorXd mu_x_f;
    Eigen::MatrixXd Sigma_x_f;
};

GLLSResult glls(
    const Eigen::VectorXd& mu_x_i,
    const Eigen::MatrixXd& Sigma_x_i,
    const Eigen::MatrixXd& S,
    const Eigen::VectorXd& Delta_E_i,
    const Eigen::MatrixXd& Sigma_E
);