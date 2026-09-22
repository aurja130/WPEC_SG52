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

# include <iostream>
# include "glls.hpp"
# include <highfive/highfive.hpp>

int main() {
    std::cout << "Nuclear Data Adjustment Tool; Copyright (C) 2026 Aurora Jahan" << std::endl;
    std::cout << "This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are" << std::endl;
    std::cout << "welcome to redistribute it under certain conditions. Read LICENSE.txt for details." << std::endl;

    Eigen::MatrixXd A(2, 2);
    A << 4.0, 1.0,
         1.0, 3.0;

    Eigen::VectorXd b(2);
    b << 1.0, 2.0;

    SPDSolver solver(A);
    const Eigen::VectorXd x = solver.solve(b);

    std::cout << x << '\n';

    return 0;
}